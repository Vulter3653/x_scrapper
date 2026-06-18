"""
run_h1_h2_h3_models.py

OLS regressions for H1, H2, H3 using numpy for matrix operations.
- H1: humor_presence → log_total_engagement (post-level, firm FE + year FE)
- H2: humor type dummies → log_total_engagement (post-level, firm FE + year FE)
- H3: aggressive_humor_usage_intensity (quadratic) → mean_log_total_engagement (firm-month, FE)

SE: non-robust (standard OLS SE). No HC/robust/cluster SE.
p-values: t-distribution, two-tailed.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/user/.local/pypackages")))
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
MT = ROOT / "20260618expand" / "model_transfer"

H1_RR = MT / "data" / "regression_ready" / "h1_post_level_regression_ready.csv"
H2_RR = MT / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"
H3_RR = MT / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"

OUT_H1_RESULTS = MT / "results" / "h1" / "h1_regression_results.csv"
OUT_H2_RESULTS = MT / "results" / "h2" / "h2_regression_results.csv"
OUT_H2_CONTRAST = MT / "results" / "h2" / "h2_aggressive_contrast_tests.csv"
OUT_H3_RESULTS = MT / "results" / "h3" / "h3_regression_results.csv"
OUT_H3_TURNING = MT / "results" / "h3" / "h3_turning_point_diagnostics.csv"
OUT_H1_REPORT = MT / "reports" / "h1_results.md"
OUT_H2_REPORT = MT / "reports" / "h2_results.md"
OUT_H3_REPORT = MT / "reports" / "h3_results.md"


def safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── t-distribution p-value from scratch (Lentz continued fraction) ──────────

def _betai(a: float, b: float, x: float) -> float:
    if x < 0.0 or x > 1.0:
        return float("nan")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    # Use symmetry when x > (a+1)/(a+b+2)
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betai(b, a, 1.0 - x)
    # Lentz continued fraction
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta) / a
    # Modified Lentz
    TINY = 1e-30
    EPS = 3e-7
    MAXIT = 200
    f = TINY
    C = f
    D = 0.0
    for m in range(MAXIT):
        for step in range(2):
            if step == 0:
                if m == 0:
                    d = 1.0
                else:
                    d = m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m))
            else:
                d = -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1))
            D = 1.0 + d * D
            if abs(D) < TINY:
                D = TINY
            D = 1.0 / D
            C = 1.0 + d / C
            if abs(C) < TINY:
                C = TINY
            delta = C * D
            f *= delta
            if abs(delta - 1.0) < EPS:
                return front * (f - TINY)
    return front * (f - TINY)


def t_pvalue_twotail(t: float, df: float) -> float:
    if math.isnan(t) or df <= 0:
        return float("nan")
    x = df / (df + t * t)
    p_one_tail = 0.5 * _betai(df / 2.0, 0.5, x)
    return min(2.0 * p_one_tail, 1.0)


# ── Entity-demeaning (within transformation) ─────────────────────────────────

def demean_by_groups(arr: np.ndarray, group_ids: np.ndarray) -> np.ndarray:
    result = arr.copy().astype(float)
    for gid in np.unique(group_ids):
        mask = group_ids == gid
        result[mask] -= result[mask].mean(axis=0)
    return result


# ── OLS ──────────────────────────────────────────────────────────────────────

def ols(y: np.ndarray, X: np.ndarray) -> dict:
    n, k = X.shape
    try:
        XtX = X.T @ X
        XtX_inv = np.linalg.pinv(XtX)
        beta = XtX_inv @ (X.T @ y)
        yhat = X @ beta
        resid = y - yhat
        sse = float(resid @ resid)
        df_resid = n - k
        if df_resid <= 0:
            raise ValueError("df_resid <= 0")
        sigma2 = sse / df_resid
        var_beta = sigma2 * XtX_inv
        se = np.sqrt(np.diag(var_beta))
        t_vals = beta / np.where(se > 0, se, np.nan)
        p_vals = np.array([t_pvalue_twotail(float(t), df_resid) for t in t_vals])
        sst = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - sse / sst if sst > 0 else float("nan")
        return {
            "n": n, "k": k, "df_resid": df_resid,
            "beta": beta, "se": se, "t": t_vals, "p": p_vals,
            "r2": r2, "sse": sse, "sigma2": sigma2,
        }
    except Exception as e:
        return {"error": str(e)}


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def write_results_csv(path: Path, results: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not results:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)


# ── H1 ───────────────────────────────────────────────────────────────────────

def run_h1() -> dict:
    print("\n--- H1: humor_presence → log_total_engagement ---")
    with open(H1_RR, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    firms = [r["company_name"] for r in rows]
    years = [r["year"] for r in rows]

    y = np.array([safe_float(r["log_total_engagement"]) for r in rows])
    humor = np.array([safe_float(r["humor_presence"]) for r in rows])
    text_len = np.array([safe_float(r["text_length"]) for r in rows])
    hashtag = np.array([safe_float(r["hashtag_count"]) for r in rows])
    mention = np.array([safe_float(r["mention_count"]) for r in rows])

    firm_ids = np.array(firms)
    year_ids = np.array(years)

    # Within-transform by firm then by year
    y_w = demean_by_groups(y, firm_ids)
    y_w = demean_by_groups(y_w, year_ids)

    X_raw = np.column_stack([humor, text_len, hashtag, mention])
    X_w = demean_by_groups(X_raw, firm_ids)
    X_w = demean_by_groups(X_w, year_ids)
    # Add within-demeaned intercept proxy (constant after FE is absorbed)
    X_w = np.column_stack([np.ones(len(y_w)), X_w])

    res = ols(y_w, X_w)
    if "error" in res:
        print(f"H1 OLS error: {res['error']}")
        return res

    var_names = ["(FE-absorbed constant)", "humor_presence", "text_length",
                 "hashtag_count", "mention_count"]

    results_rows = []
    for i, vn in enumerate(var_names):
        results_rows.append({
            "variable": vn,
            "coefficient": round(float(res["beta"][i]), 6),
            "se": round(float(res["se"][i]), 6),
            "t_stat": round(float(res["t"][i]), 4),
            "p_value": round(float(res["p"][i]), 4),
            "significance": stars(float(res["p"][i])),
            "n": res["n"],
            "r2_within": round(res["r2"], 4),
            "fixed_effects": "firm+year",
        })

    write_results_csv(OUT_H1_RESULTS, results_rows)

    beta_h = float(res["beta"][1])
    se_h = float(res["se"][1])
    p_h = float(res["p"][1])
    print(f"H1 humor_presence: β={beta_h:.4f}  SE={se_h:.4f}  p={p_h:.4f}{stars(p_h)}")
    print(f"N={res['n']}  R²(within)={res['r2']:.4f}")

    OUT_H1_RESULTS.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_H1_REPORT, "w", encoding="utf-8") as f:
        f.write(f"""# H1 Regression Results

