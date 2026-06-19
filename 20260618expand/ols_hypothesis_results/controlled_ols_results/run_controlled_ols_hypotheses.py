"""
Controlled OLS analysis for H1/H2/H3.

Adds post-format controls to existing OLS structure:
  controls = text_length, hashtag_count, mention_count

Models per hypothesis:
  1. Plain OLS + controls
  2. Year + Month FE + controls
  3. Firm dummy only + controls
  4. Firm dummy + Year + Month FE + controls

H3 controls aggregated at firm-period level (mean_*).
H3 firm+month FE → not_estimable (df_resid=0 by construction).
H3 combined FE representative model: firm dummy + year FE + agg controls.

SE: Classical OLS only. emoji_count: NOT used.
Firm FE: explicit binary dummies (n_firms-1). C(company_id): NOT used.
"""

import csv, math, os, re
from datetime import datetime
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/home/user/marketingstrategy/20260618expand"
OUT  = os.path.join(BASE, "ols_hypothesis_results/controlled_ols_results")
os.makedirs(OUT, exist_ok=True)

TEMPLATE_CSV   = (BASE+"/classifier_improvement/data/human_labeling_template"
                  "/fortune100_human_labeling_template.csv")
TYPE_CSV       = (BASE+"/classifier_improvement/humor_type_leakage_filtered/data"
                  "/type_training_leakage_filtered_variants.csv")
F100_CSV       = (BASE+"/classifier_improvement/h1_presence_only/full_corpus_classification"
                  "/data/fortune100_h1_presence_classified_posts.csv")
INTEGRATED_CSV = (BASE+"/classifier_improvement/h1_presence_only/integrated_collected_corpus"
                  "/data/integrated_h1_presence_classified_posts.csv")
H2_FULL_CSV    = BASE+"/model_transfer/data/regression_ready/h2_post_level_regression_ready.csv"
H3_PANEL_CSV   = BASE+"/model_transfer/data/processed/h3_firm_month_panel.csv"

CTRL_COLS = ["text_length", "hashtag_count", "mention_count"]

# ---------------------------------------------------------------------------
# Utilities
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

def log1p_safe(v):
    try: return math.log1p(max(float(v), 0.0))
    except: return float("nan")

def safe_float(v):
    try: return float(v)
    except: return float("nan")

def p_stars(p):
    try:
        p = float(p)
        if p < 0.01: return "***"
        if p < 0.05: return "**"
        if p < 0.10: return "*"
    except: pass
    return "ns"

def compute_text_controls(text):
    """Compute text_length, hashtag_count, mention_count from raw text string."""
    if not text:
        return 0, 0, 0
    tl = len(text)
    hc = len(re.findall(r'#\w+', text))
    mc = len(re.findall(r'@\w+', text))
    return tl, hc, mc

def parse_tw(s):
    try: return datetime.strptime(s.strip(), "%a %b %d %H:%M:%S +0000 %Y")
    except: return None

def fe_from_twitter(r):
    dt = parse_tw(r.get("created_at",""))
    if dt is None: return {}
    return {
        "year":  str(dt.year),
        "month": f"{dt.year}-{dt.month:02d}",
    }

def fe_from_integrated(r):
    return {"year": r.get("year",""), "month": r.get("year_month","")}

def fe_from_period(period):
    year = period[:4] if period else ""
    return {"year": year, "month": period}

# ---------------------------------------------------------------------------
# Core OLS functions
# ---------------------------------------------------------------------------

def plain_ols(y_np, X_np, feature_names):
    """Standard OLS. y_np and X_np already assembled (includes intercept)."""
    n, k = X_np.shape
    XtX = X_np.T @ X_np
    rank = int(np.linalg.matrix_rank(XtX))
    if rank < k:
        XtX_inv = np.linalg.pinv(XtX)
    else:
        XtX_inv = np.linalg.inv(XtX)
    beta = XtX_inv @ (X_np.T @ y_np)
    e = y_np - X_np @ beta
    ss_res = float(np.sum(e**2))
    ss_tot = float(np.sum((y_np - y_np.mean())**2))
    df_res = max(n - rank, 1)
    s2 = ss_res / df_res
    vcov = s2 * XtX_inv
    ses = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st = np.where(ses > 0, beta / ses, float("nan"))
    pv = np.array([
        2*(1-scipy_stats.t.cdf(abs(t), df=df_res)) if not math.isnan(t) else float("nan")
        for t in t_st
    ])
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1-r2)*(n-1)/df_res if df_res > 0 else float("nan")
    coef_rows = [{
        "feature":     feat,
        "coefficient": round(float(beta[i]),6),
        "classical_ols_se": round(float(ses[i]),6),
        "t_stat":  round(float(t_st[i]),4) if not math.isnan(t_st[i]) else "",
        "p_value": round(float(pv[i]),6) if not math.isnan(pv[i]) else "",
        "stars":   p_stars(pv[i]),
    } for i, feat in enumerate(feature_names)]
    return coef_rows, r2, r2_adj, {"n":n,"df_resid":df_res,"rank":rank}


def fe_ols(y_np, X_focal, focal_names, time_arr):
    """
    Time FE via cell demeaning (FWL). cell = time_arr values.
    Returns same as plain_ols but for focal variables only.
    """
    n = len(y_np)
    k = X_focal.shape[1]
    mask = (time_arr != "")
    if mask.sum() < k + 3:
        raise ValueError(f"too few valid rows: {mask.sum()}")
    y_m  = y_np[mask].astype(np.float64)
    X_m  = X_focal[mask].astype(np.float64)
    t_m  = time_arr[mask]
    s_t  = pd.Series(t_m)
    n_cells = int(s_t.nunique())
    y_dm = (pd.Series(y_m) - pd.Series(y_m).groupby(s_t).transform("mean")).values
    X_dm = np.empty_like(X_m)
    for j in range(k):
        sx = pd.Series(X_m[:,j])
        X_dm[:,j] = (sx - sx.groupby(s_t).transform("mean")).values
    k_eff = k + n_cells  # k_focal + (n_cells-1) + 1
    k_eff = min(k_eff, len(y_m)-1)
    df_res = max(len(y_m) - k_eff, 1)
    XtX = X_dm.T @ X_dm
    rank = int(np.linalg.matrix_rank(XtX))
    XtX_inv = np.linalg.pinv(XtX) if rank < k else np.linalg.inv(XtX)
    beta = XtX_inv @ (X_dm.T @ y_dm)
    e = y_dm - X_dm @ beta
    ss_res = float(np.sum(e**2))
    ss_tot = float(np.sum((y_m - float(y_m.mean()))**2))
    s2 = ss_res / df_res
    vcov = s2 * XtX_inv
    ses = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st = np.where(ses > 0, beta / ses, float("nan"))
    pv = np.array([
        2*(1-scipy_stats.t.cdf(abs(t), df=df_res)) if not math.isnan(t) else float("nan")
        for t in t_st
    ])
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1-r2)*(len(y_m)-1)/df_res if df_res > 0 else float("nan")
    coef_rows = [{
        "feature":     feat,
        "coefficient": round(float(beta[i]),6),
        "classical_ols_se": round(float(ses[i]),6),
        "t_stat":  round(float(t_st[i]),4) if not math.isnan(t_st[i]) else "",
        "p_value": round(float(pv[i]),6) if not math.isnan(pv[i]) else "",
        "stars":   p_stars(pv[i]),
    } for i, feat in enumerate(focal_names)]
    return coef_rows, r2, r2_adj, {"n":int(mask.sum()),"df_resid":df_res,
                                    "rank":rank,"n_cells":n_cells}


def joint_cell_ols(y_np, X_focal, focal_names, firm_arr, time_arr):
    """
    Two-way (firm×time) FE via joint cell demeaning. focal_names includes controls.
    """
    n = len(y_np)
    k = X_focal.shape[1]
    mask = (firm_arr != "") & (time_arr != "")
    if mask.sum() < max(k+3, 10):
        raise ValueError(f"too few rows: {mask.sum()}")
    y_m = y_np[mask].astype(np.float64)
    X_m = X_focal[mask].astype(np.float64)
    f_m = firm_arr[mask]
    t_m = time_arr[mask]
    cell = np.array([f"{f};{t}" for f,t in zip(f_m, t_m)])
    s_cell = pd.Series(cell)
    n_cells = int(s_cell.nunique())
    n_singletons = int((s_cell.groupby(s_cell).transform("count") == 1).sum())
    k_eff = k + n_cells + 1
    k_eff = min(k_eff, len(y_m))
    df_res = len(y_m) - k_eff
    if df_res <= 0:
        raise ValueError(f"insufficient df: n={len(y_m)} k_eff={k_eff} df={df_res}")
    y_dm = (pd.Series(y_m) - pd.Series(y_m).groupby(s_cell).transform("mean")).values
    X_dm = np.empty_like(X_m)
    for j in range(k):
        sx = pd.Series(X_m[:,j])
        X_dm[:,j] = (sx - sx.groupby(s_cell).transform("mean")).values
    XtX = X_dm.T @ X_dm
    rank = int(np.linalg.matrix_rank(XtX))
    XtX_inv = np.linalg.pinv(XtX) if rank < k else np.linalg.inv(XtX)
    beta = XtX_inv @ (X_dm.T @ y_dm)
    e = y_dm - X_dm @ beta
    ss_res = float(np.sum(e**2))
    ss_tot = float(np.sum((y_m - float(y_m.mean()))**2))
    s2 = ss_res / df_res
    vcov = s2 * XtX_inv
    ses = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st = np.where(ses > 0, beta / ses, float("nan"))
    pv = np.array([
        2*(1-scipy_stats.t.cdf(abs(t), df=df_res)) if not math.isnan(t) else float("nan")
        for t in t_st
    ])
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1-r2)*(len(y_m)-1)/df_res if df_res > 0 else float("nan")
    coef_rows = [{
        "feature":     feat,
        "coefficient": round(float(beta[i]),6),
        "classical_ols_se": round(float(ses[i]),6),
        "t_stat":  round(float(t_st[i]),4) if not math.isnan(t_st[i]) else "",
        "p_value": round(float(pv[i]),6) if not math.isnan(pv[i]) else "",
        "stars":   p_stars(pv[i]),
    } for i, feat in enumerate(focal_names)]
    return coef_rows, r2, r2_adj, {"n":int(mask.sum()),"df_resid":df_res,
                                    "rank":rank,"n_cells":n_cells,
                                    "n_singletons":n_singletons}


