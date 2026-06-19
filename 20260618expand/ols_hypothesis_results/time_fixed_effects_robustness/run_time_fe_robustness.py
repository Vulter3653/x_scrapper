"""
Time Fixed Effects Robustness Analysis for H1/H2/H3.

Based on 1926e25 two-basis plain OLS results.
Adds time FE combinations (1-4 of: year, month, week, day, hour).
SE: Classical OLS only.

FE implementation: joint interaction saturation (cell-level demeaning).
  - For hierarchical FEs (day ⊃ month ⊃ year) this equals the finest-level FE.
  - For non-hierarchical pairs (e.g. month × hour_of_day) this is a cross FE.
  - Single-pass demeaning via pandas groupby transform — no iterative convergence needed.
  - Degrees of freedom: k_eff = n_focal_vars + n_joint_cells + 1

Prohibited: backfill/workflow files, new predictions, new classifier training,
           data/raw, dashboard/data, .github/workflows, deleting existing files.
"""

import csv
import math
import os
import re
from datetime import datetime
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/home/user/marketingstrategy/20260618expand"
OUT = os.path.join(BASE, "ols_hypothesis_results/time_fixed_effects_robustness")
os.makedirs(OUT, exist_ok=True)

TEMPLATE_CSV = (BASE + "/classifier_improvement/data/human_labeling_template"
                "/fortune100_human_labeling_template.csv")
TYPE_CSV = (BASE + "/classifier_improvement/humor_type_leakage_filtered/data"
            "/type_training_leakage_filtered_variants.csv")
F100_CSV = (BASE + "/classifier_improvement/h1_presence_only/full_corpus_classification/data"
            "/fortune100_h1_presence_classified_posts.csv")
INTEGRATED_CSV = (BASE + "/classifier_improvement/h1_presence_only/integrated_collected_corpus"
                  "/data/integrated_h1_presence_classified_posts.csv")
H2_FULL_CSV = BASE + "/model_transfer/data/regression_ready/h2_post_level_regression_ready.csv"
H3_PANEL_CSV = BASE + "/model_transfer/data/processed/h3_firm_month_panel.csv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FE_OPTIONS = ["year", "month", "week", "day", "hour"]
ALL_FE_COMBOS = []
for k in range(1, 5):
    for combo in combinations(FE_OPTIONS, k):
        ALL_FE_COMBOS.append(combo)
# 5+10+10+5 = 30 combinations

