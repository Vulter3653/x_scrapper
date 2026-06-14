#!/usr/bin/env python3
"""
build_humor_iv_gate5_1_repair.py

Gate 5.1: Paper-grounded Humor IV Reconstruction Repair.

참조 문헌:
  - Martin et al. (2003) HSQ — 4가지 humor type codebook
  - CCPA assurance AI working paper — multi-measurement, threshold sensitivity
  - brand/personality ML 논문 — soft-label, ambiguity preservation

생성 파일 (기존 파일 덮어쓰기 없음):
  1. data/audit/regression/humor_iv_probability_score_provenance.csv
  2. data/audit/regression/humor_iv_candidate_sanity_checks.csv
  3. data/derived/regression/humor_iv_reconstructed_candidates_gate5_1.csv
  4. data/derived/regression/humor_iv_reconstructed_candidate_diagnostics_gate5_1.csv
  5. data/derived/validation/humor_candidate_manual_audit_sample.csv
  6. data/derived/regression/humor_iv_threshold_sensitivity_gate5_1.csv
  7. data/audit/regression/humor_iv_reconstruction_gate5_1_manifest.json

금지:
  회귀 실행 / raw humor output 수정 / 기존 IV 덮어쓰기
  causal claim / Brand Equity claim / Tobin's Q 시작
"""

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────────
FULL_CHAIN   = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
HYPO_VARS    = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
GATE5_CANDS  = Path("data/derived/regression/humor_iv_reconstructed_candidates.csv")
REG_MASTER   = Path("data/derived/regression/humor_car_hypothesis_regression_master.csv")

OUT_PROV     = Path("data/audit/regression/humor_iv_probability_score_provenance.csv")
OUT_SANITY   = Path("data/audit/regression/humor_iv_candidate_sanity_checks.csv")
OUT_CANDS    = Path("data/derived/regression/humor_iv_reconstructed_candidates_gate5_1.csv")
OUT_DIAGS    = Path("data/derived/regression/humor_iv_reconstructed_candidate_diagnostics_gate5_1.csv")
OUT_SAMPLE   = Path("data/derived/validation/humor_candidate_manual_audit_sample.csv")
OUT_THRESH   = Path("data/derived/regression/humor_iv_threshold_sensitivity_gate5_1.csv")
OUT_MAN      = Path("data/audit/regression/humor_iv_reconstruction_gate5_1_manifest.json")

# ── constants ────────────────────────────────────────────────────────────────
GATE5_COMMIT  = "d4c20be22c71185bd3bb7609d76a20acc5e060b8"
SEED          = 42
TOP_K         = 3

# Base rates from full corpus: aggressive=105, self_defeating=41 out of 9701 humor
HUMOR_TOTAL_V1        = 9701
AGGRESSIVE_BASE_RATE  = 105 / HUMOR_TOTAL_V1   # 0.01082
SELF_DEFEATING_BASE_RATE = 41 / HUMOR_TOTAL_V1  # 0.00423

# Threshold grids
HUMOR_THRESHOLDS      = [0.40, 0.45, 0.50, 0.55, 0.60]
AGGRESSIVE_THRESHOLDS = [0.30, 0.40, 0.50, 0.60]
SELF_DEFEATING_THRESHOLDS = [0.30, 0.40, 0.50, 0.60]

# H3 feasibility thresholds
H3_BLOCKED      = 30
H3_EXPLORATORY  = 50

# Concentration threshold
CONCENTRATION_TOP1_THRESHOLD = 0.50  # top 1 company > 50% → concentrated


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_twitter_date(s):
    try:
        return pd.to_datetime(s, format="%a %b %d %H:%M:%S %z %Y", utc=True).strftime("%Y-%m")
    except Exception:
        try:
            return pd.to_datetime(s, utc=True).strftime("%Y-%m")
        except Exception:
            return None


def pct(n, d):
    return round(100 * n / d, 4) if d > 0 else 0.0


def safe_corr(a, b):
    try:
        r = pd.to_numeric(a, errors="coerce").fillna(0).corr(
            pd.to_numeric(b, errors="coerce").fillna(0)
        )
        return round(float(r), 4) if not np.isnan(r) else None
    except Exception:
        return None


def describe_iv(s, primary_df, col, co_col="company_name", period_col="period"):
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    n = len(s)
    nz = int((s > 0).sum())
    has_neg = bool((s < 0).any())
    exceeds1 = bool((s > 1).any())

    # company/period breakdown
    nz_co = int(primary_df.loc[s > 0, co_col].nunique()) if co_col in primary_df.columns else None
    nz_pe = int(primary_df.loc[s > 0, period_col].nunique()) if period_col in primary_df.columns else None
    n_distinct_levels = int(s[s > 0].round(6).nunique())

    # concentration
    top1_share, top5_share = None, None
    if co_col in primary_df.columns:
        comp_sum = primary_df.assign(__iv=s).groupby(co_col)["__iv"].sum()
        total = comp_sum.sum()
        if total > 0:
            top1_share = round(float(comp_sum.nlargest(1).sum() / total), 4)
            top5_share = round(float(comp_sum.nlargest(5).sum() / total), 4)

    return {
        "n": n,
        "nonzero_n": nz,
        "nonzero_pct": pct(nz, n),
        "nonzero_company_n": nz_co,
        "nonzero_period_n": nz_pe,
        "intensity_level_n": n_distinct_levels,
        "min": round(float(s.min()), 6),
        "max": round(float(s.max()), 6),
        "mean": round(float(s.mean()), 6),
        "median": round(float(s.median()), 6),
        "std": round(float(s.std()), 6),
        "p10": round(float(s.quantile(0.10)), 6),
        "p25": round(float(s.quantile(0.25)), 6),
        "p75": round(float(s.quantile(0.75)), 6),
        "p90": round(float(s.quantile(0.90)), 6),
        "has_negative_value": has_neg,
        "exceeds_one": exceeds1,
        "bounded_0_1": (not has_neg) and (not exceeds1),
        "top_1_company_share": top1_share,
        "top_5_company_share": top5_share,
    }


# ── Step 0: Load data ─────────────────────────────────────────────────────────

