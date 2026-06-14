#!/usr/bin/env python3
"""
run_humor_iv_gate6_h1_h2_regressions.py

Gate 6A: H1/H2 회귀 실행 (H3 실행 금지)

기준: humor_iv_gate6_model_spec_manifest.json
IV 소스: humor_iv_reconstructed_candidates_gate5_1.csv

금지:
  - H3 모델 실행 금지
  - forbidden IV 사용 금지
  - CAR_0_p3 / CAR_0_p5 사용 금지
  - causal claim / Brand Equity claim / Tobin's Q 금지
  - raw data / hypothesis_variables / regression_master 수정 금지
"""

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────────
PANEL_PATH  = Path("data/derived/regression/humor_iv_reconstructed_candidates_gate5_1.csv")
SPEC_MAN    = Path("data/audit/regression/humor_iv_gate6_model_spec_manifest.json")
OUT_RESULTS = Path("data/derived/regression/humor_iv_gate6_h1_h2_regression_results.csv")
OUT_DIAGS   = Path("data/derived/regression/humor_iv_gate6_h1_h2_model_diagnostics.csv")
OUT_MAN     = Path("data/audit/regression/humor_iv_gate6_h1_h2_regression_manifest.json")
OUT_SUM     = Path("docs/humor_iv_gate6_h1_h2_regression_summary.md")

DESIGN_COMMIT = "f264e38895559fec6edc7f388e57b25be5c3c366"

# ── constants ────────────────────────────────────────────────────────────────
DVS    = ["CAR_m1_p1", "CAR_m3_p3", "CAR_m5_p5"]
JOIN_READY = {
    "CAR_m1_p1": "join_ready_for_CAR_m1_p1",
    "CAR_m3_p3": "join_ready_for_CAR_m3_p3",
    "CAR_m5_p5": "join_ready_for_CAR_m5_p5",
}
DV_WINDOW = {"CAR_m1_p1": "[-1,+1]", "CAR_m3_p3": "[-3,+3]", "CAR_m5_p5": "[-5,+5]"}

CTRL_BASE        = ["ambiguity_rate", "high_ambiguity_flag", "source_x_handle_count"]
CTRL_WITH_COUNT  = CTRL_BASE + ["log_humor_count"]

FORBIDDEN_IVS = {
    "hc_v2_aggressive_candidate_share", "hc_v2_aggressive_candidate_intensity",
    "hc_v2_aggressive_candidate_intensity_bounded", "hc_v2_aggressive_candidate_ratio_to_hard_humor",
    "hc_negative_humor_intensity", "top_k_aggressive_score", "top_k_aggressive_type_confidence",
    "aggressive_prob_sum", "aggressive_prob_mean", "aggressive_prob_max", "aggressive_prob_intensity",
    "CAR_0_p3", "CAR_0_p5",
}

# humor_prob_sum → renamed to humor_candidate_score_sum at load time
RENAME_MAP = {"humor_prob_sum": "humor_candidate_score_sum"}

RESULT_COLS = [
    "model_id", "hypothesis", "dv", "window", "focal_iv",
    "beta", "se_hc3", "t_stat", "p_value",
    "ci_lower_95", "ci_upper_95",
    "significant_p01", "significant_p05", "significant_p10",
    "n_obs", "n_companies", "n_periods",
    "r_squared", "adj_r_squared",
    "fixed_effects", "controls", "se_type", "sample_filter",
    "iv_nonzero_n", "iv_nonzero_pct", "iv_min", "iv_max", "iv_mean",
    "convergence_ok", "note",
]

