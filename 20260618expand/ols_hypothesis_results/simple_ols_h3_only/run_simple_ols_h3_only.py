"""
run_simple_ols_h3_only.py

Simple quadratic OLS diagnostic for H3.

Model (M1):
  mean_log1p_engagement_{ft} = α + β₁·AggressiveIntensity_{ft}
                                 + β₂·AggressiveIntensity²_{ft} + ε_{ft}

Unit of analysis : firm × month
DV               : mean_log_total_engagement (firm-month average)
IVs              : aggressive_humor_usage_intensity,
                   aggressive_humor_usage_intensity_sq
Controls         : NONE
Fixed effects    : NONE
H1/H2 variables  : EXCLUDED

H3 supported if: β₁ > 0, β₂ < 0, β₂ significant,
                 turning point = −β₁/(2β₂) within observed intensity range.
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
CI   = ROOT / "20260618expand" / "classifier_improvement"
OUT  = Path(__file__).parent

H3_CSV = CI / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"

CLASSIFIER_NOTE = (
    "domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels "
    "(batch1+batch2); aggressive_humor_usage_intensity = fraction of posts in "
    "firm-month classified as aggressive by this model; NOT_A_CANDIDATE level "
    "evidence; leakage risk: classifier trained on same corpus as regression sample"
)


# ── helpers ──────────────────────────────────────────────────────────────────

def to_f(v: str) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def p_stars(p: float) -> str:
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  [WARN] 0 rows — skipping {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  → {path.name}  ({len(rows)} rows)")


# ── OLS ──────────────────────────────────────────────────────────────────────

def ols_fit(X: np.ndarray, y: np.ndarray):
    n, k = X.shape
    XtX  = X.T @ X
    beta = np.linalg.solve(XtX, X.T @ y)
    resid  = y - X @ beta
    df_r   = n - k
    s2     = (resid @ resid) / df_r
    vcov   = s2 * np.linalg.inv(XtX)
    se     = np.sqrt(np.diag(vcov))
    t_stat = beta / se
    p_two  = 2 * t_dist.sf(np.abs(t_stat), df=df_r)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2     = 1.0 - (resid @ resid) / ss_tot
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / df_r
    return beta, se, t_stat, p_two, n, k, r2, r2_adj, df_r


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== run_simple_ols_h3_only ===\n")

    with open(H3_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input rows : {len(rows)}")
    print(f"Input file : {H3_CSV.name}")

    # Verify required columns; confirm H1/H2 variables absent from IVs
    assert "aggressive_humor_usage_intensity"    in rows[0]
    assert "aggressive_humor_usage_intensity_sq" in rows[0]
    assert "mean_log_total_engagement"           in rows[0]

    firms  = sorted(set(r["company_name"] for r in rows))
    months = sorted(set(r["period"]       for r in rows))
    n_firms  = len(firms)
    n_months = len(months)

    intensity = [to_f(r["aggressive_humor_usage_intensity"])    for r in rows]
    intens_sq = [to_f(r["aggressive_humor_usage_intensity_sq"]) for r in rows]
    dv        = [to_f(r["mean_log_total_engagement"])           for r in rows]

    sv = sorted(intensity)
    n_all = len(sv)

    int_mean   = statistics.mean(intensity)
    int_sd     = statistics.stdev(intensity)
    int_min    = min(intensity)
    int_max    = max(intensity)
    int_p25    = sv[n_all // 4]
    int_med    = statistics.median(sv)
    int_p75    = sv[3 * n_all // 4]
    dv_mean    = statistics.mean(dv)
    dv_sd      = statistics.stdev(dv)
    n_nonzero  = sum(1 for v in intensity if v > 0)

    # ── Sample distribution ───────────────────────────────────────────────
    dist_rows = [
        {"metric": "total_firm_month_observations",  "value": len(rows)},
        {"metric": "number_of_firms",                "value": n_firms},
        {"metric": "number_of_months",               "value": n_months},
        {"metric": "firm_months_with_nonzero_intensity", "value": n_nonzero},
        {"metric": "firm_months_with_zero_intensity",    "value": len(rows) - n_nonzero},
        {"metric": "aggressive_intensity_mean",      "value": f"{int_mean:.6f}"},
        {"metric": "aggressive_intensity_sd",        "value": f"{int_sd:.6f}"},
        {"metric": "aggressive_intensity_min",       "value": f"{int_min:.6f}"},
        {"metric": "aggressive_intensity_p25",       "value": f"{int_p25:.6f}"},
        {"metric": "aggressive_intensity_median",    "value": f"{int_med:.6f}"},
        {"metric": "aggressive_intensity_p75",       "value": f"{int_p75:.6f}"},
        {"metric": "aggressive_intensity_max",       "value": f"{int_max:.6f}"},
        {"metric": "mean_log1p_engagement_mean",     "value": f"{dv_mean:.4f}"},
        {"metric": "mean_log1p_engagement_sd",       "value": f"{dv_sd:.4f}"},
    ]
    write_csv(OUT / "simple_ols_h3_sample_distribution.csv", dist_rows)

    print(f"\nFirms={n_firms}  Months={n_months}  N={len(rows)}")
    print(f"Intensity: mean={int_mean:.4f}  sd={int_sd:.4f}  "
          f"min={int_min:.4f}  max={int_max:.4f}  nonzero={n_nonzero}")
    print(f"DV: mean={dv_mean:.4f}  sd={dv_sd:.4f}")

    # ── Design matrix: [intercept, intensity, intensity²] ────────────────
    X = np.column_stack([
        np.ones(len(rows)),
        np.array(intensity),
        np.array(intens_sq),
    ])
    y = np.array(dv)
    feat_names = ["intercept", "aggressive_intensity", "aggressive_intensity_sq"]

    beta, se, t_stat, p_two, n, k, r2, r2_adj, df_r = ols_fit(X, y)

    print(f"\nOLS: N={n}  k={k}  df_resid={df_r}  R²={r2:.4f}  adj-R²={r2_adj:.4f}")
    print(f"{'Variable':<30}  {'β':>10}  {'SE':>10}  {'t':>8}  {'p':>8}  Stars")
    for i, fn in enumerate(feat_names):
        print(f"  {fn:<28}  {beta[i]:+10.6f}  {se[i]:10.6f}  "
              f"{t_stat[i]:+8.4f}  {p_two[i]:8.4f}  {p_stars(p_two[i])}")

    # ── Regression results CSV ────────────────────────────────────────────
    reg_rows = []
    for i, fn in enumerate(feat_names):
        reg_rows.append({
            "variable":                fn,
            "coefficient":             f"{beta[i]:.6f}",
            "classical_ols_se":        f"{se[i]:.6f}",
            "t_stat":                  f"{t_stat[i]:.4f}",
            "p_value_two_sided":       f"{p_two[i]:.6f}",
            "stars":                   p_stars(p_two[i]),
            "n_obs":                   n,
            "r_squared":               f"{r2:.6f}",
            "r_squared_adj":           f"{r2_adj:.6f}",
            "df_resid":                df_r,
            "unit_of_analysis":        "firm_month",
            "controls_included":       "false",
            "fixed_effects_included":  "false",
            "h1_h2_variables_included":"false",
            "classifier_limitation":   CLASSIFIER_NOTE,
        })
    write_csv(OUT / "simple_ols_h3_regression_results.csv", reg_rows)

    # ── Quadratic diagnostics ─────────────────────────────────────────────
    b1 = float(beta[1])   # AggressiveIntensity
    b2 = float(beta[2])   # AggressiveIntensity²
    p_b1 = float(p_two[1])
    p_b2 = float(p_two[2])

    if b2 != 0:
        tp = -b1 / (2 * b2)
    else:
        tp = float("nan")

    tp_in_range = (
        not math.isnan(tp)
        and int_min <= tp <= int_max
    )

    # Pattern classification
    if b1 > 0 and b2 < 0:
        if p_b2 < 0.10 and tp_in_range:
            pattern = "inverted-U"
        elif p_b2 < 0.10:
            pattern = "inverted-U (turning point outside observed range)"
        else:
            pattern = "inverted-U direction but β₂ not significant"
    elif b1 < 0 and b2 > 0:
        pattern = "U-shaped"
    elif b2 > 0 and b1 > 0:
        pattern = "monotonic positive (convex)"
    elif b2 < 0 and b1 < 0:
        pattern = "monotonic negative (concave)"
    else:
        pattern = "no curvature support"

    h3_supported = (
        b1 > 0
        and b2 < 0
        and p_b2 < 0.10
        and tp_in_range
    )

    # H3 interpretation
    if b1 > 0 and b2 < 0 and p_b2 < 0.01 and tp_in_range:
        h3_interp = "H3 지지 (p<.01): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and p_b2 < 0.05 and tp_in_range:
        h3_interp = "H3 지지 (p<.05): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and p_b2 < 0.10 and tp_in_range:
        h3_interp = "H3 부분 지지 (p<.10): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and not tp_in_range:
        h3_interp = "H3 지지 불충분: 방향(역U) 맞으나 전환점이 관측 범위 밖"
    elif b1 > 0 and b2 < 0 and p_b2 >= 0.10:
        h3_interp = "H3 지지 불충분: 방향(역U) 맞으나 β₂ 유의하지 않음"
    elif b2 > 0:
        h3_interp = "H3 지지 불가: β₂>0 (역U자형 아님)"
    else:
        h3_interp = "H3 지지 불가: 역U자형 조건 미충족"

    quad_rows = [
        {
            "item":                        "beta1_intensity",
            "value":                       f"{b1:.6f}",
            "note":                        f"SE={se[1]:.6f}  t={t_stat[1]:.4f}  p={p_b1:.6f}  {p_stars(p_b1)}",
        },
        {
            "item":                        "beta2_intensity_squared",
            "value":                       f"{b2:.6f}",
            "note":                        f"SE={se[2]:.6f}  t={t_stat[2]:.4f}  p={p_b2:.6f}  {p_stars(p_b2)}",
        },
        {
            "item":                        "beta1_sign",
            "value":                       "positive" if b1 > 0 else "negative",
            "note":                        "H3 요구: positive",
        },
        {
            "item":                        "beta2_sign",
            "value":                       "negative" if b2 < 0 else "positive",
            "note":                        "H3 요구: negative (역U자형)",
        },
        {
            "item":                        "beta2_p_value",
            "value":                       f"{p_b2:.6f}",
            "note":                        p_stars(p_b2) or "ns",
        },
        {
            "item":                        "turning_point",
            "value":                       f"{tp:.6f}" if not math.isnan(tp) else "undefined",
            "note":                        "= −β₁ / (2β₂)",
        },
        {
            "item":                        "observed_intensity_min",
            "value":                       f"{int_min:.6f}",
            "note":                        "",
        },
        {
            "item":                        "observed_intensity_max",
            "value":                       f"{int_max:.6f}",
            "note":                        "",
        },
        {
            "item":                        "turning_point_in_observed_range",
            "value":                       "true" if tp_in_range else "false",
            "note":                        f"range [{int_min:.4f}, {int_max:.4f}]",
        },
        {
            "item":                        "pattern",
            "value":                       pattern,
            "note":                        "",
        },
        {
            "item":                        "H3_supported",
            "value":                       "true" if h3_supported else "false",
            "note":                        h3_interp,
        },
        {
            "item":                        "interpretation",
            "value":                       h3_interp,
            "note":                        "",
        },
    ]
    write_csv(OUT / "simple_ols_h3_quadratic_diagnostics.csv", quad_rows)

    # ── Model specification MD ────────────────────────────────────────────
    spec_md = f"""\
