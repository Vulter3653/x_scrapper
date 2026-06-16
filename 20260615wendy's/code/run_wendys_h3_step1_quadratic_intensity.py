"""
Wendy's H3 Step 1: Quadratic Intensity Direct Test
- H3-pre: general humor_proportion_quarter_loo (quadratic)
- H3-main: aggressive_humor_proportion_quarter_loo (quadratic)
- No year_quarter FE, no quarter FE, no post format controls, no view_count
- Filter: quarter_total_posts >= 10
- Primary predictor: LOO quarter proportion only
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

BASE = Path("20260615wendy's")
DATA_DIR = BASE / "data"
RESULT_DIR = BASE / "result"
CODE_DIR = BASE / "code"

PRE_FILE = DATA_DIR / "wendys_humor_frequency_proportion_post_level_dataset.csv"
MAIN_FILE = DATA_DIR / "wendys_h3_aggressive_vs_other_intensity_dataset.csv"
OUT_DATA = DATA_DIR / "wendys_h3_step1_quadratic_intensity_dataset.csv"
OUT_PRE = RESULT_DIR / "wendys_h3_step1_general_humor_quadratic_results.csv"
OUT_MAIN = RESULT_DIR / "wendys_h3_step1_aggressive_humor_quadratic_results.csv"
OUT_DIAG = RESULT_DIR / "wendys_h3_step1_quadratic_diagnostics.csv"
OUT_SUMMARY = RESULT_DIR / "wendys_h3_step1_summary.md"

PRIMARY_DV = "log1p_engagement_total"
SUPPLEMENTAL_DVS = [
    "log1p_engagement_favorite_retweet",
    "log1p_favorite_count",
    "log1p_retweet_count",
    "log1p_reply_count",
    "log1p_quote_count",
    "log1p_bookmark_count",
]
ALL_DVS = [PRIMARY_DV] + SUPPLEMENTAL_DVS

FILTER_COL = "quarter_total_posts"
FILTER_THRESH = 10

PRE_PRED = "humor_proportion_quarter_loo"
PRE_PRED_SQ = "humor_proportion_quarter_loo_sq"
MAIN_PRED = "aggressive_humor_proportion_quarter_loo"
MAIN_PRED_SQ = "aggressive_humor_proportion_quarter_loo_sq"


def load_and_filter():
    df_pre_raw = pd.read_csv(PRE_FILE)
    df_main_raw = pd.read_csv(MAIN_FILE)

    print(f"[PRE raw] rows={len(df_pre_raw)}, cols={df_pre_raw.shape[1]}")
    print(f"[MAIN raw] rows={len(df_main_raw)}, cols={df_main_raw.shape[1]}")

    # Apply quarter_total_posts >= 10 filter on pre file
    df_pre_filt = df_pre_raw[df_pre_raw[FILTER_COL] >= FILTER_THRESH].copy()
    df_main_filt = df_main_raw[df_main_raw[FILTER_COL] >= FILTER_THRESH].copy()

    print(f"[PRE filtered] rows={len(df_pre_filt)}, unique quarters={df_pre_filt['year_quarter'].nunique()}")
    print(f"[MAIN filtered] rows={len(df_main_filt)}, unique quarters={df_main_filt['year_quarter'].nunique()}")

    # Add squared terms (never stored back to source files)
    df_pre_filt[PRE_PRED_SQ] = df_pre_filt[PRE_PRED] ** 2
    df_main_filt[MAIN_PRED_SQ] = df_main_filt[MAIN_PRED] ** 2

    # Merge on shared columns for output dataset
    shared_cols = [
        "id", "year_quarter", FILTER_COL,
        PRE_PRED, PRE_PRED_SQ,
        MAIN_PRED, MAIN_PRED_SQ,
        PRIMARY_DV,
    ] + SUPPLEMENTAL_DVS

    available_pre = [c for c in shared_cols if c in df_pre_filt.columns]
    available_main = [c for c in shared_cols if c in df_main_filt.columns]

    # Use main file as base (it has both pre and main predictors)
    df_out = df_main_filt[available_main].copy()
    # Add PRE_PRED_SQ from df_pre_filt if not already present
    if PRE_PRED not in df_out.columns:
        df_out = df_out.merge(df_pre_filt[["id", PRE_PRED, PRE_PRED_SQ]], on="id", how="left")
    else:
        df_out[PRE_PRED_SQ] = df_out[PRE_PRED] ** 2

    return df_pre_filt, df_main_filt, df_out


