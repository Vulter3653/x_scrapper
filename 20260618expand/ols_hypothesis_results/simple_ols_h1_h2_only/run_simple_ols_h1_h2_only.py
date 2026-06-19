"""
run_simple_ols_h1_h2_only.py

OLS diagnostic for H1 and H2 using domain-adapted classifier predictions.

Models:
  M1 Simple OLS:
    log1p_engagement ~ β₀ + β₁*Aggressive + β₂*Affiliative
                     + β₃*SelfEnhancing + β₄*SelfDefeating + ε

  M2 Firm FE (FWL within-firm demeaning):
    log1p_engagement_dm ~ β₁*Aggressive_dm + β₂*Affiliative_dm
                        + β₃*SelfEnhancing_dm + β₄*SelfDefeating_dm + ε

Reference category : non_humorous (omitted)
Controls           : NONE
Time FE            : NONE
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

def ols_fit(X: np.ndarray, y: np.ndarray, df_override: int | None = None):
    """Classical OLS. df_override sets df_resid (used for FWL to account for FE)."""
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
    """Subtract group mean from each element (FWL within-demeaning)."""
    out = arr.copy().astype(float)
    for g in set(groups):
        idx = [i for i, x in enumerate(groups) if x == g]
        out[idx] -= out[idx].mean(axis=0)
    return out


def make_dummies(groups: list, ref: str | None = None) -> tuple[np.ndarray, list]:
    """Binary dummy matrix. ref=None includes all categories (no reference dropped)."""
    cats = [c for c in sorted(set(groups)) if ref is None or c != ref]
    groups_arr = np.array(groups)
    mat = np.column_stack([(groups_arr == cat).astype(float) for cat in cats])
    return mat, cats


def linear_contrast(c: np.ndarray, beta: np.ndarray, vcov: np.ndarray, df_r: int):
    estimate = float(c @ beta)
    var_c    = float(c @ vcov @ c)
    se_c     = math.sqrt(max(var_c, 0.0))
    t_c      = estimate / se_c if se_c > 0 else float("nan")
    p_two    = 2 * t_dist.sf(abs(t_c), df=df_r) if not math.isnan(t_c) else float("nan")
    return estimate, se_c, t_c, p_two


# ── interpretation helpers ────────────────────────────────────────────────────

def interp_h1(est, p):
    if p < 0.01 and est > 0: return "H1 지지: 전체 유머 평균효과 양수 유의 (p<.01)"
    if p < 0.05 and est > 0: return "H1 지지: 전체 유머 평균효과 양수 유의 (p<.05)"
    if p < 0.10 and est > 0: return "H1 부분 지지: 전체 유머 평균효과 양수 유의 (p<.10)"
    return "H1 지지 불가"

def interp_h21(est, p):
    if p < 0.01 and est > 0: return "H2-1 지지: aggressive > other humor weighted average (p<.01)"
    if p < 0.05 and est > 0: return "H2-1 지지: aggressive > other humor weighted average (p<.05)"
    if p < 0.10 and est > 0: return "H2-1 부분 지지: aggressive > other humor weighted average (p<.10)"
    if est > 0:               return "H2-1 지지 불가: 방향 맞으나 유의하지 않음"
    return "H2-1 지지 불가: aggressive <= other humor"

def interp_pair(est, p, lbl):
    if p < 0.01 and est > 0: return f"H2-2 지지: aggressive > {lbl} (p<.01)"
    if p < 0.05 and est > 0: return f"H2-2 지지: aggressive > {lbl} (p<.05)"
    if p < 0.10 and est > 0: return f"H2-2 부분 지지: aggressive > {lbl} (p<.10)"
    if est > 0:               return f"H2-2 지지 불가: aggressive > {lbl} 방향이나 유의하지 않음"
    return f"H2-2 지지 불가: aggressive <= {lbl}"


# ── contrast block ────────────────────────────────────────────────────────────

def run_contrasts(beta, vcov, df_r,
                  w_agg, w_aff, w_se, w_sd,
                  w_aff2, w_se2, w_sd2, model_label):
    """Return list of contrast result dicts. beta has 4 elements: [agg,aff,se,sd]."""
    c_h1   = np.array([w_agg, w_aff, w_se, w_sd])
    c_h21  = np.array([1.0, -w_aff2, -w_se2, -w_sd2])
    c_aa   = np.array([1.0, -1.0,  0.0,  0.0])
    c_as   = np.array([1.0,  0.0, -1.0,  0.0])
    c_asd  = np.array([1.0,  0.0,  0.0, -1.0])

    rows = []
    for test, hyp, lbl, formula, wt, c in [
        ("H1_humor_avg_vs_nonhumor",       "H1",   "weighted avg humor effect vs non-humorous",
         "w_agg*β1+w_aff*β2+w_se*β3+w_sd*β4",
         f"w_agg={w_agg:.4f} w_aff={w_aff:.4f} w_se={w_se:.4f} w_sd={w_sd:.4f}", c_h1),
        ("H2_1_aggressive_vs_other",       "H2-1", "aggressive vs other humor weighted average",
         "β1-(w_aff2*β2+w_se2*β3+w_sd2*β4)",
         f"w_aff2={w_aff2:.4f} w_se2={w_se2:.4f} w_sd2={w_sd2:.4f}", c_h21),
        ("H2_2a_aggressive_vs_affiliative","H2-2", "aggressive vs affiliative",  "β1-β2", "—", c_aa),
        ("H2_2b_aggressive_vs_self_enhancing","H2-2","aggressive vs self-enhancing","β1-β3","—",c_as),
        ("H2_2c_aggressive_vs_self_defeating","H2-2","aggressive vs self-defeating","β1-β4","—",c_asd),
    ]:
        est, se_c, t_c, p_c = linear_contrast(c, beta, vcov, df_r)
        if hyp == "H1":
            interp = interp_h1(est, p_c)
        elif hyp == "H2-1":
            interp = interp_h21(est, p_c)
        else:
            other = lbl.split("vs ")[-1]
            interp = interp_pair(est, p_c, other)
        rows.append({
            "model": model_label, "test": test, "hypothesis": hyp,
            "contrast_label": lbl, "contrast_formula": formula,
            "weights_used": wt,
            "estimate": f"{est:.6f}", "se": f"{se_c:.6f}",
            "t_stat": f"{t_c:.4f}", "p_value_two_sided": f"{p_c:.6f}",
            "stars": p_stars(p_c), "interpretation": interp,
        })
    return rows


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== run_simple_ols_h1_h2_only ===\n")

    with open(H2_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input rows: {len(rows)}  |  {H2_CSV.name}")

    IVS = ["aggressive_humor", "affiliative_humor",
           "self_enhancing_humor", "self_defeating_humor"]
    DV  = "log_total_engagement"
    for col in IVS + [DV]:
        assert col in rows[0], f"Missing column: {col}"

    # ── Sample counts ─────────────────────────────────────────────────────
    n_agg = sum(1 for r in rows if r["aggressive_humor"]    == "1")
    n_aff = sum(1 for r in rows if r["affiliative_humor"]   == "1")
    n_se  = sum(1 for r in rows if r["self_enhancing_humor"]== "1")
    n_sd  = sum(1 for r in rows if r["self_defeating_humor"]== "1")
    n_nh  = sum(1 for r in rows if r["non_humorous"]        == "1")
    n_tot = len(rows)
    n_hum = n_agg + n_aff + n_se + n_sd
    assert n_nh + n_hum == n_tot
    firms = sorted(set(r["company_name"] for r in rows))
    n_firms = len(firms)

    dist_rows = [
        {"group": "non_humorous (reference)", "n": n_nh,  "pct_total": f"{n_nh/n_tot*100:.2f}%", "pct_humor": "—"},
        {"group": "aggressive",               "n": n_agg, "pct_total": f"{n_agg/n_tot*100:.2f}%","pct_humor": f"{n_agg/n_hum*100:.2f}%"},
        {"group": "affiliative",              "n": n_aff, "pct_total": f"{n_aff/n_tot*100:.2f}%","pct_humor": f"{n_aff/n_hum*100:.2f}%"},
        {"group": "self_enhancing",           "n": n_se,  "pct_total": f"{n_se/n_tot*100:.2f}%", "pct_humor": f"{n_se/n_hum*100:.2f}%"},
        {"group": "self_defeating",           "n": n_sd,  "pct_total": f"{n_sd/n_tot*100:.2f}%", "pct_humor": f"{n_sd/n_hum*100:.2f}%"},
        {"group": "humor_total",              "n": n_hum, "pct_total": f"{n_hum/n_tot*100:.2f}%","pct_humor": "100.00%"},
        {"group": "TOTAL",                    "n": n_tot, "pct_total": "100.00%",                 "pct_humor": "—"},
        {"group": "n_firms",                  "n": n_firms,"pct_total": "—",                      "pct_humor": "—"},
    ]
    write_csv(OUT / "simple_ols_h1_h2_sample_distribution.csv", dist_rows)
    print(f"  N={n_tot:,}  humor={n_hum:,} (agg={n_agg} aff={n_aff} se={n_se} sd={n_sd})"
          f"  non-humor={n_nh:,}  firms={n_firms}")

    # ── Contrast weights ──────────────────────────────────────────────────
    w_agg = n_agg / n_hum
    w_aff = n_aff / n_hum
    w_se  = n_se  / n_hum
    w_sd  = n_sd  / n_hum
    n_other = n_aff + n_se + n_sd
    w_aff2 = n_aff / n_other
    w_se2  = n_se  / n_other
    w_sd2  = n_sd  / n_other

    # ════════════════════════════════════════════════════════════════════════
    # M1: Simple OLS
    # ════════════════════════════════════════════════════════════════════════
    X_m1 = np.array([
        [1.0, to_f(r["aggressive_humor"]), to_f(r["affiliative_humor"]),
         to_f(r["self_enhancing_humor"]),  to_f(r["self_defeating_humor"])]
        for r in rows
    ])
    y = np.array([to_f(r[DV]) for r in rows])

    b1, v1, s1, t1, p1, n1, k1, r2_1, r2a_1, df1 = ols_fit(X_m1, y)
    fn_m1 = ["intercept", "aggressive", "affiliative", "self_enhancing", "self_defeating"]

    print(f"\nM1 Simple OLS: N={n1:,} k={k1} df={df1:,} R²={r2_1:.4f} adj-R²={r2a_1:.4f}")
    for i, fn in enumerate(fn_m1):
        print(f"  {fn:<22} β={b1[i]:+.4f}  SE={s1[i]:.4f}  t={t1[i]:+.4f}  {p_stars(p1[i])}")

    # ════════════════════════════════════════════════════════════════════════
    # M2: Simple OLS + 기업 더미 변수 (99개, 인터셉트 없음)
    # ════════════════════════════════════════════════════════════════════════
    firm_groups = [r["company_name"] for r in rows]
    D_firm, firm_cats = make_dummies(firm_groups, ref=None)
    n_firm_dummies = len(firm_cats)  # 99

    agg_arr = np.array([to_f(r["aggressive_humor"])     for r in rows])
    aff_arr = np.array([to_f(r["affiliative_humor"])    for r in rows])
    se_arr  = np.array([to_f(r["self_enhancing_humor"]) for r in rows])
    sd_arr  = np.array([to_f(r["self_defeating_humor"]) for r in rows])

    # [agg, aff, se, sd, D_firm(99)] — no intercept (firm dummies absorb it)
    X_m2 = np.column_stack([agg_arr, aff_arr, se_arr, sd_arr, D_firm])
    b2, v2, s2, t2, p2, n2, k2, r2_2, r2a_2, df2 = ols_fit(X_m2, y)
    fn_m2 = ["aggressive", "affiliative", "self_enhancing", "self_defeating"]

    print(f"\nM2 Firm dummies OLS: N={n2:,} firm_dummies={n_firm_dummies} k={k2} df={df2:,}"
          f" R²={r2_2:.4f} adj-R²={r2a_2:.4f}")
    for i, fn in enumerate(fn_m2):
        print(f"  {fn:<22} β={b2[i]:+.4f}  SE={s2[i]:.4f}  t={t2[i]:+.4f}  {p_stars(p2[i])}")

    # ════════════════════════════════════════════════════════════════════════
    # M3: Time FE (Year + Month_of_year dummies, explicit)
    # ════════════════════════════════════════════════════════════════════════
    year_groups  = [r["year"]  for r in rows]
    month_groups = [r["month"] for r in rows]
    REF_YEAR  = "2015"
    REF_MONTH = "01"

    D_year,  year_cats  = make_dummies(year_groups,  REF_YEAR)
    D_month, month_cats = make_dummies(month_groups, REF_MONTH)
    n_year_dummies  = len(year_cats)
    n_month_dummies = len(month_cats)

    X_m3 = np.column_stack([X_m1, D_year, D_month])
    b3, v3, s3, t3, p3, n3, k3, r2_3, r2a_3, df3 = ols_fit(X_m3, y)

    print(f"\nM3 Time FE (year+month): N={n3:,} k={k3} df={df3:,}"
          f" R²={r2_3:.4f} adj-R²={r2a_3:.4f}")
    print(f"  year_dummies={n_year_dummies} (ref={REF_YEAR})  month_dummies={n_month_dummies} (ref={REF_MONTH})")
    for i, fn in enumerate(["intercept", "aggressive", "affiliative",
                             "self_enhancing", "self_defeating"]):
        print(f"  {fn:<22} β={b3[i]:+.4f}  SE={s3[i]:.4f}  t={t3[i]:+.4f}  {p_stars(p3[i])}")

    # ════════════════════════════════════════════════════════════════════════
    # M4: 기업 더미 + 시간 FE (all 99 firm dummies, no intercept)
    # ════════════════════════════════════════════════════════════════════════
    # D_firm, agg_arr, aff_arr, se_arr, sd_arr already built in M2
    # No intercept: [agg, aff, se, sd, D_firm(99), D_year(13 ref=2015), D_month(11 ref=01)]
    X_m4 = np.column_stack([agg_arr, aff_arr, se_arr, sd_arr, D_firm, D_year, D_month])
    b4, v4, s4, t4, p4, n4, k4, r2_4, r2a_4, df4 = ols_fit(X_m4, y)

    print(f"\nM4 Firm+Time FE (two-way): N={n4:,} firms={n_firms} k={k4} df={df4:,}"
          f" R²={r2_4:.4f} adj-R²={r2a_4:.4f}")
    print(f"  firm_dummies={n_firm_dummies} (no reference, no intercept)"
          f"  year_dummies={n_year_dummies} (ref=2015)  month_dummies={n_month_dummies} (ref=01)")
    for i, fn in enumerate(["aggressive", "affiliative", "self_enhancing", "self_defeating"]):
        print(f"  {fn:<22} β={b4[i]:+.4f}  SE={s4[i]:.4f}  t={t4[i]:+.4f}  {p_stars(p4[i])}")

    # ── Regression results CSV ────────────────────────────────────────────
    reg_rows = []
    for i, fn in enumerate(fn_m1):
        reg_rows.append({
            "model": "M1_simple_ols", "variable": fn,
            "coefficient": f"{b1[i]:.6f}", "classical_ols_se": f"{s1[i]:.6f}",
            "t_stat": f"{t1[i]:.4f}", "p_value_two_sided": f"{p1[i]:.6f}",
            "stars": p_stars(p1[i]),
            "n_obs": n1, "r_squared": f"{r2_1:.6f}", "r_squared_adj": f"{r2a_1:.6f}",
            "df_resid": df1, "n_firms": n_firms,
            "reference_category": "non_humorous",
            "controls_included": "false", "fixed_effects": "none",
            "h3_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    for i, fn in enumerate(fn_m2):
        reg_rows.append({
            "model": "M2_firm_dummies", "variable": fn,
            "coefficient": f"{b2[i]:.6f}", "classical_ols_se": f"{s2[i]:.6f}",
            "t_stat": f"{t2[i]:.4f}", "p_value_two_sided": f"{p2[i]:.6f}",
            "stars": p_stars(p2[i]),
            "n_obs": n2, "r_squared": f"{r2_2:.6f}", "r_squared_adj": f"{r2a_2:.6f}",
            "df_resid": df2, "n_firms": n_firms,
            "reference_category": "non_humorous",
            "controls_included": "false",
            "fixed_effects": f"firm_dummies({n_firm_dummies} all, no reference, no intercept)",
            "h3_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    for i, fn in enumerate(["intercept", "aggressive", "affiliative",
                             "self_enhancing", "self_defeating"]):
        reg_rows.append({
            "model": "M3_time_fe_year_month", "variable": fn,
            "coefficient": f"{b3[i]:.6f}", "classical_ols_se": f"{s3[i]:.6f}",
            "t_stat": f"{t3[i]:.4f}", "p_value_two_sided": f"{p3[i]:.6f}",
            "stars": p_stars(p3[i]),
            "n_obs": n3, "r_squared": f"{r2_3:.6f}", "r_squared_adj": f"{r2a_3:.6f}",
            "df_resid": df3, "n_firms": n_firms,
            "reference_category": "non_humorous",
            "controls_included": "false",
            "fixed_effects": f"year_dummies({n_year_dummies} ref={REF_YEAR}) + month_dummies({n_month_dummies} ref={REF_MONTH})",
            "h3_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    for i, fn in enumerate(["aggressive", "affiliative", "self_enhancing", "self_defeating"]):
        reg_rows.append({
            "model": "M4_firm_year_month_fe", "variable": fn,
            "coefficient": f"{b4[i]:.6f}", "classical_ols_se": f"{s4[i]:.6f}",
            "t_stat": f"{t4[i]:.4f}", "p_value_two_sided": f"{p4[i]:.6f}",
            "stars": p_stars(p4[i]),
            "n_obs": n4, "r_squared": f"{r2_4:.6f}", "r_squared_adj": f"{r2a_4:.6f}",
            "df_resid": df4, "n_firms": n_firms,
            "reference_category": "non_humorous",
            "controls_included": "false",
            "fixed_effects": f"firm_dummies({n_firm_dummies} all, no reference, no intercept) + year_dummies({n_year_dummies} ref=2015) + month_dummies({n_month_dummies} ref=01)",
            "h3_variables_included": "false",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    write_csv(OUT / "simple_ols_h1_h2_regression_results.csv", reg_rows)

    # ── Contrast tests: M1 and M2 ─────────────────────────────────────────
    # M1: beta indices [1..4] = agg,aff,se,sd; vcov slice [1:5,1:5]
    beta_iv_m1 = b1[1:]
    vcov_iv_m1 = v1[1:, 1:]
    ct_m1 = run_contrasts(beta_iv_m1, vcov_iv_m1, df1,
                          w_agg, w_aff, w_se, w_sd, w_aff2, w_se2, w_sd2, "M1_simple_ols")

    # M2: beta[0:4] = [agg,aff,se,sd]; vcov[0:4,0:4]
    ct_m2 = run_contrasts(b2[0:4], v2[0:4, 0:4], df2,
                          w_agg, w_aff, w_se, w_sd, w_aff2, w_se2, w_sd2, "M2_firm_dummies")

    # M3: beta[1:5] = [agg,aff,se,sd]; vcov[1:5,1:5]
    ct_m3 = run_contrasts(b3[1:5], v3[1:5, 1:5], df3,
                          w_agg, w_aff, w_se, w_sd, w_aff2, w_se2, w_sd2, "M3_time_fe_year_month")

    # M4: no intercept → beta[0:4] = [agg,aff,se,sd]; vcov[0:4,0:4]
    ct_m4 = run_contrasts(b4[0:4], v4[0:4, 0:4], df4,
                          w_agg, w_aff, w_se, w_sd, w_aff2, w_se2, w_sd2, "M4_firm_year_month_fe")

    write_csv(OUT / "simple_ols_h1_h2_contrast_tests.csv", ct_m1 + ct_m2 + ct_m3 + ct_m4)

    # ── Model specification MD ────────────────────────────────────────────
    spec_md = f"""\