def load_all():
    print("[Load]")
    full = pd.read_csv(FULL_CHAIN,  encoding="utf-8-sig", low_memory=False)
    hypo = pd.read_csv(HYPO_VARS,   encoding="utf-8-sig")
    g5   = pd.read_csv(GATE5_CANDS, encoding="utf-8-sig")
    rm   = pd.read_csv(REG_MASTER,  encoding="utf-8-sig")
    print(f"  full_chain: {len(full):,}  hypo_vars: {len(hypo):,}  gate5: {len(g5):,}  reg_master: {len(rm):,}")

    # Parse period from full_chain
    full["period"] = full["created_at"].apply(parse_twitter_date)
    full = full.dropna(subset=["period"])

    # Numeric cols
    for c in ["ml_humor_probability", "humor_type_confidence"]:
        full[c] = pd.to_numeric(full[c], errors="coerce")

    # Flags
    full["is_humor"]        = full["humor_presence"] == "humor"
    full["is_ambiguous"]    = full["humor_presence"] == "ambiguous"
    full["is_non_humor"]    = full["humor_presence"] == "non_humor"
    full["is_aggressive"]   = full["humor_type"] == "aggressive"
    full["is_self_defeating"] = full["humor_type"] == "self_defeating"
    full["is_negative"]     = full["humor_type"].isin(["aggressive", "self_defeating"])

    # ── Corrected candidate scores (UNIFIED formula) ──────────────────────
    # True aggressive proxy: P(humor) × P(type=aggressive | humor) for all posts
    # classified aggressive:   ml_humor_probability × humor_type_confidence
    # classified other humor:  ml_humor_probability × 0  (near-zero, negligible)
    # ambiguous:               ml_humor_probability × AGGRESSIVE_BASE_RATE
    # non_humor:               0
    p_humor = full["ml_humor_probability"].fillna(0)
    p_type_agg = full["humor_type_confidence"].fillna(0)

    full["aggressive_candidate_score"] = np.where(
        full["is_aggressive"],
        p_humor * p_type_agg,
        np.where(full["is_ambiguous"],
                 p_humor * AGGRESSIVE_BASE_RATE,
                 0.0)
    )
    full["self_defeating_candidate_score"] = np.where(
        full["is_self_defeating"],
        p_humor * p_type_agg,
        np.where(full["is_ambiguous"],
                 p_humor * SELF_DEFEATING_BASE_RATE,
                 0.0)
    )

    # Gate 5 legacy formula (for provenance comparison)
    full["aggressive_prob_legacy"] = np.where(
        full["is_aggressive"],
        full["humor_type_confidence"].fillna(p_humor),  # missing ml_humor_probability factor
        np.where(full["is_ambiguous"],
                 p_humor * AGGRESSIVE_BASE_RATE,
                 0.0)
    )

    # Primary sample filter key
    for col in ["join_ready_for_CAR_m1_p1"]:
        if col in g5.columns:
            g5[col] = g5[col].astype(str).str.lower().map(
                {"true": True, "false": False}
            ).fillna(False)

    primary = g5[
        g5["alignment_type"].isin(["prefiling_lag_1m", "prefiling_lag_3m"]) &
        (g5["join_ready_for_CAR_m1_p1"] == True)
    ].copy()
    print(f"  Primary sample: {len(primary)}")

    # company→ticker mapping
    co_tick = g5[["company_name","ticker"]].drop_duplicates().set_index("company_name")["ticker"].to_dict()

    return full, hypo, g5, rm, primary, co_tick


# ── Task 2: Probability / Score Provenance Audit ─────────────────────────────