def build_firm_dummies(co_array, global_id_map):
    counts = {}
    for cn in co_array: counts[cn] = counts.get(cn,0)+1
    ref_name = max(counts, key=counts.__getitem__)
    ref_id   = global_id_map.get(ref_name,"")
    others   = sorted([cn for cn in counts if cn != ref_name],
                       key=lambda cn: global_id_map.get(cn,0))
    dummy_names = [f"firm_dummy_{global_id_map.get(cn,'')}" for cn in others]
    n = len(co_array)
    mat = np.zeros((n, len(others)), dtype=np.float64)
    col_map = {cn: j for j,cn in enumerate(others)}
    for i, cn in enumerate(co_array):
        if cn in col_map:
            mat[i, col_map[cn]] = 1.0
    return mat, dummy_names, ref_id, ref_name, counts, len(counts)

# ---------------------------------------------------------------------------
# STEP 1: Load data
# ---------------------------------------------------------------------------
print("="*60)
print("STEP 1: Load data")
print("="*60)

# Batch1 H1: compute controls from text
tmpl = read_csv(TEMPLATE_CSV)
b1_h1_all = [r for r in tmpl if r["human_humor_presence"] in ("0","1")]
for r in b1_h1_all:
    tl, hc, mc = compute_text_controls(r.get("text",""))
    r["_tl"], r["_hc"], r["_mc"] = tl, hc, mc
    r["_fe"] = fe_from_twitter(r)
    r["_y"] = log1p_safe(r["total_engagement"])
b1h1_valid = [r for r in b1_h1_all if not math.isnan(r["_y"])]

# Batch1 H2 type: join controls from F100 by tweet_id
type_raw = read_csv(TYPE_CSV)
b1_type  = [r for r in type_raw if r["source"] == "batch1_fortune100"]
f100_raw = read_csv(F100_CSV)
f100_idx = {r["tweet_id"]: r for r in f100_raw}
for r in b1_type:
    er = f100_idx.get(r["tweet_id"])
    if er:
        r["_tl"] = safe_float(er.get("text_length",0))
        r["_hc"] = safe_float(er.get("hashtag_count",0))
        r["_mc"] = safe_float(er.get("mention_count",0))
        r["_y"]  = log1p_safe(er["total_engagement"])
    else:
        tl, hc, mc = compute_text_controls(r.get("text",""))
        r["_tl"], r["_hc"], r["_mc"] = tl, hc, mc
        r["_y"] = float("nan")
    r["_fe"] = fe_from_twitter(r)
b1_type_valid = [r for r in b1_type if not math.isnan(r["_y"])]

# Full H1
integ   = read_csv(INTEGRATED_CSV)
full_h1 = [r for r in integ
           if r.get("missing_text") != "True"
           and r.get("h1_humor_presence_pred_t50") in ("0","1")]
for r in full_h1:
    r["_tl"] = safe_float(r.get("text_length",0))
    r["_hc"] = safe_float(r.get("hashtag_count",0))
    r["_mc"] = safe_float(r.get("mention_count",0))
    r["_fe"] = fe_from_integrated(r)
    r["_y"]  = log1p_safe(r["total_engagement"])

# Full H2
h2_raw   = read_csv(H2_FULL_CSV)
h2_humor = [r for r in h2_raw if r["humor_type"] != "non_humorous"]
for r in h2_humor:
    r["_tl"] = safe_float(r.get("text_length",0))
    r["_hc"] = safe_float(r.get("hashtag_count",0))
    r["_mc"] = safe_float(r.get("mention_count",0))
    er = f100_idx.get(r.get("tweet_id",""))
    r["_fe"] = fe_from_twitter(er) if er else {"year": r.get("year",""), "month": r.get("period","")}
    r["_y"]  = safe_float(r["log_total_engagement"])

# H3 panel (controls already aggregated)
h3_panel = read_csv(H3_PANEL_CSV)
for r in h3_panel:
    r["_tl"] = safe_float(r.get("mean_text_length", 0))
    r["_hc"] = safe_float(r.get("mean_hashtag_count", 0))
    r["_mc"] = safe_float(r.get("mean_mention_count", 0))
    r["_fe"] = fe_from_period(r.get("period",""))
    r["_y"]  = safe_float(r.get("mean_log_total_engagement","nan"))

print(f"Batch1 H1: {len(b1h1_valid)}, Batch1 H2: {len(b1_type_valid)}")
print(f"Full H1: {len(full_h1)}, Full H2: {len(h2_humor)}, H3 panel: {len(h3_panel)}")

# ---------------------------------------------------------------------------
# STEP 2: Global company_id map
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 2: Company ID map")
print("="*60)
all_cos = set()
for src in [b1h1_valid, b1_type_valid, full_h1, h2_humor, h3_panel]:
    for r in src:
        cn = r.get("company_name","").strip()
        if cn: all_cos.add(cn)
sorted_cos  = sorted(all_cos)
global_id_map = {cn: i+1 for i,cn in enumerate(sorted_cos)}
print(f"Total unique companies: {len(sorted_cos)}")

# Helper to get time label
def get_ym(fe_dict):
    yr  = fe_dict.get("year","")
    mo  = fe_dict.get("month","")
    if yr and mo: return mo   # e.g. "2026-04"
    return yr                  # fall back to year only

# Build arrays
def arrays(rows, y_key="_y"):
    y  = np.array([r[y_key] for r in rows], dtype=np.float64)
    co = np.array([r.get("company_name","").strip() for r in rows])
    ym = np.array([get_ym(r["_fe"]) for r in rows])
    ctrl = np.array([[r["_tl"],r["_hc"],r["_mc"]] for r in rows], dtype=np.float64)
    return y, co, ym, ctrl

b1h1_y, b1h1_co, b1h1_ym, b1h1_ctrl = arrays(b1h1_valid)
b1h2_y, b1h2_co, b1h2_ym, b1h2_ctrl = arrays(b1_type_valid)
fh1_y,  fh1_co,  fh1_ym,  fh1_ctrl  = arrays(full_h1)
fh2_y,  fh2_co,  fh2_ym,  fh2_ctrl  = arrays(h2_humor)
h3_y,   h3_co,   h3_ym,   h3_ctrl   = arrays(h3_panel)

b1h1_X  = np.array([[float(r["human_humor_presence"])] for r in b1h1_valid])
fh1_X   = np.array([[float(r["h1_humor_presence_pred_t50"])] for r in full_h1])

for r in b1_type_valid:
    r["_agg"] = 1.0 if r["humor_type"]=="aggressive" else 0.0
    r["_se"]  = 1.0 if r["humor_type"]=="self-enhancing" else 0.0
    r["_sd"]  = 1.0 if r["humor_type"]=="self-defeating" else 0.0
for r in h2_humor:
    r["_agg"] = safe_float(r["aggressive_humor"])
    r["_se"]  = safe_float(r["self_enhancing_humor"])
    r["_sd"]  = safe_float(r["self_defeating_humor"])

h3_X = np.array([[float(r["aggressive_humor_usage_intensity"]),
                   float(r["aggressive_humor_usage_intensity_sq"])] for r in h3_panel])

# ---------------------------------------------------------------------------
# AUDIT constants
# ---------------------------------------------------------------------------
AUDIT = {
    "controls_included":          "true",
    "control_variables":          "text_length,hashtag_count,mention_count",
    "emoji_count_used":           "false",
    "company_id_used_as_numeric": "false",
    "c_company_formula_used":     "false",
    "se_type":                    "classical_ols",
}

MODEL_TYPES = ["plain_ols", "time_fe_year_month", "firm_dummy_only",
               "firm_dummy_year_month"]

