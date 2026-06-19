"""
run_time_dummy_combinations_v3.py

Model 3: Time dummy combination models (v3 classifier, coder3 batch2)

H1/H2: 31 combinations of {Year, Month, Week, Date, Hour} at post-level
H3:    4 combinations of {Year, Qoy, Year+Qoy, Year-Quarter} at firm-quarter level

FWL (Frisch-Waugh-Lovell) + iterative within-group demeaning for efficiency.
All OLS: Classical SE (s²=SSR/(n−k)). No company dummies. No controls.

Output dir: time_dummy_combinations_v3/ (11 files)
"""
from __future__ import annotations

import csv
import itertools
import math
import sys
from collections import defaultdict
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

# v3 simple OLS baseline (Model 1) for comparison
V3_CONTRAST = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h1_h2_contrast_tests.csv"
V3_COEF     = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h1_h2_full_sample_results.csv"
V3_H3       = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h3_quadratic_diagnostics.csv"

# v3 company dummy baseline (Model 2)
CD_CONTRAST = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_company_dummy_v3" / "company_dummy_h1_h2_contrast_tests.csv"
CD_COEF     = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_company_dummy_v3" / "company_dummy_h1_h2_full_sample_results.csv"
CD_H3       = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_company_dummy_v3" / "company_dummy_h3_quadratic_diagnostics.csv"

TWITTER_FMT = "%a %b %d %H:%M:%S +0000 %Y"
TIME_KEYS   = ("year", "month", "week", "date", "hour")

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def to_f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def stars(p: float) -> str:
    if math.isnan(p):  return ""
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
# Group encoding
# ─────────────────────────────────────────────────────────────────────────────

def group_encode(values: list) -> tuple[np.ndarray, int, list]:
    """Encode categorical values to 0-based integer IDs."""
    unique_sorted = sorted(set(v for v in values if v is not None))
    val_to_id = {v: i for i, v in enumerate(unique_sorted)}
    ids = np.array([val_to_id.get(v, -1) for v in values], dtype=np.int32)
    return ids, len(unique_sorted), unique_sorted


# ─────────────────────────────────────────────────────────────────────────────
# Fast iterative within-group demeaning (FWL)
# ─────────────────────────────────────────────────────────────────────────────

def _demean_col(col: np.ndarray, g_ids: np.ndarray, n_g: int) -> np.ndarray:
    """Single within-group demeaning pass for 1-D array."""
    sums   = np.bincount(g_ids, weights=col, minlength=n_g)
    counts = np.bincount(g_ids, minlength=n_g).astype(np.float64)
    means  = np.where(counts > 0, sums / np.maximum(counts, 1.0), 0.0)
    return col - means[g_ids]


def partial_out(mat: np.ndarray,
                group_specs: list[tuple[np.ndarray, int]],
                max_iter: int = 300,
                tol: float = 1e-12) -> np.ndarray:
    """
    Partial out multiple categorical groups from every column of mat (n × k).
    Uses alternating within-group demeaning (Gauss-Seidel projection).
    Single group: exact in 1 iteration. Multiple groups: iterative convergence.
    """
    result = mat.astype(np.float64).copy()
    n_col  = result.shape[1]
    if not group_specs:
        return result

    for it in range(max_iter):
        # Track max change every 5 iterations for convergence
        if it % 5 == 0:
            prev_snapshot = result.copy()

        for g_ids, n_g in group_specs:
            for c in range(n_col):
                result[:, c] = _demean_col(result[:, c], g_ids, n_g)

        if it % 5 == 4:
            delta = float(np.max(np.abs(result - prev_snapshot)))
            if delta < tol:
                break

    return result


# ─────────────────────────────────────────────────────────────────────────────
# k_time estimation (accounts for Date absorbing Year/Month/Week)
# ─────────────────────────────────────────────────────────────────────────────

def compute_k_time(combo: tuple[str, ...],
                   n_lev: dict[str, int]) -> tuple[int, bool, list[str]]:
    """
    Returns (k_time_effective, rank_deficient, absorbed_names).
    Date absorbs Year, Month, Week.
    """
    if "date" in combo:
        absorbed = [nm for nm in combo if nm in ("year", "month", "week")]
        independent = [nm for nm in combo if nm not in ("year","month","week","date")]
        k_time = (n_lev["date"] - 1) + sum(n_lev[nm] - 1 for nm in independent)
        return k_time, len(absorbed) > 0, absorbed
    else:
        k_time = sum(n_lev[nm] - 1 for nm in combo)
        return k_time, False, []


# ─────────────────────────────────────────────────────────────────────────────
# Core FWL OLS
# ─────────────────────────────────────────────────────────────────────────────

def ols_fwl(y: np.ndarray,
            humor4: np.ndarray,
            group_specs: list[tuple[np.ndarray, int]],
            k_time: int,
            n_obs: int | None = None) -> dict | None:
    """
    FWL OLS for H1/H2.
    y: (n,)  humor4: (n, 4) = [agg, aff, se, sd]
    Returns dict with b4, V4, df, SSR, R², etc.
    """
    n = len(y)
    if n_obs is not None and n != n_obs:
        return None

    # Build matrix to partial out: [y, 1, agg, aff, se, sd]
    ones = np.ones(n)
    stacked = np.column_stack([y, ones, humor4])  # (n, 6)

    # Partial out time groups
    M = partial_out(stacked, group_specs)
    M_y  = M[:, 0]
    M_h  = M[:, 2:]   # (n, 4) — residualized humor vars; column 1 (intercept) ~≈0

    # OLS without intercept on residualized
    MtM = M_h.T @ M_h  # (4,4)
    Mty = M_h.T @ M_y  # (4,)
    try:
        b4 = np.linalg.solve(MtM, Mty)
    except np.linalg.LinAlgError:
        b4 = np.linalg.lstsq(M_h, M_y, rcond=None)[0]

    resid = M_y - M_h @ b4
    SSR   = float(resid @ resid)

    k_full = 1 + 4 + k_time
    df = n - k_full
    if df <= 0:
        return None   # infeasible

    s2 = SSR / df
    try:
        MtMi = np.linalg.inv(MtM)
    except np.linalg.LinAlgError:
        MtMi = np.linalg.pinv(MtM)
    V4 = s2 * MtMi

    # R² relative to intercept-only model
    y_mean = float(np.mean(y))
    SST    = float(np.sum((y - y_mean) ** 2))
    R2     = 1.0 - SSR / SST if SST > 0 else 0.0
    adjR2  = 1.0 - (1.0 - R2) * (n - 1) / (n - k_full) if n > k_full else 0.0

    # Approximate intercept (not FWL-exact but reasonable for reporting)
    b0 = y_mean - float(np.mean(humor4, axis=0) @ b4)

    return {"b4": b4, "V4": V4, "b0": b0, "df": df, "k_full": k_full,
            "SSR": SSR, "SST": SST, "R2": R2, "adjR2": adjR2, "n": n}