# OLS Model Specification — H1 and H2 Diagnostic

## M1 Simple OLS

```
log(1+Engagement_i) = β₀ + β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating + ε_i
```

## M2 기업 더미 변수 OLS (Simple OLS + 99 firm dummies, no intercept)

```
log(1+Engagement_i) = β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating
                    + Σ(f=1~99) γ_f · D_firm_f + ε_i
```

인터셉트 없음 (기업 더미 99개가 흡수). reference 기업 없음 (all 99 included).

| Item | M1 | M2 |
|:---|:---|:---|
| DV | log_total_engagement | log_total_engagement |
| Reference category | non_humorous (omitted) | non_humorous (omitted) |
| Controls | NONE | NONE |
| Firm dummies | NONE | 99개 (no reference, no intercept) |
| Time FE | NONE | NONE |
| H3 variables | EXCLUDED | EXCLUDED |
| N | {n_tot:,} | {n2:,} |
| k | {k1} | {k2} |
| df_resid | {df1:,} | {df2:,} |
| SE type | Classical OLS | Classical OLS |

## Identification Rules

1. non_humorous = reference category (omitted)
2. non_humorous dummy not included in regression
3. HumorPresence dummy not included (avoids perfect multicollinearity)
4. No company_id numeric covariate
5. M2 firm dummies: 99개 더미 직접 포함, 인터셉트 제거 (dummy variable trap 방지)