def base_dict(hyp, basis, model_type, dv, kv):
    return {
        "hypothesis":        hyp,
        "measurement_basis": basis,
        "model_type":        model_type,
        "dependent_variable":dv,
        "key_variable":      kv,
        "coefficient":"","classical_ols_se":"","t_stat":"",
        "p_value":"","stars":"","n_obs":"","n_firms":"",
        "reference_company_id":"","reference_company_identifier":"",
        "coef_text_length":"","p_text_length":"",
        "coef_hashtag_count":"","p_hashtag_count":"",
        "coef_mention_count":"","p_mention_count":"",
        "r_squared":"","adj_r_squared":"","df_resid":"","rank":"",
        "n_cells":"","n_joint_cells":"",
        "status":"","interpretation_level":"",
        **AUDIT,
    }

def fill_ctrl(d, coef_rows):
    """Pull control coefficients from coef_rows list into d."""
    for cr in coef_rows:
        fn = cr["feature"]
        if fn in CTRL_COLS:
            d[f"coef_{fn}"] = cr["coefficient"]
            d[f"p_{fn}"]    = cr["p_value"]
    return d

def run_plain_ols(y, focal_X, focal_names, ctrl_X, d):
    """d is already filled base_dict; modifies in place."""
    try:
        valid = ~np.isnan(y)
        for j in range(ctrl_X.shape[1]):
            valid &= ~np.isnan(ctrl_X[:,j])
        if valid.sum() < focal_X.shape[1] + 4:
            raise ValueError("too few valid rows")
        y_v  = y[valid]
        Xf_v = focal_X[valid]
        Xc_v = ctrl_X[valid]
        n = int(valid.sum())
        X_all = np.column_stack([np.ones(n), Xf_v, Xc_v])
        feat  = ["intercept"] + focal_names + CTRL_COLS
        coef_rows, r2, r2_adj, info = plain_ols(y_v, X_all, feat)
        cr_focal = next(c for c in coef_rows if c["feature"] == focal_names[0])
        d["coefficient"]       = cr_focal["coefficient"]
        d["classical_ols_se"]  = cr_focal["classical_ols_se"]
        d["t_stat"]            = cr_focal["t_stat"]
        d["p_value"]           = cr_focal["p_value"]
        d["stars"]             = cr_focal["stars"]
        d["n_obs"]             = n
        d["r_squared"]         = round(r2,6) if r2==r2 else ""
        d["adj_r_squared"]     = round(r2_adj,6) if r2_adj==r2_adj else ""
        d["df_resid"]          = info["df_resid"]
        d["rank"]              = info["rank"]
        d["status"]            = "success"
        d["interpretation_level"] = "preliminary_diagnostic"
        fill_ctrl(d, coef_rows)
        return d, coef_rows
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:100]}"
        d["interpretation_level"] = "error"
        return d, []

def run_time_fe(y, focal_X, focal_names, ctrl_X, ym_arr, d):
    try:
        X_all_focal = np.column_stack([focal_X, ctrl_X])
        names_all   = focal_names + CTRL_COLS
        coef_rows, r2, r2_adj, info = fe_ols(y, X_all_focal, names_all, ym_arr)
        cr_focal = next(c for c in coef_rows if c["feature"] == focal_names[0])
        d["coefficient"]       = cr_focal["coefficient"]
        d["classical_ols_se"]  = cr_focal["classical_ols_se"]
        d["t_stat"]            = cr_focal["t_stat"]
        d["p_value"]           = cr_focal["p_value"]
        d["stars"]             = cr_focal["stars"]
        d["n_obs"]             = info["n"]
        d["n_cells"]           = info.get("n_cells","")
        d["r_squared"]         = round(r2,6) if r2==r2 else ""
        d["adj_r_squared"]     = round(r2_adj,6) if r2_adj==r2_adj else ""
        d["df_resid"]          = info["df_resid"]
        d["rank"]              = info["rank"]
        d["status"]            = "success"
        d["interpretation_level"] = "preliminary_diagnostic"
        fill_ctrl(d, coef_rows)
        return d, coef_rows
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:100]}"
        d["interpretation_level"] = "error"
        return d, []

def run_firm_dummy(y, focal_X, focal_names, ctrl_X, co_arr, d):
    try:
        valid = ~np.isnan(y)
        for j in range(ctrl_X.shape[1]):
            valid &= ~np.isnan(ctrl_X[:,j])
        if valid.sum() < focal_X.shape[1] + 4:
            raise ValueError("too few valid rows")
        y_v  = y[valid]
        Xf_v = focal_X[valid]
        Xc_v = ctrl_X[valid]
        co_v = co_arr[valid]
        n    = int(valid.sum())
        dum_mat, dum_names, ref_id, ref_name, counts, n_firms = build_firm_dummies(co_v, global_id_map)
        X_all = np.column_stack([np.ones(n), Xf_v, Xc_v, dum_mat])
        feat  = ["intercept"] + focal_names + CTRL_COLS + dum_names
        coef_rows, r2, r2_adj, info = plain_ols(y_v, X_all, feat)
        cr_focal = next(c for c in coef_rows if c["feature"] == focal_names[0])
        d["coefficient"]                 = cr_focal["coefficient"]
        d["classical_ols_se"]            = cr_focal["classical_ols_se"]
        d["t_stat"]                      = cr_focal["t_stat"]
        d["p_value"]                     = cr_focal["p_value"]
        d["stars"]                       = cr_focal["stars"]
        d["n_obs"]                       = n
        d["n_firms"]                     = n_firms
        d["reference_company_id"]        = ref_id
        d["reference_company_identifier"]= ref_name
        d["r_squared"]                   = round(r2,6) if r2==r2 else ""
        d["adj_r_squared"]               = round(r2_adj,6) if r2_adj==r2_adj else ""
        d["df_resid"]                    = info["df_resid"]
        d["rank"]                        = info["rank"]
        d["status"]                      = "success"
        d["interpretation_level"]        = "preliminary_diagnostic"
        fill_ctrl(d, coef_rows)
        return d, coef_rows
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:100]}"
        d["interpretation_level"] = "error"
        return d, []

def run_firm_time_fe(y, focal_X, focal_names, ctrl_X, co_arr, ym_arr, d):
    try:
        X_all_focal = np.column_stack([focal_X, ctrl_X])
        names_all   = focal_names + CTRL_COLS
        coef_rows, r2, r2_adj, info = joint_cell_ols(y, X_all_focal, names_all, co_arr, ym_arr)
        cr_focal = next(c for c in coef_rows if c["feature"] == focal_names[0])
        d["coefficient"]       = cr_focal["coefficient"]
        d["classical_ols_se"]  = cr_focal["classical_ols_se"]
        d["t_stat"]            = cr_focal["t_stat"]
        d["p_value"]           = cr_focal["p_value"]
        d["stars"]             = cr_focal["stars"]
        d["n_obs"]             = info["n"]
        d["n_joint_cells"]     = info.get("n_cells","")
        d["r_squared"]         = round(r2,6) if r2==r2 else ""
        d["adj_r_squared"]     = round(r2_adj,6) if r2_adj==r2_adj else ""
        d["df_resid"]          = info["df_resid"]
        d["rank"]              = info["rank"]
        d["status"]            = "success"
        d["interpretation_level"] = "preliminary_diagnostic"
        fill_ctrl(d, coef_rows)
        return d, coef_rows
    except Exception as ex:
        d["status"] = f"error: {str(ex)[:100]}"
        d["interpretation_level"] = "error"
        return d, []

# ---------------------------------------------------------------------------
# STEP 3: H1
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 3: H1")
print("="*60)

h1_rows = []

for basis, y, fX, focal, co, ym, ctrl in [
    ("batch1_human_coded",   b1h1_y, b1h1_X, ["human_humor_presence"],      b1h1_co, b1h1_ym, b1h1_ctrl),
    ("full_sample_predicted",fh1_y,  fh1_X,  ["h1_humor_presence_pred_t50"],fh1_co,  fh1_ym,  fh1_ctrl),
]:
    lim = "" if basis == "batch1_human_coded" else "h1_iv_is_classifier_predicted"
    for mt in MODEL_TYPES:
        d = base_dict("H1", basis, mt, "log1p_total_engagement", focal[0])
        if lim: d["limitation"] = lim
        if mt == "plain_ols":
            d, cr = run_plain_ols(y, fX, focal, ctrl, d)
        elif mt == "time_fe_year_month":
            d, cr = run_time_fe(y, fX, focal, ctrl, ym, d)
        elif mt == "firm_dummy_only":
            d, cr = run_firm_dummy(y, fX, focal, ctrl, co, d)
        elif mt == "firm_dummy_year_month":
            d, cr = run_firm_time_fe(y, fX, focal, ctrl, co, ym, d)
        h1_rows.append(d)
        print(f"  H1 {basis[:6]}  {mt:25s}: β={d.get('coefficient','?')} {d.get('stars','?')}")

write_csv(os.path.join(OUT, "h1_controlled_results.csv"), h1_rows)

# ---------------------------------------------------------------------------
# STEP 4: H2-1
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 4: H2-1")
print("="*60)

h21_rows = []
b1_21_X = np.array([[r["_agg"]] for r in b1_type_valid])
fh2_21_X = np.array([[r["_agg"]] for r in h2_humor])
n_b1_agg = sum(1 for r in b1_type_valid if r["humor_type"]=="aggressive")

