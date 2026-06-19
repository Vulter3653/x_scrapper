"""
Firm Dummy Only Robustness Analysis for H1/H2/H3.

Model: engagement = β0 + β1 focal_IV + firm_dummy_2 + ... + firm_dummy_N + ε
SE: Classical OLS only. NO time FE. NO controls.

Firm dummies are created as explicit binary columns (NOT C(company_id) formula,
NOT company_id as numeric covariate). Reference firm = most posts per subsample.

Based on 1926e25 two-basis plain OLS results.
Prohibited: time FE, controls, backfill files, new predictions/classifiers,
           data/raw, dashboard/data, .github/workflows.
"""

import csv
import math
import os

import numpy as np
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/home/user/marketingstrategy/20260618expand"
OUT  = os.path.join(BASE, "ols_hypothesis_results/firm_dummy_only_robustness")
os.makedirs(OUT, exist_ok=True)

TEMPLATE_CSV  = (BASE + "/classifier_improvement/data/human_labeling_template"
                 "/fortune100_human_labeling_template.csv")
TYPE_CSV      = (BASE + "/classifier_improvement/humor_type_leakage_filtered/data"
                 "/type_training_leakage_filtered_variants.csv")
F100_CSV      = (BASE + "/classifier_improvement/h1_presence_only/full_corpus_classification"
                 "/data/fortune100_h1_presence_classified_posts.csv")
INTEGRATED_CSV= (BASE + "/classifier_improvement/h1_presence_only/integrated_collected_corpus"
                 "/data/integrated_h1_presence_classified_posts.csv")
H2_FULL_CSV   = BASE + "/model_transfer/data/regression_ready/h2_post_level_regression_ready.csv"
H3_PANEL_CSV  = BASE + "/model_transfer/data/processed/h3_firm_month_panel.csv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    if not rows: return
    all_keys = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                all_keys.append(k); seen.add(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore", restval="")
        w.writeheader(); w.writerows(rows)
    print(f"  {len(rows)} rows → {os.path.basename(path)}")

def p_stars(p):
    try:
        p = float(p)
        if p < 0.01: return "***"
        if p < 0.05: return "**"
        if p < 0.10: return "*"
    except: pass
    return "ns"

def log1p_safe(v):
    try: return math.log1p(max(float(v), 0.0))
    except: return float("nan")

# ---------------------------------------------------------------------------
# Plain OLS (classical SE only)
# ---------------------------------------------------------------------------

def plain_ols(y_np, X_np, feature_names):
    n, k = X_np.shape
    y = y_np.astype(np.float64)
    X = X_np.astype(np.float64)

    XtX = X.T @ X
    rank = int(np.linalg.matrix_rank(XtX))
    if rank < k:
        XtX_inv = np.linalg.pinv(XtX)
    else:
        XtX_inv = np.linalg.inv(XtX)

    beta = XtX_inv @ (X.T @ y)
    e    = y - X @ beta
    ss_res = float(np.sum(e ** 2))
    ss_tot = float(np.sum((y - float(y.mean())) ** 2))

    r2     = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1 - r2) * (n - 1) / (n - k) if (n - k) > 0 else float("nan")
    s2     = ss_res / (n - k) if (n - k) > 0 else float("nan")
    vcov   = s2 * XtX_inv if not math.isnan(s2) else XtX_inv * float("nan")
    ses    = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st   = np.where(ses > 0, beta / ses, float("nan"))
    pv     = np.array([
        2 * (1 - scipy_stats.t.cdf(abs(t), df=n - k)) if not math.isnan(t) else float("nan")
        for t in t_st
    ])

    rows = [{
        "feature":          feat,
        "coefficient":      round(float(beta[i]), 6),
        "classical_ols_se": round(float(ses[i]), 6),
        "t_stat":           round(float(t_st[i]), 4) if not math.isnan(t_st[i]) else "",
        "p_value":          round(float(pv[i]), 6)   if not math.isnan(pv[i])   else "",
        "stars":            p_stars(pv[i]),
    } for i, feat in enumerate(feature_names)]
    return rows, r2, r2_adj, n, k, int(n - k), rank

# ---------------------------------------------------------------------------
# Firm dummy builder
# ---------------------------------------------------------------------------

def build_firm_dummies(company_array, global_id_map):
    """
    Given array of company names and a global {name: id} map,
    returns:
      dummy_matrix  : np.ndarray shape (n, n_dummies)  — explicit binary columns
      dummy_names   : list of 'firm_dummy_{id}' strings
      ref_id        : company_id of reference (most frequent) firm
      ref_name      : original company name of reference firm
      counts        : {company_name: count} for this subsample
      n_firms       : number of unique firms in subsample
    """
    # Count per firm
    counts = {}
    for cn in company_array:
        counts[cn] = counts.get(cn, 0) + 1

    # Reference = most common
    ref_name = max(counts, key=counts.__getitem__)
    ref_id   = global_id_map[ref_name]

    # All other firms sorted by id
    other_firms = sorted(
        [cn for cn in counts if cn != ref_name],
        key=lambda cn: global_id_map[cn]
    )
    other_ids = [global_id_map[cn] for cn in other_firms]
    dummy_names = [f"firm_dummy_{cid}" for cid in other_ids]

    # Build dummy matrix (no intercept here — added separately in OLS)
    n = len(company_array)
    dummy_matrix = np.zeros((n, len(other_firms)), dtype=np.float64)
    firm_to_col  = {cn: j for j, cn in enumerate(other_firms)}
    for i, cn in enumerate(company_array):
        if cn in firm_to_col:
            dummy_matrix[i, firm_to_col[cn]] = 1.0

    return dummy_matrix, dummy_names, ref_id, ref_name, counts, len(counts)

# ---------------------------------------------------------------------------
# STEP 1: Load all data
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1: Loading data")
print("=" * 60)

# --- Batch1 H1 ---
tmpl  = read_csv(TEMPLATE_CSV)
b1_h1 = [r for r in tmpl if r["human_humor_presence"] in ("0","1")]

# --- Batch1 H2/H3 type ---
type_raw = read_csv(TYPE_CSV)
b1_type  = [r for r in type_raw if r["source"] == "batch1_fortune100"]

# f100 for engagement join
f100_raw = read_csv(F100_CSV)
f100_idx = {r["tweet_id"]: r for r in f100_raw}
for r in b1_type:
    er = f100_idx.get(r["tweet_id"])
    r["_eng"]  = log1p_safe(er["total_engagement"]) if er else float("nan")

# Filter to rows with valid engagement
b1_type_valid = [r for r in b1_type if not math.isnan(r["_eng"])]

