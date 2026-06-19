"""
run_control_variables_v3.py

Model 4: Control variable model (v3 classifier, coder3 batch2)

H1/H2 post-level:
  log(1+Eng_i) = β0 + β1·Agg + β2·Aff + β3·SE + β4·SD
                 + γ1·text_length + γ2·hashtag_count + γ3·mention_count + ε

H3 firm-quarter:
  MeanLog(1+Eng)_{fq} = α + β1·Intensity + β2·Intensity²
                        + γ1·mean_text_len + γ2·mean_hashtag + γ3·mean_mention
                        + γ4·log_total_posts + ε

Classical OLS SE. No company dummies. No time dummies. No emoji_count.
"""
from __future__ import annotations

import csv
import math
import sys
from datetime import datetime
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from scipy import stats as scipy_stats

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"
OUT  = Path(__file__).parent

H2_RR    = CI / "data" / "regression_ready_v3" / "h2_post_level_regression_ready.csv"
TEMPLATE = CI / "data" / "human_labeling_template" / "training_labels_v3_with_coder3_batch2.csv"
V3_CLS   = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification_v3.csv"

# Baselines
M1_CONTRAST = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_baseline_v3_coder3_batch2/01_simple_ols_h1_h2_contrast_tests.csv"
M1_COEF     = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_baseline_v3_coder3_batch2/01_simple_ols_h1_h2_full_sample_results.csv"
M1_H3       = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_baseline_v3_coder3_batch2/01_simple_ols_h3_quadratic_diagnostics.csv"
M2_CONTRAST = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_company_dummy_v3/company_dummy_h1_h2_contrast_tests.csv"
M2_COEF     = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_company_dummy_v3/company_dummy_h1_h2_full_sample_results.csv"
M2_H3       = ROOT / "20260618expand/ols_hypothesis_results/simple_ols_company_dummy_v3/company_dummy_h3_quadratic_diagnostics.csv"
M3_CONTRAST = ROOT / "20260618expand/ols_hypothesis_results/time_dummy_combinations_v3/time_dummy_h1_h2_contrast_tests.csv"
M3_COEF     = ROOT / "20260618expand/ols_hypothesis_results/time_dummy_combinations_v3/time_dummy_h1_h2_full_sample_results.csv"
M3_H3       = ROOT / "20260618expand/ols_hypothesis_results/time_dummy_combinations_v3/time_dummy_h3_quadratic_diagnostics.csv"

TWITTER_FMT = "%a %b %d %H:%M:%S +0000 %Y"

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def to_f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def stars(p: float) -> str:
    if math.isnan(p): return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


def period_to_quarter(period: str) -> str:
    try:
        y, m = period.split("-")
        q = (int(m) - 1) // 3 + 1
        return f"{y}-Q{q}"
    except Exception:
        return "missing"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        print(f"  → {path.name} written  (0 rows)")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  → {path.name} written  ({len(rows)} rows)")


# ─────────────────────────────────────────────────────────────────────────────
# OLS core (classical SE)
# ─────────────────────────────────────────────────────────────────────────────

def ols_fit(X: np.ndarray, y: np.ndarray):
    n, k = X.shape
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat  = X @ b
    resid = y - yhat
    ssr   = float(resid @ resid)
    s2    = ssr / (n - k) if n > k else float("nan")
    try:
        XtXi = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        XtXi = np.linalg.pinv(X.T @ X)
    V     = s2 * XtXi
    se    = np.sqrt(np.diag(V))
    t_    = b / se
    p_    = np.array([float(2 * scipy_stats.t.sf(abs(ti), df=n-k)) for ti in t_])
    sst   = float(np.sum((y - float(np.mean(y)))**2))
    r2    = 1.0 - ssr / sst if sst > 0 else 0.0
    adj   = 1.0 - (1.0 - r2) * (n - 1) / (n - k) if n > k else 0.0
    rk    = int(np.linalg.matrix_rank(X))
    cn    = float(np.linalg.cond(X))
    return b, V, t_, p_, n, k, r2, adj, n - k, resid, rk, cn


def contrast_test(c: list[float], b: np.ndarray, V: np.ndarray, df: int):
    c   = np.array(c, dtype=float)
    est = float(c @ b)
    var = float(c @ V @ c)
    se  = math.sqrt(max(var, 0.0))
    if se == 0.0:
        return est, se, float("nan"), float("nan")
    t_  = est / se
    p_  = float(2 * scipy_stats.t.sf(abs(t_), df))
    return est, se, t_, p_


