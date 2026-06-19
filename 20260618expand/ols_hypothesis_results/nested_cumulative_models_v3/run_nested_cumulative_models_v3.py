"""
run_nested_cumulative_models_v3.py

Nested cumulative regression table (Table 2 & Table 3).

Model 1: Simple OLS
Model 2: Model 1 + Controls (text_length, hashtag_count, mention_count)
Model 3: Model 2 + Time dummies  (Year+Month for H1/H2;  Year+QoY for H3)
Model 4: Model 3 + Company dummies  (full specification)

H1/H2 equation:
  log(1+Eng_i) = β0 + β1·Agg + β2·Aff + β3·SE + β4·SD
                 [+ γ·controls] [+ Στ·TimeDummy] [+ Σδ·CompanyDummy] + ε

H3 equation:
  Mean log(1+Eng)_{fq} = α + β1·Intensity + β2·Intensity²
                          [+ γ·controls] [+ Στ·TimeDummy] [+ Σδ·CompanyDummy] + ε

Classical OLS SE. No HC3/robust. No emoji_count. No OOF. No firm-month aggregation.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import sys
from datetime import datetime
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from scipy import stats as scipy_stats

ROOT     = Path(__file__).resolve().parents[3]
CI       = ROOT / "20260618expand" / "classifier_improvement"
OUT      = Path(__file__).parent

H2_RR    = CI / "data" / "regression_ready_v3" / "h2_post_level_regression_ready.csv"
TEMPLATE = CI / "data" / "human_labeling_template" / "training_labels_v3_with_coder3_batch2.csv"
V3_CLS   = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification_v3.csv"

TWITTER_FMT = "%a %b %d %H:%M:%S +0000 %Y"
REF_COMPANY = "Amazon"

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def to_f(v, default: float = 0.0) -> float:
    try:    return float(v)
    except: return default

def stars(p: float) -> str:
    if math.isnan(p): return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""

def fmt_cell(b: float, se: float, p: float) -> str:
    return f"{b:+.4f}{stars(p)} ({se:.4f})"

def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        print(f"  → {path.name}  (0 rows)"); return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"  → {path.name}  ({len(rows)} rows)")

# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_full_sample() -> list[dict]:
    rows = []
    with open(H2_RR, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # ensure year/month available for time dummies
            period = r.get("period", "")
            if period and "-" in period:
                y, m = period.split("-", 1)
                r.setdefault("year",  y)
                r.setdefault("month", m)
                r["qoy"] = str((int(m) - 1) // 3 + 1)
            rows.append(r)
    print(f"[FS] N={len(rows):,}")
    return rows


def _extract_sid(url: str) -> str:
    m = re.search(r"/status/(\d+)", str(url))
    return m.group(1) if m else ""


def load_human_coded() -> list[dict]:
    """Three-tier fallback: direct tweet_id → URL status_id → text MD5 hash."""
    cls_by_tid: dict[str, dict]  = {}
    cls_by_hash: dict[str, dict] = {}
    with open(V3_CLS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tid = r["tweet_id"].strip()
            txt = r.get("text", "").strip().lower()
            if tid:
                cls_by_tid[tid] = r
            if txt:
                cls_by_hash[hashlib.md5(txt.encode()).hexdigest()] = r

    def _ctrl(cr: dict) -> dict:
        return {
            "text_length":      cr.get("text_length",   ""),
            "hashtag_count":    cr.get("hashtag_count", ""),
            "mention_count":    cr.get("mention_count", ""),
            "total_engagement": cr.get("total_engagement", "0"),
        }

    VALID = {"0", "1"}
    rows_out: list[dict] = []
    n_d = n_u = n_t = n_m = 0

    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("human_humor_presence", "").strip() not in VALID:
                continue
            pres = r["human_humor_presence"].strip()
            typ  = r.get("human_humor_type", "").strip()
            tid  = r.get("tweet_id", "").strip()
            url  = r.get("tweet_url", "").strip()
            txt  = r.get("text", "").strip().lower()
            ca   = r.get("created_at", "")

            if tid in cls_by_tid:
                ctrl = _ctrl(cls_by_tid[tid]); n_d += 1
            else:
                sid = _extract_sid(url)
                if sid and sid in cls_by_tid:
                    ctrl = _ctrl(cls_by_tid[sid]); n_u += 1
                else:
                    h = hashlib.md5(txt.encode()).hexdigest() if txt else ""
                    if h and h in cls_by_hash:
                        ctrl = _ctrl(cls_by_hash[h]); n_t += 1
                    else:
                        n_m += 1; continue

            # year / month / qoy from created_at
            year_str = month_str = qoy_str = ""
            try:
                dt = datetime.strptime(ca.strip(), TWITTER_FMT)
                year_str  = str(dt.year)
                month_str = f"{dt.month:02d}"
                qoy_str   = str((dt.month - 1) // 3 + 1)
            except Exception:
                pass

            log_eng = math.log1p(to_f(ctrl["total_engagement"]))
            rows_out.append({
                "company_name":         r.get("company_name", ""),
                "log_total_engagement": log_eng,
                "aggressive_humor":     "1" if pres == "1" and typ == "1" else "0",
                "affiliative_humor":    "1" if pres == "1" and typ == "2" else "0",
                "self_enhancing_humor": "1" if pres == "1" and typ == "3" else "0",
                "self_defeating_humor": "1" if pres == "1" and typ == "4" else "0",
                "text_length":          ctrl["text_length"],
                "hashtag_count":        ctrl["hashtag_count"],
                "mention_count":        ctrl["mention_count"],
                "year":                 year_str,
                "month":                month_str,
                "qoy":                  qoy_str,
                "created_at":           ca,
            })

    print(f"[HC] N={len(rows_out):,}  (direct={n_d}, url_sid={n_u}, text_hash={n_t}, miss={n_m})")
    return rows_out

# ─────────────────────────────────────────────────────────────────────────────
# Firm-quarter aggregation
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_fq(rows: list[dict]) -> list[dict]:
    """Aggregate posts to firm-quarter level. Both FS and HC use year/qoy fields."""
    panel: dict = {}
    for r in rows:
        y   = r.get("year",  "")
        qoy = r.get("qoy",   "")
        if not y or not qoy:
            continue
        co   = r.get("company_name", "")
        qlab = f"{y}-Q{qoy}"
        key  = (co, qlab)
        if key not in panel:
            panel[key] = {
                "company": co, "quarter": qlab, "year": y, "qoy": qoy,
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

    out = []
    for p in panel.values():
        n = p["_n"]
        if n == 0: continue
        inten = p["_agg"] / n
        out.append({
            "company":                 p["company"],
            "quarter":                 p["quarter"],
            "year":                    p["year"],
            "qoy":                     p["qoy"],
            "post_count":              n,
            "aggressive_intensity":    round(inten, 12),
            "aggressive_intensity_sq": round(inten * inten, 12),
            "mean_log_engagement":     round(p["_log_sum"] / n, 6),
            "mean_text_length":        round(p["_tl_sum"]  / n, 6),
            "mean_hashtag_count":      round(p["_ht_sum"]  / n, 6),
            "mean_mention_count":      round(p["_mn_sum"]  / n, 6),
            "log_total_posts":         round(math.log1p(n), 6),
        })
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Dummy builders
# ─────────────────────────────────────────────────────────────────────────────

def _cat_dummies(values: list[str], ref: str | None = None) -> tuple[np.ndarray, list[str]]:
    unique = sorted(set(v for v in values if v))
    if ref and ref in unique:
        cats = [c for c in unique if c != ref]
    else:
        ref = unique[0] if unique else None
        cats = unique[1:]
    if not cats:
        return np.zeros((len(values), 0), dtype=np.float64), []
    c2i = {c: i for i, c in enumerate(cats)}
    D = np.zeros((len(values), len(cats)), dtype=np.float64)
    for i, v in enumerate(values):
        if v in c2i: D[i, c2i[v]] = 1.0
    return D, cats


def make_year_month_dummies(rows: list[dict]) -> tuple[np.ndarray, int]:
    years  = [r.get("year",  "") for r in rows]
    months = [r.get("month", "") for r in rows]
    Dy, _ = _cat_dummies(years,  ref=None)   # earliest year = reference
    Dm, _ = _cat_dummies(months, ref=None)   # January = reference
    if Dy.shape[1] and Dm.shape[1]:
        return np.column_stack([Dy, Dm]), Dy.shape[1] + Dm.shape[1]
    if Dy.shape[1]: return Dy, Dy.shape[1]
    return Dm, Dm.shape[1]


def make_year_qoy_dummies(fq_rows: list[dict]) -> tuple[np.ndarray, int]:
    years = [r.get("year", "") for r in fq_rows]
    qoys  = [r.get("qoy",  "") for r in fq_rows]
    Dy, _ = _cat_dummies(years, ref=None)   # earliest year = reference
    Dq, _ = _cat_dummies(qoys,  ref=None)   # Q1 = reference
    if Dy.shape[1] and Dq.shape[1]:
        return np.column_stack([Dy, Dq]), Dy.shape[1] + Dq.shape[1]
    if Dy.shape[1]: return Dy, Dy.shape[1]
    return Dq, Dq.shape[1]


def make_company_dummies(co_list: list[str]) -> tuple[np.ndarray, int]:
    D, cats = _cat_dummies(co_list, ref=REF_COMPANY)
    return D, len(cats)

# ─────────────────────────────────────────────────────────────────────────────
# OLS core (classical SE)
# ─────────────────────────────────────────────────────────────────────────────

def ols_fit(X: np.ndarray, y: np.ndarray):
    n, k = X.shape
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    ssr   = float(resid @ resid)
    df    = n - k
    s2    = ssr / df if df > 0 else float("nan")
    try:
        XtXi = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        XtXi = np.linalg.pinv(X.T @ X)
    V   = s2 * XtXi
    se  = np.sqrt(np.clip(np.diag(V), 0.0, None))
    t_  = b / se
    df_ = max(df, 1)
    p_  = np.array([2.0 * scipy_stats.t.sf(abs(ti), df=df_) for ti in t_])
    sst = float(np.sum((y - float(np.mean(y))) ** 2))
    r2  = 1.0 - ssr / sst if sst > 0 else 0.0
    adj = 1.0 - (1.0 - r2) * (n - 1) / df if df > 0 else 0.0
    rk  = int(np.linalg.matrix_rank(X))
    cn  = float(np.linalg.cond(X))
    return b, V, t_, p_, n, k, r2, adj, df, resid, rk, cn


def contrast_test(c_vec: list[float], b: np.ndarray, V: np.ndarray, df: int):
    c   = np.array(c_vec, dtype=float)
    est = float(c @ b)
    var = float(c @ V @ c)
    se  = math.sqrt(max(var, 0.0))
    if se == 0.0:
        return est, se, float("nan"), float("nan")
    t_ = est / se
    p_ = 2.0 * scipy_stats.t.sf(abs(t_), df=max(df, 1))
    return est, se, float(t_), float(p_)


def run_h1h2_contrasts(b4: np.ndarray, V4: np.ndarray, df: int,
                        n_agg: int, n_aff: int, n_se: int, n_sd: int,
                        label: str) -> list[dict]:
    n_h = n_agg + n_aff + n_se + n_sd
    n_o = n_aff + n_se + n_sd
    n_s = n_se + n_sd

    def w(num, den): return num / den if den else 0.0

    w_agg = w(n_agg, n_h); w_aff = w(n_aff, n_h)
    w_se_ = w(n_se, n_h);  w_sd_ = w(n_sd, n_h)
    w_aff_o = w(n_aff, n_o); w_se_o = w(n_se, n_o); w_sd_o = w(n_sd, n_o)
    w_se_s  = w(n_se, n_s);  w_sd_s = w(n_sd, n_s)

    rows = []

    def _add(hyp: str, contrast: str, c4: list):
        est, se_c, t_c, p_c = contrast_test(c4, b4, V4, df)
        sig = math.isfinite(p_c) and p_c < 0.10
        sup = "supported" if est > 0 and sig else "not_supported"
        rows.append({
            "model": label, "hypothesis": hyp, "contrast": contrast,
            "estimate":    round(est, 6),
            "std_error":   round(se_c, 6),
            "t_stat":      round(t_c, 4) if math.isfinite(t_c) else "NA",
            "p_value":     round(p_c, 6) if math.isfinite(p_c) else "NA",
            "stars":       stars(p_c) if math.isfinite(p_c) else "",
            "direction":   "positive" if est > 0 else "negative",
            "support":     sup,
        })

    _add("H1",   "Weighted Humor Effect (vs non-humorous)", [w_agg, w_aff, w_se_, w_sd_])
    _add("H2-1", "Aggressive − Other humor (weighted avg)", [1, -w_aff_o, -w_se_o, -w_sd_o])
    _add("H2-2", "Aggressive − SELF (se+sd weighted avg)",  [1, 0, -w_se_s, -w_sd_s])
    _add("H2-3", "Aggressive − Affiliative",    [1, -1,  0,  0])
    _add("H2-3", "Aggressive − Self-Enhancing", [1,  0, -1,  0])
    _add("H2-3", "Aggressive − Self-Defeating", [1,  0,  0, -1])
    return rows

# ─────────────────────────────────────────────────────────────────────────────
# VIF
# ─────────────────────────────────────────────────────────────────────────────

def compute_vif(X_focal: np.ndarray, names: list[str]) -> list[dict]:
    n, k = X_focal.shape
    rows = []
    for i, nm in enumerate(names):
        yi   = X_focal[:, i]
        Xo   = np.delete(X_focal, i, axis=1)
        Xo   = np.column_stack([np.ones(n), Xo])
        b_, _, _, _ = np.linalg.lstsq(Xo, yi, rcond=None)
        yhat = Xo @ b_
        ssr  = float(np.sum((yi - yhat) ** 2))
        sst  = float(np.sum((yi - float(np.mean(yi))) ** 2))
        r2   = 1.0 - ssr / sst if sst > 0 else 0.0
        vif  = 1.0 / (1.0 - r2) if r2 < 1.0 else float("inf")
        rows.append({
            "variable": nm,
            "VIF":      round(vif, 4) if math.isfinite(vif) else "Inf",
            "R2_aux":   round(r2, 6),
        })
    return rows

# ─────────────────────────────────────────────────────────────────────────────
# H1/H2 runner
# ─────────────────────────────────────────────────────────────────────────────

def run_h1h2(rows: list[dict], label: str,
             inc_ctrl: bool, inc_time: bool, inc_co: bool) -> dict:
    n    = len(rows)
    y    = np.array([to_f(r["log_total_engagement"]) for r in rows])
    agg  = np.array([to_f(r["aggressive_humor"])     for r in rows])
    aff  = np.array([to_f(r["affiliative_humor"])    for r in rows])
    se_  = np.array([to_f(r["self_enhancing_humor"]) for r in rows])
    sd   = np.array([to_f(r["self_defeating_humor"]) for r in rows])

    X         = np.column_stack([np.ones(n), agg, aff, se_, sd])
    var_names = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]
    k_humor   = 5   # intercept + 4 humor vars

    if inc_ctrl:
        tl = np.array([to_f(r["text_length"])   for r in rows])
        ht = np.array([to_f(r["hashtag_count"])  for r in rows])
        mn = np.array([to_f(r["mention_count"])  for r in rows])
        X = np.column_stack([X, tl, ht, mn])
        var_names += ["text_length", "hashtag_count", "mention_count"]

    k_focal = X.shape[1]   # intercept + humor + controls

    if inc_time:
        T, k_td = make_year_month_dummies(rows)
        X = np.column_stack([X, T])
        var_names += [f"td_ym_{i}" for i in range(k_td)]

    if inc_co:
        D, k_co = make_company_dummies([r.get("company_name", "") for r in rows])
        X = np.column_stack([X, D])
        var_names += [f"co_{i}" for i in range(k_co)]

    b, V, t_, p_, n, k, r2, adj, df, _, rk, cn = ols_fit(X, y)

    n_agg = int(agg.sum()); n_aff = int(aff.sum())
    n_se  = int(se_.sum()); n_sd  = int(sd.sum())

    print(f"  [{label}] N={n:,} k={k} df={df:,} rk={rk} R²={r2:.4f} cond={cn:.2e}")
    for i in range(min(k_focal, len(var_names))):
        print(f"    {var_names[i]:25s} β={float(b[i]):+.4f} p={float(p_[i]):.4f}{stars(float(p_[i]))}")

    # Coefficient rows (focal only: intercept + humor + controls)
    coef_rows = []
    for i in range(k_focal):
        coef_rows.append({
            "model":          label,
            "term":           var_names[i],
            "coefficient":    round(float(b[i]), 6),
            "std_error":      round(math.sqrt(max(float(V[i, i]), 0.0)), 6),
            "t_stat":         round(float(t_[i]), 4),
            "p_value":        round(float(p_[i]), 6),
            "stars":          stars(float(p_[i])),
            "n":              n, "k": k, "df_resid": df,
            "r_squared":      round(r2, 6), "adj_r_squared": round(adj, 6),
            "inc_controls":   inc_ctrl, "inc_time": inc_time, "inc_company": inc_co,
        })

    # Contrast tests use b4 = humor coefficients at positions 1:5
    b4 = b[1:5]; V4 = V[1:5, 1:5]
    cont_rows = run_h1h2_contrasts(b4, V4, df, n_agg, n_aff, n_se, n_sd, label)
    for r in cont_rows:
        r["n"] = n; r["inc_controls"] = inc_ctrl
        r["inc_time"] = inc_time; r["inc_company"] = inc_co

    # VIF for focal variables (no intercept)
    X_focal = X[:, 1:k_focal]
    focal_names = var_names[1:k_focal]
    vif_rows = compute_vif(X_focal, focal_names)
    for vr in vif_rows:
        vr["model"] = label
        vr["inc_controls"] = inc_ctrl; vr["inc_time"] = inc_time; vr["inc_company"] = inc_co

    rank_diag = {
        "type": "H1H2", "model": label,
        "n": n, "k": k, "matrix_rank": rk, "df_resid": df,
        "condition_number": round(cn, 2) if math.isfinite(cn) else "Inf",
        "rank_deficient": str(rk < k),
        "inc_controls": inc_ctrl, "inc_time": inc_time, "inc_company": inc_co,
    }

    return {
        "coef": coef_rows, "contrast": cont_rows, "vif": vif_rows, "rank": rank_diag,
        "b4": b4, "V4": V4, "b": b, "V": V, "df": df, "n": n, "k": k,
        "r2": r2, "adj": adj, "n_agg": n_agg, "n_aff": n_aff, "n_se": n_se, "n_sd": n_sd,
    }

# ─────────────────────────────────────────────────────────────────────────────
# H3 runner
# ─────────────────────────────────────────────────────────────────────────────

def run_h3(fq_rows: list[dict], label: str,
           inc_ctrl: bool, inc_time: bool, inc_co: bool) -> dict | None:
    n = len(fq_rows)
    if n == 0:
        print(f"  [{label}] H3 SKIPPED: 0 firm-quarters"); return None

    y   = np.array([to_f(r["mean_log_engagement"])     for r in fq_rows])
    x1  = np.array([to_f(r["aggressive_intensity"])    for r in fq_rows])
    x2  = np.array([to_f(r["aggressive_intensity_sq"]) for r in fq_rows])

    X         = np.column_stack([np.ones(n), x1, x2])
    var_names = ["intercept", "AggressiveIntensity", "AggressiveIntensity_sq"]

    if inc_ctrl:
        tl = np.array([to_f(r["mean_text_length"])   for r in fq_rows])
        ht = np.array([to_f(r["mean_hashtag_count"])  for r in fq_rows])
        mn = np.array([to_f(r["mean_mention_count"])  for r in fq_rows])
        lp = np.array([to_f(r["log_total_posts"])     for r in fq_rows])
        X = np.column_stack([X, tl, ht, mn, lp])
        var_names += ["mean_text_length", "mean_hashtag_count", "mean_mention_count", "log_total_posts"]

    k_focal = X.shape[1]

    if inc_time:
        T, k_td = make_year_qoy_dummies(fq_rows)
        X = np.column_stack([X, T])
        var_names += [f"td_yq_{i}" for i in range(k_td)]

    if inc_co:
        D, k_co = make_company_dummies([r.get("company", "") for r in fq_rows])
        X = np.column_stack([X, D])
        var_names += [f"co_{i}" for i in range(k_co)]

    b, V, t_, p_, n, k, r2, adj, df, _, rk, cn = ols_fit(X, y)

    if df <= 0:
        print(f"  [{label}] H3 SKIPPED: df={df}"); return None

    beta1 = float(b[1]); beta2 = float(b[2])
    tp    = -beta1 / (2 * beta2) if beta2 != 0 else float("inf")
    obs_min = float(x1.min()); obs_max = float(x1.max())
    in_range = math.isfinite(tp) and obs_min <= tp <= obs_max
    p2   = float(p_[2])
    h3s  = beta1 > 0 and beta2 < 0 and math.isfinite(p2) and p2 < 0.10 and in_range

    print(f"  [{label}] H3 N={n} k={k} df={df} rk={rk} R²={r2:.4f}")
    print(f"    β1={beta1:+.4f}{stars(float(p_[1]))} β2={beta2:+.4f}{stars(p2)} TP={tp:.4f} H3={h3s}")

    coef_rows = []
    for i in range(k_focal):
        coef_rows.append({
            "model":        label, "term": var_names[i],
            "coefficient":  round(float(b[i]), 6),
            "std_error":    round(math.sqrt(max(float(V[i, i]), 0.0)), 6),
            "t_stat":       round(float(t_[i]), 4),
            "p_value":      round(float(p_[i]), 6),
            "stars":        stars(float(p_[i])),
            "n":            n, "k": k, "df_resid": df,
            "r_squared":    round(r2, 6), "adj_r_squared": round(adj, 6),
            "inc_controls": inc_ctrl, "inc_time": inc_time, "inc_company": inc_co,
        })

    diag = {
        "model":            label, "n_fq": n, "k": k, "matrix_rank": rk, "df_resid": df,
        "condition_number": round(cn, 2) if math.isfinite(cn) else "Inf",
        "rank_deficient":   str(rk < k),
        "beta1":      round(beta1, 6), "beta1_se": round(math.sqrt(max(float(V[1, 1]), 0.0)), 6),
        "beta1_t":    round(float(t_[1]), 4), "beta1_p": round(float(p_[1]), 6),
        "beta1_stars": stars(float(p_[1])),
        "beta2":      round(beta2, 6), "beta2_se": round(math.sqrt(max(float(V[2, 2]), 0.0)), 6),
        "beta2_t":    round(float(t_[2]), 4), "beta2_p": round(p2, 6),
        "beta2_stars": stars(p2),
        "turning_point":   round(tp, 6) if math.isfinite(tp) else "Inf",
        "obs_min":         round(obs_min, 6), "obs_max": round(obs_max, 6),
        "tp_in_obs_range": str(in_range), "H3_supported": str(h3s),
        "r_squared":       round(r2, 6), "adj_r_squared": round(adj, 6),
        "inc_controls": inc_ctrl, "inc_time": inc_time, "inc_company": inc_co,
    }

    rank_diag = {
        "type": "H3", "model": label,
        "n": n, "k": k, "matrix_rank": rk, "df_resid": df,
        "condition_number": round(cn, 2) if math.isfinite(cn) else "Inf",
        "rank_deficient": str(rk < k),
        "inc_controls": inc_ctrl, "inc_time": inc_time, "inc_company": inc_co,
    }

    X_focal = X[:, 1:k_focal]
    vif_rows = compute_vif(X_focal, var_names[1:k_focal])
    for vr in vif_rows:
        vr["model"] = label
        vr["inc_controls"] = inc_ctrl; vr["inc_time"] = inc_time; vr["inc_company"] = inc_co

    return {
        "coef": coef_rows, "diag": diag, "rank": rank_diag, "vif": vif_rows,
        "b": b, "V": V, "df": df, "n": n, "k": k, "r2": r2, "adj": adj,
        "h3s": h3s, "tp": tp, "beta1": beta1, "beta2": beta2,
        "obs_min": obs_min, "obs_max": obs_max, "in_range": in_range,
    }

# ─────────────────────────────────────────────────────────────────────────────
# Report table builders
# ─────────────────────────────────────────────────────────────────────────────

MODELS_SPEC = [
    (1, False, False, False),
    (2, True,  False, False),
    (3, True,  True,  False),
    (4, True,  True,  True),
]

FOCAL_TERMS_H1H2 = [
    "aggressive", "affiliative", "self_enhancing", "self_defeating",
    "text_length", "hashtag_count", "mention_count",
]
FOCAL_TERMS_H3 = [
    "AggressiveIntensity", "AggressiveIntensity_sq",
    "mean_text_length", "mean_hashtag_count", "mean_mention_count", "log_total_posts",
]
CONTRAST_ORDER = [
    "Weighted Humor Effect (vs non-humorous)",
    "Aggressive − Other humor (weighted avg)",
    "Aggressive − SELF (se+sd weighted avg)",
    "Aggressive − Affiliative",
    "Aggressive − Self-Enhancing",
    "Aggressive − Self-Defeating",
]


def _col(res_h1h2: dict | None, term: str) -> str:
    if res_h1h2 is None: return "—"
    for r in res_h1h2["coef"]:
        if r["term"] == term:
            se = r["std_error"]
            return fmt_cell(r["coefficient"], se, r["p_value"])
    return "—"


def _col_contrast(res_h1h2: dict | None, contrast: str) -> str:
    if res_h1h2 is None: return "—"
    for r in res_h1h2["contrast"]:
        if r["contrast"] == contrast:
            p_ = float(r["p_value"]) if str(r["p_value"]) != "NA" else float("nan")
            return f"{r['estimate']:+.4f}{r['stars']}"
    return "—"


def _col_h3(res_h3: dict | None, term: str) -> str:
    if res_h3 is None: return "—"
    for r in res_h3["coef"]:
        if r["term"] == term:
            se = r["std_error"]
            return fmt_cell(r["coefficient"], se, r["p_value"])
    return "—"


def build_report_table2(res_h1h2: dict) -> list[dict]:
    """Wide-format Table 2: H1/H2 nested regression results."""
    def _get(sample, m):
        return res_h1h2.get((sample, m))

    rows = []
    samples = [("Full_sample", "FS"), ("Human_coded", "HC")]

    for sample, stag in samples:
        r1 = _get(sample, 1); r2 = _get(sample, 2)
        r3 = _get(sample, 3); r4 = _get(sample, 4)

        # intercept
        rows.append({
            "sample": sample, "variable": "intercept", "type": "coef_se",
            "Model1": _col(r1, "intercept"), "Model2": _col(r2, "intercept"),
            "Model3": _col(r3, "intercept"), "Model4": _col(r4, "intercept"),
        })

        for term in FOCAL_TERMS_H1H2:
            row = {"sample": sample, "variable": term, "type": "coef_se"}
            for m, res in [(1, r1), (2, r2), (3, r3), (4, r4)]:
                # controls not in M1
                if term in ("text_length", "hashtag_count", "mention_count") and m == 1:
                    row[f"Model{m}"] = "—"
                else:
                    row[f"Model{m}"] = _col(res, term)
            rows.append(row)

        rows.append({"sample": sample, "variable": "--- Specification ---", "type": "header"})
        rows.append({"sample": sample, "variable": "Controls", "type": "spec",
                     "Model1": "No", "Model2": "Yes", "Model3": "Yes", "Model4": "Yes"})
        rows.append({"sample": sample, "variable": "Time FE (Year + Month)", "type": "spec",
                     "Model1": "No", "Model2": "No", "Model3": "Yes", "Model4": "Yes"})
        rows.append({"sample": sample, "variable": "Company dummies (ref=Amazon)", "type": "spec",
                     "Model1": "No", "Model2": "No", "Model3": "No", "Model4": "Yes"})

        for res, m in [(r1,1),(r2,2),(r3,3),(r4,4)]:
            n_ = res["n"] if res else "—"
            r2_ = round(res["r2"], 4) if res else "—"
            a2_ = round(res["adj"], 4) if res else "—"
            k_  = res["k"] if res else "—"
            df_ = res["df"] if res else "—"
            for attr, val in [("N", n_), ("k", k_), ("df_residual", df_), ("R_squared", r2_), ("adj_R_squared", a2_)]:
                # accumulate into single row
                pass  # handled below

        def _stat(res, attr):
            if res is None: return "—"
            return {"N": res["n"], "k": res["k"], "df": res["df"],
                    "R2": round(res["r2"],4), "adjR2": round(res["adj"],4)}[attr]

        for attr in ["N", "k", "df", "R2", "adjR2"]:
            rows.append({"sample": sample, "variable": attr, "type": "stat",
                         "Model1": _stat(r1, attr), "Model2": _stat(r2, attr),
                         "Model3": _stat(r3, attr), "Model4": _stat(r4, attr)})

        rows.append({"sample": sample, "variable": "--- Contrasts ---", "type": "header"})
        for cont in CONTRAST_ORDER:
            rows.append({"sample": sample, "variable": cont, "type": "contrast_est",
                         "Model1": _col_contrast(r1, cont),
                         "Model2": _col_contrast(r2, cont),
                         "Model3": _col_contrast(r3, cont),
                         "Model4": _col_contrast(r4, cont)})

        rows.append({"sample": sample, "variable": "--- H2 overall support ---", "type": "header"})
        for res, m in [(r1,1),(r2,2),(r3,3),(r4,4)]:
            h1s = next((r["support"] for r in res["contrast"] if r["hypothesis"]=="H1"), "n/a") if res else "n/a"
            h21 = next((r["support"] for r in res["contrast"] if r["hypothesis"]=="H2-1"), "n/a") if res else "n/a"
            h22 = next((r["support"] for r in res["contrast"] if r["hypothesis"]=="H2-2"), "n/a") if res else "n/a"
            rows.append({"sample": sample, "variable": f"H1_M{m}", "type": "hypothesis_result",
                         f"Model{m}": h1s})
            rows.append({"sample": sample, "variable": f"H2-1_M{m}", "type": "hypothesis_result",
                         f"Model{m}": h21})
            rows.append({"sample": sample, "variable": f"H2-2_M{m}", "type": "hypothesis_result",
                         f"Model{m}": h22})

        # Combined row
        for hyp, key in [("H1","H1"),("H2-1","H2-1"),("H2-2","H2-2")]:
            row = {"sample": sample, "variable": hyp + "_support", "type": "support"}
            for m, res in [(1,r1),(2,r2),(3,r3),(4,r4)]:
                row[f"Model{m}"] = next((r["support"] for r in res["contrast"] if r["hypothesis"]==hyp), "n/a") if res else "n/a"
            rows.append(row)

    return rows


def build_report_table3(res_h3: dict) -> list[dict]:
    """Wide-format Table 3: H3 nested regression results."""
    def _get(sample, m):
        return res_h3.get((sample, m))

    rows = []
    for sample in ("Full_sample", "Human_coded"):
        r1 = _get(sample, 1); r2 = _get(sample, 2)
        r3 = _get(sample, 3); r4 = _get(sample, 4)

        rows.append({"sample": sample, "variable": "intercept", "type": "coef_se",
                     "Model1": _col_h3(r1,"intercept"), "Model2": _col_h3(r2,"intercept"),
                     "Model3": _col_h3(r3,"intercept"), "Model4": _col_h3(r4,"intercept")})

        for term in FOCAL_TERMS_H3:
            row = {"sample": sample, "variable": term, "type": "coef_se"}
            for m, res in [(1,r1),(2,r2),(3,r3),(4,r4)]:
                in_ctrl = term in ("mean_text_length","mean_hashtag_count",
                                   "mean_mention_count","log_total_posts")
                row[f"Model{m}"] = "—" if (in_ctrl and m == 1) else _col_h3(res, term)
            rows.append(row)

        rows.append({"sample": sample, "variable": "--- Specification ---", "type": "header"})
        rows.append({"sample": sample, "variable": "Controls", "type": "spec",
                     "Model1":"No","Model2":"Yes","Model3":"Yes","Model4":"Yes"})
        rows.append({"sample": sample, "variable": "Time FE (Year + QoY)", "type": "spec",
                     "Model1":"No","Model2":"No","Model3":"Yes","Model4":"Yes"})
        rows.append({"sample": sample, "variable": "Company dummies (ref=Amazon)", "type": "spec",
                     "Model1":"No","Model2":"No","Model3":"No","Model4":"Yes"})

        def _stat(res, attr):
            if res is None: return "—"
            return {"N_fq": res["n"], "k": res["k"], "df": res["df"],
                    "R2": round(res["r2"],4), "adjR2": round(res["adj"],4),
                    "TP": round(res["tp"],4) if math.isfinite(res["tp"]) else "Inf",
                    "H3": str(res["h3s"]),
                    "beta1": f"{res['beta1']:+.4f}{stars(res['diag']['beta1_p'])}",
                    "beta2": f"{res['beta2']:+.4f}{stars(res['diag']['beta2_p'])}"}[attr]

        for attr in ["N_fq","k","df","R2","adjR2","TP","H3","beta1","beta2"]:
            rows.append({"sample": sample, "variable": attr, "type": "stat",
                         "Model1": _stat(r1,attr), "Model2": _stat(r2,attr),
                         "Model3": _stat(r3,attr), "Model4": _stat(r4,attr)})

        # H3 support per model
        row = {"sample": sample, "variable": "H3_supported", "type": "support"}
        for m, res in [(1,r1),(2,r2),(3,r3),(4,r4)]:
            row[f"Model{m}"] = str(res["h3s"]) if res else "—"
        rows.append(row)

    return rows

# ─────────────────────────────────────────────────────────────────────────────
# Interpretation
# ─────────────────────────────────────────────────────────────────────────────

def _write_interpretation(res_h1h2: dict, res_h3: dict, n_fs, n_hc, n_fq_fs, n_fq_hc) -> None:
    def _c(res, hyp, contrast=None):
        if res is None: return {}
        for r in res["contrast"]:
            if r["hypothesis"] == hyp and (contrast is None or r["contrast"] == contrast):
                return r
        return {}

    lines = [
        "# Nested Cumulative Models — Interpretation",
        "",
        "> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2 + coder2 batch2 URL fallback)",
        "",
        "## Model structure",
        "",
        "| | Model 1 | Model 2 | Model 3 | Model 4 |",
        "|:---|:---|:---|:---|:---|",
        "| Humor vars | ✓ | ✓ | ✓ | ✓ |",
        "| Controls | — | ✓ | ✓ | ✓ |",
        "| Time FE (Year+Month / Year+QoY) | — | — | ✓ | ✓ |",
        "| Company dummies (ref=Amazon) | — | — | — | ✓ |",
        "",
        f"- H1/H2 Full-sample N = {n_fs:,}  |  HC N = {n_hc:,} (3074 direct + 500 URL-sid recovered)",
        f"- H3 Full-sample firm-quarters = {n_fq_fs:,}  |  HC = {n_fq_hc:,}",
        "",
        "## H1: Weighted Humor Effect (Full-sample)",
        "",
        "| Model | estimate | stars | support |",
        "|:------|--------:|:-----:|:-------:|",
    ]
    for m in range(1, 5):
        r = res_h1h2.get(("Full_sample", m))
        c = _c(r, "H1")
        lines.append(f"| Model {m} | {c.get('estimate','n/a')} | {c.get('stars','')} | {c.get('support','n/a')} |")

    lines += [
        "",
        "## H2-1: Aggressive vs Other humor (Full-sample)",
        "",
        "| Model | estimate | stars | support |",
        "|:------|--------:|:-----:|:-------:|",
    ]
    for m in range(1, 5):
        r = res_h1h2.get(("Full_sample", m))
        c = _c(r, "H2-1")
        lines.append(f"| Model {m} | {c.get('estimate','n/a')} | {c.get('stars','')} | {c.get('support','n/a')} |")

    lines += [
        "",
        "## H2-2: Aggressive vs SELF humor (Full-sample)",
        "",
        "| Model | estimate | stars | support |",
        "|:------|--------:|:-----:|:-------:|",
    ]
    for m in range(1, 5):
        r = res_h1h2.get(("Full_sample", m))
        c = _c(r, "H2-2")
        lines.append(f"| Model {m} | {c.get('estimate','n/a')} | {c.get('stars','')} | {c.get('support','n/a')} |")

    lines += [
        "",
        "## H3: Firm-quarter inverted-U (Full-sample)",
        "",
        "| Model | β₁ | β₂ | TP | H3 |",
        "|:------|---:|---:|---:|:---:|",
    ]
    for m in range(1, 5):
        r = res_h3.get(("Full_sample", m))
        if r:
            d = r["diag"]
            lines.append(f"| Model {m} | {d['beta1']}{d['beta1_stars']} | {d['beta2']}{d['beta2_stars']} | {d['turning_point']} | {d['H3_supported']} |")
        else:
            lines.append(f"| Model {m} | — | — | — | — |")

    lines += [
        "",
        "## H1/H2 Human-coded (Model 4 full spec)",
        "",
    ]
    r4hc = res_h1h2.get(("Human_coded", 4))
    if r4hc:
        for cont in CONTRAST_ORDER[:3]:
            c = _c(r4hc, cont.split(" ")[0] if "H" in cont else "H1", cont)
            # match by contrast label
            c2 = next((r for r in r4hc["contrast"] if r["contrast"]==cont), {})
            lines.append(f"- {cont}: {c2.get('estimate','n/a')}{c2.get('stars','')} ({c2.get('support','n/a')})")

    lines += [
        "",
        "## Notes",
        "",
        "- Model 4 is the full specification. Humor effects in Model 4 are identified from within-firm, within-time variation.",
        "- Controls (text_length, hashtag_count, mention_count) test whether humor-engagement association is confounded by content format.",
        "- Time FE (Year+Month) absorbs platform-wide temporal trends. Year+QoY for H3 firm-quarter.",
        "- Company dummies absorb firm-level heterogeneity (follower size, account characteristics).",
        "- coder2 Batch2 500건: Excel 정밀도 손상으로 tweet_id 직접 매칭 실패 → URL status_id fallback으로 전량 복구.",
        "- All OLS uses classical SE: s² = SSR/(n−k), Var(β̂) = s²(X'X)⁻¹.",
    ]

    (OUT / "nested_cumulative_models_v3_interpretation.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print("  → nested_cumulative_models_v3_interpretation.md written")

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("run_nested_cumulative_models_v3.py")
    print("  Nested cumulative: M1 simple → M2 +ctrl → M3 +time → M4 +company")
    print("=" * 70)
    OUT.mkdir(parents=True, exist_ok=True)

    fs_rows = load_full_sample()
    hc_rows = load_human_coded()

    print("\n[Aggregating] Firm-quarter panels...")
    fs_fq = aggregate_fq(fs_rows)
    hc_fq = aggregate_fq(hc_rows)
    print(f"  FS firm-quarters: {len(fs_fq):,}  HC firm-quarters: {len(hc_fq):,}")

    all_coef = []; all_cont = []; all_h3coef = []
    all_h3diag = []; all_vif = []; all_rank = []

    res_h1h2: dict = {}
    res_h3:   dict = {}

    for sample_name, rows, fq_rows in [
        ("Full_sample", fs_rows, fs_fq),
        ("Human_coded", hc_rows, hc_fq),
    ]:
        for mnum, inc_ctrl, inc_time, inc_co in MODELS_SPEC:
            label = f"M{mnum}_{sample_name}"
            spec  = ("Model1: Simple OLS",
                     "Model2: + Controls",
                     "Model3: + Controls + Time(Year+Month)",
                     "Model4: + Controls + Time + Company dummies")[mnum - 1]

            print(f"\n{'─'*60}")
            print(f"  {spec}  [{sample_name}]")

            # H1/H2
            rh = run_h1h2(rows, label, inc_ctrl, inc_time, inc_co)
            res_h1h2[(sample_name, mnum)] = rh
            all_coef.extend(rh["coef"])
            all_cont.extend(rh["contrast"])
            all_vif.extend(rh["vif"])
            all_rank.append(rh["rank"])

            # H3
            r3 = run_h3(fq_rows, label, inc_ctrl, inc_time, inc_co)
            res_h3[(sample_name, mnum)] = r3
            if r3:
                all_h3coef.extend(r3["coef"])
                all_h3diag.append(r3["diag"])
                all_vif.extend(r3["vif"])
                all_rank.append(r3["rank"])

    # ── Raw result CSVs ────────────────────────────────────────────────────
    print()
    _write_csv(OUT / "nested_table2_h1_h2_results.csv",              all_coef)
    _write_csv(OUT / "nested_table2_h1_h2_contrasts.csv",            all_cont)
    _write_csv(OUT / "nested_table3_h3_results.csv",                  all_h3coef)
    _write_csv(OUT / "nested_table3_h3_quadratic_diagnostics.csv",    all_h3diag)
    _write_csv(OUT / "nested_model_rank_vif_diagnostics.csv",
               [{"category": "vif", **v} for v in all_vif] +
               [{"category": "rank", **r} for r in all_rank])

    # ── Model specification summary ────────────────────────────────────────
    spec_rows = [
        {"model_number": 1, "label": "Model 1: Simple OLS",
         "humor_vars": "Yes", "controls": "No",
         "time_dummies": "No", "company_dummies": "No"},
        {"model_number": 2, "label": "Model 2: + Controls",
         "humor_vars": "Yes", "controls": "Yes (text_length, hashtag_count, mention_count)",
         "time_dummies": "No", "company_dummies": "No"},
        {"model_number": 3, "label": "Model 3: + Controls + Time",
         "humor_vars": "Yes", "controls": "Yes",
         "time_dummies": "H1/H2: Year+Month;  H3: Year+QoY",
         "company_dummies": "No"},
        {"model_number": 4, "label": "Model 4: Full Spec (+ Company dummies)",
         "humor_vars": "Yes", "controls": "Yes",
         "time_dummies": "H1/H2: Year+Month;  H3: Year+QoY",
         "company_dummies": "Yes (98 dummies; ref=Amazon)"},
    ]
    _write_csv(OUT / "nested_model_specification_summary.csv", spec_rows)

    # ── Report-ready tables ───────────────────────────────────────────────
    t2 = build_report_table2(res_h1h2)
    t3 = build_report_table3(res_h3)
    _write_csv(OUT / "nested_table2_ready_for_report.csv", t2)
    _write_csv(OUT / "nested_table3_ready_for_report.csv", t3)

    # ── Interpretation markdown ───────────────────────────────────────────
    _write_interpretation(res_h1h2, res_h3, len(fs_rows), len(hc_rows), len(fs_fq), len(hc_fq))

    # ── Final summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    for sample in ("Full_sample", "Human_coded"):
        for m in range(1, 5):
            rh = res_h1h2.get((sample, m))
            r3 = res_h3.get((sample, m))
            h1s  = next((r["support"] for r in rh["contrast"] if r["hypothesis"]=="H1"),  "n/a") if rh else "—"
            h21s = next((r["support"] for r in rh["contrast"] if r["hypothesis"]=="H2-1"),"n/a") if rh else "—"
            h22s = next((r["support"] for r in rh["contrast"] if r["hypothesis"]=="H2-2"),"n/a") if rh else "—"
            h3s  = r3["h3s"] if r3 else "—"
            tp   = round(r3["tp"], 4) if r3 else "—"
            print(f"  M{m} {sample[:2]}:  H1={h1s}  H2-1={h21s}  H2-2={h22s}  H3={h3s}  TP={tp}")
    print(f"\nOutput: {OUT}")


if __name__ == "__main__":
    main()