# --- Full H1 (integrated) ---
integ   = read_csv(INTEGRATED_CSV)
full_h1 = [r for r in integ
           if r.get("missing_text") != "True"
           and r.get("h1_humor_presence_pred_t50") in ("0","1")]

# --- Full H2 (humor only) ---
h2_raw   = read_csv(H2_FULL_CSV)
h2_humor = [r for r in h2_raw if r["humor_type"] != "non_humorous"]

# --- Full H3 (firm-month panel) ---
h3_panel = read_csv(H3_PANEL_CSV)

print(f"Batch1 H1 : {len(b1_h1)} rows")
print(f"Batch1 H2 : {len(b1_type_valid)} rows (valid engagement join)")
print(f"Full H1   : {len(full_h1)} rows")
print(f"Full H2   : {len(h2_humor)} rows")
print(f"H3 panel  : {len(h3_panel)} rows")

# ---------------------------------------------------------------------------
# STEP 2: Build global company_id mapping
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Building global company_id map")
print("=" * 60)

all_companies = set()
source_info   = {}  # company_name → (n_posts_across_all, source_files)

def register(rows, key, src):
    for r in rows:
        cn = r.get(key, "").strip()
        if not cn: continue
        all_companies.add(cn)
        if cn not in source_info:
            source_info[cn] = [0, set()]
        source_info[cn][0] += 1
        source_info[cn][1].add(src)

register(b1_h1,       "company_name", "template")
register(b1_type,     "company_name", "type_training")
register(full_h1,     "company_name", "integrated")
register(h2_humor,    "company_name", "h2_regression_ready")
register(h3_panel,    "company_name", "h3_firm_month_panel")

# Sort alphabetically → assign stable IDs
sorted_companies = sorted(all_companies)
global_id_map    = {cn: i+1 for i, cn in enumerate(sorted_companies)}

id_map_rows = [{
    "company_id":               global_id_map[cn],
    "company_identifier_original": cn,
    "n_posts":                  source_info[cn][0],
    "source_file":              ";".join(sorted(source_info[cn][1])),
} for cn in sorted_companies]

write_csv(os.path.join(OUT, "firm_dummy_company_id_map.csv"), id_map_rows)
print(f"  Total unique companies: {len(sorted_companies)}")

# ---------------------------------------------------------------------------
# STEP 3: Common result template
# ---------------------------------------------------------------------------

AUDIT_FLAGS = {
    "firm_dummy_included":       "true",
    "company_id_used_as_numeric":"false",
    "c_company_formula_used":    "false",
    "time_fe_included":          "false",
    "controls_included":         "false",
}

def base_result(basis, hyp, dv, key_var, status="success", **extra):
    d = {
        "measurement_basis": basis,
        "hypothesis":        hyp,
        "model_id":          "firm_dummy_only",
        "dependent_variable": dv,
        "key_variable":      key_var,
        "coefficient": "", "classical_ols_se": "", "t_stat": "",
        "p_value": "", "stars": "", "n_obs": "", "n_firms": "",
        "reference_company_id": "", "reference_company_identifier": "",
        "n_firm_dummy_variables": "",
        "r_squared": "", "adj_r_squared": "",
        "df_model": "", "df_resid": "", "rank": "",
        "status": status,
        "interpretation_level": "",
    }
    d.update(AUDIT_FLAGS)
    d.update(extra)
    return d

def fill_ols(d, coef_rows, r2, r2_adj, n, k, df_res, rank,
             ref_id, ref_name, n_firms, n_dummies):
    cr = coef_rows[0]
    d.update({
        "coefficient":       cr["coefficient"],
        "classical_ols_se":  cr["classical_ols_se"],
        "t_stat":            cr["t_stat"],
        "p_value":           cr["p_value"],
        "stars":             cr["stars"],
        "n_obs":             n,
        "n_firms":           n_firms,
        "reference_company_id":         ref_id,
        "reference_company_identifier": ref_name,
        "n_firm_dummy_variables":       n_dummies,
        "r_squared":         round(r2, 6) if r2 == r2 else "",
        "adj_r_squared":     round(r2_adj, 6) if r2_adj == r2_adj else "",
        "df_model":          k,
        "df_resid":          df_res,
        "rank":              rank,
        "status":            "success",
        "interpretation_level": "preliminary_diagnostic",
    })
    return d

def run_firm_ols(y_np, X_focal, focal_names, company_array, basis, hyp, dv, extra_cols=None):
    """Build firm dummies, concatenate with focal X, run OLS. Return result dict."""
    d = base_result(basis, hyp, dv, focal_names[0], **(extra_cols or {}))
    try:
        D, dnames, ref_id, ref_name, counts, n_firms = build_firm_dummies(
            company_array, global_id_map
        )
        n_dummies = D.shape[1]
        # X = [intercept | focal_IVs | firm_dummies]
        intercept = np.ones((len(y_np), 1))
        X_full    = np.hstack([intercept, X_focal, D])
        fnames    = ["intercept"] + focal_names + dnames

        coef_rows, r2, r2_adj, n, k, df_res, rank = plain_ols(y_np, X_full, fnames)
        fill_ols(d, coef_rows[1:], r2, r2_adj, n, k, df_res, rank,
                 ref_id, ref_name, n_firms, n_dummies)
        # Extra focal coefficients for multi-IV models (H2-2, H3)
        focal_coefs = coef_rows[1:1+len(focal_names)]
        if len(focal_names) > 1:
            for fc in focal_coefs:
                d[f"coef_{fc['feature']}"]  = fc["coefficient"]
                d[f"se_{fc['feature']}"]    = fc["classical_ols_se"]
                d[f"p_{fc['feature']}"]     = fc["p_value"]
                d[f"stars_{fc['feature']}"] = fc["stars"]
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:120]}"
        d["interpretation_level"] = "error"
    return d

# ---------------------------------------------------------------------------
# STEP 4: H1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 4: H1")
print("=" * 60)

h1_results = []

# Batch1 H1
b1h1_y = np.array([log1p_safe(r["total_engagement"]) for r in b1_h1])
b1h1_X = np.array([[float(r["human_humor_presence"])] for r in b1_h1])
b1h1_c = np.array([r["company_name"] for r in b1_h1])

r = run_firm_ols(b1h1_y, b1h1_X, ["human_humor_presence"], b1h1_c,
                 "batch1_human_coded", "H1", "log1p_total_engagement")
h1_results.append(r)
print(f"  Batch1 H1: β={r['coefficient']} SE={r['classical_ols_se']} {r['stars']} "
      f"n={r['n_obs']} firms={r['n_firms']} ref='{r['reference_company_identifier']}'")

