#!/usr/bin/env python3
"""
build_humor_iv_reconstructed_candidates.py

Gate 5: Humor IV Reconstruction / Measurement Repair.

목적:
  Gate 4 진단에서 확인된 IV 측정 병목을 해결하는 대체 IV 세트를 생성한다.
  - 기존 IV 파일을 덮어쓰지 않음
  - ambiguous 포스트를 probability-weighting으로 활용
  - aggressive 희소성을 count/binary/probability/candidate 변수로 완화

소스:
  (A) full_chain_master → post-level ML 확률 집계
  (B) hypothesis_variables → v2_aggressive_candidate_count 등 기존 확장 변수 활용

금지:
  raw humor output 수정 / 기존 hypothesis variables 덮어쓰기
  regression master 덮어쓰기 / 회귀 실행 / causal claim / Brand Equity claim

출력:
  data/derived/regression/humor_iv_reconstructed_candidates.csv
  data/derived/regression/humor_iv_reconstructed_candidate_diagnostics.csv
  data/audit/regression/humor_iv_reconstruction_manifest.json
"""

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

FULL_CHAIN  = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
HYPO_VARS   = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
REG_MASTER  = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")
GATE4_DIAG  = Path("data/derived/regression/humor_iv_measurement_diagnostic.csv")

OUT_CANDS   = Path("data/derived/regression/humor_iv_reconstructed_candidates.csv")
OUT_DIAGS   = Path("data/derived/regression/humor_iv_reconstructed_candidate_diagnostics.csv")
OUT_MAN     = Path("data/audit/regression/humor_iv_reconstruction_manifest.json")

# H3 re-testing thresholds
H3_THRESHOLD_EXPLORATORY    = 30
H3_THRESHOLD_LIMITED_ROBUST = 50

# Top-k for aggressive score aggregation
TOP_K = 3

# Base rate for ambiguous → aggressive probability assignment
# = aggressive / (affiliative + self_enhancing + aggressive + self_defeating)
AGGRESSIVE_BASE_RATE = 105 / (4668 + 4887 + 105 + 41)  # ≈ 0.0108


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_twitter_date_to_period(s):
    """'Sun Jun 14 10:50:03 +0000 2026' → '2026-06'"""
    try:
        dt = pd.to_datetime(s, format="%a %b %d %H:%M:%S %z %Y", utc=True)
        return dt.strftime("%Y-%m")
    except Exception:
        try:
            dt = pd.to_datetime(s, utc=True)
            return dt.strftime("%Y-%m")
        except Exception:
            return None


def pct(n, d):
    return round(100 * n / d, 2) if d > 0 else 0.0


def iv_diagnostics(s, name, label, note=""):
    """Return one-row dict of diagnostics for a numeric Series."""
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    n = len(s)
    nz = int((s > 0).sum())
    return {
        "iv_name":    name,
        "label":      label,
        "note":       note,
        "n":          n,
        "zero_n":     int((s == 0).sum()),
        "zero_pct":   pct((s == 0).sum(), n),
        "nonzero_n":  nz,
        "nonzero_pct": pct(nz, n),
        "mean":       round(float(s.mean()), 6),
        "median":     round(float(s.median()), 6),
        "std":        round(float(s.std()), 6),
        "min":        round(float(s.min()), 6),
        "max":        round(float(s.max()), 6),
        "p10":        round(float(s.quantile(0.10)), 6),
        "p25":        round(float(s.quantile(0.25)), 6),
        "p75":        round(float(s.quantile(0.75)), 6),
        "p90":        round(float(s.quantile(0.90)), 6),
    }


def within_company_std(df, iv_col, co_col="company_name"):
    if co_col not in df.columns or iv_col not in df.columns:
        return None
    s = pd.to_numeric(df[iv_col], errors="coerce").fillna(0)
    grp = df.assign(__iv=s).groupby(co_col)["__iv"].std().fillna(0)
    return round(float(grp.median()), 6)


def log1p_col(s):
    return np.log1p(pd.to_numeric(s, errors="coerce").fillna(0))


# ── Step 1: load & parse full_chain ──────────────────────────────────────────

