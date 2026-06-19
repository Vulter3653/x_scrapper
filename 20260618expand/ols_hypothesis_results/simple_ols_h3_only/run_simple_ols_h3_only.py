"""
run_simple_ols_h3_only.py

Quadratic OLS diagnostic for H3.

Models:
  M1 Simple Quadratic OLS:
    mean_log1p_engagement_{ft} = α + β₁·Intensity + β₂·Intensity² + ε

  M2 Firm FE (FWL within-firm demeaning):
    mean_log1p_engagement_{ft} = β₁·Intensity + β₂·Intensity²
                                + μ_f + ε_{ft}

Unit of analysis : firm × month
DV               : mean_log_total_engagement
IVs              : aggressive_humor_usage_intensity,
                   aggressive_humor_usage_intensity_sq
Controls         : NONE
H1/H2 variables  : EXCLUDED

H3: β₁>0, β₂<0, β₂ significant, turning point within observed range.
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

def ols_fit(X: np.ndarray, y: np.ndarray, df_override: int | None = None):
    n, k = X.shape
    XtX  = X.T @ X
    beta = np.linalg.solve(XtX, X.T @ y)
    resid  = y - X @ beta
    df_r   = df_override if df_override is not None else n - k
    s2     = (resid @ resid) / df_r
    vcov   = s2 * np.linalg.inv(XtX)
    se     = np.sqrt(np.diag(vcov))
    t_stat = beta / se
    p_two  = 2 * t_dist.sf(np.abs(t_stat), df=df_r)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2     = 1.0 - (resid @ resid) / ss_tot
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / df_r
    return beta, vcov, se, t_stat, p_two, n, k, r2, r2_adj, df_r


def demean_by_group(arr: np.ndarray, groups: list) -> np.ndarray:
    out = arr.copy().astype(float)
    for g in set(groups):
        idx = [i for i, x in enumerate(groups) if x == g]
        out[idx] -= out[idx].mean(axis=0)
    return out


# ── H3 diagnostics ───────────────────────────────────────────────────────────

def h3_diagnostics(b1, b2, se_b1, se_b2, p_b1, p_b2,
                   int_min, int_max, model_label):
    tp = -b1 / (2 * b2) if b2 != 0 else float("nan")
    tp_in = not math.isnan(tp) and int_min <= tp <= int_max

    if b1 > 0 and b2 < 0:
        if p_b2 < 0.10 and tp_in:  pattern = "inverted-U"
        elif p_b2 < 0.10:           pattern = "inverted-U (TP outside observed range)"
        else:                        pattern = "inverted-U direction but β₂ not significant"
    elif b1 < 0 and b2 > 0:         pattern = "U-shaped"
    else:                            pattern = "no curvature support"

    supported = b1 > 0 and b2 < 0 and p_b2 < 0.10 and tp_in

    if b1 > 0 and b2 < 0 and p_b2 < 0.01 and tp_in:
        interp = "H3 지지 (p<.01): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and p_b2 < 0.05 and tp_in:
        interp = "H3 지지 (p<.05): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and p_b2 < 0.10 and tp_in:
        interp = "H3 부분 지지 (p<.10): β₁>0, β₂<0 유의, 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0 and not tp_in:
        interp = "H3 지지 불충분: 방향(역U) 맞으나 전환점 관측 범위 밖"
    elif b1 > 0 and b2 < 0 and p_b2 >= 0.10:
        interp = "H3 지지 불충분: 방향(역U) 맞으나 β₂ 유의하지 않음"
    elif b2 > 0:
        interp = "H3 지지 불가: β₂>0 (역U자형 아님)"
    else:
        interp = "H3 지지 불가: 역U자형 조건 미충족"

    rows = [
        {"model": model_label, "item": "beta1_intensity",
         "value": f"{b1:.6f}",
         "note": f"SE={se_b1:.6f}  t={b1/se_b1:.4f}  p={p_b1:.6f}  {p_stars(p_b1)}"},
        {"model": model_label, "item": "beta2_intensity_squared",
         "value": f"{b2:.6f}",
         "note": f"SE={se_b2:.6f}  t={b2/se_b2:.4f}  p={p_b2:.6f}  {p_stars(p_b2)}"},
        {"model": model_label, "item": "beta1_sign",
         "value": "positive" if b1 > 0 else "negative", "note": "H3 요구: positive"},
        {"model": model_label, "item": "beta2_sign",
         "value": "negative" if b2 < 0 else "positive", "note": "H3 요구: negative"},
        {"model": model_label, "item": "beta2_p_value",
         "value": f"{p_b2:.6f}", "note": p_stars(p_b2) or "ns"},
        {"model": model_label, "item": "turning_point",
         "value": f"{tp:.6f}" if not math.isnan(tp) else "undefined",
         "note": "= −β₁/(2β₂)"},
        {"model": model_label, "item": "observed_intensity_min",
         "value": f"{int_min:.6f}", "note": ""},
        {"model": model_label, "item": "observed_intensity_max",
         "value": f"{int_max:.6f}", "note": ""},
        {"model": model_label, "item": "turning_point_in_observed_range",
         "value": "true" if tp_in else "false",
         "note": f"range [{int_min:.4f}, {int_max:.4f}]"},
        {"model": model_label, "item": "pattern",
         "value": pattern, "note": ""},
        {"model": model_label, "item": "H3_supported",
         "value": "true" if supported else "false", "note": interp},
        {"model": model_label, "item": "interpretation",
         "value": interp, "note": ""},
    ]
    return rows, tp, tp_in, pattern, supported, interp


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== run_simple_ols_h3_only ===\n")

    with open(H3_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input rows : {len(rows)}  |  {H3_CSV.name}")

    assert "aggressive_humor_usage_intensity"    in rows[0]
    assert "aggressive_humor_usage_intensity_sq" in rows[0]
    assert "mean_log_total_engagement"           in rows[0]

    firms  = sorted(set(r["company_name"] for r in rows))
    months = sorted(set(r["period"]       for r in rows))
    n_firms, n_months = len(firms), len(months)
    firm_groups = [r["company_name"] for r in rows]

    intensity = [to_f(r["aggressive_humor_usage_intensity"])    for r in rows]
    intens_sq = [to_f(r["aggressive_humor_usage_intensity_sq"]) for r in rows]
    dv        = [to_f(r["mean_log_total_engagement"])           for r in rows]

    sv = sorted(intensity)
    n_all    = len(sv)
    int_mean = statistics.mean(intensity)
    int_sd   = statistics.stdev(intensity)
    int_min  = min(intensity)
    int_max  = max(intensity)
    int_p25  = sv[n_all // 4]
    int_med  = statistics.median(sv)
    int_p75  = sv[3 * n_all // 4]
    dv_mean  = statistics.mean(dv)
    dv_sd    = statistics.stdev(dv)
    n_nonzero = sum(1 for v in intensity if v > 0)

    # ── Sample distribution ───────────────────────────────────────────────
    dist_rows = [
        {"metric": "total_firm_month_observations",      "value": len(rows)},
        {"metric": "number_of_firms",                    "value": n_firms},
        {"metric": "number_of_months",                   "value": n_months},
        {"metric": "firm_months_nonzero_intensity",      "value": n_nonzero},
        {"metric": "firm_months_zero_intensity",         "value": len(rows) - n_nonzero},
        {"metric": "aggressive_intensity_mean",          "value": f"{int_mean:.6f}"},
        {"metric": "aggressive_intensity_sd",            "value": f"{int_sd:.6f}"},
        {"metric": "aggressive_intensity_min",           "value": f"{int_min:.6f}"},
        {"metric": "aggressive_intensity_p25",           "value": f"{int_p25:.6f}"},
        {"metric": "aggressive_intensity_median",        "value": f"{int_med:.6f}"},
        {"metric": "aggressive_intensity_p75",           "value": f"{int_p75:.6f}"},
        {"metric": "aggressive_intensity_max",           "value": f"{int_max:.6f}"},
        {"metric": "mean_log1p_engagement_mean",         "value": f"{dv_mean:.4f}"},
        {"metric": "mean_log1p_engagement_sd",           "value": f"{dv_sd:.4f}"},
    ]
    write_csv(OUT / "simple_ols_h3_sample_distribution.csv", dist_rows)
    print(f"  Firms={n_firms}  Months={n_months}  N={len(rows)}  nonzero={n_nonzero}")

    y   = np.array(dv)
    int_arr  = np.array(intensity)
    intsq_arr= np.array(intens_sq)

    # ════════════════════════════════════════════════════════════════════════
    # M1: Simple Quadratic OLS
    # ════════════════════════════════════════════════════════════════════════
    X_m1 = np.column_stack([np.ones(len(rows)), int_arr, intsq_arr])
    fn_m1 = ["intercept", "aggressive_intensity", "aggressive_intensity_sq"]

    bm1, vm1, sm1, tm1, pm1, nm1, km1, r2_1, r2a_1, df1 = ols_fit(X_m1, y)

    print(f"\nM1 Simple OLS: N={nm1} k={km1} df={df1} R²={r2_1:.4f} adj-R²={r2a_1:.4f}")
    for i, fn in enumerate(fn_m1):
        print(f"  {fn:<32} β={bm1[i]:+.6f}  SE={sm1[i]:.6f}  t={tm1[i]:+.4f}  {p_stars(pm1[i])}")

    diag_m1, tp1, tpin1, pat1, sup1, interp1 = h3_diagnostics(
        bm1[1], bm1[2], sm1[1], sm1[2], pm1[1], pm1[2], int_min, int_max, "M1_simple_ols")

    # ════════════════════════════════════════════════════════════════════════
    # M2: Firm FE via FWL within-firm demeaning
    # ════════════════════════════════════════════════════════════════════════
    mat = np.column_stack([y, int_arr, intsq_arr])
    mat_dm = demean_by_group(mat, firm_groups)

    y_dm   = mat_dm[:, 0]
    X_dm   = mat_dm[:, 1:]   # [intensity_dm, intensity_sq_dm]
    fn_m2  = ["aggressive_intensity", "aggressive_intensity_sq"]

    k_within = 2
    df2 = len(rows) - n_firms - k_within
    ss_within_tot = np.sum(y_dm ** 2)

    bm2, vm2, sm2, tm2, pm2, nm2, km2, _, _, _ = ols_fit(X_dm, y_dm, df_override=df2)
    resid_dm2 = y_dm - X_dm @ bm2
    r2_within = 1.0 - (resid_dm2 @ resid_dm2) / ss_within_tot
    r2a_2 = 1.0 - (1.0 - r2_within) * (len(rows) - 1) / df2

    print(f"\nM2 Firm FE (FWL): N={len(rows)} firms={n_firms} k_within={k_within}"
          f" df={df2} R²_within={r2_within:.4f}")
    for i, fn in enumerate(fn_m2):
        print(f"  {fn:<32} β={bm2[i]:+.6f}  SE={sm2[i]:.6f}  t={tm2[i]:+.4f}  {p_stars(pm2[i])}")

    # Observed intensity range within each firm (for M2 TP interpretation)
    firm_int_min = float("inf")
    firm_int_max = float("-inf")
    for g in set(firm_groups):
        idx = [i for i, x in enumerate(firm_groups) if x == g]
        vals = [intensity[i] for i in idx]
        firm_int_min = min(firm_int_min, min(vals))
        firm_int_max = max(firm_int_max, max(vals))

    diag_m2, tp2, tpin2, pat2, sup2, interp2 = h3_diagnostics(
        bm2[0], bm2[1], sm2[0], sm2[1], pm2[0], pm2[1],
        firm_int_min, firm_int_max, "M2_firm_fe_fwl")

    # ── Regression results CSV ────────────────────────────────────────────
    reg_rows = []
    for i, fn in enumerate(fn_m1):
        reg_rows.append({
            "model": "M1_simple_ols", "variable": fn,
            "coefficient": f"{bm1[i]:.6f}", "classical_ols_se": f"{sm1[i]:.6f}",
            "t_stat": f"{tm1[i]:.4f}", "p_value_two_sided": f"{pm1[i]:.6f}",
            "stars": p_stars(pm1[i]),
            "n_obs": nm1, "r_squared": f"{r2_1:.6f}", "r_squared_adj": f"{r2a_1:.6f}",
            "df_resid": df1, "n_firms": n_firms,
            "unit_of_analysis": "firm_month",
            "controls_included": "false", "fixed_effects": "none",
            "h1_h2_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    for i, fn in enumerate(fn_m2):
        reg_rows.append({
            "model": "M2_firm_fe_fwl", "variable": fn,
            "coefficient": f"{bm2[i]:.6f}", "classical_ols_se": f"{sm2[i]:.6f}",
            "t_stat": f"{tm2[i]:.4f}", "p_value_two_sided": f"{pm2[i]:.6f}",
            "stars": p_stars(pm2[i]),
            "n_obs": len(rows), "r_squared": f"{r2_within:.6f}", "r_squared_adj": f"{r2a_2:.6f}",
            "df_resid": df2, "n_firms": n_firms,
            "unit_of_analysis": "firm_month",
            "controls_included": "false", "fixed_effects": "firm (FWL within-demeaning)",
            "h1_h2_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    write_csv(OUT / "simple_ols_h3_regression_results.csv", reg_rows)

    # ── Quadratic diagnostics CSV ─────────────────────────────────────────
    write_csv(OUT / "simple_ols_h3_quadratic_diagnostics.csv", diag_m1 + diag_m2)

    # ── Model specification MD ────────────────────────────────────────────
    spec_md = f"""\