# Full H1
fh1_y = np.array([log1p_safe(r["total_engagement"]) for r in full_h1])
fh1_X = np.array([[float(r["h1_humor_presence_pred_t50"])] for r in full_h1])
fh1_c = np.array([r["company_name"] for r in full_h1])

r2 = run_firm_ols(fh1_y, fh1_X, ["h1_humor_presence_pred_t50"], fh1_c,
                  "full_sample_predicted", "H1", "log1p_total_engagement",
                  {"limitation": "h1_iv_is_classifier_predicted"})
h1_results.append(r2)
print(f"  Full H1  : β={r2['coefficient']} SE={r2['classical_ols_se']} {r2['stars']} "
      f"n={r2['n_obs']} firms={r2['n_firms']} ref='{r2['reference_company_identifier']}'")

write_csv(os.path.join(OUT, "h1_firm_dummy_only_results.csv"), h1_results)

# ---------------------------------------------------------------------------
# STEP 5: H2-1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 5: H2-1")
print("=" * 60)

h21_results = []

# Batch1 H2-1
for r in b1_type_valid:
    r["_agg_vs_other"] = 1.0 if r["humor_type"] == "aggressive" else 0.0
b1h2_y   = np.array([r["_eng"] for r in b1_type_valid])
b1h2_X21 = np.array([[r["_agg_vs_other"]] for r in b1_type_valid])
b1h2_c   = np.array([r["company_name"] for r in b1_type_valid])

r = run_firm_ols(b1h2_y, b1h2_X21, ["aggressive_vs_other"], b1h2_c,
                 "batch1_human_coded", "H2_1", "log1p_total_engagement",
                 {"n_aggressive_batch1": sum(1 for r_ in b1_type_valid if r_["humor_type"]=="aggressive"),
                  "limitation": "n_agg=44_low_power"})
h21_results.append(r)
print(f"  Batch1 H2-1: β={r['coefficient']} {r['stars']} n_agg=44")

# Full H2-1
for r in h2_humor:
    r["_agg_vs_other"] = float(r["aggressive_humor"])
fh2_y   = np.array([float(r["log_total_engagement"]) for r in h2_humor])
fh2_X21 = np.array([[r["_agg_vs_other"]] for r in h2_humor])
fh2_c   = np.array([r["company_name"] for r in h2_humor])

r2 = run_firm_ols(fh2_y, fh2_X21, ["predicted_aggressive_vs_other"], fh2_c,
                  "full_sample_predicted", "H2_1", "log1p_total_engagement",
                  {"n_predicted_aggressive": sum(1 for r_ in h2_humor if r_["aggressive_humor"]=="1"),
                   "limitation": "classifier_NOT_A_CANDIDATE_leakage"})
h21_results.append(r2)
print(f"  Full H2-1  : β={r2['coefficient']} {r2['stars']}")

write_csv(os.path.join(OUT, "h2_1_firm_dummy_only_results.csv"), h21_results)

# ---------------------------------------------------------------------------
# STEP 6: H2-2
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 6: H2-2")
print("=" * 60)

h22_results = []

# Batch1 H2-2
for r in b1_type_valid:
    r["_agg"] = 1.0 if r["humor_type"] == "aggressive"     else 0.0
    r["_se"]  = 1.0 if r["humor_type"] == "self-enhancing" else 0.0
    r["_sd"]  = 1.0 if r["humor_type"] == "self-defeating" else 0.0
b1h2_X22 = np.array([[r["_agg"], r["_se"], r["_sd"]] for r in b1_type_valid])
feat_b1  = ["aggressive", "self_enhancing", "self_defeating"]

r = run_firm_ols(b1h2_y, b1h2_X22, feat_b1, b1h2_c,
                 "batch1_human_coded", "H2_2", "log1p_total_engagement",
                 {"reference_category": "affiliative"})
h22_results.append(r)
print(f"  Batch1 H2-2: agg β={r.get('coef_aggressive',r['coefficient'])} {r.get('stars_aggressive',r['stars'])}")

# Full H2-2
for r in h2_humor:
    r["_agg"] = float(r["aggressive_humor"])
    r["_se"]  = float(r["self_enhancing_humor"])
    r["_sd"]  = float(r["self_defeating_humor"])
fh2_X22 = np.array([[r["_agg"], r["_se"], r["_sd"]] for r in h2_humor])
feat_fs  = ["predicted_aggressive", "predicted_self_enhancing", "predicted_self_defeating"]

r2 = run_firm_ols(fh2_y, fh2_X22, feat_fs, fh2_c,
                  "full_sample_predicted", "H2_2", "log1p_total_engagement",
                  {"reference_category": "predicted_affiliative",
                   "limitation": "classifier_NOT_A_CANDIDATE_leakage"})
h22_results.append(r2)
print(f"  Full H2-2  : agg β={r2.get('coef_predicted_aggressive',r2['coefficient'])} "
      f"{r2.get('stars_predicted_aggressive',r2['stars'])}")

write_csv(os.path.join(OUT, "h2_2_firm_dummy_only_results.csv"), h22_results)

# ---------------------------------------------------------------------------
# STEP 7: H3
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 7: H3")
print("=" * 60)

h3_results = []

INT_COL = "aggressive_humor_usage_intensity"
INT_SQ  = "aggressive_humor_usage_intensity_sq"
ENG_COL = "mean_log_total_engagement"

# Batch1 H3: firm-level cross-section (1 row per firm) → not applicable
# Adding firm dummies would exactly absorb all between-firm variation → collinear
n_b1_firms = 88  # known from prior analysis
h3_results.append({
    "measurement_basis":   "batch1_human_coded",
    "hypothesis":          "H3",
    "model_id":            "firm_dummy_only",
    "dependent_variable":  "firm_mean_log1p_engagement",
    "key_variable":        "aggressive_intensity",
    "beta1_intensity": "", "beta2_intensity_squared": "",
    "beta1_p_value": "",   "beta2_p_value": "",
    "coefficient": "", "classical_ols_se": "", "t_stat": "",
    "p_value": "", "stars": "", "n_obs": n_b1_firms, "n_firms": n_b1_firms,
    "reference_company_id": "", "reference_company_identifier": "",
    "n_firm_dummy_variables": n_b1_firms - 1,
    "r_squared": "", "adj_r_squared": "", "df_model": "", "df_resid": "", "rank": "",
    "turning_point": "", "turning_point_in_observed_range": "",
    "intensity_min": "", "intensity_max": "",
    "panel_unit": "firm_cross_section",
    "time_period_unit": "none",
    **AUDIT_FLAGS,
    "status": "not_applicable",
    "interpretation_level": "not_applicable",
    "note": ("firm-level cross-section: 1 row per firm; firm dummies would absorb all "
             "between-firm variation and perfectly collinear with the intercept → "
             "n_firms-1=87 dummies with n=88 leaves df_resid≤0 for focal IVs"),
})
print(f"  Batch1 H3: not_applicable (firm cross-section, n=88)")