def check_missing(df, pred, pred_sq, label):
    n_missing = df[pred].isna().sum()
    n_missing_sq = df[pred_sq].isna().sum()
    print(f"[{label}] {pred} missing={n_missing}, {pred_sq} missing={n_missing_sq}")
    stats = df[pred].describe()
    stats_sq = df[pred_sq].describe()
    return {
        "predictor": pred,
        "n_total": len(df),
        "n_missing_predictor": int(n_missing),
        "n_missing_sq": int(n_missing_sq),
        "pred_min": float(stats["min"]),
        "pred_max": float(stats["max"]),
        "pred_mean": float(stats["mean"]),
        "pred_std": float(stats["std"]),
        "pred_sq_min": float(stats_sq["min"]),
        "pred_sq_max": float(stats_sq["max"]),
        "pred_sq_mean": float(stats_sq["mean"]),
        "pred_sq_std": float(stats_sq["std"]),
    }


def interpret(beta1, p1, beta2, p2, tp, x_min, x_max):
    tp_in_range = (x_min <= tp <= x_max) if (not np.isnan(tp)) else False
    if beta2 < 0 and p2 < 0.05 and beta1 > 0 and tp_in_range:
        return "supports_H3"
    elif beta2 < 0 and 0.05 <= p2 < 0.10 and beta1 > 0 and tp_in_range:
        return "weak_support"
    elif beta2 < 0 and beta1 > 0:
        return "directional_only"
    else:
        return "not_support"


def run_quadratic(df, pred, pred_sq, dv_list, h3_test_type):
    results = []
    df_clean_base = df[[pred, pred_sq] + dv_list].dropna(subset=[pred, pred_sq])
    n_full = len(df_clean_base)
    q_count = df["year_quarter"].nunique() if "year_quarter" in df.columns else np.nan

    x_min = float(df_clean_base[pred].min())
    x_max = float(df_clean_base[pred].max())
    x_mean = float(df_clean_base[pred].mean())
    x_std = float(df_clean_base[pred].std())

    for dv in dv_list:
        sub = df_clean_base[[pred, pred_sq, dv]].dropna()
        n = len(sub)
        X = sm.add_constant(sub[[pred, pred_sq]])
        y = sub[dv]

        try:
            model = sm.OLS(y, X).fit()
            beta1 = float(model.params[pred])
            p1 = float(model.pvalues[pred])
            beta2 = float(model.params[pred_sq])
            p2 = float(model.pvalues[pred_sq])
            r2 = float(model.rsquared)
            adj_r2 = float(model.rsquared_adj)
            aic = float(model.aic)
            bic = float(model.bic)
            rank_deficient = model.df_model < 2

            if beta2 != 0:
                tp = -beta1 / (2 * beta2)
            else:
                tp = np.nan

            tp_in_range = bool(x_min <= tp <= x_max) if not np.isnan(tp) else False
            flag = interpret(beta1, p1, beta2, p2, tp, x_min, x_max)

        except Exception as e:
            print(f"  ERROR {dv}: {e}")
            beta1 = p1 = beta2 = p2 = r2 = adj_r2 = aic = bic = tp = np.nan
            tp_in_range = False
            flag = "error"
            rank_deficient = False

        results.append({
            "h3_test_type": h3_test_type,
            "dv": dv,
            "predictor": pred,
            "squared_predictor": pred_sq,
            "n": n,
            "quarter_count": q_count,
            "predictor_min": x_min,
            "predictor_max": x_max,
            "predictor_mean": x_mean,
            "predictor_std": x_std,
            "beta_linear": round(beta1, 6) if not np.isnan(beta1) else np.nan,
            "p_linear": round(p1, 6) if not np.isnan(p1) else np.nan,
            "beta_quadratic": round(beta2, 6) if not np.isnan(beta2) else np.nan,
            "p_quadratic": round(p2, 6) if not np.isnan(p2) else np.nan,
            "turning_point": round(tp, 6) if not np.isnan(tp) else np.nan,
            "turning_point_in_range": tp_in_range,
            "r_squared": round(r2, 6) if not np.isnan(r2) else np.nan,
            "adj_r_squared": round(adj_r2, 6) if not np.isnan(adj_r2) else np.nan,
            "aic": round(aic, 4) if not np.isnan(aic) else np.nan,
            "bic": round(bic, 4) if not np.isnan(bic) else np.nan,
            "interpretation_flag": flag,
        })

        tp_str = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
        print(
            f"  [{h3_test_type}] {dv}: β1={beta1:.4f}(p={p1:.4f}), "
            f"β2={beta2:.4f}(p={p2:.4f}), tp={tp_str}, flag={flag}"
        )

    return pd.DataFrame(results)