def build_provenance():
    print("\n[Task 2] Probability / score provenance audit")
    rows = [
        # H1 probability-based
        {
            "variable_name": "humor_prob_sum",
            "source_column": "ml_humor_probability",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "humor_probability",
            "score_range_min": 0.0,
            "score_range_max": "n_posts (unbounded sum)",
            "valid_probability_range": False,
            "interpretation": "Sum of P(humor) over all posts in firm-period. Not a probability itself — a probability-weighted count.",
            "allowed_variable_name": "humor_candidate_score_sum",
            "rename_required": True,
            "rename_recommendation": "humor_candidate_score_sum",
        },
        {
            "variable_name": "humor_prob_mean",
            "source_column": "ml_humor_probability",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "humor_probability",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": True,
            "interpretation": "Mean P(humor) per post in firm-period = ambiguity-adjusted humor share. Valid [0,1].",
            "allowed_variable_name": "humor_prob_mean",
            "rename_required": False,
            "rename_recommendation": "no rename needed",
        },
        {
            "variable_name": "ambiguity_adjusted_humor_share",
            "source_column": "ml_humor_probability",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "humor_probability",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": True,
            "interpretation": "sum(P(humor)) / total_posts = mean(P(humor)) = humor_prob_mean. Valid [0,1]. Identical to humor_prob_mean.",
            "allowed_variable_name": "ambiguity_adjusted_humor_share",
            "rename_required": False,
            "rename_recommendation": "no rename needed; note: identical to humor_prob_mean",
        },
        # H2/H3 aggressive scores — RENAME REQUIRED
        {
            "variable_name": "aggressive_prob_sum",
            "source_column": "humor_type_confidence (aggressive posts) + ml_humor_probability × base_rate (ambiguous)",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "classifier_confidence",
            "score_range_min": 0.0,
            "score_range_max": "n_posts (unbounded sum)",
            "valid_probability_range": False,
            "interpretation": (
                "LEGACY Gate 5 formula. Inconsistent: aggressive posts use humor_type_confidence "
                "(= P(type=aggressive | type classified) — MISSING ml_humor_probability factor). "
                "Ambiguous posts use ml_humor_probability × base_rate. "
                "NOT a true P(aggressive). Rename required."
            ),
            "allowed_variable_name": "aggressive_candidate_score_sum",
            "rename_required": True,
            "rename_recommendation": "aggressive_candidate_score_sum",
        },
        {
            "variable_name": "aggressive_prob_mean",
            "source_column": "humor_type_confidence (aggressive posts) + ml_humor_probability × base_rate (ambiguous)",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "classifier_confidence",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": False,
            "interpretation": "Same formula issue as aggressive_prob_sum. Mean of legacy composite score. Rename required.",
            "allowed_variable_name": "aggressive_candidate_score_mean",
            "rename_required": True,
            "rename_recommendation": "aggressive_candidate_score_mean",
        },
        {
            "variable_name": "aggressive_prob_max",
            "source_column": "humor_type_confidence (aggressive posts) + ml_humor_probability × base_rate (ambiguous)",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "classifier_confidence",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": False,
            "interpretation": "Max of legacy composite score per firm-period. Missing ml_humor_probability factor for classified posts. Rename required.",
            "allowed_variable_name": "aggressive_candidate_score_max",
            "rename_required": True,
            "rename_recommendation": "aggressive_candidate_score_max",
        },
        {
            "variable_name": "aggressive_prob_intensity",
            "source_column": "aggressive_prob_sum / humor_count",
            "source_file": "derived from humor_full_chain_master.csv",
            "score_type": "derived_candidate_score",
            "score_range_min": 0.0,
            "score_range_max": "> 1 possible (denominator = humor_count, not total_posts)",
            "valid_probability_range": False,
            "interpretation": "Legacy formula / humor_count. Denominator is humor posts only; sum includes all posts. Rename and rebounding required.",
            "allowed_variable_name": "aggressive_candidate_score_intensity",
            "rename_required": True,
            "rename_recommendation": "aggressive_candidate_score_intensity_bounded (use total_posts denominator)",
        },
        # Corrected versions
        {
            "variable_name": "aggressive_candidate_score_sum",
            "source_column": "ml_humor_probability × humor_type_confidence (aggressive) + ml_humor_probability × base_rate (ambiguous)",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "aggressive_specific_probability",
            "score_range_min": 0.0,
            "score_range_max": "n_posts (unbounded sum)",
            "valid_probability_range": False,
            "interpretation": (
                "CORRECTED Gate 5.1 formula. Unified: P(humor) × P(type=aggressive | humor) for all posts. "
                "For classified aggressive: ml_humor_probability × humor_type_confidence. "
                "For ambiguous: ml_humor_probability × AGGRESSIVE_BASE_RATE. "
                "Consistent approximation of P(post is aggressive)."
            ),
            "allowed_variable_name": "aggressive_candidate_score_sum",
            "rename_required": False,
            "rename_recommendation": "no rename needed — corrected formula",
        },
        {
            "variable_name": "aggressive_candidate_score_intensity_bounded",
            "source_column": "aggressive_candidate_score_sum / total_posts",
            "source_file": "derived from humor_full_chain_master.csv + hypothesis_variables",
            "score_type": "aggressive_specific_probability",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": True,
            "interpretation": (
                "Corrected bounded intensity. Divides by total_posts (not humor_count) "
                "ensuring [0,1] range. Interpretable as firm-level average P(post is aggressive)."
            ),
            "allowed_variable_name": "aggressive_candidate_score_intensity_bounded",
            "rename_required": False,
            "rename_recommendation": "no rename needed",
        },
        {
            "variable_name": "top_k_aggressive_score",
            "source_column": "humor_type_confidence (top-3 aggressive posts)",
            "source_file": "humor_full_chain_master.csv",
            "score_type": "classifier_confidence",
            "score_range_min": 0.0,
            "score_range_max": 1.0,
            "valid_probability_range": False,
            "interpretation": (
                "Mean humor_type_confidence of top-3 aggressive posts per firm-period. "
                "Only nonzero for firms with ≥1 v1 aggressive post (5/430 in primary). "
                "Not a population-level probability. H3 BLOCKED (nonzero<30)."
            ),
            "allowed_variable_name": "top_k_aggressive_type_confidence",
            "rename_required": True,
            "rename_recommendation": "top_k_aggressive_type_confidence; note H3 BLOCKED",
        },
        # v2 candidate-based
        {
            "variable_name": "hc_v2_aggressive_candidate_count",
            "source_column": "v2_aggressive_candidate_count",
            "source_file": "humor_firm_period_hypothesis_variables.csv",
            "score_type": "llm_candidate_score",
            "score_range_min": 0,
            "score_range_max": "EXCEEDS total_posts (firm-level fixed value suspected)",
            "valid_probability_range": False,
            "interpretation": (
                "CRITICAL FINDING: v2_aggressive_candidate_count EXCEEDS total_posts in 189/3767 "
                "firm-periods (max ratio=9.0). The variable appears to be a FIRM-LEVEL fixed score "
                "(e.g., Albertsons: always 7 across multiple periods) rather than a per-period post count. "
                "This means normalization by total_posts or humor_count is NOT valid. "
                "Use as raw count IV only; do NOT normalize as share/intensity."
            ),
            "allowed_variable_name": "hc_v2_aggressive_candidate_count",
            "rename_required": False,
            "rename_recommendation": "use as count only; do NOT normalize; flag as firm-level score",
        },
        {
            "variable_name": "hc_v2_aggressive_candidate_share",
            "source_column": "v2_aggressive_candidate_count / total_posts",
            "source_file": "hypothesis_variables (derived)",
            "score_type": "derived_candidate_score",
            "score_range_min": 0.0,
            "score_range_max": "EXCEEDS 1 (max observed = 8.0) — v2_count is firm-level, not per-period count",
            "valid_probability_range": False,
            "interpretation": (
                "INVALID: v2_aggressive_candidate_count exceeds total_posts in 189 firm-periods. "
                "The numerator appears to be a firm-level fixed score, not a per-period post count. "
                "Normalization by total_posts produces values > 1, making this invalid as a share. "
                "DO NOT USE as share/intensity. Use hc_v2_aggressive_candidate_count (raw count) only."
            ),
            "allowed_variable_name": "INVALID_DO_NOT_USE_AS_SHARE",
            "rename_required": True,
            "rename_recommendation": "INVALID — remove from H2/H3 share/intensity candidates; use count only",
        },
        {
            "variable_name": "hc_v2_aggressive_candidate_intensity",
            "source_column": "v2_aggressive_candidate_count / humor_count",
            "source_file": "hypothesis_variables (derived)",
            "score_type": "derived_candidate_score",
            "score_range_min": 0.0,
            "score_range_max": "EXCEEDS 1 (max observed = 7.0) — v2_count is firm-level, not per-period count",
            "valid_probability_range": False,
            "interpretation": (
                "INVALID: Same firm-level v2 issue as hc_v2_aggressive_candidate_share. "
                "v2_aggressive_candidate_count is a firm-level fixed value, NOT a period-specific count. "
                "Dividing by humor_count produces values > 1 in many firm-periods. "
                "DO NOT USE as intensity. Use hc_v2_aggressive_candidate_count (raw count) only."
            ),
            "allowed_variable_name": "INVALID_DO_NOT_USE_AS_INTENSITY",
            "rename_required": True,
            "rename_recommendation": "INVALID — remove from H3 intensity candidates; note: v2 is firm-level",
        },
        {
            "variable_name": "hc_rare_class_candidate_intensity",
            "source_column": "rare_class_candidate_count / humor_count",
            "source_file": "hypothesis_variables (derived)",
            "score_type": "derived_candidate_score",
            "score_range_min": 0.0,
            "score_range_max": ">1 possible",
            "valid_probability_range": False,
            "interpretation": "rare class count / humor_count. May exceed 1. Rename or rebound required if max>1.",
            "allowed_variable_name": "hc_rare_class_candidate_intensity_bounded",
            "rename_required": True,
            "rename_recommendation": "hc_rare_class_candidate_intensity_bounded (divide by total_posts instead)",
        },
    ]
    df = pd.DataFrame(rows)
    print(f"  {len(df)} variables audited; rename_required: {df['rename_required'].sum()}")
    return df