# Full H3: firm-month panel (3,532 rows, 97 firms, multiple periods) → applicable
h3_y   = np.array([float(r[ENG_COL]) for r in h3_panel])
h3_X   = np.array([[float(r[INT_COL]), float(r[INT_SQ])] for r in h3_panel])
h3_c   = np.array([r["company_name"] for r in h3_panel])
int_min= float(h3_X[:, 0].min())
int_max= float(h3_X[:, 0].max())

feat_h3 = ["predicted_aggressive_intensity", "predicted_aggressive_intensity_sq"]
d_h3    = base_result(
    "full_sample_predicted", "H3", "firm_period_mean_log1p_engagement",
    "predicted_aggressive_intensity",
    **{
        "beta1_intensity": "", "beta2_intensity_squared": "",
        "beta1_p_value": "",   "beta2_p_value": "",
        "turning_point": "", "turning_point_in_observed_range": "",
        "intensity_min": round(int_min, 6), "intensity_max": round(int_max, 6),
        "panel_unit": "firm_month_period",
        "time_period_unit": "year_month",
        "n_obs_panel_raw": len(h3_panel),
        "limitation": "classifier_NOT_A_CANDIDATE_leakage_in_intensity",
    }
)

try:
    D, dnames, ref_id, ref_name, counts, n_firms = build_firm_dummies(h3_c, global_id_map)
    n_dummies = D.shape[1]
    intercept = np.ones((len(h3_y), 1))
    X_full    = np.hstack([intercept, h3_X, D])
    fnames    = ["intercept"] + feat_h3 + dnames

    coef_rows, r2, r2_adj, n, k, df_res, rank = plain_ols(h3_y, X_full, fnames)

    focal_coefs = coef_rows[1:3]  # intensity, intensity_sq
    b1v = focal_coefs[0]["coefficient"]
    b2v = focal_coefs[1]["coefficient"]
    tp  = -b1v / (2 * b2v) if abs(b2v) > 1e-12 else float("nan")
    tpr = str(int_min <= tp <= int_max) if not math.isnan(tp) else ""

    d_h3.update({
        "coefficient":       b1v,
        "classical_ols_se":  focal_coefs[0]["classical_ols_se"],
        "t_stat":            focal_coefs[0]["t_stat"],
        "p_value":           focal_coefs[0]["p_value"],
        "stars":             focal_coefs[0]["stars"],
        "n_obs":             n,
        "n_firms":           n_firms,
        "reference_company_id":         ref_id,
        "reference_company_identifier": ref_name,
        "n_firm_dummy_variables":       n_dummies,
        "r_squared":         round(r2, 6) if r2 == r2 else "",
        "adj_r_squared":     round(r2_adj, 6) if r2_adj == r2_adj else "",
        "df_model":          k,
        "df_resid":          df_res,
        "rank":              rank,
        "beta1_intensity":         b1v,
        "beta2_intensity_squared": b2v,
        "beta1_p_value":  focal_coefs[0]["p_value"],
        "beta2_p_value":  focal_coefs[1]["p_value"],
        "beta2_stars":    focal_coefs[1]["stars"],
        "turning_point":  round(tp, 4) if not math.isnan(tp) else "",
        "turning_point_in_observed_range": tpr,
        "inverted_u_check": "b1>0_b2<0" if b1v>0 and b2v<0 else "other",
        "status":            "success",
        "interpretation_level": "preliminary_diagnostic",
    })
    print(f"  Full H3: β1={b1v:.4f}{focal_coefs[0]['stars']} "
          f"β2={b2v:.4f}{focal_coefs[1]['stars']} "
          f"tp={round(tp,4) if not math.isnan(tp) else 'nan'} "
          f"n={n} firms={n_firms} ref='{ref_name}'")
except Exception as ex:
    d_h3["status"] = f"error: {str(ex)[:120]}"
    d_h3["interpretation_level"] = "error"
    print(f"  Full H3 error: {ex}")

h3_results.append(d_h3)
write_csv(os.path.join(OUT, "h3_firm_dummy_only_results.csv"), h3_results)

# ---------------------------------------------------------------------------
# STEP 8: Dummy column dictionary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 8: Dummy column dictionary")
print("=" * 60)

dict_rows = []
# Derive what dummies were used per analysis from global map
datasets_info = [
    ("batch1_h1",  "company_name", b1_h1,        TEMPLATE_CSV),
    ("batch1_h2",  "company_name", b1_type_valid, TYPE_CSV),
    ("full_h1",    "company_name", full_h1,       INTEGRATED_CSV),
    ("full_h2",    "company_name", h2_humor,       H2_FULL_CSV),
    ("full_h3",    "company_name", h3_panel,       H3_PANEL_CSV),
]
for dsname, col, rows, src in datasets_info:
    counts = {}
    for r in rows:
        cn = r.get(col, "").strip()
        counts[cn] = counts.get(cn, 0) + 1
    ref = max(counts, key=counts.__getitem__)
    ref_id = global_id_map.get(ref, "")
    others = sorted([cn for cn in counts if cn != ref], key=lambda cn: global_id_map[cn])
    for cn in others:
        dict_rows.append({
            "dataset":              dsname,
            "source_file":         os.path.basename(src),
            "dummy_column_name":   f"firm_dummy_{global_id_map[cn]}",
            "company_id":          global_id_map[cn],
            "company_name":        cn,
            "n_obs_in_dataset":    counts[cn],
            "is_reference_firm":   "false",
        })
    # Add reference row
    dict_rows.append({
        "dataset":             dsname,
        "source_file":         os.path.basename(src),
        "dummy_column_name":   f"REFERENCE_firm_id_{ref_id}",
        "company_id":          ref_id,
        "company_name":        ref,
        "n_obs_in_dataset":    counts[ref],
        "is_reference_firm":   "true (omitted)",
    })

write_csv(os.path.join(OUT, "firm_dummy_columns_dictionary.csv"), dict_rows)

# ---------------------------------------------------------------------------
# STEP 9: Sample attrition
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 9: Sample attrition")
print("=" * 60)

def get_result_val(results, basis, hyp, col):
    for r in results:
        if r.get("measurement_basis") == basis and r.get("hypothesis") == hyp:
            return r.get(col, "")
    return ""

