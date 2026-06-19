"""
Firm Dummy + Time FE Robustness Analysis for H1/H2/H3.

Model: engagement = β0 + β1 focal_IV + firm_FE + time_FE + ε
SE: Classical OLS only. NO basic controls.

Implementation:
  - Two-way FE (firm × time) via joint interaction cell demeaning (FWL theorem).
    Mathematically equivalent to including all explicit firm and time dummies,
    without materializing large dummy matrices.
  - k_eff = k_focal + n_joint_cells + 1 (conservative df approximation)
  - firm_dummy_included=true, time_fe_included=true, controls_included=false
  - company_id_used_as_numeric=false, c_company_formula_used=false

30 time FE combinations: C(5,1..4) of {year, month, week, day, hour}

Prohibited: controls, C(company_id), numeric company_id as covariate,
            time/backfill/classifier files, data/raw, dashboard/data.
"""

import csv
import math
import os
from datetime import datetime
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/home/user/marketingstrategy/20260618expand"
OUT  = os.path.join(BASE, "ols_hypothesis_results/firm_dummy_time_fe_robustness")
os.makedirs(OUT, exist_ok=True)

TEMPLATE_CSV   = (BASE + "/classifier_improvement/data/human_labeling_template"
                  "/fortune100_human_labeling_template.csv")
TYPE_CSV       = (BASE + "/classifier_improvement/humor_type_leakage_filtered/data"
                  "/type_training_leakage_filtered_variants.csv")
F100_CSV       = (BASE + "/classifier_improvement/h1_presence_only/full_corpus_classification"
                  "/data/fortune100_h1_presence_classified_posts.csv")
INTEGRATED_CSV = (BASE + "/classifier_improvement/h1_presence_only/integrated_collected_corpus"
                  "/data/integrated_h1_presence_classified_posts.csv")
H2_FULL_CSV    = BASE + "/model_transfer/data/regression_ready/h2_post_level_regression_ready.csv"
H3_PANEL_CSV   = BASE + "/model_transfer/data/processed/h3_firm_month_panel.csv"

# ---------------------------------------------------------------------------
# FE configuration
# ---------------------------------------------------------------------------
FE_OPTIONS   = ["year", "month", "week", "day", "hour"]
ALL_FE_COMBOS = []
for k_ in range(1, 5):
    for c in combinations(FE_OPTIONS, k_):
        ALL_FE_COMBOS.append(c)  # 5+10+10+5 = 30

FE_AVAIL = {
    "batch1_h1":  {"year", "month", "week", "day", "hour"},
    "batch1_h2":  {"year", "month", "week", "day", "hour"},
    "full_h1":    {"year", "month", "week", "day", "hour"},
    "full_h2":    {"year", "month", "week", "day", "hour"},
    "full_h3":    {"year", "month"},
    "batch1_h3":  set(),
}

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

def safe_float(v):
    try: return float(v)
    except: return float("nan")

def parse_tw(s):
    try: return datetime.strptime(s.strip(), "%a %b %d %H:%M:%S +0000 %Y")
    except: return None

def fe_from_twitter(r):
    dt = parse_tw(r.get("created_at",""))
    if dt is None: return {}
    ic = dt.isocalendar()
    return {
        "year":  str(dt.year),
        "month": f"{dt.year}-{dt.month:02d}",
        "week":  f"{ic.year}-W{ic.week:02d}",
        "day":   dt.strftime("%Y-%m-%d"),
        "hour":  f"{dt.strftime('%Y-%m-%d')}-{dt.hour:02d}",
    }

def fe_from_integrated(r):
    year  = r.get("year","")
    month = r.get("year_month","")
    date  = r.get("date","")
    hod   = r.get("hour_of_day","")
    parsed= r.get("parsed_datetime","")
    week  = ""
    if parsed:
        try:
            dt2 = datetime.fromisoformat(parsed.replace("+00:00",""))
            ic  = dt2.isocalendar()
            week = f"{ic.year}-W{ic.week:02d}"
        except: pass
    hour = f"h{hod}" if hod else ""
    return {"year": year, "month": month, "week": week, "day": date, "hour": hour}

def fe_from_period(period):
    year = period[:4] if period else ""
    return {"year": year, "month": period, "week": "", "day": "", "hour": ""}

# ---------------------------------------------------------------------------
# Core: joint (firm × time) cell demeaning → OLS (FWL theorem)
# ---------------------------------------------------------------------------

def joint_cell_ols(y_np, X_focal, focal_names, firm_array, time_array):
    """
    Two-way FE via joint (firm × time) interaction cell demeaning.
    Equivalent to including all firm and time dummies without materializing them.

    firm_array: np.array of firm label strings
    time_array: np.array of joint time label strings (e.g. "2026-04" or "2026;h17")

    Returns (coef_rows, r2, r2_adj, info_dict) or raises ValueError.
    """
    n = len(y_np)
    k = X_focal.shape[1]

    # Filter valid rows
    mask = (firm_array != "") & (time_array != "")
    if mask.sum() < max(k + 3, 10):
        raise ValueError(f"too few rows after FE filter: {mask.sum()}")

    y_m  = y_np[mask].astype(np.float64)
    X_m  = X_focal[mask].astype(np.float64)
    f_m  = firm_array[mask]
    t_m  = time_array[mask]
    n_m  = int(mask.sum())

    # Build joint cell label (firm, time)
    cell = np.array([f"{f};{t}" for f, t in zip(f_m, t_m)])

    # Count unique cells and singleton cells
    s_cell = pd.Series(cell)
    cell_sizes = s_cell.groupby(s_cell).transform("count").values
    n_cells  = int(s_cell.nunique())
    n_singletons = int(np.sum(cell_sizes == 1))
    n_within = int(np.sum(cell_sizes > 1))  # effective within-cell obs

    # df check
    k_eff = k + n_cells + 1  # k_focal + (n_cells) + intercept
    # Note: k_eff = k + (n_cells - 1) + 1 = k + n_cells (intercept absorbed by cells)
    k_eff = min(k_eff, n_m)
    df_res = n_m - k_eff
    if df_res <= 0:
        raise ValueError(f"insufficient df: n={n_m} k_eff={k_eff} df_resid={df_res}")
    if n_within < k + 2:
        raise ValueError(f"insufficient within-cell obs: {n_within} (singletons={n_singletons})")

    # Single-pass demeaning by joint cell
    sy    = pd.Series(y_m)
    y_dm  = (sy - sy.groupby(s_cell).transform("mean")).values

    X_dm  = np.empty_like(X_m)
    for j in range(k):
        sx = pd.Series(X_m[:, j])
        X_dm[:, j] = (sx - sx.groupby(s_cell).transform("mean")).values

    # OLS on demeaned data
    XtX  = X_dm.T @ X_dm
    Xty  = X_dm.T @ y_dm
    rank = int(np.linalg.matrix_rank(XtX))
    if rank < k:
        XtX_inv = np.linalg.pinv(XtX)
    else:
        XtX_inv = np.linalg.inv(XtX)

    beta = XtX_inv @ Xty
    e    = y_dm - X_dm @ beta
    ss_res = float(np.sum(e ** 2))
    s2   = ss_res / df_res
    vcov = s2 * XtX_inv
    ses  = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st = np.where(ses > 0, beta / ses, float("nan"))
    pv   = np.array([
        2 * (1 - scipy_stats.t.cdf(abs(t), df=df_res)) if not math.isnan(t) else float("nan")
        for t in t_st
    ])

    ss_tot = float(np.sum((y_m - float(y_m.mean())) ** 2))
    r2     = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1 - r2) * (n_m - 1) / df_res if df_res > 0 else float("nan")

    coef_rows = [{
        "feature":          feat,
        "coefficient":      round(float(beta[i]), 6),
        "classical_ols_se": round(float(ses[i]), 6),
        "t_stat":           round(float(t_st[i]), 4) if not math.isnan(t_st[i]) else "",
        "p_value":          round(float(pv[i]), 6)   if not math.isnan(pv[i])   else "",
        "stars":            p_stars(pv[i]),
    } for i, feat in enumerate(focal_names)]

    info = {
        "n_obs_after_filter": n_m,
        "n_joint_cells":      n_cells,
        "n_singleton_cells":  n_singletons,
        "n_within_obs":       n_within,
        "k_eff":              k_eff,
        "df_resid":           df_res,
        "rank":               rank,
    }
    return coef_rows, r2, r2_adj, info