# OLS Model Specification — H3 Diagnostic

## M1 Simple Quadratic OLS

```
mean_log(1+Engagement)_{{ft}} = α + β₁·Intensity_{{ft}} + β₂·Intensity²_{{ft}} + ε
```

## M2 Firm FE (FWL within-firm demeaning)

```
mean_log(1+Engagement)_{{ft}} = β₁·Intensity_{{ft}} + β₂·Intensity²_{{ft}} + μ_f + ε
```

μ_f absorbed via within-firm demeaning. No intercept after demeaning.

| Item | M1 | M2 |
|:---|:---|:---|
| Unit of analysis | firm×month | firm×month |
| DV | mean_log_total_engagement | mean_log_total_engagement |
| IVs | Intensity, Intensity² | Intensity, Intensity² |
| Controls | NONE | NONE |
| Firm FE | NONE | YES (FWL) |
| Time FE | NONE | NONE |
| H1/H2 variables | EXCLUDED | EXCLUDED |
| N | {len(rows)} | {len(rows)} |
| Firms | — | {n_firms} |
| df_resid | {df1} | {df2} |

## H3 Acceptance Criteria

β₁>0, β₂<0, β₂ significant (p<.10), turning_point = −β₁/(2β₂) within observed range.

## Data Source

- `{H3_CSV.name}` — N={len(rows)} firm-month obs ({n_firms} firms × up to {n_months} months)
- Classifier: {CLASSIFIER_NOTE}
"""
    (OUT / "simple_ols_h3_model_specification.md").write_text(spec_md, encoding="utf-8")
    print("  → simple_ols_h3_model_specification.md")

    # ── Interpretation MD ─────────────────────────────────────────────────
    tp1_str = f"{tp1:.4f}" if not math.isnan(tp1) else "undefined"
    tp2_str = f"{tp2:.4f}" if not math.isnan(tp2) else "undefined"

    interp_md = f"""\