def build_diagnostics(diag_pre, diag_main, df_pre, df_main):
    rows = []

    for df, label, pred, pred_sq, filter_thresh in [
        (df_pre, "H3-pre (general humor)", PRE_PRED, PRE_PRED_SQ, FILTER_THRESH),
        (df_main, "H3-main (aggressive humor)", MAIN_PRED, MAIN_PRED_SQ, FILTER_THRESH),
    ]:
        src_file = "wendys_humor_frequency_proportion_post_level_dataset.csv" if "general" in label \
            else "wendys_h3_aggressive_vs_other_intensity_dataset.csv"
        rows.append({
            "check": "source_file",
            "label": label,
            "value": src_file,
        })
        rows.append({"check": "row_count", "label": label, "value": str(len(df))})
        rows.append({"check": "col_count", "label": label, "value": str(df.shape[1])})
        rows.append({"check": "unique_year_quarter", "label": label,
                     "value": str(df["year_quarter"].nunique()) if "year_quarter" in df.columns else "n/a"})
        rows.append({"check": "quarter_total_posts_filter", "label": label,
                     "value": f">= {filter_thresh} applied"})
        rows.append({"check": "predictor_missing", "label": label,
                     "value": str(df[pred].isna().sum())})
        rows.append({"check": "predictor_sq_missing", "label": label,
                     "value": str(df[pred_sq].isna().sum()) if pred_sq in df.columns else "col_not_found"})
        rows.append({"check": "predictor_min", "label": label,
                     "value": str(round(df[pred].min(), 6))})
        rows.append({"check": "predictor_max", "label": label,
                     "value": str(round(df[pred].max(), 6))})
        rows.append({"check": "predictor_mean", "label": label,
                     "value": str(round(df[pred].mean(), 6))})
        rows.append({"check": "predictor_std", "label": label,
                     "value": str(round(df[pred].std(), 6))})
        rows.append({"check": "year_quarter_FE_used", "label": label, "value": "False"})
        rows.append({"check": "quarter_FE_used", "label": label, "value": "False"})
        rows.append({"check": "post_format_controls_used", "label": label, "value": "False"})
        rows.append({"check": "view_count_used", "label": label, "value": "False"})
        rows.append({"check": "H1_analysis_performed", "label": label, "value": "False"})
        rows.append({"check": "H2_analysis_performed", "label": label, "value": "False"})
        rows.append({"check": "new_humor_classifier_trained", "label": label, "value": "False"})

    return pd.DataFrame(rows)