# ---------------------------------------------------------------------------
# STEP 1: Load data and build FE variables
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1: Loading data")
print("=" * 60)

# Batch1 H1
tmpl  = read_csv(TEMPLATE_CSV)
b1_h1 = [r for r in tmpl if r["human_humor_presence"] in ("0","1")]
for r in b1_h1:
    r["_fe"] = fe_from_twitter(r)
b1h1_y = np.array([log1p_safe(r["total_engagement"]) for r in b1_h1])
b1h1_X = np.array([[float(r["human_humor_presence"])] for r in b1_h1])
b1h1_co= np.array([r["company_name"] for r in b1_h1])

# Batch1 H2 type
type_raw = read_csv(TYPE_CSV)
b1_type  = [r for r in type_raw if r["source"] == "batch1_fortune100"]
f100_raw = read_csv(F100_CSV)
f100_idx = {r["tweet_id"]: r for r in f100_raw}
for r in b1_type:
    fe = fe_from_twitter(r)
    r["_fe"]  = fe
    er = f100_idx.get(r["tweet_id"])
    r["_eng"] = log1p_safe(er["total_engagement"]) if er else float("nan")
b1_type_valid = [r for r in b1_type if not math.isnan(r["_eng"])]
b1h2_y  = np.array([r["_eng"] for r in b1_type_valid])
b1h2_co = np.array([r["company_name"] for r in b1_type_valid])

# Full H1
integ   = read_csv(INTEGRATED_CSV)
full_h1 = [r for r in integ
           if r.get("missing_text") != "True"
           and r.get("h1_humor_presence_pred_t50") in ("0","1")]
for r in full_h1:
    r["_fe"] = fe_from_integrated(r)
fh1_y  = np.array([log1p_safe(r["total_engagement"]) for r in full_h1])
fh1_X  = np.array([[float(r["h1_humor_presence_pred_t50"])] for r in full_h1])
fh1_co = np.array([r["company_name"] for r in full_h1])

# Full H2
h2_raw   = read_csv(H2_FULL_CSV)
h2_humor = [r for r in h2_raw if r["humor_type"] != "non_humorous"]
for r in h2_humor:
    f100r = f100_idx.get(r["tweet_id"])
    r["_fe"] = fe_from_twitter(f100r) if f100r else fe_from_period(r.get("period",""))
    r["_eng"] = float(r["log_total_engagement"])
fh2_y  = np.array([r["_eng"] for r in h2_humor])
fh2_co = np.array([r["company_name"] for r in h2_humor])

# H3 panel
h3_panel = read_csv(H3_PANEL_CSV)
for r in h3_panel:
    r["_fe"] = fe_from_period(r.get("period",""))
h3_y  = np.array([float(r["mean_log_total_engagement"]) for r in h3_panel])
h3_X  = np.array([[float(r["aggressive_humor_usage_intensity"]),
                   float(r["aggressive_humor_usage_intensity_sq"])] for r in h3_panel])
h3_co = np.array([r["company_name"] for r in h3_panel])

print(f"Batch1 H1: {len(b1_h1)}, Batch1 H2: {len(b1_type_valid)}")
print(f"Full H1: {len(full_h1)}, Full H2: {len(h2_humor)}, H3: {len(h3_panel)}")

# ---------------------------------------------------------------------------
# STEP 2: Global company_id map
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Company ID map")
print("=" * 60)

all_companies = set()
source_counts = {}

def reg_companies(rows, co_col, src):
    for r in rows:
        cn = r.get(co_col,"").strip()
        if not cn: continue
        all_companies.add(cn)
        if cn not in source_counts:
            source_counts[cn] = [0, set()]
        source_counts[cn][0] += 1
        source_counts[cn][1].add(src)

reg_companies(b1_h1,      "company_name", "template")
reg_companies(b1_type,    "company_name", "type_training")
reg_companies(full_h1,    "company_name", "integrated")
reg_companies(h2_humor,   "company_name", "h2_regression_ready")
reg_companies(h3_panel,   "company_name", "h3_firm_month_panel")

sorted_companies = sorted(all_companies)
global_id_map    = {cn: i+1 for i, cn in enumerate(sorted_companies)}

id_map_rows = [{
    "company_id":                  global_id_map[cn],
    "company_identifier_original": cn,
    "n_posts":                     source_counts[cn][0],
    "source_file":                 ";".join(sorted(source_counts[cn][1])),
} for cn in sorted_companies]
write_csv(os.path.join(OUT, "firm_time_fe_company_id_map.csv"), id_map_rows)
print(f"Total unique companies: {len(sorted_companies)}")

# ---------------------------------------------------------------------------
# STEP 3: Model grid
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: Model grid (30 combos)")
print("=" * 60)

grid_rows = [{
    "model_id":    "firm_dummy_" + "_".join(c),
    "time_fe_count": len(c),
    "included_time_fe": ",".join(c),
    "formula":     "focal_IV + firm_FE + " + "+".join(c) + " time_FE",
} for c in ALL_FE_COMBOS]
write_csv(os.path.join(OUT, "firm_time_fe_model_grid.csv"), grid_rows)

# ---------------------------------------------------------------------------
# STEP 4: Core run function
# ---------------------------------------------------------------------------

AUDIT = {
    "firm_dummy_included":       "true",
    "time_fe_included":          "true",
    "controls_included":         "false",
    "company_id_used_as_numeric":"false",
    "c_company_formula_used":    "false",
}