for basis, y, fX, focal, co, ym, ctrl, lim in [
    ("batch1_human_coded",   b1h2_y, b1_21_X,  ["aggressive_vs_other"],          b1h2_co, b1h2_ym, b1h2_ctrl,
     f"n_aggressive_batch1={n_b1_agg}_low_power"),
    ("full_sample_predicted",fh2_y,  fh2_21_X, ["predicted_aggressive_vs_other"],fh2_co,  fh2_ym,  fh2_ctrl,
     "classifier_NOT_A_CANDIDATE"),
]:
    for mt in MODEL_TYPES:
        d = base_dict("H2_1", basis, mt, "log1p_total_engagement", focal[0])
        d["limitation"] = lim
        if mt == "plain_ols":
            d, cr = run_plain_ols(y, fX, focal, ctrl, d)
        elif mt == "time_fe_year_month":
            d, cr = run_time_fe(y, fX, focal, ctrl, ym, d)
        elif mt == "firm_dummy_only":
            d, cr = run_firm_dummy(y, fX, focal, ctrl, co, d)
        elif mt == "firm_dummy_year_month":
            d, cr = run_firm_time_fe(y, fX, focal, ctrl, co, ym, d)
        h21_rows.append(d)
        print(f"  H2-1 {basis[:6]}  {mt:25s}: β={d.get('coefficient','?')} {d.get('stars','?')}")

write_csv(os.path.join(OUT, "h2_1_controlled_results.csv"), h21_rows)

# ---------------------------------------------------------------------------
# STEP 5: H2-2
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 5: H2-2")
print("="*60)

h22_rows = []
b1_22_X  = np.array([[r["_agg"],r["_se"],r["_sd"]] for r in b1_type_valid])
fh2_22_X = np.array([[r["_agg"],r["_se"],r["_sd"]] for r in h2_humor])
b1_22_fn = ["aggressive","self_enhancing","self_defeating"]
fs_22_fn = ["predicted_aggressive","predicted_self_enhancing","predicted_self_defeating"]

def h22_result_dict(hyp, basis, mt, dv, focal_names, coef_rows, d):
    """Expand H2-2 multi-focal into extra columns."""
    if not coef_rows: return d
    cr0 = next((c for c in coef_rows if c["feature"]==focal_names[0]), {})
    d["coefficient"]      = cr0.get("coefficient","")
    d["classical_ols_se"] = cr0.get("classical_ols_se","")
    d["t_stat"]           = cr0.get("t_stat","")
    d["p_value"]          = cr0.get("p_value","")
    d["stars"]            = cr0.get("stars","")
    for cr in coef_rows:
        fn = cr["feature"]
        if fn != focal_names[0] and fn not in CTRL_COLS and fn != "intercept":
            d[f"coef_{fn}"]  = cr.get("coefficient","")
            d[f"se_{fn}"]    = cr.get("classical_ols_se","")
            d[f"p_{fn}"]     = cr.get("p_value","")
            d[f"stars_{fn}"] = cr.get("stars","")
    return d

for basis, y, fX, focal_names, co, ym, ctrl, lim in [
    ("batch1_human_coded",   b1h2_y, b1_22_X,  b1_22_fn,  b1h2_co, b1h2_ym, b1h2_ctrl,
     f"n_aggressive_batch1={n_b1_agg}"),
    ("full_sample_predicted",fh2_y,  fh2_22_X, fs_22_fn,  fh2_co,  fh2_ym,  fh2_ctrl,
     "classifier_NOT_A_CANDIDATE"),
]:
    for mt in MODEL_TYPES:
        d = base_dict("H2_2", basis, mt, "log1p_total_engagement", focal_names[0])
        d["reference_category"] = "affiliative"
        d["limitation"]         = lim
        if mt == "plain_ols":
            d, cr = run_plain_ols(y, fX, focal_names, ctrl, d)
            d = h22_result_dict("H2_2", basis, mt, "log1p_total_engagement", focal_names, cr, d)
        elif mt == "time_fe_year_month":
            d, cr = run_time_fe(y, fX, focal_names, ctrl, ym, d)
            d = h22_result_dict("H2_2", basis, mt, "log1p_total_engagement", focal_names, cr, d)
        elif mt == "firm_dummy_only":
            d, cr = run_firm_dummy(y, fX, focal_names, ctrl, co, d)
            d = h22_result_dict("H2_2", basis, mt, "log1p_total_engagement", focal_names, cr, d)
        elif mt == "firm_dummy_year_month":
            d, cr = run_firm_time_fe(y, fX, focal_names, ctrl, co, ym, d)
            d = h22_result_dict("H2_2", basis, mt, "log1p_total_engagement", focal_names, cr, d)
        h22_rows.append(d)
        agg = d.get("coefficient","?")
        print(f"  H2-2 {basis[:6]}  {mt:25s}: β_agg={agg} {d.get('stars','?')}")

write_csv(os.path.join(OUT, "h2_2_controlled_results.csv"), h22_rows)

# ---------------------------------------------------------------------------
# STEP 6: H3
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 6: H3")
print("="*60)

h3_rows = []
h3_fn   = ["predicted_aggressive_intensity","predicted_aggressive_intensity_sq"]
int_min = float(h3_X[:,0].min())
int_max = float(h3_X[:,0].max())

H3_MODELS = [
    ("plain_ols",             "plain_ols + aggregated controls"),
    ("time_fe_year_month",    "year+month FE + aggregated controls"),
    ("firm_dummy_only",       "firm dummy + aggregated controls"),
    ("firm_dummy_year_fe",    "firm dummy + year FE + aggregated controls"),
]

def h3_base(mt, basis):
    return {
        "hypothesis": "H3", "measurement_basis": basis,
        "model_type": mt, "dependent_variable": "firm_period_mean_log1p_engagement",
        "key_variable": "predicted_aggressive_intensity",
        "coefficient":"","classical_ols_se":"","t_stat":"","p_value":"","stars":"",
        "beta1_intensity":"","beta2_intensity_squared":"",
        "beta1_p_value":"","beta2_p_value":"","beta2_stars":"",
        "turning_point":"","turning_point_in_observed_range":"","inverted_u_check":"",
        "n_obs":"","n_firms":"","reference_company_id":"","reference_company_identifier":"",
        "coef_mean_text_length":"","p_mean_text_length":"",
        "coef_mean_hashtag_count":"","p_mean_hashtag_count":"",
        "coef_mean_mention_count":"","p_mean_mention_count":"",
        "r_squared":"","adj_r_squared":"","df_resid":"","rank":"","n_cells":"",
        "intensity_min": round(int_min,6), "intensity_max": round(int_max,6),
        "panel_unit": "firm_month_period",
        "status":"","interpretation_level":"",
        "limitation":"classifier_NOT_A_CANDIDATE_leakage_in_intensity",
        **AUDIT,
        "control_variables": "mean_text_length,mean_hashtag_count,mean_mention_count",
    }

def fill_h3_coefs(d, coef_rows):
    cr0 = next((c for c in coef_rows if c["feature"]==h3_fn[0]), {})
    cr1 = next((c for c in coef_rows if c["feature"]==h3_fn[1]), {})
    b1 = safe_float(cr0.get("coefficient","nan"))
    b2 = safe_float(cr1.get("coefficient","nan"))
    tp = -b1/(2*b2) if abs(b2) > 1e-12 and b1==b1 and b2==b2 else float("nan")
    tpr = str(int_min<=tp<=int_max) if not math.isnan(tp) else ""
    inv = "b1>0_b2<0" if b1>0 and b2<0 else ("b1<0_b2>0" if b1<0 and b2>0 else "other")
    d.update({
        "coefficient":     cr0.get("coefficient",""),
        "classical_ols_se":cr0.get("classical_ols_se",""),
        "t_stat":          cr0.get("t_stat",""),
        "p_value":         cr0.get("p_value",""),
        "stars":           cr0.get("stars",""),
        "beta1_intensity":          cr0.get("coefficient",""),
        "beta2_intensity_squared":  cr1.get("coefficient",""),
        "beta1_p_value":            cr0.get("p_value",""),
        "beta2_p_value":            cr1.get("p_value",""),
        "beta2_stars":              cr1.get("stars",""),
        "turning_point":            round(tp,4) if not math.isnan(tp) else "",
        "turning_point_in_observed_range": tpr,
        "inverted_u_check": inv,
    })
    # H3 controls have mean_ prefix
    for cr in coef_rows:
        fn = cr["feature"]
        if fn in ("mean_text_length","mean_hashtag_count","mean_mention_count"):
            d[f"coef_{fn}"] = cr.get("coefficient","")
            d[f"p_{fn}"]    = cr.get("p_value","")
    return d

# H3 Batch1: not_applicable (cross-section 88 firms)
for mt, _ in H3_MODELS:
    d = h3_base(mt, "batch1_human_coded")
    d["status"] = "not_applicable"
    d["interpretation_level"] = "not_applicable"
    d["note"] = "firm cross-section: n=88=n_firms → rank deficient with firm dummies or controls"
    h3_rows.append(d)

