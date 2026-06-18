"""
run_h1_exploratory_regression.py

Simple OLS check: humor presence → log total engagement.

Model:
  log_total_engagement = β0 + β1 * h1_humor_presence_pred_t50 + ε

  Method:  Simple OLS (no fixed effects, no control variables)
  SE:      Standard OLS SE
  Status:  exploratory — NOT confirmatory

IMPORTANT:
  - No firm fixed effects.
  - No month fixed effects.
  - No control variables.
  - This is a first exploratory association check only.
  - Results do NOT confirm H1.
  - H2/H3 are out of scope.

Outputs (h1_regression/results/):
  h1_regression_main_results.csv
  h1_regression_model_summary.csv
  h1_regression_dv_diagnostics.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
CI   = ROOT / "20260618expand" / "classifier_improvement"
H1   = CI / "h1_presence_only"
FC   = H1 / "full_corpus_classification" / "data"
REG  = H1 / "h1_regression"
RES  = REG / "results"

IN_POSTS    = FC / "fortune100_h1_presence_classified_posts.csv"
OUT_MAIN    = RES / "h1_regression_main_results.csv"
OUT_SUMMARY = RES / "h1_regression_model_summary.csv"
OUT_DV_DIAG = RES / "h1_regression_dv_diagnostics.csv"

REGRESSION_STATUS = "exploratory"
CLASSIFIER_MODEL  = "word_char_comb__lr_liblin_C01"
CLASSIFIER_STATUS = "provisional (batch1-only, OOF AUC=0.7811)"


def simple_ols(X: np.ndarray, y: np.ndarray) -> dict:
    """Simple OLS with intercept. X is (n,) predictor vector."""
    n = len(y)
    Xd = np.column_stack([np.ones(n), X])  # [intercept, predictor]
    k = Xd.shape[1]
    XtX = Xd.T @ Xd
    try:
        XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(XtX)
    coef = XtX_inv @ (Xd.T @ y)
    y_hat = Xd @ coef
    resid = y - y_hat
    df_resid = n - k
    mse = (resid @ resid) / df_resid
    se = np.sqrt(np.maximum(np.diag(XtX_inv) * mse, 0))
    t_stat = coef / np.where(se > 0, se, 1e-12)

    try:
        from scipy.stats import norm as scipy_norm
        p_val = 2 * (1 - scipy_norm.cdf(np.abs(t_stat)))
    except ImportError:
        def _normal_sf(z: float) -> float:
            a = abs(float(z)) / (2 ** 0.5)
            t = 1.0 / (1.0 + 0.3275911 * a)
            poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 +
                        t * (-1.453152027 + t * 1.061405429))))
            return float(np.exp(-a * a) * poly / 2)
        p_val = np.array([2 * _normal_sf(abs(tv)) for tv in t_stat])

    ss_res = float(resid @ resid)
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "intercept": round(float(coef[0]), 6),
        "coef":      round(float(coef[1]), 6),
        "se_intercept": round(float(se[0]), 6),
        "se":        round(float(se[1]), 6),
        "t_stat":    round(float(t_stat[1]), 4),
        "p_value":   round(float(p_val[1]), 6),
        "sig_10pct": "yes" if abs(t_stat[1]) > 1.645 else "no",
        "sig_5pct":  "yes" if abs(t_stat[1]) > 1.960 else "no",
        "sig_1pct":  "yes" if abs(t_stat[1]) > 2.576 else "no",
        "n_obs":     n,
        "r_squared": round(r2, 6),
    }


def main() -> None:
    print("=== run_h1_exploratory_regression ===")
    print(f"  Status: {REGRESSION_STATUS}")
    print(f"  Method: simple OLS (no FE, no controls)")
    print(f"  Classifier: {CLASSIFIER_MODEL} ({CLASSIFIER_STATUS})")

    # --- Load data ---
    if not IN_POSTS.exists():
        raise FileNotFoundError(f"Classified posts not found: {IN_POSTS}")
    print(f"  Loading: {IN_POSTS}")
    with open(IN_POSTS, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"  Rows loaded: {len(rows)}")

    # --- Parse fields (only DV and predictor needed) ---
    log_eng_list: list[float] = []
    t50_list: list[float] = []

    for r in rows:
        try:
            log_eng = float(r.get("log_total_engagement", "") or "nan")
            t50     = float(r.get("h1_humor_presence_pred_t50", "") or "nan")
        except (ValueError, TypeError):
            continue
        if log_eng != log_eng or t50 != t50:  # nan check
            continue
        log_eng_list.append(log_eng)
        t50_list.append(t50)

    log_eng = np.array(log_eng_list)
    t50     = np.array(t50_list)
    n       = len(log_eng)
    print(f"  Records after cleaning: {n}")
    if n < 1000:
        raise ValueError(f"Too few records: {n}")

    # --- DV diagnostics ---
    RES.mkdir(parents=True, exist_ok=True)
    dv_diag = [
        {"metric": "n_obs",             "value": n},
        {"metric": "dv_mean",           "value": round(float(log_eng.mean()), 4)},
        {"metric": "dv_median",         "value": round(float(np.median(log_eng)), 4)},
        {"metric": "dv_sd",             "value": round(float(log_eng.std()), 4)},
        {"metric": "dv_min",            "value": round(float(log_eng.min()), 4)},
        {"metric": "dv_max",            "value": round(float(log_eng.max()), 4)},
        {"metric": "dv_p01",            "value": round(float(np.quantile(log_eng, 0.01)), 4)},
        {"metric": "dv_p05",            "value": round(float(np.quantile(log_eng, 0.05)), 4)},
        {"metric": "dv_p95",            "value": round(float(np.quantile(log_eng, 0.95)), 4)},
        {"metric": "dv_p99",            "value": round(float(np.quantile(log_eng, 0.99)), 4)},
        {"metric": "humor_rate_t50",    "value": round(float(t50.mean()), 4)},
    ]
    with open(OUT_DV_DIAG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(dv_diag)
    print(f"  DV diagnostics → {OUT_DV_DIAG}")

    # --- Simple OLS ---
    print("\n  Running simple OLS: log_eng ~ intercept + h1_humor_presence_pred_t50")
    ols = simple_ols(t50, log_eng)

    main_row = {
        "spec_label":        "main_t50_simple_ols",
        "dv":                "log_total_engagement",
        "predictor":         "h1_humor_presence_pred_t50",
        "method":            "simple OLS (no FE, no controls)",
        "intercept":         ols["intercept"],
        "coef":              ols["coef"],
        "se":                ols["se"],
        "t_stat":            ols["t_stat"],
        "p_value":           ols["p_value"],
        "sig_10pct":         ols["sig_10pct"],
        "sig_5pct":          ols["sig_5pct"],
        "sig_1pct":          ols["sig_1pct"],
        "n_obs":             ols["n_obs"],
        "r_squared":         ols["r_squared"],
        "regression_status": REGRESSION_STATUS,
        "classifier_model":  CLASSIFIER_MODEL,
        "classifier_status": CLASSIFIER_STATUS,
    }

    MAIN_FIELDS = [
        "spec_label", "dv", "predictor", "method",
        "intercept", "coef", "se", "t_stat", "p_value",
        "sig_10pct", "sig_5pct", "sig_1pct",
        "n_obs", "r_squared",
        "regression_status", "classifier_model", "classifier_status",
    ]

    with open(OUT_MAIN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAIN_FIELDS)
        w.writeheader()
        w.writerow(main_row)
    print(f"  Written: {OUT_MAIN}")

    SUMMARY_FIELDS = [
        "spec", "dv", "predictor", "intercept",
        "coef", "se", "t_stat", "p_value", "sig_5pct",
        "n_obs", "r_squared",
    ]
    summary_row = {
        "spec":      main_row["spec_label"],
        "dv":        main_row["dv"],
        "predictor": main_row["predictor"],
        "intercept": main_row["intercept"],
        "coef":      main_row["coef"],
        "se":        main_row["se"],
        "t_stat":    main_row["t_stat"],
        "p_value":   main_row["p_value"],
        "sig_5pct":  main_row["sig_5pct"],
        "n_obs":     main_row["n_obs"],
        "r_squared": main_row["r_squared"],
    }
    with open(OUT_SUMMARY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        w.writerow(summary_row)
    print(f"  Written: {OUT_SUMMARY}")

    print("\n  === MAIN RESULT (EXPLORATORY — SIMPLE OLS) ===")
    print(f"  Model: log_eng = β0 + β1 * h1_humor_presence_pred_t50")
    print(f"  Method: simple OLS | no FE | no controls")
    print(f"  β0 (intercept) = {main_row['intercept']}")
    print(f"  β1 (humor t50) = {main_row['coef']}  SE = {main_row['se']}")
    print(f"  t = {main_row['t_stat']}  p = {main_row['p_value']:.6f}")
    print(f"  Significant at 5%: {main_row['sig_5pct']}")
    print(f"  N = {main_row['n_obs']}  R² = {main_row['r_squared']}")
    print(f"  Status: {REGRESSION_STATUS} — NOT confirmatory evidence")
    print("=== run_h1_exploratory_regression COMPLETE ===")


if __name__ == "__main__":
    main()