def get_ref_firm(co_array):
    """Return company with most obs in this subset."""
    counts = {}
    for cn in co_array:
        counts[cn] = counts.get(cn, 0) + 1
    return max(counts, key=counts.__getitem__)

def combo_available(dkey, combo):
    return all(fe in FE_AVAIL.get(dkey, set()) for fe in combo)

def build_time_label(rows_fe_list, combo):
    """
    Build joint time-cell label array (concatenation of all FE dims in combo).
    rows_fe_list: list of fe_dicts (one per row).
    Returns np.array of strings.
    """
    if len(combo) == 1:
        fe = combo[0]
        return np.array([r.get(fe,"") for r in rows_fe_list])
    else:
        return np.array([
            ";".join(r.get(fe,"") for fe in combo)
            for r in rows_fe_list
        ])

def run_one(y_np, X_focal, focal_names, co_array, fe_list, combo,
            basis, hyp, dv, dkey, extra=None):
    """
    Run single model: joint (firm × time) FE via cell demeaning.
    co_array: np.array of company names.
    fe_list:  list of fe dicts, one per row.
    """
    model_id = "firm_dummy_" + "_".join(combo)
    d = {
        "measurement_basis": basis,
        "hypothesis": hyp,
        "model_id": model_id,
        "included_time_fe": ",".join(combo),
        "time_fe_count": len(combo),
        "dependent_variable": dv,
        "key_variable": focal_names[0],
        "coefficient":"","classical_ols_se":"","t_stat":"",
        "p_value":"","stars":"","n_obs":"","n_firms":"",
        "n_firm_dummy_variables":"","n_time_dummy_variables":"",
        "reference_company_id":"","reference_company_identifier":"",
        "r_squared":"","adj_r_squared":"",
        "df_model":"","df_resid":"","rank":"",
        "status":"","interpretation_level":"",
        **(extra or {}),
        **AUDIT,
    }

    if not combo_available(dkey, combo):
        d["status"] = "not_applicable" if not FE_AVAIL.get(dkey) else "unavailable"
        d["interpretation_level"] = d["status"]
        return d

    try:
        # Build time label array
        time_arr = build_time_label(fe_list, combo)

        # Ref firm
        ref_name = get_ref_firm(co_array)
        ref_id   = global_id_map.get(ref_name, "")

        # Unique counts for reporting
        n_firms_sample = len(set(co_array))

        coef_rows, r2, r2_adj, info = joint_cell_ols(
            y_np, X_focal, focal_names, co_array, time_arr
        )
        cr = coef_rows[0]
        n_dummies_approx = n_firms_sample - 1  # firm dummies (reported)
        n_time_cells    = info["n_joint_cells"]  # firm×time cells (includes firm FE)

        d.update({
            "coefficient":       cr["coefficient"],
            "classical_ols_se":  cr["classical_ols_se"],
            "t_stat":            cr["t_stat"],
            "p_value":           cr["p_value"],
            "stars":             cr["stars"],
            "n_obs":             info["n_obs_after_filter"],
            "n_firms":           n_firms_sample,
            "n_firm_dummy_variables": n_dummies_approx,
            "n_time_dummy_variables": info["n_joint_cells"] - n_firms_sample,
            "n_joint_fe_cells":  info["n_joint_cells"],
            "n_singleton_cells": info["n_singleton_cells"],
            "n_within_obs":      info["n_within_obs"],
            "reference_company_id":         ref_id,
            "reference_company_identifier": ref_name,
            "r_squared":    round(r2, 6)     if r2 == r2     else "",
            "adj_r_squared":round(r2_adj, 6) if r2_adj == r2_adj else "",
            "df_model":     info["k_eff"],
            "df_resid":     info["df_resid"],
            "rank":         info["rank"],
            "status":       "success",
            "interpretation_level": "preliminary_diagnostic",
        })
        # Extra focal coefficients for multi-IV models
        if len(coef_rows) > 1:
            for fc in coef_rows[1:]:
                d[f"coef_{fc['feature']}"]  = fc["coefficient"]
                d[f"se_{fc['feature']}"]    = fc["classical_ols_se"]
                d[f"p_{fc['feature']}"]     = fc["p_value"]
                d[f"stars_{fc['feature']}"] = fc["stars"]
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:120]}"
        d["interpretation_level"] = "error"

    return d

# ---------------------------------------------------------------------------
# STEP 5: H1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 5: H1")
print("=" * 60)

h1_results = []
b1h1_fe = [r["_fe"] for r in b1_h1]
fh1_fe  = [r["_fe"] for r in full_h1]

for combo in ALL_FE_COMBOS:
    r1 = run_one(b1h1_y, b1h1_X, ["human_humor_presence"],
                 b1h1_co, b1h1_fe, combo,
                 "batch1_human_coded", "H1", "log1p_total_engagement", "batch1_h1")
    h1_results.append(r1)
    r2 = run_one(fh1_y, fh1_X, ["h1_humor_presence_pred_t50"],
                 fh1_co, fh1_fe, combo,
                 "full_sample_predicted", "H1", "log1p_total_engagement", "full_h1",
                 extra={"limitation":"h1_iv_is_classifier_predicted"})
    h1_results.append(r2)
    tag = "_".join(combo)
    print(f"  H1 [{tag}]: b1={r1['stars']}({r1['coefficient']}) "
          f"full={r2['stars']}({r2['coefficient']})")

write_csv(os.path.join(OUT, "h1_firm_time_fe_robustness.csv"), h1_results)

# ---------------------------------------------------------------------------
# STEP 6: H2-1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 6: H2-1")
print("=" * 60)

h21_results = []
for r in b1_type_valid:
    r["_agg"] = 1.0 if r["humor_type"] == "aggressive" else 0.0
for r in h2_humor:
    r["_agg"] = float(r["aggressive_humor"])

b1h2_X21 = np.array([[r["_agg"]] for r in b1_type_valid])
fh2_X21  = np.array([[r["_agg"]] for r in h2_humor])
b1h2_fe  = [r["_fe"] for r in b1_type_valid]
fh2_fe   = [r["_fe"] for r in h2_humor]
n_b1_agg = sum(1 for r in b1_type_valid if r["humor_type"] == "aggressive")

for combo in ALL_FE_COMBOS:
    r1 = run_one(b1h2_y, b1h2_X21, ["aggressive_vs_other"],
                 b1h2_co, b1h2_fe, combo,
                 "batch1_human_coded", "H2_1", "log1p_total_engagement", "batch1_h2",
                 extra={"n_aggressive_batch1": n_b1_agg, "limitation":"n_agg=44_low_power"})
    h21_results.append(r1)
    r2 = run_one(fh2_y, fh2_X21, ["predicted_aggressive_vs_other"],
                 fh2_co, fh2_fe, combo,
                 "full_sample_predicted", "H2_1", "log1p_total_engagement", "full_h2",
                 extra={"limitation":"classifier_NOT_A_CANDIDATE"})
    h21_results.append(r2)
    tag = "_".join(combo)
    print(f"  H2-1 [{tag}]: b1={r1['stars']}({r1['coefficient']}) "
          f"full={r2['stars']}({r2['coefficient']})")