DIAG_COLS = [
    "model_id", "hypothesis", "dv", "focal_iv",
    "n_obs", "n_companies", "n_periods",
    "r_squared", "adj_r_squared", "f_stat", "f_pvalue",
    "fixed_effects", "controls",
    "iv_nonzero_n", "iv_nonzero_pct",
    "focal_iv_vif_approx", "convergence_ok",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def primary_sample(df, dv):
    col = JOIN_READY[dv]
    jr = df[col].astype(str).str.lower().map({"true": True, "false": False}).fillna(False)
    mask = df["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) & jr
    return df[mask].copy()


def run_ols(df, dv, focal_iv, controls, fe_cols, model_id, hyp, note=""):
    assert focal_iv not in FORBIDDEN_IVS, f"FORBIDDEN IV: {focal_iv}"
    assert dv not in FORBIDDEN_IVS, f"FORBIDDEN DV: {dv}"

    # numeric coerce
    for c in [dv, focal_iv] + controls:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # drop rows with any NaN in key columns
    needed = [dv, focal_iv] + controls + fe_cols
    needed = [c for c in needed if c in df.columns]
    sub = df.dropna(subset=needed).copy()

    n = len(sub)
    if n < 30:
        return _failed_row(model_id, hyp, dv, focal_iv, controls, fe_cols, note,
                           f"insufficient obs n={n}"), \
               _failed_diag(model_id, hyp, dv, focal_iv, controls, fe_cols, n)

    # build formula
    fe_terms = " + ".join(f"C({c})" for c in fe_cols)
    ctrl_terms = " + ".join(controls)
    parts = [focal_iv, ctrl_terms, fe_terms]
    formula = f"{dv} ~ " + " + ".join(p for p in parts if p)

    try:
        mdl = smf.ols(formula=formula, data=sub)
        res = mdl.fit(cov_type="HC3")
    except Exception as e:
        return _failed_row(model_id, hyp, dv, focal_iv, controls, fe_cols, note, str(e)), \
               _failed_diag(model_id, hyp, dv, focal_iv, controls, fe_cols, n)

    # extract focal IV param — handle bracket notation from statsmodels
    pname = None
    for k in res.params.index:
        if k == focal_iv or k == f"[{focal_iv}]":
            pname = k
            break
    if pname is None:
        return _failed_row(model_id, hyp, dv, focal_iv, controls, fe_cols, note,
                           f"param not found in {list(res.params.index)[:5]}"), \
               _failed_diag(model_id, hyp, dv, focal_iv, controls, fe_cols, n)

    beta  = float(res.params[pname])
    se    = float(res.bse[pname])
    tval  = float(res.tvalues[pname])
    pval  = float(res.pvalues[pname])
    ci    = res.conf_int(alpha=0.05)
    ci_lo = float(ci.loc[pname, 0])
    ci_hi = float(ci.loc[pname, 1])

    iv_s   = sub[focal_iv]
    nz     = int((iv_s > 0).sum())
    nz_pct = round(100 * nz / n, 2)
    fe_lbl = "+".join(fe_cols)
    ctrl_lbl = ",".join(controls)

    rrow = {
        "model_id": model_id, "hypothesis": hyp, "dv": dv,
        "window": DV_WINDOW[dv], "focal_iv": focal_iv,
        "beta": round(beta, 6), "se_hc3": round(se, 6),
        "t_stat": round(tval, 4), "p_value": round(pval, 4),
        "ci_lower_95": round(ci_lo, 6), "ci_upper_95": round(ci_hi, 6),
        "significant_p01": int(pval < 0.01),
        "significant_p05": int(pval < 0.05),
        "significant_p10": int(pval < 0.10),
        "n_obs": n,
        "n_companies": int(sub["company_name"].nunique()),
        "n_periods": int(sub["target_report_year"].nunique()) if "target_report_year" in sub.columns else "",
        "r_squared": round(float(res.rsquared), 4),
        "adj_r_squared": round(float(res.rsquared_adj), 4),
        "fixed_effects": fe_lbl,
        "controls": ctrl_lbl,
        "se_type": "HC3",
        "sample_filter": "prefiling_lag_1m|lag_3m, join_ready",
        "iv_nonzero_n": nz,
        "iv_nonzero_pct": nz_pct,
        "iv_min": round(float(iv_s.min()), 6),
        "iv_max": round(float(iv_s.max()), 6),
        "iv_mean": round(float(iv_s.mean()), 6),
        "convergence_ok": 1,
        "note": note,
    }

    # f-stat
    try:
        fstat = float(res.fvalue) if res.fvalue is not None else None
        fpval = float(res.f_pvalue) if res.f_pvalue is not None else None
    except Exception:
        fstat, fpval = None, None

    drow = {
        "model_id": model_id, "hypothesis": hyp, "dv": dv, "focal_iv": focal_iv,
        "n_obs": n, "n_companies": int(sub["company_name"].nunique()),
        "n_periods": int(sub["target_report_year"].nunique()) if "target_report_year" in sub.columns else "",
        "r_squared": round(float(res.rsquared), 4),
        "adj_r_squared": round(float(res.rsquared_adj), 4),
        "f_stat": round(fstat, 4) if fstat else None,
        "f_pvalue": round(fpval, 4) if fpval else None,
        "fixed_effects": fe_lbl,
        "controls": ctrl_lbl,
        "iv_nonzero_n": nz,
        "iv_nonzero_pct": nz_pct,
        "focal_iv_vif_approx": None,
        "convergence_ok": 1,
    }
    return rrow, drow


def _failed_row(model_id, hyp, dv, focal_iv, controls, fe_cols, note, err):
    return {
        "model_id": model_id, "hypothesis": hyp, "dv": dv,
        "window": DV_WINDOW.get(dv, ""), "focal_iv": focal_iv,
        "beta": None, "se_hc3": None, "t_stat": None, "p_value": None,
        "ci_lower_95": None, "ci_upper_95": None,
        "significant_p01": None, "significant_p05": None, "significant_p10": None,
        "n_obs": None, "n_companies": None, "n_periods": None,
        "r_squared": None, "adj_r_squared": None,
        "fixed_effects": "+".join(fe_cols), "controls": ",".join(controls),
        "se_type": "HC3", "sample_filter": "prefiling_lag_1m|lag_3m, join_ready",
        "iv_nonzero_n": None, "iv_nonzero_pct": None,
        "iv_min": None, "iv_max": None, "iv_mean": None,
        "convergence_ok": 0, "note": f"FAILED: {err}",
    }


def _failed_diag(model_id, hyp, dv, focal_iv, controls, fe_cols, n):
    return {
        "model_id": model_id, "hypothesis": hyp, "dv": dv, "focal_iv": focal_iv,
        "n_obs": n, "n_companies": None, "n_periods": None,
        "r_squared": None, "adj_r_squared": None,
        "f_stat": None, "f_pvalue": None,
        "fixed_effects": "+".join(fe_cols), "controls": ",".join(controls),
        "iv_nonzero_n": None, "iv_nonzero_pct": None,
        "focal_iv_vif_approx": None, "convergence_ok": 0,
    }


# ── model specifications ─────────────────────────────────────────────────────

def get_h1_specs():
    FE_NAICS   = ["target_report_year", "naics_sector_code"]
    FE_COMPANY = ["target_report_year", "company_name"]

    specs = []
    # H1a primary — all 3 DVs
    for dv in DVS:
        specs.append(dict(model_id=f"H1a_gate6_{dv}", hyp="H1", dv=dv,
                          focal_iv="humor_prob_mean",
                          controls=CTRL_BASE, fe=FE_NAICS,
                          note="primary H1; bounded [0,1]; 100% nonzero"))
    # H1a alias — CAR_m1_p1 only (confirmation)
    specs.append(dict(model_id="H1a_alias_m1p1", hyp="H1", dv="CAR_m1_p1",
                      focal_iv="ambiguity_adjusted_humor_share",
                      controls=CTRL_BASE, fe=FE_NAICS,
                      note="alias of humor_prob_mean; confirmation only; not independent finding"))
    # H1b robustness — all 3 DVs each
    for dv in DVS:
        specs.append(dict(model_id=f"H1b_share_{dv}", hyp="H1", dv=dv,
                          focal_iv="hc_humor_share",
                          controls=CTRL_BASE, fe=FE_NAICS, note="robustness"))
        specs.append(dict(model_id=f"H1b_binary_{dv}", hyp="H1", dv=dv,
                          focal_iv="hc_humor_presence_any",
                          controls=CTRL_BASE, fe=FE_NAICS, note="robustness binary"))
        specs.append(dict(model_id=f"H1b_logcount_{dv}", hyp="H1", dv=dv,
                          focal_iv="hc_log_humor_count",
                          controls=CTRL_BASE, fe=FE_NAICS,
                          note="robustness; CTRL_BASE only (no log_count in controls)"))
        specs.append(dict(model_id=f"H1b_scoresum_{dv}", hyp="H1", dv=dv,
                          focal_iv="humor_candidate_score_sum",
                          controls=CTRL_BASE, fe=FE_NAICS,
                          note="robustness; renamed from humor_prob_sum; unbounded"))
    # H1a compFE robustness — all 3 DVs
    for dv in DVS:
        specs.append(dict(model_id=f"H1a_compFE_{dv}", hyp="H1", dv=dv,
                          focal_iv="humor_prob_mean",
                          controls=CTRL_BASE, fe=FE_COMPANY,
                          note="robustness: Period+Company FE"))
    return specs


def get_h2_specs():
    FE_NAICS = ["target_report_year", "naics_sector_code"]

    h2_ivs = [
        ("H2a_gate6",     "hc_v2_aggressive_candidate_count",
         "primary; firm-level count; NOT normalized"),
        ("H2a_logv2",     "hc_log_v2_aggressive_candidate",   "robustness log-count"),
        ("H2a_binary",    "hc_v2_aggressive_candidate_presence", "robustness binary"),
        ("H2b_scoresum",  "aggressive_candidate_score_sum",
         "robustness; corrected formula P(humor)xP(type)"),
        ("H2b_scoremean", "aggressive_candidate_score_mean",   "robustness mean score"),
        ("H2b_scoremax",  "aggressive_candidate_score_max",    "robustness max score"),
        ("H2c_rare",      "hc_rare_class_candidate_count",     "robustness rare count"),
        ("H2c_rarelogg",  "hc_log_rare_class_candidate",       "robustness log rare"),
        ("H2c_rarebinary","hc_rare_class_candidate_presence",  "robustness rare binary"),
    ]

    specs = []
    for base_id, iv, note in h2_ivs:
        for dv in DVS:
            specs.append(dict(model_id=f"{base_id}_{dv}", hyp="H2", dv=dv,
                              focal_iv=iv, controls=CTRL_WITH_COUNT,
                              fe=FE_NAICS, note=note))
    return specs


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Gate 6A: H1/H2 Regressions (H3 NOT run) ===\n")

    # Load
    df = pd.read_csv(PANEL_PATH, encoding="utf-8-sig", low_memory=False)
    print(f"  Panel: {len(df)} rows, {len(df.columns)} cols")

    # Alias: humor_candidate_score_sum ← humor_prob_sum
    if "humor_prob_sum" in df.columns and "humor_candidate_score_sum" not in df.columns:
        df["humor_candidate_score_sum"] = pd.to_numeric(df["humor_prob_sum"], errors="coerce")

    # Numeric coerce for key columns
    for c in ["ambiguity_rate", "high_ambiguity_flag", "source_x_handle_count",
              "log_humor_count"] + DVS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # high_ambiguity_flag boolean → int
    if "high_ambiguity_flag" in df.columns:
        df["high_ambiguity_flag"] = df["high_ambiguity_flag"].astype(str).map(
            {"True": 1, "False": 0, "1": 1, "0": 0, "1.0": 1, "0.0": 0}
        ).fillna(0).astype(int)

    # Validate no forbidden IV in data columns used
    used_cols = set(df.columns)
    forbidden_present = used_cols & FORBIDDEN_IVS
    if forbidden_present:
        print(f"  WARNING: Forbidden columns exist in panel (will not be used): {forbidden_present}")

    # Collect specs
    h1_specs = get_h1_specs()
    h2_specs = get_h2_specs()
    all_specs = h1_specs + h2_specs
    print(f"  H1 specs: {len(h1_specs)}")
    print(f"  H2 specs: {len(h2_specs)}")
    print(f"  Total:    {len(all_specs)}")

    results = []
    diags   = []
    failed  = 0

    print("\n[Running H1 models]")
    for s in h1_specs:
        dv = s["dv"]
        sam = primary_sample(df, dv)
        r, d = run_ols(sam, dv, s["focal_iv"], s["controls"], s["fe"],
                       s["model_id"], s["hyp"], s["note"])
        results.append(r)
        diags.append(d)
        ok  = "OK" if r["convergence_ok"] else "FAIL"
        sig = " *" if (r["p_value"] is not None and r["p_value"] < 0.10) else ""
        pv  = f"p={r['p_value']:.3f}" if r["p_value"] is not None else "p=NA"
        bt  = f"β={r['beta']:.4f}" if r["beta"] is not None else "β=NA"
        print(f"  [{ok}] {s['model_id']:<35} {bt}  {pv}{sig}")
        if not r["convergence_ok"]:
            failed += 1

    print("\n[Running H2 models]")
    for s in h2_specs:
        dv = s["dv"]
        sam = primary_sample(df, dv)
        r, d = run_ols(sam, dv, s["focal_iv"], s["controls"], s["fe"],
                       s["model_id"], s["hyp"], s["note"])
        results.append(r)
        diags.append(d)
        ok  = "OK" if r["convergence_ok"] else "FAIL"
        sig = " *" if (r["p_value"] is not None and r["p_value"] < 0.10) else ""
        pv  = f"p={r['p_value']:.3f}" if r["p_value"] is not None else "p=NA"
        bt  = f"β={r['beta']:.4f}" if r["beta"] is not None else "β=NA"
        print(f"  [{ok}] {s['model_id']:<35} {bt}  {pv}{sig}")
        if not r["convergence_ok"]:
            failed += 1

    # ── Write outputs ─────────────────────────────────────────────────────
    OUT_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    res_df  = pd.DataFrame(results)
    diag_df = pd.DataFrame(diags)
    res_df.to_csv(OUT_RESULTS,  index=False, encoding="utf-8-sig")
    diag_df.to_csv(OUT_DIAGS,   index=False, encoding="utf-8-sig")
    print(f"\n  Results  → {OUT_RESULTS}  ({len(res_df)} rows)")
    print(f"  Diags    → {OUT_DIAGS}")

    # ── Summary stats ─────────────────────────────────────────────────────
    ok_df   = res_df[res_df["convergence_ok"] == 1].copy()
    h1_res  = ok_df[ok_df["hypothesis"] == "H1"]
    h2_res  = ok_df[ok_df["hypothesis"] == "H2"]

    def sig_summary(sub, label):
        if len(sub) == 0:
            return f"{label}: no OK models"
        n_total  = len(sub)
        n_p10    = int((sub["p_value"] < 0.10).sum())
        n_p05    = int((sub["p_value"] < 0.05).sum())
        n_p01    = int((sub["p_value"] < 0.01).sum())
        beta_rng = f"[{sub['beta'].min():.4f}, {sub['beta'].max():.4f}]"
        pval_rng = f"[{sub['p_value'].min():.3f}, {sub['p_value'].max():.3f}]"
        return (f"{label}: n={n_total}  sig@p10={n_p10}  sig@p05={n_p05}  sig@p01={n_p01}  "
                f"β range={beta_rng}  p range={pval_rng}")

    print()
    print("=== H1 RESULTS ===")
    print(sig_summary(h1_res, "H1 all"))
    for dv in DVS:
        sub = h1_res[h1_res["dv"] == dv]
        print(f"  {dv}: n={len(sub)}  sig@p05={int((sub['p_value']<0.05).sum())}  "
              f"sig@p10={int((sub['p_value']<0.10).sum())}  "
              f"β=[{sub['beta'].min():.4f},{sub['beta'].max():.4f}]  "
              f"p=[{sub['p_value'].min():.3f},{sub['p_value'].max():.3f}]")

    print()
    print("=== H2 RESULTS ===")
    print(sig_summary(h2_res, "H2 all"))
    for dv in DVS:
        sub = h2_res[h2_res["dv"] == dv]
        print(f"  {dv}: n={len(sub)}  sig@p05={int((sub['p_value']<0.05).sum())}  "
              f"sig@p10={int((sub['p_value']<0.10).sum())}  "
              f"β=[{sub['beta'].min():.4f},{sub['beta'].max():.4f}]  "
              f"p=[{sub['p_value'].min():.3f},{sub['p_value'].max():.3f}]")

    # notable results
    notable = ok_df[ok_df["p_value"] < 0.10].sort_values("p_value")
    print()
    if len(notable) > 0:
        print("=== Notable (p < 0.10) ===")
        for _, row in notable.iterrows():
            print(f"  {row['model_id']:<38} β={row['beta']:+.4f}  p={row['p_value']:.3f}  "
                  f"n={row['n_obs']}  IV={row['focal_iv']}")
    else:
        print("=== No models significant at p < 0.10 ===")

    # ── Manifest ──────────────────────────────────────────────────────────
    n_total_run = len(results)
    n_ok        = int(ok_df.__len__())
    n_failed    = failed

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "Gate 6A — H1/H2 Regression Execution",
        "based_on_design_commit": DESIGN_COMMIT,
        "based_on_spec_manifest": str(SPEC_MAN),
        "iv_source_file": str(PANEL_PATH),
        "se_type": "HC3",
        "fe_primary": "target_report_year + naics_sector_code",
        "fe_compFE": "target_report_year + company_name (H1a_compFE only)",
        # execution flags
        "regression_run": True,
        "h1_run": True,
        "h2_run": True,
        "h3_run": False,
        "h3_blocked_pending_manual_validation": True,
        # counts
        "models_run": n_total_run,
        "models_ok": n_ok,
        "models_failed": n_failed,
        "h1_models_run": len(h1_specs),
        "h2_models_run": len(h2_specs),
        # result summary
        "h1_sig_p05": int((h1_res["p_value"] < 0.05).sum()) if len(h1_res) else 0,
        "h1_sig_p10": int((h1_res["p_value"] < 0.10).sum()) if len(h1_res) else 0,
        "h2_sig_p05": int((h2_res["p_value"] < 0.05).sum()) if len(h2_res) else 0,
        "h2_sig_p10": int((h2_res["p_value"] < 0.10).sum()) if len(h2_res) else 0,
        "h1_primary_beta_m1p1": round(float(
            ok_df.loc[(ok_df["model_id"]=="H1a_gate6_CAR_m1_p1") & (ok_df["hypothesis"]=="H1"), "beta"].iloc[0]
        ), 6) if len(ok_df[(ok_df["model_id"]=="H1a_gate6_CAR_m1_p1")]) > 0 else None,
        "h1_primary_p_m1p1": round(float(
            ok_df.loc[(ok_df["model_id"]=="H1a_gate6_CAR_m1_p1") & (ok_df["hypothesis"]=="H1"), "p_value"].iloc[0]
        ), 4) if len(ok_df[(ok_df["model_id"]=="H1a_gate6_CAR_m1_p1")]) > 0 else None,
        "h2_primary_beta_m1p1": round(float(
            ok_df.loc[ok_df["model_id"]=="H2a_gate6_CAR_m1_p1", "beta"].iloc[0]
        ), 6) if len(ok_df[ok_df["model_id"]=="H2a_gate6_CAR_m1_p1"]) > 0 else None,
        "h2_primary_p_m1p1": round(float(
            ok_df.loc[ok_df["model_id"]=="H2a_gate6_CAR_m1_p1", "p_value"].iloc[0]
        ), 4) if len(ok_df[ok_df["model_id"]=="H2a_gate6_CAR_m1_p1"]) > 0 else None,
        # constraint flags
        "forbidden_iv_used": False,
        "car_0_p3_used": False,
        "car_0_p5_used": False,
        "tobins_q_initiated": False,
        "causal_claim_made": False,
        "brand_equity_claimed": False,
        "v2_candidate_ground_truth_claimed": False,
        "car_used_as_tobins_q": False,
        "car_used_as_direct_brand_equity": False,
        "raw_data_modified": False,
        "existing_iv_overwritten": False,
        "regression_master_overwritten": False,
        "hypothesis_variables_overwritten": False,
    }
    OUT_MAN.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAN.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  Manifest → {OUT_MAN}")

    # ── Summary markdown ──────────────────────────────────────────────────
    _write_summary(ok_df, h1_res, h2_res, manifest, n_total_run, n_ok, n_failed)
    print(f"  Summary  → {OUT_SUM}")


def _write_summary(ok_df, h1_res, h2_res, manifest, n_total_run, n_ok, n_failed):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def pval_label(p):
        if p is None or (isinstance(p, float) and np.isnan(p)):
            return "NA"
        if p < 0.01:  return f"{p:.3f} **"
        if p < 0.05:  return f"{p:.3f} *"
        if p < 0.10:  return f"{p:.3f} †"
        return f"{p:.3f} NS"

    # H1 primary results table
    h1_primary = ok_df[ok_df["model_id"].str.startswith("H1a_gate6")].sort_values("dv")
    h2_primary = ok_df[ok_df["model_id"].str.startswith("H2a_gate6")].sort_values("dv")

    h1_tbl = ""
    for _, r in h1_primary.iterrows():
        h1_tbl += (f"| {r['model_id']:<30} | {r['focal_iv']:<30} | {r['beta']:+.4f} | "
                   f"{r['se_hc3']:.4f} | {pval_label(r['p_value']):<12} | "
                   f"{r['n_obs']} | {r['r_squared']:.3f} |\n")

    h2_tbl = ""
    for _, r in h2_primary.iterrows():
        h2_tbl += (f"| {r['model_id']:<30} | {r['focal_iv']:<35} | {r['beta']:+.4f} | "
                   f"{r['se_hc3']:.4f} | {pval_label(r['p_value']):<12} | "
                   f"{r['n_obs']} | {r['r_squared']:.3f} |\n")

    # H1 full robustness table
    h1_rob_tbl = ""
    for _, r in h1_res.iterrows():
        if "gate6" not in r["model_id"] and "alias" not in r["model_id"]:
            h1_rob_tbl += (f"| {r['model_id']:<35} | {r['focal_iv']:<30} | {r['dv']:<12} | "
                           f"{r['beta']:+.4f} | {pval_label(r['p_value']):<12} |\n")

    # H2 full robustness table
    h2_rob_tbl = ""
    for _, r in h2_res.iterrows():
        if "gate6" not in r["model_id"]:
            h2_rob_tbl += (f"| {r['model_id']:<35} | {r['focal_iv']:<35} | {r['dv']:<12} | "
                           f"{r['beta']:+.4f} | {pval_label(r['p_value']):<12} |\n")

    h1_sig_any = int((h1_res["p_value"] < 0.10).sum()) if len(h1_res) else 0
    h2_sig_any = int((h2_res["p_value"] < 0.10).sum()) if len(h2_res) else 0

    h1_verdict = "No significant associations at p < 0.10." if h1_sig_any == 0 else \
                 f"{h1_sig_any} model(s) significant at p < 0.10 — see table."
    h2_verdict = "No significant associations at p < 0.10." if h2_sig_any == 0 else \
                 f"{h2_sig_any} model(s) significant at p < 0.10 — see table."

    md = f"""# Gate 6A — H1/H2 Regression Results

**Date:** {now}
**Status:** H1 and H2 executed; H3 blocked (pending human validation)
**Design commit:** {manifest['based_on_design_commit']}
**Models run:** {n_total_run} total ({manifest['h1_models_run']} H1, {manifest['h2_models_run']} H2)
**Failed models:** {n_failed}

---

## Interpretation Constraints

> **CAR is a short-window market reaction proxy only.** Results must not be described as evidence of causal effects on brand equity, firm value, or Tobin's Q. All associations are observational. Significant coefficients reflect correlation, not causation.

> **v2 aggressive candidates are unvalidated candidate signals.** H2 results using v2-based IVs are not evidence of true aggressive humor presence.

---

## H1 Results: Humor Presence and Market Reaction

**Hypothesis:** Greater probability-weighted humor presence is associated with higher CAR.

**Primary IV:** `humor_prob_mean` (bounded [0,1]; mean P(humor) per firm-period; 100% nonzero)

**Overall H1 verdict:** {h1_verdict}

### H1 Primary Models (humor_prob_mean × 3 DVs)

| Model | IV | β | SE (HC3) | p-value | n | R² |
|-------|----|----|----------|---------|---|-----|
{h1_tbl}
*† p<0.10  * p<0.05  ** p<0.01  NS = not significant*

### H1 Robustness Models

| Model | IV | DV | β | p-value |
|-------|----|----|---|---------|
{h1_rob_tbl if h1_rob_tbl else "*(no additional robustness models displayed)*"}

---

## H2 Results: Aggressive Humor Candidate Signal and Market Reaction

**Hypothesis:** Greater aggressive humor candidate signal is associated with differential CAR.

**Primary IV:** `hc_v2_aggressive_candidate_count` (firm-level count; NOT confirmed aggressive)

**Overall H2 verdict:** {h2_verdict}

### H2 Primary Models (hc_v2_aggressive_candidate_count × 3 DVs)

| Model | IV | β | SE (HC3) | p-value | n | R² |
|-------|----|----|----------|---------|---|-----|
{h2_tbl}

### H2 Robustness Models

| Model | IV | DV | β | p-value |
|-------|----|----|---|---------|
{h2_rob_tbl if h2_rob_tbl else "*(no additional robustness models displayed)*"}

---

## Consistency with Gate 3

Gate 3 (Extended CAR Regression, commit `f5caa90`) found no significant H1–H3 associations across all three CAR windows using the original IVs (`humor_share`, `self_enhancing_share`, `aggressive_share`). Gate 6A uses reconstructed probability-weighted IVs.

---

## H3 Status

**H3 NOT executed.** Blocked pending:
1. Human coding of `humor_candidate_manual_audit_sample.csv`
2. Inter-rater reliability ≥ κ 0.60
3. PI sign-off

---

## Constraint Verification

| Constraint | Status |
|-----------|--------|
| H3 not run | ✅ True |
| Forbidden IVs not used | ✅ True |
| CAR_0_p3 not used | ✅ True |
| CAR_0_p5 not used | ✅ True |
| causal_claim_made | ✅ False |
| brand_equity_claimed | ✅ False |
| tobins_q_initiated | ✅ False |
| v2 candidate as ground truth | ✅ False |
| raw_data_modified | ✅ False |

*Gate 6A manifest: `data/audit/regression/humor_iv_gate6_h1_h2_regression_manifest.json`*
"""
    OUT_SUM.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUM.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