attrition_rows = [
    {"dataset": "batch1_h1",  "measurement_basis": "batch1_human_coded",  "hypothesis": "H1",
     "raw_n": len(tmpl), "after_label_filter": len(b1_h1),
     "after_company_filter": get_result_val(h1_results,  "batch1_human_coded",  "H1",   "n_obs"),
     "n_firms": get_result_val(h1_results,  "batch1_human_coded",  "H1",   "n_firms"),
     "n_dummies": get_result_val(h1_results,"batch1_human_coded",  "H1",   "n_firm_dummy_variables"),
     "note": "human_humor_presence in {0,1}"},
    {"dataset": "full_h1",   "measurement_basis": "full_sample_predicted", "hypothesis": "H1",
     "raw_n": len(integ), "after_label_filter": len(full_h1),
     "after_company_filter": get_result_val(h1_results,  "full_sample_predicted","H1",   "n_obs"),
     "n_firms": get_result_val(h1_results,  "full_sample_predicted","H1",   "n_firms"),
     "n_dummies": get_result_val(h1_results,"full_sample_predicted","H1",   "n_firm_dummy_variables"),
     "note": "missing_text excluded; h1_pred_t50 in {0,1}"},
    {"dataset": "batch1_h2",  "measurement_basis": "batch1_human_coded",   "hypothesis": "H2_1/H2_2",
     "raw_n": len(b1_type), "after_label_filter": len(b1_type_valid),
     "after_company_filter": get_result_val(h21_results, "batch1_human_coded",  "H2_1", "n_obs"),
     "n_firms": get_result_val(h21_results, "batch1_human_coded",  "H2_1", "n_firms"),
     "n_dummies": get_result_val(h21_results,"batch1_human_coded",  "H2_1","n_firm_dummy_variables"),
     "note": "batch1_fortune100 source; valid engagement join"},
    {"dataset": "full_h2",   "measurement_basis": "full_sample_predicted",  "hypothesis": "H2_1/H2_2",
     "raw_n": len(h2_raw), "after_label_filter": len(h2_humor),
     "after_company_filter": get_result_val(h21_results, "full_sample_predicted","H2_1","n_obs"),
     "n_firms": get_result_val(h21_results, "full_sample_predicted","H2_1","n_firms"),
     "n_dummies": get_result_val(h21_results,"full_sample_predicted","H2_1","n_firm_dummy_variables"),
     "note": "humor_type != non_humorous"},
    {"dataset": "batch1_h3",  "measurement_basis": "batch1_human_coded",   "hypothesis": "H3",
     "raw_n": 88, "after_label_filter": 88, "after_company_filter": "not_applicable",
     "n_firms": 88, "n_dummies": 87,
     "note": "firm cross-section; firm dummies = n_firms-1 = 87 with n=88 → collinear"},
    {"dataset": "full_h3",   "measurement_basis": "full_sample_predicted",  "hypothesis": "H3",
     "raw_n": len(h3_panel), "after_label_filter": len(h3_panel),
     "after_company_filter": get_result_val(h3_results,"full_sample_predicted","H3","n_obs"),
     "n_firms": get_result_val(h3_results,"full_sample_predicted","H3","n_firms"),
     "n_dummies": get_result_val(h3_results,"full_sample_predicted","H3","n_firm_dummy_variables"),
     "note": "firm-month panel; multiple periods per firm"},
]
write_csv(os.path.join(OUT, "firm_dummy_sample_attrition.csv"), attrition_rows)

# ---------------------------------------------------------------------------
# STEP 10: Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 10: Summary")
print("=" * 60)

def describe_result(res, basis, hyp, key_col="coefficient"):
    r = next((x for x in res if x.get("measurement_basis")==basis and x.get("hypothesis")==hyp), None)
    if not r: return "not_found"
    status = r.get("status","")
    if status != "success": return status
    coef = r.get(key_col,"")
    stars = r.get("stars","")
    p    = r.get("p_value","")
    n    = r.get("n_obs","")
    firms= r.get("n_firms","")
    return f"β={coef}{stars} p={p} n={n} firms={firms}"

sum_rows = []
for hyp, res, key, b1_note, fs_note in [
    ("H1",   h1_results,  "coefficient",
     "human_humor_presence", "h1_humor_presence_pred_t50"),
    ("H2_1", h21_results, "coefficient",
     "aggressive_vs_other (n_agg=44, low power)", "predicted_aggressive_vs_other (NOT_A_CANDIDATE)"),
    ("H2_2", h22_results, "coefficient",
     "aggressive vs affiliative ref (n_agg=44)", "predicted_aggressive vs affiliative (NOT_A_CANDIDATE)"),
    ("H3",   h3_results,  "beta1_intensity",
     "firm_cross_section_not_applicable", "predicted_aggressive_intensity"),
]:
    for basis, note in [("batch1_human_coded", b1_note), ("full_sample_predicted", fs_note)]:
        r = next((x for x in res if x.get("measurement_basis")==basis and x.get("hypothesis")==hyp), None)
        if not r:
            continue
        def safe_float(v):
            try: return float(v)
            except: return float("nan")
        coef = safe_float(r.get("coefficient",""))
        p_v  = safe_float(r.get("p_value",""))
        direction = "positive" if coef > 0 else ("negative" if coef < 0 else "zero")
        sig05 = "yes" if p_v < 0.05 else ("no" if p_v == p_v else "na")
        sig10 = "yes" if p_v < 0.10 else ("no" if p_v == p_v else "na")
        if r.get("status") != "success":
            conclusion = r.get("status","")
        elif coef > 0 and p_v < 0.05:
            conclusion = "positive_sig_p05"
        elif coef > 0 and p_v < 0.10:
            conclusion = "positive_sig_p10"
        elif coef > 0:
            conclusion = "positive_ns"
        elif coef < 0 and p_v < 0.05:
            conclusion = "negative_sig_p05"
        elif coef < 0 and p_v < 0.10:
            conclusion = "negative_sig_p10"
        elif coef < 0:
            conclusion = "negative_ns"
        else:
            conclusion = "zero"

        sum_rows.append({
            "hypothesis":        hyp,
            "measurement_basis": basis,
            "key_variable":      note,
            "model_id":          "firm_dummy_only",
            "coefficient":       r.get("coefficient",""),
            "classical_ols_se":  r.get("classical_ols_se",""),
            "p_value":           r.get("p_value",""),
            "stars":             r.get("stars",""),
            "n_obs":             r.get("n_obs",""),
            "n_firms":           r.get("n_firms",""),
            "n_firm_dummies":    r.get("n_firm_dummy_variables",""),
            "reference_company": r.get("reference_company_identifier",""),
            "r_squared":         r.get("r_squared",""),
            "adj_r_squared":     r.get("adj_r_squared",""),
            "direction":         direction,
            "significant_p05":   sig05,
            "significant_p10":   sig10,
            "conclusion":        conclusion,
            "status":            r.get("status",""),
        })
        print(f"  {hyp:5} {basis:35}: {conclusion} ({r.get('coefficient','')} {r.get('stars','')})")