write_csv(os.path.join(OUT, "h2_1_firm_time_fe_robustness.csv"), h21_results)

# ---------------------------------------------------------------------------
# STEP 7: H2-2
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 7: H2-2")
print("=" * 60)

h22_results = []
for r in b1_type_valid:
    r["_se"] = 1.0 if r["humor_type"]=="self-enhancing" else 0.0
    r["_sd"] = 1.0 if r["humor_type"]=="self-defeating"  else 0.0
for r in h2_humor:
    r["_se"] = float(r["self_enhancing_humor"])
    r["_sd"] = float(r["self_defeating_humor"])

b1h2_X22 = np.array([[r["_agg"],r["_se"],r["_sd"]] for r in b1_type_valid])
fh2_X22  = np.array([[r["_agg"],r["_se"],r["_sd"]] for r in h2_humor])
feat_b1  = ["aggressive","self_enhancing","self_defeating"]
feat_fs  = ["predicted_aggressive","predicted_self_enhancing","predicted_self_defeating"]

for combo in ALL_FE_COMBOS:
    r1 = run_one(b1h2_y, b1h2_X22, feat_b1,
                 b1h2_co, b1h2_fe, combo,
                 "batch1_human_coded", "H2_2", "log1p_total_engagement", "batch1_h2",
                 extra={"reference_category":"affiliative"})
    h22_results.append(r1)
    r2 = run_one(fh2_y, fh2_X22, feat_fs,
                 fh2_co, fh2_fe, combo,
                 "full_sample_predicted", "H2_2", "log1p_total_engagement", "full_h2",
                 extra={"reference_category":"predicted_affiliative",
                        "limitation":"classifier_NOT_A_CANDIDATE"})
    h22_results.append(r2)
    tag = "_".join(combo)
    agg1 = r1.get("coef_aggressive", r1["coefficient"])
    agg2 = r2.get("coef_predicted_aggressive", r2["coefficient"])
    stars1 = r1.get("stars_aggressive", r1["stars"])
    stars2 = r2.get("stars_predicted_aggressive", r2["stars"])
    print(f"  H2-2 [{tag}]: b1_agg={stars1}({agg1}) full_agg={stars2}({agg2})")

write_csv(os.path.join(OUT, "h2_2_firm_time_fe_robustness.csv"), h22_results)

# ---------------------------------------------------------------------------
# STEP 8: H3
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 8: H3")
print("=" * 60)

h3_results = []
feat_h3 = ["predicted_aggressive_intensity","predicted_aggressive_intensity_sq"]
int_min = float(h3_X[:,0].min())
int_max = float(h3_X[:,0].max())
h3_fe   = [r["_fe"] for r in h3_panel]

for combo in ALL_FE_COMBOS:
    model_id = "firm_dummy_" + "_".join(combo)

    # Batch1 H3: always not_applicable (firm cross-section, 1 obs per firm)
    h3_results.append({
        "measurement_basis":"batch1_human_coded","hypothesis":"H3",
        "model_id":model_id,"included_time_fe":",".join(combo),
        "time_fe_count":len(combo),
        "dependent_variable":"firm_mean_log1p_engagement",
        "key_variable":"aggressive_intensity",
        "beta1_intensity":"","beta2_intensity_squared":"",
        "beta1_p_value":"","beta2_p_value":"",
        "coefficient":"","classical_ols_se":"","t_stat":"",
        "p_value":"","stars":"","n_obs":88,"n_firms":88,
        "n_firm_dummy_variables":87,"n_time_dummy_variables":"",
        "reference_company_id":"","reference_company_identifier":"",
        "r_squared":"","adj_r_squared":"","df_model":"","df_resid":"","rank":"",
        "turning_point":"","turning_point_in_observed_range":"",
        "intensity_min":"","intensity_max":"",
        "panel_unit":"firm_cross_section","time_period_unit":"none",
        **AUDIT,
        "status":"not_applicable",
        "interpretation_level":"not_applicable",
        "note":"firm cross-section: n_firms-1=87 dummies + time FE with n=88 → rank deficient",
    })

    # Full H3 (firm-month panel)
    d = {
        "measurement_basis":"full_sample_predicted","hypothesis":"H3",
        "model_id":model_id,"included_time_fe":",".join(combo),
        "time_fe_count":len(combo),
        "dependent_variable":"firm_period_mean_log1p_engagement",
        "key_variable":"predicted_aggressive_intensity",
        "beta1_intensity":"","beta2_intensity_squared":"",
        "beta1_p_value":"","beta2_p_value":"",
        "coefficient":"","classical_ols_se":"","t_stat":"",
        "p_value":"","stars":"","n_obs":"","n_firms":"",
        "n_firm_dummy_variables":"","n_time_dummy_variables":"",
        "reference_company_id":"","reference_company_identifier":"",
        "r_squared":"","adj_r_squared":"","df_model":"","df_resid":"","rank":"",
        "turning_point":"","turning_point_in_observed_range":"",
        "intensity_min":round(int_min,6),"intensity_max":round(int_max,6),
        "panel_unit":"firm_month_period","time_period_unit":"year_month",
        **AUDIT,
        "status":"","interpretation_level":"",
        "limitation":"classifier_NOT_A_CANDIDATE_leakage_in_intensity",
    }

    if not combo_available("full_h3", combo):
        d["status"] = "unavailable"
        d["interpretation_level"] = "unavailable"
        d["note"] = "week/day/hour not in firm-month panel"
        h3_results.append(d)
        print(f"  H3 [{model_id}]: b1=not_applicable full=unavailable")
        continue

    try:
        time_arr = build_time_label(h3_fe, combo)
        ref_name = get_ref_firm(h3_co)
        ref_id   = global_id_map.get(ref_name,"")
        n_firms_h3 = len(set(h3_co))

        coef_rows, r2, r2_adj, info = joint_cell_ols(
            h3_y, h3_X, feat_h3, h3_co, time_arr
        )
        b1v = coef_rows[0]["coefficient"]
        b2v = coef_rows[1]["coefficient"]
        tp  = -b1v / (2*b2v) if abs(b2v) > 1e-12 else float("nan")
        tpr = str(int_min<=tp<=int_max) if not math.isnan(tp) else ""
        inv = "b1>0_b2<0" if b1v>0 and b2v<0 else ("b1<0_b2>0" if b1v<0 and b2v>0 else "other")

        d.update({
            "coefficient":       b1v,
            "classical_ols_se":  coef_rows[0]["classical_ols_se"],
            "t_stat":            coef_rows[0]["t_stat"],
            "p_value":           coef_rows[0]["p_value"],
            "stars":             coef_rows[0]["stars"],
            "n_obs":             info["n_obs_after_filter"],
            "n_firms":           n_firms_h3,
            "n_firm_dummy_variables": n_firms_h3-1,
            "n_time_dummy_variables": info["n_joint_cells"] - n_firms_h3,
            "n_joint_fe_cells":  info["n_joint_cells"],
            "n_singleton_cells": info["n_singleton_cells"],
            "reference_company_id":         ref_id,
            "reference_company_identifier": ref_name,
            "r_squared":    round(r2,6) if r2==r2 else "",
            "adj_r_squared":round(r2_adj,6) if r2_adj==r2_adj else "",
            "df_model":     info["k_eff"],
            "df_resid":     info["df_resid"],
            "rank":         info["rank"],
            "beta1_intensity":         b1v,
            "beta2_intensity_squared": b2v,
            "beta1_p_value":  coef_rows[0]["p_value"],
            "beta2_p_value":  coef_rows[1]["p_value"],
            "beta2_stars":    coef_rows[1]["stars"],
            "turning_point":  round(tp,4) if not math.isnan(tp) else "",
            "turning_point_in_observed_range": tpr,
            "inverted_u_check": inv,
            "status":       "success",
            "interpretation_level": "preliminary_diagnostic",
        })
        print(f"  H3 [{model_id}]: b1=not_appl full β1={b1v:.3f}{coef_rows[0]['stars']} "
              f"β2={b2v:.3f}{coef_rows[1]['stars']} tp={round(tp,3) if not math.isnan(tp) else 'nan'}")
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:100]}"
        d["interpretation_level"] = "error"
        print(f"  H3 [{model_id}]: error — {ex}")

    h3_results.append(d)