## Data Source

- `{H2_CSV.name}` — N={n_tot:,} Fortune100 posts
- Classifier: {CLASSIFIER_NOTE}
"""
    (OUT / "simple_ols_h1_h2_model_specification.md").write_text(spec_md, encoding="utf-8")
    print("  → simple_ols_h1_h2_model_specification.md")

    # ── Interpretation MD ─────────────────────────────────────────────────
    def h22_verdict(contrast_rows, model_lbl):
        sub = [r for r in contrast_rows if r["model"] == model_lbl and r["hypothesis"] == "H2-2"]
        n_sup = sum(1 for r in sub if float(r["estimate"]) > 0 and float(r["p_value_two_sided"]) < 0.05)
        if n_sup == 3: return "완전 지지 (3/3 유의)"
        if n_sup == 2: return "부분 지지 (2/3 유의)"
        if n_sup == 1: return "부분 지지 (1/3 유의)"
        return "지지 불가"

    all_ct = ct_m1 + ct_m2 + ct_m3 + ct_m4

    def ct_row(model_lbl, test_key):
        for r in all_ct:
            if r["model"] == model_lbl and r["test"] == test_key:
                return r
        return {}

    interp_md = f"""\
# OLS H1 / H2 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 유형 | N | 비율(전체) | 비율(유머 내) |
|:---|---:|---:|---:|
| Non-humorous (reference) | {n_nh:,} | {n_nh/n_tot*100:.1f}% | — |
| Aggressive | {n_agg:,} | {n_agg/n_tot*100:.1f}% | {n_agg/n_hum*100:.1f}% |
| Affiliative | {n_aff:,} | {n_aff/n_tot*100:.1f}% | {n_aff/n_hum*100:.1f}% |
| Self-Enhancing | {n_se:,} | {n_se/n_tot*100:.1f}% | {n_se/n_hum*100:.1f}% |
| Self-Defeating | {n_sd:,} | {n_sd/n_tot*100:.1f}% | {n_sd/n_hum*100:.1f}% |
| Humor Total | {n_hum:,} | {n_hum/n_tot*100:.1f}% | 100% |
| **Total** | **{n_tot:,}** | **100%** | — |
| Firms | {n_firms} | — | — |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm dummies |
|:---|:---:|:---:|
| Aggressive (β₁) | {b1[1]:+.4f}{p_stars(p1[1])} ({s1[1]:.4f}) | {b2[0]:+.4f}{p_stars(p2[0])} ({s2[0]:.4f}) |
| Affiliative (β₂) | {b1[2]:+.4f}{p_stars(p1[2])} ({s1[2]:.4f}) | {b2[1]:+.4f}{p_stars(p2[1])} ({s2[1]:.4f}) |
| Self-Enhancing (β₃) | {b1[3]:+.4f}{p_stars(p1[3])} ({s1[3]:.4f}) | {b2[2]:+.4f}{p_stars(p2[2])} ({s2[2]:.4f}) |
| Self-Defeating (β₄) | {b1[4]:+.4f}{p_stars(p1[4])} ({s1[4]:.4f}) | {b2[3]:+.4f}{p_stars(p2[3])} ({s2[3]:.4f}) |
| Intercept | {b1[0]:+.4f} | — (absorbed by firm dummies) |
| N | {n_tot:,} | {n2:,} |
| Firms | — | {n_firms} |
| R² | {r2_1:.4f} | {r2_2:.4f} |
| adj-R² | {r2a_1:.4f} | {r2a_2:.4f} |
| df_resid | {df1:,} | {df2:,} |
| Controls | none | none |
| Firm dummies | no | 99개 (no reference, no intercept) |

