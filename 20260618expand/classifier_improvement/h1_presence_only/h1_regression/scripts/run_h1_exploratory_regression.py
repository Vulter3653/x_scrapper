"""
run_h1_exploratory_regression.py

Runs exploratory H1 regression on provisional humor presence labels.

H1 (exploratory): humor presence → log total engagement

Main specification:
  DV:         log_total_engagement
  Predictor:  h1_humor_presence_pred_t50  (binary, t=0.50)
  Controls:   text_length, hashtag_count, mention_count
  FE:         firm fixed effects + month fixed effects
  Method:     OLS with iterative two-way FE demeaning (Gauss-Seidel)
  SE:         HC1 heteroskedasticity-robust

Robustness specifications:
  - Predictor: t40 / t60 / continuous probability
  - DV: winsorized 1% / 5%
  - DV: trimmed (top-1% / top-5% deleted)

IMPORTANT:
  - This is an EXPLORATORY regression. Results are provisional.
  - Classifier is batch1-only (OOF AUC=0.7811, FH F1=0.4770).
  - H1 regression results do NOT confirm H1.
  - H2/H3 are out of scope.

Outputs (h1_regression/results/):
  h1_regression_main_results.csv
  h1_regression_robustness_results.csv
  h1_regression_model_summary.csv
  h1_regression_dv_diagnostics.csv
"""

from __future__ import annotations

import csv
import datetime
import sys
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
CI = ROOT / "20260618expand" / "classifier_improvement"
H1 = CI / "h1_presence_only"
FC = H1 / "full_corpus_classification" / "data"
REG = H1 / "h1_regression"
RES = REG / "results"

IN_POSTS = FC / "fortune100_h1_presence_classified_posts.csv"
OUT_MAIN     = RES / "h1_regression_main_results.csv"
OUT_ROBUST   = RES / "h1_regression_robustness_results.csv"
OUT_SUMMARY  = RES / "h1_regression_model_summary.csv"
OUT_DV_DIAG  = RES / "h1_regression_dv_diagnostics.csv"

REGRESSION_STATUS = "exploratory"
CLASSIFIER_MODEL  = "word_char_comb__lr_liblin_C01"
CLASSIFIER_STATUS = "provisional (batch1-only, OOF AUC=0.7811)"


def parse_month(created_at: str) -> str:
    try:
        dt = datetime.datetime.strptime(created_at.strip(), "%a %b %d %H:%M:%S +0000 %Y")
        return dt.strftime("%Y-%m")
    except Exception:
        return ""


def winsorize(arr: np.ndarray, lower: float = 0.0, upper: float = 1.0) -> np.ndarray:
    lo = np.quantile(arr, lower)
    hi = np.quantile(arr, upper)
    return np.clip(arr, lo, hi)


def demean_twoway(arr: np.ndarray, g1: np.ndarray, g2: np.ndarray,
                  n_iter: int = 100, tol: float = 1e-7) -> np.ndarray:
    """Iterative two-way FE demeaning (Gauss-Seidel)."""
    out = arr.copy().astype(float)
    for _ in range(n_iter):
        prev = out.copy()
        for g in np.unique(g1):
            mask = g1 == g
            out[mask] -= out[mask].mean()
        for g in np.unique(g2):
            mask = g2 == g
            out[mask] -= out[mask].mean()
        if np.max(np.abs(out - prev)) < tol:
            break
    return out


def ols_fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """OLS with HC1 robust SE. Returns (coef, se_ols, se_hc1)."""
    n, k = X.shape
    XtX = X.T @ X
    try:
        XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(XtX)
    coef = XtX_inv @ (X.T @ y)
    resid = y - X @ coef
    df_resid = n - k
    mse = (resid @ resid) / df_resid

    # OLS SE
    se_ols = np.sqrt(np.maximum(np.diag(XtX_inv) * mse, 0))

    # HC1 robust SE (White's with n/(n-k) correction)
    e2 = resid ** 2
    meat = (X * e2[:, None]).T @ X
    hc1 = (n / df_resid) * (XtX_inv @ meat @ XtX_inv)
    se_hc1 = np.sqrt(np.maximum(np.diag(hc1), 0))

    return coef, se_ols, se_hc1


