#!/usr/bin/env python3
"""
run_humor_iv_measurement_diagnostic.py

Gate 4: Humor IV Measurement Diagnostic.

진단 목적:
  H1-H3가 모든 CAR window에서 비유의인 원인이 IV 측정 문제인지 진단.

진단 항목:
  D1. Post-level humor classification distribution
  D2. Ambiguous classification 비중 및 구조
  D3. Humor type distribution (post-level)
  D4. Aggressive humor 희소성 (post-level → firm-period)
  D5. Firm-period aggregation: signal dilution 진단
  D6. IV 변수 분포 비교 (share/count/binary/intensity)
  D7. Firm-period level: zero-inflation / floor effect
  D8. Regression sample coverage: 사용된 firm-period의 post 기반 대표성
  D9. Classifier confidence 분포 (ambiguous zone 분석)
  D10. Cross-variable correlation (multicollinearity check)

금지:
  - 새로운 회귀 해석 확장 금지
  - causal claim 금지
  - raw humor output 수정 금지
"""

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DEFAULT_FULL_CHAIN  = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
DEFAULT_HYPO_VARS   = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
DEFAULT_REG_MASTER  = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")
DEFAULT_OUT_DIAG    = Path("data/derived/regression/humor_iv_measurement_diagnostic.csv")
DEFAULT_OUT_DETAIL  = Path("data/derived/regression/humor_iv_measurement_diagnostic_detail.csv")
DEFAULT_OUT_MAN     = Path("data/audit/regression/humor_iv_measurement_diagnostic_manifest.json")


# ── helpers ──────────────────────────────────────────────────────────────────

def pct(n, d):
    return round(100 * n / d, 2) if d > 0 else 0.0