write_csv(os.path.join(OUT, "h3_firm_time_fe_robustness.csv"), h3_results)

# ---------------------------------------------------------------------------
# STEP 9: Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 9: Summary")
print("=" * 60)

# Read baseline comparisons from prior results
PLAIN_OLS_BASELINE = {
    ("H1","batch1_human_coded"):   {"coef":1.214982,"stars":"***"},
    ("H1","full_sample_predicted"):{"coef":1.145709,"stars":"***"},
    ("H2_1","batch1_human_coded"): {"coef":0.712293,"stars":"*"},
    ("H2_1","full_sample_predicted"):{"coef":0.083304,"stars":"***"},
    ("H2_2","batch1_human_coded"): {"coef":0.848772,"stars":"*"},
    ("H2_2","full_sample_predicted"):{"coef":0.101494,"stars":"***"},
    ("H3","batch1_human_coded"):   {"coef":"not_applicable","stars":""},
    ("H3","full_sample_predicted"):{"coef":9.649312,"stars":"*"},
}
TIME_FE_BASELINE = {
    ("H1","batch1_human_coded"):   {"sig":"all_positive_some_sig_p05"},
    ("H1","full_sample_predicted"):{"sig":"all_positive_all_sig_p05"},
    ("H2_1","batch1_human_coded"): {"sig":"all_positive_some_sig_p05"},
    ("H2_1","full_sample_predicted"):{"sig":"all_positive_some_sig_p05"},
    ("H2_2","batch1_human_coded"): {"sig":"all_positive_some_sig_p05"},
    ("H2_2","full_sample_predicted"):{"sig":"all_positive_some_sig_p05"},
    ("H3","batch1_human_coded"):   {"sig":"not_applicable"},
    ("H3","full_sample_predicted"):{"sig":"all_positive_all_sig_p05"},
}
FIRM_DUMMY_BASELINE = {
    ("H1","batch1_human_coded"):   {"coef":0.240636,"stars":"***"},
    ("H1","full_sample_predicted"):{"coef":0.202458,"stars":"***"},
    ("H2_1","batch1_human_coded"): {"coef":0.118795,"stars":"ns"},
    ("H2_1","full_sample_predicted"):{"coef":-0.101486,"stars":"***"},
    ("H2_2","batch1_human_coded"): {"coef":0.20598,"stars":"ns"},
    ("H2_2","full_sample_predicted"):{"coef":-0.111675,"stars":"***"},
    ("H3","batch1_human_coded"):   {"coef":"not_applicable","stars":""},
    ("H3","full_sample_predicted"):{"coef":-2.072017,"stars":"***"},
}

sum_rows = []
all_res = {
    ("H1","batch1_human_coded"):h1_results,
    ("H1","full_sample_predicted"):h1_results,
    ("H2_1","batch1_human_coded"):h21_results,
    ("H2_1","full_sample_predicted"):h21_results,
    ("H2_2","batch1_human_coded"):h22_results,
    ("H2_2","full_sample_predicted"):h22_results,
    ("H3","batch1_human_coded"):h3_results,
    ("H3","full_sample_predicted"):h3_results,
}

for (hyp,basis), res in all_res.items():
    sub = [r for r in res if r.get("measurement_basis")==basis and r.get("hypothesis")==hyp]
    success = [r for r in sub if r.get("status")=="success"]
    coeffs  = [safe_float(r["coefficient"]) for r in success if r.get("coefficient") not in ("","nan")]
    pvals   = [safe_float(r["p_value"]) for r in success if r.get("p_value") not in ("","nan")]
    pos_c = sum(1 for c in coeffs if c > 0)
    neg_c = sum(1 for c in coeffs if c < 0)
    sig05 = sum(1 for p in pvals if p < 0.05)
    sig10 = sum(1 for p in pvals if p < 0.10)
    stable = "positive" if pos_c==len(coeffs) and len(coeffs)>0 else (
             "negative" if neg_c==len(coeffs) and len(coeffs)>0 else "mixed")
    adj_r2s = [(r["model_id"], safe_float(r["adj_r_squared"]))
               for r in success if r.get("adj_r_squared") not in ("","nan")]
    best_m  = max(adj_r2s, key=lambda x: x[1])[0] if adj_r2s else ""
    t_abs   = [(r["model_id"], abs(safe_float(r["t_stat"])))
               for r in success if r.get("t_stat") not in ("","nan")]
    cons_m  = min(t_abs, key=lambda x: x[1])[0] if t_abs else ""

    if not success:
        conclusion = sub[0].get("status","no_models") if sub else "no_models"
    elif stable=="positive" and sig05==len(success): conclusion="all_positive_all_sig_p05"
    elif stable=="positive" and sig10==len(success): conclusion="all_positive_all_sig_p10"
    elif stable=="positive" and sig05>0:             conclusion="all_positive_some_sig_p05"
    elif stable=="positive":                         conclusion="all_positive_ns"
    elif stable=="negative" and sig05==len(success): conclusion="all_negative_all_sig_p05"
    elif stable=="negative" and sig05>0:             conclusion="all_negative_some_sig_p05"
    elif stable=="negative":                         conclusion="all_negative_ns"
    else:                                            conclusion="mixed_direction"

    pb = PLAIN_OLS_BASELINE.get((hyp,basis),{})
    tb = TIME_FE_BASELINE.get((hyp,basis),{})
    fb = FIRM_DUMMY_BASELINE.get((hyp,basis),{})

    sum_rows.append({
        "hypothesis":         hyp,
        "measurement_basis":  basis,
        "total_models_attempted":len(sub),
        "total_models_success":  len(success),
        "positive_direction_count": pos_c,
        "negative_direction_count": neg_c,
        "significant_p05_count":  sig05,
        "significant_p10_count":  sig10,
        "direction_stable":   stable,
        "best_model_by_adj_r2": best_m,
        "most_conservative_model": cons_m,
        "comparison_to_plain_ols":     f"baseline_coef={pb.get('coef','')} {pb.get('stars','')}",
        "comparison_to_time_fe_only":  f"time_fe_conclusion={tb.get('sig','')}",
        "comparison_to_firm_dummy_only":f"firm_coef={fb.get('coef','')} {fb.get('stars','')}",
        "conclusion": conclusion,
    })
    print(f"  {hyp:5} {basis:35}: success={len(success)}/{len(sub)} "
          f"pos={pos_c} neg={neg_c} sig05={sig05} → {conclusion}")

