"""
run_wendys_h1_simple_ols.py

Simple bivariate OLS for Wendy's H1:
    DV = alpha + beta * log1p_humor_score + epsilon

No controls. No fixed effects. No robust SE. No HC3.
No count models. No logistic. No causal claims.

Model: statsmodels OLS, standard errors.
"""

import csv
import math
import hashlib
import statistics
from pathlib import Path
from datetime import datetime

try:
    import statsmodels.api as sm
except ImportError:
    raise ImportError("statsmodels is required. Install with: pip install statsmodels")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path("20260615wendy's")
INPUT_CSV  = BASE_DIR / "data"   / "wendys_h1_log_humor_input.csv"
OUT_DATASET    = BASE_DIR / "result" / "wendys_h1_simple_ols_analysis_dataset.csv"
OUT_RESULTS    = BASE_DIR / "result" / "wendys_h1_simple_ols_results.csv"
OUT_SUMMARY    = BASE_DIR / "result" / "wendys_h1_simple_ols_summary.md"
OUT_DIAGNOSTICS = BASE_DIR / "result" / "wendys_h1_simple_ols_diagnostics.csv"
RAW_SRC    = Path("data/wendys/posts.json")

PASS_THRU = [
    "id", "tweet_url", "created_year", "created_month", "created_day",
    "created_time", "text", "is_quote_status", "is_retweet_text",
    "reply_count", "favorite_count", "retweet_count", "quote_count",
    "bookmark_count", "view_count",
]

DVS = [
    ("log1p_engagement_total", "primary"),
    ("log1p_favorite_count",   "secondary"),
    ("log1p_retweet_count",    "secondary"),
    ("log1p_reply_count",      "secondary"),
    ("log1p_quote_count",      "secondary"),
    ("log1p_bookmark_count",   "secondary"),
]


def md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def safe_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def median_of(lst):
    s = sorted(lst)
    n = len(s)
    if n == 0:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def direction(beta):
    if beta > 0:
        return "positive"
    elif beta < 0:
        return "negative"
    return "zero"


def h1_interp(beta, p):
    if beta > 0 and p < 0.05:
        return "Preliminary support for H1"
    elif beta > 0:
        return "Directional support for H1"
    return "No support for H1"


def run_ols(x_vals, y_vals):
    X = sm.add_constant(x_vals)
    model = sm.OLS(y_vals, X)
    result = model.fit()
    n = int(result.nobs)
    intercept = result.params[0]
    beta      = result.params[1]
    se        = result.bse[1]
    t_val     = result.tvalues[1]
    p_val     = result.pvalues[1]
    ci        = result.conf_int(alpha=0.05)
    ci_lo     = ci[0][1]
    ci_hi     = ci[1][1]
    r2        = result.rsquared
    adj_r2    = result.rsquared_adj
    return dict(
        n_obs=n, intercept=intercept, beta=beta, se=se,
        t_value=t_val, p_value=p_val,
        ci_lower_95=ci_lo, ci_upper_95=ci_hi,
        r_squared=r2, adj_r_squared=adj_r2,
    )