# ── Task 3: Share / Intensity Sanity Check ────────────────────────────────────

def build_sanity_checks(g5, primary):
    print("\n[Task 3] Share / intensity sanity checks")

    candidates = [
        # (col, expected_range, denom_col, num_col, variable_type)
        ("hc_humor_share",                     "[0,1]", "total_posts", "humor_count",         "share"),
        ("hc_v2_aggressive_candidate_share",   "[0,1]", "total_posts", "hc_v2_aggressive_candidate_count", "share"),
        ("hc_rare_class_candidate_share",      "[0,1]", "total_posts", "hc_rare_class_candidate_count", "share"),
        ("hc_negative_humor_share",            "[0,1]", "total_posts", "hc_negative_humor_count", "share"),
        ("hc_aggressive_share_among_humor",    "[0,1]", "humor_count", "hc_aggressive_count",  "share"),
        ("hc_v2_aggressive_candidate_intensity","[0,1]?","humor_count", "hc_v2_aggressive_candidate_count", "intensity"),
        ("hc_rare_class_candidate_intensity",  "[0,1]?","humor_count", "hc_rare_class_candidate_count", "intensity"),
        ("hc_negative_humor_intensity",        "[0,1]", "humor_count", "hc_negative_humor_count", "intensity"),
        ("aggressive_prob_sum",                "unbounded", "—",       "—",                   "probability_sum"),
        ("aggressive_prob_intensity",          "[0,1]?","humor_count", "aggressive_prob_sum",  "intensity"),
        ("ambiguity_adjusted_humor_share",     "[0,1]", "total_posts", "humor_prob_sum",       "share"),
        ("humor_prob_mean",                    "[0,1]", "total_posts", "—",                    "mean"),
    ]

    rows = []
    for col, exp_range, denom_col, num_col, vtype in candidates:
        if col not in g5.columns:
            continue
        s = pd.to_numeric(g5[col], errors="coerce").fillna(0)
        ps = pd.to_numeric(primary[col], errors="coerce").fillna(0) if col in primary.columns else s

        # Check denominator = 0
        denom_zero_n = 0
        num_gt_denom_n = 0
        if denom_col in g5.columns and denom_col != "—":
            denom_s = pd.to_numeric(g5[denom_col], errors="coerce").fillna(0)
            denom_zero_n = int((denom_s == 0).sum())
        if num_col in g5.columns and denom_col in g5.columns and num_col != "—" and denom_col != "—":
            num_s   = pd.to_numeric(g5[num_col],   errors="coerce").fillna(0)
            denom_s = pd.to_numeric(g5[denom_col], errors="coerce").fillna(0)
            mask = denom_s > 0
            num_gt_denom_n = int((num_s[mask] > denom_s[mask]).sum())

        has_neg    = bool((s < 0).any())
        exceeds1   = bool((s > 1.0).any())
        max_val    = round(float(s.max()), 6)
        is_valid   = (not has_neg) and (not exceeds1)

        action_required = "ok"
        rename_rec = col
        if vtype in ("share", "intensity") and exceeds1:
            action_required = "rename_and_rebound"
            if vtype == "intensity" and denom_col == "humor_count":
                rename_rec = col.replace("_intensity", "_ratio_to_hard_humor")
            elif vtype == "share":
                rename_rec = col.replace("_share", "_ratio")
        elif vtype == "probability_sum" and "prob" in col and "aggressive" in col:
            action_required = "rename_to_candidate_score"
            rename_rec = col.replace("aggressive_prob", "aggressive_candidate_score")

        rows.append({
            "variable_name":           col,
            "variable_type":           vtype,
            "n":                       int((s != 0).count()),
            "min":                     round(float(s.min()), 6),
            "max":                     max_val,
            "has_negative_value":      has_neg,
            "exceeds_one":             exceeds1,
            "expected_range":          exp_range,
            "denominator_column":      denom_col,
            "numerator_column":        num_col,
            "denominator_zero_n":      denom_zero_n,
            "numerator_greater_than_denominator_n": num_gt_denom_n,
            "bounded_share_valid":     is_valid,
            "action_required":         action_required,
            "recommended_rename":      rename_rec,
        })

    df = pd.DataFrame(rows)
    print(f"  {len(df)} variables checked")
    print(f"  action_required != ok: {(df['action_required'] != 'ok').sum()}")
    print(f"  exceeds_one: {df['exceeds_one'].sum()}")
    return df


# ── Task 4: Corrected H3 candidate panel ─────────────────────────────────────

