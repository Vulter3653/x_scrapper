"""
Wendy's H3 Step 2: Proportion-Based Quadratic Test with Time Variables
- M0~M7: LOO quarter proportion + squared term, with created_year/month/hour FE combinations
- NO year_quarter FE, NO quarter FE, NO post format controls, NO view_count, NO frequency count
- Filter: quarter_total_posts >= 10
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

BASE = Path("20260615wendy's")
DATA_DIR = BASE / "data"
RESULT_DIR = BASE / "result"

PRE_FILE = DATA_DIR / "wendys_humor_frequency_proportion_post_level_dataset.csv"
MAIN_FILE = DATA_DIR / "wendys_h3_aggressive_vs_other_intensity_dataset.csv"
OUT_DATA = DATA_DIR / "wendys_h3_step2_proportion_time_variables_dataset.csv"
OUT_PRE = RESULT_DIR / "wendys_h3_step2_general_humor_time_results.csv"
OUT_MAIN = RESULT_DIR / "wendys_h3_step2_aggressive_humor_time_results.csv"
OUT_DIAG = RESULT_DIR / "wendys_h3_step2_time_diagnostics.csv"
OUT_SUMMARY = RESULT_DIR / "wendys_h3_step2_summary.md"

FILTER_COL = "quarter_total_posts"
FILTER_THRESH = 10

PRE_PRED = "humor_proportion_quarter_loo"
PRE_PRED_SQ = "humor_proportion_quarter_loo_sq"
MAIN_PRED = "aggressive_humor_proportion_quarter_loo"
MAIN_PRED_SQ = "aggressive_humor_proportion_quarter_loo_sq"

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

TIME_VARS = ["created_year", "created_month", "created_hour"]

MODEL_SPECS = {
    "M0": [],
    "M1": ["created_year"],
    "M2": ["created_month"],
    "M3": ["created_hour"],
    "M4": ["created_year", "created_month"],
    "M5": ["created_year", "created_hour"],
    "M6": ["created_month", "created_hour"],
    "M7": ["created_year", "created_month", "created_hour"],
}


def load_and_filter():
    df_pre_raw = pd.read_csv(PRE_FILE)
    df_main_raw = pd.read_csv(MAIN_FILE)

    print(f"[PRE raw]  rows={len(df_pre_raw)}, cols={df_pre_raw.shape[1]}")
    print(f"[MAIN raw] rows={len(df_main_raw)}, cols={df_main_raw.shape[1]}")

    df_pre = df_pre_raw[df_pre_raw[FILTER_COL] >= FILTER_THRESH].copy()
    df_main = df_main_raw[df_main_raw[FILTER_COL] >= FILTER_THRESH].copy()

    print(f"[PRE  filtered] n={len(df_pre)}, unique year_quarter={df_pre['year_quarter'].nunique()}")
    print(f"[MAIN filtered] n={len(df_main)}, unique year_quarter={df_main['year_quarter'].nunique()}")

    df_pre[PRE_PRED_SQ] = df_pre[PRE_PRED] ** 2
    df_main[MAIN_PRED_SQ] = df_main[MAIN_PRED] ** 2

    return df_pre, df_main


def interpret(beta1, p1, beta2, p2, tp, x_min, x_max):
    if np.isnan(beta1) or np.isnan(beta2):
        return "error"
    tp_in_range = (x_min <= tp <= x_max) if (not np.isnan(tp)) else False
    if beta2 < 0 and p2 < 0.05 and beta1 > 0 and tp_in_range:
        return "supports_H3"
    elif beta2 < 0 and 0.05 <= p2 < 0.10 and beta1 > 0 and tp_in_range:
        return "weak_support"
    elif beta2 < 0 and beta1 > 0:
        return "directional_only"
    else:
        return "not_support"


def make_dummies(df, time_cols):
    """Return dummy-encoded columns (float) with drop_first=True for each time var."""
    parts = []
    for col in time_cols:
        dummies = pd.get_dummies(df[col].astype(str), prefix=col, drop_first=True).astype(float)
        parts.append(dummies)
    if parts:
        return pd.concat(parts, axis=1)
    return pd.DataFrame(index=df.index)


def run_models(df, pred, pred_sq, dv_list, h3_test_type):
    x_vals = df[pred].dropna()
    x_min = float(x_vals.min())
    x_max = float(x_vals.max())
    x_mean = float(x_vals.mean())
    x_std = float(x_vals.std())
    q_count = df["year_quarter"].nunique()

    results = []

    for model_name, time_cols in MODEL_SPECS.items():
        time_label = "+".join(time_cols) if time_cols else "none"

        # Build design matrix columns for this model
        base_cols = [pred, pred_sq] + time_cols
        needed = base_cols + dv_list

        # Subset to needed columns and drop NAs on pred/pred_sq/time_cols
        available = [c for c in needed if c in df.columns]
        df_sub = df[available].copy()

        # Build dummy variables for time FEs
        if time_cols:
            dummies = make_dummies(df_sub, time_cols)
            df_sub = pd.concat([df_sub, dummies], axis=1)
            dummy_cols = list(dummies.columns)
        else:
            dummy_cols = []

        feature_cols = [pred, pred_sq] + dummy_cols
        drop_subset = [pred, pred_sq] + time_cols
        df_sub = df_sub.dropna(subset=drop_subset)
        n_base = len(df_sub)

        for dv in dv_list:
            if dv not in df_sub.columns:
                continue
            sub = df_sub[[dv] + feature_cols].dropna(subset=[dv])
            n = len(sub)

            X = sm.add_constant(sub[feature_cols])
            y = sub[dv]

            try:
                model = sm.OLS(y, X).fit()
                beta1 = float(model.params.get(pred, np.nan))
                p1 = float(model.pvalues.get(pred, np.nan))
                beta2 = float(model.params.get(pred_sq, np.nan))
                p2 = float(model.pvalues.get(pred_sq, np.nan))
                r2 = float(model.rsquared)
                adj_r2 = float(model.rsquared_adj)
                aic = float(model.aic)
                bic = float(model.bic)
                rank_deficient = bool(model.df_model < len(feature_cols))

                if beta2 != 0 and not np.isnan(beta2):
                    tp = -beta1 / (2 * beta2)
                else:
                    tp = np.nan

                tp_in_range = bool(x_min <= tp <= x_max) if not np.isnan(tp) else False
                flag = interpret(beta1, p1, beta2, p2, tp, x_min, x_max)

                if rank_deficient:
                    print(f"  WARNING rank deficiency: {h3_test_type} {model_name} {dv}")

            except Exception as e:
                print(f"  ERROR {h3_test_type} {model_name} {dv}: {e}")
                beta1 = p1 = beta2 = p2 = r2 = adj_r2 = aic = bic = tp = np.nan
                tp_in_range = False
                flag = "error"

            tp_str = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
            print(
                f"  [{h3_test_type}|{model_name}|{dv[:30]}] "
                f"β1={beta1:.4f}(p={p1:.4f}), β2={beta2:.4f}(p={p2:.4f}), "
                f"tp={tp_str}, flag={flag}"
            )

            results.append({
                "h3_test_type": h3_test_type,
                "model_name": model_name,
                "dv": dv,
                "predictor": pred,
                "squared_predictor": pred_sq,
                "n": n,
                "quarter_count": q_count,
                "predictor_min": round(x_min, 6),
                "predictor_max": round(x_max, 6),
                "predictor_mean": round(x_mean, 6),
                "predictor_std": round(x_std, 6),
                "beta_linear": round(beta1, 6) if not np.isnan(beta1) else np.nan,
                "p_linear": round(p1, 6) if not np.isnan(p1) else np.nan,
                "beta_quadratic": round(beta2, 6) if not np.isnan(beta2) else np.nan,
                "p_quadratic": round(p2, 6) if not np.isnan(p2) else np.nan,
                "turning_point": round(tp, 6) if not np.isnan(tp) else np.nan,
                "turning_point_in_range": tp_in_range,
                "included_time_variables": time_label,
                "number_of_time_variables": len(time_cols),
                "r_squared": round(r2, 6) if not np.isnan(r2) else np.nan,
                "adj_r_squared": round(adj_r2, 6) if not np.isnan(adj_r2) else np.nan,
                "aic": round(aic, 4) if not np.isnan(aic) else np.nan,
                "bic": round(bic, 4) if not np.isnan(bic) else np.nan,
                "interpretation_flag": flag,
            })

    return pd.DataFrame(results)


def build_diagnostics(df_pre, df_main):
    rows = []

    for df, label, pred, pred_sq, src in [
        (df_pre,  "H3-pre (general humor)",    PRE_PRED,  PRE_PRED_SQ,  PRE_FILE.name),
        (df_main, "H3-main (aggressive humor)", MAIN_PRED, MAIN_PRED_SQ, MAIN_FILE.name),
    ]:
        checks = {
            "source_file": src,
            "row_count_after_filter": str(len(df)),
            "col_count": str(df.shape[1]),
            "unique_year_quarter": str(df["year_quarter"].nunique()),
            "quarter_total_posts_filter": f">= {FILTER_THRESH} applied",
            "predictor_missing": str(df[pred].isna().sum()),
            "predictor_sq_missing": str(df[pred_sq].isna().sum() if pred_sq in df.columns else "col_missing"),
            "predictor_min": str(round(df[pred].min(), 6)),
            "predictor_max": str(round(df[pred].max(), 6)),
            "predictor_mean": str(round(df[pred].mean(), 6)),
            "predictor_std": str(round(df[pred].std(), 6)),
            "created_year_unique": str(sorted(df["created_year"].dropna().unique().tolist())),
            "created_month_unique": str(sorted(df["created_month"].dropna().unique().tolist())),
            "created_hour_unique": str(sorted(df["created_hour"].dropna().unique().tolist())),
            "year_quarter_FE_used": "False",
            "quarter_FE_used": "False",
            "post_format_controls_used": "False",
            "view_count_used": "False",
            "frequency_count_used": "False",
            "H1_performed": "False",
            "H2_performed": "False",
            "new_humor_classifier": "False",
        }
        for check, value in checks.items():
            rows.append({"label": label, "check": check, "value": value})

    return pd.DataFrame(rows)


def build_summary(res_pre, res_main, df_pre, df_main):
    def fmt(row):
        tp = row["turning_point"]
        tp_str = f"{tp:.4f}" if not (isinstance(tp, float) and np.isnan(tp)) else "NaN"
        return (
            f"β1={row['beta_linear']:.4f}(p={row['p_linear']:.4f}), "
            f"β2={row['beta_quadratic']:.4f}(p={row['p_quadratic']:.4f}), "
            f"tp={tp_str}(in_range={row['turning_point_in_range']}), "
            f"판정={row['interpretation_flag']}"
        )

    pre_q = df_pre["year_quarter"].nunique()
    main_q = df_main["year_quarter"].nunique()

    # Primary DV rows per model
    pri_pre = res_pre[res_pre["dv"] == PRIMARY_DV].set_index("model_name")
    pri_main = res_main[res_main["dv"] == PRIMARY_DV].set_index("model_name")

    pri_pre_m0 = pri_pre.loc["M0"]
    pri_pre_m7 = pri_pre.loc["M7"]
    pri_main_m0 = pri_main.loc["M0"]
    pri_main_m7 = pri_main.loc["M7"]

    # Supplemental summary per DV (M7)
    def supp_summary(res, model="M7"):
        lines = []
        for dv in SUPPLEMENTAL_DVS:
            row = res[(res["dv"] == dv) & (res["model_name"] == model)]
            if len(row) == 0:
                lines.append(f"  - {dv}: N/A")
            else:
                lines.append(f"  - {dv}: {fmt(row.iloc[0])}")
        return lines

    # Per-model primary DV table
    def model_table(pri_df, label):
        lines = [f"\n### {label} - Primary DV ({PRIMARY_DV}) 모형별 결과"]
        for m in MODEL_SPECS:
            if m in pri_df.index:
                row = pri_df.loc[m]
                tv = row["included_time_variables"]
                lines.append(f"- {m} ({tv}): {fmt(row)}")
        return lines

    lines = [
        "# Wendy's H3 Step 2: Proportion-Based Quadratic Test with Time Variables — 분석 요약",
        "",
        "## 1. 분석 목적",
        "Wendy's H3 분석의 2단계로, Step 1에서 사용한 비중 기반 LOO proportion quadratic model에 "
        "시간 변수(created_year, created_month, created_hour)를 추가하여, "
        "H3의 역 U자형 관계가 시간 효과를 고려한 뒤에도 유지되는지 확인한다.",
        "",
        "## 2. H3 가설",
        "H3: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다. "
        "즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 감소할 것이다.",
        "",
        "## 3. H3-pre와 H3-main 구분",
        "- **H3-pre**: general humor usage intensity (humor_proportion_quarter_loo)의 역 U자형 관계",
        "- **H3-main**: aggressive humor usage intensity (aggressive_humor_proportion_quarter_loo)의 역 U자형 관계",
        "",
        "## 4. 사용한 파일",
        f"- H3-pre: `{PRE_FILE.name}`",
        f"- H3-main: `{MAIN_FILE.name}`",
        "- 참조: Step 1 결과 파일 (비교용)",
        "",
        "## 5. 원본 posts.json 변경 없음 확인",
        "data/wendys/posts.json 원본 파일은 수정하지 않았다.",
        "",
        "## 6. 새 통제변수 생성 없음 확인",
        "이번 분석에서 새로운 통제변수는 생성하지 않았다. "
        "quadratic term 및 시간 FE dummy는 분석용 모형항으로만 사용하였다.",
        "",
        "## 7. Frequency Count 변수 미사용 확인",
        "포스트 수 기반 frequency count 변수는 사용하지 않았다. "
        "비중 기반 LOO proportion 변수만 H3 predictor로 사용하였다.",
        "",
        "## 8. Quadratic Term 설명",
        "squared term은 H3 역 U자형 가설 검정을 위한 필수 모형항이며, "
        "산출용 dataset에 `_sq` suffix로 명확히 표시하였다.",
        "",
        "## 9. 분석 표본 구성",
        f"- H3-pre base 파일: {PRE_FILE.name} (전체 n=978 before filter)",
        f"- H3-main base 파일: {MAIN_FILE.name} (전체 n=978 before filter)",
        "",
        "## 10. quarter_total_posts >= 10 필터 적용 결과",
        f"- H3-pre filtered: n={len(df_pre)}, unique year_quarter={pre_q}",
        f"- H3-main filtered: n={len(df_main)}, unique year_quarter={main_q}",
        "",
        "## 11. 사용한 Predictor 설명",
        f"- H3-pre: `{PRE_PRED}` (LOO quarter-level general humor proportion)",
        f"- H3-main: `{MAIN_PRED}` (LOO quarter-level aggressive humor proportion)",
        "- non-LOO proportion, month-level proportion, frequency count 변수는 사용하지 않았다.",
        "",
        "## 12. 사용한 시간 변수 조합",
        "- M0: 없음 (baseline quadratic only)",
        "- M1: created_year FE",
        "- M2: created_month FE",
        "- M3: created_hour FE",
        "- M4: created_year + created_month FE",
        "- M5: created_year + created_hour FE",
        "- M6: created_month + created_hour FE",
        "- M7: created_year + created_month + created_hour FE",
        "- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.",
        "",
        "## 13. H3-pre: General Humor Proportion Quadratic 결과",
        *model_table(pri_pre, "H3-pre"),
        "",
        "**Supplemental DVs (M7 기준)**:",
        *supp_summary(res_pre, "M7"),
        "",
        "## 14. H3-main: Aggressive Humor Proportion Quadratic 결과",
        *model_table(pri_main, "H3-main"),
        "",
        "**Supplemental DVs (M7 기준)**:",
        *supp_summary(res_main, "M7"),
        "",
        "## 15. Primary DV 기준 시간 변수 조합별 결과 요약",
        f"H3-pre M0 (baseline): {fmt(pri_pre_m0)}",
        f"H3-pre M7 (full time): {fmt(pri_pre_m7)}",
        f"H3-main M0 (baseline): {fmt(pri_main_m0)}",
        f"H3-main M7 (full time): {fmt(pri_main_m7)}",
        "",
        "## 16. Supplemental DV 기준 결과 요약",
        "H3-pre (M7):",
        *[f"  - {dv}: {res_pre[(res_pre['dv']==dv)&(res_pre['model_name']=='M7')].iloc[0]['interpretation_flag']}"
          for dv in SUPPLEMENTAL_DVS
          if len(res_pre[(res_pre['dv']==dv)&(res_pre['model_name']=='M7')]) > 0],
        "",
        "H3-main (M7):",
        *[f"  - {dv}: {res_main[(res_main['dv']==dv)&(res_main['model_name']=='M7')].iloc[0]['interpretation_flag']}"
          for dv in SUPPLEMENTAL_DVS
          if len(res_main[(res_main['dv']==dv)&(res_main['model_name']=='M7')]) > 0],
        "",
        "## 17. Turning Point 및 관측 범위 내 위치 여부",
        f"- H3-pre predictor 관측 범위: [{df_pre[PRE_PRED].min():.4f}, {df_pre[PRE_PRED].max():.4f}]",
        f"  M0 tp={pri_pre_m0['turning_point']:.4f}, in_range={pri_pre_m0['turning_point_in_range']}",
        f"  M7 tp={pri_pre_m7['turning_point']:.4f}, in_range={pri_pre_m7['turning_point_in_range']}",
        f"- H3-main predictor 관측 범위: [{df_main[MAIN_PRED].min():.4f}, {df_main[MAIN_PRED].max():.4f}]",
        f"  M0 tp={pri_main_m0['turning_point']:.4f}, in_range={pri_main_m0['turning_point_in_range']}",
        f"  M7 tp={pri_main_m7['turning_point']:.4f}, in_range={pri_main_m7['turning_point_in_range']}",
        "",
        "## 18. H3-pre 판정",
        f"- M0 (baseline): **{pri_pre_m0['interpretation_flag']}**",
        f"- M7 (full time FE): **{pri_pre_m7['interpretation_flag']}**",
        "",
        "## 19. H3-main 판정",
        f"- M0 (baseline): **{pri_main_m0['interpretation_flag']}**",
        f"- M7 (full time FE): **{pri_main_m7['interpretation_flag']}**",
        "",
        "## 20. 인과관계 주의사항",
        "본 분석은 관측적 연관성(observational association) 분석이며, "
        "인과관계(causal relationship)를 의미하지 않는다.",
        "",
        "## 21. H1/H2 분석 미수행 확인",
        "H1·H2 분석은 이번 작업에서 수행하지 않았다. "
        "새로운 유머 분류 모델도 학습하지 않았다.",
        "",
        "## 22. 다음 단계",
        "다음 단계에서 post format controls를 추가할 수 있으나, 사용자 승인 후 진행한다.",
    ]

    return "\n".join(lines)


def save_output_dataset(df_pre, df_main):
    keep_pre = ["id", "year_quarter", FILTER_COL, PRE_PRED, PRE_PRED_SQ] + TIME_VARS + ALL_DVS
    keep_main = ["id", "year_quarter", FILTER_COL, MAIN_PRED, MAIN_PRED_SQ] + TIME_VARS + ALL_DVS

    cols_pre = [c for c in keep_pre if c in df_pre.columns]
    cols_main = [c for c in keep_main if c in df_main.columns]

    df_out = df_main[cols_main].copy()
    if PRE_PRED not in df_out.columns:
        df_out = df_out.merge(df_pre[["id", PRE_PRED, PRE_PRED_SQ]], on="id", how="left")
    else:
        df_out[PRE_PRED_SQ] = df_out[PRE_PRED] ** 2

    df_out.to_csv(OUT_DATA, index=False)
    print(f"Saved output dataset: {OUT_DATA} (n={len(df_out)})")


def main():
    print("=== Wendy's H3 Step 2: Proportion Quadratic + Time Variables ===\n")

    df_pre, df_main = load_and_filter()

    # Predictor stats
    for df, pred, label in [(df_pre, PRE_PRED, "H3-pre"), (df_main, MAIN_PRED, "H3-main")]:
        s = df[pred].describe()
        print(f"[{label}] {pred}: min={s['min']:.4f}, max={s['max']:.4f}, "
              f"mean={s['mean']:.4f}, std={s['std']:.4f}, missing={df[pred].isna().sum()}")

    print("\n--- H3-pre: M0~M7 ---")
    res_pre = run_models(df_pre, PRE_PRED, PRE_PRED_SQ, ALL_DVS, "H3-pre")

    print("\n--- H3-main: M0~M7 ---")
    res_main = run_models(df_main, MAIN_PRED, MAIN_PRED_SQ, ALL_DVS, "H3-main")

    save_output_dataset(df_pre, df_main)

    res_pre.to_csv(OUT_PRE, index=False)
    res_main.to_csv(OUT_MAIN, index=False)
    print(f"Saved H3-pre results:  {OUT_PRE}  ({len(res_pre)} rows)")
    print(f"Saved H3-main results: {OUT_MAIN}  ({len(res_main)} rows)")

    diag_df = build_diagnostics(df_pre, df_main)
    diag_df.to_csv(OUT_DIAG, index=False)
    print(f"Saved diagnostics: {OUT_DIAG}")

    summary = build_summary(res_pre, res_main, df_pre, df_main)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")
    print(f"Saved summary: {OUT_SUMMARY}")

    # Final checklist
    print("\n=== Checklist ===")
    for item, val in [
        ("posts.json modified", "False"),
        ("H1/H2 performed", "False"),
        ("new humor classifier", "False"),
        ("frequency count used", "False"),
        ("post format controls", "False"),
        ("year_quarter FE", "False"),
        ("quarter FE", "False"),
        ("view_count used", "False"),
        (f"quarter_total_posts>={FILTER_THRESH} filter", "True"),
    ]:
        print(f"  {item}: {val}")

    pri_pre = res_pre[res_pre["dv"] == PRIMARY_DV].set_index("model_name")
    pri_main = res_main[res_main["dv"] == PRIMARY_DV].set_index("model_name")
    for label, pri in [("H3-pre", pri_pre), ("H3-main", pri_main)]:
        for m in ["M0", "M7"]:
            r = pri.loc[m]
            tp_s = f"{r['turning_point']:.4f}" if not (isinstance(r['turning_point'], float) and np.isnan(r['turning_point'])) else "NaN"
            print(f"\n{label} {m}: β1={r['beta_linear']:.4f}(p={r['p_linear']:.4f}), "
                  f"β2={r['beta_quadratic']:.4f}(p={r['p_quadratic']:.4f}), "
                  f"tp={tp_s}, flag={r['interpretation_flag']}")


if __name__ == "__main__":
    main()