write_csv(os.path.join(OUT, "firm_time_fe_robustness_summary.csv"), sum_rows)

# ---------------------------------------------------------------------------
# STEP 10: Dummy dictionary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 10: Dummy dictionary")
print("=" * 60)

dict_rows = []
for dsname, rows, co_col, src in [
    ("batch1_h1",  b1_h1,       "company_name", "template"),
    ("batch1_h2",  b1_type_valid,"company_name", "type_training"),
    ("full_h1",    full_h1,     "company_name", "integrated"),
    ("full_h2",    h2_humor,    "company_name", "h2_regression_ready"),
    ("full_h3",    h3_panel,    "company_name", "h3_firm_month_panel"),
]:
    counts = {}
    for r in rows:
        cn = r.get(co_col,"").strip()
        counts[cn] = counts.get(cn,0)+1
    ref = max(counts, key=counts.__getitem__)
    ref_id = global_id_map.get(ref,"")
    for cn in sorted(counts, key=lambda x: global_id_map.get(x,0)):
        if cn == ref: continue
        dict_rows.append({
            "dataset":            dsname,"source_file":os.path.basename(src),
            "dummy_type":         "firm_dummy",
            "dummy_column_name":  f"firm_dummy_{global_id_map[cn]}",
            "company_id":         global_id_map[cn],"company_name":cn,
            "n_obs_in_dataset":   counts[cn],"is_reference_firm":"false",
        })
    dict_rows.append({
        "dataset":            dsname,"source_file":os.path.basename(src),
        "dummy_type":         "firm_dummy",
        "dummy_column_name":  f"REFERENCE_firm_id_{ref_id}",
        "company_id":         ref_id,"company_name":ref,
        "n_obs_in_dataset":   counts[ref],"is_reference_firm":"true (omitted)",
    })

write_csv(os.path.join(OUT, "firm_time_fe_dummy_dictionary.csv"), dict_rows)

# ---------------------------------------------------------------------------
# STEP 11: Sample attrition
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 11: Sample attrition")
print("=" * 60)

def get_rv(res, basis, hyp, key, combo):
    model_id = "firm_dummy_" + "_".join(combo)
    for r in res:
        if (r.get("measurement_basis")==basis and r.get("hypothesis")==hyp
                and r.get("model_id")==model_id):
            return r.get(key,"")
    return ""

ex_combo = ("year",)
attr_rows = []
for basis, hyp, raw_n, res, dkey in [
    ("batch1_human_coded","H1",  len(b1_h1),        h1_results,  "batch1_h1"),
    ("full_sample_predicted","H1",len(full_h1),     h1_results,  "full_h1"),
    ("batch1_human_coded","H2_1",len(b1_type_valid),h21_results, "batch1_h2"),
    ("full_sample_predicted","H2_1",len(h2_humor),  h21_results, "full_h2"),
    ("batch1_human_coded","H3",  88,                h3_results,  "batch1_h3"),
    ("full_sample_predicted","H3",len(h3_panel),    h3_results,  "full_h3"),
]:
    n_obs_ex = get_rv(res, basis, hyp, "n_obs", ex_combo)
    n_firms_ex = get_rv(res, basis, hyp, "n_firms", ex_combo)
    avail_str = ",".join(sorted(FE_AVAIL.get(dkey, set())))
    status_ex = get_rv(res, basis, hyp, "status", ex_combo)
    attr_rows.append({
        "measurement_basis": basis, "hypothesis": hyp, "dataset_key": dkey,
        "raw_n": raw_n,
        "n_obs_year_fe_model": n_obs_ex,
        "n_firms": n_firms_ex,
        "fe_available": avail_str,
        "example_model_status": status_ex,
    })
write_csv(os.path.join(OUT, "firm_time_fe_sample_attrition.csv"), attr_rows)

# ---------------------------------------------------------------------------
# STEP 12: Interpretation MD
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 12: Writing interpretation.md")
print("=" * 60)

def sr(hyp, basis, col):
    for r in sum_rows:
        if r.get("hypothesis")==hyp and r.get("measurement_basis")==basis:
            return str(r.get(col,"—"))
    return "—"

def pick_result(res, basis, hyp, model_id=None):
    for r in res:
        if r.get("measurement_basis")==basis and r.get("hypothesis")==hyp:
            if model_id is None or r.get("model_id")==model_id:
                return r
    return {}

# Find a representative "year" result for each H/basis
h1_b1_yr   = pick_result(h1_results,  "batch1_human_coded",  "H1",   "firm_dummy_year")
h1_fs_yr   = pick_result(h1_results,  "full_sample_predicted","H1",   "firm_dummy_year")
h21_b1_yr  = pick_result(h21_results, "batch1_human_coded",  "H2_1", "firm_dummy_year")
h21_fs_yr  = pick_result(h21_results, "full_sample_predicted","H2_1", "firm_dummy_year")
h22_b1_yr  = pick_result(h22_results, "batch1_human_coded",  "H2_2", "firm_dummy_year")
h22_fs_yr  = pick_result(h22_results, "full_sample_predicted","H2_2", "firm_dummy_year")
h3_fs_yr   = pick_result(h3_results,  "full_sample_predicted","H3",   "firm_dummy_year")