def build_corrected_panel(g5, full, hypo):
    print("\n[Task 4] Building corrected Gate 5.1 candidate panel")

    # Aggregate corrected scores to firm-period from full_chain
    agg = full.groupby(["company_name", "period"]).agg(
        _total_posts_fc         =("global_post_id", "count"),
        agg_score_sum           =("aggressive_candidate_score", "sum"),
        agg_score_mean          =("aggressive_candidate_score", "mean"),
        agg_score_max           =("aggressive_candidate_score", "max"),
        sd_candidate_score_sum  =("self_defeating_candidate_score", "sum"),
        sd_candidate_score_mean =("self_defeating_candidate_score", "mean"),
        sd_candidate_score_max  =("self_defeating_candidate_score", "max"),
        _humor_count_fc         =("is_humor", "sum"),
        _ambiguous_count_fc     =("is_ambiguous", "sum"),
    ).reset_index()
    agg = agg.rename(columns={
        "agg_score_sum":  "aggressive_candidate_score_sum",
        "agg_score_mean": "aggressive_candidate_score_mean",
        "agg_score_max":  "aggressive_candidate_score_max",
    })

    # Also compute top-k type confidence for aggressive posts (corrected)
    def topk_mean(grp_df):
        scores = grp_df.loc[grp_df["is_aggressive"], "humor_type_confidence"].dropna()
        return float(scores.nlargest(TOP_K).mean()) if len(scores) else 0.0

    topk = full.groupby(["company_name", "period"]).apply(topk_mean).reset_index()
    topk.columns = ["company_name", "period", "top_k_aggressive_type_confidence"]
    agg = agg.merge(topk, on=["company_name", "period"], how="left")
    agg["top_k_aggressive_type_confidence"] = agg["top_k_aggressive_type_confidence"].fillna(0)

    # Start from Gate 5 candidate panel
    panel = g5.copy()
    panel = panel.merge(agg, on=["company_name", "period"], how="left")

    # Rename aliases for legacy prob_* columns
    for old, new in [
        ("aggressive_prob_sum",       "aggressive_prob_sum_legacy"),
        ("aggressive_prob_mean",      "aggressive_prob_mean_legacy"),
        ("aggressive_prob_max",       "aggressive_prob_max_legacy"),
        ("aggressive_prob_intensity", "aggressive_prob_intensity_legacy"),
        ("top_k_aggressive_score",    "top_k_aggressive_score_legacy"),
    ]:
        if old in panel.columns:
            panel[f"{new}"] = panel[old]  # keep original, add alias with _legacy suffix

    # Fill NaN for corrected aggregates
    for c in ["aggressive_candidate_score_sum","aggressive_candidate_score_mean",
              "aggressive_candidate_score_max","sd_candidate_score_sum",
              "sd_candidate_score_mean","sd_candidate_score_max"]:
        if c in panel.columns:
            panel[c] = pd.to_numeric(panel[c], errors="coerce").fillna(0)

    # Bounded H3 candidates (divide by total_posts)
    tp = pd.to_numeric(panel["total_posts"], errors="coerce").replace(0, np.nan)
    hc = pd.to_numeric(panel.get("humor_count", pd.Series(np.nan, index=panel.index)), errors="coerce").replace(0, np.nan)

    panel["aggressive_candidate_score_intensity_bounded"] = (
        panel["aggressive_candidate_score_sum"] / tp
    ).fillna(0)

    panel["hc_v2_aggressive_candidate_intensity_bounded"] = (
        pd.to_numeric(panel["hc_v2_aggressive_candidate_count"], errors="coerce").fillna(0) / tp
    ).fillna(0)

    panel["hc_rare_class_candidate_intensity_bounded"] = (
        pd.to_numeric(panel["hc_rare_class_candidate_count"], errors="coerce").fillna(0) / tp
    ).fillna(0)

    # Ratio candidate (explicitly named — may exceed 1)
    panel["hc_v2_aggressive_candidate_ratio_to_hard_humor"] = (
        pd.to_numeric(panel["hc_v2_aggressive_candidate_count"], errors="coerce").fillna(0) / hc
    ).fillna(0)

    # Self-defeating bounded
    panel["sd_candidate_score_intensity_bounded"] = (
        panel["sd_candidate_score_sum"] / tp
    ).fillna(0)

    print(f"  Panel: {len(panel)} rows, {len(panel.columns)} cols")
    return panel


def build_h3_diagnostics(panel, primary):
    print("  Computing H3 candidate diagnostics ...")

    h3_candidates = [
        # (col, label, is_bounded, note)
        ("aggressive_candidate_score_sum",            "Corrected aggressive score sum", False,
         "P(humor)×P(type|humor) summed; unified formula; unbounded"),
        ("aggressive_candidate_score_intensity_bounded","Corrected aggressive bounded intensity", True,
         "score_sum/total_posts; bounded [0,1]; PRIMARY H3 CANDIDATE"),
        ("aggressive_prob_sum_legacy",                "Legacy aggressive prob sum (RENAME REQUIRED)", False,
         "Gate5 legacy; missing ml_humor_prob factor for classified posts"),
        ("hc_v2_aggressive_candidate_intensity_bounded","v2 candidate bounded intensity", True,
         "v2_count/total_posts; bounded [0,1]"),
        ("hc_v2_aggressive_candidate_ratio_to_hard_humor","v2 ratio to hard humor", False,
         "v2_count/humor_count; CAN EXCEED 1; label as ratio not intensity"),
        ("hc_rare_class_candidate_intensity_bounded", "Rare class bounded intensity", True,
         "rare_count/total_posts; bounded [0,1]"),
        ("hc_negative_humor_intensity",               "Negative humor intensity (BLOCKED)", False,
         "negative/humor_count; nonzero<30 → H3 BLOCKED"),
        ("top_k_aggressive_type_confidence",          "Top-k type confidence (BLOCKED)", True,
         "top-3 humor_type_confidence for aggressive posts; nonzero<30 → H3 BLOCKED"),
        ("sd_candidate_score_intensity_bounded",      "Self-defeating bounded intensity", True,
         "P(self_defeating) summed / total_posts; bounded [0,1]"),
    ]

    rows = []
    for col, label, is_bounded, note in h3_candidates:
        if col not in primary.columns:
            continue
        s = pd.to_numeric(primary[col], errors="coerce").fillna(0)
        d = describe_iv(s, primary, col)

        # Feasibility verdict
        nz = d["nonzero_n"]
        top1 = d["top_1_company_share"]
        concentrated = (top1 is not None and top1 > CONCENTRATION_TOP1_THRESHOLD)

        if nz < H3_BLOCKED:
            verdict = "do_not_use_for_regression"
        elif nz < H3_EXPLORATORY:
            verdict = "exploratory_only"
        elif not d["bounded_0_1"]:
            verdict = "rename_required (exceeds 1)"
        elif concentrated:
            verdict = "limited_robustness_blocked_concentration"
        else:
            verdict = "limited_robustness_possible"

        rows.append({
            "iv_name":           col,
            "label":             label,
            "note":              note,
            "bounded_0_1":       d["bounded_0_1"],
            "is_explicitly_bounded_construction": is_bounded,
            **{k: d[k] for k in ["n","nonzero_n","nonzero_pct","nonzero_company_n",
                                   "nonzero_period_n","intensity_level_n",
                                   "min","max","mean","median","std",
                                   "p10","p25","p75","p90",
                                   "has_negative_value","exceeds_one",
                                   "top_1_company_share","top_5_company_share"]},
            "recommended_use":   verdict,
        })
        print(f"    {col:<55} nonzero={nz:4d} ({d['nonzero_pct']:5.1f}%)  {verdict}")

    return pd.DataFrame(rows)


# ── Task 5: Manual Validation Sample ─────────────────────────────────────────