## Model

```
log_total_engagement = β0 + β1*humor_presence + γ1*text_length + γ2*hashtag_count + γ3*mention_count
                     + firm FE + year FE + ε
```

Implementation: within-group demeaning (entity FE via Frisch-Waugh).
SE: non-robust standard OLS SE.

## Results (N = {res['n']})

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
{"".join(f"| {r['variable']} | {r['coefficient']} | {r['se']} | {r['t_stat']} | {r['p_value']} | {r['significance']} |" + chr(10) for r in results_rows)}

R² (within) = {res['r2']:.4f}

## H1 Interpretation

H1 predicts β1 > 0 (humor_presence positively associated with engagement).

β1 = {beta_h:.4f}  SE = {se_h:.4f}  p = {p_h:.4f} {stars(p_h)}

{"**H1 supported**: humor_presence coefficient is positive and statistically significant." if beta_h > 0 and p_h < 0.10 else "**H1 not supported** at p<.10." if beta_h <= 0 else f"**H1 directionally consistent** (β>0) but p={p_h:.4f} exceeds conventional threshold."}

## Fixed Effects

- Firm fixed effects: {len(set(firms))} firms
- Year fixed effects: {len(set(years))} years
- Controls: text_length, hashtag_count, mention_count
- emoji_count: excluded