# OLS H3 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 항목 | 값 |
|:---|---:|
| Total firm-month observations | {len(rows):,} |
| Firms | {n_firms} |
| Months | {n_months} |
| Nonzero intensity firm-months | {n_nonzero:,} ({n_nonzero/len(rows)*100:.1f}%) |
| AggressiveIntensity mean | {int_mean:.4f} |
| AggressiveIntensity SD | {int_sd:.4f} |
| AggressiveIntensity min/max | {int_min:.4f} / {int_max:.4f} |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm FE (FWL) |
|:---|:---:|:---:|
| Intensity (β₁) | {bm1[1]:+.4f}{p_stars(pm1[1])} ({sm1[1]:.4f}) | {bm2[0]:+.4f}{p_stars(pm2[0])} ({sm2[0]:.4f}) |
| Intensity² (β₂) | {bm1[2]:+.4f}{p_stars(pm1[2])} ({sm1[2]:.4f}) | {bm2[1]:+.4f}{p_stars(pm2[1])} ({sm2[1]:.4f}) |
| Intercept | {bm1[0]:+.4f} | absorbed |
| N | {len(rows):,} | {len(rows):,} |
| Firms | — | {n_firms} |
| R² | {r2_1:.4f} | {r2_within:.4f} (within) |
| adj-R² | {r2a_1:.4f} | {r2a_2:.4f} |
| df_resid | {df1:,} | {df2:,} |

