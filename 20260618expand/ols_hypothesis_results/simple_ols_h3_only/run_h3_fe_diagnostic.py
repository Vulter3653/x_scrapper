#!/usr/bin/env python3
"""H3 fixed-effects diagnostic: M1 simple OLS + M2 Firm FE + M3 Time FE + M4 Firm+Time FE.

Separate from run_simple_ols_h3_only.py (M1 baseline only).
Output files: h3_fe_diagnostic_*.csv / *.md  (do not overwrite simple_ols_h3_* files).

Unit: firm × month panel (N=3,532, 97 firms, 130 months).
DV:  mean_log_total_engagement
IV:  aggressive_humor_usage_intensity, aggressive_humor_usage_intensity_sq
Time FE: year + month_of_year dummies (common spec with H1/H2).
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
OUT  = Path(__file__).resolve().parent
INPUT = ROOT / "20260618expand" / "classifier_improvement" / "data" / "regression_ready" / "h3_firm_period_regression_ready.csv"

CLASSIFIER_NOTE = (
    "domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels "
    "(batch1+batch2); aggressive intensity = fraction of firm-month posts "
    "predicted as aggressive; NOT_A_CANDIDATE level evidence; leakage risk"
)


# ── helpers ──────────────────────────────────────────────────────────────────

def to_f(v: str) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return float("nan")


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
    return beta, vcov, se, t_stat, p_two, n, k, r2, r2_adj, df_r, resid


def demean_by_group(arr: np.ndarray, groups: list) -> np.ndarray:
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


# ── H3 diagnostics ───────────────────────────────────────────────────────────

def h3_diag(b1: float, b2: float, p2: float,
            obs_min: float, obs_max: float, model_lbl: str) -> dict:
    tp = -b1 / (2 * b2) if abs(b2) > 1e-14 else float("nan")
    in_range = (not math.isnan(tp)) and obs_min <= tp <= obs_max

    if b1 > 0 and b2 < 0 and p2 < 0.10 and in_range:
        pattern   = "inverted-U"
        supported = "true"
        verdict   = "H3 지지: β₁>0, β₂<0 유의(p<.10), 전환점 관측 범위 내"
    elif b1 > 0 and b2 < 0:
        pattern   = "inverted-U (부분)"
        supported = "false"
        verdict   = "H3 지지 불가: β₁>0 β₂<0 방향 맞으나 β₂ 미유의 또는 전환점 범위 외"
    elif b2 > 0:
        pattern   = "U-shaped"
        supported = "false"
        verdict   = "H3 지지 불가: β₂>0 (역U자형 아님)"
    else:
        pattern   = "기타"
        supported = "false"
        verdict   = "H3 지지 불가"

    return {
        "model":               model_lbl,
        "beta1_intensity":     f"{b1:.6f}",
        "beta2_intensity_sq":  f"{b2:.6f}",
        "beta2_p_value":       f"{p2:.6f}",
        "beta2_stars":         p_stars(p2),
        "turning_point":       f"{tp:.6f}" if not math.isnan(tp) else "undefined",
        "observed_min":        f"{obs_min:.6f}",
        "observed_max":        f"{obs_max:.6f}",
        "tp_in_range":         str(in_range).lower(),
        "pattern":             pattern,
        "H3_supported":        supported,
        "verdict":             verdict,
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== run_h3_fe_diagnostic ===\n")

    with open(INPUT, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input rows: {len(rows)}  |  {INPUT.name}")

    clean = []
    for r in rows:
        iv  = to_f(r["aggressive_humor_usage_intensity"])
        iv2 = to_f(r["aggressive_humor_usage_intensity_sq"])
        dv  = to_f(r["mean_log_total_engagement"])
        if any(math.isnan(x) for x in [iv, iv2, dv]):
            continue
        year  = r["period"][:4]
        month = r["period"][5:7]
        clean.append({
            "company": r["company_name"],
            "period":  r["period"],
            "year":    year,
            "month":   month,
            "iv":  iv,
            "iv2": iv2,
            "dv":  dv,
        })

    n_obs  = len(clean)
    firms  = sorted(set(r["company"] for r in clean))
    n_firms = len(firms)
    obs_min = min(r["iv"] for r in clean)
    obs_max = max(r["iv"] for r in clean)

    y   = np.array([r["dv"]  for r in clean])
    x1  = np.array([r["iv"]  for r in clean])
    x2  = np.array([r["iv2"] for r in clean])
    ones = np.ones(n_obs)

    firm_groups  = [r["company"] for r in clean]
    year_groups  = [r["year"]   for r in clean]
    month_groups = [r["month"]  for r in clean]

    REF_YEAR  = min(year_groups)   # earliest year in data
    REF_MONTH = "01"
    D_year,  year_cats  = make_dummies(year_groups,  ref=REF_YEAR)
    D_month, month_cats = make_dummies(month_groups, ref=REF_MONTH)
    D_firm,  firm_cats  = make_dummies(firm_groups,  ref=None)   # all 99 firms, no reference

    n_yd = len(year_cats)
    n_md = len(month_cats)
    n_fd = len(firm_cats)

    print(f"  Firms={n_firms}  Periods={len(set(r['period'] for r in clean))}  N={n_obs}")
    print(f"  Year dummies: {n_yd} (ref={REF_YEAR})  Month dummies: {n_md} (ref={REF_MONTH})")
    print(f"  Firm dummies: {n_fd} (no reference, no intercept in M4)")
    print(f"  Intensity range: [{obs_min:.6f}, {obs_max:.6f}]")

    reg_rows  = []
    diag_rows = []

    # ════════════════════════════════════════════════════════════════════════
    # M1: Simple OLS
    # ════════════════════════════════════════════════════════════════════════
    X1 = np.column_stack([ones, x1, x2])
    b1, v1, s1, t1, p1, n1, k1, r2_1, ra1, df1, _ = ols_fit(X1, y)
    fn1 = ["intercept", "aggressive_intensity", "aggressive_intensity_sq"]

    print(f"\nM1 Simple OLS: N={n1} k={k1} df={df1} R²={r2_1:.4f} adj-R²={ra1:.4f}")
    for i, fn in enumerate(fn1):
        print(f"  {fn:<28} β={b1[i]:+.4f}  SE={s1[i]:.4f}  t={t1[i]:+.4f}  {p_stars(p1[i])}")

    for i, fn in enumerate(fn1):
        reg_rows.append({
            "model": "M1_simple_ols", "variable": fn,
            "coefficient": f"{b1[i]:.6f}", "classical_ols_se": f"{s1[i]:.6f}",
            "t_stat": f"{t1[i]:.4f}", "p_value_two_sided": f"{p1[i]:.6f}",
            "stars": p_stars(p1[i]),
            "n_obs": n1, "r_squared": f"{r2_1:.6f}", "r_squared_adj": f"{ra1:.6f}",
            "df_resid": df1, "n_firms": n_firms,
            "fixed_effects": "none", "classifier_limitation": CLASSIFIER_NOTE,
        })
    diag_rows.append(h3_diag(float(b1[1]), float(b1[2]), float(p1[2]),
                              obs_min, obs_max, "M1_simple_ols"))

    # ════════════════════════════════════════════════════════════════════════
    # M2: Firm FE (FWL within-demeaning)
    # ════════════════════════════════════════════════════════════════════════
    mat = np.column_stack([y, x1, x2])
    mat_dm = demean_by_group(mat, firm_groups)
    y_dm  = mat_dm[:, 0]
    X2_dm = mat_dm[:, 1:]   # no intercept
    k_within = 2
    df2 = n_obs - n_firms - k_within
    ss_within = np.sum(y_dm ** 2)

    b2, v2, s2, t2, p2, n2, k2, _, _, _, resid2 = ols_fit(X2_dm, y_dm, df_override=df2)
    r2_2  = 1.0 - (resid2 @ resid2) / ss_within
    ra2   = 1.0 - (1.0 - r2_2) * (n_obs - 1) / df2
    fn2 = ["aggressive_intensity", "aggressive_intensity_sq"]

    print(f"\nM2 Firm FE (FWL): N={n_obs} firms={n_firms} k_within={k_within} df={df2} R²_within={r2_2:.4f}")
    for i, fn in enumerate(fn2):
        print(f"  {fn:<28} β={b2[i]:+.4f}  SE={s2[i]:.4f}  t={t2[i]:+.4f}  {p_stars(p2[i])}")

    for i, fn in enumerate(fn2):
        reg_rows.append({
            "model": "M2_firm_fe_fwl", "variable": fn,
            "coefficient": f"{b2[i]:.6f}", "classical_ols_se": f"{s2[i]:.6f}",
            "t_stat": f"{t2[i]:.4f}", "p_value_two_sided": f"{p2[i]:.6f}",
            "stars": p_stars(p2[i]),
            "n_obs": n_obs, "r_squared": f"{r2_2:.6f}", "r_squared_adj": f"{ra2:.6f}",
            "df_resid": df2, "n_firms": n_firms,
            "fixed_effects": "firm (FWL within-demeaning)", "classifier_limitation": CLASSIFIER_NOTE,
        })
    diag_rows.append(h3_diag(float(b2[0]), float(b2[1]), float(p2[1]),
                              obs_min, obs_max, "M2_firm_fe_fwl"))

    # ════════════════════════════════════════════════════════════════════════
    # M3: Time FE (year + month dummies, explicit)
    # ════════════════════════════════════════════════════════════════════════
    X3 = np.column_stack([ones, x1, x2, D_year, D_month])
    b3, v3, s3, t3, p3, n3, k3, r2_3, ra3, df3, _ = ols_fit(X3, y)
    fn3 = ["intercept", "aggressive_intensity", "aggressive_intensity_sq"]

    print(f"\nM3 Time FE (year+month): N={n3} k={k3} df={df3} R²={r2_3:.4f} adj-R²={ra3:.4f}")
    for i, fn in enumerate(fn3):
        print(f"  {fn:<28} β={b3[i]:+.4f}  SE={s3[i]:.4f}  t={t3[i]:+.4f}  {p_stars(p3[i])}")

    for i, fn in enumerate(fn3):
        reg_rows.append({
            "model": "M3_time_fe_year_month", "variable": fn,
            "coefficient": f"{b3[i]:.6f}", "classical_ols_se": f"{s3[i]:.6f}",
            "t_stat": f"{t3[i]:.4f}", "p_value_two_sided": f"{p3[i]:.6f}",
            "stars": p_stars(p3[i]),
            "n_obs": n3, "r_squared": f"{r2_3:.6f}", "r_squared_adj": f"{ra3:.6f}",
            "df_resid": df3, "n_firms": n_firms,
            "fixed_effects": f"year_dummies({n_yd} ref={REF_YEAR}) + month_dummies({n_md} ref={REF_MONTH})",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    diag_rows.append(h3_diag(float(b3[1]), float(b3[2]), float(p3[2]),
                              obs_min, obs_max, "M3_time_fe_year_month"))

    # ════════════════════════════════════════════════════════════════════════
    # M4: Firm + Time FE (all 99 firm dummies, no intercept, no reference)
    # ════════════════════════════════════════════════════════════════════════
    # No intercept: [intensity, intensity², D_firm(99), D_year(ref), D_month(ref)]
    X4 = np.column_stack([x1, x2, D_firm, D_year, D_month])
    b4, v4, s4, t4, p4, n4, k4, r2_4, ra4, df4, _ = ols_fit(X4, y)
    fn4 = ["aggressive_intensity", "aggressive_intensity_sq"]

    print(f"\nM4 Firm+Time FE (two-way): N={n4} firms={n_firms} k={k4} df={df4} R²={r2_4:.4f} adj-R²={ra4:.4f}")
    print(f"  firm_dummies={n_fd} (no reference, no intercept)"
          f"  year_dummies={n_yd} (ref={REF_YEAR})  month_dummies={n_md} (ref={REF_MONTH})")
    for i, fn in enumerate(fn4):
        print(f"  {fn:<28} β={b4[i]:+.4f}  SE={s4[i]:.4f}  t={t4[i]:+.4f}  {p_stars(p4[i])}")

    for i, fn in enumerate(fn4):
        reg_rows.append({
            "model": "M4_firm_year_month_fe", "variable": fn,
            "coefficient": f"{b4[i]:.6f}", "classical_ols_se": f"{s4[i]:.6f}",
            "t_stat": f"{t4[i]:.4f}", "p_value_two_sided": f"{p4[i]:.6f}",
            "stars": p_stars(p4[i]),
            "n_obs": n4, "r_squared": f"{r2_4:.6f}", "r_squared_adj": f"{ra4:.6f}",
            "df_resid": df4, "n_firms": n_firms,
            "fixed_effects": f"firm_dummies({n_fd} all, no reference, no intercept) + year_dummies({n_yd} ref={REF_YEAR}) + month_dummies({n_md} ref={REF_MONTH})",
            "classifier_limitation": CLASSIFIER_NOTE,
        })
    diag_rows.append(h3_diag(float(b4[0]), float(b4[1]), float(p4[1]),
                              obs_min, obs_max, "M4_firm_year_month_fe"))

    # ── Output ───────────────────────────────────────────────────────────────
    write_csv(OUT / "h3_fe_diagnostic_regression_results.csv",   reg_rows)
    write_csv(OUT / "h3_fe_diagnostic_h3_verdict.csv",           diag_rows)

    print("\n=== H3 FE DIAGNOSTIC SUMMARY ===")
    for d in diag_rows:
        tp_str = d["turning_point"]
        print(f"  [{d['model']}]")
        print(f"    β₁={d['beta1_intensity']}  β₂={d['beta2_intensity_sq']}{d['beta2_stars']}"
              f"  TP={tp_str}  in_range={d['tp_in_range']}")
        print(f"    pattern={d['pattern']}  H3_supported={d['H3_supported']}")
        print(f"    → {d['verdict']}")

    print("\n=== run_h3_fe_diagnostic COMPLETE ===")


if __name__ == "__main__":
    main()
