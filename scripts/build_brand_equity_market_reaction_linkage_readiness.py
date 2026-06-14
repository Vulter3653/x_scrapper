#!/usr/bin/env python3
"""Build Brand Equity and Market Reaction Linkage Readiness.

Assesses readiness of x_scrapper humor variables for joining with Brand Equity
proxies (Tobin's Q) and market-based reaction outcomes (CAR, AbnormalVolume).

DV roles:
  Tobin's Q    — primary long-run Brand Equity / firm value proxy
                 (Simon & Sullivan 1993 financial-market-based approach)
                 CURRENTLY MISSING: financial statement panel not in x_scrapper.
  CAR          — short-window capital market response proxy; market-based firm
                 value response around 10-K filing dates (from korea_uni).
                 NOT equivalent to Tobin's Q.
                 NOT a direct consumer-based brand equity measure.
                 NOT to be used as a causal brand equity claim.
  AbnormalVolume — investor attention / trading attention proxy.

CONSTRAINTS (enforced throughout):
  - No regression is run here.
  - No Brand Equity values are generated or imputed.
  - No market data is downloaded (network calls forbidden).
  - No SEC data collection is initiated.
  - No X collection is initiated.
  - Humor outputs are NOT modified.
  - Raw data is NOT modified.
  - korea_uni files are read ONLY if user has manually placed them in
    data/external/korea_uni/ — absent files produce unavailable flags, not errors.
  - CAR is never described as equivalent to Tobin's Q or as a direct causal
    brand equity estimate.

Inputs (required):
  data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv
  data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json

Inputs (optional — placed manually by user from korea_uni):
  data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv
  data/external/korea_uni/post_filing_market_reaction_estimates.csv
  data/external/korea_uni/market_data_collection_report.csv

Outputs:
  data/derived/brand_equity_linkage/brand_equity_market_reaction_linkage_readiness.csv
  data/derived/brand_equity_linkage/dv_candidate_variable_dictionary.csv
  data/derived/brand_equity_linkage/brand_equity_market_reaction_missing_inputs.csv
  data/audit/brand_equity_linkage/brand_equity_market_reaction_linkage_manifest.json
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_HUMOR_VARS     = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
DEFAULT_HUMOR_MANIFEST = Path("data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json")
DEFAULT_KOREA_EVENT    = Path("data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv")
DEFAULT_KOREA_MARKET   = Path("data/external/korea_uni/post_filing_market_reaction_estimates.csv")
DEFAULT_KOREA_REPORT   = Path("data/external/korea_uni/market_data_collection_report.csv")
DEFAULT_FORTUNE_10K    = Path("config/fortune2025/fortune2025_top100_10k_report_index.csv")

DEFAULT_OUT_READINESS  = Path("data/derived/brand_equity_linkage/brand_equity_market_reaction_linkage_readiness.csv")
DEFAULT_OUT_DV_DICT    = Path("data/derived/brand_equity_linkage/dv_candidate_variable_dictionary.csv")
DEFAULT_OUT_MISSING    = Path("data/derived/brand_equity_linkage/brand_equity_market_reaction_missing_inputs.csv")
DEFAULT_OUT_MANIFEST   = Path("data/audit/brand_equity_linkage/brand_equity_market_reaction_linkage_manifest.json")

# Event outcome column families
CAR_COLS      = ["CAR_m1_p1", "CAR_0_p1", "CAR_0_p3", "CAR_0_p5"]
ABVOL_COLS    = ["AbnormalVolume_0_p1", "AbnormalVolume_0_p3", "AbnormalVolume_0_p5"]
PLACEBO_COLS  = ["CAR_m10_m6", "CAR_m5_m2", "AbnormalVolume_m5_m2"]
ALL_EVENT_COLS = CAR_COLS + ABVOL_COLS + PLACEBO_COLS

# Company name normalization
_NORM_SUFFIXES = [
    " corporation", " corp", " incorporated", " inc", " llc", " ltd", " limited",
    " group", " company", " co", " plc", " holdings", " holding", " enterprises",
    " international", " intl", " services", " solutions",
]

# ---------------------------------------------------------------------------
# Output field definitions
# ---------------------------------------------------------------------------
READINESS_FIELDS = [
    "company_name", "period", "period_year", "period_month",
    "total_posts", "humor_count", "humor_share",
    "aggressive_count", "aggressive_humor_usage_intensity",
    "source_x_handle_count", "source_x_handle_list",
    # Crosswalk
    "ticker_available", "cik_available", "matched_ticker", "matched_cik",
    "matched_korea_uni_company_name", "korea_uni_match_status",
    # Tobin's Q
    "tobins_q_available", "tobins_q_join_ready", "tobins_q_blocking_reason",
    # CAR / event outcomes
    "car_outcome_available", "matched_event_count",
    "nearest_filing_date", "nearest_event_trading_date",
    "nearest_target_report_year", "nearest_event_time_gap_days",
    "CAR_m1_p1_available", "CAR_0_p1_available", "CAR_0_p3_available", "CAR_0_p5_available",
    "AbnormalVolume_0_p1_available", "AbnormalVolume_0_p3_available", "AbnormalVolume_0_p5_available",
    "placebo_outcome_available",
    # Alignment
    "same_month_alignment_ready", "prefiling_lag_alignment_ready",
    "join_ready_for_tobins_q", "join_ready_for_car",
    "future_date_flag", "date_alignment_warning",
]

DV_DICT_FIELDS = [
    "dv_candidate", "conceptual_role", "measurement_type",
    "required_inputs", "source_repo_or_source_type",
    "currently_available", "recommended_use", "limitations",
]

MISSING_FIELDS = [
    "missing_input", "category", "required_for",
    "current_status", "blocking_reason", "resolution_path",
]

# ---------------------------------------------------------------------------
# DV candidate dictionary (static definition)
# ---------------------------------------------------------------------------
DV_CANDIDATE_DICTIONARY = [
    {
        "dv_candidate": "tobins_q",
        "conceptual_role": (
            "Primary long-run Brand Equity / firm value proxy "
            "(Simon & Sullivan 1993 financial-market-based approach). "
            "Measures market-based valuation relative to book value."
        ),
        "measurement_type": (
            "Level-based market valuation ratio: "
            "(market value of equity + book value of liabilities) / book value of assets"
        ),
        "required_inputs": (
            "Monthly or annual market capitalization; book value of total assets; "
            "book value of liabilities; preferred stock; fiscal year-end alignment; "
            "ticker or CIK company crosswalk"
        ),
        "source_repo_or_source_type": (
            "Financial statement panel (Compustat / WRDS or equivalent) — "
            "NOT present in x_scrapper"
        ),
        "currently_available": "false",
        "recommended_use": (
            "Primary DV for H1-H3 regression. Join by company_name × fiscal-year "
            "after constructing annual Tobin's Q from financial statement data. "
            "Use fiscal year aligned to humor period (e.g., fiscal year t = humor periods within year t)."
        ),
        "limitations": (
            "Requires financial statement panel not currently in x_scrapper. "
            "SEC CIK matching failed at collection time (HTTP 403). "
            "Ticker/CIK crosswalk incomplete for all 99 sample companies. "
            "Annual frequency creates temporal alignment challenge with monthly humor data."
        ),
    },
    {
        "dv_candidate": "market_to_book",
        "conceptual_role": (
            "Alternative long-run market valuation proxy; simplified approximation "
            "of Tobin's Q using equity-side data only."
        ),
        "measurement_type": "Level-based ratio: market value of equity / book value of equity",
        "required_inputs": "Market capitalization; book value of equity; ticker or CIK crosswalk",
        "source_repo_or_source_type": (
            "Financial statement panel (Compustat or equivalent) — NOT present in x_scrapper"
        ),
        "currently_available": "false",
        "recommended_use": (
            "Robustness check for Tobin's Q. Use when full Tobin's Q data is "
            "unavailable but market cap and book equity are accessible."
        ),
        "limitations": (
            "Simpler than Tobin's Q: ignores liabilities side. "
            "Same data pipeline requirements as Tobin's Q. Not preferred over Tobin's Q."
        ),
    },
    {
        "dv_candidate": "market_cap",
        "conceptual_role": "Market valuation proxy; size-sensitive measure of total firm value.",
        "measurement_type": "Level: shares outstanding × closing price (daily or monthly)",
        "required_inputs": "Daily/monthly stock prices; shares outstanding; ticker crosswalk",
        "source_repo_or_source_type": (
            "Market data feed (CRSP, Yahoo Finance, etc.) — NOT present in x_scrapper"
        ),
        "currently_available": "false",
        "recommended_use": (
            "Scale control or secondary DV. Use log(market_cap) to reduce scale effects. "
            "Not preferred as primary DV due to size confound with firm scale."
        ),
        "limitations": (
            "Scale effect dominates; highly correlated with firm size. "
            "Must control for firm size (revenue, total assets) when using as DV."
        ),
    },
    {
        "dv_candidate": "CAR_m1_p1",
        "conceptual_role": (
            "Short-window capital market response proxy (3-day window: t-1 to t+1). "
            "Market-based firm value response around 10-K filing date. "
            "NOT equivalent to Tobin's Q. NOT direct consumer-based brand equity."
        ),
        "measurement_type": (
            "Cumulative Abnormal Return over event window [-1, +1] relative to 10-K filing date"
        ),
        "required_inputs": (
            "Daily stock returns; market or benchmark returns; 10-K filing date; ticker crosswalk. "
            "Available from korea_uni: data/derived/causal/ai_10k_event_study_analysis_dataset.csv"
        ),
        "source_repo_or_source_type": (
            "korea_uni repo: data/derived/causal/ai_10k_event_study_analysis_dataset.csv "
            "— optional external input; NOT present in x_scrapper"
        ),
        "currently_available": "false",
        "recommended_use": (
            "Primary short-window market reaction proxy. Use with pre-filing humor lag alignment: "
            "humor period = filing_month - 1 (or range -3 to -1). "
            "Interpret as capital market response to 10-K disclosure, not as direct humor→equity effect. "
            "Note: CAR is a short-window market-based brand/value response proxy, not Tobin's Q."
        ),
        "limitations": (
            "Captures only short-window reaction to 10-K filings. "
            "Not equivalent to long-run brand equity (Tobin's Q). "
            "Simultaneity risk: humor posts in the same month as filing may violate temporal ordering. "
            "Pre-filing lag alignment recommended to maintain temporal ordering."
        ),
    },
    {
        "dv_candidate": "CAR_0_p1",
        "conceptual_role": (
            "Short-window capital market response proxy (2-day: t to t+1). "
            "Market-based firm value response; NOT equivalent to Tobin's Q."
        ),
        "measurement_type": "Cumulative Abnormal Return over event window [0, +1]",
        "required_inputs": "Same as CAR_m1_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": (
            "Robustness check for CAR_m1_p1. Narrower post-announcement window "
            "reduces contamination from pre-announcement leakage."
        ),
        "limitations": "Same caveats as CAR_m1_p1. Narrower window may miss post-announcement drift.",
    },
    {
        "dv_candidate": "CAR_0_p3",
        "conceptual_role": (
            "Short-window capital market response proxy (4-day: t to t+3). "
            "Market-based firm value response; NOT equivalent to Tobin's Q."
        ),
        "measurement_type": "Cumulative Abnormal Return over event window [0, +3]",
        "required_inputs": "Same as CAR_m1_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Robustness check; wider window captures short-run post-announcement drift.",
        "limitations": "Wider window increases noise from confounding news events beyond 10-K filing.",
    },
    {
        "dv_candidate": "CAR_0_p5",
        "conceptual_role": (
            "Short-window capital market response proxy (6-day: t to t+5). "
            "Market-based firm value response; NOT equivalent to Tobin's Q."
        ),
        "measurement_type": "Cumulative Abnormal Return over event window [0, +5]",
        "required_inputs": "Same as CAR_m1_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Robustness check for longer post-announcement drift detection.",
        "limitations": "Increasing noise; 6 trading days raises probability of confounding events.",
    },
    {
        "dv_candidate": "AbnormalVolume_0_p1",
        "conceptual_role": (
            "Investor attention / trading attention proxy (2-day window: t to t+1). "
            "Measures investor engagement, not return performance."
        ),
        "measurement_type": (
            "Abnormal trading volume relative to pre-event benchmark over window [0, +1]"
        ),
        "required_inputs": (
            "Daily trading volume; pre-event benchmark volume; 10-K filing date; ticker crosswalk"
        ),
        "source_repo_or_source_type": (
            "korea_uni repo: data/derived/market_extension/post_filing_market_reaction_estimates.csv "
            "— optional external input"
        ),
        "currently_available": "false",
        "recommended_use": (
            "Supplementary outcome: investor attention response. Distinct from CAR. "
            "Use for H1 investor engagement analysis alongside CAR outcomes."
        ),
        "limitations": (
            "Volume response may reflect uncertainty rather than positive sentiment. "
            "Not a price-based brand equity measure. Interpret as attention, not return."
        ),
    },
    {
        "dv_candidate": "AbnormalVolume_0_p3",
        "conceptual_role": "Investor attention / trading attention proxy (4-day: t to t+3).",
        "measurement_type": "Abnormal trading volume over event window [0, +3]",
        "required_inputs": "Same as AbnormalVolume_0_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Robustness check for AbnormalVolume_0_p1.",
        "limitations": "Same caveats as AbnormalVolume_0_p1.",
    },
    {
        "dv_candidate": "AbnormalVolume_0_p5",
        "conceptual_role": "Investor attention / trading attention proxy (6-day: t to t+5).",
        "measurement_type": "Abnormal trading volume over event window [0, +5]",
        "required_inputs": "Same as AbnormalVolume_0_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Robustness check for longer investor attention window.",
        "limitations": "Wider window reduces signal specificity; more confounding events possible.",
    },
    {
        "dv_candidate": "CAR_m10_m6",
        "conceptual_role": (
            "Pre-event placebo diagnostic (window [-10, -6] trading days relative to filing). "
            "NOT a DV for primary analysis."
        ),
        "measurement_type": "Cumulative Abnormal Return over pre-event placebo window",
        "required_inputs": "Same as CAR_m1_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": (
            "Pre-event parallel trends / falsification diagnostic ONLY. "
            "Should not be significantly predicted by humor variables if temporal ordering holds."
        ),
        "limitations": (
            "Placebo only. Not interpretable as brand equity or market reaction to humor. "
            "Use exclusively for pre-trend diagnostic."
        ),
    },
    {
        "dv_candidate": "CAR_m5_m2",
        "conceptual_role": (
            "Pre-event placebo diagnostic (window [-5, -2] trading days). "
            "NOT a DV for primary analysis."
        ),
        "measurement_type": "Cumulative Abnormal Return over pre-event placebo window",
        "required_inputs": "Same as CAR_m1_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Pre-event diagnostic ONLY. Closer pre-event window than CAR_m10_m6.",
        "limitations": "Placebo diagnostic only. Same caveats as CAR_m10_m6.",
    },
    {
        "dv_candidate": "AbnormalVolume_m5_m2",
        "conceptual_role": (
            "Pre-event attention placebo diagnostic (volume window [-5, -2]). "
            "NOT a DV for primary analysis."
        ),
        "measurement_type": "Abnormal trading volume over pre-event placebo window",
        "required_inputs": "Same as AbnormalVolume_0_p1",
        "source_repo_or_source_type": "korea_uni repo — optional external input",
        "currently_available": "false",
        "recommended_use": "Pre-event diagnostic ONLY. Parallel trends check for AbnormalVolume outcomes.",
        "limitations": "Placebo diagnostic only.",
    },
]

# ---------------------------------------------------------------------------
# Missing inputs definition (static)
# ---------------------------------------------------------------------------
MISSING_INPUTS = [
    {
        "missing_input": "Tobin's Q / market valuation financial statement panel",
        "category": "Financial data (primary DV)",
        "required_for": "tobins_q, market_to_book, market_cap",
        "current_status": "Not present in x_scrapper",
        "blocking_reason": (
            "Requires market capitalization, book value of total assets, and liabilities "
            "at firm-year level. No financial statement panel has been collected."
        ),
        "resolution_path": (
            "Obtain from Compustat (WRDS), EDGAR financial statements, or equivalent. "
            "Crosswalk via ticker (PERMNO / GVKEY) or CIK. "
            "Store at data/external/financial_panel/ and re-run this script."
        ),
    },
    {
        "missing_input": "Ticker / CIK company crosswalk (complete)",
        "category": "Company crosswalk",
        "required_for": "All financial market outcomes (tobins_q, CAR, AbnormalVolume)",
        "current_status": (
            "config/fortune2025/fortune2025_top100_10k_report_index.csv present "
            "but sec_cik and sec_ticker are empty (SEC API returned HTTP 403 at collection time)"
        ),
        "blocking_reason": (
            "Without ticker or CIK, humor variables cannot be joined to any "
            "financial market or event study dataset."
        ),
        "resolution_path": (
            "Manually populate sec_ticker and sec_cik in fortune2025_top100_10k_report_index.csv "
            "from EDGAR company search (https://www.sec.gov/cgi-bin/browse-edgar) "
            "or from korea_uni's company crosswalk file."
        ),
    },
    {
        "missing_input": "korea_uni event study data (ai_10k_event_study_analysis_dataset.csv)",
        "category": "Event study outcomes (short-window CAR proxy)",
        "required_for": "CAR_m1_p1, CAR_0_p1, CAR_0_p3, CAR_0_p5, all placebo CAR outcomes",
        "current_status": "Not copied to data/external/korea_uni/ in x_scrapper",
        "blocking_reason": (
            "File must be manually placed by user from korea_uni repo. "
            "GitHub Actions workflows do not clone external repositories."
        ),
        "resolution_path": (
            "Copy from korea_uni repo: "
            "korea_uni/data/derived/causal/ai_10k_event_study_analysis_dataset.csv "
            "→ x_scrapper/data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv"
        ),
    },
    {
        "missing_input": "korea_uni market reaction estimates (post_filing_market_reaction_estimates.csv)",
        "category": "Event study outcomes (AbnormalVolume proxy)",
        "required_for": "AbnormalVolume_0_p1, AbnormalVolume_0_p3, AbnormalVolume_0_p5",
        "current_status": "Not copied to data/external/korea_uni/ in x_scrapper",
        "blocking_reason": "Same as above — manual copy required.",
        "resolution_path": (
            "Copy from korea_uni repo: "
            "korea_uni/data/derived/market_extension/post_filing_market_reaction_estimates.csv "
            "→ x_scrapper/data/external/korea_uni/post_filing_market_reaction_estimates.csv"
        ),
    },
    {
        "missing_input": "korea_uni market data report (market_data_collection_report.csv)",
        "category": "Metadata / coverage audit",
        "required_for": "Coverage audit of which companies have market data",
        "current_status": "Not copied to data/external/korea_uni/ in x_scrapper",
        "blocking_reason": "Manual copy required.",
        "resolution_path": (
            "Copy from korea_uni repo: "
            "korea_uni/data/derived/market_extension/market_data_collection_report.csv "
            "→ x_scrapper/data/external/korea_uni/market_data_collection_report.csv"
        ),
    },
    {
        "missing_input": "Brand equity panel (Tobin's Q values, firm-year level)",
        "category": "Dependent variable panel",
        "required_for": "H1-H3 primary regression (Tobin's Q as DV)",
        "current_status": "Not present in x_scrapper",
        "blocking_reason": (
            "Tobin's Q requires financial statement data (market cap + book assets + liabilities). "
            "These have not been collected. CAR (event-study proxy) is NOT a substitute for Tobin's Q."
        ),
        "resolution_path": (
            "Construct from Compustat annual files (GVKEY) or equivalent. "
            "Join on ticker by fiscal year. Store at data/external/financial_panel/."
        ),
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_company(name: str) -> str:
    n = name.lower().strip()
    n = n.replace("&", "and").replace(",", "").replace(".", "").replace("'", "")
    for suffix in _NORM_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return " ".join(n.split())


def safe_parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def period_from_date(d: date) -> str:
    return d.strftime("%Y-%m")


def period_to_date_start(period: str) -> date | None:
    try:
        return datetime.strptime(period + "-01", "%Y-%m-%d").date()
    except ValueError:
        return None


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year  = d.year + month // 12
    month = month % 12 + 1
    import calendar
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


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
                print(f"ERROR: {label} is empty: {path}", file=sys.stderr)
                sys.exit(1)
            return None
        rows = list(reader)
    print(f"  Loaded {label}: {len(rows)} rows from {path}")
    return rows


def load_json(path: Path, label: str, required: bool = True) -> dict | None:
    if not path.exists():
        if required:
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)
        print(f"  INFO: {label} not found (optional): {path}")
        return None
    obj = json.loads(path.read_text(encoding="utf-8"))
    print(f"  Loaded {label}: {path}")
    return obj


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Fortune 500 crosswalk
# ---------------------------------------------------------------------------

def build_fortune_crosswalk(crosswalk_path: Path) -> dict[str, dict]:
    """Return {normalized_company_name: {firm_name, matched_ticker, matched_cik}}."""
    rows = load_csv(crosswalk_path, "fortune 10-K crosswalk", required=False)
    if not rows:
        return {}

    crosswalk: dict[str, dict] = {}
    for r in rows:
        firm  = r.get("firm_name", "").strip()
        cik   = r.get("sec_cik", "").strip()
        ticker = r.get("sec_ticker", "").strip()
        status = r.get("sec_match_status", "").strip()
        if not firm:
            continue
        key = normalize_company(firm)
        if key not in crosswalk:
            crosswalk[key] = {
                "firm_name":      firm,
                "matched_ticker": "",
                "matched_cik":    "",
            }
        # Prefer rows where CIK/ticker are actually resolved
        if cik and status not in ("sec_source_fetch_failed", ""):
            crosswalk[key]["matched_cik"]    = cik
        if ticker and status not in ("sec_source_fetch_failed", ""):
            crosswalk[key]["matched_ticker"] = ticker

    resolved = sum(1 for v in crosswalk.values() if v["matched_ticker"] or v["matched_cik"])
    print(f"  Crosswalk: {len(crosswalk)} companies, {resolved} with resolved ticker/CIK")
    return crosswalk


# ---------------------------------------------------------------------------
# Korea_uni optional inputs
# ---------------------------------------------------------------------------

def load_korea_uni_data(
    event_path: Path,
    market_path: Path,
    report_path: Path,
) -> dict:
    """Load korea_uni files if present. Returns a status dict."""
    result = {
        "available":           False,
        "event_rows_loaded":   0,
        "market_rows_loaded":  0,
        "report_rows_loaded":  0,
        "available_car_cols":  [],
        "available_abvol_cols":[],
        "available_placebo_cols": [],
        "event_index":         {},   # normalized_company -> list[event_dict]
        "market_index":        {},   # normalized_company -> list[row_dict]
        "event_company_col":   None,
        "event_date_col":      None,
    }

    event_rows  = load_csv(event_path,  "korea_uni event study dataset",     required=False)
    market_rows = load_csv(market_path, "korea_uni market reaction estimates", required=False)
    report_rows = load_csv(report_path, "korea_uni market data report",       required=False)

    if not event_rows and not market_rows:
        print("  INFO: No korea_uni optional inputs found. CAR outcomes unavailable.")
        return result

    result["available"] = True

    # Process event study data
    if event_rows:
        result["event_rows_loaded"] = len(event_rows)
        sample_cols = set(event_rows[0].keys()) if event_rows else set()

        # Detect company column
        for cand in ["firm_name", "company_name", "ticker", "Ticker", "TICKER", "CIK", "cik"]:
            if cand in sample_cols:
                result["event_company_col"] = cand
                break

        # Detect date column
        for cand in ["filing_date", "event_date", "FilingDate", "date", "Date"]:
            if cand in sample_cols:
                result["event_date_col"] = cand
                break

        # Detect which outcome columns exist
        result["available_car_cols"]      = [c for c in CAR_COLS    if c in sample_cols]
        result["available_abvol_cols"]    = [c for c in ABVOL_COLS  if c in sample_cols]
        result["available_placebo_cols"]  = [c for c in PLACEBO_COLS if c in sample_cols]

        # Build event index keyed by normalized company name
        co_col   = result["event_company_col"]
        date_col = result["event_date_col"]
        index: dict[str, list] = defaultdict(list)
        for r in event_rows:
            co_raw = r.get(co_col, "").strip() if co_col else ""
            if not co_raw:
                continue
            key = normalize_company(co_raw)
            event_d = safe_parse_date(r.get(date_col, "") if date_col else "")
            index[key].append({
                "raw_company":          co_raw,
                "filing_date":          r.get(date_col, "") if date_col else "",
                "filing_date_parsed":   event_d,
                "target_report_year":   r.get("target_report_year", ""),
                "event_trading_date":   r.get("event_trading_date", r.get("EventTradingDate", "")),
                "outcomes":             {c: r.get(c, "") for c in ALL_EVENT_COLS if c in sample_cols},
            })
        result["event_index"] = dict(index)
        print(f"  Event index: {len(index)} normalized companies")

    if market_rows:
        result["market_rows_loaded"] = len(market_rows)

    if report_rows:
        result["report_rows_loaded"] = len(report_rows)

    return result


# ---------------------------------------------------------------------------
# Linkage readiness per company-period
# ---------------------------------------------------------------------------

def _find_nearest_event(
    humor_period: str,
    events: list[dict],
) -> dict:
    """Find event nearest to humor_period start date. Returns metadata dict."""
    period_start = period_to_date_start(humor_period)
    if not period_start or not events:
        return {}

    best = None
    best_gap = None
    for ev in events:
        fd = ev.get("filing_date_parsed")
        if fd is None:
            continue
        gap = abs((fd - period_start).days)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best = ev

    if best is None:
        return {}

    filing_period = period_from_date(best["filing_date_parsed"]) if best.get("filing_date_parsed") else ""
    return {
        "nearest_filing_date":        best.get("filing_date", ""),
        "nearest_event_trading_date": best.get("event_trading_date", ""),
        "nearest_target_report_year": best.get("target_report_year", ""),
        "nearest_event_time_gap_days": best_gap,
        "nearest_filing_period":      filing_period,
        "outcomes":                   best.get("outcomes", {}),
        "filing_date_obj":            best.get("filing_date_parsed"),
    }


def build_linkage_row(
    humor_row: dict,
    crosswalk: dict[str, dict],
    korea_uni: dict,
    reference_date: date,
) -> dict:
    company  = humor_row.get("company_name", "").strip()
    period   = humor_row.get("period", "").strip()
    norm_key = normalize_company(company)

    # --- Crosswalk lookup ---
    cw = crosswalk.get(norm_key, {})
    matched_ticker = cw.get("matched_ticker", "")
    matched_cik    = cw.get("matched_cik", "")
    ticker_available = "true" if matched_ticker else "false"
    cik_available    = "true" if matched_cik    else "false"

    # --- Tobin's Q (always unavailable at this stage) ---
    tobins_q_blocking = "Tobin's Q financial/market value panel not present in x_scrapper"

    # --- Korea_uni event matching ---
    ku_available = korea_uni.get("available", False)
    event_index  = korea_uni.get("event_index", {})

    if not ku_available:
        match_status      = "korea_uni_data_not_available"
        matched_ku_name   = ""
        matched_events    = []
    elif norm_key in event_index:
        matched_events  = event_index[norm_key]
        matched_ku_name = matched_events[0]["raw_company"] if matched_events else ""
        match_status    = "matched"
    else:
        # Try partial match: any event_index key that contains or is contained in norm_key
        partial = next(
            (k for k in event_index if k in norm_key or norm_key in k), None
        )
        if partial:
            matched_events  = event_index[partial]
            matched_ku_name = matched_events[0]["raw_company"] if matched_events else ""
            match_status    = "partial_match"
        else:
            matched_events  = []
            matched_ku_name = ""
            match_status    = "unmatched"

    matched_event_count = len(matched_events)
    nearest = _find_nearest_event(period, matched_events)

    # --- Outcome availability ---
    avail_car   = korea_uni.get("available_car_cols",     [])
    avail_abvol = korea_uni.get("available_abvol_cols",   [])
    avail_pl    = korea_uni.get("available_placebo_cols", [])

    car_data_exists  = ku_available and bool(avail_car) and matched_event_count > 0
    abvol_data_exists = ku_available and bool(avail_abvol) and matched_event_count > 0

    def col_avail(col: str, avail_list: list) -> str:
        return "true" if (col in avail_list and matched_event_count > 0) else "false"

    # --- Date alignment ---
    filing_period = nearest.get("nearest_filing_period", "")
    period_start  = period_to_date_start(period)

    same_month_ready = "false"
    prefiling_lag_ready = "false"
    date_warn = ""
    future_flag = "false"
    join_car = "false"

    if nearest:
        filing_date_obj = nearest.get("filing_date_obj")

        # Future date check
        if filing_date_obj and filing_date_obj > reference_date:
            future_flag = "true"
            date_warn   = f"Nearest filing date {filing_date_obj} is after reference date {reference_date}. Regression not valid until after event."

        # Same-month alignment
        if filing_period and period == filing_period:
            same_month_ready = "true"
            if not date_warn:
                date_warn = (
                    "Same-month alignment: simultaneity risk — humor posts in same month as "
                    "filing may violate temporal ordering. Pre-filing lag alignment recommended."
                )

        # Pre-filing lag alignment: humor period is 1-3 months before filing
        if filing_date_obj and period_start:
            for lag in (1, 2, 3):
                lag_period = period_from_date(add_months(filing_date_obj, -lag))
                if period == lag_period:
                    prefiling_lag_ready = "true"
                    break

        if match_status == "matched" and (same_month_ready == "true" or prefiling_lag_ready == "true"):
            join_car = "true"

    return {
        "company_name":         company,
        "period":               period,
        "period_year":          period[:4] if len(period) >= 4 else "",
        "period_month":         period[5:7] if len(period) >= 7 else "",
        "total_posts":          humor_row.get("total_posts", ""),
        "humor_count":          humor_row.get("humor_count", ""),
        "humor_share":          humor_row.get("humor_share", ""),
        "aggressive_count":     humor_row.get("aggressive_count", ""),
        "aggressive_humor_usage_intensity": humor_row.get("aggressive_humor_usage_intensity", ""),
        "source_x_handle_count": humor_row.get("source_x_handle_count", ""),
        "source_x_handle_list":  humor_row.get("source_x_handle_list", ""),
        # Crosswalk
        "ticker_available":     ticker_available,
        "cik_available":        cik_available,
        "matched_ticker":       matched_ticker,
        "matched_cik":          matched_cik,
        "matched_korea_uni_company_name": matched_ku_name,
        "korea_uni_match_status": match_status,
        # Tobin's Q
        "tobins_q_available":    "false",
        "tobins_q_join_ready":   "false",
        "tobins_q_blocking_reason": tobins_q_blocking,
        # CAR
        "car_outcome_available": "true" if car_data_exists else "false",
        "matched_event_count":   matched_event_count,
        "nearest_filing_date":   nearest.get("nearest_filing_date", ""),
        "nearest_event_trading_date": nearest.get("nearest_event_trading_date", ""),
        "nearest_target_report_year": nearest.get("nearest_target_report_year", ""),
        "nearest_event_time_gap_days": nearest.get("nearest_event_time_gap_days", ""),
        "CAR_m1_p1_available":        col_avail("CAR_m1_p1",         avail_car),
        "CAR_0_p1_available":         col_avail("CAR_0_p1",          avail_car),
        "CAR_0_p3_available":         col_avail("CAR_0_p3",          avail_car),
        "CAR_0_p5_available":         col_avail("CAR_0_p5",          avail_car),
        "AbnormalVolume_0_p1_available": col_avail("AbnormalVolume_0_p1", avail_abvol),
        "AbnormalVolume_0_p3_available": col_avail("AbnormalVolume_0_p3", avail_abvol),
        "AbnormalVolume_0_p5_available": col_avail("AbnormalVolume_0_p5", avail_abvol),
        "placebo_outcome_available":  "true" if (ku_available and bool(avail_pl) and matched_event_count > 0) else "false",
        # Alignment
        "same_month_alignment_ready":    same_month_ready,
        "prefiling_lag_alignment_ready": prefiling_lag_ready,
        "join_ready_for_tobins_q":       "false",
        "join_ready_for_car":            join_car,
        "future_date_flag":              future_flag,
        "date_alignment_warning":        date_warn,
    }


# ---------------------------------------------------------------------------
# Future date audit across all events
# ---------------------------------------------------------------------------

def compute_future_audit(korea_uni: dict, reference_date: date) -> dict:
    if not korea_uni.get("available"):
        return {
            "future_event_count": 0,
            "future_event_share": 0.0,
            "future_event_date_min": "",
            "future_event_date_max": "",
            "requires_date_audit": False,
        }

    all_events = [ev for events in korea_uni["event_index"].values() for ev in events]
    total = len(all_events)
    future_dates = [
        ev["filing_date_parsed"] for ev in all_events
        if ev.get("filing_date_parsed") and ev["filing_date_parsed"] > reference_date
    ]
    future_count = len(future_dates)
    return {
        "future_event_count": future_count,
        "future_event_share": round(future_count / total, 4) if total > 0 else 0.0,
        "future_event_date_min": str(min(future_dates)) if future_dates else "",
        "future_event_date_max": str(max(future_dates)) if future_dates else "",
        "requires_date_audit": future_count > 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build Brand Equity and Market Reaction Linkage Readiness."
    )
    parser.add_argument("--humor-variables",  type=Path, default=DEFAULT_HUMOR_VARS)
    parser.add_argument("--humor-manifest",   type=Path, default=DEFAULT_HUMOR_MANIFEST)
    parser.add_argument("--korea-uni-event",  type=Path, default=DEFAULT_KOREA_EVENT)
    parser.add_argument("--korea-uni-market", type=Path, default=DEFAULT_KOREA_MARKET)
    parser.add_argument("--korea-uni-report", type=Path, default=DEFAULT_KOREA_REPORT)
    parser.add_argument("--fortune-crosswalk",type=Path, default=DEFAULT_FORTUNE_10K)
    parser.add_argument("--out-readiness",    type=Path, default=DEFAULT_OUT_READINESS)
    parser.add_argument("--out-dv-dict",      type=Path, default=DEFAULT_OUT_DV_DICT)
    parser.add_argument("--out-missing",      type=Path, default=DEFAULT_OUT_MISSING)
    parser.add_argument("--out-manifest",     type=Path, default=DEFAULT_OUT_MANIFEST)
    args = parser.parse_args()

    reference_date = datetime.now(timezone.utc).date()
    print(f"Reference date: {reference_date}")

    # --- Load inputs ---
    print(f"\nLoading humor variables: {args.humor_variables}")
    humor_rows = load_csv(args.humor_variables, "humor firm-period variables", required=True)

    print(f"Loading humor manifest: {args.humor_manifest}")
    humor_manifest = load_json(args.humor_manifest, "humor manifest", required=True)

    # Validate humor manifest
    h_constraints = humor_manifest.get("constraints", {})
    if not h_constraints.get("hypothesis_testing_ready"):
        print("ERROR: humor manifest hypothesis_testing_ready is not True", file=sys.stderr)
        sys.exit(1)
    dup_count = humor_manifest.get("company_period_duplicate_count", -1)
    if dup_count != 0:
        print(f"ERROR: humor manifest company_period_duplicate_count={dup_count} (must be 0)", file=sys.stderr)
        sys.exit(1)
    print(f"  Humor manifest OK: {len(humor_rows)} firm-period rows, dup_count={dup_count}")

    # --- Load crosswalk ---
    print(f"\nBuilding Fortune 500 crosswalk from: {args.fortune_crosswalk}")
    crosswalk = build_fortune_crosswalk(args.fortune_crosswalk)

    # --- Load korea_uni (optional) ---
    print("\nChecking optional korea_uni inputs...")
    korea_uni = load_korea_uni_data(
        args.korea_uni_event,
        args.korea_uni_market,
        args.korea_uni_report,
    )

    # --- Build per-row readiness ---
    print("\nBuilding linkage readiness per company-period...")
    readiness_rows = [
        build_linkage_row(r, crosswalk, korea_uni, reference_date)
        for r in humor_rows
    ]

    # --- Summary statistics ---
    n = len(readiness_rows)
    ticker_avail      = sum(1 for r in readiness_rows if r["ticker_available"] == "true")
    cik_avail         = sum(1 for r in readiness_rows if r["cik_available"] == "true")
    car_avail         = sum(1 for r in readiness_rows if r["car_outcome_available"] == "true")
    same_month        = sum(1 for r in readiness_rows if r["same_month_alignment_ready"] == "true")
    prefiling_lag     = sum(1 for r in readiness_rows if r["prefiling_lag_alignment_ready"] == "true")
    join_car_count    = sum(1 for r in readiness_rows if r["join_ready_for_car"] == "true")
    matched_companies = {r["company_name"] for r in readiness_rows if r["korea_uni_match_status"] in ("matched", "partial_match")}
    unique_humor_cos  = {r["company_name"] for r in readiness_rows}
    future_flags      = sum(1 for r in readiness_rows if r["future_date_flag"] == "true")

    # --- Future date audit ---
    future_audit = compute_future_audit(korea_uni, reference_date)

    # --- Write outputs ---
    n_readiness = write_csv(args.out_readiness, READINESS_FIELDS, readiness_rows)
    print(f"  Readiness CSV → {args.out_readiness} ({n_readiness} rows)")

    n_dv = write_csv(args.out_dv_dict, DV_DICT_FIELDS, DV_CANDIDATE_DICTIONARY)
    print(f"  DV dict CSV   → {args.out_dv_dict} ({n_dv} rows)")

    n_miss = write_csv(args.out_missing, MISSING_FIELDS, MISSING_INPUTS)
    print(f"  Missing CSV   → {args.out_missing} ({n_miss} rows)")

    # --- Determine regression readiness ---
    regression_ready = False
    reasons_not_ready = []
    if not korea_uni.get("available"):
        reasons_not_ready.append("korea_uni event study data not copied to data/external/korea_uni/")
    if not ticker_avail and not cik_avail:
        reasons_not_ready.append("no ticker or CIK resolved in fortune crosswalk (SEC API 403 at collection)")
    if not join_car_count:
        reasons_not_ready.append("no firm-period rows are join_ready_for_car")
    reasons_not_ready.append("Tobin's Q financial statement panel not present in x_scrapper")
    if future_audit["requires_date_audit"]:
        reasons_not_ready.append(
            f"future event dates detected ({future_audit['future_event_count']} events after {reference_date})"
        )
    reason_str = "; ".join(reasons_not_ready) if reasons_not_ready else "all conditions met"

    # --- Manifest ---
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "created_at":          created_at,
        "reference_date":      str(reference_date),
        "humor_input_rows":    humor_manifest.get("output_rows", len(humor_rows)),
        "humor_company_period_duplicate_count": dup_count,
        "unique_humor_companies": humor_manifest.get("unique_companies", len(unique_humor_cos)),
        "unique_humor_periods":   humor_manifest.get("unique_periods", len({r["period"] for r in humor_rows})),
        # DV roles
        "tobins_q_primary_dv":                  True,
        "tobins_q_available":                   False,
        "car_allowed_as_market_reaction_proxy":  True,
        "car_is_direct_brand_equity":            False,
        "car_is_equivalent_to_tobins_q":         False,
        # Korea_uni
        "korea_uni_inputs_available":            korea_uni.get("available", False),
        "korea_uni_event_rows_loaded":           korea_uni.get("event_rows_loaded", 0),
        "car_outcome_data_available":            bool(korea_uni.get("available_car_cols")),
        "available_car_cols":                    korea_uni.get("available_car_cols", []),
        "available_abvol_cols":                  korea_uni.get("available_abvol_cols", []),
        # Crosswalk
        "fortune_crosswalk_companies":           len(crosswalk),
        "ticker_available_rows":                 ticker_avail,
        "cik_available_rows":                    cik_avail,
        # Matching
        "matched_company_count":                 len(matched_companies),
        # Alignment
        "same_month_alignment_ready_rows":       same_month,
        "prefiling_lag_alignment_ready_rows":    prefiling_lag,
        "join_ready_for_car_rows":               join_car_count,
        # Future date audit
        "future_event_count":                    future_audit["future_event_count"],
        "future_event_share":                    future_audit["future_event_share"],
        "future_event_date_min":                 future_audit["future_event_date_min"],
        "future_event_date_max":                 future_audit["future_event_date_max"],
        "requires_date_audit":                   future_audit["requires_date_audit"],
        # Regression readiness
        "regression_ready":                      regression_ready,
        "reason_regression_not_ready":           reason_str,
        # Constraint flags
        "external_repo_modified":                False,
        "external_data_downloaded":              False,
        "x_collection_run":                      False,
        "market_data_collection_run":            False,
        "sec_collection_run":                    False,
        "humor_outputs_modified":                False,
        "raw_data_modified":                     False,
        # Output paths
        "output_files": {
            "linkage_readiness":       str(args.out_readiness),
            "dv_candidate_dictionary": str(args.out_dv_dict),
            "missing_inputs":          str(args.out_missing),
        },
        # Next steps
        "next_steps": [
            "Copy korea_uni event study files to data/external/korea_uni/ (see brand_equity_market_reaction_missing_inputs.csv)",
            "Manually populate ticker/CIK in config/fortune2025/fortune2025_top100_10k_report_index.csv",
            "Obtain Tobin's Q financial statement panel (Compustat or equivalent)",
            "Re-run Build Brand Equity Market Reaction Linkage Readiness after copying files",
            "Once join_ready_for_car > 0, proceed to regression script construction",
        ],
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest      → {args.out_manifest}")

    print(f"\n{'='*60}")
    print(f"Linkage Readiness Summary")
    print(f"  Humor firm-period rows:     {n}")
    print(f"  Ticker-resolved rows:       {ticker_avail}")
    print(f"  CIK-resolved rows:          {cik_avail}")
    print(f"  korea_uni available:        {korea_uni.get('available')}")
    print(f"  Matched companies (korea):  {len(matched_companies)}")
    print(f"  CAR-available rows:         {car_avail}")
    print(f"  Same-month alignment rows:  {same_month}")
    print(f"  Pre-filing lag align rows:  {prefiling_lag}")
    print(f"  Join-ready for CAR rows:    {join_car_count}")
    print(f"  Future event rows:          {future_flags}")
    print(f"  regression_ready:           {regression_ready}")
    if not regression_ready:
        print(f"  reason: {reason_str}")


if __name__ == "__main__":
    main()