def r_squared(y: np.ndarray, y_hat: np.ndarray) -> float:
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def run_spec(y_raw: np.ndarray, predictors: dict[str, np.ndarray],
             main_pred: str, firm_idx: np.ndarray, month_idx: np.ndarray,
             dv_label: str, spec_label: str) -> dict:
    """Run one regression spec: demean, OLS, report coefficient on main_pred."""
    pred_names = list(predictors.keys())
    X_raw = np.column_stack([predictors[k] for k in pred_names])

    # Two-way demeaning
    y_dm = demean_twoway(y_raw, firm_idx, month_idx)
    X_dm = np.column_stack([
        demean_twoway(X_raw[:, j], firm_idx, month_idx)
        for j in range(X_raw.shape[1])
    ])

    coef, se_ols, se_hc1 = ols_fit(X_dm, y_dm)
    y_hat = X_dm @ coef

    # p-values using normal approximation (large-n)
    t_ols  = coef / np.where(se_ols  > 0, se_ols,  1e-12)
    t_hc1  = coef / np.where(se_hc1 > 0, se_hc1, 1e-12)

    try:
        from scipy.stats import norm as scipy_norm
        p_ols  = 2 * (1 - scipy_norm.cdf(np.abs(t_ols)))
        p_hc1  = 2 * (1 - scipy_norm.cdf(np.abs(t_hc1)))
    except ImportError:
        # Normal approximation via erfcc
        def normal_sf(z):
            return 0.5 * (1 - np.array([float(np.tanh(x * (1 - x * x / 3) / np.sqrt(2 / np.pi)))
                                         for x in np.atleast_1d(z)]))
        p_ols  = 2 * normal_sf(np.abs(t_ols))
        p_hc1  = 2 * normal_sf(np.abs(t_hc1))

    idx = pred_names.index(main_pred)
    n   = len(y_raw)
    r2  = r_squared(y_dm, y_hat)

    return {
        "spec_label":          spec_label,
        "dv":                  dv_label,
        "main_predictor":      main_pred,
        "coef":                round(float(coef[idx]), 6),
        "se_ols":              round(float(se_ols[idx]), 6),
        "se_hc1":              round(float(se_hc1[idx]), 6),
        "t_ols":               round(float(t_ols[idx]), 4),
        "t_hc1":               round(float(t_hc1[idx]), 4),
        "p_ols":               round(float(p_ols[idx]), 6),
        "p_hc1":               round(float(p_hc1[idx]), 6),
        "sig_hc1_10pct":       "yes" if abs(t_hc1[idx]) > 1.645 else "no",
        "sig_hc1_5pct":        "yes" if abs(t_hc1[idx]) > 1.960 else "no",
        "sig_hc1_1pct":        "yes" if abs(t_hc1[idx]) > 2.576 else "no",
        "n_obs":               n,
        "r_sq_within":         round(r2, 6),
        "all_coefs":           dict(zip(pred_names, [round(float(c), 6) for c in coef])),
        "all_se_hc1":          dict(zip(pred_names, [round(float(s), 6) for s in se_hc1])),
        "fe":                  "firm + month",
        "regression_status":   REGRESSION_STATUS,
        "classifier_model":    CLASSIFIER_MODEL,
        "classifier_status":   CLASSIFIER_STATUS,
    }


