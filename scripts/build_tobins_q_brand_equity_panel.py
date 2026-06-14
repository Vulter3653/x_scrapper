#!/usr/bin/env python3
"""Build Tobin's Q Brand Equity firm-year panel scaffold.

Tobin's Q is the primary long-run Brand Equity / firm value proxy for H1-H3
regression analysis (Simon & Sullivan 1993 financial-market-based approach).

Formula:
  tobins_q = (market_cap + total_liabilities) / total_assets
  market_cap = stock_price_fiscal_year_end × shares_outstanding

This script builds a scaffold panel from available identifiers (company_name,
ticker, CIK, fiscal_year, filing_date from korea_uni event study data) and
marks all financial components as missing where no source is available.

When a financial panel CSV is later supplied via --financial-panel, the script
will join it and compute Tobin's Q for any complete rows.

CAR is NOT used as a substitute for Tobin's Q here.
CAR is a short-window event-study market reaction proxy — distinct from the
long-run level-based firm value measure that Tobin's Q represents.

CONSTRAINTS:
  - No external API calls are made.
  - No SEC data collection is initiated.
  - No market data is collected.
  - Missing financial components are recorded as missing, never imputed.
  - Tobin's Q is only computed where all three components are present.
  - CAR is never used as or equated to Tobin's Q.

Inputs (required):
  data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv

Inputs (optional — supplied by user when available):
  --financial-panel : CSV with total_assets, total_liabilities, market_cap
                      keyed by (ticker, fiscal_year) or (cik, fiscal_year)

Outputs:
  data/derived/brand_equity/tobins_q_brand_equity_panel.csv
  data/derived/brand_equity/tobins_q_missing_components.csv
  data/audit/brand_equity/tobins_q_brand_equity_manifest.json
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_KOREA_EVENT   = Path("data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv")
DEFAULT_FORTUNE_CW    = Path("config/fortune2025/fortune2025_top100_10k_report_index.csv")
DEFAULT_HUMOR_VARS    = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")

DEFAULT_OUT_PANEL     = Path("data/derived/brand_equity/tobins_q_brand_equity_panel.csv")
DEFAULT_OUT_MISSING   = Path("data/derived/brand_equity/tobins_q_missing_components.csv")
DEFAULT_OUT_MANIFEST  = Path("data/audit/brand_equity/tobins_q_brand_equity_manifest.json")

# Tobin's Q formula (Chung & Pruitt 1994 approximation)
TOBINS_Q_FORMULA = "(market_cap + total_liabilities) / total_assets"
MARKET_CAP_FORMULA = "stock_price_fiscal_year_end × shares_outstanding"

PANEL_FIELDS = [
    "company_name",
    "ticker",
    "cik",
    "fiscal_year",
    "filing_date",
    "total_assets",
    "total_liabilities",
    "market_cap",
    "shares_outstanding",
    "stock_price_fiscal_year_end",
    "tobins_q",
    "tobins_q_formula_used",
    "data_available_flag",
    "missing_component_reason",
]

MISSING_FIELDS = [
    "component_name",
    "required_for",
    "source_type",
    "rows_missing",
    "status",
    "resolution_path",
]

# ---------------------------------------------------------------------------
# Missing component definitions (static — reflects current repo state)
# ---------------------------------------------------------------------------
MISSING_COMPONENT_TEMPLATES = [
    {
        "component_name":  "total_assets",
        "required_for":    "Tobin's Q denominator",
        "source_type":     "financial_statement_panel",
        "status":          "not_available_in_repo",
        "resolution_path": (
            "Obtain from SEC EDGAR XBRL companyfacts API "
            "(concept: us-gaap/Assets, form: 10-K) or Compustat Fundamentals Annual (at). "
            "Join to panel by (ticker, fiscal_year) or (cik, fiscal_year)."
        ),
    },
    {
        "component_name":  "total_liabilities",
        "required_for":    "Tobin's Q numerator (book value of debt)",
        "source_type":     "financial_statement_panel",
        "status":          "not_available_in_repo",
        "resolution_path": (
            "Obtain from SEC EDGAR XBRL companyfacts API "
            "(concept: us-gaap/Liabilities, form: 10-K) or Compustat Fundamentals Annual (lt). "
            "Join to panel by (ticker, fiscal_year) or (cik, fiscal_year)."
        ),
    },
    {
        "component_name":  "shares_outstanding",
        "required_for":    "market_cap computation (market_cap = price × shares)",
        "source_type":     "financial_statement_panel_or_market_data",
        "status":          "not_available_in_repo",
        "resolution_path": (
            "Obtain from SEC EDGAR XBRL companyfacts API "
            "(concept: us-gaap/CommonStockSharesOutstanding, form: 10-K), "
            "or Compustat Fundamentals Annual (csho), or CRSP shares outstanding. "
            "Use fiscal year-end value."
        ),
    },
    {
        "component_name":  "stock_price_fiscal_year_end",
        "required_for":    "market_cap computation (market_cap = price × shares)",
        "source_type":     "market_data",
        "status":          "not_available_in_repo",
        "resolution_path": (
            "Obtain closing price at fiscal year-end date from CRSP (prc), "
            "Yahoo Finance, or Compustat CRSP merged (prcc_f). "
            "Join to panel by (ticker, fiscal_year_end_date)."
        ),
    },
    {
        "component_name":  "market_cap",
        "required_for":    "Tobin's Q numerator (market value of equity)",
        "source_type":     "derived_from_price_and_shares_or_market_data",
        "status":          "not_available_in_repo",
        "resolution_path": (
            "Compute as stock_price_fiscal_year_end × shares_outstanding once both "
            "components are available. Alternatively, use market cap directly from "
            "Compustat (mkvalt) or CRSP (prc × shrout) at fiscal year-end."
        ),
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: Path, label: str, required: bool = True) -> list[dict] | None:
    if not path.exists():
        if required:
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)
        print(f"  INFO: {label} not found (optional): {path}")
        return None
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            if required:
                print(f"ERROR: {label} has no header: {path}", file=sys.stderr)
                sys.exit(1)
            return None
        rows = list(reader)
    print(f"  Loaded {label}: {len(rows)} rows")
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def safe_float(val: str) -> float | None:
    try:
        v = float(str(val).strip().replace(",", ""))
        return v if v == v else None  # NaN guard
    except (ValueError, TypeError):
        return None


def try_tobins_q(
    market_cap: float | None,
    total_liabilities: float | None,
    total_assets: float | None,
) -> tuple[float | None, str]:
    """Attempt Tobin's Q computation. Returns (value_or_None, formula_note)."""
    if market_cap is None or total_liabilities is None or total_assets is None:
        return None, ""
    if total_assets == 0:
        return None, "total_assets_zero"
    q = (market_cap + total_liabilities) / total_assets
    return round(q, 6), TOBINS_Q_FORMULA