## Claim Boundary

This analysis applies the Wendy's-trained TF-IDF LogReg classifier to Fortune Top 100 posts.
Results reflect model-transfer classification, not human-validated Fortune-wide labels.
""")

    return {"beta_humor": beta_h, "se": se_h, "p": p_h, "n": res["n"], "r2": res["r2"]}


# ── H2 ───────────────────────────────────────────────────────────────────────

def run_h2() -> dict:
    print("\n--- H2: humor type dummies → log_total_engagement ---")
    with open(H2_RR, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    firms = [r["company_name"] for r in rows]
    years = [r["year"] for r in rows]

    y = np.array([safe_float(r["log_total_engagement"]) for r in rows])
    agg = np.array([safe_float(r["aggressive_humor"]) for r in rows])
    aff = np.array([safe_float(r["affiliative_humor"]) for r in rows])
    se_humor = np.array([safe_float(r["self_enhancing_humor"]) for r in rows])
    sd_humor = np.array([safe_float(r["self_defeating_humor"]) for r in rows])
    text_len = np.array([safe_float(r["text_length"]) for r in rows])
    hashtag = np.array([safe_float(r["hashtag_count"]) for r in rows])
    mention = np.array([safe_float(r["mention_count"]) for r in rows])

    firm_ids = np.array(firms)
    year_ids = np.array(years)

    y_w = demean_by_groups(y, firm_ids)
    y_w = demean_by_groups(y_w, year_ids)

    X_raw = np.column_stack([agg, aff, se_humor, sd_humor, text_len, hashtag, mention])
    X_w = demean_by_groups(X_raw, firm_ids)
    X_w = demean_by_groups(X_w, year_ids)
    X_w = np.column_stack([np.ones(len(y_w)), X_w])

    res = ols(y_w, X_w)
    if "error" in res:
        print(f"H2 OLS error: {res['error']}")
        return res

    var_names = [
        "(FE-absorbed constant)",
        "aggressive_humor", "affiliative_humor",
        "self_enhancing_humor", "self_defeating_humor",
        "text_length", "hashtag_count", "mention_count",
    ]

    results_rows = []
    for i, vn in enumerate(var_names):
        results_rows.append({
            "variable": vn,
            "coefficient": round(float(res["beta"][i]), 6),
            "se": round(float(res["se"][i]), 6),
            "t_stat": round(float(res["t"][i]), 4),
            "p_value": round(float(res["p"][i]), 4),
            "significance": stars(float(res["p"][i])),
            "n": res["n"],
            "r2_within": round(res["r2"], 4),
            "fixed_effects": "firm+year",
        })

    write_results_csv(OUT_H2_RESULTS, results_rows)

    coef = {r["variable"]: r for r in results_rows}

    # Contrast tests: Aggressive > Affiliative / Self-Enhancing / Self-Defeating
    beta_agg = float(res["beta"][1])
    beta_aff = float(res["beta"][2])
    beta_se_h = float(res["beta"][3])
    beta_sd_h = float(res["beta"][4])

    n = res["n"]
    df = res["df_resid"]
    sigma2 = res["sigma2"]

    # XtX_inv for SE of linear combination
    X_raw2 = np.column_stack([np.ones(len(y_w)), agg, aff, se_humor, sd_humor, text_len, hashtag, mention])
    X_w2 = demean_by_groups(X_raw2, firm_ids)
    X_w2 = demean_by_groups(X_w2, year_ids)
    try:
        XtX_inv = np.linalg.pinv(X_w2.T @ X_w2)
    except Exception:
        XtX_inv = None

    def contrast_se(c_vec: np.ndarray) -> float:
        if XtX_inv is None:
            return float("nan")
        return float(math.sqrt(sigma2 * float(c_vec @ XtX_inv @ c_vec)))

    contrast_rows = []
    contrasts = [
        ("aggressive_vs_affiliative", beta_agg - beta_aff,
         np.array([0, 1, -1, 0, 0, 0, 0, 0], dtype=float)),
        ("aggressive_vs_self_enhancing", beta_agg - beta_se_h,
         np.array([0, 1, 0, -1, 0, 0, 0, 0], dtype=float)),
        ("aggressive_vs_self_defeating", beta_agg - beta_sd_h,
         np.array([0, 1, 0, 0, -1, 0, 0, 0], dtype=float)),
    ]
    for name, diff, c_vec in contrasts:
        c_se = contrast_se(c_vec)
        t_c = diff / c_se if c_se > 0 and not math.isnan(c_se) else float("nan")
        p_c = t_pvalue_twotail(t_c, df)
        contrast_rows.append({
            "contrast": name,
            "difference": round(diff, 6),
            "se": round(c_se, 6) if not math.isnan(c_se) else "nan",
            "t_stat": round(t_c, 4) if not math.isnan(t_c) else "nan",
            "p_value": round(p_c, 4) if not math.isnan(p_c) else "nan",
            "significance": stars(p_c) if not math.isnan(p_c) else "",
            "direction": "aggressive > other" if diff > 0 else "aggressive ≤ other",
        })
        print(f"  Contrast {name}: diff={diff:.4f}  p={p_c:.4f}{stars(p_c) if not math.isnan(p_c) else ''}")

    write_results_csv(OUT_H2_CONTRAST, contrast_rows)

    print(f"H2 aggressive: β={beta_agg:.4f}  SE={float(res['se'][1]):.4f}  "
          f"p={float(res['p'][1]):.4f}{stars(float(res['p'][1]))}")
    print(f"N={res['n']}  R²(within)={res['r2']:.4f}")

    OUT_H2_RESULTS.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_H2_REPORT, "w", encoding="utf-8") as f:
        f.write(f"""# H2 Regression Results

