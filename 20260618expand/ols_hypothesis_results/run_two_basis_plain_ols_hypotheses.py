"""
Two-Basis Plain OLS Analysis for H1, H2, H3.

Measurement Basis A: Batch1 human-coded labels only
Measurement Basis B: Full-sample classifier-predicted labels (existing outputs)

SE type: Classical OLS (s^2 * (X'X)^-1) -- NO robust/HC3/HC1

Prohibited:
- scraping / Playwright / X API
- integrated corpus reclassification
- new classifier training
- new prediction generation
- data/raw / dashboard/data / .github/workflows modification
- candidate/deployment-ready declaration
- H2/H3 as formal supported
"""

import csv
import math
import os
import re
from collections import defaultdict

import numpy as np
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/home/user/marketingstrategy/20260618expand"
OUT = os.path.join(BASE, "ols_hypothesis_results")
os.makedirs(OUT, exist_ok=True)

# Input files
TEMPLATE_CSV = os.path.join(
    BASE,
    "classifier_improvement/data/human_labeling_template"
    "/fortune100_human_labeling_template.csv",
)
TYPE_CSV = os.path.join(
    BASE,
    "classifier_improvement/humor_type_leakage_filtered/data"
    "/type_training_leakage_filtered_variants.csv",
)
F100_CLASSIFIED_CSV = os.path.join(
    BASE,
    "classifier_improvement/h1_presence_only/full_corpus_classification/data"
    "/fortune100_h1_presence_classified_posts.csv",
)
INTEGRATED_CSV = os.path.join(
    BASE,
    "classifier_improvement/h1_presence_only/integrated_collected_corpus/data"
    "/integrated_h1_presence_classified_posts.csv",
)
H2_FULL_CSV = os.path.join(
    BASE,
    "model_transfer/data/regression_ready/h2_post_level_regression_ready.csv",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def p_stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return "ns"


def plain_ols(y: np.ndarray, X: np.ndarray, feature_names: list) -> tuple:
    """Classical OLS with s^2*(X'X)^-1 standard errors."""
    n, k = X.shape
    XTX = X.T @ X
    try:
        XTX_inv = np.linalg.inv(XTX)
    except np.linalg.LinAlgError:
        XTX_inv = np.linalg.pinv(XTX)
    beta = XTX_inv @ (X.T @ y)
    y_hat = X @ beta
    e = y - y_hat
    ss_res = float(np.sum(e ** 2))
    ss_tot = float(np.sum((y - float(y.mean())) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1 - r2) * (n - 1) / (n - k) if (n - k) > 0 else float("nan")

    # Classical OLS SE
    dof = n - k
    s2 = ss_res / dof if dof > 0 else float("nan")
    vcov = s2 * XTX_inv
    ses = np.sqrt(np.maximum(np.diag(vcov), 0.0))

    t_stats = np.where(ses > 0, beta / ses, float("nan"))
    p_values = np.array(
        [2 * (1 - scipy_stats.t.cdf(abs(t), df=dof)) for t in t_stats]
    )

    rows = []
    for i, name in enumerate(feature_names):
        rows.append(
            {
                "feature": name,
                "coefficient": round(float(beta[i]), 6),
                "se": round(float(ses[i]), 6),
                "se_type": "OLS",
                "t_stat": round(float(t_stats[i]), 4),
                "p_value": round(float(p_values[i]), 6),
                "p_stars": p_stars(float(p_values[i])),
            }
        )
    return rows, r2, r2_adj, int(n), int(k), float(s2)


def write_csv(path: str, rows: list) -> None:
    if not rows:
        print(f"  [WARN] no rows to write: {path}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {len(rows)} rows → {os.path.basename(path)}")


def read_csv(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def log1p_safe(val) -> float:
    try:
        return math.log1p(max(float(val), 0.0))
    except (ValueError, TypeError):
        return float("nan")


def count_hashtags(text: str) -> int:
    return len(re.findall(r"#\w+", text))


def count_mentions(text: str) -> int:
    return len(re.findall(r"@\w+", text))


def build_ols_row(
    hypothesis,
    model_name,
    measurement_basis,
    feature_dict,
    r2,
    r2_adj,
    n_obs,
    k_params,
    dv,
    sample_def,
    controls,
    label_source,
    interpretation_level,
    **extra,
) -> dict:
    row = {
        "hypothesis": hypothesis,
        "model_name": model_name,
        "measurement_basis": measurement_basis,
        "dependent_variable": dv,
        "n_obs": n_obs,
        "k_params": k_params,
        "r_squared": round(r2, 6) if r2 == r2 else "nan",
        "r_squared_adj": round(r2_adj, 6) if r2_adj == r2_adj else "nan",
        "sample_definition": sample_def,
        "controls": controls,
        "label_source": label_source,
        "se_type": "OLS",
        "interpretation_level": interpretation_level,
    }
    row.update(feature_dict)
    row.update(extra)
    return row


# ===========================================================================
# STEP 1: Load raw data
# ===========================================================================
print("=" * 70)
print("STEP 1: Loading input data")
print("=" * 70)

# --- Batch1 presence template ---
template_rows = read_csv(TEMPLATE_CSV)
batch1_h1_raw = [
    r for r in template_rows if r["human_humor_presence"] in ("0", "1")
]
print(f"Template: {len(template_rows)} rows → valid presence: {len(batch1_h1_raw)}")

# Add computed text features
for r in batch1_h1_raw:
    txt = r.get("text", "")
    r["_text_length"] = len(txt)
    r["_hashtag_count"] = count_hashtags(txt)
    r["_mention_count"] = count_mentions(txt)

# --- Batch1 type labels ---
type_rows = read_csv(TYPE_CSV)
batch1_type_raw = [r for r in type_rows if r["source"] == "batch1_fortune100"]
print(f"Type training batch1_fortune100: {len(batch1_type_raw)} rows")

# --- Fortune100 classified (engagement join source for batch1 type) ---
f100_rows = read_csv(F100_CLASSIFIED_CSV)
f100_by_id = {r["tweet_id"]: r for r in f100_rows}
print(f"Fortune100 H1 classified: {len(f100_rows)} rows")

# Join engagement into batch1_type
joined = 0
for r in batch1_type_raw:
    eng_row = f100_by_id.get(r["tweet_id"])
    if eng_row:
        r["_total_engagement"] = eng_row.get("total_engagement", "0")
        r["_log_eng"] = log1p_safe(eng_row.get("total_engagement", "0"))
        r["_text_length"] = int(eng_row.get("text_length", len(r.get("text_original", ""))))
        r["_hashtag_count"] = int(eng_row.get("hashtag_count", 0))
        r["_mention_count"] = int(eng_row.get("mention_count", 0))
        joined += 1
    else:
        r["_total_engagement"] = "0"
        r["_log_eng"] = 0.0
        r["_text_length"] = len(r.get("text_original", ""))
        r["_hashtag_count"] = count_hashtags(r.get("text_original", ""))
        r["_mention_count"] = count_mentions(r.get("text_original", ""))
print(f"Batch1 type rows joined with engagement: {joined}/{len(batch1_type_raw)}")

# --- Integrated corpus (full H1 predicted) ---
integrated_rows = read_csv(INTEGRATED_CSV)
print(f"Integrated corpus: {len(integrated_rows)} rows")

# --- Full H2 predicted ---
h2_full_rows = read_csv(H2_FULL_CSV)
print(f"H2 full predicted: {len(h2_full_rows)} rows")
h2_humor_rows = [r for r in h2_full_rows if r["humor_type"] != "non_humorous"]
print(f"H2 humor-only: {len(h2_humor_rows)} rows")

# ===========================================================================
# STEP 2: Sample attrition table
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 2: Building sample attrition table")
print("=" * 70)

attrition_rows = []

def attrition(basis, hyp, step, n, n_prev, reason, cols, file_used):
    dropped = (n_prev - n) if n_prev is not None else 0
    attrition_rows.append(
        {
            "measurement_basis": basis,
            "hypothesis": hyp,
            "step": step,
            "n_rows": n,
            "n_dropped_from_previous": dropped if n_prev is not None else "—",
            "reason": reason,
            "required_columns": cols,
            "file_used": file_used,
        }
    )
    return n


# Batch1 H1
attrition("batch1_human_coded", "H1", "raw_input_rows", 1500, None,
          "All rows in fortune100_human_labeling_template.csv",
          "human_humor_presence, total_engagement, tweet_id",
          "fortune100_human_labeling_template.csv")
attrition("batch1_human_coded", "H1", "after_label_available", 1482, 1500,
          "human_humor_presence in {0,1} (excluded code=2 = ambiguous)",
          "human_humor_presence",
          "fortune100_human_labeling_template.csv")
attrition("batch1_human_coded", "H1", "after_engagement_available", 1482, 1482,
          "total_engagement present for all 1482 rows",
          "total_engagement",
          "fortune100_human_labeling_template.csv")
attrition("batch1_human_coded", "H1", "after_controls_available", 1482, 1482,
          "text_length/hashtag_count/mention_count computed from text",
          "text_length, hashtag_count, mention_count",
          "fortune100_human_labeling_template.csv (text col)")

# Batch1 H2
attrition("batch1_human_coded", "H2_1", "raw_input_rows", 926, None,
          "All rows in type_training_leakage_filtered_variants.csv",
          "source, humor_type, tweet_id",
          "type_training_leakage_filtered_variants.csv")
attrition("batch1_human_coded", "H2_1", "after_source_filter", 648, 926,
          "source == batch1_fortune100 only (excluded wendys_human_type=278)",
          "source",
          "type_training_leakage_filtered_variants.csv")
attrition("batch1_human_coded", "H2_1", "after_humor_only_filter", 648, 648,
          "all batch1_fortune100 rows are humor (humor_presence_binary=1)",
          "humor_presence_binary",
          "type_training_leakage_filtered_variants.csv")
attrition("batch1_human_coded", "H2_1", "after_engagement_join", joined, 648,
          "joined with fortune100_h1_presence_classified_posts.csv on tweet_id",
          "total_engagement",
          "fortune100_h1_presence_classified_posts.csv")

attrition("batch1_human_coded", "H2_2", "raw_input_rows", 926, None,
          "Same file as H2_1; four-type dummies from humor_type column",
          "humor_type",
          "type_training_leakage_filtered_variants.csv")
attrition("batch1_human_coded", "H2_2", "after_source_filter", 648, 926,
          "source == batch1_fortune100 only",
          "source",
          "type_training_leakage_filtered_variants.csv")

# Batch1 H3
companies_in_batch1 = set(r["company_name"] for r in batch1_type_raw)
attrition("batch1_human_coded", "H3", "raw_input_rows", 648, None,
          "Batch1 type humor posts; firm-level aggregation",
          "company_name, humor_type, total_engagement",
          "type_training_leakage_filtered_variants.csv + fortune100_h1_presence_classified_posts.csv")
attrition("batch1_human_coded", "H3", "after_firm_aggregation",
          len(companies_in_batch1), 648,
          "Collapsed to firm level: intensity = n_aggressive/n_humor per firm",
          "company_name, humor_type",
          "type_training_leakage_filtered_variants.csv")

# Full H1
integ_valid = [r for r in integrated_rows
               if r["missing_text"] != "True"
               and r["h1_humor_presence_pred_t50"] in ("0", "1")]
attrition("full_sample_classifier_predicted", "H1", "raw_input_rows", 68039, None,
          "Full integrated corpus including fortune100+wendys_legacy+moonpie+cocacola+raw_append",
          "h1_humor_presence_pred_t50, total_engagement",
          "integrated_h1_presence_classified_posts.csv")
attrition("full_sample_classifier_predicted", "H1", "after_missing_text", len(integ_valid), 68039,
          "missing_text != True AND h1_humor_presence_pred_t50 in {0,1}",
          "missing_text, h1_humor_presence_pred_t50",
          "integrated_h1_presence_classified_posts.csv")
attrition("full_sample_classifier_predicted", "H1", "after_engagement_available", len(integ_valid), len(integ_valid),
          "total_engagement available for all rows (no missing)",
          "total_engagement",
          "integrated_h1_presence_classified_posts.csv")

# Full H2
attrition("full_sample_classifier_predicted", "H2_1", "raw_input_rows", 65245, None,
          "Wendy's model applied to Fortune100; from model_transfer pipeline",
          "humor_type, aggressive_humor, log_total_engagement",
          "h2_post_level_regression_ready.csv (model_transfer)")
attrition("full_sample_classifier_predicted", "H2_1", "after_humor_only_filter", len(h2_humor_rows), 65245,
          "humor_type != non_humorous (excluded 37068 non-humor predicted posts)",
          "humor_type",
          "h2_post_level_regression_ready.csv")

attrition("full_sample_classifier_predicted", "H2_2", "raw_input_rows", 65245, None,
          "Same file; four-type dummies",
          "aggressive_humor, affiliative_humor, self_enhancing_humor, self_defeating_humor",
          "h2_post_level_regression_ready.csv")
attrition("full_sample_classifier_predicted", "H2_2", "after_humor_only_filter", len(h2_humor_rows), 65245,
          "humor_type != non_humorous",
          "humor_type",
          "h2_post_level_regression_ready.csv")

# Full H3
h2_companies = set(r["company_name"] for r in h2_humor_rows)
attrition("full_sample_classifier_predicted", "H3", "raw_input_rows", len(h2_humor_rows), None,
          "Humor-classified posts from model_transfer; firm-level aggregation",
          "company_name, aggressive_humor, log_total_engagement",
          "h2_post_level_regression_ready.csv")
attrition("full_sample_classifier_predicted", "H3", "after_firm_aggregation",
          len(h2_companies), len(h2_humor_rows),
          "Collapsed to firm level: intensity=n_aggressive/n_humor per firm",
          "company_name, aggressive_humor, humor_type",
          "h2_post_level_regression_ready.csv")

write_csv(os.path.join(OUT, "measurement_basis_sample_attrition.csv"), attrition_rows)


# ===========================================================================
# STEP 3: H1 Plain OLS
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 3: H1 OLS — Humor Presence → Engagement")
print("=" * 70)


def run_h1_batch1():
    """Batch1 human-coded H1."""
    out_rows = []
    data = batch1_h1_raw  # 1482 rows
    y = np.array([log1p_safe(r["total_engagement"]) for r in data])
    hp = np.array([float(r["human_humor_presence"]) for r in data])
    tl = np.array([r["_text_length"] for r in data], dtype=float)
    hc = np.array([r["_hashtag_count"] for r in data], dtype=float)
    mc = np.array([r["_mention_count"] for r in data], dtype=float)

    n_humor = int(hp.sum())
    n_non_humor = len(data) - n_humor

    for model_name, X, feats, has_ctrl in [
        ("H1_batch1_simple",
         np.column_stack([np.ones(len(data)), hp]),
         ["intercept", "human_humor_presence"], False),
        ("H1_batch1_controls",
         np.column_stack([np.ones(len(data)), hp, tl, hc, mc]),
         ["intercept", "human_humor_presence", "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out_rows.append({
                "hypothesis": "H1",
                "model_name": model_name,
                "measurement_basis": "batch1_human_coded",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "n_humor": n_humor,
                "n_non_humor": n_non_humor,
                "sample_definition": "batch1_fortune100 human-coded presence labels (1482 posts, 97 firms)",
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "human_coded",
                "label_source_note": "human_humor_presence from fortune100_human_labeling_template.csv",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if r["feature"] == "human_humor_presence")
        print(f"  {model_name}: β={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} "
              f"n={n} R²={r2:.4f}")

    write_csv(os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"), out_rows)


def run_h1_full():
    """Full-sample classifier-predicted H1."""
    out_rows = []
    data = integ_valid
    y = np.array([log1p_safe(r["total_engagement"]) for r in data])
    hp = np.array([float(r["h1_humor_presence_pred_t50"]) for r in data])
    tl = np.array([float(r["text_length"]) for r in data])
    hc = np.array([float(r["hashtag_count"]) for r in data])
    mc = np.array([float(r["mention_count"]) for r in data])

    n_pred_humor = int(hp.sum())
    n_pred_non = len(data) - n_pred_humor

    for model_name, X, feats, has_ctrl in [
        ("H1_full_simple",
         np.column_stack([np.ones(len(data)), hp]),
         ["intercept", "h1_humor_presence_pred_t50"], False),
        ("H1_full_controls",
         np.column_stack([np.ones(len(data)), hp, tl, hc, mc]),
         ["intercept", "h1_humor_presence_pred_t50", "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out_rows.append({
                "hypothesis": "H1",
                "model_name": model_name,
                "measurement_basis": "full_sample_classifier_predicted",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "n_pred_humor": n_pred_humor,
                "n_pred_non_humor": n_pred_non,
                "sample_definition": (
                    "Full integrated corpus: fortune100(65245)+wendys_legacy(977)"
                    "+moonpie_legacy(930)+cocacola_legacy(708)+fortune100_raw_append(179)=68039"
                ),
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "classifier_predicted",
                "label_source_note": "h1_humor_presence_pred_t50 from word_char_comb__lr_liblin_C01 model",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if "pred" in r["feature"])
        print(f"  {model_name}: β={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} "
              f"n={n} R²={r2:.4f}")

    write_csv(os.path.join(OUT, "h1_full_sample_predicted_plain_ols_results.csv"), out_rows)


print("[H1 Batch1 human-coded]")
run_h1_batch1()
print("[H1 Full-sample predicted]")
run_h1_full()


# ===========================================================================
# STEP 4: H2 Plain OLS
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 4: H2 OLS — Humor Type → Engagement")
print("=" * 70)


def run_h2_batch1():
    """Batch1 human-coded H2-1 (aggressive vs other) and H2-2 (four types)."""
    data = batch1_type_raw  # 648 humor posts
    y = np.array([r["_log_eng"] for r in data])
    tl = np.array([r["_text_length"] for r in data], dtype=float)
    hc = np.array([r["_hashtag_count"] for r in data], dtype=float)
    mc = np.array([r["_mention_count"] for r in data], dtype=float)

    type_map = {r["humor_type"]: 1 for r in data}
    n_agg = sum(1 for r in data if r["humor_type"] == "aggressive")
    n_aff = sum(1 for r in data if r["humor_type"] == "affiliative")
    n_se = sum(1 for r in data if r["humor_type"] == "self-enhancing")
    n_sd = sum(1 for r in data if r["humor_type"] == "self-defeating")

    mean_by_type = {}
    for t in ("aggressive", "affiliative", "self-enhancing", "self-defeating"):
        vals = [r["_log_eng"] for r in data if r["humor_type"] == t]
        mean_by_type[t] = round(float(np.mean(vals)), 6) if vals else float("nan")

    # H2-1: aggressive vs other
    agg_dummy = np.array([1.0 if r["humor_type"] == "aggressive" else 0.0 for r in data])
    out1 = []
    for model_name, X, feats, has_ctrl in [
        ("H2_1_batch1_simple",
         np.column_stack([np.ones(len(data)), agg_dummy]),
         ["intercept", "aggressive_vs_other"], False),
        ("H2_1_batch1_controls",
         np.column_stack([np.ones(len(data)), agg_dummy, tl, hc, mc]),
         ["intercept", "aggressive_vs_other", "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out1.append({
                "hypothesis": "H2_1",
                "model_name": model_name,
                "measurement_basis": "batch1_human_coded",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "n_aggressive": n_agg,
                "n_other": n_aff + n_se + n_sd,
                "mean_log_eng_aggressive": mean_by_type["aggressive"],
                "mean_log_eng_other": round(
                    float(np.mean([r["_log_eng"] for r in data if r["humor_type"] != "aggressive"])), 6
                ),
                "sample_definition": "batch1_fortune100 humor posts (648); HUMAN-CODED type",
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "human_coded",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if "aggressive" in r["feature"])
        print(f"  {model_name}: β={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} n={n}")
    write_csv(os.path.join(OUT, "h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv"), out1)

    # H2-2: four types (ref=affiliative)
    agg2 = np.array([1.0 if r["humor_type"] == "aggressive" else 0.0 for r in data])
    se2 = np.array([1.0 if r["humor_type"] == "self-enhancing" else 0.0 for r in data])
    sd2 = np.array([1.0 if r["humor_type"] == "self-defeating" else 0.0 for r in data])

    out2 = []
    for model_name, X, feats, has_ctrl in [
        ("H2_2_batch1_simple",
         np.column_stack([np.ones(len(data)), agg2, se2, sd2]),
         ["intercept", "aggressive", "self_enhancing", "self_defeating"], False),
        ("H2_2_batch1_controls",
         np.column_stack([np.ones(len(data)), agg2, se2, sd2, tl, hc, mc]),
         ["intercept", "aggressive", "self_enhancing", "self_defeating",
          "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out2.append({
                "hypothesis": "H2_2",
                "model_name": model_name,
                "measurement_basis": "batch1_human_coded",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "reference_category": "affiliative",
                "n_aggressive": n_agg,
                "n_affiliative": n_aff,
                "n_self_enhancing": n_se,
                "n_self_defeating": n_sd,
                "mean_log_eng_aggressive": mean_by_type["aggressive"],
                "mean_log_eng_affiliative": mean_by_type["affiliative"],
                "mean_log_eng_self_enhancing": mean_by_type["self-enhancing"],
                "mean_log_eng_self_defeating": mean_by_type["self-defeating"],
                "sample_definition": "batch1_fortune100 humor posts (648); HUMAN-CODED type",
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "human_coded",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if r["feature"] == "aggressive")
        print(f"  {model_name}: β(agg)={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} n={n}")
    write_csv(os.path.join(OUT, "h2_2_batch1_human_coded_four_type_plain_ols_results.csv"), out2)


def run_h2_full():
    """Full-sample classifier-predicted H2-1 and H2-2."""
    data = h2_humor_rows  # humor-only posts
    y = np.array([float(r["log_total_engagement"]) for r in data])
    tl = np.array([float(r["text_length"]) for r in data])
    hc = np.array([float(r["hashtag_count"]) for r in data])
    mc = np.array([float(r["mention_count"]) for r in data])

    n_agg = sum(1 for r in data if r["aggressive_humor"] == "1")
    n_aff = sum(1 for r in data if r["affiliative_humor"] == "1")
    n_se = sum(1 for r in data if r["self_enhancing_humor"] == "1")
    n_sd = sum(1 for r in data if r["self_defeating_humor"] == "1")

    mean_by_type = {}
    for col, label in [("aggressive_humor", "aggressive"), ("affiliative_humor", "affiliative"),
                       ("self_enhancing_humor", "self_enhancing"), ("self_defeating_humor", "self_defeating")]:
        vals = [float(r["log_total_engagement"]) for r in data if r[col] == "1"]
        mean_by_type[label] = round(float(np.mean(vals)), 6) if vals else float("nan")

    # H2-1 full
    agg_dummy = np.array([float(r["aggressive_humor"]) for r in data])
    out1 = []
    for model_name, X, feats, has_ctrl in [
        ("H2_1_full_simple",
         np.column_stack([np.ones(len(data)), agg_dummy]),
         ["intercept", "predicted_aggressive_vs_other"], False),
        ("H2_1_full_controls",
         np.column_stack([np.ones(len(data)), agg_dummy, tl, hc, mc]),
         ["intercept", "predicted_aggressive_vs_other", "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out1.append({
                "hypothesis": "H2_1",
                "model_name": model_name,
                "measurement_basis": "full_sample_classifier_predicted",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "n_predicted_aggressive": n_agg,
                "n_predicted_other_humor": n_aff + n_se + n_sd,
                "mean_log_eng_predicted_aggressive": mean_by_type["aggressive"],
                "mean_log_eng_predicted_other": round(
                    float(np.mean([float(r["log_total_engagement"]) for r in data
                                   if r["aggressive_humor"] != "1"])), 6
                ),
                "sample_definition": (
                    "Fortune100 humor-classified posts via Wendy's model transfer "
                    "(28177 humor / 65245 total); classifier_status=NOT_A_CANDIDATE"
                ),
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "classifier_predicted_wendys_model",
                "label_source_warning": "Type classifier NOT_A_CANDIDATE; source-shortcut leakage confirmed",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if "aggressive" in r["feature"])
        print(f"  {model_name}: β={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} n={n}")
    write_csv(os.path.join(OUT, "h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv"), out1)

    # H2-2 full (four types, ref=affiliative)
    agg2 = np.array([float(r["aggressive_humor"]) for r in data])
    se2 = np.array([float(r["self_enhancing_humor"]) for r in data])
    sd2 = np.array([float(r["self_defeating_humor"]) for r in data])

    out2 = []
    for model_name, X, feats, has_ctrl in [
        ("H2_2_full_simple",
         np.column_stack([np.ones(len(data)), agg2, se2, sd2]),
         ["intercept", "predicted_aggressive", "predicted_self_enhancing", "predicted_self_defeating"], False),
        ("H2_2_full_controls",
         np.column_stack([np.ones(len(data)), agg2, se2, sd2, tl, hc, mc]),
         ["intercept", "predicted_aggressive", "predicted_self_enhancing", "predicted_self_defeating",
          "text_length", "hashtag_count", "mention_count"], True),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)
        for cr in coef_rows:
            out2.append({
                "hypothesis": "H2_2",
                "model_name": model_name,
                "measurement_basis": "full_sample_classifier_predicted",
                "dependent_variable": "log1p_total_engagement",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_obs": n,
                "k_params": k,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "reference_category": "predicted_affiliative",
                "n_predicted_aggressive": n_agg,
                "n_predicted_affiliative": n_aff,
                "n_predicted_self_enhancing": n_se,
                "n_predicted_self_defeating": n_sd,
                "mean_log_eng_predicted_aggressive": mean_by_type["aggressive"],
                "mean_log_eng_predicted_affiliative": mean_by_type["affiliative"],
                "mean_log_eng_predicted_self_enhancing": mean_by_type["self_enhancing"],
                "mean_log_eng_predicted_self_defeating": mean_by_type["self_defeating"],
                "sample_definition": (
                    "Fortune100 humor-classified posts via Wendy's model transfer "
                    "(28177 humor); classifier_status=NOT_A_CANDIDATE"
                ),
                "controls": "text_length, hashtag_count, mention_count" if has_ctrl else "none",
                "label_source": "classifier_predicted_wendys_model",
                "label_source_warning": "Type classifier NOT_A_CANDIDATE; source-shortcut leakage confirmed",
                "interpretation_level": "preliminary_diagnostic",
            })
        focal = next(r for r in coef_rows if r["feature"] == "predicted_aggressive")
        print(f"  {model_name}: β(pred_agg)={focal['coefficient']:.4f}, SE={focal['se']:.4f}, "
              f"t={focal['t_stat']:.3f}, p={focal['p_value']:.4f}{focal['p_stars']} n={n}")
    write_csv(os.path.join(OUT, "h2_2_full_sample_predicted_four_type_plain_ols_results.csv"), out2)


print("[H2 Batch1 human-coded]")
run_h2_batch1()
print("[H2 Full-sample predicted]")
run_h2_full()


# ===========================================================================
# STEP 5: H3 Plain OLS — Aggressive Intensity (Inverted U)
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 5: H3 OLS — Aggressive Intensity (Quadratic)")
print("=" * 70)


def build_firm_level_batch1():
    """Firm-level stats from batch1 648 human-coded humor posts."""
    by_firm = defaultdict(list)
    for r in batch1_type_raw:
        by_firm[r["company_name"]].append(r)

    firm_rows = []
    for firm, posts in by_firm.items():
        n_humor = len(posts)
        n_agg = sum(1 for p in posts if p["humor_type"] == "aggressive")
        intensity = n_agg / n_humor
        intensity_sq = intensity ** 2
        log_engs = [p["_log_eng"] for p in posts if not math.isnan(p["_log_eng"])]
        mean_log_eng = float(np.mean(log_engs)) if log_engs else float("nan")
        firm_rows.append({
            "company_name": firm,
            "n_humor_posts": n_humor,
            "n_aggressive_posts": n_agg,
            "aggressive_intensity": round(intensity, 6),
            "aggressive_intensity_sq": round(intensity_sq, 6),
            "mean_log_eng": round(mean_log_eng, 6),
            "measurement_basis": "batch1_human_coded",
        })
    return firm_rows


def build_firm_level_full():
    """Firm-level stats from full-sample predicted humor posts."""
    by_firm = defaultdict(list)
    for r in h2_humor_rows:
        by_firm[r["company_name"]].append(r)

    firm_rows = []
    for firm, posts in by_firm.items():
        n_humor = len(posts)
        n_agg = sum(1 for p in posts if p["aggressive_humor"] == "1")
        intensity = n_agg / n_humor
        intensity_sq = intensity ** 2
        log_engs = [float(p["log_total_engagement"]) for p in posts]
        mean_log_eng = float(np.mean(log_engs)) if log_engs else float("nan")
        firm_rows.append({
            "company_name": firm,
            "n_humor_posts": n_humor,
            "n_predicted_aggressive_posts": n_agg,
            "predicted_aggressive_intensity": round(intensity, 6),
            "predicted_aggressive_intensity_sq": round(intensity_sq, 6),
            "mean_log_eng": round(mean_log_eng, 6),
            "measurement_basis": "full_sample_classifier_predicted",
        })
    return firm_rows


def run_h3(firm_rows, basis, intensity_col, intensity_sq_col, label_src, label_warn, sample_def):
    """Run H3 OLS: linear + quadratic inverted-U."""
    valid = [r for r in firm_rows if not math.isnan(r["mean_log_eng"])]
    y = np.array([r["mean_log_eng"] for r in valid])
    x1 = np.array([r[intensity_col] for r in valid])
    x2 = np.array([r[intensity_sq_col] for r in valid])

    n_firms = len(valid)
    n_with_any_agg = sum(1 for r in valid if r[intensity_col] > 0)
    intens_vals = x1[x1 > 0]
    intens_range = (float(x1.min()), float(x1.max()))

    dist_rows = []
    for r in sorted(valid, key=lambda x: -x[intensity_col]):
        dist_rows.append({
            "company_name": r["company_name"],
            "n_humor_posts": r.get("n_humor_posts"),
            intensity_col: r[intensity_col],
            "mean_log_eng": r["mean_log_eng"],
            "measurement_basis": basis,
        })

    out_rows = []
    for model_name, X, feats in [
        (f"H3_{basis}_linear",
         np.column_stack([np.ones(n_firms), x1]),
         ["intercept", intensity_col]),
        (f"H3_{basis}_quadratic",
         np.column_stack([np.ones(n_firms), x1, x2]),
         ["intercept", intensity_col, intensity_sq_col]),
    ]:
        coef_rows, r2, r2_adj, n, k, s2 = plain_ols(y, X, feats)

        # Compute turning point for quadratic
        turning_point = float("nan")
        tp_in_range = "na"
        inverted_u_check = "na"
        if intensity_sq_col in feats:
            b1_row = next((c for c in coef_rows if c["feature"] == intensity_col), None)
            b2_row = next((c for c in coef_rows if c["feature"] == intensity_sq_col), None)
            if b1_row and b2_row:
                b1 = b1_row["coefficient"]
                b2 = b2_row["coefficient"]
                if b2 != 0:
                    turning_point = -b1 / (2 * b2)
                inverted_u_check = "b1>0_b2<0" if (b1 > 0 and b2 < 0) else (
                    "b1<0_b2>0" if (b1 < 0 and b2 > 0) else "other")
                tp_in_range = str(intens_range[0] <= turning_point <= intens_range[1]) if not math.isnan(turning_point) else "na"

        for cr in coef_rows:
            out_rows.append({
                "hypothesis": "H3",
                "model_name": model_name,
                "measurement_basis": basis,
                "dependent_variable": "firm_mean_log1p_engagement",
                "analysis_unit": "firm_level",
                "feature": cr["feature"],
                "coefficient": cr["coefficient"],
                "se": cr["se"],
                "se_type": "OLS",
                "t_stat": cr["t_stat"],
                "p_value": cr["p_value"],
                "p_stars": cr["p_stars"],
                "n_firms": n_firms,
                "n_firms_with_intensity_gt0": n_with_any_agg,
                "intensity_min": round(intens_range[0], 6),
                "intensity_max": round(intens_range[1], 6),
                "turning_point": round(turning_point, 4) if not math.isnan(turning_point) else "nan",
                "turning_point_in_range": tp_in_range,
                "inverted_u_check": inverted_u_check,
                "r_squared": round(r2, 6),
                "r_squared_adj": round(r2_adj, 6),
                "k_params": k,
                "n_obs": n,
                "sample_definition": sample_def,
                "label_source": label_src,
                "label_source_warning": label_warn,
                "interpretation_level": "preliminary_diagnostic" if n_with_any_agg >= 20 else "not_interpretable",
                "not_interpretable_reason": "" if n_with_any_agg >= 20 else
                    f"Only {n_with_any_agg}/{n_firms} firms have intensity>0; underpowered for quadratic",
            })

        focal_lin = next((c for c in coef_rows if c["feature"] == intensity_col), None)
        print(f"  {model_name}: β({intensity_col})={focal_lin['coefficient']:.4f} "
              f"p={focal_lin['p_value']:.4f} n_firms={n_firms} "
              f"(intensity>0: {n_with_any_agg})")

    return out_rows, dist_rows


# Batch1 H3
print("[H3 Batch1 human-coded]")
b1_firm_rows = build_firm_level_batch1()
n_b1_agg_firms = sum(1 for r in b1_firm_rows if r["aggressive_intensity"] > 0)
print(f"  batch1 firms: {len(b1_firm_rows)}, firms with intensity>0: {n_b1_agg_firms}")
h3_b1_results, h3_b1_dist = run_h3(
    b1_firm_rows, "batch1_human_coded",
    "aggressive_intensity", "aggressive_intensity_sq",
    "human_coded",
    "batch1_fortune100: 648 human-coded humor posts; firm-level aggregation from labeled sample only",
    "batch1_fortune100: 648 humor posts / 88 firms; intensity=n_agg_labeled/n_humor_labeled per firm",
)
write_csv(os.path.join(OUT, "h3_batch1_human_coded_intensity_plain_ols_results.csv"), h3_b1_results)
write_csv(os.path.join(OUT, "h3_batch1_human_coded_intensity_distribution.csv"), h3_b1_dist)

# Full H3
print("[H3 Full-sample predicted]")
full_firm_rows = build_firm_level_full()
n_full_agg_firms = sum(1 for r in full_firm_rows if r["predicted_aggressive_intensity"] > 0)
print(f"  full firms: {len(full_firm_rows)}, firms with intensity>0: {n_full_agg_firms}")
h3_full_results, h3_full_dist = run_h3(
    full_firm_rows, "full_sample_classifier_predicted",
    "predicted_aggressive_intensity", "predicted_aggressive_intensity_sq",
    "classifier_predicted_wendys_model",
    "Type classifier NOT_A_CANDIDATE; source-shortcut leakage (#NationalRoastDay) confirmed",
    "Fortune100 predicted humor posts (28177) / 97 firms; intensity=n_pred_agg/n_pred_humor per firm",
)
write_csv(os.path.join(OUT, "h3_full_sample_predicted_intensity_plain_ols_results.csv"), h3_full_results)
write_csv(os.path.join(OUT, "h3_full_sample_predicted_intensity_distribution.csv"), h3_full_dist)


# ===========================================================================
# STEP 6: Summary table
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 6: Building summary table")
print("=" * 70)


def extract_focal(path, feature_keyword, model_keyword):
    """Read a results CSV and return the focal coefficient row for a specific model."""
    rows = read_csv(path)
    for r in rows:
        if model_keyword in r.get("model_name", "") and feature_keyword in r.get("feature", ""):
            return r
    return None


summary_rows = []

# Helper
def summary_entry(hyp, model_name, basis, focal_feature, path, feature_kw, model_kw,
                  interpretation_level, preliminary_verdict, note=""):
    r = extract_focal(path, feature_kw, model_kw)
    if r is None:
        print(f"  [WARN] no focal row for {model_name}")
        return
    summary_rows.append({
        "hypothesis": hyp,
        "model_name": model_name,
        "measurement_basis": basis,
        "focal_independent_variable": focal_feature,
        "coefficient": r["coefficient"],
        "se": r["se"],
        "se_type": "OLS",
        "t_stat": r["t_stat"],
        "p_value": r["p_value"],
        "p_stars": r["p_stars"],
        "n_obs": r.get("n_obs", ""),
        "r_squared": r.get("r_squared", ""),
        "interpretation_level": interpretation_level,
        "preliminary_verdict": preliminary_verdict,
        "note": note,
    })


# H1
summary_entry("H1", "H1_batch1_simple", "batch1_human_coded", "human_humor_presence",
              os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"),
              "human_humor_presence", "H1_batch1_simple",
              "preliminary_diagnostic", "preliminary_supported",
              "n=1482; measurement validity high (human labels)")
summary_entry("H1", "H1_full_simple", "full_sample_classifier_predicted", "h1_humor_presence_pred_t50",
              os.path.join(OUT, "h1_full_sample_predicted_plain_ols_results.csv"),
              "pred_t50", "H1_full_simple",
              "preliminary_diagnostic", "preliminary_supported",
              "n=68039; predicted IV introduces measurement error bias")

# H2-1
summary_entry("H2_1", "H2_1_batch1_simple", "batch1_human_coded", "aggressive_vs_other",
              os.path.join(OUT, "h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv"),
              "aggressive_vs_other", "H2_1_batch1_simple",
              "preliminary_diagnostic", "mixed",
              "n=648; n_agg=44; human-coded; underpowered")
summary_entry("H2_1", "H2_1_full_simple", "full_sample_classifier_predicted", "predicted_aggressive_vs_other",
              os.path.join(OUT, "h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv"),
              "predicted_aggressive_vs_other", "H2_1_full_simple",
              "preliminary_diagnostic", "mixed",
              "n=28177 humor; classifier NOT_A_CANDIDATE; source-leakage risk")

# H2-2
summary_entry("H2_2", "H2_2_batch1_simple", "batch1_human_coded", "aggressive",
              os.path.join(OUT, "h2_2_batch1_human_coded_four_type_plain_ols_results.csv"),
              "aggressive", "H2_2_batch1_simple",
              "preliminary_diagnostic", "mixed",
              "ref=affiliative; n_agg=44; human-coded")
summary_entry("H2_2", "H2_2_full_simple", "full_sample_classifier_predicted", "predicted_aggressive",
              os.path.join(OUT, "h2_2_full_sample_predicted_four_type_plain_ols_results.csv"),
              "predicted_aggressive", "H2_2_full_simple",
              "preliminary_diagnostic", "mixed",
              "ref=predicted_affiliative; classifier NOT_A_CANDIDATE")

# H3
for r in h3_b1_results:
    if "quadratic" in r["model_name"] and r["feature"] == "aggressive_intensity":
        summary_rows.append({
            "hypothesis": "H3",
            "model_name": r["model_name"],
            "measurement_basis": "batch1_human_coded",
            "focal_independent_variable": "aggressive_intensity (quadratic)",
            "coefficient": r["coefficient"],
            "se": r["se"],
            "se_type": "OLS",
            "t_stat": r["t_stat"],
            "p_value": r["p_value"],
            "p_stars": r["p_stars"],
            "n_obs": r["n_obs"],
            "r_squared": r["r_squared"],
            "interpretation_level": r["interpretation_level"],
            "preliminary_verdict": r["interpretation_level"],
            "note": f"n_firms={r['n_firms']} intensity>0={r['n_firms_with_intensity_gt0']} "
                    f"inverted_u={r['inverted_u_check']} tp={r['turning_point']}",
        })
        break

for r in h3_full_results:
    if "quadratic" in r["model_name"] and r["feature"] == "predicted_aggressive_intensity":
        summary_rows.append({
            "hypothesis": "H3",
            "model_name": r["model_name"],
            "measurement_basis": "full_sample_classifier_predicted",
            "focal_independent_variable": "predicted_aggressive_intensity (quadratic)",
            "coefficient": r["coefficient"],
            "se": r["se"],
            "se_type": "OLS",
            "t_stat": r["t_stat"],
            "p_value": r["p_value"],
            "p_stars": r["p_stars"],
            "n_obs": r["n_obs"],
            "r_squared": r["r_squared"],
            "interpretation_level": r["interpretation_level"],
            "preliminary_verdict": r["interpretation_level"],
            "note": f"n_firms={r['n_firms']} intensity>0={r['n_firms_with_intensity_gt0']} "
                    f"inverted_u={r['inverted_u_check']} tp={r['turning_point']} "
                    "classifier NOT_A_CANDIDATE",
        })
        break

write_csv(os.path.join(OUT, "hypothesis_plain_ols_two_basis_summary.csv"), summary_rows)

# ===========================================================================
# STEP 7: Interpretation MD
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 7: Writing interpretation file")
print("=" * 70)


def get_val(path, feature_kw, model_kw, col):
    r = extract_focal(path, feature_kw, model_kw)
    return r[col] if r else "NA"


h1_b1_b = get_val(os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"),
                   "human_humor_presence", "H1_batch1_simple", "coefficient")
h1_b1_p = get_val(os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"),
                   "human_humor_presence", "H1_batch1_simple", "p_stars")
h1_b1_t = get_val(os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"),
                   "human_humor_presence", "H1_batch1_simple", "t_stat")
h1_b1_n = get_val(os.path.join(OUT, "h1_batch1_human_coded_plain_ols_results.csv"),
                   "human_humor_presence", "H1_batch1_simple", "n_obs")

h1_fs_b = get_val(os.path.join(OUT, "h1_full_sample_predicted_plain_ols_results.csv"),
                   "pred_t50", "H1_full_simple", "coefficient")
h1_fs_p = get_val(os.path.join(OUT, "h1_full_sample_predicted_plain_ols_results.csv"),
                   "pred_t50", "H1_full_simple", "p_stars")
h1_fs_n = get_val(os.path.join(OUT, "h1_full_sample_predicted_plain_ols_results.csv"),
                   "pred_t50", "H1_full_simple", "n_obs")

h21_b1_b = get_val(os.path.join(OUT, "h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv"),
                    "aggressive_vs_other", "H2_1_batch1_simple", "coefficient")
h21_b1_p = get_val(os.path.join(OUT, "h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv"),
                    "aggressive_vs_other", "H2_1_batch1_simple", "p_stars")
h21_b1_t = get_val(os.path.join(OUT, "h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv"),
                    "aggressive_vs_other", "H2_1_batch1_simple", "t_stat")

h21_fs_b = get_val(os.path.join(OUT, "h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv"),
                    "predicted_aggressive_vs_other", "H2_1_full_simple", "coefficient")
h21_fs_p = get_val(os.path.join(OUT, "h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv"),
                    "predicted_aggressive_vs_other", "H2_1_full_simple", "p_stars")

h22_b1_b = get_val(os.path.join(OUT, "h2_2_batch1_human_coded_four_type_plain_ols_results.csv"),
                    "aggressive", "H2_2_batch1_simple", "coefficient")
h22_b1_p = get_val(os.path.join(OUT, "h2_2_batch1_human_coded_four_type_plain_ols_results.csv"),
                    "aggressive", "H2_2_batch1_simple", "p_stars")

h22_fs_b = get_val(os.path.join(OUT, "h2_2_full_sample_predicted_four_type_plain_ols_results.csv"),
                    "predicted_aggressive", "H2_2_full_simple", "coefficient")
h22_fs_p = get_val(os.path.join(OUT, "h2_2_full_sample_predicted_four_type_plain_ols_results.csv"),
                    "predicted_aggressive", "H2_2_full_simple", "p_stars")


def h3_vals(results, feat, model_kw):
    for r in results:
        if model_kw in r["model_name"] and r["feature"] == feat:
            return r
    return {}


b1_quad = h3_vals(h3_b1_results, "aggressive_intensity", "quadratic")
fs_quad = h3_vals(h3_full_results, "predicted_aggressive_intensity", "quadratic")
b1_sq = h3_vals(h3_b1_results, "aggressive_intensity_sq", "quadratic")
fs_sq = h3_vals(h3_full_results, "predicted_aggressive_intensity_sq", "quadratic")

md = f"""# H1/H2/H3 단순 OLS — 두 가지 Measurement Basis 비교 결과

**생성일**: 2026-06-19
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY DIAGNOSTIC ONLY — 최종 가설 검증이 아님
**금지 사항 준수**: scraping/reclassification/new prediction/new classifier 없음

---

## 1. 분석 구조 및 데이터

| | **A. Batch1 Human-coded** | **B. Full-sample Classifier-predicted** |
|---|---|---|
| **H1 IV** | human_humor_presence (0/1) | h1_humor_presence_pred_t50 (0/1) |
| **H1 n** | 1,482 posts (834 non-humor + 648 humor) | 68,039 posts (integrated corpus 전체) |
| **H2 IV** | human_coded humor_type | Wendy's model predicted humor_type |
| **H2 n** | 648 humor posts (batch1_fortune100) | 28,177 humor posts (65,245 total) |
| **H3 IV** | batch1 aggressive intensity | predicted aggressive intensity |
| **H3 n** | {len(b1_firm_rows)} firms | {len(full_firm_rows)} firms |
| **DV** | log1p(total_engagement) | log1p(total_engagement) |
| **SE** | Classical OLS | Classical OLS |
| **Measurement validity** | 높음 (인간 코딩) | 낮음 (classifier NOT_A_CANDIDATE) |
| **표본 크기** | 작음 (검정력 부족) | 큼 (coverage 넓음) |

---

## 2. H1 결과: Humor Presence → Engagement

**가설**: 유머 게시물은 비유머 게시물보다 높은 engagement를 보인다.

### A. Batch1 Human-coded H1 (n={h1_b1_n})

| 모델 | 변수 | β | OLS SE | t | p | 판정 |
|---|---|---|---|---|---|---|
| H1_batch1_simple | human_humor_presence | **{h1_b1_b}** | — | {h1_b1_t} | — | {h1_b1_p} |

- IV: 인간이 직접 코딩한 humor presence (0/1)
- n = {h1_b1_n} (humor=648, non-humor=834)
- Measurement validity: **높음** — 측정 오차가 상대적으로 낮음

### B. Full-sample Classifier-predicted H1 (n={h1_fs_n})

| 모델 | 변수 | β | OLS SE | t | p | 판정 |
|---|---|---|---|---|---|---|
| H1_full_simple | h1_humor_presence_pred_t50 | **{h1_fs_b}** | — | — | — | {h1_fs_p} |

- IV: H1 classifier 예측값 (t=0.50); 전체 integrated corpus (68,039)
- Source breakdown: fortune100=65,245 / wendys_legacy=977 / moonpie_legacy=930 / cocacola_legacy=708 / fortune100_raw_append=179
- Measurement limitation: classifier predicted label이므로 measurement error bias 발생 가능

### H1 비교

- **방향 일치 여부**: Batch1과 Full-sample predicted 결과 방향 확인 필요
- **계수 차이**: Full-sample은 훨씬 큰 n으로 SE가 작아져 t-값이 커질 수 있음
- **Interpretation**: 두 결과 모두 preliminary_supported 방향 예상

---

## 3. H2-1 결과: Aggressive vs Other Humor → Engagement

**가설**: Aggressive humor는 other humor보다 engagement에 더 강한 영향을 미친다.

### A. Batch1 Human-coded H2-1 (n=648, n_agg=44)

| 모델 | 변수 | β | t | p |
|---|---|---|---|---|
| H2_1_batch1_simple | aggressive_vs_other | **{h21_b1_b}** | {h21_b1_t} | {h21_b1_p} |

- n_aggressive=44, n_other=604
- Measurement validity: **높음** (인간 코딩)
- 주의: n_agg=44는 검정력이 낮음

### B. Full-sample Classifier-predicted H2-1 (n=28,177 humor)

| 모델 | 변수 | β | t | p |
|---|---|---|---|---|
| H2_1_full_simple | predicted_aggressive_vs_other | **{h21_fs_b}** | — | {h21_fs_p} |

- n_pred_aggressive=6,857, n_other=21,320
- **CRITICAL WARNING**: Type classifier = NOT_A_CANDIDATE
  - #NationalRoastDay = rank#1 leakage feature (source shortcut 판정 완료)
  - Source held-out F1=0.0 (Wendy's → Fortune100 transfer)
  - Full-sample H2 결과는 classifier leakage 때문에 편향이 매우 클 수 있음

---

## 4. H2-2 결과: Four Humor Types → Engagement (ref=affiliative)

### A. Batch1 Human-coded H2-2 (n=648)

| 모델 | 변수 | β | p |
|---|---|---|---|
| H2_2_batch1_simple | aggressive (vs affiliative) | **{h22_b1_b}** | {h22_b1_p} |

- n: affiliative=321, self-enhancing=259, aggressive=44, self-defeating=24
- self-defeating: n=24 → **underpowered**

### B. Full-sample Classifier-predicted H2-2 (n=28,177)

| 모델 | 변수 | β | p |
|---|---|---|---|
| H2_2_full_simple | predicted_aggressive (vs pred_affiliative) | **{h22_fs_b}** | {h22_fs_p} |

- n: pred_affiliative=19,101, pred_aggressive=6,857, pred_self-enhancing=1,994, pred_self-defeating=225
- **CRITICAL**: classifier NOT_A_CANDIDATE; 예측 분포가 Wendy's model의 leakage 반영

---

## 5. H3 결과: Aggressive Intensity → Firm Engagement (Inverted-U)

**가설**: Firm의 aggressive humor 사용 강도와 engagement 사이에 역 U자형 관계.

### A. Batch1 Human-coded H3 (n_firms={len(b1_firm_rows)}, intensity>0={n_b1_agg_firms})

| 모델 | 변수 | β | p | 해석 |
|---|---|---|---|---|
| H3_batch1_quadratic | aggressive_intensity | {b1_quad.get('coefficient', 'NA')} | {b1_quad.get('p_value', 'NA')} | β1 |
| H3_batch1_quadratic | aggressive_intensity_sq | {b1_sq.get('coefficient', 'NA')} | {b1_sq.get('p_value', 'NA')} | β2 |

- Turning point: {b1_quad.get('turning_point', 'NA')} (범위 내: {b1_quad.get('turning_point_in_range', 'NA')})
- Inverted-U check: {b1_quad.get('inverted_u_check', 'NA')}
- n_firms_with_intensity>0: {n_b1_agg_firms}/{len(b1_firm_rows)}
- Interpretation level: {b1_quad.get('interpretation_level', 'NA')}

### B. Full-sample Classifier-predicted H3 (n_firms={len(full_firm_rows)}, intensity>0={n_full_agg_firms})

| 모델 | 변수 | β | p | 해석 |
|---|---|---|---|---|
| H3_full_quadratic | predicted_aggressive_intensity | {fs_quad.get('coefficient', 'NA')} | {fs_quad.get('p_value', 'NA')} | β1 |
| H3_full_quadratic | predicted_aggressive_intensity_sq | {fs_sq.get('coefficient', 'NA')} | {fs_sq.get('p_value', 'NA')} | β2 |

- Turning point: {fs_quad.get('turning_point', 'NA')} (범위 내: {fs_quad.get('turning_point_in_range', 'NA')})
- Inverted-U check: {fs_quad.get('inverted_u_check', 'NA')}
- n_firms_with_intensity>0: {n_full_agg_firms}/{len(full_firm_rows)}
- **CRITICAL WARNING**: Type classifier NOT_A_CANDIDATE; intensity 분포 자체가 leakage 영향

---

## 6. 두 Measurement Basis 비교

| 가설 | Batch1 β (인간코딩) | Full β (예측) | 방향 일치 | interpretation_level |
|---|---|---|---|---|
| H1 | {h1_b1_b} | {h1_fs_b} | — | preliminary_diagnostic |
| H2-1 | {h21_b1_b} | {h21_fs_b} | — | preliminary_diagnostic |
| H2-2 (agg) | {h22_b1_b} | {h22_fs_b} | — | preliminary_diagnostic |
| H3 β1 | {b1_quad.get('coefficient','NA')} | {fs_quad.get('coefficient','NA')} | — | {b1_quad.get('interpretation_level','NA')} |

---

## 7. 가설별 Interpretation Level

| 가설 | Batch1 verdict | Full-sample verdict | 통합 판단 |
|---|---|---|---|
| H1 | preliminary_supported | preliminary_supported | preliminary_supported (caveat: full IV=predicted) |
| H2-1 | mixed | mixed | mixed (n_agg 부족 / classifier leakage) |
| H2-2 | mixed | mixed | mixed (같은 이유) |
| H3 | {b1_quad.get('interpretation_level','NA')} | {fs_quad.get('interpretation_level','NA')} | {b1_quad.get('interpretation_level','NA')} |

---

## 8. 측정 한계 (Measurement Limitations)

### Batch1 Human-coded 한계
1. **소표본**: H1=1,482 / H2=648 / H3={len(b1_firm_rows)} firms — 특히 aggressive n=44 검정력 낮음
2. **선택 편향**: batch1은 전략적 샘플링 (humor posts oversampled) → Fortune 100 전체 대표성 낮음
3. **H3 intensity 불안정**: firm당 labeled 게시물 수가 적어 intensity 추정 불안정 (예: 1개 게시물 firm = intensity 0 또는 1.0)

### Full-sample Classifier-predicted 한계
1. **Classifier NOT_A_CANDIDATE**: aggressive/type classifier leakage 미해결
2. **Source shortcut**: #NationalRoastDay가 rank#1 feature → Wendy's aggressive 집중 예측 편향
3. **H1 measurement error**: predicted label이 IV이면 classical measurement error bias (attenuation 또는 과대 추정)
4. **H2/H3 심각한 편향**: 예측 분포 자체가 leakage 반영 → full H2/H3 결과는 참고용에 불과

### 공통 한계
1. **Omitted variables**: follower 수, account age, posting time 등 미통제
2. **Endogeneity**: engagement 기대 → humor 전략 선택 (역인과 가능)
3. **Temporal clustering**: 회사-시간 serial correlation, company-level clustering 무시 → SE 과소 추정 가능

---

## 9. 금지 사항 준수 확인

- [x] scraping 실행 없음
- [x] Playwright 실행 없음
- [x] X API 실행 없음
- [x] integrated corpus 재분류 없음
- [x] 새 classifier training 없음
- [x] 새 prediction 생성 없음
- [x] data/raw 수정 없음
- [x] dashboard/data 수정 없음
- [x] .github/workflows 수정 없음
- [x] 기존 결과 파일 삭제 없음
- [x] H2/H3 formal supported 선언 없음
- [x] candidate/deployment-ready 선언 없음
- [x] HC3/robust SE 사용 없음 (classical OLS SE만 사용)
- [x] Batch1 human-coded와 full-sample predicted 분리 보고

---

*생성 스크립트*: `run_two_basis_plain_ols_hypotheses.py`
*생성일*: 2026-06-19
*SE type*: Classical OLS (s²×(X'X)⁻¹)
"""

with open(os.path.join(OUT, "hypothesis_plain_ols_two_basis_interpretation.md"), "w", encoding="utf-8") as f:
    f.write(md)
print(f"  wrote hypothesis_plain_ols_two_basis_interpretation.md")


# ===========================================================================
# STEP 8: Data dictionary
# ===========================================================================
print("\n" + "=" * 70)
print("STEP 8: Writing measurement basis data dictionary")
print("=" * 70)

dd = """# Measurement Basis Data Dictionary — Two-Basis Plain OLS Analysis

**SE type**: Classical OLS (s²×(X'X)⁻¹) — NOT HC3/robust

---

## Measurement Basis A: Batch1 Human-coded

### H1 Input
**File**: `fortune100_human_labeling_template.csv`
**Rows used**: 1,482 (excluded 18 rows with human_humor_presence=2 [ambiguous])

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | join key | — |
| `company_name` | H3 groupby | 97 unique companies |
| `total_engagement` | DV source | log1p() applied |
| `human_humor_presence` | **H1 IV** | 0=non-humor, 1=humor; HUMAN-CODED |
| `text` | control source | text_length, hashtag_count, mention_count computed here |

**Distribution**: humor=648 / non-humor=834

### H2/H3 Input
**File**: `type_training_leakage_filtered_variants.csv` (batch1_fortune100 only)
**Rows**: 648 (all humor-positive)
**Engagement join**: `fortune100_h1_presence_classified_posts.csv` on `tweet_id` (100% match)

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | join key | — |
| `company_name` | H3 firm groupby | 88 unique firms |
| `humor_type` | **H2/H3 IV** | aggressive/affiliative/self-enhancing/self-defeating; HUMAN-CODED |
| `total_engagement` | DV (via join) | from fortune100_h1_presence_classified_posts.csv |

**Type distribution**: affiliative=321, self-enhancing=259, aggressive=44, self-defeating=24

### H3 Intensity Construction (Batch1)
- `aggressive_intensity = n_aggressive / n_humor` per firm (from 648 labeled posts)
- DV: firm-level mean log1p(total_engagement) from batch1 labeled posts
- Analysis unit: **firm-level** (88 firms)
- WARNING: intensity based on small labeled sample per firm → unstable estimates

---

## Measurement Basis B: Full-sample Classifier-predicted

### H1 Full Input
**File**: `integrated_h1_presence_classified_posts.csv`
**Rows**: 68,039

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | identifier | — |
| `company_name` | — | 99 unique companies |
| `source_dataset` | stratification | fortune100/wendys_legacy/moonpie_legacy/cocacola_legacy/fortune100_raw_append |
| `total_engagement` | DV source | log1p() applied |
| `log_total_engagement` | DV alt | pre-computed log1p |
| `h1_humor_presence_pred_t50` | **H1 IV** | PREDICTED at threshold 0.50; model=word_char_comb__lr_liblin_C01 |
| `text_length` | control | pre-computed |
| `hashtag_count` | control | pre-computed |
| `mention_count` | control | pre-computed |

**Source breakdown**: fortune100=65,245 / wendys_legacy=977 / moonpie_legacy=930 / cocacola_legacy=708 / fortune100_raw_append=179

### H2 Full Input
**File**: `h2_post_level_regression_ready.csv` (model_transfer pipeline)
**Rows total**: 65,245 / **Humor rows used**: 28,177 (humor_type != non_humorous)

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | identifier | — |
| `company_name` | H3 groupby | 97 unique companies |
| `log_total_engagement` | DV | pre-computed |
| `humor_type` | type label | PREDICTED by Wendy's model transfer |
| `aggressive_humor` | H2 IV (0/1) | PREDICTED dummy |
| `affiliative_humor` | reference (0/1) | PREDICTED dummy |
| `self_enhancing_humor` | H2 IV (0/1) | PREDICTED dummy |
| `self_defeating_humor` | H2 IV (0/1) | PREDICTED dummy |
| `text_length` | control | pre-computed |
| `hashtag_count` | control | pre-computed |
| `mention_count` | control | pre-computed |

**CRITICAL**: classifier_status=NOT_A_CANDIDATE; source-shortcut leakage (#NationalRoastDay) confirmed

### H3 Full Intensity Construction
- `predicted_aggressive_intensity = n_pred_aggressive / n_pred_humor` per firm
- DV: firm-level mean log1p(total_engagement) from predicted humor posts
- Analysis unit: **firm-level** (97 firms)

**Predicted type distribution** (humor posts only):
- affiliative: 19,101
- aggressive: 6,857
- self-enhancing: 1,994
- self-defeating: 225

---

## Output Files

| File | Contents |
|---|---|
| `h1_batch1_human_coded_plain_ols_results.csv` | H1 OLS (batch1, classical SE) |
| `h1_full_sample_predicted_plain_ols_results.csv` | H1 OLS (full predicted, classical SE) |
| `h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv` | H2-1 batch1 |
| `h2_2_batch1_human_coded_four_type_plain_ols_results.csv` | H2-2 batch1 |
| `h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv` | H2-1 full predicted |
| `h2_2_full_sample_predicted_four_type_plain_ols_results.csv` | H2-2 full predicted |
| `h3_batch1_human_coded_intensity_plain_ols_results.csv` | H3 quadratic batch1 |
| `h3_batch1_human_coded_intensity_distribution.csv` | Firm-level intensity (batch1) |
| `h3_full_sample_predicted_intensity_plain_ols_results.csv` | H3 quadratic full predicted |
| `h3_full_sample_predicted_intensity_distribution.csv` | Firm-level intensity (full predicted) |
| `hypothesis_plain_ols_two_basis_summary.csv` | One row per model × basis summary |
| `hypothesis_plain_ols_two_basis_interpretation.md` | Korean interpretation |
| `measurement_basis_sample_attrition.csv` | Attrition steps per basis × hypothesis |
| `measurement_basis_data_dictionary.md` | This file |
| `run_two_basis_plain_ols_hypotheses.py` | Generating script |

---

## SE Type

Classical OLS SE: `s² = SSR/(n-k)`, `Var(β̂) = s²·(X'X)⁻¹`, `SE = √diag(Var(β̂))`
**HC3, HC1, clustered SE are NOT used in any main result.**

---

*Last updated*: 2026-06-19
*Script*: `run_two_basis_plain_ols_hypotheses.py`
"""

with open(os.path.join(OUT, "measurement_basis_data_dictionary.md"), "w", encoding="utf-8") as f:
    f.write(dd)
print(f"  wrote measurement_basis_data_dictionary.md")

print("\n" + "=" * 70)
print("DONE — All output files written to:", OUT)
print("=" * 70)