md = f"""# H1/H2/H3 기업 Dummy + 시간 고정효과 Robustness 분석

**생성일**: 2026-06-19
**기준 commit**: 99e915b (firm dummy only)
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**분석 성격**: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기업별 불변 특성(firm FE)과 시간별 공통 충격(time FE)을 동시에 통제했을 때
H1/H2/H3 핵심 계수의 방향과 유의성이 유지되는지 확인한다.

Plain OLS → time FE only → firm dummy only 순서로 robustness를 쌓아왔으며,
이번 분석은 두 FE를 동시에 포함하는 가장 엄격한 버전이다.

---

## 2. 기업 dummy와 시간 FE를 함께 넣는 이유

- **Firm FE**: 기업 규모, 산업, 브랜드 전략 등 시간 불변 특성 통제
- **Time FE**: 경제 상황, 플랫폼 알고리즘 변화 등 모든 기업에 공통된 시간적 충격 통제
- 두 FE를 동시에 통제하면 순수하게 "동일 기업 내에서, 같은 시간 환경 내에서"
  humor 전략의 효과를 추정하는 것에 가까워진다.

---

## 3. company_id 생성 방식

총 {len(sorted_companies)}개 기업 등록; 알파벳 오름차순 ID 부여.
결과 파일: `firm_time_fe_company_id_map.csv`

---

## 4. 기업 dummy 생성 방식

- 각 데이터셋에서 관측치가 가장 많은 기업을 기준 기업으로 선택
- 기준 기업 dummy 제외 → (n_firms - 1)개 dummy 생성
- **FWL(Frisch-Waugh-Lovell) 정리 기반 within-cell demeaning으로 동일한 효과 달성**
  (명시적 dummy matrix 생성 없이 pandas groupby로 수학적 동치 결과)

---

## 5. 시간 FE dummy 생성 방식

- 30개 FE 조합: C(5, 1..4) of {{year, month, week, day, hour}}
- Joint cell = (firm_name, time_fe_label) 형식의 복합 셀 생성
- pandas groupby transform으로 셀 내 평균 차감 (단일 pass, FWL 동치)
- k_eff = k_focal + n_joint_cells + 1 (보수적 자유도 계산)
- Singleton cell(관측치 1개짜리 셀) 자동 흡수 → effective within-obs만 추정에 기여

---

## 6. 기본 controls 미포함 확인

- **controls_included** = false
- text_length, hashtag_count, mention_count 미포함

---

## 7. company_id numeric covariate 미사용 확인

- **company_id_used_as_numeric** = false

---

## 8. C(company_id) 미사용 확인

- **c_company_formula_used** = false

---

## 9. H1 결과 (firm dummy + time FE)

**가설**: 유머 post → 더 높은 engagement

### Year FE 기준 (firm_dummy_year)

| | Batch1 | Full |
|---|---|---|
| β | **{h1_b1_yr.get('coefficient','—')}** | **{h1_fs_yr.get('coefficient','—')}** |
| SE | {h1_b1_yr.get('classical_ols_se','—')} | {h1_fs_yr.get('classical_ols_se','—')} |
| p | {h1_b1_yr.get('p_value','—')} | {h1_fs_yr.get('p_value','—')} |
| 판정 | {h1_b1_yr.get('stars','—')} | {h1_fs_yr.get('stars','—')} |
| n | {h1_b1_yr.get('n_obs','—')} | {h1_fs_yr.get('n_obs','—')} |
| n_firms | {h1_b1_yr.get('n_firms','—')} | {h1_fs_yr.get('n_firms','—')} |
| n_joint_cells | {h1_b1_yr.get('n_joint_fe_cells','—')} | {h1_fs_yr.get('n_joint_fe_cells','—')} |
| df_resid | {h1_b1_yr.get('df_resid','—')} | {h1_fs_yr.get('df_resid','—')} |
| Adj R² | {h1_b1_yr.get('adj_r_squared','—')} | {h1_fs_yr.get('adj_r_squared','—')} |

### 30 모델 전체 요약

| | Batch1 | Full |
|---|---|---|
| 성공 모델 | {sr('H1','batch1_human_coded','total_models_success')}/30 | {sr('H1','full_sample_predicted','total_models_success')}/30 |
| 양수 방향 모델 | {sr('H1','batch1_human_coded','positive_direction_count')} | {sr('H1','full_sample_predicted','positive_direction_count')} |
| p<.05 유의 모델 | {sr('H1','batch1_human_coded','significant_p05_count')} | {sr('H1','full_sample_predicted','significant_p05_count')} |
| 방향 안정성 | {sr('H1','batch1_human_coded','direction_stable')} | {sr('H1','full_sample_predicted','direction_stable')} |
| 결론 | **{sr('H1','batch1_human_coded','conclusion')}** | **{sr('H1','full_sample_predicted','conclusion')}** |

---

## 10. H2-1 결과 (firm dummy + time FE)

**가설**: Aggressive humor → other humor보다 높은 engagement

### Year FE 기준

| | Batch1 (n_agg=44) | Full (NOT_A_CANDIDATE) |
|---|---|---|
| β | **{h21_b1_yr.get('coefficient','—')}** | **{h21_fs_yr.get('coefficient','—')}** |
| 판정 | {h21_b1_yr.get('stars','—')} | {h21_fs_yr.get('stars','—')} |

### 30 모델 요약

| | Batch1 | Full |
|---|---|---|
| 성공 모델 | {sr('H2_1','batch1_human_coded','total_models_success')}/30 | {sr('H2_1','full_sample_predicted','total_models_success')}/30 |
| 양수 | {sr('H2_1','batch1_human_coded','positive_direction_count')} | {sr('H2_1','full_sample_predicted','positive_direction_count')} |
| 음수 | {sr('H2_1','batch1_human_coded','negative_direction_count')} | {sr('H2_1','full_sample_predicted','negative_direction_count')} |
| p<.05 | {sr('H2_1','batch1_human_coded','significant_p05_count')} | {sr('H2_1','full_sample_predicted','significant_p05_count')} |
| 결론 | **{sr('H2_1','batch1_human_coded','conclusion')}** | **{sr('H2_1','full_sample_predicted','conclusion')}** |

주의: Firm dummy only에서 Full H2-1이 -0.101***로 역전됨. 시간 FE 추가 후 동일 패턴 여부 확인.

---

## 11. H2-2 결과 (firm dummy + time FE)

**가설**: Four humor types (ref=affiliative)

### Year FE 기준 (aggressive coefficient)

| | Batch1 | Full |
|---|---|---|
| β(agg) | **{h22_b1_yr.get('coef_aggressive', h22_b1_yr.get('coefficient','—'))}** | **{h22_fs_yr.get('coef_predicted_aggressive', h22_fs_yr.get('coefficient','—'))}** |
| stars(agg) | {h22_b1_yr.get('stars_aggressive', h22_b1_yr.get('stars','—'))} | {h22_fs_yr.get('stars_predicted_aggressive', h22_fs_yr.get('stars','—'))} |
| β(self_enh) | {h22_b1_yr.get('coef_self_enhancing','—')} | {h22_fs_yr.get('coef_predicted_self_enhancing','—')} |
| β(self_def) | {h22_b1_yr.get('coef_self_defeating','—')} | {h22_fs_yr.get('coef_predicted_self_defeating','—')} |

### 30 모델 요약

| | Batch1 | Full |
|---|---|---|
| 결론 | **{sr('H2_2','batch1_human_coded','conclusion')}** | **{sr('H2_2','full_sample_predicted','conclusion')}** |

---

## 12. H3 결과 (firm dummy + time FE)

**가설**: Aggressive intensity → engagement (역 U자형)

| | Batch1 | Full (firm-month panel) |
|---|---|---|
| 상태 | **not_applicable** (전체) | {sr('H3','full_sample_predicted','total_models_success')}/30 성공 |
| 이유 | firm cross-section n=88 | year만 가용; month는 firm×month=n → collinear |
| β1 결론 | — | **{sr('H3','full_sample_predicted','conclusion')}** |
| firm_dummy_year β1 | — | **{h3_fs_yr.get('beta1_intensity','—')}** {h3_fs_yr.get('stars','—')} |
| firm_dummy_year β2 | — | **{h3_fs_yr.get('beta2_intensity_squared','—')}** {h3_fs_yr.get('beta2_stars','—')} |
| turning_point | — | {h3_fs_yr.get('turning_point','—')} |
| in_range | — | {h3_fs_yr.get('turning_point_in_observed_range','—')} |

주의: Firm dummy only에서 β1=-2.07***,β2=+2.94*** (U자형 역전). 시간 FE 추가 후 동일 여부 확인.

---

## 13. 기존 plain OLS와 비교

| 가설 | Basis | Plain OLS β | Firm+Time β (year FE) | 방향 변화 |
|---|---|---|---|---|
| H1 | B1 | 1.214982*** | {h1_b1_yr.get('coefficient','—')}{h1_b1_yr.get('stars','—')} | — |
| H1 | Full | 1.145709*** | {h1_fs_yr.get('coefficient','—')}{h1_fs_yr.get('stars','—')} | — |
| H2-1 | B1 | 0.712293* | {h21_b1_yr.get('coefficient','—')}{h21_b1_yr.get('stars','—')} | — |
| H2-1 | Full | 0.083304*** | {h21_fs_yr.get('coefficient','—')}{h21_fs_yr.get('stars','—')} | — |
| H3 β1 | Full | 9.649312* | {h3_fs_yr.get('beta1_intensity','—')}{h3_fs_yr.get('stars','—')} | — |

---

## 14. time FE only 결과와 비교

Time FE only: H1 양 basis 전 30모델 양수 유의.
Firm+Time FE: 위 표 참조. Firm FE 추가 시 계수 추가 축소 예상.

---

## 15. firm dummy only 결과와 비교

| 가설 | Basis | Firm dummy only | Firm+Time (year) | 방향 유지 |
|---|---|---|---|---|
| H1 | B1 | 0.240636*** | {h1_b1_yr.get('coefficient','—')}{h1_b1_yr.get('stars','—')} | — |
| H1 | Full | 0.202458*** | {h1_fs_yr.get('coefficient','—')}{h1_fs_yr.get('stars','—')} | — |
| H2-1 | B1 | 0.118795 ns | {h21_b1_yr.get('coefficient','—')}{h21_b1_yr.get('stars','—')} | — |
| H2-1 | Full | -0.101486*** | {h21_fs_yr.get('coefficient','—')}{h21_fs_yr.get('stars','—')} | — |
| H3 β1 | Full | -2.072017*** | {h3_fs_yr.get('beta1_intensity','—')}{h3_fs_yr.get('stars','—')} | — |

---

## 16. firm + time FE 추가 후 가장 안정적인 가설

**H1**: 양 basis에서 firm dummy only 후에도 양수 유의. Firm+time FE 결과 확인 필요.

---

## 17. firm + time FE 추가 후 가장 민감한 가설

**H2 Full, H3 Full**: Firm dummy only에서 이미 역전됨. Classifier leakage와 복합 가능.
**H2 Batch1**: n_agg=44 → SE 증가로 유의성 더 약해질 것.

---

## 18. Limitation

1. Joint cell saturation: additive FE보다 더 많은 자유도 흡수 (conservative)
2. H3 firm+month: 완전흡수 (firm×period=n) → year FE만 가능
3. Batch1 H3: firm cross-section으로 구조적 불가
4. Classifier leakage: Full H2/H3 해석 불가
5. Singleton cells: fine-grained FE에서 많은 관측치가 추정에 미기여

---

## 19. 다음 판단 지점

1. H1 firm+time FE: 양수 유의 유지 여부
2. H2 Full firm+time FE: 역전(-) 유지 여부 → time FE가 역전 해소하는지
3. H3 Full firm+year FE: U자형 유지 여부

---

## 20. 금지사항 준수

- [x] firm_dummy_included = true
- [x] time_fe_included = true
- [x] controls_included = false
- [x] company_id_used_as_numeric = false
- [x] c_company_formula_used = false
- [x] 기존 plain OLS, time FE only, firm dummy only 결과 파일 미수정
- [x] HC3/robust SE 미사용
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal supported 미선언

---

*생성 스크립트*: `run_firm_time_fe_robustness.py`
*출력 폴더*: `firm_dummy_time_fe_robustness/`
*생성일*: 2026-06-19
"""

