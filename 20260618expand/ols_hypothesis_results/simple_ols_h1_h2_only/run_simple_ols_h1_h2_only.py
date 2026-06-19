"""
run_simple_ols_h1_h2_only.py

Simple OLS diagnostic for H1 and H2 using domain-adapted classifier predictions.

Model (M1 Simple OLS only):
  log1p_engagement ~ β₀ + β₁*Aggressive + β₂*Affiliative
                   + β₃*SelfEnhancing + β₄*SelfDefeating + ε

Reference category : non_humorous (omitted)
Controls           : NONE
Fixed effects      : NONE
H3 variables       : EXCLUDED

H1: All four β > 0 (humor > non-humor); weighted average humor effect > 0
H2-1: β₁ > weighted_avg(β₂, β₃, β₄)   [aggressive > other humor]
H2-2: β₁ > β₂, β₁ > β₃, β₁ > β₄      [pairwise contrasts]
"""

from __future__ import annotations

import csv
import math
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

H2_CSV = CI / "data" / "regression_ready" / "h2_post_level_regression_ready.csv"

CLASSIFIER_NOTE = (
    "domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels "
    "(batch1+batch2); predictions only — NOT_A_CANDIDATE level evidence; "
    "leakage risk: classifier trained on same corpus as regression sample"
)


# ── helpers ──────────────────────────────────────────────────────────────────

def to_f(v: str) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def p_stars(p: float) -> str:
    if p < 0.01:  return "***"
    if p < 0.05:  return "**"
    if p < 0.10:  return "*"
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
    """
    Returns beta, vcov (s²(X'X)⁻¹), se, t_stat, p_two, n, k, r2, r2_adj, df_resid.
    Classical (homoskedastic) OLS SE.
    """
    n, k = X.shape
    XtX  = X.T @ X
    Xty  = X.T @ y
    beta = np.linalg.solve(XtX, Xty)

    y_hat = X @ beta
    resid = y - y_hat
    df_r  = n - k
    s2    = (resid @ resid) / df_r
    vcov  = s2 * np.linalg.inv(XtX)
    se    = np.sqrt(np.diag(vcov))
    t_stat = beta / se
    p_two  = 2 * t_dist.sf(np.abs(t_stat), df=df_r)

    ss_tot = np.sum((y - y.mean()) ** 2)
    ss_res = resid @ resid
    r2     = 1.0 - ss_res / ss_tot
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / df_r

    return beta, vcov, se, t_stat, p_two, n, k, r2, r2_adj, df_r