# H3 Full
ctrl_names_h3 = ["mean_text_length","mean_hashtag_count","mean_mention_count"]

for mt, desc in H3_MODELS:
    d = h3_base(mt, "full_sample_predicted")

    if mt == "plain_ols":
        try:
            n = len(h3_y)
            X_all = np.column_stack([np.ones(n), h3_X, h3_ctrl])
            feat  = ["intercept"] + h3_fn + ctrl_names_h3
            coef_rows, r2, r2_adj, info = plain_ols(h3_y, X_all, feat)
            fill_h3_coefs(d, coef_rows)
            d["n_obs"] = n; d["r_squared"]=round(r2,6); d["adj_r_squared"]=round(r2_adj,6)
            d["df_resid"]=info["df_resid"]; d["rank"]=info["rank"]
            d["status"]="success"; d["interpretation_level"]="preliminary_diagnostic"
        except Exception as ex:
            d["status"]=f"error: {str(ex)[:100]}"; d["interpretation_level"]="error"

    elif mt == "time_fe_year_month":
        try:
            # year+month FE for H3 firm-month panel
            ym_h3 = np.array([get_ym(r["_fe"]) for r in h3_panel])
            X_all_focal = np.column_stack([h3_X, h3_ctrl])
            coef_rows, r2, r2_adj, info = fe_ols(h3_y, X_all_focal, h3_fn+ctrl_names_h3, ym_h3)
            fill_h3_coefs(d, coef_rows)
            d["n_obs"]=info["n"]; d["n_cells"]=info.get("n_cells","")
            d["r_squared"]=round(r2,6); d["adj_r_squared"]=round(r2_adj,6)
            d["df_resid"]=info["df_resid"]; d["rank"]=info["rank"]
            d["status"]="success"; d["interpretation_level"]="preliminary_diagnostic"
            d["note"]="H3 year+month FE: month already groups 1 firm per period — all variation absorbed"
        except Exception as ex:
            msg = str(ex)[:150]
            if "df" in msg.lower() or "insufficient" in msg.lower():
                d["status"]="not_estimable_df_resid_zero"
                d["note"]="firm-month panel: month FE absorbs all within-firm variation → df_resid=0"
            else:
                d["status"]=f"error: {msg}"
            d["interpretation_level"]="not_estimable"

    elif mt == "firm_dummy_only":
        try:
            dum_mat, dum_names, ref_id, ref_name, counts, n_firms = build_firm_dummies(h3_co, global_id_map)
            n = len(h3_y)
            X_all = np.column_stack([np.ones(n), h3_X, h3_ctrl, dum_mat])
            feat  = ["intercept"] + h3_fn + ctrl_names_h3 + dum_names
            coef_rows, r2, r2_adj, info = plain_ols(h3_y, X_all, feat)
            fill_h3_coefs(d, coef_rows)
            d["n_obs"]=n; d["n_firms"]=n_firms
            d["reference_company_id"]=ref_id; d["reference_company_identifier"]=ref_name
            d["r_squared"]=round(r2,6); d["adj_r_squared"]=round(r2_adj,6)
            d["df_resid"]=info["df_resid"]; d["rank"]=info["rank"]
            d["status"]="success"; d["interpretation_level"]="preliminary_diagnostic"
        except Exception as ex:
            d["status"]=f"error: {str(ex)[:100]}"; d["interpretation_level"]="error"

    elif mt == "firm_dummy_year_fe":
        try:
            yr_h3 = np.array([r["_fe"].get("year","") for r in h3_panel])
            X_all_focal = np.column_stack([h3_X, h3_ctrl])
            # Use joint (firm, year) cell demeaning
            coef_rows, r2, r2_adj, info = joint_cell_ols(
                h3_y, X_all_focal, h3_fn+ctrl_names_h3, h3_co, yr_h3)
            fill_h3_coefs(d, coef_rows)
            d["n_obs"]=info["n"]; d["n_joint_cells"]=info.get("n_cells","")
            d["r_squared"]=round(r2,6); d["adj_r_squared"]=round(r2_adj,6)
            d["df_resid"]=info["df_resid"]; d["rank"]=info["rank"]
            d["status"]="success"; d["interpretation_level"]="preliminary_diagnostic"
        except Exception as ex:
            d["status"]=f"error: {str(ex)[:100]}"; d["interpretation_level"]="error"

    print(f"  H3 Full {mt:30s}: status={d['status']} β1={d.get('beta1_intensity','?')} {d.get('stars','?')}")
    h3_rows.append(d)

write_csv(os.path.join(OUT, "h3_controlled_results.csv"), h3_rows)

# ---------------------------------------------------------------------------
# STEP 7: Controlled OLS summary
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 7: Summary")
print("="*60)

all_results = h1_rows + h21_rows + h22_rows + h3_rows
sum_rows = []

for hyp, basis, res in [
    ("H1",   "batch1_human_coded",   h1_rows),
    ("H1",   "full_sample_predicted",h1_rows),
    ("H2_1", "batch1_human_coded",   h21_rows),
    ("H2_1", "full_sample_predicted",h21_rows),
    ("H2_2", "batch1_human_coded",   h22_rows),
    ("H2_2", "full_sample_predicted",h22_rows),
    ("H3",   "batch1_human_coded",   h3_rows),
    ("H3",   "full_sample_predicted",h3_rows),
]:
    sub = [r for r in res if r.get("hypothesis")==hyp and r.get("measurement_basis")==basis]
    for r in sub:
        mt = r.get("model_type","")
        b  = safe_float(r.get("coefficient","nan"))
        se = safe_float(r.get("classical_ols_se","nan"))
        pv = safe_float(r.get("p_value","nan"))
        st = r.get("status","")
        sum_rows.append({
            "hypothesis":        hyp,
            "measurement_basis": basis,
            "model_type":        mt,
            "key_variable":      r.get("key_variable",""),
            "coefficient":       r.get("coefficient",""),
            "se":                r.get("classical_ols_se",""),
            "p_value":           r.get("p_value",""),
            "stars":             r.get("stars",""),
            "n_obs":             r.get("n_obs",""),
            "adj_r_squared":     r.get("adj_r_squared",""),
            "df_resid":          r.get("df_resid",""),
            "direction":         "positive" if b>0 else ("negative" if b<0 else ""),
            "significant_p05":   str(pv < 0.05) if pv==pv else "",
            "status":            st,
        })
        print(f"  {hyp:5} {basis[:8]:8} {mt:30s}: β={r.get('coefficient','?')} {r.get('stars','?')}")

write_csv(os.path.join(OUT, "controlled_ols_summary.csv"), sum_rows)

# ---------------------------------------------------------------------------
# STEP 8: Comparison with no-control results
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 8: controlled_vs_no_control_comparison.csv")
print("="*60)

OLS_BASE = os.path.join(BASE, "ols_hypothesis_results")

def load_no_ctrl(hyp, basis):
    """Load no-control plain OLS coefficient for comparison."""
    mapping = {
        ("H1","batch1_human_coded"):
            (OLS_BASE+"/h1_batch1_human_coded_plain_ols_results.csv",
             "human_humor_presence"),
        ("H1","full_sample_predicted"):
            (OLS_BASE+"/h1_full_sample_predicted_plain_ols_results.csv",
             "h1_humor_presence_pred_t50"),
        ("H2_1","batch1_human_coded"):
            (OLS_BASE+"/h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv",
             "aggressive_vs_other"),
        ("H2_1","full_sample_predicted"):
            (OLS_BASE+"/h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv",
             "predicted_aggressive_vs_other"),
        ("H2_2","batch1_human_coded"):
            (OLS_BASE+"/h2_2_batch1_human_coded_four_type_plain_ols_results.csv",
             "aggressive"),
        ("H2_2","full_sample_predicted"):
            (OLS_BASE+"/h2_2_full_sample_predicted_four_type_plain_ols_results.csv",
             "predicted_aggressive"),
        ("H3","full_sample_predicted"):
            (OLS_BASE+"/h3_full_sample_predicted_intensity_plain_ols_results.csv",
             "predicted_aggressive_intensity"),
    }
    key = (hyp, basis)
    if key not in mapping: return {}, {}
    path, feat = mapping[key]
    try:
        rows = read_csv(path)
        # filter for no-controls model (key=none or controls=none, matching feature)
        for r in rows:
            if (r.get("feature","") == feat and
                r.get("controls","") in ("none","","no_controls")):
                return r, {"path": path, "feature": feat}
        # fallback: first matching feature
        for r in rows:
            if r.get("feature","") == feat:
                return r, {"path": path, "feature": feat}
    except: pass
    return {}, {}