def load_full_chain(path):
    print(f"  Loading {path} ...")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    print(f"  Rows: {len(df):,}")

    # Parse period
    df["period"] = df["created_at"].apply(parse_twitter_date_to_period)
    n_bad_period = df["period"].isna().sum()
    if n_bad_period > 0:
        print(f"  WARNING: {n_bad_period} rows with unparseable created_at — dropped")
        df = df.dropna(subset=["period"])

    # Numeric columns
    df["ml_humor_probability"] = pd.to_numeric(df["ml_humor_probability"], errors="coerce")
    df["humor_type_confidence"] = pd.to_numeric(df["humor_type_confidence"], errors="coerce")

    # Flags
    df["is_humor"]      = df["humor_presence"] == "humor"
    df["is_ambiguous"]  = df["humor_presence"] == "ambiguous"
    df["is_aggressive"] = df["humor_type"] == "aggressive"
    df["is_negative"]   = df["humor_type"].isin(["aggressive", "self_defeating"])

    # Per-post aggressive probability:
    #   classified aggressive:  P = humor_type_confidence (classifier confidence)
    #   classified non-aggr humor: P = 0
    #   ambiguous: P = ml_humor_probability × AGGRESSIVE_BASE_RATE (probability-weighted base rate)
    #   non_humor: P = 0
    df["aggressive_prob"] = np.where(
        df["is_aggressive"],
        df["humor_type_confidence"].fillna(df["ml_humor_probability"]),
        np.where(
            df["is_ambiguous"],
            df["ml_humor_probability"].fillna(0) * AGGRESSIVE_BASE_RATE,
            0.0,
        )
    )

    # Humor probability weight for ALL posts (including ambiguous)
    df["humor_prob_weight"] = df["ml_humor_probability"].fillna(0)

    return df


# ── Step 2: aggregate to (company_name, period) ──────────────────────────────

def aggregate_post_level(full):
    print("  Aggregating post-level IVs to (company_name, period) ...")
    grp = full.groupby(["company_name", "period"])

    agg = grp.agg(
        _total_posts       =("global_post_id", "count"),
        _humor_count       =("is_humor", "sum"),
        _ambiguous_count   =("is_ambiguous", "sum"),
        _aggressive_count  =("is_aggressive", "sum"),
        _negative_count    =("is_negative", "sum"),
        # Probability sums
        humor_prob_sum     =("humor_prob_weight", "sum"),
        humor_prob_mean    =("humor_prob_weight", "mean"),
        aggressive_prob_sum=("aggressive_prob", "sum"),
        aggressive_prob_mean=("aggressive_prob", "mean"),
        aggressive_prob_max=("aggressive_prob", "max"),
    ).reset_index()

    # Derived
    agg["ambiguity_adjusted_humor_share"] = (
        agg["humor_prob_sum"] / agg["_total_posts"].replace(0, np.nan)
    ).fillna(0)

    agg["aggressive_prob_intensity"] = (
        agg["aggressive_prob_sum"] / agg["_humor_count"].replace(0, np.nan)
    ).fillna(0)

    agg["negative_humor_presence_any_post"] = (agg["_negative_count"] > 0).astype(int)

    # Top-k aggressive type_confidence per firm-period
    def topk_mean(grp_df):
        scores = grp_df.loc[grp_df["is_aggressive"], "humor_type_confidence"].dropna()
        if len(scores) == 0:
            return 0.0
        return float(scores.nlargest(TOP_K).mean())

    topk = full.groupby(["company_name", "period"]).apply(topk_mean).reset_index()
    topk.columns = ["company_name", "period", "top_k_aggressive_score"]
    agg = agg.merge(topk, on=["company_name", "period"], how="left")
    agg["top_k_aggressive_score"] = agg["top_k_aggressive_score"].fillna(0)

    print(f"  Aggregated: {len(agg):,} firm-period rows")
    return agg


# ── Step 3: build from hypothesis_variables ──────────────────────────────────

