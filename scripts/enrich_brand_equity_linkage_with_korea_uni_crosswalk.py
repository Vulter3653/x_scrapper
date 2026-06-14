#!/usr/bin/env python3
"""Enrich Brand Equity / Market Reaction linkage readiness with korea_uni crosswalk fields.

This is a post-processing step after
`scripts/build_brand_equity_market_reaction_linkage_readiness.py`.

Purpose:
- Use the already-copied korea_uni event-study dataset as a read-only fallback
  company crosswalk for ticker, CIK, and NAICS fields.
- Add Industry Homogeneity metadata using NAICS Code:
  NAICS (North American Industry Classification System).
- Recompute linkage coverage counts after fallback enrichment.

Constraints:
- Does not modify korea_uni.
- Does not download external data.
- Does not collect SEC, market, or X data.
- Does not compute Tobin's Q.
- Does not run regressions.
- Does not describe CAR as Tobin's Q or direct consumer-based Brand Equity.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_READINESS = Path("data/derived/brand_equity_linkage/brand_equity_market_reaction_linkage_readiness.csv")
DEFAULT_MANIFEST = Path("data/audit/brand_equity_linkage/brand_equity_market_reaction_linkage_manifest.json")
DEFAULT_MISSING = Path("data/derived/brand_equity_linkage/brand_equity_market_reaction_missing_inputs.csv")
DEFAULT_KOREA_EVENT = Path("data/external/korea_uni/ai_10k_event_study_analysis_dataset.csv")

ADDED_FIELDS = [
    "matched_cik_padded",
    "crosswalk_source",
    "naics_code",
    "naics_description",
    "naics_sector_code",
    "naics_sector_name",
    "industry_homogeneity_control",
    "industry_homogeneity_naics_code",
    "industry_homogeneity_naics_system",
]


def normalize_company(name: str) -> str:
    n = (name or "").lower().strip()
    n = n.replace("&", "and").replace(",", "").replace(".", "").replace("'", "")
    suffixes = [
        " corporation", " corp", " incorporated", " inc", " llc", " ltd", " limited",
        " group", " company", " co", " plc", " holdings", " holding", " enterprises",
        " international", " intl", " services", " solutions",
    ]
    for suffix in suffixes:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return " ".join(n.split())


def read_csv(path: Path, required: bool = True) -> tuple[list[str], list[dict]]:
    if not path.exists():
        if required:
            print(f"ERROR: missing required file: {path}", file=sys.stderr)
            sys.exit(1)
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    return fields, rows


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first_nonempty(row: dict, candidates: list[str]) -> str:
    for c in candidates:
        v = (row.get(c, "") or "").strip()
        if v:
            return v
    return ""


def build_korea_crosswalk(event_rows: list[dict]) -> dict[str, dict]:
    crosswalk: dict[str, dict] = {}
    for row in event_rows:
        company = first_nonempty(row, ["company_name", "company", "firm_name"])
        if not company:
            continue
        key = normalize_company(company)
        if not key:
            continue
        entry = crosswalk.setdefault(key, {
            "company_name": company,
            "ticker": "",
            "cik": "",
            "cik_padded": "",
            "naics_code": "",
            "naics_description": "",
            "naics_sector_code": "",
            "naics_sector_name": "",
        })
        entry["ticker"] = entry["ticker"] or first_nonempty(row, [
            "ticker", "ticker_estimate", "norm_ticker", "ticker_used", "ticker_original"
        ])
        entry["cik"] = entry["cik"] or first_nonempty(row, ["cik", "norm_cik", "cik_estimate"])
        entry["cik_padded"] = entry["cik_padded"] or first_nonempty(row, [
            "cik_padded", "norm_cik", "norm_cik_estimate"
        ])
        entry["naics_code"] = entry["naics_code"] or first_nonempty(row, ["naics_code"])
        entry["naics_description"] = entry["naics_description"] or first_nonempty(row, ["naics_description"])
        entry["naics_sector_code"] = entry["naics_sector_code"] or first_nonempty(row, ["naics_sector_code"])
        entry["naics_sector_name"] = entry["naics_sector_name"] or first_nonempty(row, ["naics_sector_name"])
    return crosswalk


def lookup_crosswalk(norm_key: str, crosswalk: dict[str, dict]) -> tuple[str, dict | None]:
    if norm_key in crosswalk:
        return "korea_uni_exact_company_match", crosswalk[norm_key]
    for k, v in crosswalk.items():
        if k in norm_key or norm_key in k:
            return "korea_uni_partial_company_match", v
    return "", None


def update_missing_inputs(path: Path, ticker_rows: int, cik_rows: int, naics_rows: int) -> None:
    fields, rows = read_csv(path, required=False)
    if not rows:
        return
    for row in rows:
        if row.get("missing_input") == "Ticker / CIK company crosswalk (complete)":
            if ticker_rows or cik_rows:
                row["current_status"] = (
                    f"Partially resolved by korea_uni fallback: ticker rows={ticker_rows}, CIK rows={cik_rows}. "
                    "Original Fortune SEC crosswalk remains incomplete because SEC API returned HTTP 403."
                )
                row["blocking_reason"] = (
                    "No longer blocks CAR linkage where korea_uni fallback matched company names. "
                    "Still blocks Tobin's Q or external financial-panel joins unless the financial panel uses the same identifiers."
                )
                row["resolution_path"] = (
                    "Use korea_uni-derived ticker/CIK fallback for CAR readiness. For Tobin's Q, obtain a financial panel "
                    "and validate ticker/CIK/GVKEY/PERMNO crosswalk separately."
                )
        if row.get("missing_input") == "Industry homogeneity control (NAICS Code)":
            row["current_status"] = f"Available for {naics_rows} firm-period rows via korea_uni NAICS fallback."
    # Add if absent
    if not any(row.get("missing_input") == "Industry homogeneity control (NAICS Code)" for row in rows):
        rows.append({
            "missing_input": "Industry homogeneity control (NAICS Code)",
            "category": "Control variable / industry homogeneity",
            "required_for": "Industry Homogeneity control using NAICS (North American Industry Classification System)",
            "current_status": f"Available for {naics_rows} firm-period rows via korea_uni NAICS fallback.",
            "blocking_reason": "Not blocking CAR linkage; use as industry homogeneity control when present.",
            "resolution_path": "Use naics_code or naics_sector_code from korea_uni event dataset; validate sector granularity before regression.",
        })
    write_csv(path, fields, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich linkage readiness with korea_uni ticker/CIK/NAICS fallback.")
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--missing", type=Path, default=DEFAULT_MISSING)
    parser.add_argument("--korea-event", type=Path, default=DEFAULT_KOREA_EVENT)
    args = parser.parse_args()

    fields, readiness_rows = read_csv(args.readiness, required=True)
    _, event_rows = read_csv(args.korea_event, required=False)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest.exists() else {}

    if not event_rows:
        manifest.update({
            "korea_uni_crosswalk_fallback_used": False,
            "industry_homogeneity_measure": "Industry Homogeneity: NAICS Code — NAICS (North American Industry Classification System)",
            "industry_homogeneity_naics_available_rows": 0,
            "ticker_available_rows_after_korea_fallback": sum(1 for r in readiness_rows if r.get("ticker_available") == "true"),
            "cik_available_rows_after_korea_fallback": sum(1 for r in readiness_rows if r.get("cik_available") == "true"),
        })
        args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("No korea_uni event dataset available. Crosswalk enrichment skipped.")
        return

    crosswalk = build_korea_crosswalk(event_rows)
    enriched_rows = 0
    ticker_rows = 0
    cik_rows = 0
    naics_rows = 0
    join_car_rows = 0
    matched_companies = set()

    for row in readiness_rows:
        company = row.get("company_name", "")
        norm_key = normalize_company(company)
        match_type, cw = lookup_crosswalk(norm_key, crosswalk)
        existing_source = "fortune_sec_crosswalk" if (row.get("matched_ticker") or row.get("matched_cik")) else ""
        row.setdefault("matched_cik_padded", "")
        row.setdefault("crosswalk_source", existing_source)
        row.setdefault("naics_code", "")
        row.setdefault("naics_description", "")
        row.setdefault("naics_sector_code", "")
        row.setdefault("naics_sector_name", "")
        row.setdefault("industry_homogeneity_control", "")
        row.setdefault("industry_homogeneity_naics_code", "")
        row.setdefault("industry_homogeneity_naics_system", "")

        if cw:
            enriched_rows += 1
            matched_companies.add(company)
            if not row.get("matched_ticker") and cw.get("ticker"):
                row["matched_ticker"] = cw["ticker"]
            if not row.get("matched_cik") and cw.get("cik"):
                row["matched_cik"] = cw["cik"]
            if cw.get("cik_padded"):
                row["matched_cik_padded"] = cw["cik_padded"]
            row["ticker_available"] = "true" if row.get("matched_ticker") else "false"
            row["cik_available"] = "true" if row.get("matched_cik") or row.get("matched_cik_padded") else "false"
            if row.get("korea_uni_match_status") in ("unmatched", ""):
                row["korea_uni_match_status"] = "matched" if match_type == "korea_uni_exact_company_match" else "partial_match"
            if not row.get("matched_korea_uni_company_name"):
                row["matched_korea_uni_company_name"] = cw.get("company_name", "")
            row["crosswalk_source"] = match_type
            row["naics_code"] = cw.get("naics_code", "")
            row["naics_description"] = cw.get("naics_description", "")
            row["naics_sector_code"] = cw.get("naics_sector_code", "")
            row["naics_sector_name"] = cw.get("naics_sector_name", "")
            naics_control_code = cw.get("naics_code") or cw.get("naics_sector_code", "")
            row["industry_homogeneity_control"] = "Industry Homogeneity: NAICS Code"
            row["industry_homogeneity_naics_code"] = naics_control_code
            row["industry_homogeneity_naics_system"] = "NAICS (North American Industry Classification System)"

        if row.get("ticker_available") == "true":
            ticker_rows += 1
        if row.get("cik_available") == "true":
            cik_rows += 1
        if row.get("industry_homogeneity_naics_code"):
            naics_rows += 1
        # Allow partial company match to be join-ready when CAR data and temporal alignment are available.
        if (
            row.get("car_outcome_available") == "true"
            and row.get("future_date_flag") != "true"
            and row.get("korea_uni_match_status") in ("matched", "partial_match")
            and (row.get("same_month_alignment_ready") == "true" or row.get("prefiling_lag_alignment_ready") == "true")
        ):
            row["join_ready_for_car"] = "true"
        if row.get("join_ready_for_car") == "true":
            join_car_rows += 1

    final_fields = list(fields)
    for f in ADDED_FIELDS:
        if f not in final_fields:
            final_fields.append(f)
    write_csv(args.readiness, final_fields, readiness_rows)
    update_missing_inputs(args.missing, ticker_rows, cik_rows, naics_rows)

    # Keep Tobin's Q unavailable unless a financial panel is added; CAR readiness can improve.
    reasons = []
    if join_car_rows == 0:
        reasons.append("no firm-period rows are join_ready_for_car")
    reasons.append("Tobin's Q financial statement panel not present in x_scrapper")
    if manifest.get("requires_date_audit"):
        reasons.append(f"future event dates detected ({manifest.get('future_event_count')} events after {manifest.get('reference_date')})")

    manifest.update({
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "korea_uni_crosswalk_fallback_used": True,
        "korea_uni_crosswalk_companies": len(crosswalk),
        "korea_uni_crosswalk_enriched_rows": enriched_rows,
        "ticker_available_rows": ticker_rows,
        "cik_available_rows": cik_rows,
        "ticker_available_rows_after_korea_fallback": ticker_rows,
        "cik_available_rows_after_korea_fallback": cik_rows,
        "matched_company_count": len(matched_companies) or manifest.get("matched_company_count", 0),
        "join_ready_for_car_rows": join_car_rows,
        "industry_homogeneity_measure": "Industry Homogeneity: NAICS Code — NAICS (North American Industry Classification System)",
        "industry_homogeneity_naics_available_rows": naics_rows,
        "industry_homogeneity_naics_system": "NAICS (North American Industry Classification System)",
        "regression_ready": False,
        "reason_regression_not_ready": "; ".join(reasons),
        "external_repo_modified": False,
        "external_data_downloaded": False,
        "x_collection_run": False,
        "market_data_collection_run": False,
        "sec_collection_run": False,
        "humor_outputs_modified": False,
        "raw_data_modified": False,
        "car_is_direct_brand_equity": False,
        "car_is_equivalent_to_tobins_q": False,
    })
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("korea_uni crosswalk enrichment complete")
    print(f"  korea_uni crosswalk companies: {len(crosswalk)}")
    print(f"  enriched rows: {enriched_rows}")
    print(f"  ticker rows: {ticker_rows}")
    print(f"  CIK rows: {cik_rows}")
    print(f"  NAICS industry homogeneity rows: {naics_rows}")
    print(f"  join_ready_for_car rows: {join_car_rows}")


if __name__ == "__main__":
    main()