def build_summary(res_pre, res_main, df_pre, df_main):
    pri_pre = res_pre[res_pre["dv"] == PRIMARY_DV].iloc[0]
    pri_main = res_main[res_main["dv"] == PRIMARY_DV].iloc[0]

    def fmt_row(row):
        return (
            f"β1={row['beta_linear']:.4f} (p={row['p_linear']:.4f}), "
            f"β2={row['beta_quadratic']:.4f} (p={row['p_quadratic']:.4f}), "
            f"turning_point={row['turning_point']:.4f} (in_range={row['turning_point_in_range']}), "
            f"판정={row['interpretation_flag']}"
        )

    supp_pre_lines = []
    supp_main_lines = []
    for dv in SUPPLEMENTAL_DVS:
        r_pre = res_pre[res_pre["dv"] == dv].iloc[0]
        r_main = res_main[res_main["dv"] == dv].iloc[0]
        supp_pre_lines.append(f"  - {dv}: {fmt_row(r_pre)}")
        supp_main_lines.append(f"  - {dv}: {fmt_row(r_main)}")

    pre_q = df_pre["year_quarter"].nunique()
    main_q = df_main["year_quarter"].nunique()
    pre_n = int(pri_pre["n"])
    main_n = int(pri_main["n"])

    lines = [
        "# Wendy's H3 Step 1 Quadratic Intensity Direct Test — 분석 요약",
        "",
        "## 1. 분석 목적",
        "Wendy's H3 분석의 1단계로, 전체 데이터 기반 model-based intensity 변수를 사용하여 "
        "humor usage intensity와 post-level engagement 간 역 U자형 관계가 존재하는지 확인한다.",
        "",
        "## 2. H3 가설",
        "H3: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다. "
        "즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 engagement가 감소할 것이다.",
        "",
        "## 3. H3-pre와 H3-main 구분",
        "- **H3-pre**: general humor usage intensity (humor_proportion_quarter_loo)의 역 U자형 관계",
        "- **H3-main**: aggressive humor usage intensity (aggressive_humor_proportion_quarter_loo)의 역 U자형 관계",
        "",
        "## 4. 사용한 파일",
        f"- H3-pre: `{PRE_FILE.name}`",
        f"- H3-main: `{MAIN_FILE.name}`",
        "",
        "## 5. 원본 posts.json 변경 없음 확인",
        "data/wendys/posts.json 원본 파일은 수정하지 않았다. "
        "분석은 기존 파생 파일만 사용한다.",
        "",
        "## 6. 새 통제변수 생성 없음 확인",
        "이번 분석에서 새로운 통제변수는 생성하지 않았다. "
        "quadratic term은 H3 가설 검정을 위한 필수 모형항으로만 사용하였다.",
        "",
        "## 7. Quadratic term 설명",
        "H3 검정에는 역 U자형 관계를 포착하기 위해 quadratic term이 필요하다. "
        "이는 새로운 통제변수가 아니라 H3 가설 검정을 위한 필수 모형항이다. "
        "squared term은 회귀식 내부의 분석용 항으로만 생성하였으며, "
        "산출용 dataset에 `_sq` suffix로 명확히 표시하였다.",
        "",
        "## 8. 분석 표본 구성",
        f"- H3-pre base 파일: {PRE_FILE.name} (전체 n=1330)",
        f"- H3-main base 파일: {MAIN_FILE.name} (전체 n=978)",
        "",
        "## 9. quarter_total_posts >= 10 필터 적용 결과",
        f"- H3-pre filtered: n={len(df_pre)}, unique year_quarter={pre_q}",
        f"- H3-main filtered: n={len(df_main)}, unique year_quarter={main_q}",
        f"- Primary DV 분석 표본 (결측 제외 후): H3-pre n={pre_n}, H3-main n={main_n}",
        "",
        "## 10. 사용한 Predictor 설명",
        f"- H3-pre primary predictor: `{PRE_PRED}` (LOO quarter-level general humor proportion)",
        f"- H3-main primary predictor: `{MAIN_PRED}` (LOO quarter-level aggressive humor proportion)",
        "- LOO 변수는 focal post가 자기 자신이 속한 quarter-level proportion에 기계적으로 반영되는 "
        "문제를 줄이기 위한 변수이다.",
        "- non-LOO proportion 변수, month-level proportion 변수, frequency count 변수는 사용하지 않았다.",
        "",
        "## 11. H3-pre: General Humor Proportion Quadratic 결과",
        f"**Primary DV ({PRIMARY_DV})**:",
        f"  {fmt_row(pri_pre)}",
        "",
        "**Supplemental DVs**:",
        *supp_pre_lines,
        "",
        "## 12. H3-main: Aggressive Humor Proportion Quadratic 결과",
        f"**Primary DV ({PRIMARY_DV})**:",
        f"  {fmt_row(pri_main)}",
        "",
        "**Supplemental DVs**:",
        *supp_main_lines,
        "",
        "## 13. Primary DV 기준 결과 요약",
        f"- H3-pre ({PRIMARY_DV}): {fmt_row(pri_pre)}",
        f"- H3-main ({PRIMARY_DV}): {fmt_row(pri_main)}",
        "",
        "## 14. Supplemental DV 기준 결과 요약",
        "H3-pre supplemental DVs:",
        *[f"  - {dv}: {res_pre[res_pre['dv']==dv].iloc[0]['interpretation_flag']}" for dv in SUPPLEMENTAL_DVS],
        "",
        "H3-main supplemental DVs:",
        *[f"  - {dv}: {res_main[res_main['dv']==dv].iloc[0]['interpretation_flag']}" for dv in SUPPLEMENTAL_DVS],
        "",
        "## 15. Turning Point 및 관측 범위 내 위치 여부",
        f"- H3-pre predictor 관측 범위: [{df_pre[PRE_PRED].min():.4f}, {df_pre[PRE_PRED].max():.4f}]",
        f"  Primary DV turning point: {pri_pre['turning_point']:.4f}, "
        f"  in_range: {pri_pre['turning_point_in_range']}",
        f"- H3-main predictor 관측 범위: [{df_main[MAIN_PRED].min():.4f}, {df_main[MAIN_PRED].max():.4f}]",
        f"  Primary DV turning point: {pri_main['turning_point']:.4f}, "
        f"  in_range: {pri_main['turning_point_in_range']}",
        "",
        "## 16. H3-pre 판정",
        f"Primary DV 기준: **{pri_pre['interpretation_flag']}**",
        "",
        "## 17. H3-main 판정",
        f"Primary DV 기준: **{pri_main['interpretation_flag']}**",
        "",
        "## 18. 인과관계 주의사항",
        "본 분석은 관측적 연관성(observational association) 분석이며, "
        "인과관계(causal relationship)를 의미하지 않는다.",
        "",
        "## 19. H1/H2 분석 미수행 확인",
        "H1·H2 분석은 이번 작업에서 수행하지 않았다. "
        "새로운 유머 분류 모델도 학습하지 않았다.",
        "",
        "## 20. 다음 단계",
        "다음 단계에서 시간 변수(year FE 등) 또는 post format controls를 추가할 수 있으나, "
        "사용자 승인 후 진행한다.",
    ]
    return "\n".join(lines)