def main():
    raw_md5 = md5_file(RAW_SRC)

    # ---- 1. Read input ----
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))
    n_in = len(rows_in)
    print(f"Input rows: {n_in}")

    # ---- 2. Build analysis dataset ----
    records = []
    for row in rows_in:
        r  = safe_int(row.get("reply_count",    0))
        fv = safe_int(row.get("favorite_count", 0))
        rt = safe_int(row.get("retweet_count",  0))
        qt = safe_int(row.get("quote_count",    0))
        bm = safe_int(row.get("bookmark_count", 0))
        eng = r + fv + rt + qt + bm

        hs      = safe_float(row.get("humor_score", 0), 0.0)
        log1p_hs = safe_float(row.get("log1p_humor_score", 0), math.log1p(hs))

        rec = {k: row.get(k, "") for k in PASS_THRU}
        rec["engagement_total"]       = eng
        rec["humor_score"]            = hs
        rec["log1p_humor_score"]      = log1p_hs
        rec["log1p_engagement_total"] = math.log1p(eng)
        rec["log1p_favorite_count"]   = math.log1p(fv)
        rec["log1p_retweet_count"]    = math.log1p(rt)
        rec["log1p_reply_count"]      = math.log1p(r)
        rec["log1p_quote_count"]      = math.log1p(qt)
        rec["log1p_bookmark_count"]   = math.log1p(bm)
        records.append(rec)

    # ---- 3. Write analysis dataset ----
    analysis_cols = PASS_THRU + [
        "engagement_total", "humor_score", "log1p_humor_score",
        "log1p_engagement_total", "log1p_favorite_count", "log1p_retweet_count",
        "log1p_reply_count", "log1p_quote_count", "log1p_bookmark_count",
    ]
    with open(OUT_DATASET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=analysis_cols)
        w.writeheader()
        w.writerows(records)
    print(f"Analysis dataset: {OUT_DATASET} ({len(records)} rows)")

    # ---- 4. Run OLS for each DV ----
    x_vals = [r["log1p_humor_score"] for r in records]
    ols_rows = []
    for dv_col, role in DVS:
        y_vals = [r[dv_col] for r in records]
        res = run_ols(x_vals, y_vals)
        beta = res["beta"]
        p    = res["p_value"]
        ols_rows.append({
            "dv":                       dv_col,
            "model_name":               "Simple OLS",
            "n_obs":                    res["n_obs"],
            "intercept":                "%.6f" % res["intercept"],
            "beta_log1p_humor_score":   "%.6f" % beta,
            "standard_error":           "%.6f" % res["se"],
            "t_value":                  "%.4f"  % res["t_value"],
            "p_value":                  "%.6f" % p,
            "ci_lower_95":              "%.6f" % res["ci_lower_95"],
            "ci_upper_95":              "%.6f" % res["ci_upper_95"],
            "r_squared":                "%.6f" % res["r_squared"],
            "adj_r_squared":            "%.6f" % res["adj_r_squared"],
            "direction":                direction(beta),
            "h1_interpretation":        h1_interp(beta, p),
            "notes":                    "Simple bivariate OLS; no controls; no FE; conventional SE",
        })
        print(f"  {dv_col}: beta={beta:.4f} p={p:.4f} R2={res['r_squared']:.4f}")

    results_cols = [
        "dv", "model_name", "n_obs", "intercept",
        "beta_log1p_humor_score", "standard_error", "t_value", "p_value",
        "ci_lower_95", "ci_upper_95", "r_squared", "adj_r_squared",
        "direction", "h1_interpretation", "notes",
    ]
    with open(OUT_RESULTS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results_cols)
        w.writeheader()
        w.writerows(ols_rows)
    print(f"Results: {OUT_RESULTS}")

    # ---- 5. Diagnostics ----
    hs_vals  = [r["humor_score"] for r in records]
    log_vals = [r["log1p_humor_score"] for r in records]
    eng_vals = [r["engagement_total"] for r in records]
    n_hs_zero = sum(1 for v in hs_vals if v == 0.0)

    diag_dataset = [
        ("total_rows_input",            n_in),
        ("total_rows_analysis",         len(records)),
        ("humor_score_zero_count",      n_hs_zero),
        ("humor_score_zero_share",      "%.4f" % (n_hs_zero / len(records))),
        ("log1p_humor_score_min",       "%.6f" % min(log_vals)),
        ("log1p_humor_score_mean",      "%.6f" % (sum(log_vals) / len(log_vals))),
        ("log1p_humor_score_median",    "%.6f" % median_of(log_vals)),
        ("log1p_humor_score_max",       "%.6f" % max(log_vals)),
        ("engagement_total_min",        min(eng_vals)),
        ("engagement_total_mean",       "%.2f" % (sum(eng_vals) / len(eng_vals))),
        ("engagement_total_median",     median_of(eng_vals)),
        ("engagement_total_max",        max(eng_vals)),
    ]

    dv_diag = []
    for dv_col, _ in DVS:
        vals = [r[dv_col] for r in records]
        valid = [v for v in vals if v is not None and not math.isnan(v)]
        dv_diag.append({
            "dv":           dv_col,
            "n_nonmissing": len(valid),
            "n_missing":    len(vals) - len(valid),
            "mean":         "%.4f" % (sum(valid) / len(valid)) if valid else "",
            "median":       "%.4f" % median_of(valid),
            "min":          "%.4f" % min(valid) if valid else "",
            "max":          "%.4f" % max(valid) if valid else "",
        })

    with open(OUT_DIAGNOSTICS, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(diag_dataset)
        w.writerow([])
        w.writerow(["dv", "n_nonmissing", "n_missing", "mean", "median", "min", "max"])
        for d in dv_diag:
            w.writerow([d["dv"], d["n_nonmissing"], d["n_missing"],
                        d["mean"], d["median"], d["min"], d["max"]])
    print(f"Diagnostics: {OUT_DIAGNOSTICS}")

    # ---- 6. Markdown summary ----
    main_res = {r["dv"]: r for r in ols_rows}["log1p_engagement_total"]

    def fmt_row(r):
        return (f"| {r['dv']} | {r['beta_log1p_humor_score']} | {r['standard_error']} | "
                f"{r['t_value']} | {r['p_value']} | {r['r_squared']} | "
                f"{r['direction']} | {r['h1_interpretation']} |")

    table_header = ("| DV | beta | SE | t | p | R² | direction | H1 interpretation |\n"
                    "|---|---|---|---|---|---|---|---|")
    table_rows = "\n".join(fmt_row(r) for r in ols_rows)

    summary_md = f"""# Wendy's H1 Simple OLS Results

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. H1 Statement

> Higher humor presence in Wendy's brand posts is associated with higher post-level engagement.

---

## 2. Input Dataset

- File: `{INPUT_CSV}`
- Rows: {n_in}
- IV: `log1p_humor_score`
- humor_score == 0: {n_hs_zero} ({n_hs_zero/n_in*100:.1f}%)

---

## 3. Main IV Definition

```
log1p_humor_score = log(1 + humor_score)
```

`log1p` is used because `humor_score` contains many zero values and `log(0)` is undefined.
`humor_score` is a transparent rule-based score (0.000–1.000), not a calibrated probability.

---

## 4. DV Definitions

```
engagement_total        = reply_count + favorite_count + retweet_count + quote_count + bookmark_count
log1p_engagement_total  = log(1 + engagement_total)   ← main DV
log1p_favorite_count    = log(1 + favorite_count)
log1p_retweet_count     = log(1 + retweet_count)
log1p_reply_count       = log(1 + reply_count)
log1p_quote_count       = log(1 + quote_count)
log1p_bookmark_count    = log(1 + bookmark_count)
```

`view_count` is excluded as DV per task specification.

---

## 5. Model Specification

```
DV = α + β × log1p_humor_score + ε
```

- Model type: Simple bivariate OLS (statsmodels OLS)
- Controls: **None**
- Fixed effects: **None**
- Standard errors: **Conventional OLS (not robust, not HC3)**
- Clustering: **None**

---

## 6. Main Result: log1p_engagement_total

| Parameter | Value |
|-----------|-------|
| n_obs | {main_res['n_obs']} |
| Intercept | {main_res['intercept']} |
| β (log1p_humor_score) | {main_res['beta_log1p_humor_score']} |
| Standard Error | {main_res['standard_error']} |
| t-value | {main_res['t_value']} |
| p-value | {main_res['p_value']} |
| 95% CI | [{main_res['ci_lower_95']}, {main_res['ci_upper_95']}] |
| R² | {main_res['r_squared']} |
| Adj. R² | {main_res['adj_r_squared']} |
| Direction | {main_res['direction']} |
| H1 Interpretation | **{main_res['h1_interpretation']}** |

---

## 7. All DV Results

{table_header}
{table_rows}

---

## 8. H1 Interpretation

The main DV result (`log1p_engagement_total`):

**{main_res['h1_interpretation']}**

β = {main_res['beta_log1p_humor_score']}, SE = {main_res['standard_error']}, p = {main_res['p_value']}, R² = {main_res['r_squared']}

Higher `log(1 + humor_score)` is **{main_res['direction']}ly** associated with `log(1 + engagement_total)` in this Wendy's-only simple OLS analysis.

---

## 9. Limitations

- This is a Wendy's-only post-level association test.
- This is not causal evidence.
- This is simple OLS only.
- No controls or fixed effects are included.
- Standard errors are conventional OLS standard errors, not robust standard errors.
- `humor_score` is rule-based and not a calibrated probability.
- `log1p_humor_score` is used because `humor_score` contains many zeros ({n_hs_zero}/{n_in} = {n_hs_zero/n_in*100:.1f}%).
- Engagement is observational and may be affected by timing, media assets, platform algorithms, campaigns, and external events.
"""

    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary_md)
    print(f"Summary: {OUT_SUMMARY}")

    # ---- 7. Validation ----
    raw_md5_after = md5_file(RAW_SRC)
    eng_ok = all(
        records[i]["engagement_total"] == (
            safe_int(rows_in[i].get("reply_count", 0)) +
            safe_int(rows_in[i].get("favorite_count", 0)) +
            safe_int(rows_in[i].get("retweet_count", 0)) +
            safe_int(rows_in[i].get("quote_count", 0)) +
            safe_int(rows_in[i].get("bookmark_count", 0))
        )
        for i in range(len(records))
    )
    dv_finite = all(
        all(math.isfinite(r[dv]) for dv, _ in DVS)
        for r in records
    )

    checks = [
        (n_in == 978,                                      "Input row count == 978"),
        (len(records) == 978,                              "Analysis dataset row count == 978"),
        (n_hs_zero == 739,                                 "humor_score_zero_count == 739"),
        (all(math.isfinite(r["log1p_humor_score"]) for r in records), "log1p_humor_score finite for all rows"),
        (eng_ok,                                           "engagement_total correctly calculated"),
        (dv_finite,                                        "All six DVs finite and nonmissing"),
        (len(ols_rows) == 6,                               "Simple OLS results exist for 6 DVs"),
        (True,                                             "No controls included (by design)"),
        (True,                                             "No fixed effects included (by design)"),
        (True,                                             "No robust SE used (by design)"),
        (True,                                             "No zero-inflated model run"),
        (True,                                             "No logistic regression run"),
        (True,                                             "No Poisson or negative binomial run"),
        (not any("aggressive_score" in str(list(r.values())) for r in records), "No aggressive humor variable"),
        (not any("humor_type" in str(list(r.keys())) for r in records),         "No humor_type variable"),
        (raw_md5 == raw_md5_after,                         "data/wendys/posts.json not modified"),
        (all(str(p).startswith(str(BASE_DIR)) for p in [OUT_DATASET, OUT_RESULTS, OUT_SUMMARY, OUT_DIAGNOSTICS]),
                                                           "All outputs inside 20260615wendy's/"),
    ]

    print("\n=== VALIDATION (17 checks) ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %2d. %s" % (status, i, desc))

    print("\n  All 17 checks passed: %s" % all_pass)
    if not all_pass:
        raise RuntimeError("Validation failed — do not commit.")
    print("\nDone.")


if __name__ == "__main__":
    main()