def run_contrasts(b4: np.ndarray, V4: np.ndarray, df: int,
                  n_agg: int, n_aff: int, n_se: int, n_sd: int,
                  model_label: str) -> list[dict]:
    n_h = n_agg + n_aff + n_se + n_sd
    n_o = n_aff + n_se + n_sd
    n_s = n_se  + n_sd

    def w(num, den): return num / den if den else 0

    c_rows = []
    def _add(hyp, label_c, c, direction="positive_sig"):
        est, se_c, t_c, p_c = contrast_test(c, b4, V4, df)
        sig = not math.isnan(p_c) and p_c < 0.10
        support = ("supported" if est > 0 and sig else "not_supported") \
                  if direction == "positive_sig" else \
                  ("supported" if est > 0 else "not_supported")
        c_rows.append({
            "model":      model_label,
            "hypothesis": hyp,
            "contrast":   label_c,
            "estimate":   round(est, 6),
            "std_error":  round(se_c, 6),
            "t_statistic": round(t_c, 4) if math.isfinite(t_c) else "NA",
            "p_value":    round(p_c, 6) if math.isfinite(p_c) else "NA",
            "stars":      stars(p_c) if math.isfinite(p_c) else "",
            "direction":  "positive" if est > 0 else "negative",
            "support":    support,
        })
        print(f"    {hyp} | {label_c:50s} est={est:+.4f} p={p_c:.4f}{stars(p_c)}")

    w_agg = w(n_agg, n_h); w_aff = w(n_aff, n_h)
    w_se_ = w(n_se, n_h);  w_sd_ = w(n_sd, n_h)
    w_aff_o = w(n_aff, n_o); w_se_o = w(n_se, n_o); w_sd_o = w(n_sd, n_o)
    w_se_s  = w(n_se, n_s);  w_sd_s = w(n_sd, n_s)

    print(f"  === Contrast tests [{model_label}] ===")
    _add("H1",   "Weighted Humor Effect (vs non-humorous)", [w_agg, w_aff, w_se_, w_sd_])
    _add("H2-1", "Aggressive − Other humor (weighted avg)", [1, -w_aff_o, -w_se_o, -w_sd_o])
    _add("H2-2", "Aggressive − SELF (se+sd weighted avg)",  [1, 0, -w_se_s, -w_sd_s])
    _add("H2-3", "Aggressive − Affiliative",    [1, -1,  0,  0])
    _add("H2-3", "Aggressive − Self-Enhancing", [1,  0, -1,  0])
    _add("H2-3", "Aggressive − Self-Defeating", [1,  0,  0, -1])
    return c_rows


# ─────────────────────────────────────────────────────────────────────────────
# VIF
# ─────────────────────────────────────────────────────────────────────────────

def compute_vif(X_no_intercept: np.ndarray, var_names: list[str]) -> list[dict]:
    n, k = X_no_intercept.shape
    rows = []
    for i, nm in enumerate(var_names):
        y_i   = X_no_intercept[:, i]
        X_oth = np.delete(X_no_intercept, i, axis=1)
        X_oth = np.column_stack([np.ones(n), X_oth])
        b_, _, _, _ = np.linalg.lstsq(X_oth, y_i, rcond=None)
        yhat  = X_oth @ b_
        ssr   = float(np.sum((y_i - yhat)**2))
        sst   = float(np.sum((y_i - float(np.mean(y_i)))**2))
        r2    = 1.0 - ssr / sst if sst > 0 else 0.0
        vif   = 1.0 / (1.0 - r2) if r2 < 1.0 else float("inf")
        rows.append({"variable": nm, "R2_in_aux": round(r2, 6),
                     "VIF": round(vif, 4) if math.isfinite(vif) else "Inf"})
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────

def summary_stats(arr: np.ndarray, name: str, sample: str) -> dict:
    valid = arr[~np.isnan(arr)]
    n = len(valid)
    if n == 0:
        return {"sample": sample, "variable": name, "n": 0}
    return {
        "sample":   sample,
        "variable": name,
        "n":        n,
        "mean":     round(float(np.mean(valid)), 4),
        "std":      round(float(np.std(valid, ddof=1)), 4),
        "min":      round(float(np.min(valid)), 4),
        "p25":      round(float(np.percentile(valid, 25)), 4),
        "median":   round(float(np.median(valid)), 4),
        "p75":      round(float(np.percentile(valid, 75)), 4),
        "max":      round(float(np.max(valid)), 4),
    }


def corr_matrix(X_cols: np.ndarray, col_names: list[str]) -> list[dict]:
    n, k = X_cols.shape
    rows = []
    for i in range(k):
        row = {"variable": col_names[i]}
        for j in range(k):
            xi = X_cols[:, i]; xj = X_cols[:, j]
            denom = np.std(xi, ddof=1) * np.std(xj, ddof=1) * n
            if denom == 0:
                row[col_names[j]] = "NA"
            else:
                corr = float(np.cov(xi, xj, ddof=1)[0, 1] / (np.std(xi, ddof=1) * np.std(xj, ddof=1)))
                row[col_names[j]] = round(corr, 4)
        rows.append(row)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_full_sample():
    print("[Loading] H2 regression-ready v3 with controls...")
    rows = []
    with open(H2_RR, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"  N={len(rows):,}")
    return rows


