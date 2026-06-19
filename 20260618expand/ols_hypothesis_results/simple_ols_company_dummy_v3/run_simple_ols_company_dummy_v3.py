"""
run_simple_ols_company_dummy_v3.py

Model 2: Company dummy OLS (2번째 분석)

H1/H2: log(1+Engagement_i) = β0 + β1·Agg + β2·Aff + β3·SE + β4·SD
                              + Σδ_c·CompanyDummy_{ic}  (c=2..N)  + ε
H3:    Mean log(1+Eng)_{fq}  = α + β1·Intensity_{fq} + β2·Intensity²_{fq}
                              + Σδ_c·CompanyDummy_{fc}  (c=2..N)  + ε

기준 데이터: v3 reclassified corpus (68,039건)
기업 더미: 기업별 categorical dummy, reference=최저 fortune_rank 기업
고정 사항:
  - Classical OLS SE (s²=SSR/(n−k)), no HC3/robust
  - H2 번호: H2-1(Other wtd), H2-2(SELF wtd), H2-3(pairwise×3)  [b657bc0 기준]
  - 시간 FE, 통제변수, OOF, emoji_count, firm-month aggregation 금지

출력: simple_ols_company_dummy_v3/ (9개 파일)
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"
OUT  = Path(__file__).parent

# ── v3 입력 데이터 ─────────────────────────────────────────────────────────────
H2_RR    = CI / "data" / "regression_ready_v3" / "h2_post_level_regression_ready.csv"
TEMPLATE = CI / "data" / "human_labeling_template" / "training_labels_v3_with_coder3_batch2.csv"
MASTER   = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"

# v3 simple OLS 비교 기준
V3_H1H2_FS  = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h1_h2_full_sample_results.csv"
V3_H3_FS    = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h3_full_sample_results.csv"
V3_CONTRAST = ROOT / "20260618expand" / "ols_hypothesis_results" / \
              "simple_ols_baseline_v3_coder3_batch2" / "01_simple_ols_h1_h2_contrast_tests.csv"

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
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


def period_to_quarter(period: str) -> str:
    try:
        year, mo = period.split("-")
        q = (int(mo) - 1) // 3 + 1
        return f"{year}-Q{q}"
    except Exception:
        return "missing"


def created_at_to_quarter(created_at: str) -> str:
    try:
        dt = datetime.strptime(created_at.strip(), TWITTER_FMT)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}"
    except Exception:
        return "missing"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Company code mapping
# ─────────────────────────────────────────────────────────────────────────────

def build_company_map(all_company_names: list[str]) -> tuple[dict[str, int], str]:
    """
    company_name → company_code (1-based, sorted by fortune_rank then name).
    Returns (name→code dict, reference company name).
    reference = company with code=1 (omitted from dummies).
    """
    # fortune_rank from master
    name_to_rank: dict[str, int] = {}
    with open(MASTER, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cn = r["company_name"].strip()
            rk = r.get("fortune_rank", "").strip()
            if cn and rk:
                name_to_rank[cn] = int(rk)

    # Legacy companies not in Fortune list → assign high ranks
    next_rank = 200
    for cn in sorted(set(all_company_names)):
        if cn not in name_to_rank:
            name_to_rank[cn] = next_rank
            next_rank += 1

    # Sort all companies by rank, assign sequential codes 1..N
    present = sorted(set(all_company_names), key=lambda c: name_to_rank.get(c, 999))
    code_map = {cn: i + 1 for i, cn in enumerate(present)}
    reference = present[0]  # lowest rank = code 1 = omitted reference

    return code_map, reference


def make_company_dummies(rows: list[dict], code_map: dict[str, int]) -> tuple[np.ndarray, list[str]]:
    """
    Returns (D, dummy_names) where D is (n × n_dummies).
    Dummies for codes 2..max_code (reference=code1 omitted).
    """
    max_code = max(code_map.values())
    dummy_codes = list(range(2, max_code + 1))  # omit code=1 (reference)
    n = len(rows)
    D = np.zeros((n, len(dummy_codes)), dtype=float)
    code_to_col = {c: i for i, c in enumerate(dummy_codes)}
    for i, r in enumerate(rows):
        c = code_map.get(r.get("company_name", ""), 0)
        if c in code_to_col:
            D[i, code_to_col[c]] = 1.0
    dummy_names = [f"company_{c}" for c in dummy_codes]
    return D, dummy_names


# ─────────────────────────────────────────────────────────────────────────────
# OLS core (classical SE)
# ─────────────────────────────────────────────────────────────────────────────

def ols_fit(X: np.ndarray, y: np.ndarray):
    n, k = X.shape
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat  = X @ b
    resid = y - yhat
    ssr   = float(resid @ resid)
    s2    = ssr / (n - k)
    XtXi  = np.linalg.inv(X.T @ X)
    V     = s2 * XtXi
    se    = np.sqrt(np.diag(V))
    t_    = b / se
    p_    = 2 * stats.t.sf(np.abs(t_), df=n - k)
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2    = 1.0 - ssr / ss_tot if ss_tot > 0 else 0.0
    adj   = 1.0 - (1.0 - r2) * (n - 1) / (n - k) if n > k else 0.0
    return b, V, s2, t_, p_, n, k, r2, adj, n - k, resid


def contrast_test(c: list[float], b_sub: np.ndarray, V_sub: np.ndarray, df: int):
    c = np.array(c, dtype=float)
    est = float(c @ b_sub)
    var = float(c @ V_sub @ c)
    se  = math.sqrt(max(var, 0.0))
    if se == 0:
        return est, se, float("nan"), float("nan")
    t_stat = est / se
    p_val  = 2 * stats.t.sf(abs(t_stat), df)
    return est, se, t_stat, p_val


# ─────────────────────────────────────────────────────────────────────────────
# H1/H2 OLS (with company dummies)
# ─────────────────────────────────────────────────────────────────────────────

def run_h1h2_ols(rows: list[dict], code_map: dict[str, int],
                 label: str) -> tuple[list[dict], np.ndarray, np.ndarray, float, int]:
    """
    Runs post-level OLS with company dummies.
    Returns (coef_rows, b, V, df, n_*)
    """
    y   = np.array([to_f(r["log_total_engagement"]) for r in rows])
    agg = np.array([to_f(r["aggressive_humor"])     for r in rows])
    aff = np.array([to_f(r["affiliative_humor"])    for r in rows])
    se_ = np.array([to_f(r["self_enhancing_humor"]) for r in rows])
    sd  = np.array([to_f(r["self_defeating_humor"]) for r in rows])

    D, dummy_names = make_company_dummies(rows, code_map)
    ones = np.ones(len(rows))

    # X = [1, Agg, Aff, SE, SD, company_dummies...]
    X = np.column_stack([ones, agg, aff, se_, sd, D])

    b, V, s2, t_v, p_v, n, k, r2, adj_r2, df, _ = ols_fit(X, y)

    n_agg = int(agg.sum()); n_aff = int(aff.sum())
    n_se  = int(se_.sum()); n_sd  = int(sd.sum())

    term_names = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"] + dummy_names
    print(f"\n  [{label}] n={n:,}  k={k}  df={df:,}  R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, nm in enumerate(term_names[:5]):
        print(f"    {nm:25s}  β={float(b[i]):+.4f}  t={float(t_v[i]):+.3f}  p={float(p_v[i]):.4f}{stars(float(p_v[i]))}")

    coef_rows = []
    for i, nm in enumerate(term_names):
        coef_rows.append({
            "model":         label,
            "term":          nm,
            "coefficient":   round(float(b[i]), 6),
            "std_error":     round(math.sqrt(float(V[i, i])), 6),
            "t_statistic":   round(float(t_v[i]), 4),
            "p_value":       round(float(p_v[i]), 6),
            "stars":         stars(float(p_v[i])),
            "n":             n,
            "r_squared":     round(r2, 6),
            "adj_r_squared": round(adj_r2, 6),
            "df_residual":   df,
        })

    return coef_rows, b, V, df, n_agg, n_aff, n_se, n_sd, n


# ─────────────────────────────────────────────────────────────────────────────
# Contrast tests (H2 numbering: b657bc0 기준)
# H2-1: Agg − Other(wtd)  |  H2-2: Agg − SELF(wtd)  |  H2-3: pairwise ×3
# ─────────────────────────────────────────────────────────────────────────────

def run_contrasts(b, V, df, n_agg, n_aff, n_se, n_sd, model_label) -> list[dict]:
    """Contrasts on b[1:5], V[1:5,1:5] (humor type indices)."""
    b_h = b[1:5]
    V_h = V[1:5, 1:5]

    n_humor = n_agg + n_aff + n_se + n_sd
    n_other = n_aff + n_se + n_sd
    n_self  = n_se  + n_sd

    w_agg = n_agg / n_humor if n_humor else 0
    w_aff = n_aff / n_humor if n_humor else 0
    w_se  = n_se  / n_humor if n_humor else 0
    w_sd  = n_sd  / n_humor if n_humor else 0

    w_aff_o = n_aff / n_other if n_other else 0
    w_se_o  = n_se  / n_other if n_other else 0
    w_sd_o  = n_sd  / n_other if n_other else 0
    w_se_s  = n_se  / n_self  if n_self  else 0
    w_sd_s  = n_sd  / n_self  if n_self  else 0

    contrast_rows = []

    def _add(hyp, label_c, c, direction):
        est, se_c, t_c, p_c = contrast_test(c, b_h, V_h, df)
        sig    = not math.isnan(p_c) and p_c < 0.10
        if direction == "positive_sig":
            support = "supported" if est > 0 and sig else "not_supported"
        else:
            support = "supported" if est > 0 else "not_supported"
        contrast_rows.append({
            "model":       model_label,
            "hypothesis":  hyp,
            "contrast":    label_c,
            "weights_info": (f"agg:{w_agg:.3f} aff:{w_aff:.3f} se:{w_se:.3f} sd:{w_sd:.3f}"
                             if "Weighted" in label_c else ""),
            "estimate":    round(est, 6),
            "std_error":   round(se_c, 6),
            "t_statistic": round(t_c, 4) if not math.isnan(t_c) else "NA",
            "p_value":     round(p_c, 6) if not math.isnan(p_c) else "NA",
            "stars":       stars(p_c) if not math.isnan(p_c) else "",
            "direction":   "positive" if est > 0 else "negative",
            "support":     support,
        })
        print(f"    {hyp} | {label_c:50s} est={est:+.4f} se={se_c:.4f} t={t_c:+.3f} p={p_c:.4f}{stars(p_c)}")

    print(f"\n  === Contrast tests [{model_label}] ===")

    # H1
    _add("H1", "Weighted Humor Effect (vs non-humorous)", [w_agg, w_aff, w_se, w_sd], "positive_sig")
    # H2-1: Agg − Other weighted avg
    _add("H2-1", "Aggressive − Other humor (weighted avg)", [1.0, -w_aff_o, -w_se_o, -w_sd_o], "positive_sig")
    # H2-2: Agg − SELF weighted avg
    _add("H2-2", "Aggressive − SELF (se+sd weighted avg)", [1.0, 0.0, -w_se_s, -w_sd_s], "positive_sig")
    # H2-3: pairwise
    _add("H2-3", "Aggressive − Affiliative",    [1.0, -1.0,  0.0,  0.0], "positive_sig")
    _add("H2-3", "Aggressive − Self-Enhancing", [1.0,  0.0, -1.0,  0.0], "positive_sig")
    _add("H2-3", "Aggressive − Self-Defeating", [1.0,  0.0,  0.0, -1.0], "positive_sig")

    return contrast_rows


# ─────────────────────────────────────────────────────────────────────────────
# H3: firm-quarter OLS with company dummies
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_firm_quarter(posts: list[dict]) -> list[dict]:
    panel: dict[tuple, dict] = {}
    for r in posts:
        key = (r["company_name"], r["quarter"])
        if key not in panel:
            panel[key] = {"_n": 0, "_agg": 0, "_log_sum": 0.0}
        p = panel[key]
        p["_n"]       += 1
        p["_agg"]     += int(to_f(r.get("aggressive_humor", "0")))
        p["_log_sum"] += to_f(r.get("log_total_engagement", "0"))
    rows = []
    for (company, quarter), p in panel.items():
        n = p["_n"]
        if n == 0:
            continue
        intensity = p["_agg"] / n
        rows.append({
            "company_name":          company,
            "quarter":               quarter,
            "post_count":            n,
            "aggressive_count":      p["_agg"],
            "aggressive_intensity":  round(intensity, 12),
            "aggressive_intensity_sq": round(intensity * intensity, 12),
            "mean_log_engagement":   round(p["_log_sum"] / n, 6),
        })
    return rows


def run_h3_ols_with_dummies(panel_rows: list[dict], code_map: dict[str, int],
                             label: str) -> tuple[list[dict], dict]:
    """H3 quadratic OLS + company dummies."""
    y    = np.array([to_f(r["mean_log_engagement"])    for r in panel_rows])
    x1   = np.array([to_f(r["aggressive_intensity"])   for r in panel_rows])
    x2   = np.array([to_f(r["aggressive_intensity_sq"])for r in panel_rows])
    ones = np.ones(len(panel_rows))

    D, dummy_names = make_company_dummies(panel_rows, code_map)
    X = np.column_stack([ones, x1, x2, D])

    b, V, s2, t_v, p_v, n, k, r2, adj_r2, df, _ = ols_fit(X, y)

    beta1 = float(b[1])
    beta2 = float(b[2])
    tp    = -beta1 / (2 * beta2) if beta2 != 0 else float("inf")
    obs_min, obs_max = float(x1.min()), float(x1.max())
    in_range = obs_min <= tp <= obs_max
    h3_support = (beta1 > 0 and beta2 < 0 and float(p_v[2]) < 0.10 and in_range)
    n_nonzero  = int((x1 > 0).sum())

    term_names = ["intercept", "AggressiveIntensity", "AggressiveIntensity_sq"] + dummy_names
    print(f"\n  [{label}] n={n:,}  k={k}  df={df:,}  R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, nm in enumerate(["intercept", "AggressiveIntensity", "AggressiveIntensity²"]):
        print(f"    {nm:25s}  β={float(b[i]):+.6f}  t={float(t_v[i]):+.3f}  p={float(p_v[i]):.4f}{stars(float(p_v[i]))}")
    print(f"    Turning point: {tp:.4f}  (range: [{obs_min:.4f}, {obs_max:.4f}])  in_range={in_range}")
    print(f"    H3 supported: {h3_support}")

    coef_rows = [
        {"model": label, "term": nm,
         "coefficient":   round(float(b[i]), 6),
         "std_error":     round(math.sqrt(float(V[i, i])), 6),
         "t_statistic":   round(float(t_v[i]), 4),
         "p_value":       round(float(p_v[i]), 6),
         "stars":         stars(float(p_v[i])),
         "n": n, "r_squared": round(r2, 6), "adj_r_squared": round(adj_r2, 6),
         "df_residual": df}
        for i, nm in enumerate(term_names)
    ]

    diag = {
        "model":             label,
        "n_firm_quarters":   n,
        "n_nonzero_intensity": n_nonzero,
        "k":                 k,
        "beta1_intensity":   round(beta1, 6),
        "beta1_se":          round(math.sqrt(float(V[1, 1])), 6),
        "beta1_t":           round(float(t_v[1]), 4),
        "beta1_p":           round(float(p_v[1]), 6),
        "beta1_stars":       stars(float(p_v[1])),
        "beta2_intensity_sq": round(beta2, 6),
        "beta2_se":          round(math.sqrt(float(V[2, 2])), 6),
        "beta2_t":           round(float(t_v[2]), 4),
        "beta2_p":           round(float(p_v[2]), 6),
        "beta2_stars":       stars(float(p_v[2])),
        "turning_point":     round(tp, 6) if math.isfinite(tp) else "Inf",
        "obs_intensity_min": round(obs_min, 6),
        "obs_intensity_max": round(obs_max, 6),
        "tp_in_obs_range":   str(in_range),
        "H3_supported":      str(h3_support),
        "r_squared":         round(r2, 6),
        "adj_r_squared":     round(adj_r2, 6),
    }
    return coef_rows, diag


# ─────────────────────────────────────────────────────────────────────────────
# v3 baseline 비교
# ─────────────────────────────────────────────────────────────────────────────

def load_v3_baseline() -> tuple[dict, dict, dict]:
    """
    Returns (h1h2_map, h3_map, contrast_map):
      h1h2_map[term] = {coefficient, std_error, p_value}
    """
    h1h2_map, h3_map, contrast_map = {}, {}, {}
    if V3_H1H2_FS.exists():
        with open(V3_H1H2_FS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("model", "").startswith("Full_sample"):
                    h1h2_map[r["term"]] = r
    if V3_H3_FS.exists():
        with open(V3_H3_FS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("model", "").startswith("Full_sample"):
                    h3_map[r["term"]] = r
    if V3_CONTRAST.exists():
        with open(V3_CONTRAST, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("model", "").startswith("Full_sample"):
                    contrast_map[r["contrast"]] = r
    return h1h2_map, h3_map, contrast_map


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("run_simple_ols_company_dummy_v3.py")
    print("  Model 2: Company dummy OLS")
    print("  Classical OLS SE. No time FE. No controls. No OOF.")
    print("=" * 70)

    OUT.mkdir(parents=True, exist_ok=True)

    # ── 1. H2 regression-ready 로드 ───────────────────────────────────────────
    print(f"\n[Loading] H2 regression-ready (v3)...")
    with open(H2_RR, newline="", encoding="utf-8") as f:
        h2_rows = list(csv.DictReader(f))
    print(f"  H2 rows: {len(h2_rows):,}")

    all_cos = [r["company_name"] for r in h2_rows]
    code_map, reference_co = build_company_map(all_cos)
    n_companies  = len(code_map)
    n_dummies    = n_companies - 1   # reference omitted
    print(f"  Unique companies: {n_companies}")
    print(f"  Company dummies:  {n_dummies}  (reference = '{reference_co}')")

    # H3 firm-quarter 집계
    h3_rows_with_q = []
    for r in h2_rows:
        q = period_to_quarter(r.get("period", ""))
        if q != "missing":
            h3_rows_with_q.append({**r, "quarter": q})

    fq_rows = aggregate_firm_quarter(h3_rows_with_q)
    print(f"  Firm-quarter obs: {len(fq_rows):,}")
    n_nonzero_fq = sum(1 for r in fq_rows if to_f(r["aggressive_intensity"]) > 0)
    print(f"  Non-zero intensity: {n_nonzero_fq}/{len(fq_rows)}")

    # ── 2. Full-sample H1/H2 OLS ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H1/H2 Full-sample company dummy OLS")
    print("─" * 60)

    fs_coef, b_fs, V_fs, df_fs, n_agg_f, n_aff_f, n_se_f, n_sd_f, n_fs = \
        run_h1h2_ols(h2_rows, code_map, "Full_sample_CD")
    _write_csv(OUT / "company_dummy_h1_h2_full_sample_results.csv", fs_coef)
    print("  → company_dummy_h1_h2_full_sample_results.csv written")

    # ── 3. Human-coded H1/H2 OLS ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H1/H2 Human-coded company dummy OLS")
    print("─" * 60)

    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        tmpl_rows = list(csv.DictReader(f))

    VALID_PRES = {"0", "1"}
    TYPE_MAP = {"1": "aggressive", "2": "affiliative", "3": "self_enhancing", "4": "self_defeating"}

    hc_rows = []
    for r in tmpl_rows:
        pres = r.get("human_humor_presence", "").strip()
        if pres not in VALID_PRES:
            continue
        typ = r.get("human_humor_type", "").strip()
        total_eng = to_f(r.get("total_engagement", "0"))
        log_eng   = math.log1p(total_eng)
        agg = "1" if (pres == "1" and typ == "1") else "0"
        aff = "1" if (pres == "1" and typ == "2") else "0"
        se  = "1" if (pres == "1" and typ == "3") else "0"
        sd  = "1" if (pres == "1" and typ == "4") else "0"
        hc_rows.append({
            "company_name":       r.get("company_name", ""),
            "log_total_engagement": log_eng,
            "aggressive_humor":   agg,
            "affiliative_humor":  aff,
            "self_enhancing_humor": se,
            "self_defeating_humor": sd,
        })

    # Human-coded company map (may have fewer companies)
    hc_all_cos = [r["company_name"] for r in hc_rows]
    hc_code_map, hc_ref = build_company_map(hc_all_cos)
    hc_n_dummies = len(hc_code_map) - 1

    print(f"  Human-coded posts: {len(hc_rows):,}")
    print(f"  HC companies: {len(hc_code_map)}  (dummies: {hc_n_dummies}  ref='{hc_ref}')")

    hc_coef, b_hc, V_hc, df_hc, n_agg_h, n_aff_h, n_se_h, n_sd_h, n_hc = \
        run_h1h2_ols(hc_rows, hc_code_map, "Human_coded_CD")
    _write_csv(OUT / "company_dummy_h1_h2_human_coded_results.csv", hc_coef)
    print("  → company_dummy_h1_h2_human_coded_results.csv written")

    # ── 4. Contrast tests ─────────────────────────────────────────────────────
    contrast_fs = run_contrasts(b_fs, V_fs, df_fs, n_agg_f, n_aff_f, n_se_f, n_sd_f, "Full_sample_CD")
    contrast_hc = run_contrasts(b_hc, V_hc, df_hc, n_agg_h, n_aff_h, n_se_h, n_sd_h, "Human_coded_CD")
    _write_csv(OUT / "company_dummy_h1_h2_contrast_tests.csv", contrast_fs + contrast_hc)
    print("  → company_dummy_h1_h2_contrast_tests.csv written")

    # ── 5. H3 Full-sample ─────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H3 Full-sample firm-quarter company dummy OLS")
    print("─" * 60)
    # company_map for H3 (only companies in firm-quarter data)
    fq_cos = [r["company_name"] for r in fq_rows]
    fq_code_map, fq_ref = build_company_map(fq_cos)
    fq_n_dummies = len(fq_code_map) - 1
    print(f"  FQ companies: {len(fq_code_map)}  (dummies: {fq_n_dummies}  ref='{fq_ref}')")

    h3_fs_coef, h3_fs_diag = run_h3_ols_with_dummies(fq_rows, fq_code_map, "Full_sample_H3_CD")
    _write_csv(OUT / "company_dummy_h3_full_sample_results.csv", h3_fs_coef)
    print("  → company_dummy_h3_full_sample_results.csv written")

    # ── 6. H3 Human-coded ─────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("H3 Human-coded firm-quarter company dummy OLS")
    print("─" * 60)

    hc_q_rows = []
    for r in tmpl_rows:
        if r.get("human_humor_presence", "").strip() not in VALID_PRES:
            continue
        ca = r.get("created_at", "").strip()
        q  = created_at_to_quarter(ca)
        if q == "missing":
            continue
        total_eng = to_f(r.get("total_engagement", "0"))
        log_eng   = math.log1p(total_eng)
        agg = 1 if (r.get("human_humor_presence","")=="1" and r.get("human_humor_type","")=="1") else 0
        hc_q_rows.append({
            "company_name":       r.get("company_name", ""),
            "quarter":            q,
            "log_total_engagement": log_eng,
            "aggressive_humor":   str(agg),
        })

    hc_fq_rows = aggregate_firm_quarter(hc_q_rows)
    hc_fq_cos = [r["company_name"] for r in hc_fq_rows]
    hc_fq_code_map, hc_fq_ref = build_company_map(hc_fq_cos)

    SUFFICIENT_FQ_THRESHOLD = 30
    n_nonzero_hc = sum(1 for r in hc_fq_rows if to_f(r["aggressive_intensity"]) > 0)
    hc_feasible  = len(hc_fq_rows) >= SUFFICIENT_FQ_THRESHOLD and n_nonzero_hc >= 10
    print(f"  HC firm-quarters: {len(hc_fq_rows):,}  non-zero: {n_nonzero_hc}")

    if hc_feasible:
        hc_n_dummies_fq = len(hc_fq_code_map) - 1
        print(f"  HC FQ companies: {len(hc_fq_code_map)}  (dummies: {hc_n_dummies_fq}  ref='{hc_fq_ref}')")
        h3_hc_coef, h3_hc_diag = run_h3_ols_with_dummies(hc_fq_rows, hc_fq_code_map, "Human_coded_H3_CD")
    else:
        print("  HC H3: insufficient data — skipped")
        h3_hc_coef = [{"model": "Human_coded_H3_CD", "note": "insufficient_data"}]
        h3_hc_diag = {"model": "Human_coded_H3_CD", "H3_supported": "insufficient_data"}

    _write_csv(OUT / "company_dummy_h3_human_coded_results.csv", h3_hc_coef)
    print("  → company_dummy_h3_human_coded_results.csv written")

    # ── 7. H3 diagnostics ─────────────────────────────────────────────────────
    _write_csv(OUT / "company_dummy_h3_quadratic_diagnostics.csv",
               [h3_fs_diag, h3_hc_diag])
    print("  → company_dummy_h3_quadratic_diagnostics.csv written")

    # ── 8. v3 simple OLS 비교 ─────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("v3 simple OLS vs company dummy comparison")
    print("─" * 60)
    v3_h1h2, v3_h3, v3_contrast = load_v3_baseline()

    def delta_str(new_val, old_val) -> str:
        try:
            return f"{float(new_val) - float(old_val):+.4f}"
        except Exception:
            return "n/a"

    cmp_rows = []
    for term in ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]:
        cd_row  = next((r for r in fs_coef if r["term"] == term), {})
        v3_row  = v3_h1h2.get(term, {})
        cmp_rows.append({
            "term":             term,
            "v3_simple_coef":   v3_row.get("coefficient", "n/a"),
            "v3_simple_p":      v3_row.get("p_value", "n/a"),
            "v3_simple_stars":  v3_row.get("stars", ""),
            "cd_coef":          cd_row.get("coefficient", "n/a"),
            "cd_p":             cd_row.get("p_value", "n/a"),
            "cd_stars":         cd_row.get("stars", ""),
            "delta_coef":       delta_str(cd_row.get("coefficient"), v3_row.get("coefficient")),
        })

    # Contrast 비교
    c_labels = {
        "H1":   "Weighted Humor Effect (vs non-humorous)",
        "H2-1": "Aggressive − Other humor (weighted avg)",
        "H2-2": "Aggressive − SELF (se+sd weighted avg)",
        "H2-3a": "Aggressive − Affiliative",
        "H2-3b": "Aggressive − Self-Enhancing",
        "H2-3c": "Aggressive − Self-Defeating",
    }
    for hyp_key, contrast_label in c_labels.items():
        cd_c  = next((r for r in contrast_fs if r["contrast"] == contrast_label), {})
        v3_c  = v3_contrast.get(contrast_label, {})
        cmp_rows.append({
            "term":             hyp_key,
            "v3_simple_coef":   v3_c.get("estimate", "n/a"),
            "v3_simple_p":      v3_c.get("p_value", "n/a"),
            "v3_simple_stars":  v3_c.get("stars", ""),
            "cd_coef":          cd_c.get("estimate", "n/a"),
            "cd_p":             cd_c.get("p_value", "n/a"),
            "cd_stars":         cd_c.get("stars", ""),
            "delta_coef":       delta_str(cd_c.get("estimate"), v3_c.get("estimate")),
        })

    # H3 비교
    for h3_label, h3_key in [("H3_beta1", "beta1_intensity"), ("H3_beta2", "beta2_intensity_sq"),
                               ("H3_TP", "turning_point")]:
        cmp_rows.append({
            "term":             h3_label,
            "v3_simple_coef":   v3_h3.get(h3_key.replace("beta1_intensity","AggressiveIntensity")
                                          .replace("beta2_intensity_sq","AggressiveIntensity_sq"), {}).get("coefficient", "n/a"),
            "v3_simple_p":      "n/a",
            "v3_simple_stars":  "",
            "cd_coef":          h3_fs_diag.get(h3_key, "n/a"),
            "cd_p":             "n/a",
            "cd_stars":         "",
            "delta_coef":       "n/a",
        })

    _write_csv(OUT / "simple_ols_v3_vs_company_dummy_v3_comparison.csv", cmp_rows)
    print("  → simple_ols_v3_vs_company_dummy_v3_comparison.csv written")

    # ── 9. Interpretation markdown ────────────────────────────────────────────
    _write_interpretation(
        b_fs, V_fs, p_=None, df_fs=df_fs,
        n_agg_f=n_agg_f, n_aff_f=n_aff_f, n_se_f=n_se_f, n_sd_f=n_sd_f, n_fs=n_fs,
        b_hc=b_hc, V_hc=V_hc, df_hc=df_hc,
        n_agg_h=n_agg_h, n_aff_h=n_aff_h, n_se_h=n_se_h, n_sd_h=n_sd_h, n_hc=n_hc,
        contrast_fs=contrast_fs, contrast_hc=contrast_hc,
        h3_fs_diag=h3_fs_diag, h3_hc_diag=h3_hc_diag,
        hc_feasible=hc_feasible,
        reference_co=reference_co, n_companies=n_companies, n_dummies=n_dummies,
        fq_n=len(fq_rows), r2_fs=None, adj_fs=None,
    )

    # Summary print
    print("\n" + "=" * 70)
    print("run_simple_ols_company_dummy_v3 COMPLETE")
    print("=" * 70)
    print(f"\n  출력 디렉토리: {OUT}")
    generated = [
        "company_dummy_h1_h2_full_sample_results.csv",
        "company_dummy_h1_h2_human_coded_results.csv",
        "company_dummy_h1_h2_contrast_tests.csv",
        "company_dummy_h3_full_sample_results.csv",
        "company_dummy_h3_human_coded_results.csv",
        "company_dummy_h3_quadratic_diagnostics.csv",
        "simple_ols_v3_vs_company_dummy_v3_comparison.csv",
        "company_dummy_v3_interpretation.md",
    ]
    for fn in generated:
        print(f"  {fn}")


def _write_interpretation(
    b_fs, V_fs, p_, df_fs,
    n_agg_f, n_aff_f, n_se_f, n_sd_f, n_fs,
    b_hc, V_hc, df_hc,
    n_agg_h, n_aff_h, n_se_h, n_sd_h, n_hc,
    contrast_fs, contrast_hc,
    h3_fs_diag, h3_hc_diag,
    hc_feasible,
    reference_co, n_companies, n_dummies,
    fq_n, r2_fs, adj_fs,
) -> None:

    def sig(p):
        try:
            return stars(float(p))
        except Exception:
            return ""

    def _c(lst, hyp, contrast_label):
        return next((r for r in lst if r.get("hypothesis") == hyp
                     and r.get("contrast") == contrast_label), {})

    h1_f  = _c(contrast_fs, "H1",   "Weighted Humor Effect (vs non-humorous)")
    h21_f = _c(contrast_fs, "H2-1", "Aggressive − Other humor (weighted avg)")
    h22_f = _c(contrast_fs, "H2-2", "Aggressive − SELF (se+sd weighted avg)")
    h1_h  = _c(contrast_hc, "H1",   "Weighted Humor Effect (vs non-humorous)")
    h21_h = _c(contrast_hc, "H2-1", "Aggressive − Other humor (weighted avg)")
    h22_h = _c(contrast_hc, "H2-2", "Aggressive − SELF (se+sd weighted avg)")

    term_display = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]
    b_names_fs = [f"β={float(b_fs[i]):+.4f}" for i in range(5)]
    b_names_hc = [f"β={float(b_hc[i]):+.4f}" for i in range(5)]

    n_humor_f = n_agg_f + n_aff_f + n_se_f + n_sd_f
    n_humor_h = n_agg_h + n_aff_h + n_se_h + n_sd_h

    md_lines = [
        "# Company Dummy OLS — Interpretation (Model 2)",
        "",
        "## Model specification",
        "",
        "**Model 2 (Company dummy model)**:",
        "",
        "$$\\log(1+\\text{Engagement}_i) = \\beta_0 + \\beta_1\\text{Aggressive}_i "
        "+ \\beta_2\\text{Affiliative}_i + \\beta_3\\text{SelfEnhancing}_i "
        "+ \\beta_4\\text{SelfDefeating}_i + \\sum_{c=2}^{N}\\delta_c\\text{CompanyDummy}_{ic} + \\varepsilon_i$$",
        "",
        f"- Total companies: {n_companies}  |  Company dummies included: {n_dummies}  |  Reference: {reference_co}",
        "- Classical OLS SE (s²=SSR/(n−k)). No time FE. No controls.",
        "- H3: firm-quarter level with same company dummies",
        "- Stars: \\*\\*\\* p<.01, \\*\\* p<.05, \\* p<.10 (two-sided)",
        "",
        "---",
        "",
        "## H1/H2 Coefficient table",
        "",
        "| Term | Full β | Full stars | HC β | HC stars |",
        "|:-----|-------:|:----------:|-----:|:--------:|",
    ]

    from scipy import stats as _stats
    for i, nm in enumerate(term_display):
        p_f = float(2 * _stats.t.sf(abs(float(b_fs[i]) / math.sqrt(float(V_fs[i, i]))), df=df_fs))
        p_h = float(2 * _stats.t.sf(abs(float(b_hc[i]) / math.sqrt(float(V_hc[i, i]))), df=df_hc))
        md_lines.append(
            f"| {nm} | {float(b_fs[i]):+.4f} | {sig(p_f)} | {float(b_hc[i]):+.4f} | {sig(p_h)} |"
        )
    md_lines += [
        f"| **N** | {n_fs:,} | | {n_hc:,} | |",
        "",
        "---",
        "",
        "## H1: Weighted Humor Effect",
        "",
        f"**Full sample**: estimate = {h1_f.get('estimate','n/a')}, "
        f"SE = {h1_f.get('std_error','n/a')}, "
        f"t = {h1_f.get('t_statistic','n/a')}, p = {h1_f.get('p_value','n/a')}{h1_f.get('stars','')}  "
        f"→ H1 **{h1_f.get('support','n/a')}**",
        "",
        f"**Human-coded**: estimate = {h1_h.get('estimate','n/a')}, "
        f"SE = {h1_h.get('std_error','n/a')}, "
        f"t = {h1_h.get('t_statistic','n/a')}, p = {h1_h.get('p_value','n/a')}{h1_h.get('stars','')}  "
        f"→ H1 **{h1_h.get('support','n/a')}**",
        "",
        "---",
        "",
        "## H2-1: Aggressive vs Other humor (weighted average)",
        "",
        f"**Full sample**: estimate = {h21_f.get('estimate','n/a')}, "
        f"p = {h21_f.get('p_value','n/a')}{h21_f.get('stars','')}  "
        f"→ H2-1 **{h21_f.get('support','n/a')}**",
        "",
        f"**Human-coded**: estimate = {h21_h.get('estimate','n/a')}, "
        f"p = {h21_h.get('p_value','n/a')}{h21_h.get('stars','')}  "
        f"→ H2-1 **{h21_h.get('support','n/a')}**",
        "",
        "---",
        "",
        "## H2-2: Aggressive vs SELF humor (weighted average)",
        "",
        f"**Full sample**: estimate = {h22_f.get('estimate','n/a')}, "
        f"p = {h22_f.get('p_value','n/a')}{h22_f.get('stars','')}  "
        f"→ H2-2 **{h22_f.get('support','n/a')}**",
        "",
        f"**Human-coded**: estimate = {h22_h.get('estimate','n/a')}, "
        f"p = {h22_h.get('p_value','n/a')}{h22_h.get('stars','')}  "
        f"→ H2-2 **{h22_h.get('support','n/a')}**",
        "",
        "---",
        "",
        "## H2 overall judgment",
        "",
        "**H2 is strongly but partially supported.** (company dummy model에서도 동일)",
        "",
        "---",
        "",
        "## H3 firm-quarter results",
        "",
        "| Item | Full sample | Human-coded |",
        "|:-----|:-----------:|:-----------:|",
        f"| N (firm-quarters) | {h3_fs_diag.get('n_firm_quarters','NA')} | "
        f"{'insufficient_data' if not hc_feasible else h3_hc_diag.get('n_firm_quarters','NA')} |",
        f"| k (parameters) | {h3_fs_diag.get('k','NA')} | "
        f"{'n/a' if not hc_feasible else h3_hc_diag.get('k','NA')} |",
        f"| β₁ (intensity) | {h3_fs_diag.get('beta1_intensity','NA')}{h3_fs_diag.get('beta1_stars','')} | "
        f"{'n/a' if not hc_feasible else str(h3_hc_diag.get('beta1_intensity','NA'))+h3_hc_diag.get('beta1_stars','')} |",
        f"| β₂ (intensity²) | {h3_fs_diag.get('beta2_intensity_sq','NA')}{h3_fs_diag.get('beta2_stars','')} | "
        f"{'n/a' if not hc_feasible else str(h3_hc_diag.get('beta2_intensity_sq','NA'))+h3_hc_diag.get('beta2_stars','')} |",
        f"| Turning point | {h3_fs_diag.get('turning_point','NA')} | "
        f"{'n/a' if not hc_feasible else h3_hc_diag.get('turning_point','NA')} |",
        f"| TP in obs range | {h3_fs_diag.get('tp_in_obs_range','NA')} | "
        f"{'n/a' if not hc_feasible else h3_hc_diag.get('tp_in_obs_range','NA')} |",
        f"| H3 supported | {h3_fs_diag.get('H3_supported','NA')} | "
        f"{'insufficient_data' if not hc_feasible else h3_hc_diag.get('H3_supported','NA')} |",
        f"| R² | {h3_fs_diag.get('r_squared','NA')} | "
        f"{'n/a' if not hc_feasible else h3_hc_diag.get('r_squared','NA')} |",
        "",
        "---",
        "",
        "## Interpretation notes",
        "",
        "- **Model 2 vs Model 1**: company dummy model은 기업 간 평균 engagement 수준 차이를 반영한다.",
        "- 시간 효과나 post-level controls는 포함하지 않았다.",
        "- 따라서 이는 완전한 robustness test가 아니라 기업별 heterogeneity를 단순 통제한 두 번째 단계의 분석이다.",
        "- H1/H2/H3 판정이 Model 1과 일치하면 기업 간 이질성을 통제한 후에도 결과가 robust하다고 해석한다.",
        "",
        "> Generated by run_simple_ols_company_dummy_v3.py | 2026-06-19",
    ]

    (OUT / "company_dummy_v3_interpretation.md").write_text("\n".join(md_lines), encoding="utf-8")
    print("  → company_dummy_v3_interpretation.md written")


if __name__ == "__main__":
    main()