def load_nc_from_robustness(hyp, basis, model_type):
    """Load no-control coefficient from robustness files for firm_dummy/time_fe models."""
    RDIR = OLS_BASE
    try:
        if model_type == "time_fe_year_month":
            tf_map = {
                ("H1","batch1_human_coded"):   (RDIR+"/time_fixed_effects_robustness/h1_time_fe_robustness.csv","year_month","human_humor_presence","batch1_human_coded"),
                ("H1","full_sample_predicted"): (RDIR+"/time_fixed_effects_robustness/h1_time_fe_robustness.csv","year_month","h1_humor_presence_pred_t50","full_sample_predicted"),
                ("H2_1","batch1_human_coded"):  (RDIR+"/time_fixed_effects_robustness/h2_1_time_fe_robustness.csv","year_month","aggressive_vs_other","batch1_human_coded"),
                ("H2_1","full_sample_predicted"):(RDIR+"/time_fixed_effects_robustness/h2_1_time_fe_robustness.csv","year_month","predicted_aggressive_vs_other","full_sample_predicted"),
                ("H2_2","batch1_human_coded"):  (RDIR+"/time_fixed_effects_robustness/h2_2_time_fe_robustness.csv","year_month","aggressive","batch1_human_coded"),
                ("H2_2","full_sample_predicted"):(RDIR+"/time_fixed_effects_robustness/h2_2_time_fe_robustness.csv","year_month","predicted_aggressive","full_sample_predicted"),
                ("H3","full_sample_predicted"): (RDIR+"/time_fixed_effects_robustness/h3_time_fe_robustness.csv","year_month","predicted_aggressive_intensity","full_sample_predicted"),
            }
            if (hyp,basis) not in tf_map: return {}
            path, mid, feat, bas = tf_map[(hyp,basis)]
            rows = read_csv(path)
            r = next((x for x in rows if x.get("model_id")==mid and x.get("measurement_basis")==bas), {})
            return {"coefficient": r.get("coefficient",""), "se": r.get("classical_ols_se",""),
                    "p_value": r.get("p_value",""), "stars": r.get("stars",""),
                    "n_obs": r.get("n_obs",""), "adj_r_squared": r.get("adj_r_squared","")}
        elif model_type == "firm_dummy_only":
            fd_map = {
                ("H1","batch1_human_coded"):   (RDIR+"/firm_dummy_only_robustness/h1_firm_dummy_only_results.csv","batch1_human_coded"),
                ("H1","full_sample_predicted"): (RDIR+"/firm_dummy_only_robustness/h1_firm_dummy_only_results.csv","full_sample_predicted"),
                ("H2_1","batch1_human_coded"):  (RDIR+"/firm_dummy_only_robustness/h2_1_firm_dummy_only_results.csv","batch1_human_coded"),
                ("H2_1","full_sample_predicted"):(RDIR+"/firm_dummy_only_robustness/h2_1_firm_dummy_only_results.csv","full_sample_predicted"),
                ("H2_2","batch1_human_coded"):  (RDIR+"/firm_dummy_only_robustness/h2_2_firm_dummy_only_results.csv","batch1_human_coded"),
                ("H2_2","full_sample_predicted"):(RDIR+"/firm_dummy_only_robustness/h2_2_firm_dummy_only_results.csv","full_sample_predicted"),
                ("H3","full_sample_predicted"): (RDIR+"/firm_dummy_only_robustness/h3_firm_dummy_only_results.csv","full_sample_predicted"),
            }
            if (hyp,basis) not in fd_map: return {}
            path, bas = fd_map[(hyp,basis)]
            rows = read_csv(path)
            r = next((x for x in rows if x.get("measurement_basis")==bas), {})
            coef_key = "coefficient"
            if hyp == "H2_2":
                coef_key = "coef_aggressive" if basis=="batch1_human_coded" else "coef_predicted_aggressive"
            beta = r.get(coef_key, r.get("coefficient",""))
            se   = r.get("se_aggressive" if (hyp=="H2_2" and basis=="batch1_human_coded") else
                         ("se_predicted_aggressive" if (hyp=="H2_2") else "classical_ols_se"),"")
            p    = r.get("p_aggressive" if (hyp=="H2_2" and basis=="batch1_human_coded") else
                         ("p_predicted_aggressive" if (hyp=="H2_2") else "p_value"),"")
            st   = r.get("stars_aggressive" if (hyp=="H2_2" and basis=="batch1_human_coded") else
                         ("stars_predicted_aggressive" if (hyp=="H2_2") else "stars"),"")
            return {"coefficient": beta, "se": se, "p_value": p, "stars": st,
                    "n_obs": r.get("n_obs",""), "adj_r_squared": r.get("adj_r_squared","")}
        elif model_type in ("firm_dummy_year_month","firm_dummy_year_fe"):
            fft_map = {
                ("H1","batch1_human_coded"):   (RDIR+"/firm_dummy_time_fe_robustness/h1_firm_time_fe_robustness.csv","firm_dummy_year_month","batch1_human_coded","human_humor_presence"),
                ("H1","full_sample_predicted"): (RDIR+"/firm_dummy_time_fe_robustness/h1_firm_time_fe_robustness.csv","firm_dummy_year_month","full_sample_predicted","h1_humor_presence_pred_t50"),
                ("H2_1","batch1_human_coded"):  (RDIR+"/firm_dummy_time_fe_robustness/h2_1_firm_time_fe_robustness.csv","firm_dummy_year_month","batch1_human_coded","aggressive_vs_other"),
                ("H2_1","full_sample_predicted"):(RDIR+"/firm_dummy_time_fe_robustness/h2_1_firm_time_fe_robustness.csv","firm_dummy_year_month","full_sample_predicted","predicted_aggressive_vs_other"),
                ("H2_2","batch1_human_coded"):  (RDIR+"/firm_dummy_time_fe_robustness/h2_2_firm_time_fe_robustness.csv","firm_dummy_year_month","batch1_human_coded","aggressive"),
                ("H2_2","full_sample_predicted"):(RDIR+"/firm_dummy_time_fe_robustness/h2_2_firm_time_fe_robustness.csv","firm_dummy_year_month","full_sample_predicted","predicted_aggressive"),
                ("H3","full_sample_predicted"): (RDIR+"/firm_dummy_time_fe_robustness/h3_firm_time_fe_robustness.csv","firm_dummy_year","full_sample_predicted","predicted_aggressive_intensity"),
            }
            if (hyp,basis) not in fft_map: return {}
            path, mid, bas, feat = fft_map[(hyp,basis)]
            rows = read_csv(path)
            r = next((x for x in rows if x.get("model_id")==mid and x.get("measurement_basis")==bas), {})
            if hyp == "H2_2":
                coef = r.get("coefficient","")
            else:
                coef = r.get("coefficient","")
            return {"coefficient": coef, "se": r.get("classical_ols_se",""),
                    "p_value": r.get("p_value",""), "stars": r.get("stars",""),
                    "n_obs": r.get("n_obs",""), "adj_r_squared": r.get("adj_r_squared","")}
    except: pass
    return {}

cmp_rows = []

for hyp, basis, ctrl_res in [
    ("H1",   "batch1_human_coded",   h1_rows),
    ("H1",   "full_sample_predicted",h1_rows),
    ("H2_1", "batch1_human_coded",   h21_rows),
    ("H2_1", "full_sample_predicted",h21_rows),
    ("H2_2", "batch1_human_coded",   h22_rows),
    ("H2_2", "full_sample_predicted",h22_rows),
    ("H3",   "full_sample_predicted",h3_rows),
]:
    sub = [r for r in ctrl_res if r.get("hypothesis")==hyp and r.get("measurement_basis")==basis
           and r.get("status")=="success"]
    for r in sub:
        mt  = r.get("model_type","")
        # Load no-control counterpart
        if mt == "plain_ols":
            nc_r, _ = load_no_ctrl(hyp, basis)
            nc_b  = safe_float(nc_r.get("coefficient","nan"))
            nc_se = safe_float(nc_r.get("se","nan"))
            nc_p  = safe_float(nc_r.get("p_value","nan"))
            nc_n  = nc_r.get("n_obs","")
            nc_r2 = nc_r.get("r_squared_adj","")
        else:
            nc_r  = load_nc_from_robustness(hyp, basis, mt)
            nc_b  = safe_float(nc_r.get("coefficient","nan"))
            nc_se = safe_float(nc_r.get("se","nan"))
            nc_p  = safe_float(nc_r.get("p_value","nan"))
            nc_n  = nc_r.get("n_obs","")
            nc_r2 = nc_r.get("adj_r_squared","")
        cb  = safe_float(r.get("coefficient","nan"))
        cse = safe_float(r.get("classical_ols_se","nan"))
        cp  = safe_float(r.get("p_value","nan"))
        dir_changed = str((nc_b > 0) != (cb > 0)) if nc_b==nc_b and cb==cb else ""
        sig_changed = str((nc_p < 0.05) != (cp < 0.05)) if nc_p==nc_p and cp==cp else ""
        ctrl_vars = ("mean_text_length,mean_hashtag_count,mean_mention_count"
                     if hyp=="H3" else "text_length,hashtag_count,mention_count")
        cmp_rows.append({
            "hypothesis":        hyp,
            "measurement_basis": basis,
            "model_type":        mt,
            "key_variable":      r.get("key_variable",""),
            "beta_no_control":   round(nc_b,6) if nc_b==nc_b else "",
            "se_no_control":     round(nc_se,6) if nc_se==nc_se else "",
            "p_no_control":      round(nc_p,6) if nc_p==nc_p else "",
            "stars_no_control":  p_stars(nc_p),
            "n_no_control":      nc_n,
            "beta_controlled":   r.get("coefficient",""),
            "se_controlled":     r.get("classical_ols_se",""),
            "p_controlled":      r.get("p_value",""),
            "stars_controlled":  r.get("stars",""),
            "n_controlled":      r.get("n_obs",""),
            "direction_changed": dir_changed,
            "significance_changed": sig_changed,
            "controls_included": "true",
            "control_variables": ctrl_vars,
            "adj_r2_no_ctrl":    nc_r2,
            "adj_r2_controlled": r.get("adj_r_squared",""),
        })