def load_human_coded():
    print("[Loading] Human-coded template + controls join...")
    # Build classified v3 control lookup
    ctrl_lookup: dict[str, dict] = {}
    with open(V3_CLS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ctrl_lookup[r["tweet_id"]] = {
                "text_length":   r.get("text_length",   ""),
                "hashtag_count": r.get("hashtag_count", ""),
                "mention_count": r.get("mention_count", ""),
                "log_total_engagement": r.get("log_total_engagement", ""),
                "total_engagement": r.get("total_engagement", ""),
            }

    VALID_PRES = {"0", "1"}
    rows_out = []
    n_missing_ctrl = 0
    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("human_humor_presence", "").strip() not in VALID_PRES:
                continue
            pres = r["human_humor_presence"].strip()
            typ  = r.get("human_humor_type", "").strip()
            tid  = r.get("tweet_id", "")
            ctrl = ctrl_lookup.get(tid, {})
            if not ctrl:
                n_missing_ctrl += 1
                continue   # drop rows where controls unavailable
            log_eng = math.log1p(to_f(ctrl.get("total_engagement", "0")))
            rows_out.append({
                "company_name":         r.get("company_name", ""),
                "log_total_engagement": log_eng,
                "aggressive_humor":     "1" if pres=="1" and typ=="1" else "0",
                "affiliative_humor":    "1" if pres=="1" and typ=="2" else "0",
                "self_enhancing_humor": "1" if pres=="1" and typ=="3" else "0",
                "self_defeating_humor": "1" if pres=="1" and typ=="4" else "0",
                "text_length":          ctrl["text_length"],
                "hashtag_count":        ctrl["hashtag_count"],
                "mention_count":        ctrl["mention_count"],
                "period":               "",  # not available in template
                "tweet_id":             tid,
            })
    print(f"  HC matched: {len(rows_out):,}  dropped (controls unavailable): {n_missing_ctrl}")
    return rows_out, n_missing_ctrl


def aggregate_fq_with_controls(rows: list[dict]) -> list[dict]:
    panel: dict = {}
    for r in rows:
        period = r.get("period", "")
        if not period:
            continue
        q   = period_to_quarter(period)
        if q == "missing":
            continue
        co  = r.get("company_name", "")
        key = (co, q)
        if key not in panel:
            panel[key] = {
                "company": co, "quarter": q,
                "_n": 0, "_agg": 0, "_log_sum": 0.0,
                "_tl_sum": 0.0, "_ht_sum": 0.0, "_mn_sum": 0.0,
            }
        p = panel[key]
        p["_n"]       += 1
        p["_agg"]     += int(to_f(r.get("aggressive_humor", "0")))
        p["_log_sum"] += to_f(r.get("log_total_engagement", "0"))
        p["_tl_sum"]  += to_f(r.get("text_length", "0"))
        p["_ht_sum"]  += to_f(r.get("hashtag_count", "0"))
        p["_mn_sum"]  += to_f(r.get("mention_count", "0"))

    fq_rows = []
    for p in panel.values():
        n = p["_n"]
        if n == 0:
            continue
        inten = p["_agg"] / n
        fq_rows.append({
            "company":                 p["company"],
            "quarter":                 p["quarter"],
            "post_count":              n,
            "aggressive_intensity":    round(inten, 12),
            "aggressive_intensity_sq": round(inten * inten, 12),
            "mean_log_engagement":     round(p["_log_sum"] / n, 6),
            "mean_text_length":        round(p["_tl_sum"]  / n, 6),
            "mean_hashtag_count":      round(p["_ht_sum"]  / n, 6),
            "mean_mention_count":      round(p["_mn_sum"]  / n, 6),
            "log_total_posts":         round(math.log1p(n), 6),
        })
    return fq_rows


def aggregate_hc_fq_with_controls(rows: list[dict]) -> list[dict]:
    """HC aggregation: derive quarter from created_at (no period field)."""
    panel: dict = {}
    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        tid_to_ca = {r["tweet_id"]: r.get("created_at", "") for r in csv.DictReader(f)}

    # Build lookup from rows
    tid_to_row = {r["tweet_id"]: r for r in rows}

    for tid, r in tid_to_row.items():
        ca = tid_to_ca.get(tid, "")
        try:
            dt = datetime.strptime(ca.strip(), TWITTER_FMT)
            q_int = (dt.month - 1) // 3 + 1
            q = f"{dt.year}-Q{q_int}"
        except Exception:
            continue
        co  = r.get("company_name", "")
        key = (co, q)
        if key not in panel:
            panel[key] = {
                "company": co, "quarter": q,
                "_n": 0, "_agg": 0, "_log_sum": 0.0,
                "_tl_sum": 0.0, "_ht_sum": 0.0, "_mn_sum": 0.0,
            }
        p = panel[key]
        p["_n"]       += 1
        p["_agg"]     += int(to_f(r.get("aggressive_humor", "0")))
        p["_log_sum"] += to_f(r.get("log_total_engagement", "0"))
        p["_tl_sum"]  += to_f(r.get("text_length", "0"))
        p["_ht_sum"]  += to_f(r.get("hashtag_count", "0"))
        p["_mn_sum"]  += to_f(r.get("mention_count", "0"))

    fq_rows = []
    for p in panel.values():
        n = p["_n"]
        if n == 0:
            continue
        inten = p["_agg"] / n
        fq_rows.append({
            "company":                 p["company"],
            "quarter":                 p["quarter"],
            "post_count":              n,
            "aggressive_intensity":    round(inten, 12),
            "aggressive_intensity_sq": round(inten * inten, 12),
            "mean_log_engagement":     round(p["_log_sum"] / n, 6),
            "mean_text_length":        round(p["_tl_sum"]  / n, 6),
            "mean_hashtag_count":      round(p["_ht_sum"]  / n, 6),
            "mean_mention_count":      round(p["_mn_sum"]  / n, 6),
            "log_total_posts":         round(math.log1p(n), 6),
        })
    return fq_rows


# ─────────────────────────────────────────────────────────────────────────────
# Baseline loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_fs_baseline(path: Path, key_col: str, val_cols: list[str],
                      model_filter: str = "Full_sample") -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if model_filter:
                # check either "model" or "sample" column
                model_val = r.get("model", "") or r.get("sample", "")
                if not model_val.startswith(model_filter):
                    continue
            k = r.get(key_col, "")
            if k and k not in out:
                out[k] = {c: r.get(c, "n/a") for c in val_cols}
    return out


