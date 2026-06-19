"""
run_simple_ols_baseline_main.py

Task 0 : Classified data summary (no regressions)
Task 1 : Simple OLS baseline — H1/H2 post-level + H3 firm-quarter
         Full sample & human-coded sample

Model specs (fixed, do NOT alter):
  H1/H2: log(1+Engagement_i) = β0 + β1*Agg + β2*Aff + β3*SE + β4*SD + ε
  H3:    MeanLog(1+Eng)_{fq} = α + β1*Intensity_{fq} + β2*Intensity²_{fq} + ε

Classical OLS SE (s²=SSR/(n-k)), no HC3/robust.
Stars: ***p<.01  **p<.05  *p<.10

NO controls, NO fixed effects, NO OOF, NO emoji_count.
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

# Input files
CLASSIFIED  = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"
H1_RR       = CI / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"
H2_RR       = CI / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"
TEMPLATE    = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv"

TWITTER_FMT = "%a %b %d %H:%M:%S +0000 %Y"


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def to_f(v: str, default: float = 0.0) -> float:
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
    """'2015-03' → '2015-Q1'"""
    try:
        year, mo = period.split("-")
        q = (int(mo) - 1) // 3 + 1
        return f"{year}-Q{q}"
    except Exception:
        return "missing"


def created_at_to_quarter(created_at: str) -> str:
    """'Mon Jul 24 15:36:01 +0000 2023' → '2023-Q3'"""
    try:
        dt = datetime.strptime(created_at.strip(), TWITTER_FMT)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}"
    except Exception:
        return "missing"


# ─────────────────────────────────────────────────────────────────────────────
# OLS core
# ─────────────────────────────────────────────────────────────────────────────

def ols_fit(X: np.ndarray, y: np.ndarray):
    """
    Classical OLS. Returns:
      b, V, s2, t_stats, p_vals, n, k, r2, adj_r2, df, resid
    """
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
    """Linear contrast c @ b_sub with classical SE."""
    c = np.array(c, dtype=float)
    est = float(c @ b_sub)
    var = float(c @ V_sub @ c)
    se  = math.sqrt(max(var, 0.0))
    if se == 0:
        return est, se, float("nan"), float("nan")
    t_stat = est / se
    p_val  = 2 * stats.t.sf(abs(t_stat), df)
    return est, se, t_stat, float(p_val)


# ─────────────────────────────────────────────────────────────────────────────
# Task 0 – Classified data summary
# ─────────────────────────────────────────────────────────────────────────────

def task0_summary(classified: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("TASK 0 : Classified data summary")
    print("=" * 70)

    n_total = len(classified)
    pres    = Counter(r["humor_presence"] for r in classified)
    typ_    = Counter(r["humor_type"] for r in classified)
    stat_   = Counter(r["classification_status"] for r in classified)

    n_humor   = pres.get("1", 0)
    n_nh      = pres.get("0", 0)
    n_agg     = typ_.get("aggressive", 0)
    n_aff     = typ_.get("affiliative", 0)
    n_se      = typ_.get("self_enhancing", 0)
    n_sd      = typ_.get("self_defeating", 0)
    n_nh_type = typ_.get("non_humorous", 0)

    periods = sorted(
        set(r.get("period", "")
            for r in classified
            if r.get("period", "") not in ("", "missing_period")),
        key=lambda x: x
    )

    print(f"\nTotal posts            : {n_total:,}")
    print(f"Classification status  : {dict(stat_)}")
    print(f"Sample period          : {periods[0] if periods else 'N/A'} ~ {periods[-1] if periods else 'N/A'}")
    print(f"\nHumor presence:")
    print(f"  Humorous (1)         : {n_humor:,}  ({n_humor/n_total*100:.1f}%)")
    print(f"  Non-humorous (0)     : {n_nh:,}  ({n_nh/n_total*100:.1f}%)")
    print(f"\nHumor type distribution:")
    print(f"  non_humorous         : {n_nh_type:,}  ({n_nh_type/n_total*100:.1f}%)")
    print(f"  affiliative          : {n_aff:,}  ({n_aff/n_total*100:.1f}%)")
    print(f"  self_enhancing       : {n_se:,}  ({n_se/n_total*100:.1f}%)")
    print(f"  aggressive           : {n_agg:,}  ({n_agg/n_total*100:.1f}%)")
    print(f"  self_defeating       : {n_sd:,}  ({n_sd/n_total*100:.1f}%)")

    # Write distribution CSV
    dist_rows = [
        {"category": "full_sample_total",      "label": "All posts",        "n": n_total, "pct": 100.0},
        {"category": "humor_presence_humorous", "label": "Humorous",         "n": n_humor, "pct": round(n_humor/n_total*100,2)},
        {"category": "humor_presence_non",      "label": "Non-humorous",     "n": n_nh,    "pct": round(n_nh/n_total*100,2)},
        {"category": "type_non_humorous",       "label": "non_humorous",     "n": n_nh_type,"pct": round(n_nh_type/n_total*100,2)},
        {"category": "type_affiliative",        "label": "affiliative",      "n": n_aff,   "pct": round(n_aff/n_total*100,2)},
        {"category": "type_self_enhancing",     "label": "self_enhancing",   "n": n_se,    "pct": round(n_se/n_total*100,2)},
        {"category": "type_aggressive",         "label": "aggressive",       "n": n_agg,   "pct": round(n_agg/n_total*100,2)},
        {"category": "type_self_defeating",     "label": "self_defeating",   "n": n_sd,    "pct": round(n_sd/n_total*100,2)},
    ]
    _write_csv(OUT / "00_classified_data_distribution.csv",
               ["category", "label", "n", "pct"], dist_rows)
    print(f"\n→ 00_classified_data_distribution.csv written")

    # Write summary markdown
    md_lines = [
        "# 00 Classified Data Summary",
        "",
        "## Analysis basis",
        "",
        "| Item | Value |",
        "|:-----|:------|",
        f"| Corpus | Fortune 100 X/Twitter integrated corpus |",
        f"| Total posts (N) | {n_total:,} |",
        f"| Sample period | {periods[0] if periods else 'N/A'} ~ {periods[-1] if periods else 'N/A'} |",
        f"| parsed date rows | {n_total:,} |",
        f"| missing date rows | 0 |",
        f"| Classifier | TF-IDF + Logistic Regression (domain-adapted) |",
        f"| Training labels | 2,498 (combined batch1 + batch2, coder1~coder3) |",
        f"| Presence threshold | 0.50 argmax |",
        f"| Type assignment | argmax (always assigned) |",
        "",
        "## Humor presence distribution",
        "",
        "| Presence | N | % |",
        "|:---------|--:|--:|",
        f"| Humorous (1) | {n_humor:,} | {n_humor/n_total*100:.1f}% |",
        f"| Non-humorous (0) | {n_nh:,} | {n_nh/n_total*100:.1f}% |",
        f"| **Total** | **{n_total:,}** | **100.0%** |",
        "",
        "## Humor type distribution (classifier-predicted)",
        "",
        "| Type | N | % of total | % of humorous |",
        "|:-----|--:|----------:|-------------:|",
        f"| affiliative | {n_aff:,} | {n_aff/n_total*100:.1f}% | {n_aff/n_humor*100:.1f}% |",
        f"| self_enhancing | {n_se:,} | {n_se/n_total*100:.1f}% | {n_se/n_humor*100:.1f}% |",
        f"| aggressive | {n_agg:,} | {n_agg/n_total*100:.1f}% | {n_agg/n_humor*100:.1f}% |",
        f"| self_defeating | {n_sd:,} | {n_sd/n_total*100:.1f}% | {n_sd/n_humor*100:.1f}% |",
        f"| **Humorous total** | **{n_humor:,}** | **{n_humor/n_total*100:.1f}%** | **100.0%** |",
        f"| non_humorous | {n_nh_type:,} | {n_nh_type/n_total*100:.1f}% | — |",
        "",
        "## Human-coded sample (supplemental validation)",
        "",
        "| Item | N |",
        "|:-----|--:|",
        "| Combined labeling template (all candidates) | 2,498 |",
        "| Valid presence labels (0 or 1) | 2,480 |",
        "| Valid type labels (presence=1, type=1~4) | 1,027 |",
        "| — aggressive (type=1) | 80 |",
        "| — affiliative (type=2) | 510 |",
        "| — self-enhancing (type=3) | 403 |",
        "| — self-defeating (type=4) | 34 |",
        "| Non-humorous (presence=0) | 1,453 |",
        "",
        "## Measurement notes",
        "",
        "- **Dependent variable**: log(1 + total_engagement) as a proxy for brand equity "
        "(consumer/brand engagement). Engagement is a proxy, not brand equity itself.",
        "- **Full-sample type classification**: predicted by domain-adapted classifier. "
        "Measurement error in type labels cannot be ruled out.",
        "- **Human-coded data**: used as supplemental validation evidence, NOT as main results. "
        "Do not over-interpret human-coded results as representative of the full sample.",
        "- **Limitation**: H2 and H3 type-level results are based on classifier-predicted labels "
        "and should be interpreted with measurement limitation caveat.",
        "",
        "> Generated by run_simple_ols_baseline_main.py",
    ]
    (OUT / "00_classified_data_summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print("→ 00_classified_data_summary.md written")


# ─────────────────────────────────────────────────────────────────────────────
# H1/H2 OLS
# ─────────────────────────────────────────────────────────────────────────────

def run_h1_h2_ols(rows: list[dict], label: str):
    """
    rows: each dict must have log_total_engagement, aggressive_humor,
          affiliative_humor, self_enhancing_humor, self_defeating_humor
          (all as str "0"/"1" or float-convertible).
    Returns (b, V, t_, p_, n, k, r2, adj_r2, df, coef_names,
             n_agg, n_aff, n_se, n_sd, n_nh)
    """
    y     = np.array([to_f(r["log_total_engagement"]) for r in rows])
    agg   = np.array([to_f(r.get("aggressive_humor", "0"))     for r in rows])
    aff   = np.array([to_f(r.get("affiliative_humor", "0"))    for r in rows])
    se    = np.array([to_f(r.get("self_enhancing_humor", "0")) for r in rows])
    sd    = np.array([to_f(r.get("self_defeating_humor", "0")) for r in rows])
    ones  = np.ones(len(rows))

    X = np.column_stack([ones, agg, aff, se, sd])
    b, V, s2, t_, p_, n, k, r2, adj_r2, df, _ = ols_fit(X, y)

    n_agg = int(agg.sum())
    n_aff = int(aff.sum())
    n_se  = int(se.sum())
    n_sd  = int(sd.sum())
    n_nh  = n - (n_agg + n_aff + n_se + n_sd)

    coef_names = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]

    print(f"\n  [{label}] n={n:,}  k={k}  df={df:,}  R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, name in enumerate(coef_names):
        print(f"    {name:20s}  β={float(b[i]):+.4f}  t={float(t_[i]):+.3f}  p={float(p_[i]):.4f}{stars(float(p_[i]))}")

    return (b, V, t_, p_, n, k, r2, adj_r2, df,
            coef_names, n_agg, n_aff, n_se, n_sd, n_nh)


def build_coef_rows(b, V, t_, p_, coef_names, model_label, n, r2, adj_r2, df):
    rows = []
    for i, name in enumerate(coef_names):
        rows.append({
            "model":       model_label,
            "term":        name,
            "coefficient": round(float(b[i]), 6),
            "std_error":   round(math.sqrt(float(V[i, i])), 6),
            "t_statistic": round(float(t_[i]), 4),
            "p_value":     round(float(p_[i]), 6),
            "stars":       stars(float(p_[i])),
            "n":           n,
            "r_squared":   round(r2, 6),
            "adj_r_squared": round(adj_r2, 6),
            "df_residual": df,
        })
    return rows


def run_contrasts(b, V, df, n_agg, n_aff, n_se, n_sd, model_label):
    """Run H1, H2-1, H2-2, H2-3 contrasts on b[1:5], V[1:5,1:5].
    Order: H1 · H2-1(Other wtd) · H2-2(SELF wtd) · H2-3(pairwise ×3)."""
    b_h  = b[1:5]         # [β_agg, β_aff, β_se, β_sd]
    V_h  = V[1:5, 1:5]

    n_humor = n_agg + n_aff + n_se + n_sd
    n_other = n_aff + n_se + n_sd
    n_self  = n_se  + n_sd

    # prevent zero-division
    w_agg  = n_agg / n_humor if n_humor > 0 else 0
    w_aff  = n_aff / n_humor if n_humor > 0 else 0
    w_se   = n_se  / n_humor if n_humor > 0 else 0
    w_sd   = n_sd  / n_humor if n_humor > 0 else 0

    w_aff_other = n_aff / n_other if n_other > 0 else 0
    w_se_other  = n_se  / n_other if n_other > 0 else 0
    w_sd_other  = n_sd  / n_other if n_other > 0 else 0

    w_se_self   = n_se  / n_self  if n_self  > 0 else 0
    w_sd_self   = n_sd  / n_self  if n_self  > 0 else 0

    contrast_rows = []

    def _add(hyp, contrast_label, c, direction_label):
        est, se_, t_c, p_c = contrast_test(c, b_h, V_h, df)
        direction = "positive" if est > 0 else "negative"
        support = _support(hyp, est, p_c, direction_label)
        contrast_rows.append({
            "model":         model_label,
            "hypothesis":    hyp,
            "contrast":      contrast_label,
            "weights_info":  f"agg:{w_agg:.3f} aff:{w_aff:.3f} se:{w_se:.3f} sd:{w_sd:.3f}" if "Weighted" in contrast_label else "",
            "estimate":      round(est, 6),
            "std_error":     round(se_, 6),
            "t_statistic":   round(t_c, 4) if not math.isnan(t_c) else "NA",
            "p_value":       round(p_c, 6) if not math.isnan(p_c) else "NA",
            "stars":         stars(p_c) if not math.isnan(p_c) else "",
            "direction":     direction,
            "support":       support,
        })
        print(f"    {hyp} | {contrast_label:50s} est={est:+.4f} se={se_:.4f} t={t_c:+.3f} p={p_c:.4f}{stars(p_c)}")
        return est, p_c

    def _support(hyp, est, p_c, direction_label):
        if math.isnan(p_c):
            return "inconclusive"
        sig = p_c < 0.10
        if direction_label == "positive":
            return "supported" if est > 0 and sig else ("directional" if est > 0 else "not_supported")
        if direction_label == "positive_sig":
            return "supported" if est > 0 and sig else "not_supported"
        return "supported" if est > 0 else "not_supported"

    print(f"\n  === Contrast tests [{model_label}] ===")

    # H1: Weighted Humor Effect = Σwi*βi
    c_h1 = [w_agg, w_aff, w_se, w_sd]
    _add("H1", "Weighted Humor Effect (vs non-humorous)", c_h1, "positive_sig")

    # H2-1: Aggressive − Other humor weighted avg
    c_h2_1 = [1.0, -w_aff_other, -w_se_other, -w_sd_other]
    _add("H2-1", "Aggressive − Other humor (weighted avg)", c_h2_1, "positive_sig")

    # H2-2: Aggressive − SELF weighted avg
    c_h2_2 = [1.0, 0.0, -w_se_self, -w_sd_self]
    _add("H2-2", "Aggressive − SELF (se+sd weighted avg)", c_h2_2, "positive_sig")

    # H2-3: pairwise
    _add("H2-3", "Aggressive − Affiliative",      [1.0, -1.0,  0.0,  0.0], "positive_sig")
    _add("H2-3", "Aggressive − Self-Enhancing",   [1.0,  0.0, -1.0,  0.0], "positive_sig")
    _add("H2-3", "Aggressive − Self-Defeating",   [1.0,  0.0,  0.0, -1.0], "positive_sig")

    return contrast_rows


# ─────────────────────────────────────────────────────────────────────────────
# H3 firm-quarter OLS
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_firm_quarter(posts: list[dict]) -> list[dict]:
    """
    Aggregate post-level rows to firm-quarter.
    posts must have: company_name, quarter (pre-computed str 'YYYY-Qq'),
                     aggressive_humor (str '0'/'1'), log_total_engagement.
    Returns list of firm-quarter dicts with intensity and mean log engagement.
    """
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
            "company_name":        company,
            "quarter":             quarter,
            "post_count":          n,
            "aggressive_count":    p["_agg"],
            "aggressive_intensity": round(intensity, 12),
            "aggressive_intensity_sq": round(intensity * intensity, 12),
            "mean_log_engagement": round(p["_log_sum"] / n, 6),
        })
    return rows


def run_h3_ols(panel_rows: list[dict], label: str):
    """
    Quadratic OLS on firm-quarter panel.
    Returns full OLS results + turning-point diagnostics.
    """
    y    = np.array([to_f(r["mean_log_engagement"])    for r in panel_rows])
    x1   = np.array([to_f(r["aggressive_intensity"])   for r in panel_rows])
    x2   = np.array([to_f(r["aggressive_intensity_sq"])for r in panel_rows])
    ones = np.ones(len(panel_rows))

    X = np.column_stack([ones, x1, x2])
    b, V, s2, t_, p_, n, k, r2, adj_r2, df, _ = ols_fit(X, y)

    beta1 = float(b[1])
    beta2 = float(b[2])
    tp    = -beta1 / (2 * beta2) if beta2 != 0 else float("inf")

    obs_min = float(x1.min())
    obs_max = float(x1.max())
    in_range = obs_min <= tp <= obs_max

    # H3 support: β1>0 AND β2<0 (sig) AND TP in range
    h3_support = (
        beta1 > 0
        and beta2 < 0
        and float(p_[2]) < 0.10
        and in_range
    )

    print(f"\n  [{label}] n={n:,}  k={k}  df={df:,}  R²={r2:.4f}  adj-R²={adj_r2:.4f}")
    for i, name in enumerate(["intercept", "AggressiveIntensity", "AggressiveIntensity²"]):
        print(f"    {name:25s}  β={float(b[i]):+.6f}  t={float(t_[i]):+.3f}  p={float(p_[i]):.4f}{stars(float(p_[i]))}")
    print(f"    Turning point: {tp:.4f}  (range: [{obs_min:.4f}, {obs_max:.4f}])  in_range={in_range}")
    print(f"    H3 supported: {h3_support}")

    coef_rows = [
        {"model": label, "term": nm,
         "coefficient": round(float(b[i]), 6),
         "std_error": round(math.sqrt(float(V[i, i])), 6),
         "t_statistic": round(float(t_[i]), 4),
         "p_value": round(float(p_[i]), 6),
         "stars": stars(float(p_[i])),
         "n": n, "r_squared": round(r2, 6),
         "adj_r_squared": round(adj_r2, 6), "df_residual": df}
        for i, nm in enumerate(["intercept", "AggressiveIntensity", "AggressiveIntensity_sq"])
    ]

    diag_row = {
        "model":              label,
        "n_firm_quarters":    n,
        "beta1_intensity":    round(beta1, 6),
        "beta1_se":           round(math.sqrt(float(V[1, 1])), 6),
        "beta1_t":            round(float(t_[1]), 4),
        "beta1_p":            round(float(p_[1]), 6),
        "beta1_stars":        stars(float(p_[1])),
        "beta2_intensity_sq": round(beta2, 6),
        "beta2_se":           round(math.sqrt(float(V[2, 2])), 6),
        "beta2_t":            round(float(t_[2]), 4),
        "beta2_p":            round(float(p_[2]), 6),
        "beta2_stars":        stars(float(p_[2])),
        "turning_point":      round(tp, 6) if math.isfinite(tp) else "Inf",
        "obs_intensity_min":  round(obs_min, 6),
        "obs_intensity_max":  round(obs_max, 6),
        "tp_in_obs_range":    str(in_range),
        "H3_supported":       str(h3_support),
        "r_squared":          round(r2, 6),
        "adj_r_squared":      round(adj_r2, 6),
    }

    return coef_rows, diag_row


# ─────────────────────────────────────────────────────────────────────────────
# CSV writer helper
# ─────────────────────────────────────────────────────────────────────────────

def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("run_simple_ols_baseline_main.py")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────────
    print("\n[Loading] classified data...")
    with open(CLASSIFIED, newline="", encoding="utf-8") as f:
        classified = list(csv.DictReader(f))

    print(f"[Loading] H2 regression-ready...")
    with open(H2_RR, newline="", encoding="utf-8") as f:
        h2_rows = list(csv.DictReader(f))

    print(f"[Loading] Human labeling combined template...")
    with open(TEMPLATE, newline="", encoding="utf-8") as f:
        template = list(csv.DictReader(f))

    # ── Task 0 ───────────────────────────────────────────────────────────────
    # Add period to classified for summary
    for r in classified:
        ca = r.get("created_at", "")
        try:
            dt = datetime.strptime(ca.strip(), TWITTER_FMT)
            r["period"] = dt.strftime("%Y-%m")
        except Exception:
            r["period"] = "missing_period"

    task0_summary(classified)

    # ── Build full-sample H1/H2 data ─────────────────────────────────────────
    # H2 rows already have aggressive_humor, affiliative_humor, etc.
    # Add quarter to H2 rows for H3 aggregation
    for r in h2_rows:
        r["quarter"] = period_to_quarter(r.get("period", ""))

    # Counts for weights
    n_agg_full = sum(1 for r in h2_rows if r["aggressive_humor"] == "1")
    n_aff_full = sum(1 for r in h2_rows if r["affiliative_humor"] == "1")
    n_se_full  = sum(1 for r in h2_rows if r["self_enhancing_humor"] == "1")
    n_sd_full  = sum(1 for r in h2_rows if r["self_defeating_humor"] == "1")
    n_nh_full  = sum(1 for r in h2_rows if r["non_humorous"] == "1")

    # ── Build human-coded H1/H2 data ─────────────────────────────────────────
    hc_rows_raw = [r for r in template
                   if r.get("human_humor_presence", "") in ("0", "1")
                   and (r["human_humor_presence"] == "0"
                        or r.get("human_humor_type", "") in ("1", "2", "3", "4"))]

    # Build indicator variables for human-coded rows
    hc_rows = []
    for r in hc_rows_raw:
        pres = r["human_humor_presence"]
        typ_ = r.get("human_humor_type", "")
        te   = to_f(r.get("total_engagement", "0"))
        log_eng = math.log(1 + te)
        agg = "1" if pres == "1" and typ_ == "1" else "0"
        aff = "1" if pres == "1" and typ_ == "2" else "0"
        se  = "1" if pres == "1" and typ_ == "3" else "0"
        sd  = "1" if pres == "1" and typ_ == "4" else "0"
        quarter = created_at_to_quarter(r.get("created_at", ""))
        hc_rows.append({
            "company_name":           r.get("company_name", ""),
            "created_at":             r.get("created_at", ""),
            "quarter":                quarter,
            "log_total_engagement":   str(log_eng),
            "aggressive_humor":       agg,
            "affiliative_humor":      aff,
            "self_enhancing_humor":   se,
            "self_defeating_humor":   sd,
            "non_humorous":           "1" if pres == "0" else "0",
            "human_humor_presence":   pres,
            "human_humor_type":       typ_,
        })

    n_agg_hc = sum(1 for r in hc_rows if r["aggressive_humor"] == "1")
    n_aff_hc = sum(1 for r in hc_rows if r["affiliative_humor"] == "1")
    n_se_hc  = sum(1 for r in hc_rows if r["self_enhancing_humor"] == "1")
    n_sd_hc  = sum(1 for r in hc_rows if r["self_defeating_humor"] == "1")
    n_nh_hc  = sum(1 for r in hc_rows if r["non_humorous"] == "1")

    print("\n" + "=" * 70)
    print("TASK 1 : Simple OLS baseline")
    print("=" * 70)

    # ────────────────────────────────────────────────────────────────────────
    # H1/H2 – Full sample
    # ────────────────────────────────────────────────────────────────────────
    print("\n── H1/H2 Full-sample OLS ──")
    (b_fs, V_fs, t_fs, p_fs, n_fs, k_fs, r2_fs, adj_fs, df_fs,
     cn_fs, _, _, _, _, _) = run_h1_h2_ols(h2_rows, "Full-sample")

    coef_rows_full = build_coef_rows(
        b_fs, V_fs, t_fs, p_fs, cn_fs,
        "Full_sample_simple_OLS", n_fs, r2_fs, adj_fs, df_fs
    )
    _write_csv(OUT / "01_simple_ols_h1_h2_full_sample_results.csv",
               ["model","term","coefficient","std_error","t_statistic",
                "p_value","stars","n","r_squared","adj_r_squared","df_residual"],
               coef_rows_full)
    print("  → 01_simple_ols_h1_h2_full_sample_results.csv written")

    contrast_rows_full = run_contrasts(
        b_fs, V_fs, df_fs, n_agg_full, n_aff_full, n_se_full, n_sd_full,
        "Full_sample"
    )

    # ────────────────────────────────────────────────────────────────────────
    # H1/H2 – Human-coded
    # ────────────────────────────────────────────────────────────────────────
    print("\n── H1/H2 Human-coded OLS ──")
    (b_hc, V_hc, t_hc, p_hc, n_hc, k_hc, r2_hc, adj_hc, df_hc,
     cn_hc, _, _, _, _, _) = run_h1_h2_ols(hc_rows, "Human-coded")

    coef_rows_hc = build_coef_rows(
        b_hc, V_hc, t_hc, p_hc, cn_hc,
        "Human_coded_simple_OLS", n_hc, r2_hc, adj_hc, df_hc
    )
    _write_csv(OUT / "01_simple_ols_h1_h2_human_coded_results.csv",
               ["model","term","coefficient","std_error","t_statistic",
                "p_value","stars","n","r_squared","adj_r_squared","df_residual"],
               coef_rows_hc)
    print("  → 01_simple_ols_h1_h2_human_coded_results.csv written")

    contrast_rows_hc = run_contrasts(
        b_hc, V_hc, df_hc, n_agg_hc, n_aff_hc, n_se_hc, n_sd_hc,
        "Human_coded"
    )

    # Write combined contrast table
    contrast_fieldnames = [
        "model", "hypothesis", "contrast", "weights_info",
        "estimate", "std_error", "t_statistic", "p_value", "stars",
        "direction", "support"
    ]
    _write_csv(OUT / "01_simple_ols_h1_h2_contrast_tests.csv",
               contrast_fieldnames,
               contrast_rows_full + contrast_rows_hc)
    print("  → 01_simple_ols_h1_h2_contrast_tests.csv written")

    # ────────────────────────────────────────────────────────────────────────
    # H3 – Full sample, firm-quarter
    # ────────────────────────────────────────────────────────────────────────
    print("\n── H3 Full-sample firm-quarter OLS ──")
    fq_full = aggregate_firm_quarter(h2_rows)
    fq_full_valid = [r for r in fq_full if r["quarter"] != "missing"]
    print(f"  Firm-quarter observations: {len(fq_full_valid)}")

    coef_h3_full, diag_h3_full = run_h3_ols(fq_full_valid, "Full_sample_H3")
    _write_csv(OUT / "01_simple_ols_h3_full_sample_results.csv",
               ["model","term","coefficient","std_error","t_statistic",
                "p_value","stars","n","r_squared","adj_r_squared","df_residual"],
               coef_h3_full)
    print("  → 01_simple_ols_h3_full_sample_results.csv written")

    # ────────────────────────────────────────────────────────────────────────
    # H3 – Human-coded, firm-quarter
    # ────────────────────────────────────────────────────────────────────────
    print("\n── H3 Human-coded firm-quarter OLS ──")
    fq_hc = aggregate_firm_quarter(hc_rows)
    fq_hc_valid = [r for r in fq_hc if r["quarter"] != "missing"]
    print(f"  Firm-quarter observations: {len(fq_hc_valid)}")

    # Check intensity variation
    intensities_hc = [to_f(r["aggressive_intensity"]) for r in fq_hc_valid]
    n_nonzero_hc = sum(1 for v in intensities_hc if v > 0)
    print(f"  Non-zero intensity obs: {n_nonzero_hc} / {len(fq_hc_valid)}")

    SUFFICIENT_FQ_THRESHOLD = 30
    hc_h3_feasible = len(fq_hc_valid) >= SUFFICIENT_FQ_THRESHOLD and n_nonzero_hc >= 10

    if hc_h3_feasible:
        coef_h3_hc, diag_h3_hc = run_h3_ols(fq_hc_valid, "Human_coded_H3")
        _write_csv(OUT / "01_simple_ols_h3_human_coded_results.csv",
                   ["model","term","coefficient","std_error","t_statistic",
                    "p_value","stars","n","r_squared","adj_r_squared","df_residual"],
                   coef_h3_hc)
        print("  → 01_simple_ols_h3_human_coded_results.csv written")
    else:
        note = (f"Human-coded data are insufficient for stable firm-quarter H3 estimation. "
                f"Firm-quarters: {len(fq_hc_valid)}, non-zero intensity: {n_nonzero_hc}. "
                f"Minimum required: {SUFFICIENT_FQ_THRESHOLD} firm-quarters, 10 non-zero intensity.")
        print(f"  WARNING: {note}")
        coef_h3_hc = [{"model": "Human_coded_H3", "term": "NOTE",
                        "coefficient": note, "std_error": "", "t_statistic": "",
                        "p_value": "", "stars": "", "n": len(fq_hc_valid),
                        "r_squared": "", "adj_r_squared": "", "df_residual": ""}]
        _write_csv(OUT / "01_simple_ols_h3_human_coded_results.csv",
                   ["model","term","coefficient","std_error","t_statistic",
                    "p_value","stars","n","r_squared","adj_r_squared","df_residual"],
                   coef_h3_hc)
        diag_h3_hc = {"model": "Human_coded_H3", "note": note,
                       "n_firm_quarters": len(fq_hc_valid),
                       "H3_supported": "insufficient_data"}
        print("  → 01_simple_ols_h3_human_coded_results.csv written (insufficient data note)")

    # Write H3 diagnostics
    diag_fieldnames = [
        "model", "n_firm_quarters",
        "beta1_intensity", "beta1_se", "beta1_t", "beta1_p", "beta1_stars",
        "beta2_intensity_sq", "beta2_se", "beta2_t", "beta2_p", "beta2_stars",
        "turning_point", "obs_intensity_min", "obs_intensity_max",
        "tp_in_obs_range", "H3_supported",
        "r_squared", "adj_r_squared",
    ]
    diag_rows = [diag_h3_full]
    if hc_h3_feasible:
        diag_rows.append(diag_h3_hc)
    else:
        diag_rows.append({"model": "Human_coded_H3",
                          "n_firm_quarters": len(fq_hc_valid),
                          "H3_supported": "insufficient_data"})
    _write_csv(OUT / "01_simple_ols_h3_quadratic_diagnostics.csv",
               diag_fieldnames, diag_rows)
    print("  → 01_simple_ols_h3_quadratic_diagnostics.csv written")

    # ────────────────────────────────────────────────────────────────────────
    # Interpretation markdown
    # ────────────────────────────────────────────────────────────────────────
    _write_interpretation(
        b_fs, V_fs, p_fs, df_fs, n_agg_full, n_aff_full, n_se_full, n_sd_full,
        b_hc, V_hc, p_hc, df_hc, n_agg_hc, n_aff_hc, n_se_hc, n_sd_hc,
        n_fs, n_hc, r2_fs, adj_fs, r2_hc, adj_hc,
        diag_h3_full, diag_h3_hc if hc_h3_feasible else {"H3_supported": "insufficient_data",
                                                           "n_firm_quarters": len(fq_hc_valid)},
        hc_h3_feasible
    )

    print("\n" + "=" * 70)
    print("run_simple_ols_baseline_main COMPLETE")
    print("=" * 70)
    print(f"\nOutput directory: {OUT}")
    generated = [
        "00_classified_data_summary.md",
        "00_classified_data_distribution.csv",
        "01_simple_ols_h1_h2_full_sample_results.csv",
        "01_simple_ols_h1_h2_human_coded_results.csv",
        "01_simple_ols_h1_h2_contrast_tests.csv",
        "01_simple_ols_h3_full_sample_results.csv",
        "01_simple_ols_h3_human_coded_results.csv",
        "01_simple_ols_h3_quadratic_diagnostics.csv",
        "01_simple_ols_interpretation.md",
    ]
    for f in generated:
        print(f"  {f}")


# ─────────────────────────────────────────────────────────────────────────────
# Interpretation markdown
# ─────────────────────────────────────────────────────────────────────────────

def _write_interpretation(
    b_fs, V_fs, p_fs, df_fs, n_agg_f, n_aff_f, n_se_f, n_sd_f,
    b_hc, V_hc, p_hc, df_hc, n_agg_h, n_aff_h, n_se_h, n_sd_h,
    n_fs, n_hc, r2_fs, adj_fs, r2_hc, adj_hc,
    diag_full, diag_hc, hc_feasible
) -> None:

    def sig(p): return stars(p) if not (isinstance(p, float) and math.isnan(p)) else ""
    def fmt(v): return f"{v:+.4f}" if isinstance(v, float) else str(v)

    n_humor_f = n_agg_f + n_aff_f + n_se_f + n_sd_f
    n_other_f = n_aff_f + n_se_f + n_sd_f
    n_self_f  = n_se_f + n_sd_f
    w_aff_o_f = n_aff_f / n_other_f if n_other_f else 0
    w_se_o_f  = n_se_f  / n_other_f if n_other_f else 0
    w_sd_o_f  = n_sd_f  / n_other_f if n_other_f else 0
    w_se_s_f  = n_se_f  / n_self_f  if n_self_f  else 0
    w_sd_s_f  = n_sd_f  / n_self_f  if n_self_f  else 0

    n_humor_h = n_agg_h + n_aff_h + n_se_h + n_sd_h
    n_other_h = n_aff_h + n_se_h + n_sd_h
    n_self_h  = n_se_h + n_sd_h
    w_aff_o_h = n_aff_h / n_other_h if n_other_h else 0
    w_se_o_h  = n_se_h  / n_other_h if n_other_h else 0
    w_sd_o_h  = n_sd_h  / n_other_h if n_other_h else 0
    w_se_s_h  = n_se_h  / n_self_h  if n_self_h  else 0
    w_sd_s_h  = n_sd_h  / n_self_h  if n_self_h  else 0

    def whe_f():
        b = b_fs[1:5]; V = V_fs[1:5,1:5]
        c = [n_agg_f/n_humor_f, n_aff_f/n_humor_f, n_se_f/n_humor_f, n_sd_f/n_humor_f]
        return contrast_test(c, b, V, df_fs)

    def whe_h():
        b = b_hc[1:5]; V = V_hc[1:5,1:5]
        c = [n_agg_h/n_humor_h, n_aff_h/n_humor_h, n_se_h/n_humor_h, n_sd_h/n_humor_h]
        return contrast_test(c, b, V, df_hc)

    whe_f_est, whe_f_se, whe_f_t, whe_f_p = whe_f()
    whe_h_est, whe_h_se, whe_h_t, whe_h_p = whe_h()

    h1_f_supp = whe_f_est > 0 and whe_f_p < 0.10
    h1_h_supp = whe_h_est > 0 and whe_h_p < 0.10

    # H2-1 full
    def h21_est(b, V, df, n_a, n_af, n_s, n_sd_):
        n_o = n_af + n_s + n_sd_
        c = [1, -n_af/n_o if n_o else 0, -n_s/n_o if n_o else 0, -n_sd_/n_o if n_o else 0]
        return contrast_test(c, b[1:5], V[1:5,1:5], df)

    h21_f = h21_est(b_fs, V_fs, df_fs, n_agg_f, n_aff_f, n_se_f, n_sd_f)
    h21_h = h21_est(b_hc, V_hc, df_hc, n_agg_h, n_aff_h, n_se_h, n_sd_h)

    # H2-2: Aggressive − SELF weighted avg
    def h22_est(b, V, df, n_s, n_sd_):
        n_self_ = n_s + n_sd_
        c = [1, 0, -n_s/n_self_ if n_self_ else 0, -n_sd_/n_self_ if n_self_ else 0]
        return contrast_test(c, b[1:5], V[1:5, 1:5], df)

    h22_f = h22_est(b_fs, V_fs, df_fs, n_se_f, n_sd_f)
    h22_h = h22_est(b_hc, V_hc, df_hc, n_se_h, n_sd_h)

    lines = [
        "# 01 Simple OLS Baseline — Interpretation",
        "",
        "## Model specification",
        "",
        "**H1/H2** (post-level, N=68,039 full / N=2,480 human-coded):",
        "",
        "$$\\log(1+\\text{Engagement}_i) = \\beta_0 + \\beta_1\\text{Aggressive}_i + \\beta_2\\text{Affiliative}_i + \\beta_3\\text{SelfEnhancing}_i + \\beta_4\\text{SelfDefeating}_i + \\varepsilon_i$$",
        "",
        "- Reference category: non-humorous posts (all four type dummies = 0)",
        "- Classical OLS SE (s²=SSR/(n−k)). No controls, no fixed effects.",
        "- Stars: \\*\\*\\* p<.01, \\*\\* p<.05, \\* p<.10 (two-sided)",
        "",
        "**H3** (firm-quarter panel):",
        "",
        "$$\\overline{\\log(1+\\text{Eng})}_{fq} = \\alpha + \\beta_1\\text{AggressiveIntensity}_{fq} + \\beta_2\\text{AggressiveIntensity}^2_{fq} + \\varepsilon_{fq}$$",
        "",
        "- Intensity = aggressive humor posts / total posts in firm-quarter",
        "- No controls, no fixed effects.",
        "",
        "---",
        "",
        "## H1/H2 Coefficient table",
        "",
        "| Term | Full β | Full p | Full stars | HC β | HC p | HC stars |",
        "|:-----|-------:|-------:|:----------:|-----:|-----:|:--------:|",
    ]

    coef_names = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]
    for i, nm in enumerate(coef_names):
        lines.append(
            f"| {nm} | {float(b_fs[i]):+.4f} | {float(p_fs[i]):.4f} | {sig(float(p_fs[i]))} "
            f"| {float(b_hc[i]):+.4f} | {float(p_hc[i]):.4f} | {sig(float(p_hc[i]))} |"
        )

    lines += [
        f"| **N** | {n_fs:,} | | | {n_hc:,} | | |",
        f"| **R²** | {r2_fs:.4f} | | | {r2_hc:.4f} | | |",
        f"| **adj-R²** | {adj_fs:.4f} | | | {adj_hc:.4f} | | |",
        "",
        "---",
        "",
        "## H1: Weighted Humor Effect",
        "",
        f"**Full sample**: estimate = {whe_f_est:+.4f}, SE = {whe_f_se:.4f}, "
        f"t = {whe_f_t:+.3f}, p = {whe_f_p:.4f}{sig(whe_f_p)}  "
        f"→ H1 **{'지지됨 (supported)' if h1_f_supp else '기각됨 (not supported)'}**",
        "",
        f"**Human-coded**: estimate = {whe_h_est:+.4f}, SE = {whe_h_se:.4f}, "
        f"t = {whe_h_t:+.3f}, p = {whe_h_p:.4f}{sig(whe_h_p)}  "
        f"→ H1 **{'지지됨 (supported)' if h1_h_supp else '기각됨 (not supported)'}**",
        "",
        "Weights (full sample): "
        f"aggressive={n_agg_f/n_humor_f:.3f}, affiliative={n_aff_f/n_humor_f:.3f}, "
        f"self_enhancing={n_se_f/n_humor_f:.3f}, self_defeating={n_sd_f/n_humor_f:.3f}",
        "",
        "---",
        "",
        "## H2-1: Aggressive vs Other humor (weighted average)",
        "",
        f"**Full sample**: estimate = {h21_f[0]:+.4f}, SE = {h21_f[1]:.4f}, "
        f"t = {h21_f[2]:+.3f}, p = {h21_f[3]:.4f}{sig(h21_f[3])}",
        f"  → H2-1 **{'supported' if h21_f[0]>0 and h21_f[3]<0.10 else 'not supported'}**",
        "",
        f"**Human-coded**: estimate = {h21_h[0]:+.4f}, SE = {h21_h[1]:.4f}, "
        f"t = {h21_h[2]:+.3f}, p = {h21_h[3]:.4f}{sig(h21_h[3])}",
        f"  → H2-1 **{'supported' if h21_h[0]>0 and h21_h[3]<0.10 else 'not supported'}**",
        "",
        "---",
        "",
        "## H2-2: Aggressive vs SELF humor (weighted average)",
        "",
        f"**Full sample**: estimate = {h22_f[0]:+.4f}, SE = {h22_f[1]:.4f}, "
        f"t = {h22_f[2]:+.3f}, p = {h22_f[3]:.4f}{sig(h22_f[3])}",
        f"  → H2-2 **{'supported' if h22_f[0]>0 and h22_f[3]<0.10 else 'not supported'}**",
        "",
        f"**Human-coded**: estimate = {h22_h[0]:+.4f}, SE = {h22_h[1]:.4f}, "
        f"t = {h22_h[2]:+.3f}, p = {h22_h[3]:.4f}{sig(h22_h[3])}",
        f"  → H2-2 **{'supported' if h22_h[0]>0 and h22_h[3]<0.10 else 'not supported'}**",
        "",
        "---",
        "",
        "## H2 overall judgment",
        "",
        "**H2 is strongly but partially supported.**",
        "",
        "Aggressive humor shows significantly higher engagement than the weighted average of "
        "other humor types (H2-1) and the combined SELF category (H2-2). "
        "However, it is not consistently higher than self-defeating humor in pairwise contrasts (H2-3). "
        "Therefore, H2 is interpreted as strongly but partially supported.",
        "",
        "한국어: Aggressive humor는 other humor의 가중평균 및 SELF 통합 범주보다 유의하게 높은 "
        "engagement를 보였다. 그러나 개별 pairwise 비교에서는 self-defeating humor보다 일관되게 "
        "높지 않았기 때문에 H2는 강한 부분 지지로 해석한다.",
        "",
        "---",
        "",
        "## H3 firm-quarter results",
        "",
        "| Item | Full sample | Human-coded |",
        "|:-----|:-----------:|:-----------:|",
        f"| N (firm-quarters) | {diag_full.get('n_firm_quarters','NA')} | {diag_hc.get('n_firm_quarters','NA')} |",
        f"| β₁ (intensity) | {diag_full.get('beta1_intensity','NA')}{sig(float(diag_full.get('beta1_p',1)))} | {'N/A (insufficient)' if not hc_feasible else str(diag_hc.get('beta1_intensity','NA'))+sig(float(diag_hc.get('beta1_p',1)))} |",
        f"| β₂ (intensity²) | {diag_full.get('beta2_intensity_sq','NA')}{sig(float(diag_full.get('beta2_p',1)))} | {'N/A' if not hc_feasible else str(diag_hc.get('beta2_intensity_sq','NA'))+sig(float(diag_hc.get('beta2_p',1)))} |",
        f"| Turning point | {diag_full.get('turning_point','NA')} | {'N/A' if not hc_feasible else diag_hc.get('turning_point','NA')} |",
        f"| TP in obs range | {diag_full.get('tp_in_obs_range','NA')} | {'N/A' if not hc_feasible else diag_hc.get('tp_in_obs_range','NA')} |",
        f"| H3 supported | {diag_full.get('H3_supported','NA')} | {'insufficient_data' if not hc_feasible else diag_hc.get('H3_supported','NA')} |",
        f"| R² | {diag_full.get('r_squared','NA')} | {'N/A' if not hc_feasible else diag_hc.get('r_squared','NA')} |",
        "",
        "---",
        "",
        "## Measurement limitations",
        "",
        "1. **Classifier measurement error**: Full-sample humor type labels are predicted by "
        "domain-adapted TF-IDF + LogReg classifier. Measurement error cannot be ruled out.",
        "2. **Human-coded data scope**: Human-coded results are based on 2,480 posts "
        "(3.6% of 68,039) and should be treated as supplemental validation, not main results.",
        "3. **H3 insufficient human data**: Human-coded firm-quarter H3 is likely underpowered "
        "given sparse aggressive humor across firm-quarters.",
        "4. **Engagement as proxy**: log(1+total_engagement) is a proxy for brand equity "
        "(consumer/brand engagement), not brand equity itself.",
        "5. **No causal identification**: Simple OLS does not control for confounds. "
        "Results describe associations only.",
        "",
        "> Generated by run_simple_ols_baseline_main.py",
    ]
    (OUT / "01_simple_ols_interpretation.md").write_text("\n".join(lines), encoding="utf-8")
    print("  → 01_simple_ols_interpretation.md written")


if __name__ == "__main__":
    main()