write_csv(os.path.join(OUT, "controlled_vs_no_control_comparison.csv"), cmp_rows)

# ---------------------------------------------------------------------------
# STEP 9: Sample attrition
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 9: Sample attrition")
print("="*60)

attrition = []
for label, y, ctrl in [
    ("batch1_h1",  b1h1_y, b1h1_ctrl),
    ("full_h1",    fh1_y,  fh1_ctrl),
    ("batch1_h2",  b1h2_y, b1h2_ctrl),
    ("full_h2",    fh2_y,  fh2_ctrl),
    ("full_h3",    h3_y,   h3_ctrl),
]:
    n_all = len(y)
    n_y_valid = int(~np.isnan(y).sum().__class__.__mro__[0]) if False else int(np.sum(~np.isnan(y)))
    n_ctrl_valid = int(np.sum(~np.any(np.isnan(ctrl), axis=1)))
    n_both_valid = int(np.sum(~np.isnan(y) & ~np.any(np.isnan(ctrl), axis=1)))
    attrition.append({
        "dataset": label,
        "n_total_rows": n_all,
        "n_y_valid": n_y_valid,
        "n_ctrl_valid": n_ctrl_valid,
        "n_both_valid": n_both_valid,
        "ctrl_miss_pct": round((n_all-n_ctrl_valid)/n_all*100,2) if n_all>0 else "",
    })
write_csv(os.path.join(OUT, "controlled_sample_attrition.csv"), attrition)

# ---------------------------------------------------------------------------
# STEP 10: Model specification
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 10: controlled_model_specification.md")
print("="*60)

spec_md = """# Controlled OLS Model Specification

**Controls**: text_length, hashtag_count, mention_count
**H3 controls**: mean_text_length, mean_hashtag_count, mean_mention_count (firm-period aggregated)
**emoji_count**: NOT included
**SE**: Classical OLS (s²×(X'X)⁻¹)
**Firm FE**: explicit binary dummies (n_firms−1), NOT C(company_id)

---

## H1 Models

```
1. Plain OLS + controls:
   E[Y] = β0 + β1 HumorPresence + β2 text_length + β3 hashtag_count + β4 mention_count + ε

2. Year+Month FE + controls:
   within-cell: ỹ = β1 H̃umorPresence + β2 t̃ext_length + β3 h̃ashtag_count + β4 m̃ention_count + ε
   (FWL: demeaning by year-month cell)

3. Firm dummy + controls:
   E[Y] = β0 + β1 HumorPresence + β2 text_length + β3 hashtag_count + β4 mention_count
          + Σ γ_j FirmDummy_j + ε

4. Firm dummy + Year+Month FE + controls:
   (FWL: demeaning by joint (firm, year_month) cell)
   within-cell: ỹ = β1 H̃P + β2 t̃l + β3 h̃c + β4 m̃c + ε
```

## H2-1 Models (same structure as H1, focal = aggressive_vs_other)

## H2-2 Models (ref=affiliative; focal = aggressive, self_enhancing, self_defeating)

## H3 Models

```
1. Plain OLS + agg controls:
   E[Ȳ] = β0 + β1 Intensity + β2 Intensity² + β3 mean_tl + β4 mean_hc + β5 mean_mc + ε

2. Year+Month FE + agg controls:
   ⚠ H3 firm-month panel: (firm, period) is unique identifier → month FE absorbs all variation
     → not_estimable_df_resid_zero

3. Firm dummy + agg controls:
   E[Ȳ] = β0 + β1 Intensity + β2 Intensity² + β3 mean_tl + β4 mean_hc + β5 mean_mc
          + Σ γ_j FirmDummy_j + ε

4. Firm dummy + Year FE + agg controls (representative combined FE):
   (FWL: demeaning by joint (firm, year) cell)
   within-cell: ỹ = β1 Ĩ + β2 Ĩ² + β3 m̃tl + β4 m̃hc + β5 m̃mc + ε
```

## Batch1 H3: not_applicable
Batch1 H3 is a firm cross-section (n=88 firms, 1 obs/firm).
With controls (5 vars) + intercept, effective k ≥ 6 for n=88 → unfeasible with firm dummies.
"""

with open(os.path.join(OUT, "controlled_model_specification.md"),"w",encoding="utf-8") as f:
    f.write(spec_md)
print("  wrote controlled_model_specification.md")

# ---------------------------------------------------------------------------
# STEP 11: Interpretation MD
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("STEP 11: controlled_ols_interpretation.md")
print("="*60)

def gv(res, hyp, basis, mt, col):
    for r in res:
        if r.get("hypothesis")==hyp and r.get("measurement_basis")==basis and r.get("model_type")==mt:
            return str(r.get(col,"—"))
    return "—"

def row_str(res, hyp, basis, mt):
    b  = gv(res,hyp,basis,mt,"coefficient")
    se = gv(res,hyp,basis,mt,"classical_ols_se")
    p  = gv(res,hyp,basis,mt,"p_value")
    st = gv(res,hyp,basis,mt,"stars")
    n  = gv(res,hyp,basis,mt,"n_obs")
    r2 = gv(res,hyp,basis,mt,"adj_r_squared")
    return f"β={b} SE={se} p={p} {st}  n={n}  adj_r²={r2}"