---

## 3. H3 역U자형 진단

| 진단 항목 | M1 Simple OLS | M2 Firm FE (FWL) | H3 요건 |
|:---|:---:|:---:|:---|
| β₁ 부호 | {"양수 ✓" if bm1[1]>0 else "음수 ✗"} | {"양수 ✓" if bm2[0]>0 else "음수 ✗"} | 양수 |
| β₁ p-value | {p_stars(pm1[1]) or "ns"} ({pm1[1]:.4f}) | {p_stars(pm2[0]) or "ns"} ({pm2[0]:.4f}) | — |
| β₂ 부호 | {"음수 ✓" if bm1[2]<0 else "양수 ✗"} | {"음수 ✓" if bm2[1]<0 else "양수 ✗"} | 음수 |
| β₂ p-value | {p_stars(pm1[2]) or "ns"} ({pm1[2]:.4f}) | {p_stars(pm2[1]) or "ns"} ({pm2[1]:.4f}) | 유의 |
| 전환점 | {tp1_str} | {tp2_str} | 관측 범위 내 |
| 범위 내 여부 | {"예 ✓" if tpin1 else "아니오 ✗"} | {"예 ✓" if tpin2 else "아니오 ✗"} | 예 |
| 패턴 | {pat1} | {pat2} | inverted-U |
| H3 지지 | {"지지 ✓" if sup1 else "지지 불가 ✗"} | {"지지 ✓" if sup2 else "지지 불가 ✗"} | true |