def main() -> None:
    print("=== run_h1_exploratory_regression ===")
    print(f"  Status: {REGRESSION_STATUS}")
    print(f"  Classifier: {CLASSIFIER_MODEL} ({CLASSIFIER_STATUS})")

    # --- Load data ---
    if not IN_POSTS.exists():
        raise FileNotFoundError(f"Classified posts not found: {IN_POSTS}")
    print(f"  Loading: {IN_POSTS}")
    with open(IN_POSTS, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"  Rows loaded: {len(rows)}")

    # --- Parse fields ---
    print("  Parsing fields...")
    records = []
    for r in rows:
        ca    = r.get("created_at", "")
        month = parse_month(ca)
        if not month:
            continue
        try:
            log_eng = float(r.get("log_total_engagement", "") or "nan")
            tlen    = float(r.get("text_length", "") or "nan")
            htag    = float(r.get("hashtag_count", "") or "nan")
            ment    = float(r.get("mention_count", "") or "nan")
            t50     = float(r.get("h1_humor_presence_pred_t50", "") or "nan")
            t40     = float(r.get("h1_humor_presence_pred_t40", "") or "nan")
            t60     = float(r.get("h1_humor_presence_pred_t60", "") or "nan")
            prob    = float(r.get("h1_humor_presence_probability", "") or "nan")
            company = r.get("company_name", "")
        except (ValueError, TypeError):
            continue
        if any(np.isnan(v) for v in [log_eng, tlen, htag, ment, t50, t40, t60, prob]):
            continue
        if not company or not month:
            continue
        records.append({
            "log_eng": log_eng, "tlen": tlen, "htag": htag, "ment": ment,
            "t50": t50, "t40": t40, "t60": t60, "prob": prob,
            "company": company, "month": month,
        })

    print(f"  Records after cleaning: {len(records)}")
    if len(records) < 1000:
        raise ValueError("Too few records for regression")

    # --- Encode FE groups ---
    firms  = sorted(set(r["company"] for r in records))
    months = sorted(set(r["month"]   for r in records))
    firm_map  = {f: i for i, f in enumerate(firms)}
    month_map = {m: i for i, m in enumerate(months)}
    print(f"  Firms: {len(firms)}   Months: {len(months)}")

    firm_idx  = np.array([firm_map[r["company"]] for r in records])
    month_idx = np.array([month_map[r["month"]]  for r in records])

    # --- Arrays ---
    log_eng = np.array([r["log_eng"] for r in records])
    tlen    = np.array([r["tlen"]    for r in records])
    htag    = np.array([r["htag"]    for r in records])
    ment    = np.array([r["ment"]    for r in records])
    t50     = np.array([r["t50"]     for r in records])
    t40     = np.array([r["t40"]     for r in records])
    t60     = np.array([r["t60"]     for r in records])
    prob    = np.array([r["prob"]    for r in records])

    # DV diagnostics
    RES.mkdir(parents=True, exist_ok=True)
    dv_diag = [
        {"metric": "n_obs",             "value": len(log_eng)},
        {"metric": "dv_mean",           "value": round(float(log_eng.mean()), 4)},
        {"metric": "dv_median",         "value": round(float(np.median(log_eng)), 4)},
        {"metric": "dv_sd",             "value": round(float(log_eng.std()), 4)},
        {"metric": "dv_min",            "value": round(float(log_eng.min()), 4)},
        {"metric": "dv_max",            "value": round(float(log_eng.max()), 4)},
        {"metric": "dv_p01",            "value": round(float(np.quantile(log_eng, 0.01)), 4)},
        {"metric": "dv_p05",            "value": round(float(np.quantile(log_eng, 0.05)), 4)},
        {"metric": "dv_p95",            "value": round(float(np.quantile(log_eng, 0.95)), 4)},
        {"metric": "dv_p99",            "value": round(float(np.quantile(log_eng, 0.99)), 4)},
        {"metric": "n_zero_engagement", "value": int((log_eng == 0).sum())},
        {"metric": "humor_rate_t50",    "value": round(float(t50.mean()), 4)},
        {"metric": "humor_rate_t40",    "value": round(float(t40.mean()), 4)},
        {"metric": "humor_rate_t60",    "value": round(float(t60.mean()), 4)},
        {"metric": "mean_probability",  "value": round(float(prob.mean()), 4)},
    ]
    with open(OUT_DV_DIAG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(dv_diag)
    print(f"  DV diagnostics → {OUT_DV_DIAG}")

    controls = {"text_length": tlen, "hashtag_count": htag, "mention_count": ment}

    # ============================
    # MAIN SPECIFICATION
    # ============================
    print("\n  Running MAIN specification (t50, log_eng, firm+month FE)...")
    main_preds = {**{"h1_humor_presence_t50": t50}, **controls}
    main_res   = run_spec(log_eng, main_preds, "h1_humor_presence_t50",
                          firm_idx, month_idx, "log_total_engagement", "main_t50")
    print(f"    coef_t50={main_res['coef']}  se_hc1={main_res['se_hc1']}  "
          f"t_hc1={main_res['t_hc1']}  p_hc1={main_res['p_hc1']:.4f}  "
          f"sig_5pct={main_res['sig_hc1_5pct']}")

    # ============================
    # ROBUSTNESS SPECIFICATIONS
    # ============================
    robust_results = []

    # Predictor variants
    for pred_name, pred_arr, label in [
        ("h1_humor_presence_t40",  t40,  "robust_t40"),
        ("h1_humor_presence_t60",  t60,  "robust_t60"),
        ("h1_humor_probability",   prob, "robust_prob"),
    ]:
        print(f"  Running robustness: {label}...")
        preds = {**{pred_name: pred_arr}, **controls}
        res   = run_spec(log_eng, preds, pred_name, firm_idx, month_idx,
                         "log_total_engagement", label)
        robust_results.append(res)
        print(f"    coef={res['coef']}  t_hc1={res['t_hc1']}  "
              f"sig_5pct={res['sig_hc1_5pct']}")

    # DV variants: winsorization
    for pct_lo, pct_hi, label in [
        (0.00, 0.99, "robust_dv_win99"),
        (0.00, 0.95, "robust_dv_win95"),
    ]:
        print(f"  Running robustness: {label}...")
        dv_w = winsorize(log_eng, lower=pct_lo, upper=pct_hi)
        preds = {**{"h1_humor_presence_t50": t50}, **controls}
        res   = run_spec(dv_w, preds, "h1_humor_presence_t50", firm_idx, month_idx,
                         f"log_eng_winsorized_{int(pct_hi*100)}pct", label)
        robust_results.append(res)
        print(f"    coef={res['coef']}  t_hc1={res['t_hc1']}  "
              f"sig_5pct={res['sig_hc1_5pct']}")

    # DV variants: trimming (delete extreme observations)
    for pct_trim, label in [(0.99, "robust_dv_trim99"), (0.95, "robust_dv_trim95")]:
        print(f"  Running robustness: {label}...")
        thresh = np.quantile(log_eng, pct_trim)
        mask   = log_eng <= thresh
        n_trim = int(mask.sum())
        preds  = {**{"h1_humor_presence_t50": t50[mask]}, **{
            "text_length": tlen[mask], "hashtag_count": htag[mask], "mention_count": ment[mask]
        }}
        res = run_spec(log_eng[mask], preds, "h1_humor_presence_t50",
                       firm_idx[mask], month_idx[mask],
                       f"log_eng_trimmed_{int(pct_trim*100)}pct", label)
        robust_results.append(res)
        print(f"    n={n_trim}  coef={res['coef']}  t_hc1={res['t_hc1']}  "
              f"sig_5pct={res['sig_hc1_5pct']}")

    # ============================
    # WRITE OUTPUTS
    # ============================
    main_keys = [
        "spec_label", "dv", "main_predictor",
        "coef", "se_ols", "se_hc1", "t_ols", "t_hc1",
        "p_ols", "p_hc1",
        "sig_hc1_10pct", "sig_hc1_5pct", "sig_hc1_1pct",
        "n_obs", "r_sq_within", "fe",
        "regression_status", "classifier_model", "classifier_status",
    ]
    with open(OUT_MAIN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=main_keys, extrasaction="ignore")
        w.writeheader()
        w.writerow(main_res)
    print(f"\n  Written: {OUT_MAIN}")

    robust_keys = main_keys.copy()
    with open(OUT_ROBUST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=robust_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(robust_results)
    print(f"  Written: {OUT_ROBUST} ({len(robust_results)} robustness specs)")

    # Summary
    all_specs = [main_res] + robust_results
    summary_rows = []
    for r in all_specs:
        summary_rows.append({
            "spec":           r["spec_label"],
            "dv":             r["dv"],
            "main_predictor": r["main_predictor"],
            "coef":           r["coef"],
            "se_hc1":         r["se_hc1"],
            "t_hc1":          r["t_hc1"],
            "p_hc1":          r["p_hc1"],
            "sig_hc1_5pct":   r["sig_hc1_5pct"],
            "n_obs":          r["n_obs"],
            "r_sq_within":    r["r_sq_within"],
        })

    with open(OUT_SUMMARY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    print(f"  Written: {OUT_SUMMARY} ({len(summary_rows)} specs)")

    print("\n  === MAIN RESULT (EXPLORATORY) ===")
    print(f"  Spec: {main_res['spec_label']}")
    print(f"  DV: {main_res['dv']}")
    print(f"  Predictor: {main_res['main_predictor']}")
    print(f"  coef = {main_res['coef']}  SE(HC1) = {main_res['se_hc1']}")
    print(f"  t(HC1) = {main_res['t_hc1']}  p(HC1) = {main_res['p_hc1']:.4f}")
    print(f"  Significant at 5%: {main_res['sig_hc1_5pct']}")
    print(f"  N obs = {main_res['n_obs']}  R²_within = {main_res['r_sq_within']}")
    print(f"  Status: {REGRESSION_STATUS} — NOT confirmatory evidence")
    print("=== run_h1_exploratory_regression COMPLETE ===")


if __name__ == "__main__":
    main()