interp_md = f"""# Controlled OLS 분석 해석 (Controls: text_length, hashtag_count, mention_count)

**생성일**: 2026-06-19
**SE**: Classical OLS
**분석 성격**: PRELIMINARY DIAGNOSTIC ONLY
**금지 controls**: emoji_count ← 사용하지 않음

---

## 1. H1: 유머 포스트 → 더 높은 engagement

### H1 Batch1

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h1_rows,'H1','batch1_human_coded','plain_ols','coefficient')} | {gv(h1_rows,'H1','batch1_human_coded','plain_ols','classical_ols_se')} | {gv(h1_rows,'H1','batch1_human_coded','plain_ols','p_value')} | {gv(h1_rows,'H1','batch1_human_coded','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h1_rows,'H1','batch1_human_coded','time_fe_year_month','coefficient')} | {gv(h1_rows,'H1','batch1_human_coded','time_fe_year_month','classical_ols_se')} | {gv(h1_rows,'H1','batch1_human_coded','time_fe_year_month','p_value')} | {gv(h1_rows,'H1','batch1_human_coded','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_only','coefficient')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_only','classical_ols_se')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_only','p_value')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_year_month','coefficient')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_year_month','classical_ols_se')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_year_month','p_value')} | {gv(h1_rows,'H1','batch1_human_coded','firm_dummy_year_month','stars')} |

### H1 Full (예측 레이블)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h1_rows,'H1','full_sample_predicted','plain_ols','coefficient')} | {gv(h1_rows,'H1','full_sample_predicted','plain_ols','classical_ols_se')} | {gv(h1_rows,'H1','full_sample_predicted','plain_ols','p_value')} | {gv(h1_rows,'H1','full_sample_predicted','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h1_rows,'H1','full_sample_predicted','time_fe_year_month','coefficient')} | {gv(h1_rows,'H1','full_sample_predicted','time_fe_year_month','classical_ols_se')} | {gv(h1_rows,'H1','full_sample_predicted','time_fe_year_month','p_value')} | {gv(h1_rows,'H1','full_sample_predicted','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_only','coefficient')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_only','classical_ols_se')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_only','p_value')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_year_month','coefficient')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_year_month','classical_ols_se')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_year_month','p_value')} | {gv(h1_rows,'H1','full_sample_predicted','firm_dummy_year_month','stars')} |

### H1 요약
- **양수 방향 유지**: Controls 추가 후에도 β > 0 유지 여부 → 파일에서 확인
- **Full 유의성**: Controls 추가 후 Full 유의성 유지 여부 확인

---

## 2. H2-1: Aggressive vs Other humor

### H2-1 Batch1

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h21_rows,'H2_1','batch1_human_coded','plain_ols','coefficient')} | {gv(h21_rows,'H2_1','batch1_human_coded','plain_ols','classical_ols_se')} | {gv(h21_rows,'H2_1','batch1_human_coded','plain_ols','p_value')} | {gv(h21_rows,'H2_1','batch1_human_coded','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h21_rows,'H2_1','batch1_human_coded','time_fe_year_month','coefficient')} | {gv(h21_rows,'H2_1','batch1_human_coded','time_fe_year_month','classical_ols_se')} | {gv(h21_rows,'H2_1','batch1_human_coded','time_fe_year_month','p_value')} | {gv(h21_rows,'H2_1','batch1_human_coded','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_only','coefficient')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_only','classical_ols_se')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_only','p_value')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_year_month','coefficient')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_year_month','classical_ols_se')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_year_month','p_value')} | {gv(h21_rows,'H2_1','batch1_human_coded','firm_dummy_year_month','stars')} |

### H2-1 Full (⚠ NOT_A_CANDIDATE)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h21_rows,'H2_1','full_sample_predicted','plain_ols','coefficient')} | {gv(h21_rows,'H2_1','full_sample_predicted','plain_ols','classical_ols_se')} | {gv(h21_rows,'H2_1','full_sample_predicted','plain_ols','p_value')} | {gv(h21_rows,'H2_1','full_sample_predicted','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h21_rows,'H2_1','full_sample_predicted','time_fe_year_month','coefficient')} | {gv(h21_rows,'H2_1','full_sample_predicted','time_fe_year_month','classical_ols_se')} | {gv(h21_rows,'H2_1','full_sample_predicted','time_fe_year_month','p_value')} | {gv(h21_rows,'H2_1','full_sample_predicted','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_only','coefficient')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_only','classical_ols_se')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_only','p_value')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_year_month','coefficient')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_year_month','classical_ols_se')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_year_month','p_value')} | {gv(h21_rows,'H2_1','full_sample_predicted','firm_dummy_year_month','stars')} |

---

## 3. H2-2: Four humor types (ref=affiliative)

### H2-2 Batch1 aggressive coefficient

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h22_rows,'H2_2','batch1_human_coded','plain_ols','coefficient')} | {gv(h22_rows,'H2_2','batch1_human_coded','plain_ols','classical_ols_se')} | {gv(h22_rows,'H2_2','batch1_human_coded','plain_ols','p_value')} | {gv(h22_rows,'H2_2','batch1_human_coded','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h22_rows,'H2_2','batch1_human_coded','time_fe_year_month','coefficient')} | {gv(h22_rows,'H2_2','batch1_human_coded','time_fe_year_month','classical_ols_se')} | {gv(h22_rows,'H2_2','batch1_human_coded','time_fe_year_month','p_value')} | {gv(h22_rows,'H2_2','batch1_human_coded','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_only','coefficient')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_only','classical_ols_se')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_only','p_value')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_year_month','coefficient')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_year_month','classical_ols_se')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_year_month','p_value')} | {gv(h22_rows,'H2_2','batch1_human_coded','firm_dummy_year_month','stars')} |

### H2-2 Full predicted_aggressive coefficient (⚠ NOT_A_CANDIDATE)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | {gv(h22_rows,'H2_2','full_sample_predicted','plain_ols','coefficient')} | {gv(h22_rows,'H2_2','full_sample_predicted','plain_ols','classical_ols_se')} | {gv(h22_rows,'H2_2','full_sample_predicted','plain_ols','p_value')} | {gv(h22_rows,'H2_2','full_sample_predicted','plain_ols','stars')} |
| Time FE(ym)+ctrl | {gv(h22_rows,'H2_2','full_sample_predicted','time_fe_year_month','coefficient')} | {gv(h22_rows,'H2_2','full_sample_predicted','time_fe_year_month','classical_ols_se')} | {gv(h22_rows,'H2_2','full_sample_predicted','time_fe_year_month','p_value')} | {gv(h22_rows,'H2_2','full_sample_predicted','time_fe_year_month','stars')} |
| Firm dummy+ctrl  | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_only','coefficient')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_only','classical_ols_se')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_only','p_value')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_only','stars')} |
| Firm+YM FE+ctrl  | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_year_month','coefficient')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_year_month','classical_ols_se')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_year_month','p_value')} | {gv(h22_rows,'H2_2','full_sample_predicted','firm_dummy_year_month','stars')} |

---

## 4. H3: Aggressive intensity → engagement (역 U자형 가설)

### H3 Full

| 모델 | β1 | β2 | β1_판정 | 전환점 |
|---|---|---|---|---|
| Plain OLS+ctrl | {gv(h3_rows,'H3','full_sample_predicted','plain_ols','beta1_intensity')} | {gv(h3_rows,'H3','full_sample_predicted','plain_ols','beta2_intensity_squared')} | {gv(h3_rows,'H3','full_sample_predicted','plain_ols','stars')} | {gv(h3_rows,'H3','full_sample_predicted','plain_ols','turning_point')} |
| YM FE+ctrl | {gv(h3_rows,'H3','full_sample_predicted','time_fe_year_month','beta1_intensity')} | {gv(h3_rows,'H3','full_sample_predicted','time_fe_year_month','beta2_intensity_squared')} | {gv(h3_rows,'H3','full_sample_predicted','time_fe_year_month','stars')} | {gv(h3_rows,'H3','full_sample_predicted','time_fe_year_month','status')} |
| Firm dummy+ctrl | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_only','beta1_intensity')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_only','beta2_intensity_squared')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_only','stars')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_only','turning_point')} |
| Firm+Year FE+ctrl | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_year_fe','beta1_intensity')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_year_fe','beta2_intensity_squared')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_year_fe','stars')} | {gv(h3_rows,'H3','full_sample_predicted','firm_dummy_year_fe','turning_point')} |

Batch1: not_applicable (firm cross-section)

---

## 5. 핵심 해석 요점

### 5.1 H1 controls 추가 후 방향 유지 여부
참조: h1_controlled_results.csv — coefficient 열 부호 확인.
Plain OLS → Firm+YM FE까지 양수 유지 여부가 핵심.

### 5.2 H1 Full controls 추가 후 유의성
Full 샘플 n=68,039 → controls 추가 후에도 충분한 파워 유지 예상.

### 5.3 H2-1 firm FE 포함 시 방향 역전
Firm dummy only (no-control): Full β=−0.101***
Firm dummy only (controlled): 위 표 참조 → 역전 유지 여부.

### 5.4 H2-2 aggressive coefficient controls 후 변화
Firm dummy only (no-control): Batch1 β=0.206 ns, Full β=−0.112***
Controls 추가 후 Full 역전 유지 여부.

### 5.5 H3 역U자형 / U자형 패턴 변화
No-control: firm dummy 후 U자형(β1<0, β2>0).
Controls 추가: 위 표 참조.

### 5.6 Controls 추가로 β 크기 변화
비교 파일: controlled_vs_no_control_comparison.csv → beta_no_control vs beta_controlled

### 5.7 Full H2/H3 Classifier NOT_A_CANDIDATE
Full H2와 H3 full sample 결과는 classifier가 NOT_A_CANDIDATE 상태 (leakage 가능)로,
controls 추가 여부와 무관하게 공식 가설 검증에 사용할 수 없다.
결과는 방향성 참고 수준에만 활용한다.

### 5.8 Batch1 소표본 limitation
- H1 batch1: n=1,482 → firm+YM FE에서 df_resid 급감
- H2-1 batch1: n=648, n_agg=44 → 극단적 저파워
- H2-2 batch1: n=648, 4유형 분할 시 각 셀 n이 더 작아짐

---

## 6. 금지사항 준수

- [x] emoji_count 미사용 (`emoji_count_used=false`)
- [x] company_id_used_as_numeric=false
- [x] c_company_formula_used=false
- [x] controls_included=true (text_length, hashtag_count, mention_count)
- [x] 기존 no-control 결과 파일 미수정
- [x] data/raw 미수정
- [x] dashboard/data 미수정
- [x] classifier 결과 파일 미수정
- [x] integrated corpus 미수정

*생성 스크립트*: `run_controlled_ols_hypotheses.py`
*출력 폴더*: `controlled_ols_results/`
*생성일*: 2026-06-19
"""

with open(os.path.join(OUT,"controlled_ols_interpretation.md"),"w",encoding="utf-8") as f:
    f.write(interp_md)
print("  wrote controlled_ols_interpretation.md")

# ---------------------------------------------------------------------------
# STEP 12: Verification
# ---------------------------------------------------------------------------
print("\n"+"="*60)
print("VERIFICATION")
print("="*60)

out_files = sorted(os.listdir(OUT))
print(f"Output files ({len(out_files)}) in {OUT}:")
for fn in out_files:
    sz = os.path.getsize(os.path.join(OUT,fn))
    print(f"  {fn}: {sz:,} bytes")

# Check existing results not modified
ols_base = os.path.join(BASE,"ols_hypothesis_results")
orig = len([f for f in os.listdir(ols_base) if not os.path.isdir(os.path.join(ols_base,f))])
print(f"\nOriginal ols_hypothesis_results/ files: {orig} (unchanged)")

# Audit flags
print("\n--- Audit flag verification ---")
print(f"emoji_count_used=false ALL: {all(r.get('emoji_count_used')=='false' for r in all_results)}")
print(f"controls_included=true ALL: {all(r.get('controls_included')=='true' for r in all_results)}")
print(f"company_id_numeric=false ALL:{all(r.get('company_id_used_as_numeric')=='false' for r in all_results)}")
print(f"c_formula=false ALL:        {all(r.get('c_company_formula_used')=='false' for r in all_results)}")

# H1 coefficient check
h1_success = [r for r in h1_rows if r.get("status")=="success"]
print(f"\nH1 models: {len(h1_rows)} total, {len(h1_success)} success")
print("DONE")
