#!/usr/bin/env python3
"""Simple OLS preliminary results for H1, H2, H3.

PRELIMINARY DIAGNOSTIC ONLY.
Results are based on predicted humor labels (H1) or human-coded
batch1 type labels (H2/H3). Classifier measurement limitations apply.
Do not treat any output as final causal evidence.

Absolute prohibitions enforced by design:
  - Does NOT scrape, call X API, or run Playwright
  - Does NOT reclassify the integrated corpus
  - Does NOT use 564 model-predicted type rows as training labels
  - Does NOT modify data/raw, dashboard/data, or workflow files
  - Does NOT declare any classifier as candidate/deployment-ready
  - Does NOT run H1/H2/H3 regressions against Wendy's-only subset

Permitted:
  - Reading existing prediction output files
  - Using predicted humor presence labels as the IV for H1
  - Using human-coded batch1 type labels for H2/H3
  - Computing firm-level aggregations from existing data
  - Writing results to 20260618expand/ols_hypothesis_results/

Usage:
    python run_simple_ols_hypotheses.py
    python run_simple_ols_hypotheses.py --out-dir /path/to/output
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

# Input files
H1_CORPUS = (
    REPO_ROOT
    / "20260618expand/classifier_improvement/h1_presence_only"
    / "full_corpus_classification/data/fortune100_h1_presence_classified_posts.csv"
)
TYPE_TRAINING = (
    REPO_ROOT
    / "20260618expand/classifier_improvement/humor_type_leakage_filtered"
    / "data/type_training_leakage_filtered_variants.csv"
)


# ---------------------------------------------------------------------------
# OLS with HC3 heteroskedasticity-robust standard errors
# ---------------------------------------------------------------------------
def ols_hc3(y: np.ndarray, X: np.ndarray, feature_names: list[str]) -> list[dict]:
    """OLS with HC3 sandwich SEs. Returns one dict per coefficient.

    HC3: V = (X'X)^{-1} X' diag(e_i^2 / (1-h_ii)^2) X (X'X)^{-1}
    Falls back to HC1 if leverage computation would overflow.
    """
    n, k = X.shape
    if n <= k:
        return []

    XTX = X.T @ X
    try:
        XTX_inv = np.linalg.inv(XTX)
    except np.linalg.LinAlgError:
        return []

    beta = XTX_inv @ (X.T @ y)
    y_hat = X @ beta
    e = y - y_hat

    ss_res = float(np.sum(e**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    r_squared_adj = 1.0 - (1.0 - r_squared) * (n - 1) / (n - k)

    # HC3 leverage
    # h_ii = X[i] @ XTX_inv @ X[i]' = einsum('ij,jk,ik->i', X, XTX_inv, X)
    try:
        h = np.einsum("ij,jk,ik->i", X, XTX_inv, X)
        h = np.clip(h, 0.0, 1.0 - 1e-8)
        w = e**2 / (1.0 - h) ** 2
        se_type = "HC3"
    except MemoryError:
        # Fallback to HC1
        w = (n / (n - k)) * e**2
        se_type = "HC1"

    XWXT = X.T @ (w[:, None] * X)
    vcov = XTX_inv @ XWXT @ XTX_inv
    ses = np.sqrt(np.diag(vcov))

    results = []
    for j, (name, b, se) in enumerate(zip(feature_names, beta, ses)):
        t = float(b / se) if se > 0 else float("nan")
        p = float(2.0 * (1.0 - _t_cdf(abs(t), df=n - k))) if not math.isnan(t) else float("nan")
        results.append(
            {
                "feature": name,
                "coefficient": round(float(b), 6),
                "robust_se": round(float(se), 6),
                "se_type": se_type,
                "t_stat": round(t, 4),
                "p_value": round(p, 6),
                "p_stars": _stars(p),
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r_squared, 6),
                "r_squared_adj": round(r_squared_adj, 6),
            }
        )
    return results


def _t_cdf(t: float, df: int) -> float:
    """Approximate CDF of t-distribution using scipy."""
    from scipy.special import betainc
    x = df / (df + t * t)
    return 1.0 - 0.5 * betainc(df / 2.0, 0.5, x)


def _stars(p: float) -> str:
    if math.isnan(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def add_intercept(X: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(X)), X])


def _log1p_engagement(rows: list[dict], col: str = "total_engagement") -> np.ndarray:
    return np.array([math.log1p(float(r[col])) for r in rows])


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_h1_corpus() -> list[dict]:
    with H1_CORPUS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # Exclude rows with missing text or engagement
    clean = [
        r for r in rows
        if r.get("missing_text", "False") in ("False", "0", "false", "")
        and r.get("total_engagement", "") != ""
        and r.get("h1_humor_presence_pred_t50", "") in ("0", "1")
    ]
    return clean


def load_type_batch1() -> list[dict]:
    with TYPE_TRAINING.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["source"] == "batch1_fortune100"]


def join_type_with_corpus(type_rows: list[dict], corp_rows: list[dict]) -> list[dict]:
    corp_by_id = {r["tweet_id"]: r for r in corp_rows if r.get("tweet_id")}
    joined = []
    for r in type_rows:
        corp = corp_by_id.get(r.get("tweet_id", ""))
        if corp and corp.get("total_engagement", "") != "":
            joined.append(
                {
                    "tweet_id": r["tweet_id"],
                    "company_name": r["company_name"],
                    "humor_type": r["humor_type"],
                    "total_engagement": corp["total_engagement"],
                    "log_total_engagement": corp.get("log_total_engagement", ""),
                    "text_length": corp.get("text_length", ""),
                    "hashtag_count": corp.get("hashtag_count", ""),
                    "mention_count": corp.get("mention_count", ""),
                    "h1_pred_t50": corp.get("h1_humor_presence_pred_t50", "1"),
                }
            )
    return joined


def _safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# H1: Humor presence → engagement
# ---------------------------------------------------------------------------
def run_h1(corp_rows: list[dict], out_dir: Path) -> list[dict]:
    """H1: humor_presence → log1p(total_engagement).

    Uses: fortune100_h1_presence_classified_posts.csv (65k rows)
    DV: log1p(total_engagement)
    IV: h1_humor_presence_pred_t50 (0/1 predicted label)
    Limitation: IV is a predicted label (classifier AUC ~0.82), not ground truth.
    """
    y = _log1p_engagement(corp_rows)
    humor = np.array([float(r["h1_humor_presence_pred_t50"]) for r in corp_rows])
    text_len = np.array([_safe_float(r.get("text_length", "0")) for r in corp_rows])
    hashtag = np.array([_safe_float(r.get("hashtag_count", "0")) for r in corp_rows])
    mention = np.array([_safe_float(r.get("mention_count", "0")) for r in corp_rows])

    output_rows: list[dict] = []
    n = len(y)

    base_meta = {
        "hypothesis": "H1",
        "dependent_variable": "log1p_total_engagement",
        "sample_definition": "fortune100_posts_full_corpus_excluding_wendys_legacy",
        "label_source": "predicted (h1_humor_presence_pred_t50, t=0.50)",
        "label_source_warning":
            "IV is model-predicted presence label, NOT human ground truth; "
            "classifier AUC~0.82; results are preliminary",
        "interpretation_level": "preliminary_diagnostic",
    }

    # Model A: simple
    X_A = add_intercept(humor.reshape(-1, 1))
    res_A = ols_hc3(y, X_A, ["intercept", "humor_presence_pred_t50"])
    for r in res_A:
        output_rows.append({
            **base_meta,
            "model_name": "H1_simple",
            "controls": "none",
            **r,
        })

    # Model B: with controls
    controls = np.column_stack([text_len, hashtag, mention])
    X_B = np.column_stack([np.ones(n), humor, controls])
    res_B = ols_hc3(
        y, X_B,
        ["intercept", "humor_presence_pred_t50",
         "text_length", "hashtag_count", "mention_count"],
    )
    for r in res_B:
        output_rows.append({
            **base_meta,
            "model_name": "H1_simple_controls",
            "controls": "text_length hashtag_count mention_count",
            **r,
        })

    write_csv(
        out_dir / "h1_simple_ols_results.csv",
        output_rows,
        [
            "hypothesis", "model_name", "dependent_variable", "independent_variable",
            "feature", "coefficient", "robust_se", "se_type", "t_stat", "p_value",
            "p_stars", "n_obs", "k_params", "r_squared", "r_squared_adj",
            "sample_definition", "controls", "label_source", "label_source_warning",
            "interpretation_level",
        ],
    )
    print(f"  H1: n={n} rows → h1_simple_ols_results.csv")
    return output_rows


# ---------------------------------------------------------------------------
# H2-1: Aggressive vs other humor
# ---------------------------------------------------------------------------
def run_h2_aggressive_vs_other(joined: list[dict], out_dir: Path) -> list[dict]:
    """H2-1: binary aggressive_vs_other → log1p(total_engagement).

    Sample: batch1_fortune100 humor posts with human type labels (648 rows).
    DV: log1p(total_engagement)
    IV: aggressive_dummy (1=aggressive, 0=affiliative/self-enhancing/self-defeating)
    Label: HUMAN-CODED (batch1_fortune100), Fortune100 only.
    """
    y = np.array([math.log1p(_safe_float(r["total_engagement"])) for r in joined])
    aggressive = np.array(
        [1.0 if r["humor_type"] == "aggressive" else 0.0 for r in joined]
    )
    text_len = np.array([_safe_float(r.get("text_length", "0")) for r in joined])
    hashtag = np.array([_safe_float(r.get("hashtag_count", "0")) for r in joined])
    mention = np.array([_safe_float(r.get("mention_count", "0")) for r in joined])
    n = len(y)

    base_meta = {
        "hypothesis": "H2_1",
        "dependent_variable": "log1p_total_engagement",
        "sample_definition": "batch1_fortune100_humor_posts_human_type_labels",
        "label_source": "HUMAN-CODED batch1_fortune100 type labels",
        "interpretation_level": "preliminary_diagnostic",
    }

    output_rows: list[dict] = []
    n_agg = int(aggressive.sum())
    n_other = n - n_agg

    # Model A: simple
    X_A = add_intercept(aggressive.reshape(-1, 1))
    res_A = ols_hc3(y, X_A, ["intercept", "aggressive_vs_other"])
    for r in res_A:
        output_rows.append({
            **base_meta,
            "model_name": "H2_1_simple",
            "controls": "none",
            "n_aggressive": n_agg,
            "n_other": n_other,
            "label_source_warning": "",
            **r,
        })

    # Model B: with controls
    X_B = np.column_stack([np.ones(n), aggressive, text_len, hashtag, mention])
    res_B = ols_hc3(
        y, X_B,
        ["intercept", "aggressive_vs_other", "text_length", "hashtag_count", "mention_count"],
    )
    for r in res_B:
        output_rows.append({
            **base_meta,
            "model_name": "H2_1_simple_controls",
            "controls": "text_length hashtag_count mention_count",
            "n_aggressive": n_agg,
            "n_other": n_other,
            "label_source_warning": "",
            **r,
        })

    write_csv(
        out_dir / "h2_aggressive_vs_other_simple_ols_results.csv",
        output_rows,
        [
            "hypothesis", "model_name", "dependent_variable",
            "feature", "coefficient", "robust_se", "se_type", "t_stat", "p_value",
            "p_stars", "n_obs", "k_params", "r_squared", "r_squared_adj",
            "n_aggressive", "n_other",
            "sample_definition", "controls", "label_source", "label_source_warning",
            "interpretation_level",
        ],
    )
    print(f"  H2-1: n={n} (agg={n_agg} other={n_other}) → h2_aggressive_vs_other_simple_ols_results.csv")
    return output_rows


# ---------------------------------------------------------------------------
# H2-2: Four humor type OLS (ref=affiliative)
# ---------------------------------------------------------------------------
def run_h2_four_type(joined: list[dict], out_dir: Path) -> list[dict]:
    """H2-2: four humor types → log1p(total_engagement); ref=affiliative.

    Includes pairwise mean comparison in output.
    """
    y = np.array([math.log1p(_safe_float(r["total_engagement"])) for r in joined])
    types = [r["humor_type"] for r in joined]
    n = len(y)

    agg = np.array([1.0 if t == "aggressive" else 0.0 for t in types])
    se = np.array([1.0 if t == "self-enhancing" else 0.0 for t in types])
    sd = np.array([1.0 if t == "self-defeating" else 0.0 for t in types])
    text_len = np.array([_safe_float(r.get("text_length", "0")) for r in joined])
    hashtag = np.array([_safe_float(r.get("hashtag_count", "0")) for r in joined])
    mention = np.array([_safe_float(r.get("mention_count", "0")) for r in joined])

    type_counts = {t: types.count(t) for t in ["aggressive", "affiliative", "self-enhancing", "self-defeating"]}
    type_means = {}
    for t in ["aggressive", "affiliative", "self-enhancing", "self-defeating"]:
        mask = np.array([r["humor_type"] == t for r in joined])
        type_means[t] = float(y[mask].mean()) if mask.sum() > 0 else float("nan")

    base_meta = {
        "hypothesis": "H2_2",
        "dependent_variable": "log1p_total_engagement",
        "reference_category": "affiliative",
        "sample_definition": "batch1_fortune100_humor_posts_human_type_labels",
        "label_source": "HUMAN-CODED batch1_fortune100 type labels",
        "interpretation_level":
            "preliminary_diagnostic; self_defeating underpowered (n=24)",
    }

    output_rows: list[dict] = []

    def _add_meta(row, model_name, controls):
        row.update({
            **base_meta,
            "model_name": model_name,
            "controls": controls,
            "n_aggressive": type_counts.get("aggressive", 0),
            "n_affiliative": type_counts.get("affiliative", 0),
            "n_self_enhancing": type_counts.get("self-enhancing", 0),
            "n_self_defeating": type_counts.get("self-defeating", 0),
            "mean_log_eng_aggressive": round(type_means.get("aggressive", float("nan")), 4),
            "mean_log_eng_affiliative": round(type_means.get("affiliative", float("nan")), 4),
            "mean_log_eng_self_enhancing": round(type_means.get("self-enhancing", float("nan")), 4),
            "mean_log_eng_self_defeating": round(type_means.get("self-defeating", float("nan")), 4),
            "label_source_warning": "",
        })
        return row

    # Model A: simple
    X_A = np.column_stack([np.ones(n), agg, se, sd])
    res_A = ols_hc3(y, X_A, ["intercept", "aggressive", "self_enhancing", "self_defeating"])
    for r in res_A:
        _add_meta(r, "H2_2_four_type_simple", "none")
        output_rows.append(r)

    # Model B: with controls
    X_B = np.column_stack([np.ones(n), agg, se, sd, text_len, hashtag, mention])
    res_B = ols_hc3(
        y, X_B,
        ["intercept", "aggressive", "self_enhancing", "self_defeating",
         "text_length", "hashtag_count", "mention_count"],
    )
    for r in res_B:
        _add_meta(r, "H2_2_four_type_controls", "text_length hashtag_count mention_count")
        output_rows.append(r)

    # Pairwise mean comparison rows
    pairs = [
        ("aggressive", "affiliative"),
        ("aggressive", "self-enhancing"),
        ("aggressive", "self-defeating"),
    ]
    for t1, t2 in pairs:
        diff = type_means.get(t1, float("nan")) - type_means.get(t2, float("nan"))
        n1 = type_counts.get(t1, 0)
        n2 = type_counts.get(t2, 0)
        output_rows.append({
            **base_meta,
            "model_name": f"H2_2_pairwise_mean_{t1}_vs_{t2}",
            "controls": "n/a",
            "feature": f"mean_diff_{t1}_vs_{t2}",
            "coefficient": round(diff, 6),
            "robust_se": "",
            "se_type": "descriptive",
            "t_stat": "",
            "p_value": "",
            "p_stars": "",
            "n_obs": n1 + n2,
            "k_params": "",
            "r_squared": "",
            "r_squared_adj": "",
            "n_aggressive": type_counts.get("aggressive", 0),
            "n_affiliative": type_counts.get("affiliative", 0),
            "n_self_enhancing": type_counts.get("self-enhancing", 0),
            "n_self_defeating": type_counts.get("self-defeating", 0),
            "mean_log_eng_aggressive": round(type_means.get("aggressive", float("nan")), 4),
            "mean_log_eng_affiliative": round(type_means.get("affiliative", float("nan")), 4),
            "mean_log_eng_self_enhancing": round(type_means.get("self-enhancing", float("nan")), 4),
            "mean_log_eng_self_defeating": round(type_means.get("self-defeating", float("nan")), 4),
            "label_source_warning": "",
        })

    write_csv(
        out_dir / "h2_four_type_simple_ols_results.csv",
        output_rows,
        [
            "hypothesis", "model_name", "dependent_variable",
            "reference_category", "feature", "coefficient", "robust_se", "se_type",
            "t_stat", "p_value", "p_stars", "n_obs", "k_params",
            "r_squared", "r_squared_adj",
            "n_aggressive", "n_affiliative", "n_self_enhancing", "n_self_defeating",
            "mean_log_eng_aggressive", "mean_log_eng_affiliative",
            "mean_log_eng_self_enhancing", "mean_log_eng_self_defeating",
            "sample_definition", "controls", "label_source", "label_source_warning",
            "interpretation_level",
        ],
    )
    print(f"  H2-2: n={n} types={type_counts} → h2_four_type_simple_ols_results.csv")
    return output_rows


# ---------------------------------------------------------------------------
# H3: Firm-level aggressive intensity → mean engagement (inverted U)
# ---------------------------------------------------------------------------
def run_h3(corp_rows: list[dict], type_rows_batch1: list[dict], out_dir: Path) -> list[dict]:
    """H3: aggressive_intensity + intensity^2 → firm_mean_log_engagement.

    Sample: 88 firms with batch1 type labels. Only 24 have any aggressive posts.
    DV: mean log1p(total_engagement) per firm (from full Fortune100 corpus)
    IV: aggressive_humor_posts / total_humor_posts in labeled sample
    H3 is likely NOT_INTERPRETABLE given sparse aggressive data.
    """
    # Build firm-level type intensity from batch1 labels
    firm_type = defaultdict(lambda: {"total": 0, "aggressive": 0})
    for r in type_rows_batch1:
        co = r["company_name"]
        firm_type[co]["total"] += 1
        if r["humor_type"] == "aggressive":
            firm_type[co]["aggressive"] += 1

    # Build firm-level mean engagement from full corpus
    firm_eng: dict[str, list[float]] = defaultdict(list)
    for r in corp_rows:
        co = r.get("company_name", "")
        if co and r.get("total_engagement", "") != "":
            firm_eng[co].append(math.log1p(float(r["total_engagement"])))

    # Construct firm-level dataset
    firm_rows: list[dict] = []
    for co, td in firm_type.items():
        if td["total"] == 0:
            continue
        intensity = td["aggressive"] / td["total"]
        engs = firm_eng.get(co, [])
        if not engs:
            continue
        firm_rows.append(
            {
                "company_name": co,
                "aggressive_intensity": intensity,
                "n_labeled_humor_posts": td["total"],
                "n_labeled_aggressive": td["aggressive"],
                "mean_log_engagement": float(np.mean(engs)),
                "n_corpus_posts": len(engs),
            }
        )

    n_firms = len(firm_rows)
    n_firms_with_aggressive = sum(1 for r in firm_rows if r["aggressive_intensity"] > 0)
    intensities = np.array([r["aggressive_intensity"] for r in firm_rows])
    intensity_range = (float(intensities.min()), float(intensities.max()))

    y_firm = np.array([r["mean_log_engagement"] for r in firm_rows])
    X_intensity = intensities
    X_intensity_sq = X_intensity**2

    output_rows: list[dict] = []

    interpretable = n_firms_with_aggressive >= 15 and intensity_range[1] > 0.15

    base_meta = {
        "hypothesis": "H3",
        "dependent_variable": "firm_mean_log1p_total_engagement",
        "sample_definition":
            f"batch1_fortune100_firm_level_n={n_firms}_firms "
            f"({n_firms_with_aggressive} with any aggressive posts)",
        "label_source": "HUMAN-CODED batch1 type labels for intensity; full corpus for engagement",
        "intensity_range": f"{intensity_range[0]:.3f}-{intensity_range[1]:.3f}",
        "n_firms_with_aggressive": n_firms_with_aggressive,
        "interpretation_level":
            "NOT_INTERPRETABLE" if not interpretable else "preliminary_diagnostic",
        "not_interpretable_reason":
            "" if interpretable else
            f"Only {n_firms_with_aggressive}/88 firms have aggressive posts (64 firms intensity=0). "
            "Insufficient variation to estimate inverted-U. Quadratic is unidentified.",
    }

    # Model A: linear only
    X_A = np.column_stack([np.ones(n_firms), X_intensity])
    res_A = ols_hc3(y_firm, X_A, ["intercept", "aggressive_intensity"])
    for r in res_A:
        output_rows.append({
            **base_meta,
            "model_name": "H3_linear_only",
            "controls": "none",
            "turning_point": "",
            "turning_point_in_range": "",
            **r,
        })

    # Model B: with quadratic
    X_B = np.column_stack([np.ones(n_firms), X_intensity, X_intensity_sq])
    res_B = ols_hc3(y_firm, X_B, ["intercept", "aggressive_intensity", "aggressive_intensity_sq"])
    beta_B = {r["feature"]: r["coefficient"] for r in res_B}
    b1 = beta_B.get("aggressive_intensity", 0.0)
    b2 = beta_B.get("aggressive_intensity_sq", 0.0)
    if b2 != 0.0:
        turning_point = -b1 / (2.0 * b2)
        in_range = intensity_range[0] <= turning_point <= intensity_range[1]
    else:
        turning_point = float("nan")
        in_range = False
    for r in res_B:
        output_rows.append({
            **base_meta,
            "model_name": "H3_quadratic",
            "controls": "none",
            "turning_point": round(turning_point, 4) if not math.isnan(turning_point) else "undefined",
            "turning_point_in_range": str(in_range) if b2 != 0 else "undefined",
            "inverted_u_check": (
                "b1>0 AND b2<0 (inverted-U pattern)"
                if b1 > 0 and b2 < 0 else
                "b1>0 AND b2>0 (U-shape, not inverted)"
                if b1 > 0 and b2 > 0 else
                "b1<0 (negative linear dominates)"
                if b1 < 0 else "ambiguous"
            ),
            **r,
        })

    write_csv(
        out_dir / "h3_intensity_simple_ols_results.csv",
        output_rows,
        [
            "hypothesis", "model_name", "dependent_variable",
            "feature", "coefficient", "robust_se", "se_type", "t_stat", "p_value",
            "p_stars", "n_obs", "k_params", "r_squared", "r_squared_adj",
            "turning_point", "turning_point_in_range", "inverted_u_check",
            "intensity_range", "n_firms_with_aggressive",
            "sample_definition", "controls", "label_source",
            "interpretation_level", "not_interpretable_reason",
        ],
    )
    print(
        f"  H3: n_firms={n_firms} (agg_intensity>0: {n_firms_with_aggressive}) → h3_intensity_simple_ols_results.csv"
        f"\n    turning_point={round(turning_point,4) if not math.isnan(turning_point) else 'n/a'} "
        f"in_range={in_range} interpretable={interpretable}"
    )
    return output_rows


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
def build_summary(
    h1: list[dict], h2a: list[dict], h2b: list[dict], h3: list[dict]
) -> list[dict]:
    rows = []

    def _focal_row(result_rows, model_name_contains, feature_contains):
        for r in result_rows:
            if (model_name_contains in r.get("model_name", "")
                    and feature_contains in r.get("feature", "")):
                return r
        return {}

    # H1 focal: humor presence coefficient in simple model
    h1_focal = _focal_row(h1, "H1_simple", "humor_presence")
    rows.append(
        {
            "hypothesis": "H1",
            "sub_hypothesis": "",
            "model": "H1_simple",
            "focal_independent_variable": "humor_presence_pred_t50",
            "dependent_variable": "log1p_total_engagement",
            "coefficient": h1_focal.get("coefficient", ""),
            "robust_se": h1_focal.get("robust_se", ""),
            "t_stat": h1_focal.get("t_stat", ""),
            "p_value": h1_focal.get("p_value", ""),
            "p_stars": h1_focal.get("p_stars", ""),
            "n_obs": h1_focal.get("n_obs", ""),
            "r_squared": h1_focal.get("r_squared", ""),
            "sample_definition": h1_focal.get("sample_definition", ""),
            "interpretation_level": h1_focal.get("interpretation_level", ""),
            "preliminary_verdict": (
                "preliminary_supported"
                if h1_focal.get("coefficient", 0) and float(h1_focal.get("coefficient", 0)) > 0
                and float(h1_focal.get("p_value", 1.0)) < 0.10
                else "preliminary_not_supported"
                if h1_focal.get("coefficient", 0)
                else "insufficient_data"
            ),
        }
    )

    # H2-1 focal
    h2a_focal = _focal_row(h2a, "H2_1_simple", "aggressive_vs_other")
    rows.append(
        {
            "hypothesis": "H2",
            "sub_hypothesis": "H2_1_aggressive_vs_other",
            "model": "H2_1_simple",
            "focal_independent_variable": "aggressive_vs_other",
            "dependent_variable": "log1p_total_engagement",
            "coefficient": h2a_focal.get("coefficient", ""),
            "robust_se": h2a_focal.get("robust_se", ""),
            "t_stat": h2a_focal.get("t_stat", ""),
            "p_value": h2a_focal.get("p_value", ""),
            "p_stars": h2a_focal.get("p_stars", ""),
            "n_obs": h2a_focal.get("n_obs", ""),
            "r_squared": h2a_focal.get("r_squared", ""),
            "sample_definition": h2a_focal.get("sample_definition", ""),
            "interpretation_level": h2a_focal.get("interpretation_level", ""),
            "preliminary_verdict": (
                "preliminary_supported"
                if h2a_focal.get("coefficient", 0) and float(h2a_focal.get("coefficient", 0)) > 0
                and float(h2a_focal.get("p_value", 1.0)) < 0.10
                else "preliminary_not_supported"
                if h2a_focal.get("coefficient", 0)
                else "insufficient_data"
            ),
        }
    )

    # H2-2 focal
    h2b_focal = _focal_row(h2b, "H2_2_four_type_simple", "aggressive")
    rows.append(
        {
            "hypothesis": "H2",
            "sub_hypothesis": "H2_2_four_type",
            "model": "H2_2_four_type_simple",
            "focal_independent_variable": "aggressive (ref=affiliative)",
            "dependent_variable": "log1p_total_engagement",
            "coefficient": h2b_focal.get("coefficient", ""),
            "robust_se": h2b_focal.get("robust_se", ""),
            "t_stat": h2b_focal.get("t_stat", ""),
            "p_value": h2b_focal.get("p_value", ""),
            "p_stars": h2b_focal.get("p_stars", ""),
            "n_obs": h2b_focal.get("n_obs", ""),
            "r_squared": h2b_focal.get("r_squared", ""),
            "sample_definition": h2b_focal.get("sample_definition", ""),
            "interpretation_level": h2b_focal.get("interpretation_level", ""),
            "preliminary_verdict": (
                "preliminary_supported"
                if h2b_focal.get("coefficient", 0) and float(h2b_focal.get("coefficient", 0)) > 0
                and float(h2b_focal.get("p_value", 1.0)) < 0.10
                else "preliminary_not_supported"
                if h2b_focal.get("coefficient", 0)
                else "insufficient_data"
            ),
        }
    )

    # H3 focal
    h3_quad = _focal_row(h3, "H3_quadratic", "aggressive_intensity")
    h3_sq = _focal_row(h3, "H3_quadratic", "aggressive_intensity_sq")
    b1 = float(h3_quad.get("coefficient", 0) or 0)
    b2 = float(h3_sq.get("coefficient", 0) or 0)
    tp_val = h3_quad.get("turning_point", "")
    inverted_u = b1 > 0 and b2 < 0
    rows.append(
        {
            "hypothesis": "H3",
            "sub_hypothesis": "H3_inverted_U",
            "model": "H3_quadratic",
            "focal_independent_variable": "aggressive_intensity + aggressive_intensity_sq",
            "dependent_variable": "firm_mean_log1p_total_engagement",
            "coefficient": f"b1={h3_quad.get('coefficient','')} b2={h3_sq.get('coefficient','')}",
            "robust_se": f"b1_se={h3_quad.get('robust_se','')} b2_se={h3_sq.get('robust_se','')}",
            "t_stat": f"b1_t={h3_quad.get('t_stat','')} b2_t={h3_sq.get('t_stat','')}",
            "p_value": f"b1_p={h3_quad.get('p_value','')} b2_p={h3_sq.get('p_value','')}",
            "p_stars": f"b1={h3_quad.get('p_stars','')} b2={h3_sq.get('p_stars','')}",
            "n_obs": h3_quad.get("n_obs", ""),
            "r_squared": h3_quad.get("r_squared", ""),
            "sample_definition": h3_quad.get("sample_definition", ""),
            "interpretation_level": h3_quad.get("interpretation_level", ""),
            "preliminary_verdict": (
                "NOT_INTERPRETABLE"
                if h3_quad.get("interpretation_level", "") == "NOT_INTERPRETABLE"
                else "preliminary_supported_with_inverted_U"
                if inverted_u
                else "preliminary_not_supported"
            ),
        }
    )

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Simple OLS for H1/H2/H3.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Output directory (default: same dir as this script)",
    )
    args = parser.parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check input files
    for f in [H1_CORPUS, TYPE_TRAINING]:
        if not f.exists():
            print(f"ERROR: Input file not found: {f}", file=sys.stderr)
            return 1

    try:
        from scipy.special import betainc  # noqa: F401
    except ImportError:
        print("ERROR: scipy not installed", file=sys.stderr)
        return 1

    print("=== run_simple_ols_hypotheses ===")
    print("PURPOSE: PRELIMINARY DIAGNOSTIC — not final causal evidence\n")

    # Load data
    print("[DATA] Loading inputs...")
    corp_rows = load_h1_corpus()
    type_batch1 = load_type_batch1()
    joined_h2 = join_type_with_corpus(type_batch1, corp_rows)
    print(f"  H1 corpus: {len(corp_rows)} Fortune100 posts")
    print(f"  H2/H3 type labels: {len(type_batch1)} batch1 Fortune100 posts")
    print(f"  H2 joined with engagement: {len(joined_h2)} posts")
    print()

    # Run analyses
    print("[H1] Running H1 OLS...")
    h1 = run_h1(corp_rows, out_dir)

    print("[H2-1] Running H2 aggressive vs other OLS...")
    h2a = run_h2_aggressive_vs_other(joined_h2, out_dir)

    print("[H2-2] Running H2 four-type OLS...")
    h2b = run_h2_four_type(joined_h2, out_dir)

    print("[H3] Running H3 firm-level intensity OLS...")
    h3 = run_h3(corp_rows, type_batch1, out_dir)

    # Summary
    print("[SUMMARY] Building summary table...")
    summary = build_summary(h1, h2a, h2b, h3)
    write_csv(
        out_dir / "hypothesis_ols_summary.csv",
        summary,
        [
            "hypothesis", "sub_hypothesis", "model", "focal_independent_variable",
            "dependent_variable", "coefficient", "robust_se", "t_stat", "p_value",
            "p_stars", "n_obs", "r_squared", "sample_definition",
            "interpretation_level", "preliminary_verdict",
        ],
    )

    # Print summary
    print("\n=== SUMMARY ===")
    for r in summary:
        print(
            f"  {r['hypothesis']} {r['sub_hypothesis']}: "
            f"coef={r['coefficient']} p={r['p_value']} "
            f"[{r['preliminary_verdict']}]"
        )

    print(f"\n=== All outputs → {out_dir} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