def linear_contrast(c: np.ndarray, beta: np.ndarray, vcov: np.ndarray, df_r: int):
    """
    Estimate and SE for a linear contrast c'β̂.
    """
    estimate = float(c @ beta)
    var_c    = float(c @ vcov @ c)
    se_c     = math.sqrt(max(var_c, 0.0))
    t_c      = estimate / se_c if se_c > 0 else float("nan")
    p_two    = 2 * t_dist.sf(abs(t_c), df=df_r) if not math.isnan(t_c) else float("nan")
    return estimate, se_c, t_c, p_two


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== run_simple_ols_h1_h2_only ===\n")

    # 1. Load H2 data (fortune100, all types including non_humorous)
    with open(H2_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input rows: {len(rows)}")
    print(f"Input file: {H2_CSV.name}")

    # Verify no H3 / control / FE columns used
    IVS = ["aggressive_humor", "affiliative_humor",
           "self_enhancing_humor", "self_defeating_humor"]
    DV  = "log_total_engagement"
    for col in IVS + [DV]:
        assert col in rows[0], f"Missing column: {col}"

    # 2. Sample distribution
    n_agg = sum(1 for r in rows if r["aggressive_humor"]    == "1")
    n_aff = sum(1 for r in rows if r["affiliative_humor"]   == "1")
    n_se  = sum(1 for r in rows if r["self_enhancing_humor"]== "1")
    n_sd  = sum(1 for r in rows if r["self_defeating_humor"]== "1")
    n_nh  = sum(1 for r in rows if r["non_humorous"]        == "1")
    n_tot = len(rows)
    n_hum = n_agg + n_aff + n_se + n_sd
    assert n_nh + n_hum == n_tot, f"Count mismatch: {n_nh}+{n_hum} != {n_tot}"

    dist_rows = [
        {"group": "non_humorous (reference)",  "n": n_nh,  "pct_total": f"{n_nh/n_tot*100:.2f}%", "pct_humor": "—"},
        {"group": "aggressive",                "n": n_agg, "pct_total": f"{n_agg/n_tot*100:.2f}%", "pct_humor": f"{n_agg/n_hum*100:.2f}%"},
        {"group": "affiliative",               "n": n_aff, "pct_total": f"{n_aff/n_tot*100:.2f}%", "pct_humor": f"{n_aff/n_hum*100:.2f}%"},
        {"group": "self_enhancing",            "n": n_se,  "pct_total": f"{n_se/n_tot*100:.2f}%",  "pct_humor": f"{n_se/n_hum*100:.2f}%"},
        {"group": "self_defeating",            "n": n_sd,  "pct_total": f"{n_sd/n_tot*100:.2f}%",  "pct_humor": f"{n_sd/n_hum*100:.2f}%"},
        {"group": "humor_total",               "n": n_hum, "pct_total": f"{n_hum/n_tot*100:.2f}%", "pct_humor": "100.00%"},
        {"group": "TOTAL",                     "n": n_tot, "pct_total": "100.00%",                  "pct_humor": "—"},
    ]
    write_csv(OUT / "simple_ols_h1_h2_sample_distribution.csv", dist_rows)

    print(f"\nSample: N={n_tot:,}  |  humor={n_hum:,} "
          f"(agg={n_agg:,} aff={n_aff:,} se={n_se:,} sd={n_sd:,})  |  non-humor={n_nh:,}")

    # 3. Build design matrix
    # X = [intercept, aggressive, affiliative, self_enhancing, self_defeating]
    # NO controls, NO FE, NO H3 variables
    X = np.array([
        [1.0,
         to_f(r["aggressive_humor"]),
         to_f(r["affiliative_humor"]),
         to_f(r["self_enhancing_humor"]),
         to_f(r["self_defeating_humor"])]
        for r in rows
    ])
    y = np.array([to_f(r[DV]) for r in rows])

    feat_names = ["intercept", "aggressive", "affiliative",
                  "self_enhancing", "self_defeating"]

    # 4. OLS fit
    beta, vcov, se, t_stat, p_two, n, k, r2, r2_adj, df_r = ols_fit(X, y)

    print(f"\nOLS: N={n:,}  k={k}  df_resid={df_r:,}  R²={r2:.4f}  adj-R²={r2_adj:.4f}")

    # 5. Regression results CSV
    reg_rows = []
    for i, fname in enumerate(feat_names):
        reg_rows.append({
            "variable":               fname,
            "coefficient":            f"{beta[i]:.6f}",
            "classical_ols_se":       f"{se[i]:.6f}",
            "t_stat":                 f"{t_stat[i]:.4f}",
            "p_value_two_sided":      f"{p_two[i]:.6f}",
            "stars":                  p_stars(p_two[i]),
            "n_obs":                  n,
            "r_squared":              f"{r2:.6f}",
            "r_squared_adj":          f"{r2_adj:.6f}",
            "df_resid":               df_r,
            "reference_category":     "non_humorous",
            "controls_included":      "false",
            "fixed_effects_included": "false",
            "h3_variables_included":  "false",
            "classifier_limitation":  CLASSIFIER_NOTE,
        })
    write_csv(OUT / "simple_ols_h1_h2_regression_results.csv", reg_rows)

    # Print results
    print("\n--- Regression Coefficients ---")
    print(f"{'Variable':<20}  {'β':>9}  {'SE':>8}  {'t':>8}  {'p':>8}  Stars")
    for i, fname in enumerate(feat_names):
        print(f"  {fname:<18}  {beta[i]:+9.4f}  {se[i]:8.4f}  "
              f"{t_stat[i]:+8.4f}  {p_two[i]:8.4f}  {p_stars(p_two[i])}")

    # 6. Contrast tests
    # ── Weights inside humor sample ──────────────────────────────
    w_agg = n_agg / n_hum
    w_aff = n_aff / n_hum
    w_se  = n_se  / n_hum
    w_sd  = n_sd  / n_hum
    # Other-humor weights (excluding aggressive)
    n_other = n_aff + n_se + n_sd
    w_aff2 = n_aff / n_other
    w_se2  = n_se  / n_other
    w_sd2  = n_sd  / n_other

    # ── H1: weighted average humor effect ──────────────────────
    # c = [0, w_agg, w_aff, w_se, w_sd]  vs. intercept (non-humor baseline)
    c_h1 = np.array([0.0, w_agg, w_aff, w_se, w_sd])
    est_h1, se_h1, t_h1, p_h1 = linear_contrast(c_h1, beta, vcov, df_r)

    # ── H2-1: aggressive vs. other humor weighted average ───────
    # contrast: β_agg - (w_aff2*β_aff + w_se2*β_se + w_sd2*β_sd)
    c_h21 = np.array([0.0, 1.0, -w_aff2, -w_se2, -w_sd2])
    est_h21, se_h21, t_h21, p_h21 = linear_contrast(c_h21, beta, vcov, df_r)

    # ── H2-2 pairwise ───────────────────────────────────────────
    # β_agg - β_aff
    c_agg_aff = np.array([0.0, 1.0, -1.0,  0.0,  0.0])
    est_aa, se_aa, t_aa, p_aa = linear_contrast(c_agg_aff, beta, vcov, df_r)
    # β_agg - β_se
    c_agg_se  = np.array([0.0, 1.0,  0.0, -1.0,  0.0])
    est_as, se_as, t_as, p_as = linear_contrast(c_agg_se,  beta, vcov, df_r)
    # β_agg - β_sd
    c_agg_sd  = np.array([0.0, 1.0,  0.0,  0.0, -1.0])
    est_asd, se_asd, t_asd, p_asd = linear_contrast(c_agg_sd, beta, vcov, df_r)

    def interp_h1(est, p):
        if p < 0.01 and est > 0:
            return "H1 지지: 전체 유머 평균효과 양수 유의 (p<.01)"
        if p < 0.05 and est > 0:
            return "H1 지지: 전체 유머 평균효과 양수 유의 (p<.05)"
        if p < 0.10 and est > 0:
            return "H1 부분 지지: 전체 유머 평균효과 양수 유의 (p<.10)"
        return "H1 지지 불가"

    def interp_h21(est, p):
        if p < 0.01 and est > 0:
            return "H2-1 지지: aggressive > other humor weighted average (p<.01)"
        if p < 0.05 and est > 0:
            return "H2-1 지지: aggressive > other humor weighted average (p<.05)"
        if p < 0.10 and est > 0:
            return "H2-1 부분 지지: aggressive > other humor weighted average (p<.10)"
        if est > 0:
            return "H2-1 지지 불가: 방향 맞으나 유의하지 않음"
        return "H2-1 지지 불가: aggressive <= other humor"

    def interp_pair(est, p, other_label):
        if p < 0.01 and est > 0:
            return f"H2-2 지지: aggressive > {other_label} (p<.01)"
        if p < 0.05 and est > 0:
            return f"H2-2 지지: aggressive > {other_label} (p<.05)"
        if p < 0.10 and est > 0:
            return f"H2-2 부분 지지: aggressive > {other_label} (p<.10)"
        if est > 0:
            return f"H2-2 지지 불가: aggressive > {other_label} 방향이나 유의하지 않음"
        return f"H2-2 지지 불가: aggressive <= {other_label}"

    contrast_rows = [
        {
            "test":             "H1_humor_avg_vs_nonhumor",
            "hypothesis":       "H1",
            "contrast_label":   "weighted avg humor effect vs non-humorous",
            "contrast_formula": "w_agg*β1 + w_aff*β2 + w_se*β3 + w_sd*β4",
            "weights_used":     f"w_agg={w_agg:.4f} w_aff={w_aff:.4f} w_se={w_se:.4f} w_sd={w_sd:.4f}",
            "estimate":         f"{est_h1:.6f}",
            "se":               f"{se_h1:.6f}",
            "t_stat":           f"{t_h1:.4f}",
            "p_value_two_sided":f"{p_h1:.6f}",
            "stars":            p_stars(p_h1),
            "interpretation":   interp_h1(est_h1, p_h1),
        },
        {
            "test":             "H2_1_aggressive_vs_other_weighted",
            "hypothesis":       "H2-1",
            "contrast_label":   "aggressive vs other humor weighted average",
            "contrast_formula": "β1 - (w_aff2*β2 + w_se2*β3 + w_sd2*β4)",
            "weights_used":     f"w_aff2={w_aff2:.4f} w_se2={w_se2:.4f} w_sd2={w_sd2:.4f}",
            "estimate":         f"{est_h21:.6f}",
            "se":               f"{se_h21:.6f}",
            "t_stat":           f"{t_h21:.4f}",
            "p_value_two_sided":f"{p_h21:.6f}",
            "stars":            p_stars(p_h21),
            "interpretation":   interp_h21(est_h21, p_h21),
        },
        {
            "test":             "H2_2a_aggressive_vs_affiliative",
            "hypothesis":       "H2-2",
            "contrast_label":   "aggressive vs affiliative",
            "contrast_formula": "β1 - β2",
            "weights_used":     "—",
            "estimate":         f"{est_aa:.6f}",
            "se":               f"{se_aa:.6f}",
            "t_stat":           f"{t_aa:.4f}",
            "p_value_two_sided":f"{p_aa:.6f}",
            "stars":            p_stars(p_aa),
            "interpretation":   interp_pair(est_aa, p_aa, "affiliative"),
        },
        {
            "test":             "H2_2b_aggressive_vs_self_enhancing",
            "hypothesis":       "H2-2",
            "contrast_label":   "aggressive vs self-enhancing",
            "contrast_formula": "β1 - β3",
            "weights_used":     "—",
            "estimate":         f"{est_as:.6f}",
            "se":               f"{se_as:.6f}",
            "t_stat":           f"{t_as:.4f}",
            "p_value_two_sided":f"{p_as:.6f}",
            "stars":            p_stars(p_as),
            "interpretation":   interp_pair(est_as, p_as, "self-enhancing"),
        },
        {
            "test":             "H2_2c_aggressive_vs_self_defeating",
            "hypothesis":       "H2-2",
            "contrast_label":   "aggressive vs self-defeating",
            "contrast_formula": "β1 - β4",
            "weights_used":     "—",
            "estimate":         f"{est_asd:.6f}",
            "se":               f"{se_asd:.6f}",
            "t_stat":           f"{t_asd:.4f}",
            "p_value_two_sided":f"{p_asd:.6f}",
            "stars":            p_stars(p_asd),
            "interpretation":   interp_pair(est_asd, p_asd, "self-defeating"),
        },
    ]
    write_csv(OUT / "simple_ols_h1_h2_contrast_tests.csv", contrast_rows)

    # 7. Model specification MD
    spec_md = f"""\
# Simple OLS Model Specification — H1 and H2 Diagnostic

## Model (M1 Simple OLS)

```
log(1 + Engagement_i) = β₀
                      + β₁ Aggressive_i
                      + β₂ Affiliative_i
                      + β₃ SelfEnhancing_i
                      + β₄ SelfDefeating_i
                      + ε_i
```

| Item | Value |
|:---|:---|
| DV | log_total_engagement (log₁₊₁) |
| Reference category | non_humorous (omitted) |
| Controls | NONE |
| Fixed effects | NONE |
| H3 variables | EXCLUDED |
| SE type | Classical OLS (homoskedastic) |
| Stars convention | *** p<.01 / ** p<.05 / * p<.10 (two-sided) |

## Identification Rules Applied

1. `non_humorous` = reference category (omitted dummy)
2. `non_humorous` dummy not included in regression
3. `HumorPresence` dummy not included (avoids perfect multicollinearity)
4. Only four humor type dummies as IVs
5. No numeric company_id covariate
6. No C(company_id) firm fixed effects

## Excluded Variables

- H3: aggressive humor usage intensity, intensity², interaction terms
- Controls: text_length, hashtag_count, mention_count, emoji_count
- Fixed effects: year, month, hour, firm

## Data Source

- Input: `{H2_CSV.name}`
- N = {n_tot:,} Fortune100 posts
- Classifier: {CLASSIFIER_NOTE}
"""
    (OUT / "simple_ols_h1_h2_model_specification.md").write_text(spec_md, encoding="utf-8")
    print(f"  → simple_ols_h1_h2_model_specification.md")

    # 8. Interpretation MD
    # Determine H2-2 verdict
    h22_results = [
        ("aggressive vs affiliative",    est_aa,  p_aa),
        ("aggressive vs self-enhancing", est_as,  p_as),
        ("aggressive vs self-defeating", est_asd, p_asd),
    ]
    n_h22_support = sum(1 for _, e, p in h22_results if e > 0 and p < 0.05)
    if n_h22_support == 3:
        h22_verdict = "완전 지지 (full support): 세 대비 모두 aggressive > other (p<.05)"
    elif n_h22_support == 2:
        h22_verdict = "부분 지지 (partial support): 세 대비 중 2개 유의"
    elif n_h22_support == 1:
        h22_verdict = "부분 지지 (partial support): 세 대비 중 1개 유의"
    else:
        h22_verdict = "지지 불가: 유의한 pairwise 우위 없음"

    interp_md = f"""\
# Simple OLS H1 / H2 해석 (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반 결과. Controls 및 Fixed Effects 미포함.
> NOT_A_CANDIDATE 수준 증거. Classifier leakage risk 존재.

---

## 1. 표본 구성

| 유형 | N | 전체 비율 | 유머 내 비율 |
|:---|---:|---:|---:|
| Non-humorous (reference) | {n_nh:,} | {n_nh/n_tot*100:.1f}% | — |
| Aggressive | {n_agg:,} | {n_agg/n_tot*100:.1f}% | {n_agg/n_hum*100:.1f}% |
| Affiliative | {n_aff:,} | {n_aff/n_tot*100:.1f}% | {n_aff/n_hum*100:.1f}% |
| Self-Enhancing | {n_se:,} | {n_se/n_tot*100:.1f}% | {n_se/n_hum*100:.1f}% |
| Self-Defeating | {n_sd:,} | {n_sd/n_tot*100:.1f}% | {n_sd/n_hum*100:.1f}% |
| Humor Total | {n_hum:,} | {n_hum/n_tot*100:.1f}% | 100% |
| **Total** | **{n_tot:,}** | **100%** | — |

---

## 2. 회귀 결과 (M1 Simple OLS)

```
log(1 + Engagement) = β₀ + β₁·Aggressive + β₂·Affiliative + β₃·SelfEnhancing + β₄·SelfDefeating
```

| 변수 | β | SE | t | p (2-sided) | Stars |
|:---|---:|---:|---:|---:|:---:|
| Intercept | {beta[0]:+.4f} | {se[0]:.4f} | {t_stat[0]:+.4f} | {p_two[0]:.4f} | {p_stars(p_two[0])} |
| Aggressive (β₁) | {beta[1]:+.4f} | {se[1]:.4f} | {t_stat[1]:+.4f} | {p_two[1]:.4f} | {p_stars(p_two[1])} |
| Affiliative (β₂) | {beta[2]:+.4f} | {se[2]:.4f} | {t_stat[2]:+.4f} | {p_two[2]:.4f} | {p_stars(p_two[2])} |
| Self-Enhancing (β₃) | {beta[3]:+.4f} | {se[3]:.4f} | {t_stat[3]:+.4f} | {p_two[3]:.4f} | {p_stars(p_two[3])} |
| Self-Defeating (β₄) | {beta[4]:+.4f} | {se[4]:.4f} | {t_stat[4]:+.4f} | {p_two[4]:.4f} | {p_stars(p_two[4])} |

N={n:,} | R²={r2:.4f} | adj-R²={r2_adj:.4f} | df_resid={df_r:,}
Reference category = non_humorous | Controls = none | FE = none

---

## 3. H1 검정 결과

**명제**: 유머 포스트가 비유머 포스트보다 engagement가 높다.

| 유형 | β | 방향 | 유의 |
|:---|---:|:---:|:---:|
| Aggressive (β₁) | {beta[1]:+.4f} | {'✓' if beta[1]>0 else '✗'} | {p_stars(p_two[1]) or 'ns'} |
| Affiliative (β₂) | {beta[2]:+.4f} | {'✓' if beta[2]>0 else '✗'} | {p_stars(p_two[2]) or 'ns'} |
| Self-Enhancing (β₃) | {beta[3]:+.4f} | {'✓' if beta[3]>0 else '✗'} | {p_stars(p_two[3]) or 'ns'} |
| Self-Defeating (β₄) | {beta[4]:+.4f} | {'✓' if beta[4]>0 else '✗'} | {p_stars(p_two[4]) or 'ns'} |

**전체 유머 평균효과** (가중치 = 유머 내 유형 비율):

- 추정치: {est_h1:+.4f}  SE={se_h1:.4f}  t={t_h1:+.4f}  p={p_h1:.4f} {p_stars(p_h1)}
- **{interp_h1(est_h1, p_h1)}**

---

## 4. H2-1 검정 결과

**명제**: Aggressive humor가 other humor types보다 engagement가 높다.

- Contrast: β₁ − (w_aff·β₂ + w_se·β₃ + w_sd·β₄)
- Other-humor weights: affiliative={w_aff2:.4f}, self-enhancing={w_se2:.4f}, self-defeating={w_sd2:.4f}
- 추정치: {est_h21:+.4f}  SE={se_h21:.4f}  t={t_h21:+.4f}  p={p_h21:.4f} {p_stars(p_h21)}
- **{interp_h21(est_h21, p_h21)}**

---

## 5. H2-2 검정 결과 (Pairwise Contrasts)

**명제**: Aggressive humor가 각 유머 유형보다 engagement가 높다.

| Contrast | 추정치 | SE | t | p (2-sided) | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| β₁ − β₂ (agg vs. affiliative) | {est_aa:+.4f} | {se_aa:.4f} | {t_aa:+.4f} | {p_aa:.4f} | {p_stars(p_aa)} | {interp_pair(est_aa, p_aa, 'affiliative')} |
| β₁ − β₃ (agg vs. self-enhancing) | {est_as:+.4f} | {se_as:.4f} | {t_as:+.4f} | {p_as:.4f} | {p_stars(p_as)} | {interp_pair(est_as, p_as, 'self-enhancing')} |
| β₁ − β₄ (agg vs. self-defeating) | {est_asd:+.4f} | {se_asd:.4f} | {t_asd:+.4f} | {p_asd:.4f} | {p_stars(p_asd)} | {interp_pair(est_asd, p_asd, 'self-defeating')} |

**H2-2 종합 판정**: {h22_verdict}

---

## 6. 해석 주의사항

1. **Classifier limitation**: 결과는 domain-adapted TF-IDF LogReg 예측값 기반이며, 동일 코퍼스에서 훈련된 분류기를 적용했으므로 leakage risk 존재.
2. **Controls/FE 미포함**: 기업 특성, 시간 트렌드, 포스트 속성이 통제되지 않아 추정치에 omitted variable bias가 있을 수 있음.
3. **단순 OLS 진단 목적**: 이 결과는 "기초 OLS 진단"으로 해석하며, causal 또는 robust evidence로 단정하지 않음.
"""
    (OUT / "simple_ols_h1_h2_interpretation.md").write_text(interp_md, encoding="utf-8")
    print(f"  → simple_ols_h1_h2_interpretation.md")

    # 9. Summary
    print("\n=== CONTRAST SUMMARY ===")
    for cr in contrast_rows:
        print(f"  [{cr['hypothesis']}] {cr['contrast_label']}")
        print(f"    estimate={cr['estimate']}  SE={cr['se']}  "
              f"t={cr['t_stat']}  p={cr['p_value_two_sided']}  {cr['stars']}")
        print(f"    → {cr['interpretation']}")

    print(f"\n  H2-2 종합: {h22_verdict}")
    print("\n=== run_simple_ols_h1_h2_only COMPLETE ===")


if __name__ == "__main__":
    main()