# Simple OLS Model Specification — H3 Diagnostic

## Model (M1 Simple Quadratic OLS)

```
mean_log(1+Engagement)_{{ft}} = α
                              + β₁·AggressiveIntensity_{{ft}}
                              + β₂·AggressiveIntensity²_{{ft}}
                              + ε_{{ft}}
```

| Item | Value |
|:---|:---|
| Unit of analysis | firm × month |
| DV | mean_log_total_engagement (firm-month average) |
| IVs | aggressive_humor_usage_intensity, aggressive_humor_usage_intensity_sq |
| Controls | NONE |
| Fixed effects | NONE |
| H1/H2 variables | EXCLUDED |
| SE type | Classical OLS (homoskedastic) |
| Stars convention | *** p<.01 / ** p<.05 / * p<.10 (two-sided) |

## H3 Acceptance Criteria

1. β₁ > 0
2. β₂ < 0
3. β₂ statistically significant
4. Turning point = −β₁/(2β₂) within observed intensity range

## Excluded Variables

- H1: humor_presence
- H2: aggressive_humor, affiliative_humor, self_enhancing_humor, self_defeating_humor
- Controls: text_length, hashtag_count, mention_count, mean_text_length,
            mean_hashtag_count, mean_mention_count, emoji_count
- Fixed effects: year, month, firm