def describe_series(s, label):
    """Return dict of summary stats for a numeric series."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return {f"{label}_n": 0}
    return {
        f"{label}_n":        len(s),
        f"{label}_zero_n":   int((s == 0).sum()),
        f"{label}_zero_pct": pct((s == 0).sum(), len(s)),
        f"{label}_mean":     round(float(s.mean()), 6),
        f"{label}_median":   round(float(s.median()), 6),
        f"{label}_std":      round(float(s.std()), 6),
        f"{label}_p10":      round(float(s.quantile(0.10)), 6),
        f"{label}_p25":      round(float(s.quantile(0.25)), 6),
        f"{label}_p75":      round(float(s.quantile(0.75)), 6),
        f"{label}_p90":      round(float(s.quantile(0.90)), 6),
        f"{label}_max":      round(float(s.max()), 6),
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-chain",  type=Path, default=DEFAULT_FULL_CHAIN)
    parser.add_argument("--hypo-vars",   type=Path, default=DEFAULT_HYPO_VARS)
    parser.add_argument("--reg-master",  type=Path, default=DEFAULT_REG_MASTER)
    parser.add_argument("--out-diag",    type=Path, default=DEFAULT_OUT_DIAG)
    parser.add_argument("--out-detail",  type=Path, default=DEFAULT_OUT_DETAIL)
    parser.add_argument("--out-manifest",type=Path, default=DEFAULT_OUT_MAN)
    args = parser.parse_args()

    print("=== Gate 4: Humor IV Measurement Diagnostic ===\n")

    # ── Load data ─────────────────────────────────────────────────────────────
    full   = pd.read_csv(args.full_chain,  encoding="utf-8-sig")
    hypo   = pd.read_csv(args.hypo_vars,   encoding="utf-8-sig")
    master = pd.read_csv(args.reg_master,  encoding="utf-8-sig")

    print(f"  full_chain_master:      {len(full):,} posts")
    print(f"  hypothesis_variables:   {len(hypo):,} firm-period rows")
    print(f"  regression_master:      {len(master):,} rows")

    # Numeric coerce key columns
    for col in ["ml_humor_probability", "humor_presence_confidence",
                "humor_type_confidence"]:
        if col in full.columns:
            full[col] = pd.to_numeric(full[col], errors="coerce")
    for col in ["humor_share", "humor_count", "total_posts", "aggressive_count",
                "aggressive_share", "aggressive_humor_usage_intensity",
                "ambiguity_rate", "ambiguous_count", "affiliative_count",
                "self_enhancing_count", "self_defeating_count"]:
        if col in hypo.columns:
            hypo[col] = pd.to_numeric(hypo[col], errors="coerce")

    diag_rows = []   # one row per diagnostic item
    detail_rows = [] # granular breakdown rows

    def add(section, metric, value, note=""):
        diag_rows.append({"section": section, "metric": metric,
                          "value": str(value), "note": note})

    # ════════════════════════════════════════════════════════════════════════
    # D1. Post-level humor classification distribution
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D1] Post-level humor presence distribution")
    n_total = len(full)
    hp = full["humor_presence"].value_counts()
    n_humor     = int(hp.get("humor", 0))
    n_nonhumor  = int(hp.get("non_humor", 0))
    n_ambiguous = int(hp.get("ambiguous", 0))
    n_other     = n_total - n_humor - n_nonhumor - n_ambiguous

    add("D1_post_presence", "total_posts",         n_total)
    add("D1_post_presence", "humor_posts",         n_humor,     f"{pct(n_humor, n_total):.1f}%")
    add("D1_post_presence", "non_humor_posts",     n_nonhumor,  f"{pct(n_nonhumor, n_total):.1f}%")
    add("D1_post_presence", "ambiguous_posts",     n_ambiguous, f"{pct(n_ambiguous, n_total):.1f}%")
    add("D1_post_presence", "other_posts",         n_other,     f"{pct(n_other, n_total):.1f}%")
    add("D1_post_presence", "ambiguous_rate",      round(pct(n_ambiguous, n_total), 2),
        "CRITICAL — ambiguous posts are deferred, not classified")

    print(f"  humor={n_humor:,} ({pct(n_humor,n_total):.1f}%)  "
          f"non_humor={n_nonhumor:,} ({pct(n_nonhumor,n_total):.1f}%)  "
          f"ambiguous={n_ambiguous:,} ({pct(n_ambiguous,n_total):.1f}%)")

    # ════════════════════════════════════════════════════════════════════════
    # D2. Ambiguous classification: confidence zone
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D2] Ambiguous classification confidence zone")
    if "ml_humor_probability" in full.columns:
        probs_all = full["ml_humor_probability"].dropna()
        bins = [0, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 1.01]
        labels = ["<0.30", "0.30-0.40", "0.40-0.45", "0.45-0.50",
                  "0.50-0.55", "0.55-0.60", "0.60-0.70", "≥0.70"]
        cuts = pd.cut(probs_all, bins=bins, labels=labels, right=False)
        dist = cuts.value_counts().sort_index()
        for lab, cnt in dist.items():
            add("D2_confidence_zone", f"prob_{lab}", int(cnt),
                f"{pct(cnt, len(probs_all)):.1f}% of scored posts")
            detail_rows.append({"section": "D2", "bin": str(lab), "count": cnt,
                                 "pct": pct(cnt, len(probs_all))})

        # Ambiguous zone: posts in [0.4, 0.6]
        zone_low, zone_high = 0.40, 0.60
        n_zone = int(((probs_all >= zone_low) & (probs_all < zone_high)).sum())
        add("D2_confidence_zone", "ambiguous_probability_zone_[0.40,0.60)_n", n_zone,
            f"{pct(n_zone, len(probs_all)):.1f}% of scored posts — near-decision-boundary")
        print(f"  Ambiguous probability zone [0.40, 0.60): {n_zone:,} ({pct(n_zone, len(probs_all)):.1f}%)")

    # ════════════════════════════════════════════════════════════════════════
    # D3. Humor type distribution (post-level, humor-classified only)
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D3] Humor type distribution (post-level)")
    humor_posts = full[full["humor_presence"] == "humor"]
    ht = humor_posts["humor_type"].value_counts()
    n_classified = int(ht.get("affiliative", 0) + ht.get("self_enhancing", 0) +
                       ht.get("aggressive", 0) + ht.get("self_defeating", 0))
    type_map = {
        "affiliative":    int(ht.get("affiliative", 0)),
        "self_enhancing": int(ht.get("self_enhancing", 0)),
        "aggressive":     int(ht.get("aggressive", 0)),
        "self_defeating": int(ht.get("self_defeating", 0)),
    }
    for t, n in type_map.items():
        add("D3_type_dist_post", t, n, f"{pct(n, n_humor):.1f}% of humor posts")
        detail_rows.append({"section": "D3", "type": t, "count": n,
                             "pct_of_humor": pct(n, n_humor)})
    add("D3_type_dist_post", "aggressive_rate_of_humor_posts", pct(type_map["aggressive"], n_humor),
        "CRITICAL SPARSITY — aggressive humor is <2% of humor posts")
    add("D3_type_dist_post", "aggressive_rate_of_all_posts",   pct(type_map["aggressive"], n_total))
    print(f"  affiliative={type_map['affiliative']:,}  "
          f"self_enhancing={type_map['self_enhancing']:,}  "
          f"aggressive={type_map['aggressive']:,}  "
          f"self_defeating={type_map['self_defeating']:,}")
    print(f"  Aggressive rate: {pct(type_map['aggressive'], n_humor):.2f}% of humor posts, "
          f"{pct(type_map['aggressive'], n_total):.3f}% of all posts")

    # ════════════════════════════════════════════════════════════════════════
    # D4. Aggressive humor sparsity: post → firm-period pipeline
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D4] Aggressive humor: post → firm-period sparsity")
    # Post-level: how many companies have ≥1 aggressive post
    if "company_name" in full.columns and "humor_type" in full.columns:
        agg_posts = full[full["humor_type"] == "aggressive"]
        n_companies_with_agg_post = agg_posts["company_name"].nunique()
        n_companies_total = full["company_name"].nunique()
        add("D4_aggressive_sparsity", "aggressive_posts_total",           len(agg_posts))
        add("D4_aggressive_sparsity", "companies_with_ge1_agg_post",      n_companies_with_agg_post,
            f"{pct(n_companies_with_agg_post, n_companies_total):.1f}% of companies")
        add("D4_aggressive_sparsity", "companies_total_in_full_chain",    n_companies_total)
        print(f"  Companies with ≥1 aggressive post: {n_companies_with_agg_post}/{n_companies_total} "
              f"({pct(n_companies_with_agg_post, n_companies_total):.1f}%)")

    # Firm-period level: aggressive_count distribution
    if "aggressive_count" in hypo.columns:
        agg_fp = hypo["aggressive_count"].fillna(0)
        n_fp_total = len(hypo)
        n_fp_zero  = int((agg_fp == 0).sum())
        n_fp_ge1   = int((agg_fp >= 1).sum())
        n_fp_ge3   = int((agg_fp >= 3).sum())
        add("D4_aggressive_sparsity", "firm_period_rows_total",       n_fp_total)
        add("D4_aggressive_sparsity", "firm_period_agg_count_zero",   n_fp_zero,
            f"{pct(n_fp_zero, n_fp_total):.1f}%")
        add("D4_aggressive_sparsity", "firm_period_agg_count_ge1",    n_fp_ge1,
            f"{pct(n_fp_ge1, n_fp_total):.1f}%")
        add("D4_aggressive_sparsity", "firm_period_agg_count_ge3",    n_fp_ge3,
            f"{pct(n_fp_ge3, n_fp_total):.1f}%")
        add("D4_aggressive_sparsity", "firm_period_agg_count_max",    int(agg_fp.max()))
        print(f"  Firm-period: zero aggressive_count={n_fp_zero}/{n_fp_total} "
              f"({pct(n_fp_zero, n_fp_total):.1f}%),  ≥1={n_fp_ge1},  ≥3={n_fp_ge3}")

    # Regression master (primary sample) aggressive check
    primary = master[
        master["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) &
        (master["join_ready_for_CAR_m1_p1"] == True)
    ]
    if "aggressive_humor_usage_intensity" in primary.columns:
        agg_int = pd.to_numeric(primary["aggressive_humor_usage_intensity"], errors="coerce").fillna(0)
        n_pri_nz = int((agg_int > 0).sum())
        add("D4_aggressive_sparsity", "regression_primary_sample_n",       len(primary))
        add("D4_aggressive_sparsity", "regression_primary_agg_nonzero",    n_pri_nz,
            f"{pct(n_pri_nz, len(primary)):.1f}% nonzero — H3 effectively unidentified")
        print(f"  Regression primary sample: {n_pri_nz}/{len(primary)} nonzero aggressive intensity "
              f"({pct(n_pri_nz, len(primary)):.2f}%)")

    # ════════════════════════════════════════════════════════════════════════
    # D5. Firm-period aggregation: signal dilution
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D5] Firm-period aggregation: signal dilution")
    if "total_posts" in hypo.columns and "humor_count" in hypo.columns:
        tp   = hypo["total_posts"].fillna(0)
        hc   = hypo["humor_count"].fillna(0)
        hs   = hypo["humor_share"].fillna(0) if "humor_share" in hypo.columns else pd.Series([0]*len(hypo))

        # Median posts per firm-period
        add("D5_dilution", "median_total_posts_per_firm_period", round(float(tp.median()), 1))
        add("D5_dilution", "p90_total_posts_per_firm_period",    round(float(tp.quantile(0.9)), 1))
        add("D5_dilution", "median_humor_count_per_firm_period", round(float(hc.median()), 1))
        add("D5_dilution", "median_humor_share",                 round(float(hs.median()), 4))
        add("D5_dilution", "p90_humor_share",                    round(float(hs.quantile(0.9)), 4))
        add("D5_dilution", "firm_period_zero_humor_n",           int((hc == 0).sum()),
            f"{pct((hc==0).sum(), len(hypo)):.1f}%")

        # Dilution: posts per firm-period (signal spread thin)
        add("D5_dilution", "dilution_note",
            "humor_share = humor_count / total_posts; high total_posts dilutes signal",
            f"median total_posts={tp.median():.0f}, median humor_count={hc.median():.0f}")

        print(f"  Median total_posts/firm-period: {tp.median():.0f}")
        print(f"  Median humor_count/firm-period: {hc.median():.0f}")
        print(f"  Median humor_share: {hs.median():.4f}")
        print(f"  Firm-periods with zero humor: {int((hc==0).sum())} ({pct((hc==0).sum(),len(hypo)):.1f}%)")

        # Per-company variation in humor_share
        if "company_name" in hypo.columns:
            co_var = hypo.groupby("company_name")["humor_share"].std().fillna(0)
            add("D5_dilution", "median_within_company_humor_share_std",
                round(float(co_var.median()), 4),
                "low within-company variation → limited time-series identification")
            add("D5_dilution", "companies_with_zero_std_humor_share",
                int((co_var == 0).sum()),
                "companies with no within-company humor_share variation across periods")
            print(f"  Median within-company humor_share std: {co_var.median():.4f}")
            print(f"  Companies with constant humor_share across periods: {int((co_var==0).sum())}")

    # ════════════════════════════════════════════════════════════════════════
    # D6. IV variable distribution comparison
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D6] IV variable distributions (regression primary sample)")
    iv_cols = {
        "humor_share":                   "H1a main IV",
        "humor_presence_any":            "H1b binary IV",
        "aggressive_share":              "H2a aggressive",
        "self_enhancing_share":          "H2a self_enhancing",
        "self_defeating_share":          "H2a self_defeating",
        "affiliative_share":             "H2a reference (excluded)",
        "rare_negative_humor_share":     "H2b",
        "aggressive_humor_usage_intensity":    "H3 linear",
        "aggressive_humor_usage_intensity_sq": "H3 quadratic",
        "ambiguity_rate":                "control",
    }
    for col, label in iv_cols.items():
        if col in primary.columns:
            stats = describe_series(primary[col], col)
            for k, v in stats.items():
                add("D6_iv_distribution", k, v, label)
            nz = int((pd.to_numeric(primary[col], errors="coerce").fillna(0) > 0).sum())
            add("D6_iv_distribution", f"{col}_nonzero_n", nz,
                f"{pct(nz, len(primary)):.1f}% nonzero in primary sample")
            print(f"  {col:45s} mean={stats.get(col+'_mean','?'):.4f}  "
                  f"zero={stats.get(col+'_zero_pct','?'):.1f}%  "
                  f"nonzero={nz}")

    # ════════════════════════════════════════════════════════════════════════
    # D7. Zero-inflation / floor effects in primary sample
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D7] Zero-inflation in primary sample IVs")
    zero_inflation = {}
    for col in ["humor_share", "aggressive_share", "self_enhancing_share",
                "self_defeating_share", "rare_negative_humor_share",
                "aggressive_humor_usage_intensity"]:
        if col in primary.columns:
            s = pd.to_numeric(primary[col], errors="coerce").fillna(0)
            n_zero = int((s == 0).sum())
            zero_inflation[col] = pct(n_zero, len(primary))
            add("D7_zero_inflation", f"{col}_zero_pct", zero_inflation[col])
    # Most severely zero-inflated IVs
    sorted_zi = sorted(zero_inflation.items(), key=lambda x: -x[1])
    for col, zpct in sorted_zi:
        print(f"  {col:50s}  {zpct:.1f}% zeros")

    # ════════════════════════════════════════════════════════════════════════
    # D8. Regression sample coverage
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D8] Regression sample coverage")
    # How many unique companies and periods in primary sample
    n_co  = primary["company_name"].nunique() if "company_name" in primary.columns else "?"
    n_per = primary["target_report_year"].nunique() if "target_report_year" in primary.columns else "?"
    # Average posts per firm-period in regression sample
    if "humor_count" in primary.columns and "total_posts" in primary.columns:
        tp_pri = pd.to_numeric(primary["total_posts"], errors="coerce").fillna(0)
        hc_pri = pd.to_numeric(primary["humor_count"], errors="coerce").fillna(0)
        add("D8_sample_coverage", "primary_n_rows",        len(primary))
        add("D8_sample_coverage", "primary_n_companies",   n_co)
        add("D8_sample_coverage", "primary_n_periods",     n_per)
        add("D8_sample_coverage", "primary_median_total_posts",  round(float(tp_pri.median()), 1))
        add("D8_sample_coverage", "primary_median_humor_count",  round(float(hc_pri.median()), 1))
        add("D8_sample_coverage", "primary_median_humor_share",  round(float(pd.to_numeric(primary.get("humor_share", pd.Series([0])), errors="coerce").fillna(0).median()), 4))
        # Rows with humor_count==0 in regression sample
        n_zero_hc = int((hc_pri == 0).sum())
        add("D8_sample_coverage", "primary_zero_humor_count_n", n_zero_hc,
            f"{pct(n_zero_hc, len(primary)):.1f}% — humor IV=0, no signal contribution")
        print(f"  Primary sample: {len(primary)} rows, {n_co} companies, {n_per} periods")
        print(f"  Median total_posts: {tp_pri.median():.0f}  "
              f"median humor_count: {hc_pri.median():.0f}")
        print(f"  Rows with zero humor: {n_zero_hc} ({pct(n_zero_hc, len(primary)):.1f}%)")

    # ════════════════════════════════════════════════════════════════════════
    # D9. Classifier confidence: ambiguous zone analysis
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D9] Classifier confidence distribution")
    if "ml_humor_probability" in full.columns:
        probs = full["ml_humor_probability"].dropna()
        # Near-boundary: posts within 0.05 of threshold (assumed 0.5)
        near_boundary = ((probs >= 0.45) & (probs < 0.55)).sum()
        add("D9_classifier_confidence", "total_posts_with_prob_score", len(probs))
        add("D9_classifier_confidence", "near_boundary_0.45_0.55_n", int(near_boundary),
            f"{pct(near_boundary, len(probs)):.1f}% near decision boundary")
        add("D9_classifier_confidence", "high_confidence_ge0.80_n",
            int((probs >= 0.80).sum()),
            f"{pct((probs >= 0.80).sum(), len(probs)):.1f}%")
        add("D9_classifier_confidence", "low_confidence_le0.30_n",
            int((probs <= 0.30).sum()),
            f"{pct((probs <= 0.30).sum(), len(probs)):.1f}%")

        # Ambiguous posts: what is their prob distribution?
        amb_probs = full.loc[full["humor_presence"] == "ambiguous", "ml_humor_probability"].dropna()
        add("D9_classifier_confidence", "ambiguous_posts_with_prob", len(amb_probs))
        if len(amb_probs) > 0:
            add("D9_classifier_confidence", "ambiguous_prob_mean",   round(float(amb_probs.mean()), 4))
            add("D9_classifier_confidence", "ambiguous_prob_median", round(float(amb_probs.median()), 4))
            add("D9_classifier_confidence", "ambiguous_prob_std",    round(float(amb_probs.std()), 4))
            print(f"  Ambiguous posts prob: mean={amb_probs.mean():.3f}  "
                  f"median={amb_probs.median():.3f}  std={amb_probs.std():.3f}")
            print(f"  Near-boundary [0.45,0.55): {near_boundary:,} ({pct(near_boundary, len(probs)):.1f}%)")

    # ════════════════════════════════════════════════════════════════════════
    # D10. Cross-variable correlations (multicollinearity)
    # ════════════════════════════════════════════════════════════════════════
    print("\n[D10] Cross-variable correlation in primary sample")
    corr_cols = [c for c in [
        "humor_share", "humor_presence_any", "log_humor_count",
        "aggressive_share", "self_enhancing_share", "affiliative_share",
        "self_defeating_share", "ambiguity_rate", "source_x_handle_count",
        "aggressive_humor_usage_intensity",
    ] if c in primary.columns]
    corr_data = primary[corr_cols].apply(pd.to_numeric, errors="coerce")
    corr_matrix = corr_data.corr()

    high_corr_pairs = []
    for i, c1 in enumerate(corr_cols):
        for c2 in corr_cols[i+1:]:
            r = corr_matrix.loc[c1, c2] if c1 in corr_matrix.index and c2 in corr_matrix.columns else np.nan
            if not np.isnan(r):
                detail_rows.append({"section": "D10", "var1": c1, "var2": c2, "pearson_r": round(r, 4)})
                if abs(r) >= 0.50:
                    high_corr_pairs.append((c1, c2, round(r, 4)))
                    add("D10_correlation", f"high_corr_{c1}_x_{c2}", round(r, 4),
                        "r≥0.50 — potential multicollinearity")

    if not high_corr_pairs:
        add("D10_correlation", "high_correlation_pairs_n", 0, "No r≥0.50 pairs")
        print("  No high-correlation pairs (r≥0.50)")
    else:
        for c1, c2, r in high_corr_pairs:
            print(f"  {c1} × {c2}: r={r:+.3f}")

    # humor_share vs log_humor_count correlation (volume confound)
    if "humor_share" in primary.columns and "log_humor_count" in primary.columns:
        r_hs_lhc = corr_data["humor_share"].corr(corr_data["log_humor_count"])
        add("D10_correlation", "humor_share_x_log_humor_count_r", round(float(r_hs_lhc), 4),
            "share and count log both used as IV+control — check orthogonality")
        print(f"  humor_share × log_humor_count: r={r_hs_lhc:+.4f}")

    # ════════════════════════════════════════════════════════════════════════
    # Summary diagnosis
    # ════════════════════════════════════════════════════════════════════════
    print("\n=== DIAGNOSTIC SUMMARY ===")
    summary = {
        "ambiguous_post_rate_pct":         pct(n_ambiguous, n_total),
        "aggressive_post_rate_of_humor_pct": pct(type_map["aggressive"], n_humor),
        "aggressive_post_rate_of_all_pct":  pct(type_map["aggressive"], n_total),
    }

    # Primary bottlenecks
    bottlenecks = []
    if pct(n_ambiguous, n_total) > 30:
        bottlenecks.append(
            f"AMBIGUITY CEILING: {pct(n_ambiguous, n_total):.1f}% of posts unclassified (ambiguous). "
            "Effective humor-classified corpus is severely reduced."
        )
    if pct(type_map["aggressive"], n_humor) < 5:
        bottlenecks.append(
            f"AGGRESSIVE SPARSITY: Only {pct(type_map['aggressive'], n_humor):.2f}% of humor posts "
            f"({type_map['aggressive']} posts) classified as aggressive. "
            "H2a/H3 focal IVs are near-constant at zero. Regression effectively unidentified."
        )
    # zero_inflation check
    humor_share_zero = zero_inflation.get("humor_share", 0)
    if humor_share_zero > 20:
        bottlenecks.append(
            f"ZERO INFLATION (humor_share): {humor_share_zero:.1f}% of primary sample rows "
            "have humor_share=0. H1 IV has low effective variation."
        )
    agg_share_zero = zero_inflation.get("aggressive_share", 0)
    if agg_share_zero > 90:
        bottlenecks.append(
            f"EXTREME ZERO INFLATION (aggressive_share): {agg_share_zero:.1f}% zero. "
            "Share is not a meaningful IV at this sparsity level."
        )

    for i, b in enumerate(bottlenecks, 1):
        add("SUMMARY_bottleneck", f"bottleneck_{i}", b)
        print(f"  BOTTLENECK {i}: {b}")

    add("SUMMARY_flags", "raw_data_modified",     False)
    add("SUMMARY_flags", "car_calculation_run",   False)
    add("SUMMARY_flags", "regression_run",         False)
    add("SUMMARY_flags", "causal_claim_made",      False)
    add("SUMMARY_flags", "tobins_q_initiated",     False)
    add("SUMMARY_flags", "brand_equity_claimed",   False)

    # ── Write outputs ─────────────────────────────────────────────────────
    args.out_diag.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(diag_rows).to_csv(args.out_diag, index=False, encoding="utf-8-sig")
    print(f"\n  Diagnostic CSV  → {args.out_diag}  ({len(diag_rows)} metrics)")

    if detail_rows:
        pd.DataFrame(detail_rows).to_csv(args.out_detail, index=False, encoding="utf-8-sig")
        print(f"  Detail CSV      → {args.out_detail}  ({len(detail_rows)} rows)")

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "Gate 4 — Humor IV Measurement Diagnostic",
        "script": "scripts/run_humor_iv_measurement_diagnostic.py",
        "inputs": {
            "full_chain_master_posts":        n_total,
            "hypothesis_variables_rows":      len(hypo),
            "regression_master_rows":         len(master),
            "primary_sample_rows":            len(primary),
        },
        "D1_post_level": {
            "humor_posts":     n_humor,
            "non_humor_posts": n_nonhumor,
            "ambiguous_posts": n_ambiguous,
            "ambiguous_rate_pct": pct(n_ambiguous, n_total),
        },
        "D3_type_distribution_post_level": type_map,
        "D3_aggressive_rate_of_humor_pct": pct(type_map["aggressive"], n_humor),
        "D3_aggressive_rate_of_all_posts_pct": pct(type_map["aggressive"], n_total),
        "D4_firm_period_aggressive_zero_pct": pct(int((hypo["aggressive_count"].fillna(0) == 0).sum()), len(hypo)) if "aggressive_count" in hypo.columns else None,
        "D4_regression_primary_aggressive_nonzero": int(n_pri_nz) if "n_pri_nz" in dir() else None,
        "D7_humor_share_zero_inflation_pct": zero_inflation.get("humor_share"),
        "D7_aggressive_share_zero_inflation_pct": zero_inflation.get("aggressive_share"),
        "bottlenecks": bottlenecks,
        "n_bottlenecks_identified": len(bottlenecks),
        # Constraint flags
        "raw_data_modified":   False,
        "car_calculation_run": False,
        "regression_run":      False,
        "causal_claim_made":   False,
        "tobins_q_initiated":  False,
        "brand_equity_claimed": False,
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest        → {args.out_manifest}")
    print(f"\n  Total diagnostic metrics: {len(diag_rows)}")
    print(f"  Bottlenecks identified:   {len(bottlenecks)}")


if __name__ == "__main__":
    main()