def main():
    print("=== Wendy's H3 Step 1: Quadratic Intensity Direct Test ===")

    df_pre, df_main, df_out = load_and_filter()

    # Diagnostics checks
    diag_pre = check_missing(df_pre, PRE_PRED, PRE_PRED_SQ, "H3-pre")
    diag_main = check_missing(df_main, MAIN_PRED, MAIN_PRED_SQ, "H3-main")

    print("\n--- Running H3-pre quadratic OLS ---")
    res_pre = run_quadratic(df_pre, PRE_PRED, PRE_PRED_SQ, ALL_DVS, "H3-pre")

    print("\n--- Running H3-main quadratic OLS ---")
    res_main = run_quadratic(df_main, MAIN_PRED, MAIN_PRED_SQ, ALL_DVS, "H3-main")

    # Save output dataset
    out_cols = ["id", "year_quarter", FILTER_COL]
    for col in [PRE_PRED, PRE_PRED_SQ, MAIN_PRED, MAIN_PRED_SQ] + ALL_DVS:
        if col in df_out.columns:
            out_cols.append(col)
    df_out[out_cols].to_csv(OUT_DATA, index=False)
    print(f"\nSaved output dataset: {OUT_DATA} (n={len(df_out)})")

    # Save results
    res_pre.to_csv(OUT_PRE, index=False)
    res_main.to_csv(OUT_MAIN, index=False)
    print(f"Saved H3-pre results: {OUT_PRE}")
    print(f"Saved H3-main results: {OUT_MAIN}")

    # Save diagnostics
    diag_df = build_diagnostics(diag_pre, diag_main, df_pre, df_main)
    diag_df.to_csv(OUT_DIAG, index=False)
    print(f"Saved diagnostics: {OUT_DIAG}")

    # Save summary
    summary_text = build_summary(res_pre, res_main, df_pre, df_main)
    OUT_SUMMARY.write_text(summary_text, encoding="utf-8")
    print(f"Saved summary: {OUT_SUMMARY}")

    # Final checklist print
    print("\n=== Checklist ===")
    print("posts.json modified: False")
    print("H1/H2 performed: False")
    print("New humor classifier trained: False")
    print("year_quarter FE used: False")
    print("quarter FE used: False")
    print("post format controls used: False")
    print("view_count used: False")
    print(f"H3-pre filter applied (quarter_total_posts>={FILTER_THRESH}): True")
    print(f"H3-main filter applied (quarter_total_posts>={FILTER_THRESH}): True")

    pri_pre = res_pre[res_pre["dv"] == PRIMARY_DV].iloc[0]
    pri_main = res_main[res_main["dv"] == PRIMARY_DV].iloc[0]
    print(f"\nH3-pre primary result: β1={pri_pre['beta_linear']:.4f}(p={pri_pre['p_linear']:.4f}), "
          f"β2={pri_pre['beta_quadratic']:.4f}(p={pri_pre['p_quadratic']:.4f}), "
          f"tp={pri_pre['turning_point']:.4f}, flag={pri_pre['interpretation_flag']}")
    print(f"H3-main primary result: β1={pri_main['beta_linear']:.4f}(p={pri_main['p_linear']:.4f}), "
          f"β2={pri_main['beta_quadratic']:.4f}(p={pri_main['p_quadratic']:.4f}), "
          f"tp={pri_main['turning_point']:.4f}, flag={pri_main['interpretation_flag']}")


if __name__ == "__main__":
    main()
