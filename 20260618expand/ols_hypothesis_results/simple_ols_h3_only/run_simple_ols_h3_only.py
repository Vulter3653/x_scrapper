#!/usr/bin/env python3
"""Run H3-only simple quadratic OLS diagnostic.

Scope is intentionally narrow:
  - H3 only
  - firm-month unit of analysis
  - no controls
  - no fixed effects
  - no H1/H2 variables
  - no post-level aggressive dummy or humor-type dummies
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from scipy.stats import t as t_dist

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INPUT = ROOT / "20260618expand" / "classifier_improvement" / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"

CLASSIFIER_LIMITATION = (
    "classifier-predicted aggressive labels from the current domain-adapted classifier; "
    "preliminary diagnostic evidence only; aggressive/type classifier leakage risk and "
    "NOT_A_CANDIDATE limitations remain; not robust or causal evidence"
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return "ns"


def pctl(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] * (hi - pos) + sorted_values[hi] * (pos - lo)


def ols(y: np.ndarray, x: np.ndarray) -> dict[str, object]:
    n, k = x.shape
    beta = np.linalg.solve(x.T @ x, x.T @ y)
    resid = y - x @ beta
    df_resid = n - k
    s2 = float((resid @ resid) / df_resid)
    vcov = s2 * np.linalg.inv(x.T @ x)
    se = np.sqrt(np.diag(vcov))
    t_stats = beta / se
    p_vals = 2 * t_dist.sf(np.abs(t_stats), df=df_resid)
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    ss_res = float(resid @ resid)
    r2 = 1.0 - ss_res / ss_tot
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_resid
    return {
        "beta": beta,
        "se": se,
        "t": t_stats,
        "p": p_vals,
        "n": n,
        "k": k,
        "df_resid": df_resid,
        "r2": r2,
        "adj_r2": adj_r2,
    }


def classify_pattern(b1: float, b2: float, p2: float, tp_in_range: bool) -> tuple[str, bool, str]:
    if b1 > 0 and b2 < 0:
        if p2 < 0.05 and tp_in_range:
            return "inverted-U", True, "H3 supported in this simple diagnostic: beta1>0, beta2<0, beta2 statistically significant, and turning point is inside the observed range."
        if p2 >= 0.05:
            return "no curvature support", False, "H3 not sufficiently supported: beta1>0 and beta2<0, but beta2 is not statistically significant."
        return "no curvature support", False, "H3 not substantively supported: signs fit an inverted-U, but the turning point is outside the observed intensity range."
    if b1 < 0 and b2 > 0:
        return "U-shaped", False, "H3 not supported: coefficient signs indicate a U-shaped pattern, opposite to H3."
    if abs(b2) < 1e-12:
        if b1 > 0:
            return "monotonic positive", False, "H3 not supported: no quadratic curvature; relationship is approximately monotonic positive."
        if b1 < 0:
            return "monotonic negative", False, "H3 not supported: no quadratic curvature; relationship is approximately monotonic negative."
    if b2 > 0:
        return "U-shaped", False, "H3 not supported: beta2>0, so the curve is not inverted-U."
    if b1 > 0:
        return "monotonic positive", False, "H3 not supported under the stated criteria."
    if b1 < 0:
        return "monotonic negative", False, "H3 not supported under the stated criteria."
    return "no curvature support", False, "H3 not supported under the stated criteria."


def main() -> int:
    rows = read_rows(INPUT)
    required = {
        "company_name", "period", "aggressive_humor_usage_intensity",
        "aggressive_humor_usage_intensity_sq", "mean_log_total_engagement",
    }
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError(f"Missing required columns: {sorted(missing)}")

    clean = []
    for row in rows:
        intensity = as_float(row["aggressive_humor_usage_intensity"])
        intensity_sq = as_float(row["aggressive_humor_usage_intensity_sq"])
        dv = as_float(row["mean_log_total_engagement"])
        if math.isnan(intensity) or math.isnan(intensity_sq) or math.isnan(dv):
            continue
        clean.append({
            "company_name": row["company_name"],
            "period": row["period"],
            "aggressive_intensity": intensity,
            "aggressive_intensity_sq": intensity_sq,
            "mean_log1p_engagement": dv,
        })
    if len(clean) < 4:
        raise RuntimeError("Insufficient firm-month rows for quadratic OLS")

    firms = sorted({r["company_name"] for r in clean})
    months = sorted({r["period"] for r in clean})
    intensity = [r["aggressive_intensity"] for r in clean]
    dv = [r["mean_log1p_engagement"] for r in clean]
    sorted_intensity = sorted(intensity)
    sorted_dv = sorted(dv)

    y = np.array(dv, dtype=float)
    x1 = np.array(intensity, dtype=float)
    x2 = np.array([r["aggressive_intensity_sq"] for r in clean], dtype=float)
    x = np.column_stack([np.ones(len(clean)), x1, x2])
    fit = ols(y, x)

    beta = fit["beta"]
    se = fit["se"]
    t_stats = fit["t"]
    p_vals = fit["p"]
    b1 = float(beta[1])
    b2 = float(beta[2])
    p2 = float(p_vals[2])
    observed_min = min(intensity)
    observed_max = max(intensity)
    turning_point = -b1 / (2 * b2) if b2 != 0 else float("nan")
    tp_in_range = (not math.isnan(turning_point)) and observed_min <= turning_point <= observed_max
    pattern, h3_supported, interpretation = classify_pattern(b1, b2, p2, tp_in_range)

    sample_row = {
        "total_firm_month_observations": len(clean),
        "number_of_firms": len(firms),
        "number_of_months": len(months),
        "aggressive_intensity_mean": f"{statistics.mean(intensity):.6f}",
        "aggressive_intensity_sd": f"{statistics.stdev(intensity):.6f}",
        "aggressive_intensity_min": f"{observed_min:.6f}",
        "aggressive_intensity_max": f"{observed_max:.6f}",
        "aggressive_intensity_p25": f"{pctl(sorted_intensity, 0.25):.6f}",
        "aggressive_intensity_median": f"{statistics.median(sorted_intensity):.6f}",
        "aggressive_intensity_p75": f"{pctl(sorted_intensity, 0.75):.6f}",
        "mean_log1p_engagement_mean": f"{statistics.mean(dv):.6f}",
        "mean_log1p_engagement_sd": f"{statistics.stdev(dv):.6f}",
    }
    write_csv(OUT / "simple_ols_h3_sample_distribution.csv", [sample_row])

    variables = ["intercept", "aggressive_intensity", "aggressive_intensity_sq"]
    reg_rows = []
    for i, var in enumerate(variables):
        reg_rows.append({
            "variable": var,
            "coefficient": f"{float(beta[i]):.6f}",
            "classical_OLS_SE": f"{float(se[i]):.6f}",
            "t_stat": f"{float(t_stats[i]):.6f}",
            "p_value": f"{float(p_vals[i]):.6f}",
            "stars": stars(float(p_vals[i])),
            "N": fit["n"],
            "R_squared": f"{float(fit['r2']):.6f}",
            "adjusted_R_squared": f"{float(fit['adj_r2']):.6f}",
            "df_resid": fit["df_resid"],
            "controls_included": "false",
            "fixed_effects_included": "false",
            "classifier_limitation": CLASSIFIER_LIMITATION,
        })
    write_csv(OUT / "simple_ols_h3_regression_results.csv", reg_rows)

    diag_row = {
        "beta1_intensity": f"{b1:.6f}",
        "beta2_intensity_squared": f"{b2:.6f}",
        "beta1_sign": "positive" if b1 > 0 else "negative" if b1 < 0 else "zero",
        "beta2_sign": "positive" if b2 > 0 else "negative" if b2 < 0 else "zero",
        "beta2_p_value": f"{p2:.6f}",
        "turning_point": f"{turning_point:.6f}" if not math.isnan(turning_point) else "undefined",
        "observed_intensity_min": f"{observed_min:.6f}",
        "observed_intensity_max": f"{observed_max:.6f}",
        "turning_point_in_observed_range": str(tp_in_range).lower(),
        "pattern": pattern,
        "H3_supported": str(h3_supported).lower(),
        "interpretation": interpretation,
    }
    write_csv(OUT / "simple_ols_h3_quadratic_diagnostics.csv", [diag_row])

    spec = f"""# Simple OLS H3 Model Specification\n\n## Model\n\n```text\nmean_log1p_engagement_ft = alpha + beta1 * aggressive_intensity_ft + beta2 * aggressive_intensity_sq_ft + epsilon_ft\n```\n\n## Scope\n\n- Hypothesis: H3 only\n- Unit of analysis: firm x month\n- Dependent variable: firm-month mean log(1 + engagement), stored as `mean_log_total_engagement` in the source panel\n- Independent variables: `aggressive_humor_usage_intensity`, `aggressive_humor_usage_intensity_sq`\n- Controls included: false\n- Fixed effects included: false\n- H1 humor presence variables included: false\n- H2 humor type dummies included: false\n- Post-level aggressive dummy included: false\n\n## Explicit Exclusions\n\nNo firm fixed effects, year fixed effects, month fixed effects, text controls, hashtag controls, mention controls, emoji controls, post-format controls, H1 variables, H2 variables, or post-level type dummies are included.\n\n## H3 Criteria\n\nH3 is supported only if beta1 > 0, beta2 < 0, beta2 is statistically significant, and the turning point `-beta1 / (2 * beta2)` lies inside the observed aggressive intensity range.\n\n## Data Source\n\n`{INPUT.relative_to(ROOT)}`\n\n## Limitation\n\n{CLASSIFIER_LIMITATION}. This is a preliminary diagnostic baseline, not robust causal evidence.\n"""
    (OUT / "simple_ols_h3_model_specification.md").write_text(spec, encoding="utf-8")

    interp = f"""# Simple OLS H3 Interpretation\n\n## Model\n\n```text\nmean_log1p_engagement ~ aggressive_intensity + aggressive_intensity_sq\n```\n\nThis file reports H3 only. H1 and H2 are not analyzed. Controls and fixed effects are not included.\n\n## Sample\n\n- Unit of analysis: firm x month\n- N: {len(clean):,}\n- Firms: {len(firms):,}\n- Months: {len(months):,}\n- Aggressive intensity range: [{observed_min:.6f}, {observed_max:.6f}]\n\n## Simple Quadratic OLS Result\n\n- beta1 aggressive_intensity: {b1:.6f} (p={float(p_vals[1]):.6f}, {stars(float(p_vals[1]))})\n- beta2 aggressive_intensity_sq: {b2:.6f} (p={p2:.6f}, {stars(p2)})\n- turning point: {turning_point:.6f}\n- turning point in observed range: {str(tp_in_range).lower()}\n- pattern: {pattern}\n- H3_supported: {str(h3_supported).lower()}\n\n## Interpretation\n\n{interpretation}\n\n## Boundary\n\nThis is a preliminary H3-only simple OLS diagnostic. It excludes all controls and fixed effects by design. Even if coefficients are statistically significant, this result should not be treated as robust evidence or a causal estimate. The aggressive intensity variable is based on classifier-predicted aggressive labels, and classifier leakage / NOT_A_CANDIDATE limitations must be carried forward.\n"""
    (OUT / "simple_ols_h3_interpretation.md").write_text(interp, encoding="utf-8")

    # Guard against accidentally adding controls or FE flags to the regression table.
    reg_text = (OUT / "simple_ols_h3_regression_results.csv").read_text(encoding="utf-8").lower()
    if "controls_included,true" in reg_text or "fixed_effects_included,true" in reg_text:
        raise RuntimeError("Controls or fixed effects were marked as included in H3-only output")

    print("\n=== Simple OLS H3 only complete ===")
    print(f"N={fit['n']} R2={float(fit['r2']):.6f} adj_R2={float(fit['adj_r2']):.6f}")
    print(f"beta1={b1:.6f}, beta2={b2:.6f}, beta2_p={p2:.6f}")
    print(f"turning_point={turning_point:.6f}, in_range={tp_in_range}, H3_supported={h3_supported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