def try_market_cap(price: float | None, shares: float | None) -> float | None:
    if price is None or shares is None:
        return None
    return price * shares


# ---------------------------------------------------------------------------
# Build financial panel index (if external financial panel is provided)
# ---------------------------------------------------------------------------

def build_financial_index(fin_rows: list[dict] | None) -> dict[tuple, dict]:
    """Build {(ticker_upper, fiscal_year_str): {total_assets, total_liabilities, ...}}."""
    if not fin_rows:
        return {}
    index: dict[tuple, dict] = {}
    for r in fin_rows:
        ticker = r.get("ticker", r.get("TICKER", "")).strip().upper()
        cik    = r.get("cik", r.get("CIK", "")).strip().lstrip("0")
        fy     = str(r.get("fiscal_year", r.get("year", ""))).strip()
        if not fy:
            continue
        entry = {
            "total_assets":              safe_float(r.get("total_assets",  r.get("Assets", ""))),
            "total_liabilities":         safe_float(r.get("total_liabilities", r.get("Liabilities", ""))),
            "market_cap":                safe_float(r.get("market_cap",    r.get("market_capitalization", ""))),
            "shares_outstanding":        safe_float(r.get("shares_outstanding", r.get("shares", ""))),
            "stock_price_fiscal_year_end": safe_float(r.get("stock_price_fiscal_year_end", r.get("price_fy_end", ""))),
        }
        if ticker:
            index[(ticker, fy)] = entry
        if cik:
            cik_norm = cik.lstrip("0")
            index[(cik_norm, fy)] = entry
    print(f"  Financial index built: {len(index)} entries")
    return index