**판정**:
- M1 Simple OLS: {interp1}
- M2 Firm FE:    {interp2}

---

## 4. 해석 주의사항

1. **Zero-inflation**: 전체 firm-month의 {(len(rows)-n_nonzero)/len(rows)*100:.1f}%가 intensity=0. quadratic 추정이 nonzero {n_nonzero}개 관측치에 집중.
2. **Classifier limitation**: aggressive_humor_usage_intensity는 domain-adapted 분류기 예측값 기반. Leakage risk 존재.
3. **Controls 미포함**: 시간 FE, 포스트 속성 미통제. M2 Firm FE는 기업 수준 고정 이질성 흡수.
4. **단순 OLS 진단 목적**: preliminary diagnostic. Robust causal evidence 아님.
"""
    (OUT / "simple_ols_h3_interpretation.md").write_text(interp_md, encoding="utf-8")
    print("  → simple_ols_h3_interpretation.md")

    # ── Console summary ───────────────────────────────────────────────────
    print("\n=== H3 DIAGNOSTICS SUMMARY ===")
    for ml, b1, b2, sb1, sb2, pb1, pb2, tp, tpin, pat, sup, interp in [
        ("M1", bm1[1], bm1[2], sm1[1], sm1[2], pm1[1], pm1[2], tp1, tpin1, pat1, sup1, interp1),
        ("M2", bm2[0], bm2[1], sm2[0], sm2[1], pm2[0], pm2[1], tp2, tpin2, pat2, sup2, interp2),
    ]:
        tp_s = f"{tp:.4f}" if not math.isnan(tp) else "n/a"
        print(f"  [{ml}] β₁={b1:+.4f}{p_stars(pb1)}  β₂={b2:+.4f}{p_stars(pb2)}"
              f"  TP={tp_s}  in_range={tpin}")
        print(f"        → {interp}")

    print("\n=== run_simple_ols_h3_only COMPLETE ===")


if __name__ == "__main__":
    main()