## Model

```
log_total_engagement = β0 + β1*aggressive + β2*affiliative + β3*self_enhancing
                     + β4*self_defeating
                     + γ1*text_length + γ2*hashtag_count + γ3*mention_count
                     + firm FE + year FE + ε
```

Reference group: non_humorous posts.
humor_presence and humor_presence × type interactions are NOT included (avoids perfect collinearity).
SE: non-robust standard OLS SE.

## Results (N = {res['n']})

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
{"".join(f"| {r['variable']} | {r['coefficient']} | {r['se']} | {r['t_stat']} | {r['p_value']} | {r['significance']} |" + chr(10) for r in results_rows)}

R² (within) = {res['r2']:.4f}

## Contrast Tests (Aggressive vs Other Types)

| Contrast | Difference | SE | t | p | Sig | Direction |
|---|---|---|---|---|---|---|
{"".join(f"| {r['contrast']} | {r['difference']} | {r['se']} | {r['t_stat']} | {r['p_value']} | {r['significance']} | {r['direction']} |" + chr(10) for r in contrast_rows)}

## H2 Interpretation

H2 predicts aggressive humor has larger engagement effect than other humor types.

aggressive β = {beta_agg:.4f}  SE = {float(res['se'][1]):.4f}  p = {float(res['p'][1]):.4f} {stars(float(res['p'][1]))}
affiliative β = {beta_aff:.4f}
self-enhancing β = {beta_se_h:.4f}
self-defeating β = {beta_sd_h:.4f}

## Aggressive Humor Sparsity Warning

The Wendy's-trained classifier may yield a different number of aggressive humor posts
for Fortune Top 100 than the original full_chain_master. If aggressive humor posts are
fewer than 200, H2 contrast interpretations should be treated with caution.

## Claim Boundary