*괄호 = classical OLS SE. *** p<.01 / ** p<.05 / * p<.10 (two-sided)*

---

## 3. H1 검정 — 전체 유머 가중평균효과

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
"""
    for ml in ["M1_simple_ols", "M2_firm_dummies", "M3_time_fe_year_month", "M4_firm_year_month_fe"]:
        r = ct_row(ml, "H1_humor_avg_vs_nonhumor")
        interp_md += f"| {ml} | {r['estimate']} | {r['se']} | {r['t_stat']} | {r['p_value_two_sided']} | {r['stars']} | {r['interpretation']} |\n"

    interp_md += f"""
---

## 4. H2-1 검정 — Aggressive vs Other Humor 가중평균

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
"""
    for ml in ["M1_simple_ols", "M2_firm_dummies", "M3_time_fe_year_month", "M4_firm_year_month_fe"]:
        r = ct_row(ml, "H2_1_aggressive_vs_other")
        interp_md += f"| {ml} | {r['estimate']} | {r['se']} | {r['t_stat']} | {r['p_value_two_sided']} | {r['stars']} | {r['interpretation']} |\n"

    interp_md += f"""
---

## 5. H2-2 검정 — Pairwise Contrasts

| 모델 | Contrast | 추정치 | SE | t | p | Stars | 판정 |
|:---|:---|---:|---:|---:|---:|:---:|:---|
"""
    for ml in ["M1_simple_ols", "M2_firm_dummies", "M3_time_fe_year_month", "M4_firm_year_month_fe"]:
        for tk, lbl in [
            ("H2_2a_aggressive_vs_affiliative",    "agg vs aff"),
            ("H2_2b_aggressive_vs_self_enhancing", "agg vs se"),
            ("H2_2c_aggressive_vs_self_defeating",  "agg vs sd"),
        ]:
            r = ct_row(ml, tk)
            interp_md += (f"| {ml} | {lbl} | {r['estimate']} | {r['se']} | "
                          f"{r['t_stat']} | {r['p_value_two_sided']} | {r['stars']} | {r['interpretation']} |\n")

    interp_md += f"""