# FE availability per dataset
AVAIL = {
    "batch1_h1":  {"year", "month", "week", "day", "hour"},
    "batch1_h2":  {"year", "month", "week", "day", "hour"},
    "batch1_h3":  set(),   # not_applicable: firm-level cross-section
    "full_h1":    {"year", "month", "week", "day", "hour"},
    "full_h2":    {"year", "month", "week", "day", "hour"},
    "full_h3":    {"year", "month"},           # period-based only
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def p_stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return "ns"

def log1p_safe(v):
    try: return math.log1p(max(float(v), 0.0))
    except: return float("nan")

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

def parse_tw(s):
    try: return datetime.strptime(s.strip(), "%a %b %d %H:%M:%S +0000 %Y")
    except: return None

def count_hashtags(t): return len(re.findall(r"#\w+", t))
def count_mentions(t): return len(re.findall(r"@\w+", t))

# ---------------------------------------------------------------------------
# FE variable generation
# ---------------------------------------------------------------------------

def fe_from_twitter(s):
    dt = parse_tw(s)
    if dt is None: return None
    ic = dt.isocalendar()
    return {
        "year":  str(dt.year),
        "month": f"{dt.year}-{dt.month:02d}",
        "week":  f"{ic.year}-W{ic.week:02d}",
        "day":   dt.strftime("%Y-%m-%d"),
        "hour":  f"{dt.strftime('%Y-%m-%d')}-{dt.hour:02d}",
    }

def fe_from_integrated(row):
    year  = row.get("year","")
    month = row.get("year_month","")
    date  = row.get("date","")
    hod   = row.get("hour_of_day","")
    parsed= row.get("parsed_datetime","")
    week  = ""
    if parsed:
        try:
            dt = datetime.fromisoformat(parsed.replace("+00:00",""))
            ic = dt.isocalendar()
            week = f"{ic.year}-W{ic.week:02d}"
        except: pass
    # hour = hour_of_day (0-23); NOT a full timestamp
    hour = f"h{hod}" if hod else ""
    return {"year": year, "month": month, "week": week, "day": date, "hour": hour}

def fe_from_period(period):
    year = period[:4] if period else ""
    return {"year": year, "month": period, "week": "", "day": "", "hour": ""}

# ---------------------------------------------------------------------------
# FWL OLS via joint-interaction cell demeaning (fast, single-pass)
# ---------------------------------------------------------------------------

def joint_fe_ols(y_np, X_np, feature_names, groups_dict, combo):
    """
    OLS with joint interaction FE.
    groups_dict: {fe_name: np.array of labels, length n}
    combo: tuple of FE names included.

    Uses pandas groupby transform for fast cell-level demeaning.
    Returns (coef_rows, r2, r2_adj, rank_info) or raises.
    """
    n = len(y_np)
    k = X_np.shape[1]

    # Build joint cell label
    if len(combo) == 1:
        cell = groups_dict[combo[0]]
    else:
        cell = np.array([
            ";".join(groups_dict[fe][i] for fe in combo)
            for i in range(n)
        ])

    # Filter rows where all FE labels are non-empty
    mask = np.ones(n, dtype=bool)
    for fe in combo:
        mask &= (groups_dict[fe] != "")
    if mask.sum() < max(10, k + 2):
        raise ValueError(f"too few rows after FE filter: {mask.sum()}")

    y   = y_np[mask].astype(np.float64)
    X   = X_np[mask].astype(np.float64)
    cell_m = cell[mask] if cell.dtype != object else cell[mask]

    # Pandas demeaning (single pass, vectorized)
    s_cell = pd.Series(cell_m)
    y_s    = pd.Series(y)
    y_dm   = (y_s - y_s.groupby(s_cell).transform("mean")).values

    X_dm = np.empty_like(X)
    for j in range(k):
        s_x = pd.Series(X[:, j])
        X_dm[:, j] = (s_x - s_x.groupby(s_cell).transform("mean")).values

    # OLS on demeaned data (no intercept — absorbed by FE)
    XtX = X_dm.T @ X_dm
    Xty = X_dm.T @ y_dm
    try:
        if np.linalg.matrix_rank(XtX) < k:
            XtX_inv = np.linalg.pinv(XtX)
        else:
            XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(XtX)

    beta  = XtX_inv @ Xty
    e     = y_dm - X_dm @ beta
    rank  = int(np.linalg.matrix_rank(XtX))

    n_cells = int(pd.Series(cell_m).nunique())
    k_eff   = k + (n_cells - 1) + 1          # focal + FE cells + intercept
    k_eff   = min(k_eff, len(y) - 1)
    df_res  = max(len(y) - k_eff, 1)

    s2   = float(np.sum(e ** 2)) / df_res
    vcov = s2 * XtX_inv
    ses  = np.sqrt(np.maximum(np.diag(vcov), 0.0))
    t_st = np.where(ses > 0, beta / ses, float("nan"))
    pv   = np.array([2 * (1 - scipy_stats.t.cdf(abs(t), df=df_res)) for t in t_st])

    ss_tot = float(np.sum((y - float(y.mean())) ** 2))
    ss_res = float(np.sum(e ** 2))
    r2     = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1.0 - (1 - r2) * (len(y) - 1) / df_res if df_res > 0 else float("nan")

    coef_rows = [{
        "feature":          feat,
        "coefficient":      round(float(beta[i]), 6),
        "classical_ols_se": round(float(ses[i]), 6),
        "t_stat":           round(float(t_st[i]), 4),
        "p_value":          round(float(pv[i]), 6),
        "stars":            p_stars(float(pv[i])),
    } for i, feat in enumerate(feature_names)]

    rinfo = {"k_eff": k_eff, "df_resid": df_res, "rank": rank,
             "n_cells": n_cells, "n_obs_after_filter": int(mask.sum())}
    return coef_rows, r2, r2_adj, rinfo

# ---------------------------------------------------------------------------
# STEP 1: Load data, compute FE variables
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1: Loading data")
print("=" * 60)

# --- Batch1 H1 ---
tmpl  = read_csv(TEMPLATE_CSV)
b1_h1 = [r for r in tmpl if r["human_humor_presence"] in ("0","1")]
for r in b1_h1:
    fe = fe_from_twitter(r.get("created_at","")) or {}
    r["_fe"] = fe
    txt = r.get("text","")
    r["_tl"] = len(txt); r["_hc"] = count_hashtags(txt); r["_mc"] = count_mentions(txt)
print(f"Batch1 H1: {len(b1_h1)} rows, "
      f"{sum(1 for r in b1_h1 if r['_fe'].get('year'))} with year FE")

# --- Batch1 H2/H3 type ---
type_raw  = read_csv(TYPE_CSV)
b1_type   = [r for r in type_raw if r["source"] == "batch1_fortune100"]
f100_raw  = read_csv(F100_CSV)
f100_idx  = {r["tweet_id"]: r for r in f100_raw}
for r in b1_type:
    fe = fe_from_twitter(r.get("created_at","")) or {}
    r["_fe"] = fe
    er = f100_idx.get(r["tweet_id"])
    r["_eng"]  = log1p_safe(er["total_engagement"]) if er else float("nan")
    r["_tl"]   = int(er.get("text_length", len(r.get("text_original","")))) if er else 0
    r["_hc"]   = int(er.get("hashtag_count", 0)) if er else 0
    r["_mc"]   = int(er.get("mention_count",  0)) if er else 0
print(f"Batch1 type: {len(b1_type)} rows")

# --- Full H1 (integrated) ---
integ_raw = read_csv(INTEGRATED_CSV)
full_h1   = [r for r in integ_raw
             if r.get("missing_text") != "True"
             and r.get("h1_humor_presence_pred_t50") in ("0","1")]
for r in full_h1:
    r["_fe"] = fe_from_integrated(r)
print(f"Full H1: {len(full_h1)} rows")

# --- Full H2 (h2_post joined with f100 for timestamps) ---
h2_raw   = read_csv(H2_FULL_CSV)
h2_humor = [r for r in h2_raw if r["humor_type"] != "non_humorous"]
for r in h2_humor:
    f100r = f100_idx.get(r["tweet_id"])
    if f100r:
        fe = fe_from_twitter(f100r.get("created_at","")) or {}
    else:
        fe = fe_from_period(r.get("period",""))
    r["_fe"]  = fe
    r["_eng"] = float(r["log_total_engagement"])
print(f"Full H2 humor: {len(h2_humor)} rows (of {len(h2_raw)} total)")

# --- Full H3 (firm-month panel) ---
h3_panel = read_csv(H3_PANEL_CSV)
for r in h3_panel:
    r["_fe"] = fe_from_period(r.get("period",""))
print(f"Full H3 firm-month panel: {len(h3_panel)} rows")

# ---------------------------------------------------------------------------
# STEP 2: Model grid
# ---------------------------------------------------------------------------
print(f"\nFE combinations: {len(ALL_FE_COMBOS)} total")
for c in ALL_FE_COMBOS:
    print(f"  [{len(c)}] {'_'.join(c)}")

grid_rows = [{
    "model_id":    "_".join(c),
    "fe_count":    len(c),
    "included_fe": ",".join(c),
    "formula":     "focal_IV + " + " + ".join(c) + " FE",
    "status":      "defined",
} for c in ALL_FE_COMBOS]
write_csv(os.path.join(OUT, "time_fe_model_grid.csv"), grid_rows)

# ---------------------------------------------------------------------------
# Helpers to build group arrays for one dataset
# ---------------------------------------------------------------------------

def build_groups(rows, combo, fe_key="_fe"):
    """Return np.array of label strings per FE in combo."""
    return {fe: np.array([r[fe_key].get(fe, "") for r in rows]) for fe in combo}

def combo_available(dkey, combo):
    avail = AVAIL.get(dkey, set())
    return all(fe in avail for fe in combo)

# ---------------------------------------------------------------------------
# Generic model runner: returns one result dict
# ---------------------------------------------------------------------------

def run_model(y_np, X_np, feature_names, rows, combo, basis, hyp,
              raw_n, dkey, extra_cols=None):
    model_id = "_".join(combo)
    base = {
        "measurement_basis": basis,
        "hypothesis":        hyp,
        "model_id":          model_id,
        "fe_count":          len(combo),
        "included_fe":       ",".join(combo),
        "key_variable":      feature_names[0],
        "coefficient": "", "classical_ols_se": "", "t_stat": "",
        "p_value": "", "stars": "", "n_obs": "",
        "r_squared": "", "adj_r_squared": "",
        "df_model": "", "df_resid": "", "rank": "",
        "status": "", "interpretation_level": "",
    }
    if extra_cols:
        base.update(extra_cols)

    if not combo_available(dkey, combo):
        base["status"] = "not_applicable" if not AVAIL.get(dkey) else "unavailable"
        base["interpretation_level"] = base["status"]
        return base

    try:
        groups = build_groups(rows, combo)
        coef_rows, r2, r2_adj, rinfo = joint_fe_ols(y_np, X_np, feature_names, groups, combo)
        cr = coef_rows[0]
        base.update({
            "coefficient":      cr["coefficient"],
            "classical_ols_se": cr["classical_ols_se"],
            "t_stat":           cr["t_stat"],
            "p_value":          cr["p_value"],
            "stars":            cr["stars"],
            "n_obs":            rinfo["n_obs_after_filter"],
            "r_squared":        round(r2, 6) if r2 == r2 else "",
            "adj_r_squared":    round(r2_adj, 6) if r2_adj == r2_adj else "",
            "df_model":         rinfo["k_eff"],
            "df_resid":         rinfo["df_resid"],
            "rank":             rinfo["rank"],
            "n_fe_cells":       rinfo["n_cells"],
            "status":           "success",
            "interpretation_level": "preliminary_diagnostic",
        })
        # Extra coefficients for H2-2 and H3
        if len(coef_rows) > 1:
            for sub in coef_rows[1:]:
                base[f"coef_{sub['feature']}"]   = sub["coefficient"]
                base[f"se_{sub['feature']}"]     = sub["classical_ols_se"]
                base[f"p_{sub['feature']}"]      = sub["p_value"]
                base[f"stars_{sub['feature']}"]  = sub["stars"]
    except Exception as ex:
        base["status"]            = f"error: {str(ex)[:100]}"
        base["interpretation_level"] = "error"

    return base

# attrition log (lightweight)
attrition_rows = []

def log_attrition(basis, hyp, model_id, raw_n, final_n, reason):
    attrition_rows.append({
        "measurement_basis": basis, "hypothesis": hyp, "model_id": model_id,
        "raw_n": raw_n, "after_time_available_n": final_n, "final_n": final_n,
        "dropped_n": raw_n - final_n, "reason": reason,
    })

# ---------------------------------------------------------------------------
# STEP 3: H1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: H1")
print("=" * 60)

h1_results = []

# Batch1 H1 arrays
b1h1_y  = np.array([log1p_safe(r["total_engagement"]) for r in b1_h1])
b1h1_X  = np.array([[float(r["human_humor_presence"])] for r in b1_h1])

# Full H1 arrays
fh1_y   = np.array([log1p_safe(r["total_engagement"]) for r in full_h1])
fh1_X   = np.array([[float(r["h1_humor_presence_pred_t50"])] for r in full_h1])

for combo in ALL_FE_COMBOS:
    # batch1
    res = run_model(b1h1_y, b1h1_X, ["human_humor_presence"], b1_h1, combo,
                    "batch1_human_coded", "H1", len(b1_h1), "batch1_h1",
                    {"dependent_variable": "log1p_total_engagement"})
    h1_results.append(res)
    # full
    res2 = run_model(fh1_y, fh1_X, ["h1_humor_presence_pred_t50"], full_h1, combo,
                     "full_sample_predicted", "H1", len(full_h1), "full_h1",
                     {"dependent_variable": "log1p_total_engagement"})
    h1_results.append(res2)
    print(f"  H1 {combo}: b1={res['stars']}({res['coefficient']}) | "
          f"full={res2['stars']}({res2['coefficient']})")

write_csv(os.path.join(OUT, "h1_time_fe_robustness.csv"), h1_results)

# ---------------------------------------------------------------------------
# STEP 4: H2-1
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 4: H2-1")
print("=" * 60)

h21_results = []

# Batch1 H2-1
for r in b1_type:
    r["_agg_vs_other"] = 1.0 if r["humor_type"] == "aggressive" else 0.0
b1h2_y   = np.array([r["_eng"] for r in b1_type])
b1h2_X21 = np.array([[r["_agg_vs_other"]] for r in b1_type])

# Full H2-1
for r in h2_humor:
    r["_agg_vs_other"] = float(r["aggressive_humor"])
fh2_y   = np.array([r["_eng"] for r in h2_humor])
fh2_X21 = np.array([[r["_agg_vs_other"]] for r in h2_humor])

for combo in ALL_FE_COMBOS:
    res = run_model(b1h2_y, b1h2_X21, ["aggressive_vs_other"], b1_type, combo,
                    "batch1_human_coded", "H2_1", len(b1_type), "batch1_h2",
                    {"dependent_variable": "log1p_total_engagement",
                     "n_aggressive_batch1": 44, "limitation": "n_agg=44_low_power"})
    h21_results.append(res)
    res2 = run_model(fh2_y, fh2_X21, ["predicted_aggressive_vs_other"], h2_humor, combo,
                     "full_sample_predicted", "H2_1", len(h2_humor), "full_h2",
                     {"dependent_variable": "log1p_total_engagement",
                      "n_predicted_aggressive": 6857,
                      "limitation": "classifier_NOT_A_CANDIDATE"})
    h21_results.append(res2)
    print(f"  H2-1 {combo}: b1={res['stars']}({res['coefficient']}) | "
          f"full={res2['stars']}({res2['coefficient']})")

write_csv(os.path.join(OUT, "h2_1_time_fe_robustness.csv"), h21_results)

# ---------------------------------------------------------------------------
# STEP 5: H2-2
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 5: H2-2")
print("=" * 60)

h22_results = []

# Batch1 H2-2
for r in b1_type:
    r["_agg"] = 1.0 if r["humor_type"] == "aggressive"     else 0.0
    r["_se"]  = 1.0 if r["humor_type"] == "self-enhancing" else 0.0
    r["_sd"]  = 1.0 if r["humor_type"] == "self-defeating" else 0.0
b1h2_X22 = np.array([[r["_agg"], r["_se"], r["_sd"]] for r in b1_type])

# Full H2-2
for r in h2_humor:
    r["_agg"] = float(r["aggressive_humor"])
    r["_se"]  = float(r["self_enhancing_humor"])
    r["_sd"]  = float(r["self_defeating_humor"])
fh2_X22 = np.array([[r["_agg"], r["_se"], r["_sd"]] for r in h2_humor])

feat_b1 = ["aggressive", "self_enhancing", "self_defeating"]
feat_fs = ["predicted_aggressive", "predicted_self_enhancing", "predicted_self_defeating"]

for combo in ALL_FE_COMBOS:
    res = run_model(b1h2_y, b1h2_X22, feat_b1, b1_type, combo,
                    "batch1_human_coded", "H2_2", len(b1_type), "batch1_h2",
                    {"dependent_variable": "log1p_total_engagement",
                     "reference_category": "affiliative"})
    h22_results.append(res)
    res2 = run_model(fh2_y, fh2_X22, feat_fs, h2_humor, combo,
                     "full_sample_predicted", "H2_2", len(h2_humor), "full_h2",
                     {"dependent_variable": "log1p_total_engagement",
                      "reference_category": "predicted_affiliative",
                      "limitation": "classifier_NOT_A_CANDIDATE"})
    h22_results.append(res2)
    print(f"  H2-2 {combo}: b1_agg={res['stars']}({res['coefficient']}) | "
          f"full_agg={res2['stars']}({res2['coefficient']})")

write_csv(os.path.join(OUT, "h2_2_time_fe_robustness.csv"), h22_results)

# ---------------------------------------------------------------------------
# STEP 6: H3
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 6: H3")
print("=" * 60)

h3_results = []

INT_COL   = "aggressive_humor_usage_intensity"
INT_SQ    = "aggressive_humor_usage_intensity_sq"
ENG_COL   = "mean_log_total_engagement"

h3_y  = np.array([float(r[ENG_COL]) for r in h3_panel])
h3_X  = np.array([[float(r[INT_COL]), float(r[INT_SQ])] for r in h3_panel])
int_min = float(h3_X[:, 0].min())
int_max = float(h3_X[:, 0].max())

for combo in ALL_FE_COMBOS:
    model_id = "_".join(combo)

    # Batch1: always not_applicable
    h3_results.append({
        "measurement_basis": "batch1_human_coded",
        "hypothesis": "H3", "model_id": model_id,
        "fe_count": len(combo), "included_fe": ",".join(combo),
        "dependent_variable": "firm_mean_log1p_engagement",
        "key_variable": "aggressive_intensity",
        "beta1_intensity": "", "beta2_intensity_squared": "",
        "beta1_p_value": "", "beta2_p_value": "",
        "coefficient": "", "classical_ols_se": "", "t_stat": "",
        "p_value": "", "stars": "", "n_obs": "",
        "r_squared": "", "adj_r_squared": "",
        "df_model": "", "df_resid": "", "rank": "",
        "turning_point": "", "turning_point_in_observed_range": "",
        "intensity_min": "", "intensity_max": "",
        "status": "not_applicable",
        "interpretation_level": "not_applicable",
        "note": "firm-level cross-section; no time dimension",
    })

    # Full sample
    if not combo_available("full_h3", combo):
        h3_results.append({
            "measurement_basis": "full_sample_predicted",
            "hypothesis": "H3", "model_id": model_id,
            "fe_count": len(combo), "included_fe": ",".join(combo),
            "dependent_variable": "firm_period_mean_log1p_engagement",
            "key_variable": "predicted_aggressive_intensity",
            "beta1_intensity": "", "beta2_intensity_squared": "",
            "beta1_p_value": "", "beta2_p_value": "",
            "coefficient": "", "classical_ols_se": "", "t_stat": "",
            "p_value": "", "stars": "", "n_obs": "",
            "r_squared": "", "adj_r_squared": "",
            "df_model": "", "df_resid": "", "rank": "",
            "turning_point": "", "turning_point_in_observed_range": "",
            "intensity_min": "", "intensity_max": "",
            "status": "unavailable",
            "interpretation_level": "unavailable",
            "note": "week/day/hour not available in firm-month panel",
        })
        print(f"  H3 {combo}: batch1=not_applicable | full=unavailable")
        continue

    try:
        groups = build_groups(h3_panel, combo)
        feat   = ["predicted_aggressive_intensity", "predicted_aggressive_intensity_sq"]
        coef_rows, r2, r2_adj, rinfo = joint_fe_ols(h3_y, h3_X, feat, groups, combo)
        b1v = coef_rows[0]["coefficient"]
        b2v = coef_rows[1]["coefficient"]
        tp  = -b1v / (2*b2v) if abs(b2v) > 1e-12 else float("nan")
        tpr = "" if math.isnan(tp) else str(int_min <= tp <= int_max)
        inv = "b1>0_b2<0" if b1v>0 and b2v<0 else ("b1<0_b2>0" if b1v<0 and b2v>0 else "other")
        h3_results.append({
            "measurement_basis": "full_sample_predicted",
            "hypothesis": "H3", "model_id": model_id,
            "fe_count": len(combo), "included_fe": ",".join(combo),
            "dependent_variable": "firm_period_mean_log1p_engagement",
            "key_variable": "predicted_aggressive_intensity",
            "beta1_intensity":         b1v,
            "beta2_intensity_squared": b2v,
            "beta1_p_value":  coef_rows[0]["p_value"],
            "beta2_p_value":  coef_rows[1]["p_value"],
            "coefficient":          b1v,
            "classical_ols_se":     coef_rows[0]["classical_ols_se"],
            "t_stat":               coef_rows[0]["t_stat"],
            "p_value":              coef_rows[0]["p_value"],
            "stars":                coef_rows[0]["stars"],
            "n_obs":                rinfo["n_obs_after_filter"],
            "r_squared":            round(r2, 6) if r2==r2 else "",
            "adj_r_squared":        round(r2_adj, 6) if r2_adj==r2_adj else "",
            "df_model":             rinfo["k_eff"],
            "df_resid":             rinfo["df_resid"],
            "rank":                 rinfo["rank"],
            "n_fe_cells":           rinfo["n_cells"],
            "turning_point":        round(tp,4) if not math.isnan(tp) else "",
            "turning_point_in_observed_range": tpr,
            "inverted_u_check":     inv,
            "beta2_stars":          coef_rows[1]["stars"],
            "intensity_min":        round(int_min,4),
            "intensity_max":        round(int_max,4),
            "status":               "success",
            "interpretation_level": "preliminary_diagnostic",
            "note": "classifier NOT_A_CANDIDATE; predicted intensity leakage possible",
        })
        print(f"  H3 {combo}: batch1=not_applicable | full β1={b1v:.3f}{coef_rows[0]['stars']} "
              f"β2={b2v:.3f}{coef_rows[1]['stars']} tp={round(tp,3) if not math.isnan(tp) else 'nan'}")
    except Exception as ex:
        h3_results.append({
            "measurement_basis": "full_sample_predicted",
            "hypothesis": "H3", "model_id": model_id,
            "fe_count": len(combo), "included_fe": ",".join(combo),
            "dependent_variable": "firm_period_mean_log1p_engagement",
            "key_variable": "predicted_aggressive_intensity",
            "beta1_intensity": "", "beta2_intensity_squared": "",
            "beta1_p_value": "", "beta2_p_value": "",
            "coefficient": "", "classical_ols_se": "", "t_stat": "",
            "p_value": "", "stars": "", "n_obs": "",
            "r_squared": "", "adj_r_squared": "",
            "df_model": "", "df_resid": "", "rank": "",
            "turning_point": "", "turning_point_in_observed_range": "",
            "intensity_min": "", "intensity_max": "",
            "status": f"error: {str(ex)[:100]}",
            "interpretation_level": "error",
            "note": "",
        })

write_csv(os.path.join(OUT, "h3_time_fe_robustness.csv"), h3_results)

# ---------------------------------------------------------------------------
# STEP 7: Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 7: Summary")
print("=" * 60)

all_results_map = {
    ("H1",   "batch1_human_coded"):           h1_results,
    ("H1",   "full_sample_predicted"):        h1_results,
    ("H2_1", "batch1_human_coded"):           h21_results,
    ("H2_1", "full_sample_predicted"):        h21_results,
    ("H2_2", "batch1_human_coded"):           h22_results,
    ("H2_2", "full_sample_predicted"):        h22_results,
    ("H3",   "batch1_human_coded"):           h3_results,
    ("H3",   "full_sample_predicted"):        h3_results,
}

sum_rows = []
for (hyp, basis), all_res in all_results_map.items():
    sub = [r for r in all_res
           if r.get("measurement_basis") == basis
           and r.get("hypothesis") == hyp]
    success = [r for r in sub if r.get("status") == "success"]
    coeffs = [float(r["coefficient"]) for r in success if r.get("coefficient") not in ("","nan")]
    pvals  = [float(r["p_value"])     for r in success if r.get("p_value")     not in ("","nan")]
    pos    = sum(1 for c in coeffs if c > 0)
    sig05  = sum(1 for p in pvals  if p < 0.05)
    sig10  = sum(1 for p in pvals  if p < 0.10)
    d_stable = "yes" if (not coeffs or pos == len(coeffs) or pos == 0) else "no"

    adj_r2s = [(r["model_id"], float(r["adj_r_squared"]))
               for r in success if r.get("adj_r_squared") not in ("","nan")]
    best = max(adj_r2s, key=lambda x: x[1])[0] if adj_r2s else ""
    best_ar2 = max(adj_r2s, key=lambda x: x[1])[1] if adj_r2s else ""

    t_abs = [(r["model_id"], abs(float(r["t_stat"])))
             for r in success if r.get("t_stat") not in ("","nan")]
    conservative = min(t_abs, key=lambda x: x[1])[0] if t_abs else ""

    if not success:
        conclusion = "no_models_run"
    elif pos == len(coeffs) and sig05 == len(coeffs):
        conclusion = "all_positive_all_sig_p05"
    elif pos == len(coeffs) and sig10 == len(coeffs):
        conclusion = "all_positive_all_sig_p10"
    elif pos == len(coeffs) and sig05 > 0:
        conclusion = "all_positive_some_sig_p05"
    elif pos == len(coeffs):
        conclusion = "all_positive_ns"
    elif d_stable == "yes":
        conclusion = "all_negative_ns"
    else:
        conclusion = "mixed_direction"

    sum_rows.append({
        "hypothesis":             hyp,
        "measurement_basis":      basis,
        "key_variable":           sub[0].get("key_variable","") if sub else "",
        "total_models_attempted": len(sub),
        "total_models_success":   len(success),
        "positive_direction_count": pos,
        "significant_p05_count":  sig05,
        "significant_p10_count":  sig10,
        "direction_stable":       d_stable,
        "best_model_by_adj_r2":  best,
        "best_adj_r2":            round(best_ar2, 6) if best_ar2 != "" else "",
        "most_conservative_model": conservative,
        "conclusion":             conclusion,
    })
    print(f"  {hyp:5} {basis:35}: success={len(success)}/{len(sub)} "
          f"pos={pos} sig05={sig05} → {conclusion}")

write_csv(os.path.join(OUT, "time_fe_robustness_summary.csv"), sum_rows)
write_csv(os.path.join(OUT, "time_fe_sample_attrition.csv"), attrition_rows)

# ---------------------------------------------------------------------------
# STEP 8: Spot-check coefficients
# ---------------------------------------------------------------------------
print("\n--- Spot-checks ---")

def show(results, basis, model_id):
    for r in results:
        if r.get("measurement_basis") == basis and r.get("model_id") == model_id:
            return f"β={r['coefficient']} SE={r['classical_ols_se']} {r['stars']} n={r['n_obs']}"
    return "not found"

print("H1 batch1 year_month:", show(h1_results, "batch1_human_coded", "year_month"))
print("H1 full   year_month:", show(h1_results, "full_sample_predicted", "year_month"))
print("H2-1 batch1 year:    ", show(h21_results, "batch1_human_coded", "year"))
print("H2-1 full   year:    ", show(h21_results, "full_sample_predicted", "year"))
print("H3 full year:        ", show(h3_results, "full_sample_predicted", "year"))
print("H3 full year_month:  ", show(h3_results, "full_sample_predicted", "year_month"))

# ---------------------------------------------------------------------------
# STEP 9: Interpretation MD
# ---------------------------------------------------------------------------
def gs(hyp, basis, col):
    for r in sum_rows:
        if r["hypothesis"] == hyp and r["measurement_basis"] == basis:
            return r.get(col, "—")
    return "—"

def coef_range(results, basis, hyp):
    vals = [float(r["coefficient"]) for r in results
            if r.get("measurement_basis")==basis and r.get("hypothesis")==hyp
            and r.get("status")=="success" and r.get("coefficient") not in ("","nan")]
    return f"{min(vals):.3f} ~ {max(vals):.3f}" if vals else "—"

md = f"""# H1/H2/H3 시간 고정효과 Robustness 분석

**생성일**: 2026-06-19  **기준 commit**: 1926e25
**SE 유형**: Classical OLS (s²×(X'X)⁻¹) — HC3/robust SE 미사용
**FE 구현**: Joint interaction cell demeaning (pandas groupby, single-pass)
- 계층적 FE 조합(예: year+month+day)은 가장 세밀한 단위와 동치
- 비계층적 조합(예: month×hour_of_day)은 교차 셀(cross-cell) FE
- 분석 성격: PRELIMINARY ROBUSTNESS CHECK ONLY

---

## 1. 분석 목적

기존 1926e25 two-basis plain OLS 결과가 시간별 공통 충격(time shocks) 통제 후에도
핵심 계수의 방향과 유의성이 유지되는지 확인.

---

## 2. 기존 1926e25 vs 이번 robustness

| 항목 | 1926e25 plain OLS | 이번 time FE robustness |
|---|---|---|
| 시간 통제 | 없음 | 1~4개 FE 조합 30가지 |
| SE 방식 | Classical OLS | Classical OLS (동일) |
| 분리 구조 | Batch1 / Full-sample | 동일 |
| 모델 수 | 4 per basis | 30 × 2 basis per hypothesis |

---

## 3. 시간 FE 조합 (30개)

FE 후보: year / month / week / day / hour
C(5,1)=5 + C(5,2)=10 + C(5,3)=10 + C(5,4)=5 = **30 combinations**

| 데이터 | year | month | week | day | hour |
|---|---|---|---|---|---|
| Batch1 H1 (1,482) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch1 H2/H3 (648) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch1 H3 firm-level | N/A | N/A | N/A | N/A | N/A |
| Full H1 integrated (68,039) | ✅ | ✅ | ✅ | ✅ | ✅ (hour_of_day) |
| Full H2 h2_post (28,177) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Full H3 firm-month (3,532) | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4. H1 결과 요약

**가설**: 유머 post → 더 높은 engagement

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 성공 모델 수 | {gs('H1','batch1_human_coded','total_models_success')}/30 | {gs('H1','full_sample_predicted','total_models_success')}/30 |
| 계수 범위 | {coef_range(h1_results,'batch1_human_coded','H1')} | {coef_range(h1_results,'full_sample_predicted','H1')} |
| 양수 방향 유지 모델 | {gs('H1','batch1_human_coded','positive_direction_count')} | {gs('H1','full_sample_predicted','positive_direction_count')} |
| p<.05 유의 모델 수 | {gs('H1','batch1_human_coded','significant_p05_count')} | {gs('H1','full_sample_predicted','significant_p05_count')} |
| 방향 안정성 | {gs('H1','batch1_human_coded','direction_stable')} | {gs('H1','full_sample_predicted','direction_stable')} |
| 결론 | **{gs('H1','batch1_human_coded','conclusion')}** | **{gs('H1','full_sample_predicted','conclusion')}** |

---

## 5. H2-1 결과 요약

**가설**: Aggressive humor → other humor보다 높은 engagement

| | Batch1 human-coded (n_agg=44) | Full-sample predicted (n_pred_agg=6,857) |
|---|---|---|
| 성공 모델 수 | {gs('H2_1','batch1_human_coded','total_models_success')}/30 | {gs('H2_1','full_sample_predicted','total_models_success')}/30 |
| 계수 범위 | {coef_range(h21_results,'batch1_human_coded','H2_1')} | {coef_range(h21_results,'full_sample_predicted','H2_1')} |
| 양수 방향 유지 | {gs('H2_1','batch1_human_coded','positive_direction_count')} | {gs('H2_1','full_sample_predicted','positive_direction_count')} |
| p<.05 유의 모델 수 | {gs('H2_1','batch1_human_coded','significant_p05_count')} | {gs('H2_1','full_sample_predicted','significant_p05_count')} |
| 방향 안정성 | {gs('H2_1','batch1_human_coded','direction_stable')} | {gs('H2_1','full_sample_predicted','direction_stable')} |
| 결론 | **{gs('H2_1','batch1_human_coded','conclusion')}** | **{gs('H2_1','full_sample_predicted','conclusion')}** |

- Batch1 주의: n_agg=44 → time FE 추가 시 검정력 더욱 낮아짐
- Full 주의: type classifier NOT_A_CANDIDATE; leakage (#NationalRoastDay) 확인됨

---

## 6. H2-2 결과 요약

**가설**: Four humor types 비교 (aggressive coefficient, ref=affiliative)

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 성공 모델 수 | {gs('H2_2','batch1_human_coded','total_models_success')}/30 | {gs('H2_2','full_sample_predicted','total_models_success')}/30 |
| 계수 범위 | {coef_range(h22_results,'batch1_human_coded','H2_2')} | {coef_range(h22_results,'full_sample_predicted','H2_2')} |
| 양수 방향 유지 | {gs('H2_2','batch1_human_coded','positive_direction_count')} | {gs('H2_2','full_sample_predicted','positive_direction_count')} |
| p<.05 유의 모델 수 | {gs('H2_2','batch1_human_coded','significant_p05_count')} | {gs('H2_2','full_sample_predicted','significant_p05_count')} |
| 방향 안정성 | {gs('H2_2','batch1_human_coded','direction_stable')} | {gs('H2_2','full_sample_predicted','direction_stable')} |
| 결론 | **{gs('H2_2','batch1_human_coded','conclusion')}** | **{gs('H2_2','full_sample_predicted','conclusion')}** |

---

## 7. H3 결과 요약

**가설**: Aggressive intensity → engagement (역 U자형)

| | Batch1 human-coded | Full-sample predicted |
|---|---|---|
| 상태 | not_applicable (전체) | {gs('H3','full_sample_predicted','total_models_success')}/30 성공 |
| 이유 | firm-level cross-section; no time dim | week/day/hour 미가용 (year/month만 가능) |
| 계수 범위(β1) | — | {coef_range(h3_results,'full_sample_predicted','H3')} |
| 양수 방향(β1) | — | {gs('H3','full_sample_predicted','positive_direction_count')} |
| p<.05 유의(β1) | — | {gs('H3','full_sample_predicted','significant_p05_count')} |
| 방향 안정성 | — | {gs('H3','full_sample_predicted','direction_stable')} |
| 결론 | not_applicable | **{gs('H3','full_sample_predicted','conclusion')}** |

- Full H3 주의: classifier NOT_A_CANDIDATE; predicted intensity leakage 가능

---

## 8. Batch1 vs Full-sample 비교

| 가설 | Batch1 방향 안정 | Full 방향 안정 | 해석 |
|---|---|---|---|
| H1 | {gs('H1','batch1_human_coded','direction_stable')} | {gs('H1','full_sample_predicted','direction_stable')} | 시간 통제 후 안정성 |
| H2-1 | {gs('H2_1','batch1_human_coded','direction_stable')} | {gs('H2_1','full_sample_predicted','direction_stable')} | |
| H2-2 | {gs('H2_2','batch1_human_coded','direction_stable')} | {gs('H2_2','full_sample_predicted','direction_stable')} | |
| H3 | N/A | {gs('H3','full_sample_predicted','direction_stable')} | firm-level 한계 |

---

## 9. 가장 안정적인 가설 (time FE 후)

H1이 가장 안정적으로 예상:
- 양 basis에서 계수 양수 방향 유지
- Full H1은 n=68,039으로 time FE 추가 후에도 검정력 충분

---

## 10. 가장 민감한 가설 (time FE 후)

H2 batch1이 가장 민감:
- n_agg=44의 낮은 검정력으로 time FE 추가 시 SE 증가 → 유의성 손실 가능
- 방향성(양수)은 유지될 수 있으나 p-value는 상승 예상

---

## 11. 주요 limitation

1. **Joint interaction FE**: Additive FE가 아닌 joint saturation 사용 → 비계층적 조합에서 더 많은 자유도 흡수 (conservative)
2. **k_eff 근사**: n_joint_cells 기반 계산 → 실제 rank보다 과대 추정 가능 → SE 약간 과대
3. **Batch1 H3**: firm-level → time FE 불가 (fundamental limitation)
4. **Full H3 week/day/hour**: firm-month panel의 period-based 구조 한계
5. **Classifier leakage**: Full H2/H3의 모든 결과는 type classifier leakage 영향 가능

---

## 12. 다음 판단 지점

1. H1 양 basis에서 time FE 후에도 계수 유지 → H1 preliminary robustness 일부 확보
2. H2 batch1 time FE 후 방향성 유지 여부 → 인간 코딩 결과의 time-driven confound 여부 판단
3. H3 full-sample: β1>0, β2<0 패턴이 year/month FE 후에도 유지되는지 확인
4. Company-level clustered SE는 별도 robustness 작업으로 추가 가능

---

## 13. 금지사항 준수

- [x] backfill/workflow 파일 미수정
- [x] 기존 1926e25 결과 파일 삭제/덮어쓰기 없음
- [x] HC3/robust SE 미사용
- [x] 새 prediction/classifier 없음
- [x] H2/H3 formal support 미선언

---

*생성 스크립트*: `run_time_fe_robustness.py`
*출력 폴더*: `time_fixed_effects_robustness/`
*생성일*: 2026-06-19
"""

with open(os.path.join(OUT, "time_fe_robustness_interpretation.md"), "w") as f:
    f.write(md)
print("  wrote time_fe_robustness_interpretation.md")

# ---------------------------------------------------------------------------
# Final verification
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)
out_files = sorted(os.listdir(OUT))
print(f"Output files in {OUT}:")
for fn in out_files:
    sz = os.path.getsize(os.path.join(OUT, fn))
    print(f"  {fn}: {sz:,} bytes")

orig = os.path.join(BASE, "ols_hypothesis_results")
orig_count = sum(1 for f in os.listdir(orig) if not os.path.isdir(os.path.join(orig, f)))
print(f"\nOriginal ols_hypothesis_results/ files: {orig_count} (not deleted)")
print("DONE")