def ols_fwl_h3(y: np.ndarray,
               x1: np.ndarray,
               x2: np.ndarray,
               group_specs: list[tuple[np.ndarray, int]],
               k_time: int) -> dict | None:
    """
    FWL OLS for H3: y = α + β1·x1 + β2·x2 + time_dummies + ε
    b[0]=β1, b[1]=β2
    """
    n = len(y)
    ones = np.ones(n)
    stacked = np.column_stack([y, ones, x1, x2])  # (n, 4)
    M = partial_out(stacked, group_specs)
    M_y  = M[:, 0]
    M_x  = M[:, 2:]  # (n, 2) = [M_x1, M_x2]

    MtM = M_x.T @ M_x
    Mty = M_x.T @ M_y
    try:
        b2 = np.linalg.solve(MtM, Mty)
    except np.linalg.LinAlgError:
        b2 = np.linalg.lstsq(M_x, M_y, rcond=None)[0]

    resid = M_y - M_x @ b2
    SSR   = float(resid @ resid)
    k_full = 1 + 2 + k_time
    df = n - k_full
    if df <= 0:
        return None

    s2  = SSR / df
    try:
        V2 = s2 * np.linalg.inv(MtM)
    except np.linalg.LinAlgError:
        V2 = s2 * np.linalg.pinv(MtM)

    y_mean = float(np.mean(y))
    SST    = float(np.sum((y - y_mean) ** 2))
    R2     = 1.0 - SSR / SST if SST > 0 else 0.0
    adjR2  = 1.0 - (1.0 - R2) * (n-1) / (n - k_full) if n > k_full else 0.0

    beta1 = float(b2[0])
    beta2 = float(b2[1])
    se1   = math.sqrt(max(float(V2[0, 0]), 0.0))
    se2   = math.sqrt(max(float(V2[1, 1]), 0.0))
    t1    = beta1 / se1 if se1 > 0 else float("nan")
    t2    = beta2 / se2 if se2 > 0 else float("nan")
    p1    = float(2 * scipy_stats.t.sf(abs(t1), df)) if math.isfinite(t1) else float("nan")
    p2    = float(2 * scipy_stats.t.sf(abs(t2), df)) if math.isfinite(t2) else float("nan")

    tp = -beta1 / (2 * beta2) if beta2 != 0.0 else float("inf")
    obs_min, obs_max = float(x1.min()), float(x1.max())
    in_range = math.isfinite(tp) and obs_min <= tp <= obs_max
    h3_sup   = (beta1 > 0 and beta2 < 0 and not math.isnan(p2) and p2 < 0.10 and in_range)

    return {
        "b2": b2, "V2": V2, "df": df, "k_full": k_full,
        "beta1": beta1, "beta2": beta2,
        "se1": se1, "se2": se2, "t1": t1, "t2": t2,
        "p1": p1, "p2": p2,
        "tp": tp, "obs_min": obs_min, "obs_max": obs_max,
        "in_range": in_range, "H3_supported": h3_sup,
        "R2": R2, "adjR2": adjR2, "SSR": SSR, "n": n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Contrast tests
# ─────────────────────────────────────────────────────────────────────────────

def contrast_test(c: list[float], b4: np.ndarray,
                  V4: np.ndarray, df: int) -> tuple:
    c   = np.array(c, dtype=float)
    est = float(c @ b4)
    var = float(c @ V4 @ c)
    se  = math.sqrt(max(var, 0.0))
    if se == 0.0:
        return est, se, float("nan"), float("nan")
    t_stat = est / se
    p_val  = float(2 * scipy_stats.t.sf(abs(t_stat), df))
    return est, se, t_stat, p_val


def run_contrasts(b4: np.ndarray, V4: np.ndarray, df: int,
                  n_agg: int, n_aff: int, n_se: int, n_sd: int,
                  model_label: str, combo_name: str) -> list[dict]:
    n_h = n_agg + n_aff + n_se + n_sd
    n_o = n_aff + n_se + n_sd
    n_s = n_se + n_sd

    w_agg = n_agg / n_h if n_h else 0
    w_aff = n_aff / n_h if n_h else 0
    w_se  = n_se  / n_h if n_h else 0
    w_sd  = n_sd  / n_h if n_h else 0

    w_aff_o = n_aff / n_o if n_o else 0
    w_se_o  = n_se  / n_o if n_o else 0
    w_sd_o  = n_sd  / n_o if n_o else 0
    w_se_s  = n_se  / n_s if n_s else 0
    w_sd_s  = n_sd  / n_s if n_s else 0

    rows = []

    def _add(hyp, label_c, c, direction):
        est, se_c, t_c, p_c = contrast_test(c, b4, V4, df)
        sig = not math.isnan(p_c) and p_c < 0.10
        support = ("supported" if est > 0 and sig else "not_supported") \
                  if direction == "positive_sig" else \
                  ("supported" if est > 0 else "not_supported")
        rows.append({
            "model":      model_label,
            "combo":      combo_name,
            "hypothesis": hyp,
            "contrast":   label_c,
            "estimate":   round(est, 6),
            "std_error":  round(se_c, 6),
            "t_stat":     round(t_c, 4)   if math.isfinite(t_c)  else "NA",
            "p_value":    round(p_c, 6)   if math.isfinite(p_c)  else "NA",
            "stars":      stars(p_c)       if math.isfinite(p_c)  else "",
            "direction":  "positive" if est > 0 else "negative",
            "support":    support,
        })

    _add("H1",   "WHE",                                [w_agg, w_aff, w_se, w_sd],  "positive_sig")
    _add("H2-1", "Aggressive − Other (weighted avg)",  [1,-w_aff_o,-w_se_o,-w_sd_o], "positive_sig")
    _add("H2-2", "Aggressive − SELF (weighted avg)",   [1, 0, -w_se_s, -w_sd_s],     "positive_sig")
    _add("H2-3", "Aggressive − Affiliative",           [1,-1, 0, 0],                  "positive_sig")
    _add("H2-3", "Aggressive − Self-Enhancing",        [1, 0,-1, 0],                  "positive_sig")
    _add("H2-3", "Aggressive − Self-Defeating",        [1, 0, 0,-1],                  "positive_sig")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def parse_created_at(ca: str) -> datetime | None:
    try:
        return datetime.strptime(ca.strip(), TWITTER_FMT)
    except Exception:
        return None


def load_h2_data():
    """Load H2 regression-ready + join created_at for week/date/hour."""
    print("[Loading] v3 classified created_at index...")
    tid_to_ca: dict[str, str] = {}
    with open(V3_CLS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tid_to_ca[r["tweet_id"]] = r.get("created_at", "")

    print("[Loading] H2 regression-ready v3...")
    rows = []
    time_arrays: dict[str, list] = {k: [] for k in TIME_KEYS}
    with open(H2_RR, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
            yr = int(to_f(r["year"], 0))
            mo = int(to_f(r["month"], 0))
            time_arrays["year"].append(yr if yr else None)
            time_arrays["month"].append(mo if mo else None)
            # week / date / hour from created_at
            ca = tid_to_ca.get(r["tweet_id"], "")
            dt = parse_created_at(ca) if ca else None
            if dt:
                time_arrays["week"].append(int(dt.isocalendar()[1]))
                time_arrays["date"].append(dt.strftime("%Y-%m-%d"))
                time_arrays["hour"].append(dt.hour)
            else:
                time_arrays["week"].append(None)
                time_arrays["date"].append(None)
                time_arrays["hour"].append(None)

    # Build encoded group arrays
    encoded: dict[str, tuple[np.ndarray, int, list]] = {}
    for key in TIME_KEYS:
        vals = time_arrays[key]
        non_none = [v for v in vals if v is not None]
        if len(non_none) < len(vals):
            print(f"  Warning: {key} has {len(vals)-len(non_none)} missing values")
        ids, n_g, uniq = group_encode(vals)
        encoded[key] = (ids, n_g, uniq)

    n_lev = {key: encoded[key][1] for key in TIME_KEYS}
    print(f"  N={len(rows):,}  |  year={n_lev['year']}, month={n_lev['month']}, "
          f"week={n_lev['week']}, date={n_lev['date']}, hour={n_lev['hour']}")

    return rows, encoded, n_lev


def load_template_data():
    """Load human-coded template with created_at for time fields."""
    VALID_PRES = {"0", "1"}
    rows_out, time_arrays = [], {k: [] for k in TIME_KEYS}
    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("human_humor_presence", "").strip() not in VALID_PRES:
                continue
            dt = parse_created_at(r.get("created_at", ""))
            pres = r["human_humor_presence"].strip()
            typ  = r.get("human_humor_type", "").strip()
            agg  = "1" if pres=="1" and typ=="1" else "0"
            aff  = "1" if pres=="1" and typ=="2" else "0"
            se_  = "1" if pres=="1" and typ=="3" else "0"
            sd   = "1" if pres=="1" and typ=="4" else "0"
            log_eng = math.log1p(to_f(r.get("total_engagement","0")))
            rows_out.append({
                "log_total_engagement": log_eng,
                "aggressive_humor": agg, "affiliative_humor": aff,
                "self_enhancing_humor": se_, "self_defeating_humor": sd,
            })
            # Time fields
            if dt:
                time_arrays["year"].append(dt.year)
                time_arrays["month"].append(dt.month)
                time_arrays["week"].append(int(dt.isocalendar()[1]))
                time_arrays["date"].append(dt.strftime("%Y-%m-%d"))
                time_arrays["hour"].append(dt.hour)
            else:
                for k in TIME_KEYS:
                    time_arrays[k].append(None)

    encoded: dict[str, tuple[np.ndarray, int, list]] = {}
    for key in TIME_KEYS:
        ids, n_g, uniq = group_encode(time_arrays[key])
        encoded[key] = (ids, n_g, uniq)

    n_lev = {key: encoded[key][1] for key in TIME_KEYS}
    print(f"  HC N={len(rows_out):,}  |  year={n_lev['year']}, "
          f"month={n_lev['month']}, week={n_lev['week']}, date={n_lev['date']}, hour={n_lev['hour']}")
    return rows_out, encoded, n_lev


def aggregate_firm_quarter(rows, year_arr, month_arr):
    """Aggregate post-level rows to firm-quarter panel."""
    panel: dict = {}
    for i, r in enumerate(rows):
        yr  = year_arr[i]
        mo  = month_arr[i]
        if yr is None or mo is None:
            continue
        q   = (int(mo) - 1) // 3 + 1
        key = (r.get("company_name", r.get("company_name", "")),
               f"{int(yr)}-Q{q}")
        if key not in panel:
            panel[key] = {"_n": 0, "_agg": 0, "_log_sum": 0.0,
                          "company": key[0], "quarter": key[1],
                          "year": int(yr), "qoy": q,
                          "year_quarter": f"{int(yr)}-Q{q}"}
        p = panel[key]
        p["_n"]       += 1
        p["_agg"]     += int(to_f(r.get("aggressive_humor", "0")))
        p["_log_sum"] += to_f(r.get("log_total_engagement", "0"))

    fq_rows = []
    for p in panel.values():
        n = p["_n"]
        if n == 0:
            continue
        inten = p["_agg"] / n
        fq_rows.append({
            "company":       p["company"],
            "quarter":       p["quarter"],
            "year":          p["year"],
            "qoy":           p["qoy"],
            "year_quarter":  p["year_quarter"],
            "post_count":    n,
            "aggressive_intensity":    round(inten, 12),
            "aggressive_intensity_sq": round(inten * inten, 12),
            "mean_log_engagement":     round(p["_log_sum"] / n, 6),
        })
    return fq_rows


# ─────────────────────────────────────────────────────────────────────────────
# Combo runners
# ─────────────────────────────────────────────────────────────────────────────

def build_group_specs(combo: tuple[str, ...],
                      encoded: dict[str, tuple]) -> list[tuple[np.ndarray, int]]:
    specs = []
    for key in combo:
        if key in encoded:
            ids, n_g, _ = encoded[key]
            # Mask -1 (missing) as a separate "missing" group
            safe_ids = np.where(ids >= 0, ids, n_g)  # put missing in one extra group
            n_g_safe = n_g + (1 if np.any(ids < 0) else 0)
            specs.append((safe_ids, n_g_safe))
    return specs


def run_h1h2_combo(combo: tuple[str, ...],
                   rows: list[dict],
                   encoded: dict,
                   n_lev: dict,
                   sample_label: str) -> tuple[dict | None, list[dict], dict]:
    """Run single H1/H2 combo. Returns (coef_row, contrast_rows, diag_row)."""
    combo_name = "+".join(combo) if combo else "baseline_no_time"
    k_time, rank_def, absorbed = compute_k_time(combo, n_lev)

    n = len(rows)
    y    = np.array([to_f(r["log_total_engagement"]) for r in rows])
    agg  = np.array([to_f(r["aggressive_humor"])     for r in rows])
    aff  = np.array([to_f(r["affiliative_humor"])    for r in rows])
    se_  = np.array([to_f(r["self_enhancing_humor"]) for r in rows])
    sd   = np.array([to_f(r["self_defeating_humor"]) for r in rows])
    humor4 = np.column_stack([agg, aff, se_, sd])

    n_agg = int(agg.sum()); n_aff = int(aff.sum())
    n_se  = int(se_.sum()); n_sd  = int(sd.sum())

    group_specs = build_group_specs(combo, encoded)

    # Estimate effective time dummy count (before any drops)
    n_time_cols_naive = sum(n_lev[k] - 1 for k in combo if k in n_lev)

    result = ols_fwl(y, humor4, group_specs, k_time)

    diag = {
        "sample":           sample_label,
        "combo":            combo_name,
        "included_dummies": "+".join(combo),
        "n":                n,
        "n_time_cols_before_drop": n_time_cols_naive,
        "n_estimated_params":      (1 + 4 + k_time) if result else "n/a",
        "k_time_effective":        k_time,
        "df_resid":                result["df"] if result else "n/a",
        "rank_deficient":          str(rank_def),
        "absorbed_columns":        "+".join(absorbed) if absorbed else "none",
        "n_absorbed":              len(absorbed) * (sum(n_lev.get(a,1)-1 for a in absorbed) if absorbed else 0),
        "successfully_estimated":  "yes" if result else "no",
        "skip_reason":             ("df_resid<=0 or infeasible" if not result and k_time > 0 else ""),
    }

    if result is None:
        return None, [], diag

    b4 = result["b4"]
    V4 = result["V4"]
    df = result["df"]
    R2 = result["R2"]
    adjR2 = result["adjR2"]

    # SE and t/p for individual humor coefficients
    def _bp(i):
        se_i = math.sqrt(max(float(V4[i, i]), 0.0))
        t_i  = float(b4[i]) / se_i if se_i > 0 else float("nan")
        p_i  = float(2 * scipy_stats.t.sf(abs(t_i), df)) if math.isfinite(t_i) else float("nan")
        return se_i, t_i, p_i

    se_a, t_a, p_a = _bp(0)
    se_f, t_f, p_f = _bp(1)
    se_s, t_s, p_s = _bp(2)
    se_d, t_d, p_d = _bp(3)

    coef_row = {
        "sample":         sample_label,
        "combo":          combo_name,
        "n":              n,
        "k_full":         result["k_full"],
        "df_resid":       df,
        "R2":             round(R2, 6),
        "adjR2":          round(adjR2, 6),
        "b_aggressive":   round(float(b4[0]), 6),
        "se_aggressive":  round(se_a, 6),
        "t_aggressive":   round(t_a, 4) if math.isfinite(t_a) else "NA",
        "p_aggressive":   round(p_a, 6) if math.isfinite(p_a) else "NA",
        "stars_agg":      stars(p_a),
        "b_affiliative":  round(float(b4[1]), 6),
        "se_affiliative": round(se_f, 6),
        "p_affiliative":  round(p_f, 6) if math.isfinite(p_f) else "NA",
        "stars_aff":      stars(p_f),
        "b_self_enhancing":  round(float(b4[2]), 6),
        "se_self_enhancing": round(se_s, 6),
        "p_self_enhancing":  round(p_s, 6) if math.isfinite(p_s) else "NA",
        "stars_se":       stars(p_s),
        "b_self_defeating":  round(float(b4[3]), 6),
        "se_self_defeating": round(se_d, 6),
        "p_self_defeating":  round(p_d, 6) if math.isfinite(p_d) else "NA",
        "stars_sd":       stars(p_d),
        "rank_deficient": str(rank_def),
    }

    contrast_rows = run_contrasts(b4, V4, df, n_agg, n_aff, n_se, n_sd,
                                   sample_label, combo_name)
    return coef_row, contrast_rows, diag


def run_h3_combo(combo: tuple[str, ...],
                 fq_rows: list[dict],
                 fq_encoded: dict,
                 fq_n_lev: dict,
                 sample_label: str) -> tuple[dict | None, dict, dict]:
    """Run single H3 time dummy combo."""
    combo_name = "+".join(combo) if combo else "baseline_no_time"
    k_time, rank_def, absorbed = compute_k_time(combo, fq_n_lev)

    n = len(fq_rows)
    y   = np.array([to_f(r["mean_log_engagement"])    for r in fq_rows])
    x1  = np.array([to_f(r["aggressive_intensity"])   for r in fq_rows])
    x2  = np.array([to_f(r["aggressive_intensity_sq"])for r in fq_rows])
    n_time_cols_naive = sum(fq_n_lev.get(k, 1) - 1 for k in combo if k in fq_n_lev)

    group_specs = build_group_specs(combo, fq_encoded)
    result = ols_fwl_h3(y, x1, x2, group_specs, k_time)

    diag = {
        "sample":           sample_label,
        "combo":            combo_name,
        "n_firm_quarters":  n,
        "k_time_effective": k_time,
        "df_resid":         result["df"] if result else "n/a",
        "rank_deficient":   str(rank_def),
        "beta1":            round(result["beta1"], 6) if result else "n/a",
        "beta1_se":         round(result["se1"], 6)   if result else "n/a",
        "beta1_t":          round(result["t1"], 4)    if result else "n/a",
        "beta1_p":          round(result["p1"], 6)    if result else "n/a",
        "beta1_stars":      stars(result["p1"])        if result else "",
        "beta2":            round(result["beta2"], 6) if result else "n/a",
        "beta2_se":         round(result["se2"], 6)   if result else "n/a",
        "beta2_t":          round(result["t2"], 4)    if result else "n/a",
        "beta2_p":          round(result["p2"], 6)    if result else "n/a",
        "beta2_stars":      stars(result["p2"])        if result else "",
        "turning_point":    (round(result["tp"], 6) if math.isfinite(result["tp"]) else "Inf")
                             if result else "n/a",
        "obs_intensity_min": round(result["obs_min"], 6) if result else "n/a",
        "obs_intensity_max": round(result["obs_max"], 6) if result else "n/a",
        "tp_in_obs_range":  str(result["in_range"])  if result else "n/a",
        "H3_supported":     str(result["H3_supported"]) if result else "n/a",
        "R2":               round(result["R2"], 6)    if result else "n/a",
        "adjR2":            round(result["adjR2"], 6) if result else "n/a",
        "successfully_estimated": "yes" if result else "no",
    }

    coef_row = None
    if result:
        coef_row = {
            "sample": sample_label, "combo": combo_name,
            "n": n, "k_full": result["k_full"], "df_resid": result["df"],
            "beta1_intensity":    round(result["beta1"], 6),
            "beta1_se":          round(result["se1"], 6),
            "beta1_stars":       stars(result["p1"]),
            "beta2_intensity_sq": round(result["beta2"], 6),
            "beta2_se":          round(result["se2"], 6),
            "beta2_stars":       stars(result["p2"]),
            "turning_point":     (round(result["tp"], 6) if math.isfinite(result["tp"]) else "Inf"),
            "H3_supported":      str(result["H3_supported"]),
            "R2":                round(result["R2"], 6),
            "adjR2":             round(result["adjR2"], 6),
        }

    return coef_row, diag, diag   # coef_row, H3_diag, rank_diag


# ─────────────────────────────────────────────────────────────────────────────
# Load v3 baselines for comparison
# ─────────────────────────────────────────────────────────────────────────────

def load_baselines():
    def _read_fs(path, key_col, val_cols, model_filter="Full_sample"):
        """Load only Full_sample rows (or first matching model_filter) keyed by key_col."""
        out = {}
        if not path.exists():
            return out
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if model_filter and not r.get("model", "").startswith(model_filter):
                    continue
                k = r.get(key_col, "")
                if k and k not in out:   # keep first occurrence per key
                    out[k] = {c: r.get(c, "n/a") for c in val_cols}
        return out

    v3_contrast = _read_fs(V3_CONTRAST, "contrast",
                            ["estimate", "p_value", "stars", "support"])
    v3_coef     = _read_fs(V3_COEF, "term",
                            ["coefficient", "p_value", "stars"])
    cd_contrast = _read_fs(CD_CONTRAST, "contrast",
                            ["estimate", "p_value", "stars", "support"],
                            model_filter="Full_sample_CD")
    cd_coef     = _read_fs(CD_COEF, "term",
                            ["coefficient", "p_value", "stars"],
                            model_filter="Full_sample_CD")

    # H3 baselines
    v3_h3, cd_h3 = {}, {}
    if V3_H3.exists():
        with open(V3_H3, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if "Full_sample" in r.get("model", ""):
                    v3_h3 = r
                    break
    if CD_H3.exists():
        with open(CD_H3, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if "Full_sample" in r.get("model", ""):
                    cd_h3 = r
                    break

    return v3_contrast, v3_coef, cd_contrast, cd_coef, v3_h3, cd_h3


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("run_time_dummy_combinations_v3.py")
    print("  Model 3: Time dummy combination models")
    print("  FWL with iterative demeaning. Classical OLS SE.")
    print("=" * 70)
    OUT.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    h2_rows, h2_enc, h2_nlev = load_h2_data()

    # Extract year/month as int arrays for H3 aggregation
    yr_arr = np.array([h2_enc["year"][0][i] for i in range(len(h2_rows))], dtype=object)
    mo_arr = np.array([h2_enc["month"][0][i] for i in range(len(h2_rows))], dtype=object)
    # Build back actual year/month values from encoded IDs
    yr_vals = [h2_enc["year"][2][h2_enc["year"][0][i]] if h2_enc["year"][0][i] >= 0 else None
               for i in range(len(h2_rows))]
    mo_vals = [h2_enc["month"][2][h2_enc["month"][0][i]] if h2_enc["month"][0][i] >= 0 else None
               for i in range(len(h2_rows))]

    print("\n[Loading] Human-coded template...")
    hc_rows, hc_enc, hc_nlev = load_template_data()
    hc_yr_vals = [hc_enc["year"][2][hc_enc["year"][0][i]] if hc_enc["year"][0][i] >= 0 else None
                  for i in range(len(hc_rows))]
    hc_mo_vals = [hc_enc["month"][2][hc_enc["month"][0][i]] if hc_enc["month"][0][i] >= 0 else None
                  for i in range(len(hc_rows))]

    print("\n[Aggregating] H3 firm-quarter...")
    fq_rows = aggregate_firm_quarter(h2_rows, yr_vals, mo_vals)
    fq_hc   = aggregate_firm_quarter(hc_rows, hc_yr_vals, hc_mo_vals)
    print(f"  H3 full-sample firm-quarters: {len(fq_rows):,}")
    print(f"  H3 human-coded firm-quarters: {len(fq_hc):,}")

    # Encode H3 time fields
    def encode_fq(rows):
        enc = {}
        for key in ("year", "qoy", "year_quarter"):
            vals = [r[key] for r in rows]
            ids, n_g, uniq = group_encode(vals)
            enc[key] = (ids, n_g, uniq)
        return enc, {k: enc[k][1] for k in enc}

    fq_enc, fq_nlev = encode_fq(fq_rows)
    fq_hc_enc, fq_hc_nlev = encode_fq(fq_hc)

    # ── Define combinations ───────────────────────────────────────────────────
    H1H2_COMBOS = []
    for r in range(1, 6):
        for combo in itertools.combinations(TIME_KEYS, r):
            H1H2_COMBOS.append(combo)

    H3_COMBOS = [
        ("year",),
        ("qoy",),
        ("year", "qoy"),
        ("year_quarter",),
    ]

    print(f"\n  H1/H2 combos: {len(H1H2_COMBOS)}  |  H3 combos: {len(H3_COMBOS)}")

    # ── Run H1/H2 full-sample ────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H1/H2 Full-sample (31 combinations)")
    print("─" * 60)
    fs_coef_rows, fs_contrast_rows, fs_rank_rows = [], [], []

    for combo in H1H2_COMBOS:
        cname = "+".join(combo)
        print(f"  [{cname}] ...", end="", flush=True)
        coef_row, contrast_list, diag = run_h1h2_combo(
            combo, h2_rows, h2_enc, h2_nlev, "Full_sample")
        if coef_row:
            fs_coef_rows.append(coef_row)
            fs_contrast_rows.extend(contrast_list)
            h1_sup = next((r["support"] for r in contrast_list if r["hypothesis"]=="H1"), "?")
            h21_sup= next((r["support"] for r in contrast_list if r["hypothesis"]=="H2-1"), "?")
            print(f"  df={diag.get('df_resid','?')}  H1={h1_sup}  H2-1={h21_sup}")
        else:
            print(f"  SKIPPED (df={diag.get('df_resid','?')}, rank_def={diag.get('rank_deficient','?')})")
        fs_rank_rows.append({**diag, "model_type": "H1H2_Full"})

    # ── Run H1/H2 human-coded ────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H1/H2 Human-coded (31 combinations)")
    print("─" * 60)
    hc_coef_rows, hc_contrast_rows, hc_rank_rows = [], [], []

    for combo in H1H2_COMBOS:
        cname = "+".join(combo)
        print(f"  [{cname}] ...", end="", flush=True)
        coef_row, contrast_list, diag = run_h1h2_combo(
            combo, hc_rows, hc_enc, hc_nlev, "Human_coded")
        if coef_row:
            hc_coef_rows.append(coef_row)
            hc_contrast_rows.extend(contrast_list)
            h1_sup = next((r["support"] for r in contrast_list if r["hypothesis"]=="H1"), "?")
            print(f"  df={diag.get('df_resid','?')}  H1={h1_sup}")
        else:
            print(f"  SKIPPED")
        hc_rank_rows.append({**diag, "model_type": "H1H2_HC"})

    # ── Run H3 full-sample ───────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H3 Full-sample firm-quarter (4 combinations)")
    print("─" * 60)
    h3_fs_coef, h3_fs_diag, h3_fs_rank = [], [], []

    for combo in H3_COMBOS:
        cname = "+".join(combo)
        print(f"  [{cname}] ...", end="", flush=True)
        coef_row, diag, rank_d = run_h3_combo(
            combo, fq_rows, fq_enc, fq_nlev, "Full_sample")
        if coef_row:
            h3_fs_coef.append(coef_row)
            print(f"  β1={diag['beta1']}{diag['beta1_stars']}  β2={diag['beta2']}{diag['beta2_stars']}"
                  f"  TP={diag['turning_point']}  H3={diag['H3_supported']}")
        else:
            print("  SKIPPED")
        h3_fs_diag.append(diag)
        h3_fs_rank.append({**rank_d, "model_type": "H3_Full"})

    # ── Run H3 human-coded ───────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H3 Human-coded firm-quarter (4 combinations)")
    print("─" * 60)
    h3_hc_coef, h3_hc_diag, h3_hc_rank = [], [], []

    for combo in H3_COMBOS:
        cname = "+".join(combo)
        print(f"  [{cname}] ...", end="", flush=True)
        coef_row, diag, rank_d = run_h3_combo(
            combo, fq_hc, fq_hc_enc, fq_hc_nlev, "Human_coded")
        if coef_row:
            h3_hc_coef.append(coef_row)
            print(f"  β1={diag['beta1']}{diag['beta1_stars']}  β2={diag['beta2']}{diag['beta2_stars']}"
                  f"  H3={diag['H3_supported']}")
        else:
            print("  SKIPPED")
        h3_hc_diag.append(diag)
        h3_hc_rank.append({**rank_d, "model_type": "H3_HC"})

    # ── Write output files ────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("Writing output files")
    print("─" * 60)

    # 1. Inventory (all combos)
    inv_rows = []
    for combo in H1H2_COMBOS:
        cname = "+".join(combo)
        k_t, rd, ab = compute_k_time(combo, h2_nlev)
        inv_rows.append({
            "analysis": "H1H2",
            "combo": cname,
            "included_dummies": "+".join(combo),
            "n_groups": len(combo),
            "k_time_effective": k_t,
            "rank_deficient": str(rd),
            "absorbed": "+".join(ab) if ab else "none",
        })
    for combo in H3_COMBOS:
        cname = "+".join(combo)
        k_t, rd, ab = compute_k_time(combo, fq_nlev)
        inv_rows.append({
            "analysis": "H3",
            "combo": cname,
            "included_dummies": "+".join(combo),
            "n_groups": len(combo),
            "k_time_effective": k_t,
            "rank_deficient": str(rd),
            "absorbed": "+".join(ab) if ab else "none",
        })
    _write_csv(OUT / "time_dummy_model_inventory.csv", inv_rows)

    # 2–3. H1/H2 coefficient results
    _write_csv(OUT / "time_dummy_h1_h2_full_sample_results.csv", fs_coef_rows)
    _write_csv(OUT / "time_dummy_h1_h2_human_coded_results.csv", hc_coef_rows)

    # 4. Contrast tests (combined full+HC)
    _write_csv(OUT / "time_dummy_h1_h2_contrast_tests.csv",
               fs_contrast_rows + hc_contrast_rows)

    # 5–6. H3 results
    _write_csv(OUT / "time_dummy_h3_full_sample_results.csv", h3_fs_coef)
    _write_csv(OUT / "time_dummy_h3_human_coded_results.csv", h3_hc_coef)

    # 7. H3 diagnostics (combined)
    _write_csv(OUT / "time_dummy_h3_quadratic_diagnostics.csv",
               h3_fs_diag + h3_hc_diag)

    # 8. Rank diagnostics (all models)
    all_rank = fs_rank_rows + hc_rank_rows + h3_fs_rank + h3_hc_rank
    _write_csv(OUT / "time_dummy_rank_diagnostics.csv", all_rank)

    # 9. Three-model summary comparison
    v3_contrast, v3_coef, cd_contrast, cd_coef, v3_h3, cd_h3 = load_baselines()

    # Pick representative time dummy combos for comparison
    rep_combos = ["year", "month", "year+month",
                  "year+month+week", "year+month+week+hour",
                  "year+month+week+date+hour"]
    MAIN_CONTRASTS = ["WHE", "Aggressive − Other (weighted avg)",
                      "Aggressive − SELF (weighted avg)"]

    cmp_rows = []
    _STARS_KEY = {
        "aggressive":    "stars_agg",
        "affiliative":   "stars_aff",
        "self_enhancing":"stars_se",
        "self_defeating":"stars_sd",
    }
    # Header rows: base term comparisons
    for term in ["aggressive", "affiliative", "self_enhancing", "self_defeating"]:
        v3r = v3_coef.get(term, {})
        cdr = cd_coef.get(term, {})
        base_row = {
            "hypothesis":  "coef_" + term,
            "model1_simple_ols_est":   v3r.get("coefficient", "n/a"),
            "model1_simple_ols_stars": v3r.get("stars", ""),
            "model2_company_dummy_est":  cdr.get("coefficient", "n/a"),
            "model2_company_dummy_stars": cdr.get("stars", ""),
        }
        for rc in rep_combos:
            fr = next((r for r in fs_coef_rows if r.get("combo") == rc), {})
            base_row[f"m3_{rc}_est"]   = fr.get(f"b_{term}", "n/a")
            base_row[f"m3_{rc}_stars"] = fr.get(_STARS_KEY.get(term, ""), "")
        cmp_rows.append(base_row)

    # Contrast comparison
    # (Model3 label, baseline Model1/2 label, hyp key)
    CONTRAST_MAP = [
        ("WHE",
         "Weighted Humor Effect (vs non-humorous)", "H1"),
        ("Aggressive − Other (weighted avg)",
         "Aggressive − Other humor (weighted avg)", "H2-1"),
        ("Aggressive − SELF (weighted avg)",
         "Aggressive − SELF (se+sd weighted avg)", "H2-2"),
    ]
    for m3_lbl, baseline_lbl, hyp_label in CONTRAST_MAP:
        v3r = v3_contrast.get(baseline_lbl, {})
        cdr = cd_contrast.get(baseline_lbl, {})
        base_row = {
            "hypothesis":  hyp_label,
            "model1_simple_ols_est":    v3r.get("estimate", "n/a"),
            "model1_simple_ols_stars":  v3r.get("stars", ""),
            "model2_company_dummy_est": cdr.get("estimate", "n/a"),
            "model2_company_dummy_stars": cdr.get("stars", ""),
        }
        for rc in rep_combos:
            fr = next((r for r in fs_contrast_rows
                       if r.get("combo")==rc and r.get("contrast")==m3_lbl), {})
            base_row[f"m3_{rc}_est"]   = fr.get("estimate", "n/a")
            base_row[f"m3_{rc}_stars"] = fr.get("stars", "")
        cmp_rows.append(base_row)

    # H3 comparison (using actual H3 combos)
    H3_REP_COMBOS = ("year", "qoy", "year+qoy", "year_quarter")
    base_row = {
        "hypothesis":  "H3_beta1_intensity",
        "model1_simple_ols_est":    v3_h3.get("beta1_intensity", "n/a"),
        "model1_simple_ols_stars":  v3_h3.get("beta1_stars", ""),
        "model2_company_dummy_est": cd_h3.get("beta1_intensity", "n/a"),
        "model2_company_dummy_stars": cd_h3.get("beta1_stars", ""),
    }
    for rc in H3_REP_COMBOS:
        fr = next((r for r in h3_fs_diag if r.get("combo")==rc), {})
        base_row[f"m3_h3_{rc}_est"]   = fr.get("beta1", "n/a")
        base_row[f"m3_h3_{rc}_stars"] = fr.get("beta1_stars", "")
    cmp_rows.append(base_row)

    base_row2 = {
        "hypothesis":  "H3_supported",
        "model1_simple_ols_est":    v3_h3.get("H3_supported", "n/a"),
        "model2_company_dummy_est": cd_h3.get("H3_supported", "n/a"),
    }
    for rc in H3_REP_COMBOS:
        fr_h3 = next((r for r in h3_fs_diag if r.get("combo")==rc), {})
        base_row2[f"m3_h3_{rc}_est"] = fr_h3.get("H3_supported", "n/a")
    cmp_rows.append(base_row2)

    _write_csv(OUT / "model1_model2_model3_summary_comparison.csv", cmp_rows)

    # 10. Interpretation markdown
    _write_interpretation(
        fs_coef_rows, hc_coef_rows,
        fs_contrast_rows, hc_contrast_rows,
        h3_fs_diag, h3_hc_diag,
        fs_rank_rows, hc_rank_rows,
        h2_nlev, fq_nlev,
        len(h2_rows), len(hc_rows), len(fq_rows),
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    n_succ_fs = len(fs_coef_rows)
    n_skip_fs = 31 - n_succ_fs
    n_succ_hc = len(hc_coef_rows)
    n_rank_def_fs = sum(1 for r in fs_rank_rows if r.get("rank_deficient")=="True")

    h1_all_fs = all(
        next((r["support"] for r in fs_contrast_rows
              if r["combo"]==cr["combo"] and r["hypothesis"]=="H1"), "not_supported")
        == "supported"
        for cr in fs_coef_rows
    )

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"  H1/H2 full-sample:  {n_succ_fs} succeeded / {n_skip_fs} skipped")
    print(f"  H1/H2 human-coded:  {n_succ_hc} succeeded")
    print(f"  Rank-deficient:     {n_rank_def_fs} (full-sample)")
    print(f"  H1 consistent across all FS combos: {h1_all_fs}")
    print(f"\n  Output dir: {OUT}")


def _write_interpretation(
    fs_coef, hc_coef, fs_cont, hc_cont,
    h3_fs_diag, h3_hc_diag,
    fs_rank, hc_rank,
    h2_nlev, fq_nlev,
    n_full, n_hc, n_fq,
) -> None:
    from scipy import stats as _stats

    def _h1_support(cont_rows, sample, combo):
        r = next((r for r in cont_rows
                  if r["model"]==sample and r["combo"]==combo and r["hypothesis"]=="H1"), {})
        return r.get("support", "n/a"), r.get("estimate","n/a"), r.get("stars","")

    def _h21_support(cont_rows, sample, combo):
        r = next((r for r in cont_rows
                  if r["model"]==sample and r["combo"]==combo and r["hypothesis"]=="H2-1"), {})
        return r.get("support", "n/a"), r.get("estimate","n/a"), r.get("stars","")

    def _h22_support(cont_rows, sample, combo):
        r = next((r for r in cont_rows
                  if r["model"]==sample and r["combo"]==combo and r["hypothesis"]=="H2-2"), {})
        return r.get("support", "n/a"), r.get("estimate","n/a"), r.get("stars","")

    # Summarize H1 across combos
    h1_summary = {}
    for cr in fs_coef:
        s, e, st = _h1_support(fs_cont, "Full_sample", cr["combo"])
        h1_summary[cr["combo"]] = (s, e, st)

    n_h1_supp = sum(1 for v in h1_summary.values() if v[0]=="supported")
    n_h21_supp = sum(
        1 for cr in fs_coef
        if _h21_support(fs_cont, "Full_sample", cr["combo"])[0]=="supported"
    )
    n_h22_supp = sum(
        1 for cr in fs_coef
        if _h22_support(fs_cont, "Full_sample", cr["combo"])[0]=="supported"
    )
    n_succ = len(fs_coef)

    h3_sup_combos = [r["combo"] for r in h3_fs_diag if str(r.get("H3_supported",""))=="True"]
    h3_not_combos = [r["combo"] for r in h3_fs_diag if str(r.get("H3_supported",""))=="False"]

    # Representative combos for table
    table_combos = [c["combo"] for c in fs_coef
                    if c["combo"] in ("year","month","week","hour",
                                       "year+month","year+month+week",
                                       "year+month+week+hour",
                                       "year+month+week+date+hour")]

    lines = [
        "# Time Dummy Combination Models — Interpretation (Model 3)",
        "",
        f"> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2)",
        "",
        "## Model specification",
        "",
        "$$\\log(1+\\text{Engagement}_i) = \\beta_0 + \\beta_1\\text{Agg}_i + "
        "\\beta_2\\text{Aff}_i + \\beta_3\\text{SE}_i + \\beta_4\\text{SD}_i"
        "+ \\sum_t \\tau_t\\text{TimeDummy}_{it} + \\varepsilon_i$$",
        "",
        "- FWL (Frisch-Waugh-Lovell) + iterative within-group demeaning",
        "- Classical OLS SE: s²=SSR/(n−k). No company dummies. No controls.",
        f"- Post-level N = {n_full:,}  |  HC N = {n_hc:,}  |  Firm-quarter N = {n_fq:,}",
        f"- Time fields: year (L={h2_nlev.get('year','?')}), month (L=12), "
        f"week (L=53), date (L={h2_nlev.get('date','?')}), hour (L=24)",
        "",
        "## Execution summary",
        "",
        f"| Item | Count |",
        "|:----|------:|",
        f"| H1/H2 combos attempted | 31 |",
        f"| H1/H2 full-sample succeeded | {n_succ} |",
        f"| H1/H2 skipped (infeasible) | {31-n_succ} |",
        f"| H3 combos | 4 |",
        f"| Rank-deficient combos (Date+Year/Month/Week) | "
        f"{sum(1 for r in fs_rank if r.get('rank_deficient')=='True')} |",
        "",
        "## H1 consistency across time dummy combinations",
        "",
        f"**H1 supported in {n_h1_supp} / {n_succ} full-sample combinations**",
        "",
        "| Combo | H1 support | estimate | stars |",
        "|:------|:----------:|--------:|:-----:|",
    ]
    for cr in fs_coef[:15]:  # first 15 for brevity
        s, e, st = h1_summary.get(cr["combo"], ("n/a","n/a",""))
        lines.append(f"| {cr['combo']} | {s} | {e} | {st} |")
    if len(fs_coef) > 15:
        lines.append(f"| *(+{len(fs_coef)-15} more — see CSV)* | | | |")

    lines += [
        "",
        "## H2-1 consistency (Aggressive vs Other humor weighted avg)",
        "",
        f"**H2-1 supported in {n_h21_supp} / {n_succ} full-sample combinations**",
        "",
        "## H2-2 consistency (Aggressive vs SELF humor weighted avg)",
        "",
        f"**H2-2 supported in {n_h22_supp} / {n_succ} full-sample combinations**",
        "",
        "## H2-3 pairwise: self-defeating exception",
        "",
        "The Aggressive − Self-Defeating contrast across time dummy combinations:",
    ]

    sd_rows = [r for r in fs_cont if r.get("contrast")=="Aggressive − Self-Defeating"]
    n_sd_neg = sum(1 for r in sd_rows if r.get("direction")=="negative")
    n_sd_sig = sum(1 for r in sd_rows
                   if r.get("stars","") != "" and r.get("direction")=="negative")
    lines += [
        f"- Negative direction (Agg < SD): {n_sd_neg} / {len(sd_rows)} combos",
        f"- Significantly negative (p<.10): {n_sd_sig} / {len(sd_rows)} combos",
        "",
        "## H3 firm-quarter time dummy results",
        "",
        "| Combo | β₁ | β₁ stars | β₂ | β₂ stars | TP | H3 supported |",
        "|:------|---:|:--------:|---:|:--------:|---:|:------------:|",
    ]
    for r in h3_fs_diag:
        lines.append(
            f"| {r.get('combo','?')} | {r.get('beta1','n/a')} | {r.get('beta1_stars','')} | "
            f"{r.get('beta2','n/a')} | {r.get('beta2_stars','')} | "
            f"{r.get('turning_point','n/a')} | {r.get('H3_supported','n/a')} |"
        )
    lines += [
        "",
        f"H3 supported combos: {', '.join(h3_sup_combos) if h3_sup_combos else 'none'}",
        f"H3 not supported: {', '.join(h3_not_combos) if h3_not_combos else 'none'}",
        "",
        "## Three-model comparison (H1)",
        "",
        "| Model | H1 estimate | H1 stars |",
        "|:------|:-----------:|:--------:|",
    ]
    # Model 1 reference
    lines.append("| Model 1 Simple OLS | see comparison CSV | |")
    lines.append("| Model 2 Company Dummy | see comparison CSV | |")
    n_h1_supp_td = n_h1_supp
    lines.append(f"| Model 3 Time Dummy (all combos) | supported {n_h1_supp_td}/{n_succ} | |")
    lines += [
        "",
        "## Rank deficiency notes",
        "",
        "Date dummy absorbs Year, Month, Week (since each date uniquely determines year/month/week).",
        "Combinations with Date+Year, Date+Month, Date+Week are rank-deficient.",
        "Effective k_time for these cases uses only Date dimensions (plus Hour if present).",
        "Results from these combinations are valid for the identifiable (Date+Hour) structure.",
        "",
        "## Interpretation",
        "",
        "Model 3 tests whether the H1/H2/H3 associations are robust to time controls.",
        "",
        "- If H1 is supported across ALL time dummy combinations: "
        "the humor-engagement association is not driven by temporal confounds (posting seasons, years).",
        "- If H3 collapses under Year/Quarter controls: "
        "the inverted-U (or U-shaped) pattern in Model 2 may be a time-specific confound rather than a true dose-response effect.",
        "- All results are associations, not causal effects.",
        "",
        "> Model 3 does not replace Model 1 (Simple OLS) or Model 2 (Company Dummy).",
        "> It provides robustness checks against temporal confounding.",
    ]
    (OUT / "time_dummy_combinations_v3_interpretation.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"  → time_dummy_combinations_v3_interpretation.md written")


if __name__ == "__main__":
    main()