Model-transfer classification from Wendy's TF-IDF LogReg. Not human-validated for Fortune Top 100.
Engagement is an engagement-based brand equity proxy.
Observational evidence only.
""")

    return {
        "beta_aggressive": beta_agg,
        "se_aggressive": float(res["se"][1]),
        "p_aggressive": float(res["p"][1]),
        "n": res["n"],
        "r2": res["r2"],
        "contrasts": contrast_rows,
    }


# ── H3 ───────────────────────────────────────────────────────────────────────

def run_h3() -> dict:
    print("\n--- H3: aggressive usage intensity (quadratic) → mean_log_engagement ---")
    with open(H3_RR, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n_total = len(rows)
    n_nonzero = sum(1 for r in rows if safe_float(r["aggressive_humor_usage_intensity"]) > 0)
    print(f"H3 firm-month rows: {n_total}  non-zero aggressive: {n_nonzero}")

    if n_nonzero < 50:
        print("WARNING: fewer than 50 non-zero aggressive rows → H3 exploratory only")
        h3_status = "exploratory_insufficient_variation"
    elif n_nonzero < 200:
        print("WARNING: fewer than 200 non-zero aggressive rows → H3 treat with caution")
        h3_status = "exploratory_sparse"
    else:
        h3_status = "confirmatory_candidate"

    firms = [r["company_name"] for r in rows]
    periods = [r["period"] for r in rows]

    y = np.array([safe_float(r["mean_log_total_engagement"]) for r in rows])
    intensity = np.array([safe_float(r["aggressive_humor_usage_intensity"]) for r in rows])
    intensity_sq = np.array([safe_float(r["aggressive_humor_usage_intensity_sq"]) for r in rows])
    text_len = np.array([safe_float(r["mean_text_length"]) for r in rows])
    hashtag = np.array([safe_float(r["mean_hashtag_count"]) for r in rows])
    mention = np.array([safe_float(r["mean_mention_count"]) for r in rows])

    firm_ids = np.array(firms)
    period_ids = np.array(periods)

    y_w = demean_by_groups(y, firm_ids)
    y_w = demean_by_groups(y_w, period_ids)

    X_raw = np.column_stack([intensity, intensity_sq, text_len, hashtag, mention])
    X_w = demean_by_groups(X_raw, firm_ids)
    X_w = demean_by_groups(X_w, period_ids)
    X_w = np.column_stack([np.ones(len(y_w)), X_w])

    res = ols(y_w, X_w)
    if "error" in res:
        print(f"H3 OLS error: {res['error']}")
        return res

    var_names = [
        "(FE-absorbed constant)",
        "aggressive_humor_usage_intensity",
        "aggressive_humor_usage_intensity_sq",
        "mean_text_length", "mean_hashtag_count", "mean_mention_count",
    ]

    results_rows = []
    for i, vn in enumerate(var_names):
        results_rows.append({
            "variable": vn,
            "coefficient": round(float(res["beta"][i]), 6),
            "se": round(float(res["se"][i]), 6),
            "t_stat": round(float(res["t"][i]), 4),
            "p_value": round(float(res["p"][i]), 4),
            "significance": stars(float(res["p"][i])),
            "n": res["n"],
            "r2_within": round(res["r2"], 4),
            "fixed_effects": "firm+period",
            "h3_status": h3_status,
        })

    write_results_csv(OUT_H3_RESULTS, results_rows)

    beta1 = float(res["beta"][1])
    beta2 = float(res["beta"][2])

    # Turning point: -β1 / (2*β2)
    turning_rows = []
    if abs(beta2) > 1e-12:
        turning_point = -beta1 / (2.0 * beta2)
        intensity_vals = [safe_float(r["aggressive_humor_usage_intensity"]) for r in rows]
        obs_min = min(intensity_vals)
        obs_max = max(intensity_vals)
        in_range = obs_min <= turning_point <= obs_max
        turning_rows.append({
            "beta1": round(beta1, 6),
            "beta2": round(beta2, 6),
            "turning_point": round(turning_point, 6),
            "observed_min": round(obs_min, 6),
            "observed_max": round(obs_max, 6),
            "turning_point_in_range": str(in_range),
            "inverted_u_shape": str(beta1 > 0 and beta2 < 0),
            "h3_status": h3_status,
        })
        print(f"H3 turning point: {turning_point:.4f}  in-range: {in_range}")
    else:
        turning_rows.append({
            "beta1": round(beta1, 6), "beta2": round(beta2, 6),
            "turning_point": "undefined (β2≈0)",
            "observed_min": "", "observed_max": "",
            "turning_point_in_range": "false",
            "inverted_u_shape": "false",
            "h3_status": h3_status,
        })

    write_results_csv(OUT_H3_TURNING, turning_rows)

    print(f"H3 β1={beta1:.4f}  β2={beta2:.4f}  p1={float(res['p'][1]):.4f}  "
          f"p2={float(res['p'][2]):.4f}")
    print(f"N={res['n']}  R²(within)={res['r2']:.4f}  status={h3_status}")

    OUT_H3_RESULTS.parent.mkdir(parents=True, exist_ok=True)

    tp_info = turning_rows[0]
    with open(OUT_H3_REPORT, "w", encoding="utf-8") as f:
        f.write(f"""# H3 Regression Results