# ---------------------------------------------------------------------------
# Build scaffold from korea_uni event study file
# ---------------------------------------------------------------------------

def build_scaffold(
    event_rows: list[dict],
    fin_index: dict[tuple, dict],
) -> list[dict]:
    """
    One row per (company_name, ticker, cik, fiscal_year).
    Financial components filled from fin_index if available; otherwise marked missing.
    """
    # Deduplicate by (ticker, fiscal_year) — korea_uni file has one row per company-FY
    seen: set = set()
    panel_rows = []

    for r in event_rows:
        company_name = r.get("company_name", r.get("company", "")).strip()
        ticker       = r.get("ticker", "").strip().upper()
        cik          = str(r.get("cik", "")).strip().lstrip("0")
        fiscal_year  = str(r.get("fiscal_year", "")).strip()
        filing_date  = r.get("filing_date", "").strip()

        dedup_key = (ticker or cik, fiscal_year)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Attempt to find financial data
        fin = fin_index.get((ticker, fiscal_year), fin_index.get((cik, fiscal_year), {}))

        total_assets              = fin.get("total_assets")
        total_liabilities         = fin.get("total_liabilities")
        shares_outstanding        = fin.get("shares_outstanding")
        stock_price_fiscal_ye     = fin.get("stock_price_fiscal_year_end")
        market_cap                = fin.get("market_cap")

        # Derive market_cap if price and shares are available but market_cap is not
        if market_cap is None:
            market_cap = try_market_cap(stock_price_fiscal_ye, shares_outstanding)

        tobins_q, formula_used = try_tobins_q(market_cap, total_liabilities, total_assets)

        # Determine which components are missing
        missing = []
        if total_assets is None:
            missing.append("total_assets")
        if total_liabilities is None:
            missing.append("total_liabilities")
        if market_cap is None:
            missing.append("market_cap")
            if stock_price_fiscal_ye is None:
                missing.append("stock_price_fiscal_year_end")
            if shares_outstanding is None:
                missing.append("shares_outstanding")
        elif stock_price_fiscal_ye is None:
            missing.append("stock_price_fiscal_year_end")
        if shares_outstanding is None and "shares_outstanding" not in missing:
            missing.append("shares_outstanding")

        data_available = tobins_q is not None

        panel_rows.append({
            "company_name":               company_name,
            "ticker":                     ticker,
            "cik":                        cik,
            "fiscal_year":                fiscal_year,
            "filing_date":                filing_date,
            "total_assets":               "" if total_assets is None else total_assets,
            "total_liabilities":          "" if total_liabilities is None else total_liabilities,
            "market_cap":                 "" if market_cap is None else round(market_cap, 2),
            "shares_outstanding":         "" if shares_outstanding is None else shares_outstanding,
            "stock_price_fiscal_year_end": "" if stock_price_fiscal_ye is None else stock_price_fiscal_ye,
            "tobins_q":                   "" if tobins_q is None else tobins_q,
            "tobins_q_formula_used":      formula_used,
            "data_available_flag":        "true" if data_available else "false",
            "missing_component_reason":   "; ".join(missing) if missing else "",
        })

    return panel_rows


# ---------------------------------------------------------------------------
# Build missing components report
# ---------------------------------------------------------------------------

def build_missing_components(panel_rows: list[dict]) -> list[dict]:
    n = len(panel_rows)
    counts = {
        "total_assets":               0,
        "total_liabilities":          0,
        "market_cap":                 0,
        "shares_outstanding":         0,
        "stock_price_fiscal_year_end": 0,
    }
    for r in panel_rows:
        missing_str = r.get("missing_component_reason", "")
        for comp in missing_str.split("; "):
            comp = comp.strip()
            if comp in counts:
                counts[comp] += 1

    rows = []
    for tmpl in MISSING_COMPONENT_TEMPLATES:
        comp = tmpl["component_name"]
        rows.append({
            "component_name":  comp,
            "required_for":    tmpl["required_for"],
            "source_type":     tmpl["source_type"],
            "rows_missing":    counts.get(comp, n),
            "status":          tmpl["status"] if counts.get(comp, n) > 0 else "available",
            "resolution_path": tmpl["resolution_path"],
        })
    return rows


