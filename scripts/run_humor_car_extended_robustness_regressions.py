#!/usr/bin/env python3
"""
run_humor_car_extended_robustness_regressions.py

Extended robustness regression: H1-H3 models × 3 DVs.

DVs:
  CAR_m1_p1  = CAR[-1,+1]  — main DV (short-window market reaction proxy)
  CAR_m3_p3  = CAR[-3,+3]  — robustness DV
  CAR_m5_p5  = CAR[-5,+5]  — robustness DV

  CAR_0_p3 / CAR_0_p5 are NOT used.
  CAR is NOT Tobin's Q. CAR is NOT direct Brand Equity.
  Tobin's Q deferred (financial panel absent).
  All results are correlational — no causal claims.

Models per DV (9 per DV × 3 DVs = 27 total):
  H1a, H1b, H2a, H2b, H3 (primary sample)
  H1a_lag1m, H1a_lag3m, H1a_samemon, H1a_compFE (robustness)

H3 is EXPLORATORY ONLY (severe sparsity in aggressive intensity).

Outputs:
  data/derived/regression/humor_car_extended_robustness_regression_results.csv
  data/derived/regression/humor_car_extended_robustness_model_diagnostics.csv
  data/audit/regression/humor_car_extended_robustness_regression_manifest.json
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

DEFAULT_MASTER   = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")
DEFAULT_MAN_IN   = Path("data/audit/regression/humor_car_regression_master_manifest.json")
DEFAULT_OUT_RES  = Path("data/derived/regression/humor_car_extended_robustness_regression_results.csv")
DEFAULT_OUT_DIAG = Path("data/derived/regression/humor_car_extended_robustness_model_diagnostics.csv")
DEFAULT_OUT_MAN  = Path("data/audit/regression/humor_car_extended_robustness_regression_manifest.json")

BASE_CONTROLS = [
    "log_humor_count",
    "ambiguity_rate",
    "high_ambiguity_flag",
    "source_x_handle_count",
]

# join_ready column for each DV
JOIN_READY = {
    "CAR_m1_p1": "join_ready_for_CAR_m1_p1",
    "CAR_m3_p3": "join_ready_for_CAR_m3_p3",
    "CAR_m5_p5": "join_ready_for_CAR_m5_p5",
}

# Model ID suffix for each DV
DV_SUFFIX = {
    "CAR_m1_p1": "_m1p1",
    "CAR_m3_p3": "_m3p3",
    "CAR_m5_p5": "_m5p5",
}

RESULTS_FIELDS = [
    "model_id", "hypothesis", "dependent_variable", "dv_window", "dv_role",
    "independent_variable", "coefficient", "std_error", "t_stat", "p_value",
    "ci_lower", "ci_upper", "n_obs", "fixed_effects", "sample_filter",
    "interpretation_scope",
]

DIAG_FIELDS = [
    "model_id", "hypothesis", "dependent_variable", "dv_window", "dv_role",
    "sample_filter", "n_obs", "n_companies", "n_periods",
    "r_squared", "adjusted_r_squared", "fixed_effects_used", "controls_used",
    "dropped_variables", "collinearity_warning",
    "h3_nonzero_aggressive_intensity_rows", "h3_zero_share", "interpretation_scope",
]

DV_WINDOW = {"CAR_m1_p1": "[-1,+1]", "CAR_m3_p3": "[-3,+3]", "CAR_m5_p5": "[-5,+5]"}
DV_ROLE   = {"CAR_m1_p1": "main_dv", "CAR_m3_p3": "robustness_dv", "CAR_m5_p5": "robustness_dv"}


# ---------------------------------------------------------------------------
# OLS runner (identical to Gate 2 script, but y_col is a parameter)
# ---------------------------------------------------------------------------

def build_fe_dummies(df, fe_specs):
    parts = []
    for col, prefix in fe_specs:
        dummies = pd.get_dummies(df[col].astype(str), drop_first=True, prefix=prefix, dtype=float)
        parts.append(dummies)
    return pd.concat(parts, axis=1) if parts else pd.DataFrame(index=df.index)


def _empty_diag(model_id, hyp, y_col, sample_filter, n_obs, scope, note=""):
    return {
        "model_id": model_id, "hypothesis": hyp,
        "dependent_variable": y_col, "dv_window": DV_WINDOW.get(y_col, ""),
        "dv_role": DV_ROLE.get(y_col, ""), "sample_filter": sample_filter,
        "n_obs": n_obs, "n_companies": "", "n_periods": "",
        "r_squared": "", "adjusted_r_squared": "",
        "fixed_effects_used": "", "controls_used": "",
        "dropped_variables": note, "collinearity_warning": note,
        "h3_nonzero_aggressive_intensity_rows": "", "h3_zero_share": "",
        "interpretation_scope": scope,
    }


def run_ols_model(df, y_col, focal_ivs, control_cols, fe_specs,
                  model_id, hypothesis, sample_filter, interpretation_scope):
    all_iv_ctrl = focal_ivs + control_cols
    available   = [c for c in all_iv_ctrl if c in df.columns]

    fe_df = build_fe_dummies(df, fe_specs)
    Xdf   = pd.concat([df[available].astype(float), fe_df], axis=1)
    Xdf   = sm.add_constant(Xdf, has_constant="add")
    ydf   = df[y_col].astype(float)

    combined = pd.concat([ydf.rename("__y__"), Xdf], axis=1).dropna()
    if len(combined) < max(10, len(Xdf.columns)):
        return [], _empty_diag(model_id, hypothesis, y_col, sample_filter,
                               len(combined), interpretation_scope,
                               note="Insufficient rows after NaN drop")

    y_clean = combined["__y__"]
    X_clean = combined.drop(columns=["__y__"])

    result  = sm.OLS(y_clean, X_clean).fit()
    dropped = [v for v in X_clean.columns if np.isnan(result.params.get(v, np.nan))]
    collin  = f"Dropped (perfect collinearity): {dropped}" if dropped else ""
    fe_lbl  = ", ".join(f"{c}_FE" for c, _ in fe_specs) if fe_specs else "none"

    h3_nonzero = int((df["aggressive_humor_usage_intensity"].astype(float) > 0).sum()) \
                 if "aggressive_humor_usage_intensity" in df.columns else 0
    h3_zero    = round(1 - h3_nonzero / len(df), 4) if len(df) > 0 else 1.0

    n_companies = df.loc[combined.index, "company_name"].nunique() \
                  if "company_name" in df.columns else "?"
    n_periods   = df.loc[combined.index, "target_report_year"].nunique() \
                  if "target_report_year" in df.columns else "?"

    diag = {
        "model_id": model_id, "hypothesis": hypothesis,
        "dependent_variable": y_col, "dv_window": DV_WINDOW.get(y_col, ""),
        "dv_role": DV_ROLE.get(y_col, ""), "sample_filter": sample_filter,
        "n_obs": int(result.nobs), "n_companies": n_companies, "n_periods": n_periods,
        "r_squared": round(result.rsquared, 6),
        "adjusted_r_squared": round(result.rsquared_adj, 6),
        "fixed_effects_used": fe_lbl, "controls_used": ", ".join(control_cols),
        "dropped_variables": "; ".join(dropped) if dropped else "",
        "collinearity_warning": collin,
        "h3_nonzero_aggressive_intensity_rows": h3_nonzero,
        "h3_zero_share": h3_zero,
        "interpretation_scope": interpretation_scope,
    }

    ci = result.conf_int()
    results_rows = []
    for iv in focal_ivs:
        if iv not in result.params or np.isnan(result.params[iv]):
            continue
        results_rows.append({
            "model_id": model_id, "hypothesis": hypothesis,
            "dependent_variable": y_col, "dv_window": DV_WINDOW.get(y_col, ""),
            "dv_role": DV_ROLE.get(y_col, ""), "independent_variable": iv,
            "coefficient": round(float(result.params[iv]), 8),
            "std_error":   round(float(result.bse[iv]), 8),
            "t_stat":      round(float(result.tvalues[iv]), 4),
            "p_value":     round(float(result.pvalues[iv]), 6),
            "ci_lower":    round(float(ci.loc[iv, 0]), 8),
            "ci_upper":    round(float(ci.loc[iv, 1]), 8),
            "n_obs": int(result.nobs), "fixed_effects": fe_lbl,
            "sample_filter": sample_filter,
            "interpretation_scope": interpretation_scope,
        })

    return results_rows, diag


# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def load_and_prep(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    numeric_cols = [
        "CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5",
        "humor_share", "humor_count", "log_humor_count", "humor_presence_any",
        "humor_share_ambiguity_as_zero", "humor_share_ambiguity_excluded",
        "humor_share_ambiguity_as_missing", "aggressive_share", "affiliative_share",
        "self_enhancing_share", "self_defeating_share", "rare_negative_humor_share",
        "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
        "total_posts", "ambiguity_rate", "high_ambiguity_flag",
        "source_x_handle_count", "target_report_year",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalise join_ready_for_* columns (bool or string)
    for jr_col in JOIN_READY.values():
        if jr_col in df.columns:
            col = df[jr_col]
            if col.dtype == object:
                df[jr_col] = col.str.lower().map(
                    {"true": True, "false": False, "1": True, "0": False}
                )

    return df


def primary_sample_for_dv(df, dv):
    jr = JOIN_READY[dv]
    return df[
        df["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) &
        (df[jr] == True)
    ].copy()


def subsample_for_dv(df, dv, alignment):
    jr = JOIN_READY[dv]
    return df[
        (df["alignment_type"] == alignment) &
        (df[jr] == True)
    ].copy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master",       type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--in-manifest",  type=Path, default=DEFAULT_MAN_IN)
    parser.add_argument("--out-results",  type=Path, default=DEFAULT_OUT_RES)
    parser.add_argument("--out-diag",     type=Path, default=DEFAULT_OUT_DIAG)
    parser.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MAN)
    args = parser.parse_args()

    # ── Validate input manifest ──────────────────────────────────────────────
    print(f"\nValidating input manifest: {args.in_manifest}")
    man_in = json.loads(args.in_manifest.read_text(encoding="utf-8"))
    for flag in ["car_used_as_tobins_q", "car_used_as_direct_brand_equity",
                 "raw_data_modified", "humor_outputs_modified"]:
        if man_in.get(flag):
            print(f"ERROR: upstream constraint violation: {flag}=true", file=sys.stderr)
            sys.exit(1)
    print("  OK: upstream constraints clean.")

    # ── Load data ────────────────────────────────────────────────────────────
    print(f"\nLoading regression master: {args.master}")
    df_full = load_and_prep(args.master)
    print(f"  Total rows: {len(df_full)}")

    for dv in ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"]:
        n_primary = len(primary_sample_for_dv(df_full, dv))
        jr = JOIN_READY[dv]
        n_jr = int((df_full[jr] == True).sum()) if jr in df_full.columns else 0
        print(f"  {dv}: primary_sample={n_primary}, join_ready={n_jr}")

    PERIOD_NAICS_FE   = [("target_report_year", "year"), ("naics_sector_code", "naics")]
    PERIOD_COMPANY_FE = [("target_report_year", "year"), ("company_name", "company")]

    all_results: list[dict] = []
    all_diags:   list[dict] = []

    counters = {
        "attempted": 0, "completed": 0, "failed": 0,
        "H1": 0, "H2": 0, "H3": 0,
    }

    def run(df, y_col, ivs, controls, fe, base_id, hyp, sample_filter, scope):
        suffix = DV_SUFFIX[y_col]
        model_id = base_id + suffix
        counters["attempted"] += 1
        print(f"  {model_id} (n={len(df)}, DV={y_col})...", end=" ", flush=True)
        r, d = run_ols_model(df, y_col, ivs, controls, fe,
                             model_id, hyp, sample_filter, scope)
        all_results.extend(r)
        all_diags.append(d)
        if d["r_squared"] == "":
            counters["failed"] += 1
            print(f"FAILED: {d['dropped_variables']}")
        else:
            counters["completed"] += 1
            counters[hyp[:2]] = counters.get(hyp[:2], 0) + 1
            print(f"OK  R²={d['r_squared']}  n_focal={len(r)}")

    print("\n=== Running H1-H3 × 3 DVs ===")

    for dv in ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"]:
        df_pri    = primary_sample_for_dv(df_full, dv)
        df_lag1m  = subsample_for_dv(df_full, dv, "prefiling_lag_1m")
        df_lag3m  = subsample_for_dv(df_full, dv, "prefiling_lag_3m")
        df_samon  = subsample_for_dv(df_full, dv, "same_month")

        h3_nz = int((df_pri["aggressive_humor_usage_intensity"] > 0).sum()) \
                if "aggressive_humor_usage_intensity" in df_pri.columns else 0
        h3_zs = round(1 - h3_nz / len(df_pri), 4) if len(df_pri) > 0 else 1.0

        scope_std   = "correlational — no causal interpretation warranted"
        scope_expl  = (f"exploratory correlational — H3 has only {h3_nz} nonzero "
                       f"aggressive intensity rows ({h3_zs:.1%} zero); "
                       "interpret with extreme caution")
        scope_samon = "correlational — caution: same_month alignment carries simultaneity risk"

        pri_filt = f"primary (lag1m+lag3m, join_ready_for_{dv})"

        print(f"\n--- {dv} [{DV_WINDOW[dv]}, {DV_ROLE[dv]}]  n_primary={len(df_pri)} ---")

        run(df_pri, dv, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H1a", "H1", pri_filt, scope_std)

        run(df_pri, dv, ["humor_presence_any"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H1b", "H1", pri_filt, scope_std)

        run(df_pri, dv,
            ["aggressive_share", "self_enhancing_share", "self_defeating_share"],
            BASE_CONTROLS, PERIOD_NAICS_FE,
            "H2a", "H2",
            pri_filt + " [affiliative_share=ref]", scope_std)

        run(df_pri, dv, ["rare_negative_humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H2b", "H2", pri_filt, scope_std)

        run(df_pri, dv,
            ["aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq"],
            BASE_CONTROLS, PERIOD_NAICS_FE,
            "H3", "H3",
            pri_filt + " [EXPLORATORY — extreme sparsity]", scope_expl)

        run(df_lag1m, dv, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H1a_lag1m", "H1", f"prefiling_lag_1m only", scope_std)

        run(df_lag3m, dv, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H1a_lag3m", "H1", f"prefiling_lag_3m only", scope_std)

        run(df_samon, dv, ["humor_share"], BASE_CONTROLS, PERIOD_NAICS_FE,
            "H1a_samemon", "H1", "same_month only (simultaneity caution)", scope_samon)

        run(df_pri, dv, ["humor_share"], BASE_CONTROLS, PERIOD_COMPANY_FE,
            "H1a_compFE", "H1",
            pri_filt + " [company FE robustness]", scope_std)

    # ── Write CSVs ───────────────────────────────────────────────────────────
    def write_csv(path, fieldnames, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        return len(rows)

    n_res  = write_csv(args.out_results, RESULTS_FIELDS, all_results)
    n_diag = write_csv(args.out_diag,   DIAG_FIELDS,    all_diags)
    print(f"\n  Results  → {args.out_results}  ({n_res} rows)")
    print(f"  Diag     → {args.out_diag}  ({n_diag} rows)")

    # ── Manifest ─────────────────────────────────────────────────────────────
    # Per-DV summary for manifest
    dv_summary = {}
    for dv in ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"]:
        suf = DV_SUFFIX[dv]
        dv_rows = [r for r in all_results if r["dependent_variable"] == dv]
        dv_diags = [d for d in all_diags if d["dependent_variable"] == dv
                    and d["model_id"].endswith(("H1a" + suf, "H1b" + suf,
                                               "H2a" + suf, "H2b" + suf,
                                               "H3" + suf))]
        # Find H1a focal coef for summary
        h1a = next((r for r in dv_rows if r["model_id"] == "H1a" + suf
                    and r["independent_variable"] == "humor_share"), None)
        dv_summary[dv] = {
            "window": DV_WINDOW[dv],
            "role": DV_ROLE[dv],
            "n_primary": len(primary_sample_for_dv(df_full, dv)),
            "H1a_humor_share_beta":  h1a["coefficient"] if h1a else None,
            "H1a_humor_share_se":    h1a["std_error"]   if h1a else None,
            "H1a_humor_share_p":     h1a["p_value"]     if h1a else None,
        }

    h3_nz_primary = int(
        (primary_sample_for_dv(df_full, "CAR_m1_p1")["aggressive_humor_usage_intensity"] > 0).sum()
    )
    h3_zs_primary = round(1 - h3_nz_primary /
                          len(primary_sample_for_dv(df_full, "CAR_m1_p1")), 4)

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "scripts/run_humor_car_extended_robustness_regressions.py",
        "dv_note": (
            "CAR_m1_p1 is the main DV (short-window market reaction proxy). "
            "CAR_m3_p3 and CAR_m5_p5 are robustness DVs computed from daily return panel "
            "using per-event market model alpha/beta. "
            "CAR is NOT Tobin's Q. CAR is NOT direct Brand Equity. "
            "All results are correlational — no causal claims."
        ),
        "dvs_used": ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"],
        "dv_summary": dv_summary,
        "input_rows": len(df_full),
        "models_attempted":  counters["attempted"],
        "models_completed":  counters["completed"],
        "models_failed":     counters["failed"],
        "h3_nonzero_aggressive_intensity_rows": h3_nz_primary,
        "h3_zero_share": h3_zs_primary,
        "h3_interpretation_note": (
            f"H3 has only {h3_nz_primary} nonzero aggressive intensity rows "
            f"({h3_zs_primary:.1%} zero) in primary sample. "
            "Report as exploratory evidence only. No confirmatory inference."
        ),
        "H3_exploratory_only": True,
        # Constraint flags
        "regression_run":                 True,
        "causal_claim_made":              False,
        "car_used_as_tobins_q":           False,
        "car_used_as_direct_brand_equity": False,
        "CAR_m1_p1_used":                 True,
        "CAR_m3_p3_used":                 True,   # robustness DV
        "CAR_m5_p5_used":                 True,   # robustness DV
        "CAR_0_p3_used_as_symmetric_window": False,
        "CAR_0_p5_used_as_symmetric_window": False,
        "CAR_0_p3_used":                  False,
        "CAR_0_p5_used":                  False,
        "tobins_q_deferred":              True,
        "raw_data_modified":              False,
        "humor_outputs_modified":         False,
        "korea_uni_source_repo_modified": False,
        "daily_return_panel_used_for_car_m3_m5": True,
        "daily_abnormal_return_panel_used": False,
        "abnormal_return_recomputed_from_market_model": True,
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest → {args.out_manifest}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("EXTENDED ROBUSTNESS REGRESSION SUMMARY")
    print(f"{'='*65}")
    print(f"  models_attempted:  {counters['attempted']}")
    print(f"  models_completed:  {counters['completed']}")
    print(f"  models_failed:     {counters['failed']}")
    print(f"  H3 sparsity:       {h3_nz_primary} nonzero / "
          f"{len(primary_sample_for_dv(df_full, 'CAR_m1_p1'))} rows "
          f"({h3_zs_primary:.1%} zero)  [EXPLORATORY ONLY]")
    print()

    for dv in ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"]:
        suf = DV_SUFFIX[dv]
        print(f"  {dv} [{DV_WINDOW[dv]}, {DV_ROLE[dv]}]")
        dv_rows = [r for r in all_results if r["dependent_variable"] == dv]
        for r in dv_rows:
            p    = r["p_value"]
            sig  = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "(NS)"
            expl = " [EXPLORATORY]" if "H3" in r["model_id"] else ""
            print(f"    {r['model_id']:18s} {r['independent_variable']:45s} "
                  f"β={r['coefficient']:+.5f}  se={r['std_error']:.5f}  "
                  f"p={p:.4f} {sig}{expl}")
        print()


if __name__ == "__main__":
    main()