## Status

**{h3_status}**

Non-zero aggressive intensity firm-month rows: {n_nonzero} / {n_total}

{"H3 is treated as exploratory/readiness evidence only due to insufficient variation in aggressive humor usage." if "exploratory" in h3_status else "H3 has sufficient variation for confirmatory analysis."}

## Model

```
mean_log_total_engagement = β0 + β1*aggressive_intensity + β2*aggressive_intensity²
                          + γ1*mean_text_length + γ2*mean_hashtag_count + γ3*mean_mention_count
                          + firm FE + period FE + ε
```

SE: non-robust standard OLS SE.

## Results (N = {res['n']})

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
{"".join(f"| {r['variable']} | {r['coefficient']} | {r['se']} | {r['t_stat']} | {r['p_value']} | {r['significance']} |" + chr(10) for r in results_rows)}

R² (within) = {res['r2']:.4f}

## Turning Point Diagnostics

| Item | Value |
|---|---|
| β1 (intensity) | {tp_info['beta1']} |
| β2 (intensity²) | {tp_info['beta2']} |
| Turning point | {tp_info['turning_point']} |
| Observed range | [{tp_info.get('observed_min','')}, {tp_info.get('observed_max','')}] |
| Turning point in range | {tp_info['turning_point_in_range']} |
| Inverted-U shape (β1>0, β2<0) | {tp_info['inverted_u_shape']} |

## H3 Criterion

H3 is supported if:
- β1 > 0 (positive linear term)
- β2 < 0 (negative quadratic term)
- Turning point falls inside observed intensity range

Current: β1={'positive' if beta1>0 else 'negative'}  β2={'negative' if beta2<0 else 'positive'}

## Claim Boundary

H3 aggressive_humor_usage_intensity is a usage rate (firm-period), not message-level semantic intensity.
This is exploratory evidence due to extreme sparsity in the current dataset.
""")

    return {
        "beta1": beta1, "beta2": beta2,
        "p1": float(res["p"][1]), "p2": float(res["p"][2]),
        "n": res["n"], "n_nonzero": n_nonzero,
        "status": h3_status,
    }


def main() -> None:
    print("=== run_h1_h2_h3_models ===")
    h1 = run_h1()
    h2 = run_h2()
    h3 = run_h3()

    print("\n=== SUMMARY ===")
    if "beta_humor" in h1:
        print(f"H1: β={h1['beta_humor']:.4f}  p={h1['p']:.4f}{stars(h1['p'])}  N={h1['n']}")
    if "beta_aggressive" in h2:
        print(f"H2: agg β={h2['beta_aggressive']:.4f}  p={h2['p_aggressive']:.4f}{stars(h2['p_aggressive'])}  N={h2['n']}")
    if "beta1" in h3:
        print(f"H3: β1={h3['beta1']:.4f}  β2={h3['beta2']:.4f}  status={h3['status']}  N={h3['n']}")
    print("\n=== run_h1_h2_h3_models COMPLETE ===")


if __name__ == "__main__":
    main()