# ---------------------------------------------------------------------------
# Build manifest
# ---------------------------------------------------------------------------

def build_manifest(
    panel_rows: list[dict],
    korea_event_path: Path,
    fin_panel_path: Path | None,
) -> dict:
    n = len(panel_rows)
    tickers   = {r["ticker"] for r in panel_rows if r["ticker"]}
    ciks      = {r["cik"]    for r in panel_rows if r["cik"]}
    companies = {r["company_name"] for r in panel_rows if r["company_name"]}

    def count_present(field: str) -> int:
        return sum(1 for r in panel_rows if r.get(field) not in ("", None))

    rows_total_assets      = count_present("total_assets")
    rows_total_liabilities = count_present("total_liabilities")
    rows_market_cap        = count_present("market_cap")
    rows_tobins_q          = count_present("tobins_q")

    tobins_q_available         = rows_tobins_q > 0
    regression_ready_tobins_q  = rows_tobins_q > 0

    reasons = []
    if rows_total_assets == 0:
        reasons.append("total_assets missing for all rows (financial statement panel not available)")
    if rows_total_liabilities == 0:
        reasons.append("total_liabilities missing for all rows")
    if rows_market_cap == 0:
        reasons.append("market_cap missing for all rows (stock price × shares not available)")
    if not reasons:
        reasons.append("all components present")

    return {
        "created_at":                   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tobins_q_formula":             TOBINS_Q_FORMULA,
        "market_cap_formula":           MARKET_CAP_FORMULA,
        "tobins_q_theoretical_basis":   "Simon & Sullivan (1993) financial-market-based brand equity approach",
        "car_note":                     (
            "CAR is NOT used as a substitute for Tobin's Q. "
            "CAR is a short-window capital market response proxy (event-study). "
            "Tobin's Q is the primary long-run level-based DV."
        ),
        "source_files": {
            "korea_uni_event_study": str(korea_event_path),
            "financial_panel":       str(fin_panel_path) if fin_panel_path else "not_provided",
        },
        "firm_year_rows":               n,
        "unique_companies":             len(companies),
        "companies_with_ticker":        len(tickers),
        "companies_with_cik":           len(ciks),
        "rows_with_total_assets":       rows_total_assets,
        "rows_with_total_liabilities":  rows_total_liabilities,
        "rows_with_market_cap":         rows_market_cap,
        "rows_with_tobins_q":           rows_tobins_q,
        "missing_total_assets_count":   n - rows_total_assets,
        "missing_total_liabilities_count": n - rows_total_liabilities,
        "missing_market_cap_count":     n - rows_market_cap,
        "tobins_q_available":           tobins_q_available,
        "regression_ready_with_tobins_q": regression_ready_tobins_q,
        "reason_tobins_q_not_ready":    "; ".join(reasons),
        "fiscal_years_in_panel":        sorted({r["fiscal_year"] for r in panel_rows if r["fiscal_year"]}),
        # Constraint flags
        "external_data_downloaded":     False,
        "sec_collection_run":           False,
        "market_data_collection_run":   False,
        "tobins_q_imputed":             False,
        "car_used_as_tobins_q":         False,
        "raw_data_modified":            False,
        "humor_outputs_modified":       False,
        # Resolution path summary
        "next_steps_to_enable_tobins_q": [
            "Obtain total_assets and total_liabilities from SEC EDGAR XBRL companyfacts API "
            "(concept: us-gaap/Assets and us-gaap/Liabilities, form: 10-K) — "
            "store at data/external/financial_panel/sec_xbrl_financial_panel.csv",
            "Obtain stock_price_fiscal_year_end and shares_outstanding from CRSP or "
            "Yahoo Finance — store at data/external/financial_panel/market_price_panel.csv",
            "Supply either file as --financial-panel to this script for automatic Tobin's Q computation",
            "Alternatively, use Compustat Fundamentals Annual: "
            "at (total assets), lt (total liabilities), mkvalt (market cap) by GVKEY/fiscal_year",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build Tobin's Q Brand Equity firm-year panel scaffold."
    )
    parser.add_argument("--korea-event",     type=Path, default=DEFAULT_KOREA_EVENT,
                        help="korea_uni event study dataset (company/ticker/CIK/fiscal_year source)")
    parser.add_argument("--fortune-crosswalk", type=Path, default=DEFAULT_FORTUNE_CW,
                        help="Fortune 500 10-K crosswalk (supplementary identifier source)")
    parser.add_argument("--financial-panel",  type=Path, default=None,
                        help="Optional external financial panel CSV with total_assets, total_liabilities, "
                             "market_cap or price/shares, keyed by (ticker/cik, fiscal_year)")
    parser.add_argument("--out-panel",    type=Path, default=DEFAULT_OUT_PANEL)
    parser.add_argument("--out-missing",  type=Path, default=DEFAULT_OUT_MISSING)
    parser.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MANIFEST)
    args = parser.parse_args()

    print(f"\nLoading korea_uni event study: {args.korea_event}")
    event_rows = load_csv(args.korea_event, "korea_uni event study", required=True)

    # Optional financial panel
    fin_rows = None
    if args.financial_panel:
        print(f"Loading financial panel: {args.financial_panel}")
        fin_rows = load_csv(args.financial_panel, "external financial panel", required=False)
    else:
        print("  INFO: No --financial-panel provided. All financial components will be marked missing.")

    fin_index = build_financial_index(fin_rows)

    print("\nBuilding Tobin's Q scaffold panel...")
    panel_rows = build_scaffold(event_rows, fin_index)
    print(f"  Panel rows: {len(panel_rows)}")

    n_tobins_q = sum(1 for r in panel_rows if r.get("tobins_q") not in ("", None))
    n_missing_all = sum(
        1 for r in panel_rows
        if all(r.get(f) in ("", None) for f in ["total_assets", "total_liabilities", "market_cap"])
    )
    print(f"  Rows with computable Tobin's Q: {n_tobins_q}")
    print(f"  Rows missing all financial components: {n_missing_all}")

    print("\nBuilding missing components report...")
    missing_rows = build_missing_components(panel_rows)

    print("\nBuilding manifest...")
    manifest = build_manifest(panel_rows, args.korea_event, args.financial_panel)

    # Write outputs
    n_panel   = write_csv(args.out_panel,   PANEL_FIELDS,   panel_rows)
    n_missing = write_csv(args.out_missing, MISSING_FIELDS, missing_rows)
    print(f"  Panel   → {args.out_panel} ({n_panel} rows)")
    print(f"  Missing → {args.out_missing} ({n_missing} rows)")

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest → {args.out_manifest}")

    print(f"\n{'='*60}")
    print(f"Tobin's Q Panel Summary")
    print(f"  firm_year_rows:                 {manifest['firm_year_rows']}")
    print(f"  unique_companies:               {manifest['unique_companies']}")
    print(f"  companies_with_ticker:          {manifest['companies_with_ticker']}")
    print(f"  companies_with_cik:             {manifest['companies_with_cik']}")
    print(f"  rows_with_total_assets:         {manifest['rows_with_total_assets']}")
    print(f"  rows_with_total_liabilities:    {manifest['rows_with_total_liabilities']}")
    print(f"  rows_with_market_cap:           {manifest['rows_with_market_cap']}")
    print(f"  rows_with_tobins_q:             {manifest['rows_with_tobins_q']}")
    print(f"  tobins_q_available:             {manifest['tobins_q_available']}")
    print(f"  regression_ready_with_tobins_q: {manifest['regression_ready_with_tobins_q']}")
    if not manifest["regression_ready_with_tobins_q"]:
        print(f"  reason: {manifest['reason_tobins_q_not_ready']}")


if __name__ == "__main__":
    main()