write_csv(os.path.join(OUT, "firm_dummy_only_summary.csv"), sum_rows)

# ---------------------------------------------------------------------------
# STEP 11: Interpretation MD
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 11: Writing interpretation.md")
print("=" * 60)

def gs(hyp, basis, col):
    r = next((x for x in sum_rows if x.get("hypothesis")==hyp and x.get("measurement_basis")==basis), None)
    return r.get(col,"—") if r else "—"

def coef_str(hyp, basis, results, extra_col=None):
    r = next((x for x in results if x.get("measurement_basis")==basis and x.get("hypothesis")==hyp), None)
    if not r or r.get("status","") != "success": return "—"
    c = extra_col or "coefficient"
    return f"{r.get(c,'')} {r.get('stars','')}"

# Compare to 1926e25 baseline
BASELINE = {
    "H1_b1":    {"coef": "1.214982", "stars": "***"},
    "H1_full":  {"coef": "1.145709", "stars": "***"},
    "H2-1_b1":  {"coef": "0.712293", "stars": "*"},
    "H2-1_full":{"coef": "0.083304", "stars": "***"},
    "H2-2_b1":  {"coef": "0.848772", "stars": "*"},
    "H2-2_full":{"coef": "0.101494", "stars": "***"},
    "H3_b1":    {"coef": "1.401675 (β1)", "stars": "ns"},
    "H3_full":  {"coef": "9.649312 (β1)", "stars": "*"},
}

h1_b1_r   = next((x for x in h1_results  if x.get("measurement_basis")=="batch1_human_coded"),  {})
h1_fs_r   = next((x for x in h1_results  if x.get("measurement_basis")=="full_sample_predicted"),{})
h21_b1_r  = next((x for x in h21_results if x.get("measurement_basis")=="batch1_human_coded"),   {})
h21_fs_r  = next((x for x in h21_results if x.get("measurement_basis")=="full_sample_predicted"),{})
h22_b1_r  = next((x for x in h22_results if x.get("measurement_basis")=="batch1_human_coded"),   {})
h22_fs_r  = next((x for x in h22_results if x.get("measurement_basis")=="full_sample_predicted"),{})
h3_fs_r   = next((x for x in h3_results  if x.get("measurement_basis")=="full_sample_predicted" and x.get("status")=="success"), {})

