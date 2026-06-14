#!/usr/bin/env python3
"""Build H1-H3 × CAR regression-ready master dataset.

This script assembles the regression master dataset by joining:
  - humor_car_linkage_panel (company × period × filing_date, with alignment flags)
  - humor_firm_period_hypothesis_variables (for columns not in linkage panel)

The output dataset is regression-ready but the regression itself is NOT run here.

DV hierarchy:
  Tobin's Q:    Primary Brand Equity proxy — DEFERRED (financial panel absent).
  CAR_m1_p1:   Secondary DV, currently executable. Short-window market reaction proxy.
  CAR_m3_p3:   Placeholder — missing. Requires daily abnormal return panel.
  CAR_m5_p5:   Placeholder — missing. Requires daily abnormal return panel.

CONSTRAINTS (all must remain false in manifest):
  - No regression is executed.
  - No causal claims are made.
  - No human/gold label claims are made.
  - CAR is not used as or equated to Tobin's Q.
  - CAR is not labelled as direct Brand Equity.
  - CAR_m3_p3 / CAR_m5_p5 are NOT computed from CAR_0_p3 / CAR_0_p5.
  - No external API calls.
  - Raw data, humor outputs, korea_uni source repo are not modified.

Inputs (required):
  data/derived/car_event_windows/humor_car_linkage_panel.csv
  data/derived/car_event_windows/car_symmetric_event_window_manifest.json
  data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv
  data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json

Outputs:
  data/derived/regression/humor_car_hypothesis_regression_master.csv
  data/derived/regression/humor_car_hypothesis_variable_dictionary.csv
  data/audit/regression/humor_car_regression_master_manifest.json
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_LINKAGE    = Path("data/derived/car_event_windows/humor_car_linkage_panel.csv")
DEFAULT_CAR_MAN    = Path("data/audit/car_event_windows/car_symmetric_event_window_manifest.json")
DEFAULT_HUMOR_VARS = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
DEFAULT_HUMOR_MAN  = Path("data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json")

DEFAULT_OUT_MASTER = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")
DEFAULT_OUT_DICT   = Path("data/derived/regression/humor_car_hypothesis_variable_dictionary.csv")
DEFAULT_OUT_MAN    = Path("data/audit/regression/humor_car_regression_master_manifest.json")

# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------
MASTER_FIELDS = [
    # Identifiers
    "company_name", "ticker", "cik", "period", "filing_date", "target_report_year",
    # Alignment
    "alignment_type", "recommended_main_alignment",
    "same_month_alignment", "prefiling_lag_1m_alignment", "prefiling_lag_3m_alignment",
    # DVs
    "CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5",
    "join_ready_for_CAR_m1_p1", "join_ready_for_CAR_m3_p3", "join_ready_for_CAR_m5_p5",
    # H1 IVs — humor presence / usage
    "humor_share", "humor_count", "log_humor_count", "humor_presence_any",
    "humor_share_ambiguity_as_zero", "humor_share_ambiguity_excluded",
    "humor_share_ambiguity_as_missing",
    # H2 IVs — humor type
    "aggressive_share", "affiliative_share",
    "self_enhancing_share", "self_defeating_share",
    "rare_negative_humor_share",
    # H3 IVs — aggressive intensity (inverted-U)
    "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
    # Diagnostic
    "total_posts", "ambiguity_rate", "high_ambiguity_flag",
    "source_x_handle_count",
    # Industry controls
    "naics_sector_code", "naics_sector_name", "industry_homogeneity_control",
]

DICT_FIELDS = [
    "variable_name", "hypothesis", "role", "var_type",
    "description", "available_in_master", "availability_note",
]

# ---------------------------------------------------------------------------
# Variable dictionary (static definition)
# ---------------------------------------------------------------------------
VARIABLE_DICTIONARY = [
    # DVs
    {
        "variable_name": "CAR_m1_p1",
        "hypothesis": "H1, H2, H3",
        "role": "DV — primary (currently executable)",
        "var_type": "continuous",
        "description": (
            "Cumulative Abnormal Return over symmetric window [-1,+1] trading days "
            "around 10-K filing date. Short-window capital market response proxy. "
            "NOT equivalent to Tobin's Q. NOT direct Brand Equity."
        ),
        "available_in_master": "true",
        "availability_note": "580 rows ready (join_ready_for_CAR_m1_p1=true)",
    },
    {
        "variable_name": "CAR_m3_p3",
        "hypothesis": "H1, H2, H3",
        "role": "DV — medium-window robustness (placeholder)",
        "var_type": "continuous",
        "description": "Cumulative Abnormal Return over symmetric window [-3,+3]. Requires daily abnormal return panel.",
        "available_in_master": "false",
        "availability_note": (
            "Missing. Requires event_window_daily_abnormal_returns.csv. "
            "NOT computed from CAR_0_p3 ([0,+3]). Gemini audit of korea_uni daily AR panel pending."
        ),
    },
    {
        "variable_name": "CAR_m5_p5",
        "hypothesis": "H1, H2, H3",
        "role": "DV — wide-window robustness (placeholder)",
        "var_type": "continuous",
        "description": "Cumulative Abnormal Return over symmetric window [-5,+5]. Requires daily abnormal return panel.",
        "available_in_master": "false",
        "availability_note": (
            "Missing. Requires event_window_daily_abnormal_returns.csv. "
            "NOT computed from CAR_0_p5 ([0,+5]). Confounding event risk increases with wider window."
        ),
    },
    # H1 IVs
    {
        "variable_name": "humor_share",
        "hypothesis": "H1",
        "role": "IV — primary (continuous)",
        "var_type": "continuous [0,1]",
        "description": "Share of posts classified as humor. Primary H1 measure of humor usage/exposure.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "humor_count",
        "hypothesis": "H1",
        "role": "IV (count)",
        "var_type": "integer",
        "description": "Absolute count of humor posts in firm-period.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "log_humor_count",
        "hypothesis": "H1",
        "role": "IV — log-transformed count",
        "var_type": "continuous",
        "description": "log(1 + humor_count). Reduces skew from high-posting firms.",
        "available_in_master": "true",
        "availability_note": "Computed from humor_count: log(1 + count)",
    },
    {
        "variable_name": "humor_presence_any",
        "hypothesis": "H1",
        "role": "IV — binary indicator",
        "var_type": "binary",
        "description": "1 if any humor post in firm-period, 0 otherwise. Binary H1 IV.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "humor_share_ambiguity_as_zero",
        "hypothesis": "H1",
        "role": "IV — ambiguity sensitivity variant",
        "var_type": "continuous [0,1]",
        "description": "humor_share treating ambiguous posts as non-humor.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "humor_share_ambiguity_excluded",
        "hypothesis": "H1",
        "role": "IV — ambiguity sensitivity variant",
        "var_type": "continuous [0,1]",
        "description": "humor_share excluding ambiguous posts from denominator.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "humor_share_ambiguity_as_missing",
        "hypothesis": "H1",
        "role": "IV — ambiguity sensitivity variant",
        "var_type": "continuous or NA",
        "description": "humor_share set to missing (empty) if ambiguity_rate >= 0.50.",
        "available_in_master": "true",
        "availability_note": "",
    },
    # H2 IVs
    {
        "variable_name": "aggressive_share",
        "hypothesis": "H2",
        "role": "IV — humor type (continuous)",
        "var_type": "continuous [0,1]",
        "description": "Share of posts classified as aggressive humor. H2 main type predictor.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "affiliative_share",
        "hypothesis": "H2",
        "role": "IV — humor type (continuous)",
        "var_type": "continuous [0,1]",
        "description": "Share of posts classified as affiliative humor.",
        "available_in_master": "true",
        "availability_note": "Joined from humor_firm_period_hypothesis_variables.csv",
    },
    {
        "variable_name": "self_enhancing_share",
        "hypothesis": "H2",
        "role": "IV — humor type (continuous)",
        "var_type": "continuous [0,1]",
        "description": "Share of posts classified as self-enhancing humor.",
        "available_in_master": "true",
        "availability_note": "Joined from humor_firm_period_hypothesis_variables.csv",
    },
    {
        "variable_name": "self_defeating_share",
        "hypothesis": "H2",
        "role": "IV — humor type (continuous)",
        "var_type": "continuous [0,1]",
        "description": "Share of posts classified as self-defeating humor.",
        "available_in_master": "true",
        "availability_note": "Joined from humor_firm_period_hypothesis_variables.csv",
    },
    {
        "variable_name": "rare_negative_humor_share",
        "hypothesis": "H2",
        "role": "IV — composite negative type",
        "var_type": "continuous [0,1]",
        "description": "Share of aggressive + self-defeating humor. Rare negative humor composite.",
        "available_in_master": "true",
        "availability_note": "",
    },
    # H3 IVs
    {
        "variable_name": "aggressive_humor_usage_intensity",
        "hypothesis": "H3",
        "role": "IV — intensity (linear term)",
        "var_type": "continuous",
        "description": (
            "Aggressive humor intensity per firm-period. "
            "SPARSITY WARNING: 97.6% of firm-period observations are zero in the full humor panel. "
            "In the regression master (584 rows): ~98.5% zero."
        ),
        "available_in_master": "true",
        "availability_note": "Extreme sparsity — H3 inverted-U test has low statistical power.",
    },
    {
        "variable_name": "aggressive_humor_usage_intensity_sq",
        "hypothesis": "H3",
        "role": "IV — intensity squared (quadratic term for inverted-U)",
        "var_type": "continuous",
        "description": "Square of aggressive_humor_usage_intensity. Used for H3 inverted-U moderation.",
        "available_in_master": "true",
        "availability_note": "Same extreme sparsity as the linear term.",
    },
    # Diagnostics
    {
        "variable_name": "total_posts",
        "hypothesis": "all",
        "role": "diagnostic / scale control",
        "var_type": "integer",
        "description": "Total posts in firm-period. Use as denominator check or control for posting volume.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "ambiguity_rate",
        "hypothesis": "all",
        "role": "diagnostic",
        "var_type": "continuous [0,1]",
        "description": "Share of ambiguous classifications. High values → uncertain humor measurement.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "high_ambiguity_flag",
        "hypothesis": "all",
        "role": "diagnostic / exclusion flag",
        "var_type": "binary",
        "description": "Flag for firm-periods with high classification ambiguity. Consider excluding in robustness checks.",
        "available_in_master": "true",
        "availability_note": "",
    },
    # Controls
    {
        "variable_name": "naics_sector_code",
        "hypothesis": "all",
        "role": "control — industry FE",
        "var_type": "categorical",
        "description": "NAICS sector-level code. Use as fixed effect or cluster variable. Full NAICS code not available in dataset.",
        "available_in_master": "true",
        "availability_note": "naics_code (6-digit) not available; naics_sector_code used instead.",
    },
    {
        "variable_name": "industry_homogeneity_control",
        "hypothesis": "all",
        "role": "control — industry FE (identical to naics_sector_code)",
        "var_type": "categorical",
        "description": "Industry homogeneity control for regression. = naics_sector_code.",
        "available_in_master": "true",
        "availability_note": "",
    },
    {
        "variable_name": "alignment_type",
        "hypothesis": "all",
        "role": "alignment meta / subsetting flag",
        "var_type": "categorical",
        "description": (
            "Temporal alignment between humor period and filing event. "
            "Values: prefiling_lag_1m (recommended), prefiling_lag_3m (recommended), same_month (caution). "
            "Use as filter: retain prefiling_lag_1m or prefiling_lag_3m rows for main analysis."
        ),
        "available_in_master": "true",
        "availability_note": "",
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
        rows = list(csv.DictReader(f))
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
        v = float(str(val).strip())
        return None if v != v else v
    except (ValueError, TypeError):
        return None


def derive_alignment_type(row: dict) -> str:
    """Derive clean categorical alignment_type from boolean flags."""
    lag1m = str(row.get("prefiling_lag_1m_alignment", "")).lower() == "true"
    lag3m = str(row.get("prefiling_lag_3m_alignment", "")).lower() == "true"
    same  = str(row.get("same_month_alignment", "")).lower() == "true"
    if lag1m:
        return "prefiling_lag_1m"
    elif lag3m:
        return "prefiling_lag_3m"
    elif same:
        return "same_month"
    else:
        return "unaligned"


def safe_log1p(val: str) -> str:
    """Return log(1 + count) as string, or empty string on error."""
    v = safe_float(val)
    if v is None:
        return ""
    return str(round(math.log1p(max(0.0, v)), 6))


# ---------------------------------------------------------------------------
# Build regression master
# ---------------------------------------------------------------------------

def build_regression_master(
    linkage_rows: list[dict],
    humor_idx: dict[tuple, dict],
) -> list[dict]:
    master = []
    for lr in linkage_rows:
        company = lr.get("company_name", "")
        period  = lr.get("period", "")
        hrow    = humor_idx.get((company, period), {})

        # Derive alignment_type
        alignment_type = derive_alignment_type(lr)

        # Compute log_humor_count (prefer from humor_vars; fallback: compute from humor_count)
        log_hc = hrow.get("log_humor_count", "")
        if not log_hc:
            log_hc = safe_log1p(lr.get("humor_count", ""))

        row = {
            # Identifiers
            "company_name":           company,
            "ticker":                 lr.get("ticker", ""),
            "cik":                    lr.get("cik", ""),
            "period":                 period,
            "filing_date":            lr.get("filing_date", ""),
            "target_report_year":     lr.get("target_report_year", ""),
            # Alignment
            "alignment_type":         alignment_type,
            "recommended_main_alignment": lr.get("recommended_main_alignment", ""),
            "same_month_alignment":   lr.get("same_month_alignment", ""),
            "prefiling_lag_1m_alignment": lr.get("prefiling_lag_1m_alignment", ""),
            "prefiling_lag_3m_alignment": lr.get("prefiling_lag_3m_alignment", ""),
            # DVs
            "CAR_m1_p1":              lr.get("CAR_m1_p1", ""),
            "CAR_m3_p3":              lr.get("CAR_m3_p3", ""),
            "CAR_m5_p5":              lr.get("CAR_m5_p5", ""),
            "join_ready_for_CAR_m1_p1": lr.get("join_ready_for_CAR_m1_p1", "false"),
            "join_ready_for_CAR_m3_p3": lr.get("join_ready_for_CAR_m3_p3", "false"),
            "join_ready_for_CAR_m5_p5": lr.get("join_ready_for_CAR_m5_p5", "false"),
            # H1 IVs
            "humor_share":            lr.get("humor_share", ""),
            "humor_count":            lr.get("humor_count", ""),
            "log_humor_count":        log_hc,
            "humor_presence_any":     lr.get("humor_presence_any", ""),
            "humor_share_ambiguity_as_zero":    lr.get("humor_share_ambiguity_as_zero", ""),
            "humor_share_ambiguity_excluded":   lr.get("humor_share_ambiguity_excluded", ""),
            "humor_share_ambiguity_as_missing": lr.get("humor_share_ambiguity_as_missing", ""),
            # H2 IVs (type shares — affiliative/self_enhancing/self_defeating from humor_vars)
            "aggressive_share":       lr.get("aggressive_share", ""),
            "affiliative_share":      hrow.get("affiliative_share", lr.get("affiliative_share", "")),
            "self_enhancing_share":   hrow.get("self_enhancing_share", lr.get("self_enhancing_share", "")),
            "self_defeating_share":   hrow.get("self_defeating_share", lr.get("self_defeating_share", "")),
            "rare_negative_humor_share": lr.get("rare_negative_humor_share", ""),
            # H3 IVs
            "aggressive_humor_usage_intensity":    lr.get("aggressive_humor_usage_intensity", ""),
            "aggressive_humor_usage_intensity_sq": lr.get("aggressive_humor_usage_intensity_sq", ""),
            # Diagnostics
            "total_posts":            lr.get("total_posts", ""),
            "ambiguity_rate":         lr.get("ambiguity_rate", ""),
            "high_ambiguity_flag":    lr.get("high_ambiguity_flag", ""),
            "source_x_handle_count":  lr.get("source_x_handle_count", ""),
            # Industry controls
            "naics_sector_code":      lr.get("naics_sector_code", ""),
            "naics_sector_name":      lr.get("naics_sector_name", ""),
            "industry_homogeneity_control": lr.get("industry_homogeneity_control", lr.get("naics_sector_code", "")),
        }
        master.append(row)
    return master


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(
    linkage_rows: list[dict],
    master_rows: list[dict],
    humor_man: dict,
    car_man: dict,
) -> dict:
    n = len(master_rows)

    def flag_count(field: str, val: str = "true") -> int:
        return sum(1 for r in master_rows if str(r.get(field, "")).lower() == val.lower())

    m1p1_ready = flag_count("join_ready_for_CAR_m1_p1")
    m3p3_ready = flag_count("join_ready_for_CAR_m3_p3")
    m5p5_ready = flag_count("join_ready_for_CAR_m5_p5")

    same_month_rows  = sum(1 for r in master_rows if r.get("alignment_type") == "same_month")
    lag1m_rows       = sum(1 for r in master_rows if r.get("alignment_type") == "prefiling_lag_1m")
    lag3m_rows       = sum(1 for r in master_rows if r.get("alignment_type") == "prefiling_lag_3m")
    rec_main_rows    = lag1m_rows + lag3m_rows

    # Duplicate audit
    keys = [(r["company_name"], r["period"], r["filing_date"]) for r in master_rows]
    dup_count = len(keys) - len(set(keys))

    # H3 sparsity in master
    h3_nonzero = sum(
        1 for r in master_rows
        if safe_float(r.get("aggressive_humor_usage_intensity", "")) not in (None, 0.0)
        and safe_float(r.get("aggressive_humor_usage_intensity", "")) != 0
    )
    h3_zero_share = round(1 - h3_nonzero / n, 6) if n > 0 else 1.0

    # From upstream manifests
    h3_global = humor_man.get("h3_sparsity_diagnostics", {})

    # Companies in master
    companies = {r["company_name"] for r in master_rows if r["company_name"]}
    tickers   = {r["ticker"]       for r in master_rows if r["ticker"]}

    return {
        "created_at":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dv_hierarchy_note": (
            "Tobin's Q is the primary Brand Equity DV but is DEFERRED (financial panel absent). "
            "CAR_m1_p1 is the currently executable secondary DV (short-window market reaction proxy). "
            "CAR is NOT Tobin's Q. CAR is NOT direct Brand Equity."
        ),
        "source_manifests": {
            "humor_hypothesis_variables": str(DEFAULT_HUMOR_MAN),
            "car_symmetric_event_window": str(DEFAULT_CAR_MAN),
        },
        "input_rows":           len(linkage_rows),
        "output_rows":          n,
        "unique_companies":     len(companies),
        "unique_tickers":       len(tickers),
        "unique_key_columns":   ["company_name", "period", "filing_date"],
        "duplicate_rows":       dup_count,
        # CAR readiness
        "CAR_m1_p1_ready_rows": m1p1_ready,
        "CAR_m3_p3_ready_rows": m3p3_ready,
        "CAR_m5_p5_ready_rows": m5p5_ready,
        # Alignment
        "same_month_rows":                same_month_rows,
        "prefiling_lag_1m_rows":          lag1m_rows,
        "prefiling_lag_3m_rows":          lag3m_rows,
        "recommended_main_alignment_rows": rec_main_rows,
        # H3 sparsity in regression master
        "h3_sparsity_in_regression_master": {
            "total_rows":              n,
            "nonzero_aggressive_intensity_rows": h3_nonzero,
            "aggressive_intensity_zero_share":   h3_zero_share,
            "sparsity_warning": (
                f"H3 aggressive intensity is zero in {h3_zero_share:.1%} of regression master rows "
                f"({h3_nonzero} nonzero out of {n}). "
                "Inverted-U test (H3) has severely limited statistical power."
            ),
        },
        "h3_sparsity_full_humor_panel": h3_global,
        # Constraint flags
        "tobins_q_deferred":           True,
        "regression_run":              False,
        "causal_claim_made":           False,
        "car_used_as_tobins_q":        False,
        "car_used_as_direct_brand_equity": False,
        "CAR_m3_p3_computed":          False,
        "CAR_m5_p5_computed":          False,
        "daily_abnormal_return_required_for_symmetric_long_windows": True,
        "raw_data_modified":           False,
        "humor_outputs_modified":      False,
        "korea_uni_source_repo_modified": False,
        "external_api_called":         False,
        # Next steps
        "pending_for_full_regression_readiness": [
            "Gemini daily AR panel audit: if event_window_daily_abnormal_returns.csv "
            "exists in korea_uni, copy to data/external/korea_uni/ and re-run "
            "build_car_symmetric_event_window_panel.py → re-run this script.",
            "Tobin's Q: obtain total_assets, total_liabilities, market_cap from "
            "SEC EDGAR XBRL or Compustat → run build_tobins_q_brand_equity_panel.py "
            "--financial-panel <path>.",
            "H3 power: note that 9/584 nonzero aggressive intensity rows is extremely sparse. "
            "Interpret H3 results with caution or consider descriptive H3 only.",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build H1-H3 × CAR regression-ready master dataset."
    )
    parser.add_argument("--linkage",       type=Path, default=DEFAULT_LINKAGE)
    parser.add_argument("--car-manifest",  type=Path, default=DEFAULT_CAR_MAN)
    parser.add_argument("--humor-vars",    type=Path, default=DEFAULT_HUMOR_VARS)
    parser.add_argument("--humor-manifest", type=Path, default=DEFAULT_HUMOR_MAN)
    parser.add_argument("--out-master",    type=Path, default=DEFAULT_OUT_MASTER)
    parser.add_argument("--out-dict",      type=Path, default=DEFAULT_OUT_DICT)
    parser.add_argument("--out-manifest",  type=Path, default=DEFAULT_OUT_MAN)
    args = parser.parse_args()

    # ---- Load and validate humor manifest ----
    print(f"\nValidating humor manifest: {args.humor_manifest}")
    humor_man = json.loads(args.humor_manifest.read_text(encoding="utf-8"))
    dup_count = humor_man.get("company_period_duplicate_count", -1)
    ht_ready  = humor_man.get("constraints", {}).get(
        "hypothesis_testing_ready",
        humor_man.get("hypothesis_testing_ready", False),
    )
    if dup_count != 0:
        print(f"ERROR: humor company_period_duplicate_count={dup_count} (expected 0)", file=sys.stderr)
        sys.exit(1)
    if not ht_ready:
        print("ERROR: humor hypothesis_testing_ready is not True", file=sys.stderr)
        sys.exit(1)
    print(f"  OK: hypothesis_testing_ready={ht_ready}, duplicate_count={dup_count}")

    # ---- Load CAR manifest ----
    print(f"\nLoading CAR manifest: {args.car_manifest}")
    car_man = json.loads(args.car_manifest.read_text(encoding="utf-8"))
    print(f"  car_event_rows:          {car_man.get('car_event_rows')}")
    print(f"  CAR_m1_p1_available_rows:{car_man.get('CAR_m1_p1_available_rows')}")
    print(f"  daily_ar_available:      {car_man.get('daily_abnormal_return_input_available')}")

    # ---- Load inputs ----
    print(f"\nLoading linkage panel: {args.linkage}")
    linkage_rows = load_csv(args.linkage, "humor-CAR linkage panel", required=True)

    print(f"\nLoading humor variables: {args.humor_vars}")
    humor_rows = load_csv(args.humor_vars, "humor hypothesis variables", required=True)

    # ---- Build humor index for enrichment ----
    humor_idx: dict[tuple, dict] = {}
    for hr in humor_rows:
        key = (hr.get("company_name", "").strip(), hr.get("period", "").strip())
        humor_idx[key] = hr
    print(f"  Humor index: {len(humor_idx)} unique (company, period) entries")

    # ---- Build regression master ----
    print("\nBuilding regression master dataset...")
    master_rows = build_regression_master(linkage_rows, humor_idx)

    # ---- Duplicate audit ----
    keys = [(r["company_name"], r["period"], r["filing_date"]) for r in master_rows]
    dup_count_out = len(keys) - len(set(keys))
    if dup_count_out > 0:
        print(f"WARNING: {dup_count_out} duplicate (company_name, period, filing_date) rows in master")
    else:
        print(f"  Uniqueness OK: 0 duplicates on (company_name, period, filing_date)")

    # ---- Alignment coverage ----
    lag1m = sum(1 for r in master_rows if r["alignment_type"] == "prefiling_lag_1m")
    lag3m = sum(1 for r in master_rows if r["alignment_type"] == "prefiling_lag_3m")
    same  = sum(1 for r in master_rows if r["alignment_type"] == "same_month")
    m1p1_ready = sum(1 for r in master_rows if r.get("join_ready_for_CAR_m1_p1") == "true")
    h3_nonzero = sum(
        1 for r in master_rows
        if (v := r.get("aggressive_humor_usage_intensity", "")) and v != "" and float(v) != 0
    )
    print(f"  Total rows:                    {len(master_rows)}")
    print(f"  alignment_type=prefiling_lag_1m: {lag1m}")
    print(f"  alignment_type=prefiling_lag_3m: {lag3m}")
    print(f"  alignment_type=same_month:       {same}")
    print(f"  recommended_main_alignment rows: {lag1m + lag3m}")
    print(f"  join_ready_for_CAR_m1_p1:        {m1p1_ready}")
    print(f"  H3 nonzero aggressive rows:      {h3_nonzero} (sparsity warning)")

    # ---- Verify missing columns were enriched ----
    sample = master_rows[0] if master_rows else {}
    missing_enrich = [
        c for c in ["log_humor_count", "affiliative_share", "self_enhancing_share", "self_defeating_share"]
        if not sample.get(c)
    ]
    if missing_enrich:
        print(f"  INFO: Enriched columns with empty values in first row: {missing_enrich} (may be 0.0)")

    # ---- Variable dictionary ----
    print("\nBuilding variable dictionary...")

    # ---- Manifest ----
    print("Building manifest...")
    manifest = build_manifest(linkage_rows, master_rows, humor_man, car_man)

    # ---- Write outputs ----
    n1 = write_csv(args.out_master, MASTER_FIELDS, master_rows)
    n2 = write_csv(args.out_dict,   DICT_FIELDS,   VARIABLE_DICTIONARY)
    print(f"  Master  → {args.out_master} ({n1} rows)")
    print(f"  Dict    → {args.out_dict} ({n2} rows)")

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest → {args.out_manifest}")

    print(f"\n{'='*60}")
    print("Regression Master Summary")
    print(f"  output_rows:                {manifest['output_rows']}")
    print(f"  unique_companies:           {manifest['unique_companies']}")
    print(f"  CAR_m1_p1_ready_rows:       {manifest['CAR_m1_p1_ready_rows']}")
    print(f"  CAR_m3_p3_ready_rows:       {manifest['CAR_m3_p3_ready_rows']}")
    print(f"  CAR_m5_p5_ready_rows:       {manifest['CAR_m5_p5_ready_rows']}")
    print(f"  recommended_main_alignment: {manifest['recommended_main_alignment_rows']}")
    print(f"  tobins_q_deferred:          {manifest['tobins_q_deferred']}")
    print(f"  regression_run:             {manifest['regression_run']}")
    print(f"  causal_claim_made:          {manifest['causal_claim_made']}")
    h3s = manifest["h3_sparsity_in_regression_master"]
    print(f"  H3 sparsity warning:        {h3s['sparsity_warning'][:80]}...")


if __name__ == "__main__":
    main()