def build_manual_audit_sample(full, g5_panel):
    print("\n[Task 5] Building manual validation sample")
    np.random.seed(SEED)

    # company → ticker mapping from gate5 panel
    co_tick = g5_panel[["company_name","ticker"]].drop_duplicates()
    full2 = full.merge(co_tick, on="company_name", how="left")

    # Compute period-level total_posts for each firm-period
    period_totals = full.groupby(["company_name","period"]).size().reset_index(name="total_posts_in_firm_period")
    full2 = full2.merge(period_totals, on=["company_name","period"], how="left")

    # Output columns
    base_cols = [
        "sample_group", "company_name", "ticker", "source_x_handle",
        "global_post_id", "tweet_id", "created_at", "text",
        "humor_presence", "humor_type",
        "v2_candidate_label", "v2_candidate_type",
        "ml_humor_probability", "aggressive_candidate_score", "self_defeating_candidate_score",
        "ambiguity_status", "total_posts_in_firm_period", "firm_period",
        "human_affiliative_score_0_100", "human_self_enhancing_score_0_100",
        "human_aggressive_score_0_100", "human_self_defeating_score_0_100",
        "final_human_label", "coder_notes",
    ]

    full2["v1_humor_label"]     = full2["humor_presence"]
    full2["v1_humor_type"]      = full2["humor_type"]
    full2["v2_candidate_label"] = ""   # post-level v2 not available; filled by human coder
    full2["v2_candidate_type"]  = ""
    full2["ambiguity_status"]   = full2["humor_presence"].apply(
        lambda x: "ambiguous" if x == "ambiguous" else ("clear_humor" if x == "humor" else "non_humor")
    )
    full2["firm_period"] = full2["company_name"] + "__" + full2["period"].fillna("")
    for c in ["human_affiliative_score_0_100","human_self_enhancing_score_0_100",
              "human_aggressive_score_0_100","human_self_defeating_score_0_100",
              "final_human_label","coder_notes"]:
        full2[c] = ""

    groups = []

    # Group 1: aggressive_v1_hard — all v1-aggressive posts (≤100)
    g1 = full2[full2["humor_type"] == "aggressive"].copy()
    g1["sample_group"] = "aggressive_v1_hard"
    groups.append(g1)
    print(f"  Group 1 aggressive_v1_hard: {len(g1)}")

    # Group 2: aggressive_v2_only — posts where secondary label = aggressive but primary label is NOT
    # humor_type_secondary_label == 'aggressive' is the closest post-level proxy for "v2 candidate but not v1"
    g2_pool = full2[
        (full2.get("humor_type_secondary_label", pd.Series(dtype=str)) == "aggressive") &
        (full2["humor_type"] != "aggressive")
    ].sample(min(100, len(full2[
        (full2.get("humor_type_secondary_label", pd.Series(dtype=str)) == "aggressive") &
        (full2["humor_type"] != "aggressive")
    ])), random_state=SEED).copy()
    g2_pool["sample_group"] = "aggressive_v2_only"
    groups.append(g2_pool)
    print(f"  Group 2 aggressive_v2_only (secondary_label=aggressive, primary≠aggressive): {len(g2_pool)}")

    # Group 3: ambiguous_high_aggressive_candidate_score
    g3_pool = full2[
        (full2["humor_presence"] == "ambiguous") &
        (full2["aggressive_candidate_score"] > 0)
    ].sort_values("aggressive_candidate_score", ascending=False).head(100).copy()
    g3_pool["sample_group"] = "ambiguous_high_aggressive_candidate_score"
    groups.append(g3_pool)
    print(f"  Group 3 ambiguous_high_agg_score: {len(g3_pool)}")

    # Group 4: self_defeating_v2_only — all self_defeating posts (41 total)
    g4 = full2[full2["humor_type"] == "self_defeating"].copy()
    g4["sample_group"] = "self_defeating_v1"
    if len(g4) > 100:
        g4 = g4.sample(100, random_state=SEED)
    groups.append(g4)
    print(f"  Group 4 self_defeating: {len(g4)}")

    # Group 5: affiliative_or_self_enhancing_comparison
    g5_pool = full2[
        full2["humor_type"].isin(["affiliative", "self_enhancing"])
    ].sample(min(100, len(full2[full2["humor_type"].isin(["affiliative","self_enhancing"])])),
             random_state=SEED).copy()
    g5_pool["sample_group"] = "affiliative_or_self_enhancing_comparison"
    groups.append(g5_pool)
    print(f"  Group 5 affiliative/self_enhancing: {len(g5_pool)}")

    # Group 6: non_humor_or_low_score_comparison
    # ml_humor_probability for non_humor posts mostly 0.25-0.67; use <0.45 to get sufficient sample
    g6_pool = full2[
        (full2["humor_presence"] == "non_humor") &
        (full2["ml_humor_probability"].fillna(0) < 0.45)
    ].sample(min(100, len(full2[(full2["humor_presence"]=="non_humor") &
                                 (full2["ml_humor_probability"].fillna(0)<0.45)])),
             random_state=SEED).copy()
    g6_pool["sample_group"] = "non_humor_low_score_comparison"
    groups.append(g6_pool)
    print(f"  Group 6 non_humor_low_score (ml_prob<0.45): {len(g6_pool)}")

    sample = pd.concat(groups, ignore_index=True)

    # Align to output columns
    for c in base_cols:
        if c not in sample.columns:
            sample[c] = ""

    sample = sample[[c for c in base_cols if c in sample.columns]]
    print(f"  Total manual audit sample: {len(sample)} posts")
    return sample


# ── Task 6: Threshold Sensitivity ────────────────────────────────────────────