**H2-2 종합**:
- M1 Simple OLS:        {h22_verdict(all_ct, 'M1_simple_ols')}
- M2 Firm FE (FWL):     {h22_verdict(all_ct, 'M2_firm_dummies')}
- M3 Time FE:           {h22_verdict(all_ct, 'M3_time_fe_year_month')}
- M4 Firm+Time FE:      {h22_verdict(all_ct, 'M4_firm_year_month_fe')}

---

## 6. 해석 주의사항

1. **Classifier limitation**: domain-adapted TF-IDF LogReg 예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
2. **Controls 미포함**: text_length, hashtag_count, mention_count 미통제. M2 Firm FE는 기업 수준 고정 이질성을 흡수하지만 시간 FE 및 포스트 속성은 여전히 미통제.
3. **단순 OLS 진단 목적**: causal 또는 robust evidence가 아닌 preliminary diagnostic.
"""
    (OUT / "simple_ols_h1_h2_interpretation.md").write_text(interp_md, encoding="utf-8")
    print("  → simple_ols_h1_h2_interpretation.md")

    # ── Console summary ───────────────────────────────────────────────────
    print("\n=== CONTRAST SUMMARY ===")
    for r in all_ct:
        print(f"  [{r['model']}] [{r['hypothesis']}] {r['contrast_label']}")
        print(f"    est={r['estimate']}  SE={r['se']}  t={r['t_stat']}  "
              f"p={r['p_value_two_sided']}  {r['stars']}")
        print(f"    → {r['interpretation']}")

    print("\n=== run_simple_ols_h1_h2_only COMPLETE ===")


if __name__ == "__main__":
    main()