## Data Source

- Input: `{H3_CSV.name}`
- N = {len(rows)} firm-month observations ({n_firms} firms × up to {n_months} months)
- Classifier: {CLASSIFIER_NOTE}
"""
    (OUT / "simple_ols_h3_model_specification.md").write_text(spec_md, encoding="utf-8")
    print(f"  → simple_ols_h3_model_specification.md")

    # ── Interpretation MD ─────────────────────────────────────────────────
    tp_str = f"{tp:.4f}" if not math.isnan(tp) else "undefined"
    interp_md = f"""\
# Simple OLS H3 해석 (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반 결과. Controls 및 Fixed Effects 미포함.
> NOT_A_CANDIDATE 수준 증거. Classifier leakage risk 존재.

---

## 1. 표본 구성 (Firm-Month Panel)

| 항목 | 값 |
|:---|---:|
| Total firm-month observations | {len(rows):,} |
| Number of firms | {n_firms} |
| Number of months | {n_months} |
| Firm-months with nonzero intensity | {n_nonzero:,} ({n_nonzero/len(rows)*100:.1f}%) |
| Firm-months with zero intensity | {len(rows)-n_nonzero:,} ({(len(rows)-n_nonzero)/len(rows)*100:.1f}%) |
| AggressiveIntensity mean | {int_mean:.4f} |
| AggressiveIntensity SD | {int_sd:.4f} |
| AggressiveIntensity min | {int_min:.4f} |
| AggressiveIntensity p25 | {int_p25:.4f} |
| AggressiveIntensity median | {int_med:.4f} |
| AggressiveIntensity p75 | {int_p75:.4f} |
| AggressiveIntensity max | {int_max:.4f} |