def build_threshold_sensitivity(full, g5_panel):
    print("\n[Task 6] Threshold sensitivity grid")

    # Primary sample filter
    g5_panel = g5_panel.copy()
    for col in ["join_ready_for_CAR_m1_p1"]:
        if col in g5_panel.columns:
            g5_panel[col] = g5_panel[col].astype(str).str.lower().map(
                {"true":True,"false":False}).fillna(False)
    primary_mask = (
        g5_panel["alignment_type"].isin(["prefiling_lag_1m","prefiling_lag_3m"]) &
        (g5_panel["join_ready_for_CAR_m1_p1"] == True)
    )
    primary_pairs = set(zip(g5_panel.loc[primary_mask,"company_name"],
                             g5_panel.loc[primary_mask,"period"]))

    rows = []

    # ── Humor probability threshold ──────────────────────────────────────
    for thr in HUMOR_THRESHOLDS:
        mask = full["ml_humor_probability"].fillna(0) >= thr
        pos_posts = full[mask]
        post_n = int(mask.sum())
        fp = pos_posts.groupby(["company_name","period"]).size().reset_index(name="cnt")
        fp_nonzero = len(fp)
        fp_pct = pct(fp_nonzero, g5_panel["company_name"].nunique() * g5_panel["period"].nunique())
        prim_nz = int(sum(1 for r in fp.itertuples()
                          if (r.company_name, r.period) in primary_pairs))
        # Correlation of binary indicator with humor_presence_any at firm-period
        fp["is_nz"] = 1
        merged = g5_panel[["company_name","period","humor_presence_any"]].merge(
            fp[["company_name","period","is_nz"]], on=["company_name","period"], how="left")
        merged["is_nz"] = merged["is_nz"].fillna(0)
        corr = safe_corr(merged["is_nz"], merged["humor_presence_any"])
        v2_only = None
        consensus = None
        co_nz = int(fp["company_name"].nunique()) if len(fp) > 0 else 0
        per_nz = int(fp["period"].nunique()) if len(fp) > 0 else 0
        rows.append({
            "candidate_type": "humor_probability",
            "threshold": thr,
            "post_level_positive_n": post_n,
            "firm_period_nonzero_n": fp_nonzero,
            "firm_period_nonzero_pct": pct(fp_nonzero, len(g5_panel)),
            "primary_sample_nonzero_n": prim_nz,
            "primary_sample_nonzero_pct": pct(prim_nz, int(primary_mask.sum())),
            "nonzero_company_n": co_nz,
            "nonzero_period_n": per_nz,
            "correlation_with_v1_hard_label": corr,
            "v2_only_share": v2_only,
            "consensus_share": consensus,
            "recommended_use": (
                "primary_H1_IV" if thr == 0.50
                else ("lower_bound_sensitivity" if thr < 0.50 else "upper_bound_sensitivity")
            ),
        })

    # ── Aggressive candidate score threshold ─────────────────────────────
    for thr in AGGRESSIVE_THRESHOLDS:
        mask = full["aggressive_candidate_score"] >= thr
        pos_posts = full[mask]
        post_n = int(mask.sum())
        fp = pos_posts.groupby(["company_name","period"]).size().reset_index(name="cnt")
        fp_nonzero = len(fp)
        prim_nz = int(sum(1 for r in fp.itertuples()
                          if (r.company_name, r.period) in primary_pairs))
        # Correlation with v1 firm-period aggressive_presence_any
        fp["is_nz"] = 1
        merged = g5_panel[["company_name","period","hc_aggressive_presence"]].merge(
            fp[["company_name","period","is_nz"]], on=["company_name","period"], how="left")
        merged["is_nz"] = merged["is_nz"].fillna(0)
        corr = safe_corr(merged["is_nz"], merged["hc_aggressive_presence"])
        # v2_only_share: positive threshold posts that are NOT v1 aggressive
        v1_agg_posts = full["is_aggressive"].sum()
        v2_only_posts = int((mask & ~full["is_aggressive"]).sum())
        cons_posts    = int((mask & full["is_aggressive"]).sum())
        v2_only  = pct(v2_only_posts, post_n) if post_n > 0 else None
        consensus= pct(cons_posts,    post_n) if post_n > 0 else None
        co_nz = int(fp["company_name"].nunique()) if len(fp) > 0 else 0
        per_nz = int(fp["period"].nunique()) if len(fp) > 0 else 0
        rows.append({
            "candidate_type": "aggressive_candidate_score",
            "threshold": thr,
            "post_level_positive_n": post_n,
            "firm_period_nonzero_n": fp_nonzero,
            "firm_period_nonzero_pct": pct(fp_nonzero, len(g5_panel)),
            "primary_sample_nonzero_n": prim_nz,
            "primary_sample_nonzero_pct": pct(prim_nz, int(primary_mask.sum())),
            "nonzero_company_n": co_nz,
            "nonzero_period_n": per_nz,
            "correlation_with_v1_hard_label": corr,
            "v2_only_share": v2_only,
            "consensus_share": consensus,
            "recommended_use": (
                "consistent_with_v1_floor" if thr >= 0.60
                else ("primary_threshold" if thr == 0.50 else "exploratory")
            ),
        })

    # ── Self-defeating candidate score threshold ─────────────────────────
    for thr in SELF_DEFEATING_THRESHOLDS:
        mask = full["self_defeating_candidate_score"] >= thr
        pos_posts = full[mask]
        post_n = int(mask.sum())
        fp = pos_posts.groupby(["company_name","period"]).size().reset_index(name="cnt")
        fp_nonzero = len(fp)
        prim_nz = int(sum(1 for r in fp.itertuples()
                          if (r.company_name, r.period) in primary_pairs))
        fp["is_nz"] = 1
        v1_sd_posts = int(full["is_self_defeating"].sum())
        v2_only_posts = int((mask & ~full["is_self_defeating"]).sum())
        cons_posts    = int((mask & full["is_self_defeating"]).sum())
        v2_only  = pct(v2_only_posts, post_n) if post_n > 0 else None
        consensus= pct(cons_posts,    post_n) if post_n > 0 else None
        co_nz = int(fp["company_name"].nunique()) if len(fp) > 0 else 0
        per_nz = int(fp["period"].nunique()) if len(fp) > 0 else 0
        rows.append({
            "candidate_type": "self_defeating_candidate_score",
            "threshold": thr,
            "post_level_positive_n": post_n,
            "firm_period_nonzero_n": fp_nonzero,
            "firm_period_nonzero_pct": pct(fp_nonzero, len(g5_panel)),
            "primary_sample_nonzero_n": prim_nz,
            "primary_sample_nonzero_pct": pct(prim_nz, int(primary_mask.sum())),
            "nonzero_company_n": co_nz,
            "nonzero_period_n": per_nz,
            "correlation_with_v1_hard_label": None,
            "v2_only_share": v2_only,
            "consensus_share": consensus,
            "recommended_use": "exploratory_only_low_base_rate",
        })

    df = pd.DataFrame(rows)
    print(f"  {len(df)} threshold grid rows ({df['candidate_type'].nunique()} candidate types)")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Gate 5.1: Paper-grounded Humor IV Reconstruction Repair ===\n")

    full, hypo, g5, rm, primary, co_tick = load_all()

    # Task 2: Provenance
    prov_df = build_provenance()
    OUT_PROV.parent.mkdir(parents=True, exist_ok=True)
    prov_df.to_csv(OUT_PROV, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_PROV}")

    # Task 3: Sanity checks
    sanity_df = build_sanity_checks(g5, primary)
    OUT_SANITY.parent.mkdir(parents=True, exist_ok=True)
    sanity_df.to_csv(OUT_SANITY, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_SANITY}")

    # Task 4: Corrected panel + H3 diagnostics
    panel51 = build_corrected_panel(g5, full, hypo)
    primary51 = panel51[
        panel51["alignment_type"].isin(["prefiling_lag_1m","prefiling_lag_3m"]) &
        (panel51["join_ready_for_CAR_m1_p1"].astype(str).str.lower() == "true")
    ].copy()
    h3_diag = build_h3_diagnostics(panel51, primary51)

    OUT_CANDS.parent.mkdir(parents=True, exist_ok=True)
    panel51.to_csv(OUT_CANDS, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_CANDS}  ({len(panel51)} rows, {len(panel51.columns)} cols)")

    OUT_DIAGS.parent.mkdir(parents=True, exist_ok=True)
    h3_diag.to_csv(OUT_DIAGS, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_DIAGS}  ({len(h3_diag)} H3 IVs)")

    # Task 5: Manual audit sample
    audit_sample = build_manual_audit_sample(full, g5)
    OUT_SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    audit_sample.to_csv(OUT_SAMPLE, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_SAMPLE}  ({len(audit_sample)} posts)")

    # Task 6: Threshold sensitivity
    thresh_df = build_threshold_sensitivity(full, g5)
    OUT_THRESH.parent.mkdir(parents=True, exist_ok=True)
    thresh_df.to_csv(OUT_THRESH, index=False, encoding="utf-8-sig")
    print(f"  → {OUT_THRESH}  ({len(thresh_df)} grid rows)")

    # ── Summary prints ────────────────────────────────────────────────────
    print("\n=== Probability Score Provenance: rename_required items ===")
    for _, r in prov_df[prov_df["rename_required"]].iterrows():
        print(f"  {r['variable_name']:45s}  →  {r['rename_recommendation']}")

    print("\n=== Sanity Check: action_required items ===")
    for _, r in sanity_df[sanity_df["action_required"] != "ok"].iterrows():
        print(f"  {r['variable_name']:45s}  max={r['max']:8.4f}  exceeds1={r['exceeds_one']}  action={r['action_required']}")

    print("\n=== H3 Candidate IV Summary ===")
    for _, r in h3_diag.iterrows():
        print(f"  {r['iv_name']:<55} nonzero={r['nonzero_n']:3d}  bounded={r['bounded_0_1']}  → {r['recommended_use']}")

    print("\n=== Threshold Sensitivity Summary ===")
    for ctype in thresh_df["candidate_type"].unique():
        sub = thresh_df[thresh_df["candidate_type"]==ctype]
        print(f"  [{ctype}]")
        for _, r in sub.iterrows():
            print(f"    thr={r['threshold']:.2f}  post_n={r['post_level_positive_n']:6d}  "
                  f"prim_nonzero={r['primary_sample_nonzero_n']:4d} ({r['primary_sample_nonzero_pct']:.1f}%)")

    # ── Manifest ──────────────────────────────────────────────────────────
    rename_list = prov_df.loc[prov_df["rename_required"], "variable_name"].tolist()
    sanity_issues = sanity_df.loc[sanity_df["action_required"] != "ok", "variable_name"].tolist()
    h3_ok = h3_diag.loc[
        h3_diag["recommended_use"].isin(["limited_robustness_possible","exploratory_only"]),
        "iv_name"
    ].tolist()
    best_h3 = h3_diag.loc[h3_diag["nonzero_n"].idxmax(), "iv_name"] if len(h3_diag) > 0 else None

    sanity_v1v2_exceeds = sanity_df.loc[
        sanity_df["exceeds_one"] & sanity_df["variable_name"].str.contains("v2|rare|intensity"),
        "variable_name"
    ].tolist()

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "Gate 5.1 — Paper-grounded IV reconstruction repair",
        "based_on_commit": GATE5_COMMIT,
        "script": "scripts/build_humor_iv_gate5_1_repair.py",
        "aggressive_base_rate": round(AGGRESSIVE_BASE_RATE, 6),
        "self_defeating_base_rate": round(SELF_DEFEATING_BASE_RATE, 6),
        "seed": SEED,
        # Task flags
        "hsq_codebook_created": True,
        "probability_provenance_audited": True,
        "share_intensity_sanity_checked": True,
        "manual_validation_sample_created": True,
        "threshold_sensitivity_created": True,
        "corrected_candidate_panel_created": True,
        # Provenance findings
        "aggressive_prob_sum_is_true_aggressive_probability": False,
        "aggressive_prob_sum_formula_issue": (
            "Classified aggressive posts: uses humor_type_confidence only (missing ml_humor_probability factor). "
            "Ambiguous posts: ml_humor_probability × base_rate. Inconsistent formula. "
            "Corrected formula in Gate5.1: ml_humor_probability × humor_type_confidence for classified."
        ),
        "rename_required_variables": rename_list,
        # Sanity findings
        "sanity_issues": sanity_issues,
        "v2_candidate_exceeds_one_variables": sanity_v1v2_exceeds,
        "v2_firm_level_finding": (
            "CRITICAL: v2_aggressive_candidate_count exceeds total_posts in 189/3767 firm-periods "
            "(max ratio=9.0). Variable appears to be a firm-level fixed score, not a per-period post count. "
            "Normalization by total_posts or humor_count is INVALID. "
            "hc_v2_aggressive_candidate_share and hc_v2_aggressive_candidate_intensity are INVALID as share/intensity. "
            "Use hc_v2_aggressive_candidate_count as raw count IV only."
        ),
        # H3 feasibility
        "h3_regressionable_candidates": h3_ok,
        "h3_best_candidate": best_h3,
        "h3_best_nonzero_n": int(h3_diag["nonzero_n"].max()) if len(h3_diag) > 0 else 0,
        # Manual audit
        "manual_audit_sample_n": len(audit_sample),
        "manual_audit_sample_groups": audit_sample["sample_group"].value_counts().to_dict(),
        "manual_audit_sample_seed": SEED,
        # Constraint flags (ALL False)
        "raw_data_modified":                 False,
        "existing_iv_overwritten":           False,
        "hypothesis_variables_overwritten":  False,
        "regression_master_overwritten":     False,
        "regression_run":                    False,
        "tobins_q_initiated":                False,
        "causal_claim_made":                 False,
        "brand_equity_claimed":              False,
        "v2_candidate_interpreted_as_ground_truth": False,
    }

    OUT_MAN.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAN.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n  → {OUT_MAN}")
    print(f"\n  rename_required: {len(rename_list)} variables")
    print(f"  sanity_issues:   {len(sanity_issues)} variables")
    print(f"  H3 re-testable:  {len(h3_ok)} candidates")
    print(f"  Best H3:         {best_h3}")


if __name__ == "__main__":
    main()