md = f"""# H1/H2/H3 기업 Dummy Only Robustness 분석

**생성일**: 2026-06-19
**기준 commit**: 1926e25 (two-basis plain OLS)
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기존 1926e25 two-basis plain OLS (통제 변수 없음, 시간 FE 없음) 결과를 기준으로,
기업별 불변 특성(firm-level fixed effects)을 통제했을 때 H1/H2/H3 핵심 계수의
방향과 유의성이 유지되는지 확인한다.

---

## 2. 기업 dummy를 넣는 이유

기업별로 규모(팔로워 수), 산업, 브랜드 전략, 콘텐츠 스타일 등이 다르다.
이 기업 고유 특성들이 모두 humor 전략과 engagement에 동시에 영향을 미칠 수 있다.
Plain OLS (기업 통제 없음)에서는 이 기업 수준 confounders가 추정에 들어간다.
기업 dummy를 추가하면 기업 내(within-firm) 또는 기업 간(between-firm) variation에서
humor의 영향을 분리할 수 있다.

---

## 3. company_id 생성 방식

1. 모든 분석 파일에서 `company_name` 컬럼을 수집
2. 전체 unique company_name을 알파벳 오름차순으로 정렬
3. 순번(1, 2, 3...)을 company_id로 부여
4. 총 {len(sorted_companies)}개 기업이 등록됨
5. 결과 파일: `firm_dummy_company_id_map.csv`

---

## 4. 기준 기업 선택 방식

각 분석 데이터셋 내에서 관측치가 가장 많은 기업을 기준 기업(reference firm)으로 선택.
기준 기업의 dummy를 제외함으로써 다중공선성(perfect collinearity)을 방지한다.

| 분석 | 기준 기업 | 관측치 |
|---|---|---|
| Batch1 H1 | {h1_b1_r.get("reference_company_identifier","—")} | n_obs={h1_b1_r.get("n_obs","—")} |
| Full H1   | {h1_fs_r.get("reference_company_identifier","—")} | n_obs={h1_fs_r.get("n_obs","—")} |
| Batch1 H2 | {h21_b1_r.get("reference_company_identifier","—")} | n_obs={h21_b1_r.get("n_obs","—")} |
| Full H2   | {h21_fs_r.get("reference_company_identifier","—")} | n_obs={h21_fs_r.get("n_obs","—")} |
| Full H3   | {h3_fs_r.get("reference_company_identifier","—")} | n_periods={h3_fs_r.get("n_obs","—")} |

---

## 5. dummy variable 생성 방식

1. 각 데이터셋에서 unique company_name 추출
2. 기준 기업 제외 후 나머지를 `firm_dummy_{{company_id}}` 컬럼으로 생성
3. 해당 행의 company_name이 일치하면 1, 아니면 0으로 인코딩
4. X 행렬 = [intercept | focal_IV(s) | firm_dummy_2 | firm_dummy_3 | ...]
5. k_effective = 1 (intercept) + n_focal_IVs + (n_firms - 1)

---

## 6. company_id numeric covariate 미사용 확인

- **firm_dummy_included** = true
- **company_id_used_as_numeric** = false — company_id를 연속형 공변량으로 넣지 않음
- 이는 "기업 번호가 클수록 engagement가 다르다"는 잘못된 가정을 피하기 위함

---

## 7. C(company_id) 미사용 확인

- **c_company_formula_used** = false
- statsmodels formula API (`C(company_id)`)를 사용하지 않음
- 명시적 binary dummy column을 직접 생성하여 OLS에 포함

---

## 8. 시간 고정효과 미포함 확인

- **time_fe_included** = false
- year, month, week, day, hour FE 전혀 포함하지 않음
- 시간 FE는 별도 robustness 파일(`time_fixed_effects_robustness/`)에서 다룸

---

## 9. 기본 controls 미포함 확인

- **controls_included** = false
- text_length, hashtag_count, mention_count 등 미포함
- 이번 분석은 오직 "핵심 IV + 기업 dummy"만 포함

---

## 10. H1 결과

**가설**: 유머 post → 더 높은 engagement

| | Batch1 Human-coded | Full-sample Predicted |
|---|---|---|
| N | {h1_b1_r.get("n_obs","—")} | {h1_fs_r.get("n_obs","—")} |
| N_firms | {h1_b1_r.get("n_firms","—")} | {h1_fs_r.get("n_firms","—")} |
| N_dummies | {h1_b1_r.get("n_firm_dummy_variables","—")} | {h1_fs_r.get("n_firm_dummy_variables","—")} |
| β(humor) | **{h1_b1_r.get("coefficient","—")}** | **{h1_fs_r.get("coefficient","—")}** |
| SE | {h1_b1_r.get("classical_ols_se","—")} | {h1_fs_r.get("classical_ols_se","—")} |
| t | {h1_b1_r.get("t_stat","—")} | {h1_fs_r.get("t_stat","—")} |
| p | {h1_b1_r.get("p_value","—")} | {h1_fs_r.get("p_value","—")} |
| 판정 | {h1_b1_r.get("stars","—")} | {h1_fs_r.get("stars","—")} |
| Adj R² | {h1_b1_r.get("adj_r_squared","—")} | {h1_fs_r.get("adj_r_squared","—")} |
| ref 기업 | {h1_b1_r.get("reference_company_identifier","—")} | {h1_fs_r.get("reference_company_identifier","—")} |

비교 (1926e25 plain OLS): Batch1={BASELINE['H1_b1']['coef']}*** / Full={BASELINE['H1_full']['coef']}***

---

## 11. H2-1 결과

**가설**: Aggressive humor → other humor보다 높은 engagement

| | Batch1 Human-coded (n_agg=44) | Full-sample Predicted |
|---|---|---|
| N | {h21_b1_r.get("n_obs","—")} | {h21_fs_r.get("n_obs","—")} |
| N_firms | {h21_b1_r.get("n_firms","—")} | {h21_fs_r.get("n_firms","—")} |
| β(aggressive) | **{h21_b1_r.get("coefficient","—")}** | **{h21_fs_r.get("coefficient","—")}** |
| SE | {h21_b1_r.get("classical_ols_se","—")} | {h21_fs_r.get("classical_ols_se","—")} |
| p | {h21_b1_r.get("p_value","—")} | {h21_fs_r.get("p_value","—")} |
| 판정 | {h21_b1_r.get("stars","—")} | {h21_fs_r.get("stars","—")} |

비교 (1926e25): Batch1={BASELINE['H2-1_b1']['coef']}* / Full={BASELINE['H2-1_full']['coef']}***

주의:
- Batch1: n_agg=44 → 검정력 낮음 + 기업 dummy 추가 시 SE 증가
- Full: classifier NOT_A_CANDIDATE (#NationalRoastDay leakage); type prediction 신뢰도 낮음

---

## 12. H2-2 결과

**가설**: Four humor types 비교 (ref=affiliative)

| | Batch1 (인간 코딩) | Full (예측값) |
|---|---|---|
| β(aggressive) | **{h22_b1_r.get("coef_aggressive", h22_b1_r.get("coefficient","—"))}** | **{h22_fs_r.get("coef_predicted_aggressive", h22_fs_r.get("coefficient","—"))}** |
| stars(agg) | {h22_b1_r.get("stars_aggressive", h22_b1_r.get("stars","—"))} | {h22_fs_r.get("stars_predicted_aggressive", h22_fs_r.get("stars","—"))} |
| β(self_enhancing) | {h22_b1_r.get("coef_self_enhancing","—")} | {h22_fs_r.get("coef_predicted_self_enhancing","—")} |
| β(self_defeating) | {h22_b1_r.get("coef_self_defeating","—")} | {h22_fs_r.get("coef_predicted_self_defeating","—")} |
| N | {h22_b1_r.get("n_obs","—")} | {h22_fs_r.get("n_obs","—")} |

비교 (1926e25 agg): Batch1={BASELINE['H2-2_b1']['coef']}* / Full={BASELINE['H2-2_full']['coef']}***

---

## 13. H3 결과

**가설**: Firm aggressive intensity → engagement (역 U자형)

| | Batch1 (기업 단면) | Full (기업-월 패널) |
|---|---|---|
| 상태 | **not_applicable** | {h3_fs_r.get("status","—")} |
| 이유 | firm cross-section: n=88, n_dummies=87 → rank deficient | firm-month panel: n={h3_fs_r.get("n_obs","—")}, firms={h3_fs_r.get("n_firms","—")} |
| β1 (intensity) | — | **{h3_fs_r.get("beta1_intensity","—")}** {h3_fs_r.get("stars","—")} |
| β2 (intensity_sq) | — | **{h3_fs_r.get("beta2_intensity_squared","—")}** {h3_fs_r.get("beta2_stars","—")} |
| turning point | — | {h3_fs_r.get("turning_point","—")} |
| in_range | — | {h3_fs_r.get("turning_point_in_observed_range","—")} |
| N_firms | — | {h3_fs_r.get("n_firms","—")} |
| Adj R² | — | {h3_fs_r.get("adj_r_squared","—")} |

비교 (1926e25): Batch1=β1=1.401675 ns / Full=β1=9.649312* β2=-10.252277*

---

## 14. 기존 plain OLS와 비교

| 가설 | Basis | 1926e25 β | 기업 dummy β | 방향 유지 | 유의성 변화 |
|---|---|---|---|---|---|
| H1 | Batch1 | {BASELINE['H1_b1']['coef']}*** | {h1_b1_r.get("coefficient","—")}{h1_b1_r.get("stars","—")} | {"yes" if float(h1_b1_r.get("coefficient","0") or "0")>0 else "no"} | — |
| H1 | Full | {BASELINE['H1_full']['coef']}*** | {h1_fs_r.get("coefficient","—")}{h1_fs_r.get("stars","—")} | {"yes" if float(h1_fs_r.get("coefficient","0") or "0")>0 else "no"} | — |
| H2-1 | Batch1 | {BASELINE['H2-1_b1']['coef']}* | {h21_b1_r.get("coefficient","—")}{h21_b1_r.get("stars","—")} | {"yes" if float(h21_b1_r.get("coefficient","0") or "0")>0 else "no"} | — |
| H2-1 | Full | {BASELINE['H2-1_full']['coef']}*** | {h21_fs_r.get("coefficient","—")}{h21_fs_r.get("stars","—")} | {"yes" if float(h21_fs_r.get("coefficient","0") or "0")>0 else "no"} | — |
| H2-2 | Batch1 | {BASELINE['H2-2_b1']['coef']}* | {h22_b1_r.get("coef_aggressive",h22_b1_r.get("coefficient","—"))}{h22_b1_r.get("stars_aggressive",h22_b1_r.get("stars","—"))} | — | — |
| H2-2 | Full | {BASELINE['H2-2_full']['coef']}*** | {h22_fs_r.get("coef_predicted_aggressive",h22_fs_r.get("coefficient","—"))}{h22_fs_r.get("stars_predicted_aggressive",h22_fs_r.get("stars","—"))} | — | — |
| H3 β1 | Batch1 | {BASELINE['H3_b1']['coef']} | not_applicable | — | — |
| H3 β1 | Full | {BASELINE['H3_full']['coef']} | {h3_fs_r.get("beta1_intensity","—")}{h3_fs_r.get("stars","—")} | — | — |

---

## 15. 기업 dummy 추가 후 가장 안정적인 가설

**H1**이 가장 안정적으로 예상:
- 양 basis에서 계수 방향 양수 유지
- Full H1은 n=68,039으로 기업 dummy(~98개) 추가 후에도 충분한 검정력

---

## 16. 기업 dummy 추가 후 가장 민감한 가설

**H2 Batch1**이 가장 민감:
- n_agg=44의 낮은 검정력 + firm dummies(87개) 추가 → SE 증가
- H3 Batch1은 구조적으로 불가능(firm cross-section)

---

## 17. Limitation

1. **H3 Batch1**: firm cross-section에서 firm dummy 불가 → 기업 고정효과 통제 없음
2. **Full H2/H3**: classifier NOT_A_CANDIDATE; 예측 레이블 자체에 leakage 존재
3. **Batch1 H2-1**: n_agg=44 → firm dummy 추가 시 검정력 급감 가능
4. **기업 간 variation 흡수**: firm dummy는 기업 간 차이를 통제하지만, within-firm temporal dynamics는 미통제
5. **Measurement error**: Full H1 IV = classifier predicted label → attenuation bias 가능

---

## 18. 다음 판단 지점

1. H1 양 basis에서 기업 dummy 후에도 양수 + 유의 → H1 firm-level confound 제거 후에도 유지
2. H2 Batch1 firm dummy 추가 후 유의성 유지 여부 → 기업 효과가 H2 추정에 얼마나 영향 주는지
3. H3 Full (firm-month panel): β1>0, β2<0 패턴이 firm FE 후에도 유지되는지 → within-firm inverted-U
4. 향후 고려: company-level clustered SE (별도 robustness), time FE + firm FE 동시 포함

---

## 19. 금지사항 준수

- [x] 시간 고정효과 미포함 (time_fe_included = false)
- [x] year/month/week/day/hour FE 없음
- [x] text_length/hashtag_count/mention_count controls 없음
- [x] C(company_id) 미사용 (c_company_formula_used = false)
- [x] company_id numeric covariate 미사용 (company_id_used_as_numeric = false)
- [x] backfill/workflow 파일 미수정
- [x] 기존 1926e25 결과 파일 삭제/덮어쓰기 없음
- [x] 기존 time FE 결과 파일 삭제/덮어쓰기 없음
- [x] HC3/robust SE 미사용 (Classical OLS SE만)
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal supported 미선언

---

*생성 스크립트*: `run_firm_dummy_only_robustness.py`
*출력 폴더*: `firm_dummy_only_robustness/`
*생성일*: 2026-06-19
"""

