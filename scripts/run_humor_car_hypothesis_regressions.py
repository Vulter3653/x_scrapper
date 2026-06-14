#!/usr/bin/env python3
"""Run H1-H3 hypothesis regressions: humor IV × CAR_m1_p1 DV.

DV used: CAR_m1_p1 (CAR[-1,+1]) — short-window capital market response proxy.
         NOT Tobin's Q. NOT direct Brand Equity.
Tobin's Q: deferred (primary Brand Equity DV; financial panel absent).
CAR_m3_p3, CAR_m5_p5: missing (daily abnormal return panel not yet available).

CONSTRAINTS:
  - CAR is NOT used as or equated to Tobin's Q.
  - CAR is NOT labelled as direct Brand Equity.
  - CAR_m3_p3 / CAR_m5_p5 are NOT used (all missing).
  - CAR_0_p3 / CAR_0_p5 are NOT used as symmetric windows.
  - H3 is reported as exploratory only (5 nonzero rows in primary sample).
  - No causal claims are made.
  - Raw data, humor outputs, korea_uni source repo are not modified.

Models:
  H1a: CAR_m1_p1 ~ humor_share + controls + period_FE + naics_FE
  H1b: CAR_m1_p1 ~ humor_presence_any + controls + period_FE + naics_FE
  H2a: CAR_m1_p1 ~ aggressive_share + self_enhancing_share + self_defeating_share
                   + controls + period_FE + naics_FE  [affiliative_share = ref]
  H2b: CAR_m1_p1 ~ rare_negative_humor_share + controls + period_FE + naics_FE
  H3:  CAR_m1_p1 ~ aggressive_humor_usage_intensity + aggressive_humor_usage_intensity_sq
                   + controls + period_FE + naics_FE  [exploratory]
Robustness:
  H1a_lag1m:   H1a on alignment_type=prefiling_lag_1m subsample
  H1a_lag3m:   H1a on alignment_type=prefiling_lag_3m subsample
  H1a_samemon: H1a on alignment_type=same_month subsample
  H1a_compFE:  H1a with company FE replacing naics FE (may absorb sector variation)

Samples:
  Primary:    alignment_type in ('prefiling_lag_1m', 'prefiling_lag_3m')
              AND join_ready_for_CAR_m1_p1 == True
  Robustness: by alignment_type; also same_month as sensitivity

Inputs:
  data/derived/regression/humor_car_hypothesis_regression_master.csv
  data/audit/regression/humor_car_regression_master_manifest.json

Outputs:
  data/derived/regression/humor_car_hypothesis_regression_results.csv
  data/derived/regression/humor_car_hypothesis_model_diagnostics.csv
  data/audit/regression/humor_car_hypothesis_regression_manifest.json
"""

import argparse
import csv
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MASTER   = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")
DEFAULT_MAN_IN   = Path("data/audit/regression/humor_car_regression_master_manifest.json")
DEFAULT_OUT_RES  = Path("data/derived/regression/humor_car_hypothesis_regression_results.csv")
DEFAULT_OUT_DIAG = Path("data/derived/regression/humor_car_hypothesis_model_diagnostics.csv")
DEFAULT_OUT_MAN  = Path("data/audit/regression/humor_car_hypothesis_regression_manifest.json")

# Controls always included (except when company FE already includes log_humor_count analog)
BASE_CONTROLS = [
    "log_humor_count",
    "ambiguity_rate",
    "high_ambiguity_flag",
    "source_x_handle_count",
]

RESULTS_FIELDS = [
    "model_id", "hypothesis", "dependent_variable", "independent_variable",
    "coefficient", "std_error", "t_stat", "p_value", "ci_lower", "ci_upper",
    "n_obs", "fixed_effects", "sample_filter", "interpretation_scope",
]

DIAG_FIELDS = [
    "model_id", "hypothesis", "dependent_variable", "sample_filter",
    "n_obs", "n_companies", "n_periods", "r_squared", "adjusted_r_squared",
    "fixed_effects_used", "controls_used", "dropped_variables",
    "collinearity_warning", "h3_nonzero_aggressive_intensity_rows",
    "h3_zero_share", "interpretation_scope",
]