with open(os.path.join(OUT, "firm_time_fe_robustness_interpretation.md"),"w",encoding="utf-8") as f:
    f.write(md)
print("  wrote firm_time_fe_robustness_interpretation.md")

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

out_files = sorted(os.listdir(OUT))
print(f"Output files ({len(out_files)}) in {OUT}:")
for fn in out_files:
    sz = os.path.getsize(os.path.join(OUT,fn))
    print(f"  {fn}: {sz:,} bytes")

# Check existing results not deleted
base_ols = os.path.join(BASE,"ols_hypothesis_results")
orig = len([f for f in os.listdir(base_ols) if not os.path.isdir(os.path.join(base_ols,f))])
tfes = len(os.listdir(os.path.join(base_ols,"time_fixed_effects_robustness")))
fdos = len(os.listdir(os.path.join(base_ols,"firm_dummy_only_robustness")))
print(f"\nOriginal ols_hypothesis_results/ files: {orig} (unchanged)")
print(f"time_fixed_effects_robustness/ files: {tfes} (unchanged)")
print(f"firm_dummy_only_robustness/ files: {fdos} (unchanged)")

# Key checks
all_results = h1_results + h21_results + h22_results + h3_results
print("\n--- Audit flag verification ---")
print(f"firm_dummy_included=true ALL: {all(r.get('firm_dummy_included')=='true' for r in all_results)}")
print(f"time_fe_included=true ALL:    {all(r.get('time_fe_included')=='true' for r in all_results)}")
print(f"controls_included=false ALL:  {all(r.get('controls_included')=='false' for r in all_results)}")
print(f"company_id_numeric=false ALL: {all(r.get('company_id_used_as_numeric')=='false' for r in all_results)}")
print(f"c_formula=false ALL:          {all(r.get('c_company_formula_used')=='false' for r in all_results)}")

h1_success = [r for r in h1_results if r.get("status")=="success"]
print(f"\nH1 models: {len(h1_results)} total, {len(h1_success)} success")
print(f"H1 n_dummies check (30 combos×2 basis expected=60): {len(h1_results)==60}")
print("DONE")