def build_hypo_candidates(hypo):
    print("  Building candidates from hypothesis_variables ...")
    df = hypo.copy()

    # Numeric coerce
    for c in ["total_posts", "humor_count", "aggressive_count", "self_defeating_count",
              "v2_aggressive_candidate_count", "rare_class_candidate_count",
              "v1_v2_disagreement_candidate_count", "affiliative_count",
              "self_enhancing_count"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # ── H1 candidates from hypo ──────────────────────────────────────────
    df["hc_log_humor_count"]   = log1p_col(df["humor_count"])
    df["hc_humor_count"]       = df["humor_count"]
    df["hc_humor_presence_any"] = (df["humor_count"] > 0).astype(int)
    df["hc_humor_share"]       = df.get("humor_share",
                                 df["humor_count"] / df["total_posts"].replace(0, np.nan)).fillna(0)

    # ── H2 candidates from hypo ──────────────────────────────────────────
    # Broader aggressive: v2 candidate
    df["hc_v2_aggressive_candidate_count"]    = df["v2_aggressive_candidate_count"]
    df["hc_log_v2_aggressive_candidate"]      = log1p_col(df["v2_aggressive_candidate_count"])
    df["hc_v2_aggressive_candidate_presence"] = (df["v2_aggressive_candidate_count"] > 0).astype(int)
    df["hc_v2_aggressive_candidate_share"]    = (
        df["v2_aggressive_candidate_count"] / df["total_posts"].replace(0, np.nan)
    ).fillna(0)
    df["hc_v2_aggressive_candidate_intensity"] = (
        df["v2_aggressive_candidate_count"] / df["humor_count"].replace(0, np.nan)
    ).fillna(0)

    # Rare class candidate
    df["hc_rare_class_candidate_count"]    = df["rare_class_candidate_count"]
    df["hc_log_rare_class_candidate"]      = log1p_col(df["rare_class_candidate_count"])
    df["hc_rare_class_candidate_presence"] = (df["rare_class_candidate_count"] > 0).astype(int)
    df["hc_rare_class_candidate_share"]    = (
        df["rare_class_candidate_count"] / df["total_posts"].replace(0, np.nan)
    ).fillna(0)
    df["hc_rare_class_candidate_intensity"] = (
        df["rare_class_candidate_count"] / df["humor_count"].replace(0, np.nan)
    ).fillna(0)

    # Negative humor (aggressive + self_defeating)
    neg_count = df["aggressive_count"] + df["self_defeating_count"]
    df["hc_negative_humor_count"]        = neg_count
    df["hc_negative_humor_presence_any"] = (neg_count > 0).astype(int)
    df["hc_negative_humor_share"]        = (
        neg_count / df["total_posts"].replace(0, np.nan)
    ).fillna(0)
    df["hc_negative_humor_intensity"]    = (
        neg_count / df["humor_count"].replace(0, np.nan)
    ).fillna(0)

    # Aggressive (existing, for reference comparison)
    df["hc_aggressive_count"]    = df["aggressive_count"]
    df["hc_aggressive_presence"] = (df["aggressive_count"] > 0).astype(int)
    df["hc_log_aggressive"]      = log1p_col(df["aggressive_count"])
    df["hc_aggressive_share_among_humor"] = (
        df["aggressive_count"] / df["humor_count"].replace(0, np.nan)
    ).fillna(0)

    # V1/V2 disagreement (potential misclassification signal)
    df["hc_v1v2_disagreement_count"]    = df["v1_v2_disagreement_candidate_count"]
    df["hc_v1v2_disagreement_presence"] = (df["v1_v2_disagreement_candidate_count"] > 0).astype(int)

    return df[["company_name", "period"] +
              [c for c in df.columns if c.startswith("hc_")]]


# ── Step 4: join all onto regression master ───────────────────────────────────

def build_candidate_panel(master, hypo_cands, post_agg):
    print("  Joining candidates onto regression master ...")
    df = master.copy()
    # join key: (company_name, period)
    df = df.merge(hypo_cands, on=["company_name", "period"], how="left")
    df = df.merge(post_agg.drop(columns=["_total_posts","_humor_count",
                                          "_ambiguous_count","_aggressive_count",
                                          "_negative_count"], errors="ignore"),
                  on=["company_name", "period"], how="left")

    # Fill probability-based IVs with 0 for unmatched rows (no posts in that period)
    prob_cols = [c for c in df.columns if c in
                 ["humor_prob_sum","humor_prob_mean","aggressive_prob_sum",
                  "aggressive_prob_mean","aggressive_prob_max","top_k_aggressive_score",
                  "ambiguity_adjusted_humor_share","aggressive_prob_intensity",
                  "negative_humor_presence_any_post"]]
    for c in prob_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    print(f"  Candidate panel: {len(df)} rows, {len(df.columns)} columns")
    return df


# ── Step 5: diagnostics ───────────────────────────────────────────────────────

# IV registry: (column, label, hypothesis_target, note)
def build_iv_registry(df_primary):
    cols = df_primary.columns.tolist()
    registry = []

    # H1 candidates
    h1 = [
        ("hc_humor_count",                  "H1 count (raw)",           "H1", "existing reconstructed"),
        ("hc_log_humor_count",              "H1 log(1+count)",           "H1", "existing reconstructed"),
        ("hc_humor_presence_any",           "H1 binary",                 "H1", "existing reconstructed"),
        ("hc_humor_share",                  "H1 share (existing)",       "H1", "existing reconstructed"),
        ("humor_prob_sum",                  "H1 prob-weighted sum",      "H1", "sum(P_humor) over all posts"),
        ("humor_prob_mean",                 "H1 prob-weighted mean",     "H1", "mean(P_humor) over all posts"),
        ("ambiguity_adjusted_humor_share",  "H1 ambiguity-adj share",    "H1", "sum(P_humor)/total_posts; treats ambiguous proportionally"),
    ]
    # H2 candidates
    h2 = [
        ("hc_aggressive_count",             "H2 aggressive count (original)", "H2", "98.8% zero — baseline"),
        ("hc_aggressive_presence",          "H2 aggressive binary",      "H2", "original"),
        ("hc_log_aggressive",               "H2 log(1+aggressive)",      "H2", "original log"),
        ("hc_aggressive_share_among_humor", "H2 aggressive share/humor", "H2", "original"),
        ("hc_v2_aggressive_candidate_count","H2 v2 aggressive candidate count","H2", "BROADER DEFINITION — includes candidates"),
        ("hc_log_v2_aggressive_candidate",  "H2 log(1+v2_candidate)",    "H2", "log-transformed broader IV"),
        ("hc_v2_aggressive_candidate_presence","H2 v2 candidate binary", "H2", "binary: any v2 aggressive candidate"),
        ("hc_v2_aggressive_candidate_share","H2 v2 candidate share/total","H2","v2_count/total_posts"),
        ("hc_rare_class_candidate_count",   "H2 rare class candidate count","H2","rare_class_candidate_count"),
        ("hc_rare_class_candidate_presence","H2 rare class binary",      "H2","binary rare class"),
        ("hc_negative_humor_count",         "H2 negative humor count",   "H2", "aggressive + self_defeating"),
        ("hc_negative_humor_presence_any",  "H2 negative binary",        "H2", "any negative humor type"),
        ("hc_negative_humor_share",         "H2 negative share/total",   "H2", "negative/total_posts"),
        ("aggressive_prob_sum",             "H2 aggressive prob sum",    "H2", "Σ P(aggressive) per post"),
        ("aggressive_prob_mean",            "H2 aggressive prob mean",   "H2", "mean P(aggressive)"),
        ("aggressive_prob_max",             "H2 aggressive prob max",    "H2", "max P(aggressive) per firm-period"),
        ("top_k_aggressive_score",          "H2 top-k aggressive score", "H2", f"mean of top-{TOP_K} type_confidence for aggressive posts"),
        ("negative_humor_presence_any_post","H2 negative post-level binary","H2","any aggressive/self_defeating post"),
    ]
    # H3 candidates
    h3 = [
        ("hc_v2_aggressive_candidate_intensity","H3 v2 candidate intensity","H3","v2_count/humor_count — BROADER"),
        ("hc_rare_class_candidate_intensity",   "H3 rare class intensity", "H3", "rare_count/humor_count"),
        ("hc_negative_humor_intensity",         "H3 negative intensity",   "H3", "(aggressive+self_defeat)/humor_count"),
        ("aggressive_prob_intensity",           "H3 aggressive prob intensity","H3","Σ P(aggressive)/humor_count"),
        ("aggressive_prob_sum",                 "H3 aggressive prob sum (alt)","H3","used as continuous IV alternative"),
        ("top_k_aggressive_score",              "H3 top-k score (alt)",    "H3", "alternative intensity proxy"),
    ]
    # Filter to columns that actually exist
    for group in [h1, h2, h3]:
        for col, label, hyp, note in group:
            if col in cols:
                registry.append((col, label, hyp, note))
    return registry


def compute_all_diagnostics(df_primary, df_full_panel, registry):
    rows = []
    for col, label, hyp, note in registry:
        if col not in df_primary.columns:
            continue
        d = iv_diagnostics(df_primary[col], col, label, note)
        d["hypothesis"] = hyp
        wcs = within_company_std(df_primary, col)
        d["within_company_std_median"] = wcs

        # Correlation with existing key IVs in primary sample
        for ref_col in ["humor_share", "aggressive_share", "aggressive_humor_usage_intensity",
                         "ambiguity_rate"]:
            if ref_col in df_primary.columns:
                r = pd.to_numeric(df_primary[col], errors="coerce").fillna(0).corr(
                    pd.to_numeric(df_primary[ref_col], errors="coerce").fillna(0)
                )
                d[f"corr_with_{ref_col}"] = round(float(r), 4) if not np.isnan(r) else None
        rows.append(d)
    return rows


# ── Step 6: H3 re-testing feasibility ────────────────────────────────────────

def h3_feasibility(diag_rows):
    results = {}
    for d in diag_rows:
        if d["hypothesis"] != "H3":
            continue
        nz = d["nonzero_n"]
        if nz < H3_THRESHOLD_EXPLORATORY:
            verdict = f"H3_BLOCKED (nonzero={nz} < {H3_THRESHOLD_EXPLORATORY})"
        elif nz < H3_THRESHOLD_LIMITED_ROBUST:
            verdict = f"H3_EXPLORATORY_ONLY (nonzero={nz}, {H3_THRESHOLD_EXPLORATORY}≤n<{H3_THRESHOLD_LIMITED_ROBUST})"
        else:
            verdict = f"H3_LIMITED_ROBUSTNESS_POSSIBLE (nonzero={nz} ≥ {H3_THRESHOLD_LIMITED_ROBUST})"
        results[d["iv_name"]] = {"nonzero_n": nz, "verdict": verdict}
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Gate 5: Humor IV Reconstruction / Measurement Repair ===\n")

    # Load
    print("[Load]")
    full  = load_full_chain(FULL_CHAIN)
    hypo  = pd.read_csv(HYPO_VARS,  encoding="utf-8-sig")
    master = pd.read_csv(REG_MASTER, encoding="utf-8-sig")
    print(f"  hypothesis_variables: {len(hypo):,} rows")
    print(f"  regression_master:    {len(master):,} rows")

    # Step A: post-level aggregation
    print("\n[A] Post-level probability aggregation")
    post_agg = aggregate_post_level(full)

    # Step B: hypothesis_variables candidates
    print("\n[B] Hypothesis-variable-based candidates")
    hypo_cands = build_hypo_candidates(hypo)

    # Step C: join onto regression master
    print("\n[C] Building candidate panel")
    cand_panel = build_candidate_panel(master, hypo_cands, post_agg)

    # Primary sample
    for jr in ["join_ready_for_CAR_m1_p1"]:
        if jr in cand_panel.columns:
            col = cand_panel[jr]
            if col.dtype == object:
                cand_panel[jr] = col.str.lower().map({"true": True, "false": False})
    primary = cand_panel[
        cand_panel["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) &
        (cand_panel["join_ready_for_CAR_m1_p1"] == True)
    ].copy()
    print(f"  Primary sample for diagnostics: {len(primary)} rows")

    # Step D: diagnostics
    print("\n[D] Computing IV diagnostics")
    registry = build_iv_registry(cand_panel)
    print(f"  {len(registry)} candidate IVs to diagnose")
    diag_rows = compute_all_diagnostics(primary, cand_panel, registry)

    # Step E: H3 feasibility
    print("\n[E] H3 re-testing feasibility")
    h3_verdict = h3_feasibility(diag_rows)
    for iv, v in h3_verdict.items():
        print(f"  {iv:50s}  nonzero={v['nonzero_n']:4d}  {v['verdict']}")

    # ── Write outputs ─────────────────────────────────────────────────────
    OUT_CANDS.parent.mkdir(parents=True, exist_ok=True)
    cand_panel.to_csv(OUT_CANDS, index=False, encoding="utf-8-sig")
    print(f"\n  Candidate panel  → {OUT_CANDS}  ({len(cand_panel)} rows, {len(cand_panel.columns)} cols)")

    diag_df = pd.DataFrame(diag_rows)
    diag_df.to_csv(OUT_DIAGS, index=False, encoding="utf-8-sig")
    print(f"  Diagnostics      → {OUT_DIAGS}  ({len(diag_df)} IVs)")

    # ── Print diagnostic tables ────────────────────────────────────────────
    print("\n=== H1 Candidate IV Diagnostics (primary sample) ===")
    h1_rows = [d for d in diag_rows if d["hypothesis"] == "H1"]
    print(f"{'IV':<45} {'nonzero_n':>9} {'nonzero%':>9} {'mean':>8} {'median':>8} {'std':>8}")
    print("-"*95)
    for d in h1_rows:
        print(f"  {d['iv_name']:<43} {d['nonzero_n']:>9} {d['nonzero_pct']:>8.1f}% "
              f"{d['mean']:>8.4f} {d['median']:>8.4f} {d['std']:>8.4f}")

    print("\n=== H2 Candidate IV Diagnostics (primary sample) ===")
    h2_rows = [d for d in diag_rows if d["hypothesis"] == "H2"]
    print(f"{'IV':<50} {'nonzero_n':>9} {'nonzero%':>9} {'mean':>8}")
    print("-"*85)
    for d in h2_rows:
        print(f"  {d['iv_name']:<48} {d['nonzero_n']:>9} {d['nonzero_pct']:>8.1f}% {d['mean']:>8.4f}")

    print("\n=== H3 Candidate IV Diagnostics (primary sample) ===")
    h3_rows = [d for d in diag_rows if d["hypothesis"] == "H3"]
    print(f"{'IV':<50} {'nonzero_n':>9} {'nonzero%':>9} {'verdict'}")
    print("-"*100)
    for d in h3_rows:
        verd = h3_verdict.get(d["iv_name"], {}).get("verdict", "")
        print(f"  {d['iv_name']:<48} {d['nonzero_n']:>9} {d['nonzero_pct']:>8.1f}%  {verd}")

    # ── Manifest ──────────────────────────────────────────────────────────
    # Best H3 IV (highest nonzero_n)
    best_h3 = max(h3_verdict.items(), key=lambda x: x[1]["nonzero_n"]) if h3_verdict else (None, {})
    h3_regressionable = {iv: v for iv, v in h3_verdict.items()
                         if v["nonzero_n"] >= H3_THRESHOLD_EXPLORATORY}

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "Gate 5 — Humor IV Reconstruction / Measurement Repair",
        "script": "scripts/build_humor_iv_reconstructed_candidates.py",
        "aggressive_base_rate_used": round(AGGRESSIVE_BASE_RATE, 6),
        "top_k": TOP_K,
        "inputs": {
            "full_chain_posts": len(full),
            "hypothesis_variables_rows": len(hypo),
            "regression_master_rows": len(master),
            "candidate_panel_rows": len(cand_panel),
            "primary_sample_rows": len(primary),
        },
        "candidate_ivs_total": len(registry),
        "h1_candidates": len(h1_rows),
        "h2_candidates": len(h2_rows),
        "h3_candidates": len(h3_rows),
        "h3_feasibility": h3_verdict,
        "h3_regressionable_candidates": list(h3_regressionable.keys()),
        "h3_best_candidate": {
            "iv": best_h3[0],
            "nonzero_n": best_h3[1].get("nonzero_n"),
            "verdict": best_h3[1].get("verdict"),
        },
        "existing_iv_overwritten": False,
        "hypothesis_variables_overwritten": False,
        "regression_master_overwritten": False,
        # Constraint flags
        "raw_data_modified":     False,
        "regression_run":        False,
        "causal_claim_made":     False,
        "tobins_q_initiated":    False,
        "brand_equity_claimed":  False,
    }
    OUT_MAN.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAN.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  Manifest         → {OUT_MAN}")
    print(f"\n  Candidate IVs:  H1={len(h1_rows)}  H2={len(h2_rows)}  H3={len(h3_rows)}")
    print(f"  H3 re-testable: {len(h3_regressionable)} IVs (nonzero ≥ {H3_THRESHOLD_EXPLORATORY})")
    print(f"  Best H3 candidate: {best_h3[0]}  (nonzero={best_h3[1].get('nonzero_n')})")


if __name__ == "__main__":
    main()