# ---------------------------------------------------------------------------
# Model runner
# ---------------------------------------------------------------------------

def build_fe_dummies(df: pd.DataFrame, fe_specs: list[tuple[str, str]]) -> pd.DataFrame:
    """
    fe_specs: list of (column_name, prefix) for each FE dimension.
    Returns DataFrame of dummies with one reference category dropped per dimension.
    """
    parts = []
    for col, prefix in fe_specs:
        dummies = pd.get_dummies(
            df[col].astype(str), drop_first=True, prefix=prefix, dtype=float
        )
        parts.append(dummies)
    return pd.concat(parts, axis=1) if parts else pd.DataFrame(index=df.index)


def run_ols_model(
    df: pd.DataFrame,
    y_col: str,
    focal_ivs: list[str],
    control_cols: list[str],
    fe_specs: list[tuple[str, str]],
    model_id: str,
    hypothesis: str,
    sample_filter: str,
    interpretation_scope: str,
) -> tuple[list[dict], dict]:
    """
    Run OLS and return (results_rows, diagnostics_row).
    results_rows: one row per focal IV coefficient.
    diagnostics_row: one row per model.
    """
    # Build design matrix
    all_iv_ctrl = focal_ivs + control_cols
    available = [c for c in all_iv_ctrl if c in df.columns]
    missing_cols = [c for c in all_iv_ctrl if c not in df.columns]

    fe_df = build_fe_dummies(df, fe_specs)
    fe_col_names = list(fe_df.columns)

    Xdf = pd.concat([df[available].astype(float), fe_df], axis=1)
    Xdf = sm.add_constant(Xdf, has_constant="add")
    ydf = df[y_col].astype(float)

    # Drop rows with any NaN
    combined = pd.concat([ydf.rename("__y__"), Xdf], axis=1).dropna()
    if len(combined) < max(10, len(Xdf.columns)):
        diag = _empty_diag(model_id, hypothesis, y_col, sample_filter,
                           len(combined), interpretation_scope,
                           note="Insufficient rows after NaN drop")
        return [], diag

    y_clean = combined["__y__"]
    X_clean = combined.drop(columns=["__y__"])

    # Fit
    model  = sm.OLS(y_clean, X_clean)
    result = model.fit()

    # Identify dropped variables (NaN params)
    dropped = [v for v in X_clean.columns if np.isnan(result.params.get(v, np.nan))]
    collin_warn = ""
    if dropped:
        collin_warn = f"Dropped due to perfect collinearity: {dropped}"

    # FE labels for reporting
    fe_label = ", ".join(
        [f"{col}_FE" for col, _ in fe_specs]
    ) if fe_specs else "none"

    controls_label = ", ".join(control_cols)

    # Diagnostics
    n_obs = int(result.nobs)
    n_companies = df.loc[combined.index, "company_name"].nunique() if "company_name" in df.columns else "?"
    n_periods   = df.loc[combined.index, "target_report_year"].nunique() if "target_report_year" in df.columns else "?"
    h3_nonzero  = int((df["aggressive_humor_usage_intensity"].astype(float) > 0).sum()) \
                  if "aggressive_humor_usage_intensity" in df.columns else 0
    h3_zero_sh  = round(1 - h3_nonzero / len(df), 4) if len(df) > 0 else 1.0

    diag = {
        "model_id":                     model_id,
        "hypothesis":                   hypothesis,
        "dependent_variable":           y_col,
        "sample_filter":                sample_filter,
        "n_obs":                        n_obs,
        "n_companies":                  n_companies,
        "n_periods":                    n_periods,
        "r_squared":                    round(result.rsquared, 6),
        "adjusted_r_squared":           round(result.rsquared_adj, 6),
        "fixed_effects_used":           fe_label,
        "controls_used":                controls_label,
        "dropped_variables":            "; ".join(dropped) if dropped else "",
        "collinearity_warning":         collin_warn,
        "h3_nonzero_aggressive_intensity_rows": h3_nonzero,
        "h3_zero_share":                h3_zero_sh,
        "interpretation_scope":         interpretation_scope,
    }

    # Results: one row per focal IV
    results_rows = []
    ci = result.conf_int()
    for iv in focal_ivs:
        if iv not in result.params:
            continue
        coef = result.params[iv]
        if np.isnan(coef):
            continue
        results_rows.append({
            "model_id":            model_id,
            "hypothesis":          hypothesis,
            "dependent_variable":  y_col,
            "independent_variable": iv,
            "coefficient":         round(float(coef), 8),
            "std_error":           round(float(result.bse[iv]), 8),
            "t_stat":              round(float(result.tvalues[iv]), 4),
            "p_value":             round(float(result.pvalues[iv]), 6),
            "ci_lower":            round(float(ci.loc[iv, 0]), 8),
            "ci_upper":            round(float(ci.loc[iv, 1]), 8),
            "n_obs":               n_obs,
            "fixed_effects":       fe_label,
            "sample_filter":       sample_filter,
            "interpretation_scope": interpretation_scope,
        })

    return results_rows, diag