---

## 2. 회귀 결과 (M1 Simple Quadratic OLS)

```
mean_log(1+Engagement)_{{ft}} = α + β₁·Intensity + β₂·Intensity² + ε
```

| 변수 | β | SE | t | p (2-sided) | Stars |
|:---|---:|---:|---:|---:|:---:|
| Intercept (α) | {beta[0]:+.4f} | {se[0]:.4f} | {t_stat[0]:+.4f} | {p_two[0]:.4f} | {p_stars(p_two[0])} |
| AggressiveIntensity (β₁) | {b1:+.4f} | {se[1]:.4f} | {t_stat[1]:+.4f} | {p_two[1]:.4f} | {p_stars(p_two[1])} |
| AggressiveIntensity² (β₂) | {b2:+.4f} | {se[2]:.4f} | {t_stat[2]:+.4f} | {p_two[2]:.4f} | {p_stars(p_two[2])} |

N={n:,} (firm-month) | R²={r2:.4f} | adj-R²={r2_adj:.4f} | df_resid={df_r:,}
Unit = firm×month | Controls = none | FE = none

---

## 3. H3 역U자형 진단

| 진단 항목 | 결과 | H3 요건 |
|:---|:---|:---|
| β₁ 부호 | {"**양수** ✓" if b1 > 0 else "**음수** ✗"} | 양수 (>0) |
| β₁ 유의성 | {p_stars(p_b1) or "ns"} (p={p_b1:.4f}) | — |
| β₂ 부호 | {"**음수** ✓" if b2 < 0 else "**양수** ✗"} | 음수 (<0) |
| β₂ 유의성 | {p_stars(p_b2) or "ns"} (p={p_b2:.4f}) | 유의 필요 |
| 전환점 = −β₁/(2β₂) | {tp_str} | 관측 범위 내 |
| 관측 intensity 범위 | [{int_min:.4f}, {int_max:.4f}] | — |
| 전환점 범위 내 여부 | {"**예** ✓" if tp_in_range else "**아니오** ✗"} | 예 |
| 패턴 | {pattern} | inverted-U |

**H3 지지 여부**: {"**지지** ✓" if h3_supported else "**지지 불충분/불가** ✗"}

**판정**: {h3_interp}

---

## 4. 해석 주의사항

1. **단순 OLS 진단**: Controls, Fixed Effects 없는 기초 OLS. Firm-level heterogeneity
   및 시간 트렌드가 통제되지 않아 omitted variable bias 가능성 있음.
2. **Zero-inflation**: 전체 firm-month 중 {(len(rows)-n_nonzero)/len(rows)*100:.1f}%가 intensity=0.
   quadratic 추정이 소수 nonzero 관측치에 의존함.
3. **Classifier limitation**: aggressive_humor_usage_intensity는 domain-adapted 분류기
   예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
4. **이 결과는 H3의 기초 OLS baseline**으로만 해석하며, robust causal evidence가 아님.
"""
    (OUT / "simple_ols_h3_interpretation.md").write_text(interp_md, encoding="utf-8")
    print(f"  → simple_ols_h3_interpretation.md")

    # ── Console summary ───────────────────────────────────────────────────
    print(f"\n=== H3 QUADRATIC DIAGNOSTICS ===")
    print(f"  β₁ (Intensity):    {b1:+.6f}  SE={se[1]:.6f}  p={p_b1:.6f}  {p_stars(p_b1) or 'ns'}")
    print(f"  β₂ (Intensity²):   {b2:+.6f}  SE={se[2]:.6f}  p={p_b2:.6f}  {p_stars(p_b2) or 'ns'}")
    print(f"  Turning point:      {tp_str}")
    print(f"  Observed range:     [{int_min:.4f}, {int_max:.4f}]")
    print(f"  TP in range:        {tp_in_range}")
    print(f"  Pattern:            {pattern}")
    print(f"  H3 supported:       {h3_supported}")
    print(f"  → {h3_interp}")
    print("\n=== run_simple_ols_h3_only COMPLETE ===")


if __name__ == "__main__":
    main()