def load_baselines():
    m1_contrast = _load_fs_baseline(M1_CONTRAST, "contrast",
                                    ["estimate", "p_value", "stars", "support"])
    m1_coef     = _load_fs_baseline(M1_COEF, "term",
                                    ["coefficient", "p_value", "stars"])
    m2_contrast = _load_fs_baseline(M2_CONTRAST, "contrast",
                                    ["estimate", "p_value", "stars", "support"],
                                    "Full_sample_CD")
    m2_coef     = _load_fs_baseline(M2_COEF, "term",
                                    ["coefficient", "p_value", "stars"],
                                    "Full_sample_CD")
    m3_contrast = _load_fs_baseline(M3_CONTRAST, "contrast",
                                    ["estimate", "p_value", "stars", "support"],
                                    "Full_sample")
    m3_coef     = _load_fs_baseline(M3_COEF, "combo",
                                    ["b_aggressive", "b_affiliative",
                                     "b_self_enhancing", "b_self_defeating",
                                     "stars_agg", "stars_aff", "stars_se", "stars_sd"])

    # H3 baselines (first full-sample row)
    m1_h3, m2_h3, m3_h3 = {}, {}, {}
    for path_, d in [(M1_H3, m1_h3), (M2_H3, m2_h3), (M3_H3, m3_h3)]:
        if path_.exists():
            with open(path_, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if "Full_sample" in r.get("model","") or \
                       "Full_sample" in r.get("sample",""):
                        for k, v in r.items():
                            d[k] = v
                        break

    return m1_contrast, m1_coef, m2_contrast, m2_coef, m3_contrast, m3_coef, m1_h3, m2_h3, m3_h3


# ─────────────────────────────────────────────────────────────────────────────
# H1/H2 OLS with controls
# ─────────────────────────────────────────────────────────────────────────────

H1H2_TERMS = ["intercept", "aggressive", "affiliative",
               "self_enhancing", "self_defeating",
               "text_length", "hashtag_count", "mention_count"]

def run_h1h2_controls(rows: list[dict], label: str) -> tuple:
    n    = len(rows)
    y    = np.array([to_f(r["log_total_engagement"]) for r in rows])
    agg  = np.array([to_f(r["aggressive_humor"])     for r in rows])
    aff  = np.array([to_f(r["affiliative_humor"])    for r in rows])
    se_  = np.array([to_f(r["self_enhancing_humor"]) for r in rows])
    sd   = np.array([to_f(r["self_defeating_humor"]) for r in rows])
    tl   = np.array([to_f(r["text_length"])          for r in rows])
    ht   = np.array([to_f(r["hashtag_count"])        for r in rows])
    mn   = np.array([to_f(r["mention_count"])        for r in rows])
    ones = np.ones(n)

    X = np.column_stack([ones, agg, aff, se_, sd, tl, ht, mn])
    b, V, t_, p_, n, k, r2, adj_r2, df, resid, rk, cn = ols_fit(X, y)

    n_agg = int(agg.sum()); n_aff = int(aff.sum())
    n_se  = int(se_.sum()); n_sd  = int(sd.sum())

    print(f"\n  [{label}] N={n:,}  k={k}  df={df:,}  rank={rk}  cond={cn:.2e}")
    print(f"    R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, nm in enumerate(H1H2_TERMS):
        print(f"    {nm:25s}  β={float(b[i]):+.4f}  t={float(t_[i]):+.3f}  p={float(p_[i]):.4f}{stars(float(p_[i]))}")

    # Coefficient rows
    coef_rows = []
    for i, nm in enumerate(H1H2_TERMS):
        coef_rows.append({
            "model":         label,
            "term":          nm,
            "coefficient":   round(float(b[i]), 6),
            "std_error":     round(math.sqrt(float(V[i, i])), 6),
            "t_statistic":   round(float(t_[i]), 4),
            "p_value":       round(float(p_[i]), 6),
            "stars":         stars(float(p_[i])),
            "n":             n, "r_squared": round(r2, 6),
            "adj_r_squared": round(adj_r2, 6), "df_residual": df,
        })

    # Contrast tests (b[1:5] = humor coefficients, V[1:5,1:5])
    b4  = b[1:5]
    V4  = V[1:5, 1:5]
    contrast_rows = run_contrasts(b4, V4, df, n_agg, n_aff, n_se, n_sd, label)

    # Rank diagnostics
    rank_diag = {
        "model":               label,
        "n":                   n,
        "k":                   k,
        "matrix_rank":         rk,
        "df_resid":            df,
        "condition_number":    round(cn, 4) if math.isfinite(cn) else "Inf",
        "rank_deficient":      str(rk < k),
    }

    # VIF for non-intercept columns
    X_noint = X[:, 1:]   # [agg, aff, se, sd, tl, ht, mn]
    vif_rows = compute_vif(X_noint, H1H2_TERMS[1:])
    for vr in vif_rows:
        vr["model"] = label

    return coef_rows, contrast_rows, rank_diag, vif_rows, b4, V4, df, n_agg, n_aff, n_se, n_sd, n


# ─────────────────────────────────────────────────────────────────────────────
# H3 OLS with controls
# ─────────────────────────────────────────────────────────────────────────────

H3_TERMS = ["intercept", "AggressiveIntensity", "AggressiveIntensity_sq",
             "mean_text_length", "mean_hashtag_count", "mean_mention_count",
             "log_total_posts"]

def run_h3_controls(fq_rows: list[dict], label: str) -> tuple:
    n    = len(fq_rows)
    y    = np.array([to_f(r["mean_log_engagement"])     for r in fq_rows])
    x1   = np.array([to_f(r["aggressive_intensity"])    for r in fq_rows])
    x2   = np.array([to_f(r["aggressive_intensity_sq"]) for r in fq_rows])
    tl   = np.array([to_f(r["mean_text_length"])        for r in fq_rows])
    ht   = np.array([to_f(r["mean_hashtag_count"])      for r in fq_rows])
    mn   = np.array([to_f(r["mean_mention_count"])      for r in fq_rows])
    lp   = np.array([to_f(r["log_total_posts"])         for r in fq_rows])
    ones = np.ones(n)

    X = np.column_stack([ones, x1, x2, tl, ht, mn, lp])
    b, V, t_, p_, n, k, r2, adj_r2, df, resid, rk, cn = ols_fit(X, y)

    beta1 = float(b[1])
    beta2 = float(b[2])
    tp    = -beta1 / (2 * beta2) if beta2 != 0 else float("inf")
    obs_min, obs_max = float(x1.min()), float(x1.max())
    in_range = math.isfinite(tp) and obs_min <= tp <= obs_max
    p2_val   = float(p_[2])
    h3_sup   = beta1 > 0 and beta2 < 0 and not math.isnan(p2_val) and p2_val < 0.10 and in_range

    print(f"\n  [{label}] N={n:,}  k={k}  df={df:,}  rank={rk}  cond={cn:.2e}")
    print(f"    R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, nm in enumerate(H3_TERMS):
        print(f"    {nm:30s}  β={float(b[i]):+.6f}  p={float(p_[i]):.4f}{stars(float(p_[i]))}")
    print(f"    Turning point: {tp:.4f}  range=[{obs_min:.4f},{obs_max:.4f}]  H3={h3_sup}")

    coef_rows = []
    for i, nm in enumerate(H3_TERMS):
        coef_rows.append({
            "model":         label,
            "term":          nm,
            "coefficient":   round(float(b[i]), 6),
            "std_error":     round(math.sqrt(float(V[i, i])), 6),
            "t_statistic":   round(float(t_[i]), 4),
            "p_value":       round(float(p_[i]), 6),
            "stars":         stars(float(p_[i])),
            "n": n, "r_squared": round(r2, 6), "adj_r_squared": round(adj_r2, 6),
        })

    diag = {
        "model":             label,
        "n_firm_quarters":   n,
        "k":                 k,
        "matrix_rank":       rk,
        "df_resid":          df,
        "condition_number":  round(cn, 4) if math.isfinite(cn) else "Inf",
        "rank_deficient":    str(rk < k),
        "beta1_intensity":   round(beta1, 6),
        "beta1_se":          round(math.sqrt(float(V[1,1])), 6),
        "beta1_t":           round(float(t_[1]), 4),
        "beta1_p":           round(float(p_[1]), 6),
        "beta1_stars":       stars(float(p_[1])),
        "beta2_intensity_sq": round(beta2, 6),
        "beta2_se":          round(math.sqrt(float(V[2,2])), 6),
        "beta2_t":           round(float(t_[2]), 4),
        "beta2_p":           round(float(p_[2]), 6),
        "beta2_stars":       stars(float(p_[2])),
        "turning_point":     round(tp, 6) if math.isfinite(tp) else "Inf",
        "obs_intensity_min": round(obs_min, 6),
        "obs_intensity_max": round(obs_max, 6),
        "tp_in_obs_range":   str(in_range),
        "H3_supported":      str(h3_sup),
        "r_squared":         round(r2, 6),
        "adj_r_squared":     round(adj_r2, 6),
    }

    rank_diag = {
        "model": label, "n": n, "k": k,
        "matrix_rank": rk, "df_resid": df,
        "condition_number": round(cn, 4) if math.isfinite(cn) else "Inf",
        "rank_deficient": str(rk < k),
    }

    X_noint = X[:, 1:]
    vif_rows = compute_vif(X_noint, H3_TERMS[1:])
    for vr in vif_rows:
        vr["model"] = label

    return coef_rows, diag, rank_diag, vif_rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("run_control_variables_v3.py")
    print("  Model 4: Control variable model")
    print("  Classical OLS SE. Controls only (no company/time dummies).")
    print("=" * 70)
    OUT.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    fs_rows = load_full_sample()
    hc_rows, n_hc_dropped = load_human_coded()

    print(f"\n[Aggregating] H3 firm-quarter (full-sample)...")
    fq_rows = aggregate_fq_with_controls(fs_rows)
    print(f"  N firm-quarters: {len(fq_rows):,}")

    print(f"\n[Aggregating] H3 firm-quarter (human-coded)...")
    fq_hc = aggregate_hc_fq_with_controls(hc_rows)
    print(f"  HC N firm-quarters: {len(fq_hc):,}")

    # ── Summary statistics ────────────────────────────────────────────────────
    print("\n[Diagnostics] Control variable summary statistics...")
    summ_rows = []
    for col in ["log_total_engagement", "aggressive_humor", "affiliative_humor",
                "self_enhancing_humor", "self_defeating_humor",
                "text_length", "hashtag_count", "mention_count"]:
        vals = np.array([to_f(r.get(col,"0")) for r in fs_rows])
        summ_rows.append(summary_stats(vals, col, "Full_sample"))
    for col in ["log_total_engagement", "aggressive_humor", "affiliative_humor",
                "self_enhancing_humor", "self_defeating_humor",
                "text_length", "hashtag_count", "mention_count"]:
        vals = np.array([to_f(r.get(col,"0")) for r in hc_rows])
        summ_rows.append(summary_stats(vals, col, "Human_coded"))
    for col in ["mean_log_engagement", "aggressive_intensity",
                "mean_text_length", "mean_hashtag_count",
                "mean_mention_count", "log_total_posts"]:
        vals = np.array([to_f(r.get(col,"0")) for r in fq_rows])
        summ_rows.append(summary_stats(vals, col, "FQ_Full"))
    _write_csv(OUT / "control_variable_summary_statistics.csv", summ_rows)

    # ── Missingness ───────────────────────────────────────────────────────────
    miss_rows = []
    for col in ["text_length", "hashtag_count", "mention_count"]:
        missing_n = sum(1 for r in fs_rows if r.get(col,"") in ("","None"))
        miss_rows.append({
            "sample": "Full_sample", "variable": col,
            "n_total": len(fs_rows),
            "n_missing": missing_n,
            "missing_share": round(missing_n / len(fs_rows), 6),
        })
    miss_rows.append({
        "sample": "Human_coded", "variable": "controls_via_tweet_id_join",
        "n_total": len(hc_rows) + n_hc_dropped,
        "n_missing": n_hc_dropped,
        "missing_share": round(n_hc_dropped / (len(hc_rows) + n_hc_dropped), 6),
    })
    _write_csv(OUT / "control_variable_missingness.csv", miss_rows)

    # ── Correlation matrix ────────────────────────────────────────────────────
    print("[Diagnostics] Correlation matrix...")
    ctrl_cols_fs = np.column_stack([
        [to_f(r["aggressive_humor"])     for r in fs_rows],
        [to_f(r["affiliative_humor"])    for r in fs_rows],
        [to_f(r["self_enhancing_humor"]) for r in fs_rows],
        [to_f(r["self_defeating_humor"]) for r in fs_rows],
        [to_f(r["text_length"])          for r in fs_rows],
        [to_f(r["hashtag_count"])        for r in fs_rows],
        [to_f(r["mention_count"])        for r in fs_rows],
    ])
    corr_names_fs = ["agg","aff","se","sd","text_length","hashtag_count","mention_count"]
    corr_fs = corr_matrix(ctrl_cols_fs, corr_names_fs)
    for row in corr_fs:
        row["sample"] = "Full_sample"

    ctrl_cols_fq = np.column_stack([
        [to_f(r["aggressive_intensity"])    for r in fq_rows],
        [to_f(r["aggressive_intensity_sq"]) for r in fq_rows],
        [to_f(r["mean_text_length"])        for r in fq_rows],
        [to_f(r["mean_hashtag_count"])      for r in fq_rows],
        [to_f(r["mean_mention_count"])      for r in fq_rows],
        [to_f(r["log_total_posts"])         for r in fq_rows],
    ])
    corr_names_fq = ["intensity","intensity_sq","mean_tl","mean_ht","mean_mn","log_posts"]
    corr_fq = corr_matrix(ctrl_cols_fq, corr_names_fq)
    for row in corr_fq:
        row["sample"] = "FQ_Full"

    _write_csv(OUT / "control_variable_correlation_matrix.csv", corr_fs + corr_fq)

    # Print intensity vs intensity² correlation
    corr_int_int2 = next((r for r in corr_fq if r["variable"]=="intensity"), {})
    print(f"  H3 corr(intensity, intensity²): {corr_int_int2.get('intensity_sq','n/a')}")

    # ── H1/H2 Full-sample OLS ─────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("H1/H2 Full-sample control model")
    print("─"*60)
    fs_coef, fs_cont, fs_rank_h1h2, fs_vif, b4_fs, V4_fs, df_fs, \
        n_agg_f, n_aff_f, n_se_f, n_sd_f, n_fs = \
        run_h1h2_controls(fs_rows, "Full_sample_Ctrl")

    # ── H1/H2 Human-coded OLS ────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("H1/H2 Human-coded control model")
    print("─"*60)
    hc_coef, hc_cont, hc_rank_h1h2, hc_vif, b4_hc, V4_hc, df_hc, \
        n_agg_h, n_aff_h, n_se_h, n_sd_h, n_hc = \
        run_h1h2_controls(hc_rows, "Human_coded_Ctrl")

    _write_csv(OUT / "control_h1_h2_full_sample_results.csv",  fs_coef)
    _write_csv(OUT / "control_h1_h2_human_coded_results.csv",  hc_coef)
    _write_csv(OUT / "control_h1_h2_contrast_tests.csv", fs_cont + hc_cont)

    # ── H3 Full-sample ────────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("H3 Full-sample firm-quarter control model")
    print("─"*60)
    h3_fs_coef, h3_fs_diag, h3_fs_rank, h3_fs_vif = run_h3_controls(fq_rows, "Full_sample_H3_Ctrl")
    _write_csv(OUT / "control_h3_full_sample_results.csv", h3_fs_coef)

    # ── H3 Human-coded ───────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("H3 Human-coded firm-quarter control model")
    print("─"*60)
    if len(fq_hc) > 8:
        h3_hc_coef, h3_hc_diag, h3_hc_rank, h3_hc_vif = run_h3_controls(fq_hc, "Human_coded_H3_Ctrl")
    else:
        print(f"  SKIPPED: only {len(fq_hc)} firm-quarters (need >8 for k=7 params)")
        h3_hc_coef = [{"model": "Human_coded_H3_Ctrl", "note": "insufficient_data"}]
        h3_hc_diag = {"model": "Human_coded_H3_Ctrl", "H3_supported": "insufficient_data"}
        h3_hc_rank = {"model": "Human_coded_H3_Ctrl"}
        h3_hc_vif  = []

    _write_csv(OUT / "control_h3_human_coded_results.csv", h3_hc_coef)
    _write_csv(OUT / "control_h3_quadratic_diagnostics.csv", [h3_fs_diag, h3_hc_diag])

    # ── VIF + Rank diagnostics ────────────────────────────────────────────────
    all_vif = fs_vif + hc_vif + h3_fs_vif + h3_hc_vif
    _write_csv(OUT / "control_variable_vif_diagnostics.csv", all_vif)
    _write_csv(OUT / "control_variable_rank_diagnostics.csv",
               [fs_rank_h1h2, hc_rank_h1h2, h3_fs_rank, h3_hc_rank])

    # ── 4-model comparison ────────────────────────────────────────────────────
    print("\n[Building] 4-model summary comparison...")
    m1_cnt, m1_coef, m2_cnt, m2_coef, m3_cnt, m3_coef, m1_h3, m2_h3, m3_h3 = load_baselines()

    # Helper: get Model 3 "year+month" as representative Time Dummy
    M3_REP = "year+month"
    m3_coef_rep = m3_coef.get(M3_REP, {})

    TERM_MAP = {
        "aggressive":    ("b_aggressive",    "stars_agg"),
        "affiliative":   ("b_affiliative",   "stars_aff"),
        "self_enhancing":("b_self_enhancing","stars_se"),
        "self_defeating":("b_self_defeating","stars_sd"),
    }

    cmp_rows = []

    # Coefficient comparison
    for term, (m3_col, m3_star) in TERM_MAP.items():
        m4_row = next((r for r in fs_coef if r.get("term")==term), {})
        cmp_rows.append({
            "metric":              f"coef_{term}",
            "model1_simple_ols":   m1_coef.get(term,{}).get("coefficient","n/a"),
            "model1_stars":        m1_coef.get(term,{}).get("stars",""),
            "model2_company_dum":  m2_coef.get(term,{}).get("coefficient","n/a"),
            "model2_stars":        m2_coef.get(term,{}).get("stars",""),
            "model3_time_dum_ym":  m3_coef_rep.get(m3_col,"n/a"),
            "model3_stars":        m3_coef_rep.get(m3_star,""),
            "model4_controls":     m4_row.get("coefficient","n/a"),
            "model4_stars":        m4_row.get("stars",""),
        })

    # Contrast comparison
    CONTRAST_PAIRS = [
        ("Weighted Humor Effect (vs non-humorous)", "WHE",  "H1"),
        ("Aggressive − Other humor (weighted avg)", "Aggressive − Other (weighted avg)", "H2-1"),
        ("Aggressive − SELF (se+sd weighted avg)",  "Aggressive − SELF (weighted avg)",  "H2-2"),
        ("Aggressive − Self-Defeating",             "Aggressive − Self-Defeating",        "H2-3_SD"),
    ]
    for m1_lbl, m3_lbl, hyp in CONTRAST_PAIRS:
        m4_row = next((r for r in fs_cont if r.get("contrast")==m1_lbl), {})
        cmp_rows.append({
            "metric":              hyp,
            "model1_simple_ols":   m1_cnt.get(m1_lbl,{}).get("estimate","n/a"),
            "model1_stars":        m1_cnt.get(m1_lbl,{}).get("stars",""),
            "model2_company_dum":  m2_cnt.get(m1_lbl,{}).get("estimate","n/a"),
            "model2_stars":        m2_cnt.get(m1_lbl,{}).get("stars",""),
            "model3_time_dum_ym":  m3_cnt.get(m3_lbl,{}).get("estimate","n/a"),
            "model3_stars":        m3_cnt.get(m3_lbl,{}).get("stars",""),
            "model4_controls":     m4_row.get("estimate","n/a"),
            "model4_stars":        m4_row.get("stars",""),
        })

    # H3 comparison
    h3_fs_beta1 = h3_fs_diag.get("beta1_intensity","n/a")
    h3_fs_stars = h3_fs_diag.get("beta1_stars","")
    h3_fs_supp  = h3_fs_diag.get("H3_supported","n/a")

    def _m3_h3_val(key):
        if M3_H3.exists():
            with open(M3_H3, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("combo")=="year" and "Full_sample" in r.get("sample","Full"):
                        return r.get(key, "n/a")
        return "n/a"

    cmp_rows.append({
        "metric":              "H3_beta1_intensity",
        "model1_simple_ols":   m1_h3.get("beta1_intensity","n/a"),
        "model1_stars":        m1_h3.get("beta1_stars",""),
        "model2_company_dum":  m2_h3.get("beta1_intensity","n/a"),
        "model2_stars":        m2_h3.get("beta1_stars",""),
        "model3_time_dum_ym":  _m3_h3_val("beta1"),
        "model3_stars":        _m3_h3_val("beta1_stars"),
        "model4_controls":     h3_fs_beta1,
        "model4_stars":        h3_fs_stars,
    })
    cmp_rows.append({
        "metric":              "H3_supported",
        "model1_simple_ols":   m1_h3.get("H3_supported","n/a"),
        "model2_company_dum":  m2_h3.get("H3_supported","n/a"),
        "model3_time_dum_ym":  _m3_h3_val("H3_supported"),
        "model4_controls":     h3_fs_supp,
    })

    _write_csv(OUT / "model1_model2_model3_model4_summary_comparison.csv", cmp_rows)

    # ── Interpretation markdown ───────────────────────────────────────────────
    _write_interpretation(
        fs_coef, hc_coef, fs_cont, hc_cont,
        h3_fs_diag, h3_hc_diag,
        fs_vif, h3_fs_vif,
        fs_rank_h1h2, h3_fs_rank,
        n_fs, n_hc, n_hc_dropped, len(fq_rows), len(fq_hc),
    )

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("run_control_variables_v3 COMPLETE")
    print("="*70)
    h1_fs = next((r["support"] for r in fs_cont if r["hypothesis"]=="H1"), "n/a")
    h21_fs = next((r["support"] for r in fs_cont if r["hypothesis"]=="H2-1"), "n/a")
    h22_fs = next((r["support"] for r in fs_cont if r["hypothesis"]=="H2-2"), "n/a")
    print(f"  Full-sample:  H1={h1_fs}  H2-1={h21_fs}  H2-2={h22_fs}")
    print(f"  H3 supported: {h3_fs_diag.get('H3_supported','n/a')}  TP={h3_fs_diag.get('turning_point','n/a')}")
    print(f"  Max VIF (H1/H2 FS): {max((r.get('VIF',0) for r in fs_vif if isinstance(r.get('VIF',0),(int,float))),default='n/a'):.2f}")
    print(f"  Output: {OUT}")


def _write_interpretation(
    fs_coef, hc_coef, fs_cont, hc_cont,
    h3_fs_diag, h3_hc_diag,
    fs_vif, h3_fs_vif,
    fs_rank, h3_fs_rank,
    n_fs, n_hc, n_hc_dropped, n_fq, n_fq_hc,
) -> None:

    def _c(lst, hyp, contrast=None):
        for r in lst:
            if r["hypothesis"]==hyp and (contrast is None or r["contrast"]==contrast):
                return r
        return {}

    h1_f  = _c(fs_cont, "H1")
    h21_f = _c(fs_cont, "H2-1")
    h22_f = _c(fs_cont, "H2-2")
    h1_h  = _c(hc_cont, "H1")

    # VIF table
    vif_table = [f"| {r['variable']:25s} | {r['VIF']:>8} | {r['R2_in_aux']:.4f} |"
                 for r in fs_vif]

    lines = [
        "# Control Variable Model — Interpretation (Model 4)",
        "",
        "> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2)",
        "",
        "## Model specification",
        "",
        "**H1/H2** (post-level):",
        "$$\\log(1+\\text{Eng}_i) = \\beta_0 + \\beta_1\\text{Agg} + "
        "\\beta_2\\text{Aff} + \\beta_3\\text{SE} + \\beta_4\\text{SD}"
        " + \\gamma_1\\text{text\\_length} + \\gamma_2\\text{hashtag} + "
        "\\gamma_3\\text{mention} + \\varepsilon$$",
        "",
        "**H3** (firm-quarter):",
        "$$\\overline{\\log(1+\\text{Eng})}_{fq} = \\alpha + \\beta_1\\text{Intensity} "
        "+ \\beta_2\\text{Intensity}^2 + \\gamma_1\\text{mean\\_tl} + "
        "\\gamma_2\\text{mean\\_ht} + \\gamma_3\\text{mean\\_mn} + "
        "\\gamma_4\\log(1+\\text{posts}) + \\varepsilon$$",
        "",
        f"- Full-sample N = {n_fs:,}  |  HC N = {n_hc:,} (dropped {n_hc_dropped} missing controls)",
        f"- H3 firm-quarters: Full={n_fq:,}  HC={n_fq_hc:,}",
        "- Classical OLS SE. No company dummies. No time dummies. No emoji_count.",
        "",
        "## VIF diagnostics (Full-sample H1/H2)",
        "",
        "| Variable | VIF | R² aux |",
        "|:---------|----:|-------:|",
    ] + vif_table + [
        "",
        f"- Condition number (H1/H2 FS): {fs_rank.get('condition_number','n/a')}",
        f"- Rank deficient: {fs_rank.get('rank_deficient','n/a')}",
        "",
        "## H1: Weighted Humor Effect",
        "",
        f"**Full sample**: estimate={h1_f.get('estimate','n/a')}, "
        f"p={h1_f.get('p_value','n/a')}{h1_f.get('stars','')}  "
        f"→ H1 **{h1_f.get('support','n/a')}**",
        "",
        f"**Human-coded**: estimate={h1_h.get('estimate','n/a')}, "
        f"p={h1_h.get('p_value','n/a')}{h1_h.get('stars','')}  "
        f"→ H1 **{h1_h.get('support','n/a')}**",
        "",
        "## H2-1: Aggressive vs Other humor",
        "",
        f"**Full sample**: {h21_f.get('estimate','n/a')}{h21_f.get('stars','')}  "
        f"→ **{h21_f.get('support','n/a')}**",
        "",
        "## H2-2: Aggressive vs SELF humor",
        "",
        f"**Full sample**: {h22_f.get('estimate','n/a')}{h22_f.get('stars','')}  "
        f"→ **{h22_f.get('support','n/a')}**",
        "",
        "## H2-3 pairwise (full sample)",
        "",
        "| Contrast | estimate | stars | support |",
        "|:---------|--------:|:-----:|:-------:|",
    ]

    for contrast in ["Aggressive − Affiliative","Aggressive − Self-Enhancing","Aggressive − Self-Defeating"]:
        r = _c(fs_cont, "H2-3", contrast)
        lines.append(f"| {contrast} | {r.get('estimate','n/a')} | {r.get('stars','')} | {r.get('support','n/a')} |")

    h3_key = [
        ("H3_supported",      h3_fs_diag.get("H3_supported","n/a")),
        ("beta1_intensity",   f"{h3_fs_diag.get('beta1_intensity','n/a')}{h3_fs_diag.get('beta1_stars','')}"),
        ("beta2_intensity_sq",f"{h3_fs_diag.get('beta2_intensity_sq','n/a')}{h3_fs_diag.get('beta2_stars','')}"),
        ("turning_point",     h3_fs_diag.get("turning_point","n/a")),
        ("obs_range",         f"[{h3_fs_diag.get('obs_intensity_min','n/a')}, {h3_fs_diag.get('obs_intensity_max','n/a')}]"),
        ("tp_in_range",       h3_fs_diag.get("tp_in_obs_range","n/a")),
        ("R²",                h3_fs_diag.get("r_squared","n/a")),
        ("cond_number",       h3_fs_rank.get("condition_number","n/a")),
    ]
    lines += [
        "",
        "## H3 firm-quarter results (Full-sample)",
        "",
        "| Item | Value |",
        "|:----|:------|",
    ] + [f"| {k} | {v} |" for k, v in h3_key] + [
        "",
        "## Interpretation notes",
        "",
        "- **Model 4 vs Model 1**: adds post-level content controls (text_length, hashtag_count, mention_count).",
        "- If H1/H2 estimates change little relative to Model 1, the humor-engagement association is not explained by content format differences.",
        "- Control coefficients for text_length, hashtag_count, mention_count reflect content-format associations with engagement.",
        "- H3 adds firm-quarter mean controls + log(posts), controlling for posting volume and style heterogeneity.",
        "- All results are associations, not causal effects.",
        "",
        "> Model 4 does not replace Models 1–3. It adds robustness checks for content-level confounds.",
    ]
    (OUT / "control_variables_v3_interpretation.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  → control_variables_v3_interpretation.md written")


if __name__ == "__main__":
    main()