def _empty_diag(model_id, hypothesis, y_col, sample_filter, n_obs,
                interpretation_scope, note=""):
    return {
        "model_id":            model_id,
        "hypothesis":          hypothesis,
        "dependent_variable":  y_col,
        "sample_filter":       sample_filter,
        "n_obs":               n_obs,
        "n_companies":         "",
        "n_periods":           "",
        "r_squared":           "",
        "adjusted_r_squared":  "",
        "fixed_effects_used":  "",
        "controls_used":       "",
        "dropped_variables":   note,
        "collinearity_warning": note,
        "h3_nonzero_aggressive_intensity_rows": "",
        "h3_zero_share":       "",
        "interpretation_scope": interpretation_scope,
    }


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def load_and_prep(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")

    # Numeric coercion
    numeric_cols = [
        "CAR_m1_p1", "humor_share", "humor_count", "log_humor_count",
        "humor_presence_any", "humor_share_ambiguity_as_zero",
        "humor_share_ambiguity_excluded", "humor_share_ambiguity_as_missing",
        "aggressive_share", "affiliative_share", "self_enhancing_share",
        "self_defeating_share", "rare_negative_humor_share",
        "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
        "total_posts", "ambiguity_rate", "high_ambiguity_flag",
        "source_x_handle_count", "target_report_year",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # join_ready: handle both bool and string
    if "join_ready_for_CAR_m1_p1" in df.columns:
        col = df["join_ready_for_CAR_m1_p1"]
        if col.dtype == object:
            df["join_ready_for_CAR_m1_p1"] = col.str.lower().map(
                {"true": True, "false": False, "1": True, "0": False}
            )

    return df


def primary_sample(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        df["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) &
        (df["join_ready_for_CAR_m1_p1"] == True)
    ].copy()


def subsample(df: pd.DataFrame, alignment: str) -> pd.DataFrame:
    return df[
        (df["alignment_type"] == alignment) &
        (df["join_ready_for_CAR_m1_p1"] == True)
    ].copy()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run H1-H3 humor-CAR hypothesis regressions."
    )
    parser.add_argument("--master",       type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--in-manifest",  type=Path, default=DEFAULT_MAN_IN)
    parser.add_argument("--out-results",  type=Path, default=DEFAULT_OUT_RES)
    parser.add_argument("--out-diag",     type=Path, default=DEFAULT_OUT_DIAG)
    parser.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MAN)
    args = parser.parse_args()

    # ---- Validate input manifest ----
    print(f"\nValidating input manifest: {args.in_manifest}")
    man_in = json.loads(args.in_manifest.read_text(encoding="utf-8"))
    if man_in.get("regression_run"):
        print("ERROR: input manifest already shows regression_run=true", file=sys.stderr)
        sys.exit(1)
    for flag in ["car_used_as_tobins_q", "car_used_as_direct_brand_equity",
                 "raw_data_modified", "humor_outputs_modified"]:
        if man_in.get(flag):
            print(f"ERROR: upstream constraint violation: {flag}=true", file=sys.stderr)
            sys.exit(1)
    print("  OK: upstream constraints clean.")

    # ---- Load data ----
    print(f"\nLoading regression master: {args.master}")
    df_full = load_and_prep(args.master)
    print(f"  Total rows loaded: {len(df_full)}")

    # ---- Samples ----
    df_primary = primary_sample(df_full)
    df_lag1m   = subsample(df_full, "prefiling_lag_1m")
    df_lag3m   = subsample(df_full, "prefiling_lag_3m")
    df_samemon = subsample(df_full, "same_month")

    print(f"  Primary sample:              {len(df_primary)} rows")
    print(f"  prefiling_lag_1m subsample:  {len(df_lag1m)} rows")
    print(f"  prefiling_lag_3m subsample:  {len(df_lag3m)} rows")
    print(f"  same_month subsample:        {len(df_samemon)} rows")

    h3_nonzero_primary = int(
        (df_primary["aggressive_humor_usage_intensity"] > 0).sum()
    )
    h3_zero_share_primary = round(
        1 - h3_nonzero_primary / len(df_primary), 4
    ) if len(df_primary) > 0 else 1.0
    print(f"  H3 nonzero (primary):        {h3_nonzero_primary} ({h3_zero_share_primary:.1%} zero)")

    # FE specifications
    PERIOD_NAICS_FE = [
        ("target_report_year", "year"),
        ("naics_sector_code",  "naics"),
    ]
    PERIOD_COMPANY_FE = [
        ("target_report_year", "year"),
        ("company_name",       "company"),
    ]
    NOFE = []

    interp_standard   = "correlational — no causal interpretation warranted"
    interp_exploratory = (
        f"exploratory correlational — H3 aggressive intensity has only "
        f"{h3_nonzero_primary} nonzero rows in primary sample ({h3_zero_share_primary:.1%} zero); "
        "interpret with extreme caution"
    )
    interp_samemon = (
        "correlational — caution: same_month alignment carries simultaneity risk"
    )

    all_results: list[dict] = []
    all_diags:   list[dict] = []
    models_attempted  = 0
    models_completed  = 0
    models_failed     = 0
    h1_completed = h2_completed = h3_completed = 0

    def run(df, ivs, controls, fe, model_id, hyp, sample_filter, scope):
        nonlocal models_attempted, models_completed, models_failed
        nonlocal h1_completed, h2_completed, h3_completed
        models_attempted += 1
        print(f"  Running {model_id} (n={len(df)})...")
        r, d = run_ols_model(df, "CAR_m1_p1", ivs, controls, fe,
                             model_id, hyp, sample_filter, scope)
        all_results.extend(r)
        all_diags.append(d)
        if d["r_squared"] == "":
            models_failed += 1
            print(f"    FAILED: {d['dropped_variables']}")
        else:
            models_completed += 1
            n_coef = len(r)
            r2     = d["r_squared"]
            drops  = d["dropped_variables"] or "none"
            print(f"    OK: n={d['n_obs']}, R²={r2}, focal coefs={n_coef}, dropped={drops}")
            if "H1" in hyp: h1_completed += 1
            if "H2" in hyp: h2_completed += 1
            if "H3" in hyp: h3_completed += 1

    print("\n=== Running models ===")

    # H1a — baseline: humor_share
    run(df_primary, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H1a", "H1", "primary (lag1m+lag3m, join_ready)", interp_standard)

    # H1b — alternative: humor_presence_any
    run(df_primary, ["humor_presence_any"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H1b", "H1", "primary (lag1m+lag3m, join_ready)", interp_standard)

    # H2a — type-share model (affiliative_share as reference, excluded)
    run(df_primary,
        ["aggressive_share", "self_enhancing_share", "self_defeating_share"],
        BASE_CONTROLS, PERIOD_NAICS_FE,
        "H2a", "H2",
        "primary (lag1m+lag3m, join_ready) [affiliative_share=ref, excluded]",
        interp_standard)

    # H2b — rare-negative composite
    run(df_primary, ["rare_negative_humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H2b", "H2", "primary (lag1m+lag3m, join_ready)", interp_standard)

    # H3 — quadratic intensity (exploratory)
    run(df_primary,
        ["aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq"],
        BASE_CONTROLS, PERIOD_NAICS_FE,
        "H3", "H3",
        "primary (lag1m+lag3m, join_ready) [EXPLORATORY — extreme sparsity]",
        interp_exploratory)

    # Robustness: H1a by alignment subsample
    run(df_lag1m, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H1a_lag1m", "H1", "prefiling_lag_1m only", interp_standard)

    run(df_lag3m, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H1a_lag3m", "H1", "prefiling_lag_3m only", interp_standard)

    run(df_samemon, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
        "H1a_samemon", "H1", "same_month only (simultaneity caution)", interp_samemon)

    # Robustness: H1a with company FE (period_FE + company_FE)
    run(df_primary, ["humor_share"], BASE_CONTROLS, PERIOD_COMPANY_FE,
        "H1a_compFE", "H1",
        "primary (lag1m+lag3m) with company FE [robustness]",
        interp_standard)

    # ---- Write outputs ----
    n_res  = write_csv(args.out_results, RESULTS_FIELDS, all_results)
    n_diag = write_csv(args.out_diag,   DIAG_FIELDS,    all_diags)
    print(f"\n  Results   → {args.out_results} ({n_res} rows)")
    print(f"  Diag      → {args.out_diag} ({n_diag} rows)")

    # ---- Manifest ----
    manifest = {
        "created_at":       datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dv_note": (
            "CAR_m1_p1 is a short-window capital market response proxy (secondary DV). "
            "Tobin's Q is deferred. CAR is NOT Tobin's Q. CAR is NOT direct Brand Equity. "
            "All regression results are correlational — no causal claims."
        ),
        "input_rows":                    len(df_full),
        "regression_sample_rows":        len(df_primary),
        "recommended_main_alignment_rows": len(df_primary),
        "CAR_m1_p1_ready_rows":          int((df_full["join_ready_for_CAR_m1_p1"] == True).sum()),
        "models_attempted":              models_attempted,
        "models_completed":              models_completed,
        "models_failed":                 models_failed,
        "h1_models_completed":           h1_completed,
        "h2_models_completed":           h2_completed,
        "h3_models_completed":           h3_completed,
        "h3_nonzero_aggressive_intensity_rows": h3_nonzero_primary,
        "h3_zero_share":                 h3_zero_share_primary,
        "h3_interpretation_note": (
            f"H3 has only {h3_nonzero_primary} nonzero aggressive intensity rows "
            f"({h3_zero_share_primary:.1%} zero) in primary sample. "
            "Report as exploratory evidence only."
        ),
        # Constraint flags — all must remain false
        "regression_run":                True,   # this script ran regressions
        "causal_claim_made":             False,
        "car_used_as_tobins_q":          False,
        "car_used_as_direct_brand_equity": False,
        "CAR_m3_p3_used":                False,
        "CAR_m5_p5_used":                False,
        "CAR_0_p3_used_as_symmetric_window": False,
        "CAR_0_p5_used_as_symmetric_window": False,
        "tobins_q_deferred":             True,
        "raw_data_modified":             False,
        "humor_outputs_modified":        False,
        "korea_uni_source_repo_modified": False,
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest  → {args.out_manifest}")

    # ---- Summary ----
    print(f"\n{'='*60}")
    print("Regression Run Summary")
    print(f"  models_attempted:   {models_attempted}")
    print(f"  models_completed:   {models_completed}")
    print(f"  models_failed:      {models_failed}")
    print(f"  h1_completed:       {h1_completed}")
    print(f"  h2_completed:       {h2_completed}")
    print(f"  h3_completed:       {h3_completed}")
    print(f"  H3 sparsity:        {h3_nonzero_primary} nonzero / {len(df_primary)} rows "
          f"({h3_zero_share_primary:.1%} zero)")

    # Print focal results summary
    print("\n--- Focal IV Coefficient Summary ---")
    for r in all_results:
        p = r["p_value"]
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
        print(f"  {r['model_id']:15s} {r['independent_variable']:45s} "
              f"β={r['coefficient']:+.5f}  se={r['std_error']:.5f}  "
              f"t={r['t_stat']:+.2f}  p={p:.4f}{sig}")


if __name__ == "__main__":
    main()