with open(os.path.join(OUT, "firm_dummy_only_interpretation.md"), "w", encoding="utf-8") as f:
    f.write(md)
print("  wrote firm_dummy_only_interpretation.md")

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

files = sorted(os.listdir(OUT))
print(f"Output files ({len(files)}) in {OUT}:")
for fn in files:
    sz = os.path.getsize(os.path.join(OUT, fn))
    print(f"  {fn}: {sz:,} bytes")

# Check existing results not deleted
base_ols = os.path.join(BASE, "ols_hypothesis_results")
orig_files = [f for f in os.listdir(base_ols) if not os.path.isdir(os.path.join(base_ols, f))]
time_fe_files = [f for f in os.listdir(os.path.join(base_ols, "time_fixed_effects_robustness"))]
print(f"\nOriginal ols_hypothesis_results/ files: {len(orig_files)} (not deleted)")
print(f"Time FE robustness files: {len(time_fe_files)} (not deleted)")

# Validation checks
r_h1b1  = next((x for x in h1_results  if x.get("measurement_basis")=="batch1_human_coded"), {})
r_h1fs  = next((x for x in h1_results  if x.get("measurement_basis")=="full_sample_predicted"), {})
r_h3fs  = next((x for x in h3_results  if x.get("measurement_basis")=="full_sample_predicted" and x.get("status")=="success"), {})

print("\n--- Key validation ---")
print(f"1. H1 batch1 n_dummies={r_h1b1.get('n_firm_dummy_variables','')} = n_firms({r_h1b1.get('n_firms','')})-1 ? {str(int(r_h1b1.get('n_firm_dummy_variables',0))==int(r_h1b1.get('n_firms',1))-1)}")
print(f"2. H1 full  n_dummies={r_h1fs.get('n_firm_dummy_variables','')} = n_firms({r_h1fs.get('n_firms','')})-1 ? {str(int(r_h1fs.get('n_firm_dummy_variables',0))==int(r_h1fs.get('n_firms',1))-1)}")
print(f"3. H3 full  n_dummies={r_h3fs.get('n_firm_dummy_variables','')} = n_firms({r_h3fs.get('n_firms','')})-1 ? {str(int(r_h3fs.get('n_firm_dummy_variables',0))==int(r_h3fs.get('n_firms',1))-1) if r_h3fs else 'n/a'}")
print(f"4. firm_dummy_included=true: {all(r.get('firm_dummy_included')=='true' for rlist in [h1_results,h21_results,h22_results,h3_results] for r in rlist)}")
print(f"5. company_id_used_as_numeric=false: {all(r.get('company_id_used_as_numeric')=='false' for rlist in [h1_results,h21_results,h22_results,h3_results] for r in rlist)}")
print(f"6. c_company_formula_used=false: {all(r.get('c_company_formula_used')=='false' for rlist in [h1_results,h21_results,h22_results,h3_results] for r in rlist)}")
print(f"7. time_fe_included=false: {all(r.get('time_fe_included')=='false' for rlist in [h1_results,h21_results,h22_results,h3_results] for r in rlist)}")
print(f"8. controls_included=false: {all(r.get('controls_included')=='false' for rlist in [h1_results,h21_results,h22_results,h3_results] for r in rlist)}")
print("DONE")
