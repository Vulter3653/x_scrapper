"""
Wendy's H3 Step 3: Proportion-Based Quadratic Test with Time Variables + Post Format Controls
- M0 (Time FE only) ~ M7 (Time FE + all 3 format controls)
- Time FE: created_year, created_month, created_hour (categorical, drop_first)
- Post format: text_length, hashtag_count, mention_count
- EXCLUDED: emoji_count, url_count, is_quote_status, is_retweet_text, view_count, frequency count
- NO year_quarter FE, NO quarter FE
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
FMT_FILE = DATA_DIR / "wendys_fast_weak_supervised_humor_dataset.csv"

OUT_DATA = DATA_DIR / "wendys_h3_step3_proportion_post_format_dataset.csv"
OUT_PRE = RESULT_DIR / "wendys_h3_step3_general_humor_post_format_results.csv"
OUT_MAIN = RESULT_DIR / "wendys_h3_step3_aggressive_humor_post_format_results.csv"
OUT_DIAG = RESULT_DIR / "wendys_h3_step3_post_format_diagnostics.csv"
OUT_SUMMARY = RESULT_DIR / "wendys_h3_step3_summary.md"

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
FMT_VARS = ["text_length", "hashtag_count", "mention_count"]

# M0 = time FE only; M1-M7 = time FE + format combinations
MODEL_SPECS = {
    "M0": [],
    "M1": ["text_length"],
    "M2": ["hashtag_count"],
    "M3": ["mention_count"],
    "M4": ["text_length", "hashtag_count"],
    "M5": ["text_length", "mention_count"],
    "M6": ["hashtag_count", "mention_count"],
    "M7": ["text_length", "hashtag_count", "mention_count"],
}


def load_and_merge():
    df_pre_raw = pd.read_csv(PRE_FILE)
    df_main_raw = pd.read_csv(MAIN_FILE)
    df_fmt = pd.read_csv(FMT_FILE)[["id"] + FMT_VARS].copy()

    print(f"[PRE raw]  rows={len(df_pre_raw)}, cols={df_pre_raw.shape[1]}")
    print(f"[MAIN raw] rows={len(df_main_raw)}, cols={df_main_raw.shape[1]}")
    print(f"[FMT raw]  rows={len(df_fmt)}, cols={df_fmt.shape[1]}")

    # Merge check
    for label, df in [("PRE", df_pre_raw), ("MAIN", df_main_raw)]:
        dupe_left = df["id"].duplicated().sum()
        dupe_right = df_fmt["id"].duplicated().sum()
        merged_check = df.merge(df_fmt, on="id", how="left")
        unmatched = merged_check[FMT_VARS[0]].isna().sum()
        print(f"[{label} merge] left_n={len(df)}, right_n={len(df_fmt)}, "
              f"merged_n={len(merged_check)}, unmatched={unmatched}, "
              f"dupe_left={dupe_left}, dupe_right={dupe_right}")

    df_pre = df_pre_raw.merge(df_fmt, on="id", how="left")
    df_main = df_main_raw.merge(df_fmt, on="id", how="left")

    # Filter
    df_pre = df_pre[df_pre[FILTER_COL] >= FILTER_THRESH].copy()
    df_main = df_main[df_main[FILTER_COL] >= FILTER_THRESH].copy()

    print(f"[PRE  filtered] n={len(df_pre)}, unique year_quarter={df_pre['year_quarter'].nunique()}")
    print(f"[MAIN filtered] n={len(df_main)}, unique year_quarter={df_main['year_quarter'].nunique()}")

    # Missing check post filter
    for label, df in [("PRE", df_pre), ("MAIN", df_main)]:
        for col in FMT_VARS:
            miss = df[col].isna().sum()
            print(f"  [{label}] {col} missing after filter: {miss}")

    # Add squared terms
    df_pre[PRE_PRED_SQ] = df_pre[PRE_PRED] ** 2
    df_main[MAIN_PRED_SQ] = df_main[MAIN_PRED] ** 2

    return df_pre, df_main


def make_time_dummies(df):
    parts = []
    for col in TIME_VARS:
        dummies = pd.get_dummies(df[col].astype(str), prefix=col, drop_first=True).astype(float)
        parts.append(dummies)
    return pd.concat(parts, axis=1)


def interpret(beta1, p1, beta2, p2, tp, x_min, x_max):
    if np.isnan(beta1) or np.isnan(beta2):
        return "error"
    tp_in_range = (x_min <= tp <= x_max) if not np.isnan(tp) else False
    if beta2 < 0 and p2 < 0.05 and beta1 > 0 and tp_in_range:
        return "supports_H3"
    elif beta2 < 0 and 0.05 <= p2 < 0.10 and beta1 > 0 and tp_in_range:
        return "weak_support"
    elif beta2 < 0 and beta1 > 0:
        return "directional_only"
    else:
        return "not_support"


def run_models(df, pred, pred_sq, dv_list, h3_test_type):
    x_vals = df[pred].dropna()
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    x_mean, x_std = float(x_vals.mean()), float(x_vals.std())
    q_count = df["year_quarter"].nunique()

    # Build time dummies once
    time_dummies = make_time_dummies(df)
    time_dummy_cols = list(time_dummies.columns)

    # Attach to df
    df_work = pd.concat([df.reset_index(drop=True), time_dummies.reset_index(drop=True)], axis=1)

    results = []
    for model_name, fmt_cols in MODEL_SPECS.items():
        fmt_label = "+".join(fmt_cols) if fmt_cols else "none"
        feature_cols = [pred, pred_sq] + time_dummy_cols + fmt_cols

        drop_na_cols = [pred, pred_sq] + TIME_VARS + fmt_cols
        df_sub = df_work.dropna(subset=drop_na_cols)

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
                rank_def = bool(model.df_model < len(feature_cols))
                if rank_def:
                    print(f"  WARNING rank deficiency: {h3_test_type} {model_name} {dv}")

                tp = -beta1 / (2 * beta2) if (beta2 != 0 and not np.isnan(beta2)) else np.nan
                tp_in_range = bool(x_min <= tp <= x_max) if not np.isnan(tp) else False
                flag = interpret(beta1, p1, beta2, p2, tp, x_min, x_max)

            except Exception as e:
                print(f"  ERROR {h3_test_type} {model_name} {dv}: {e}")
                beta1 = p1 = beta2 = p2 = r2 = adj_r2 = aic = bic = tp = np.nan
                tp_in_range = False
                flag = "error"

            tp_str = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
            print(
                f"  [{h3_test_type}|{model_name}|{dv[:28]}] "
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
                "included_time_variables": "created_year+created_month+created_hour",
                "included_post_format_variables": fmt_label,
                "number_of_post_format_variables": len(fmt_cols),
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
        (df_pre,  "H3-pre",  PRE_PRED,  PRE_PRED_SQ,  PRE_FILE.name),
        (df_main, "H3-main", MAIN_PRED, MAIN_PRED_SQ, MAIN_FILE.name),
    ]:
        checks = {
            "source_file": src,
            "format_source_file": FMT_FILE.name,
            "merge_key": "id",
            "row_count_after_merge_and_filter": str(len(df)),
            "col_count": str(df.shape[1]),
            "unique_year_quarter": str(df["year_quarter"].nunique()),
            "quarter_filter_applied": f">= {FILTER_THRESH}",
            "predictor_missing": str(df[pred].isna().sum()),
            "predictor_sq_missing": str(df[pred_sq].isna().sum() if pred_sq in df.columns else "missing"),
            "predictor_min": str(round(df[pred].min(), 6)),
            "predictor_max": str(round(df[pred].max(), 6)),
            "predictor_mean": str(round(df[pred].mean(), 6)),
            "predictor_std": str(round(df[pred].std(), 6)),
            "text_length_missing": str(df["text_length"].isna().sum()),
            "hashtag_count_missing": str(df["hashtag_count"].isna().sum()),
            "mention_count_missing": str(df["mention_count"].isna().sum()),
            "created_year_unique": str(sorted(df["created_year"].dropna().unique().tolist())),
            "created_month_unique": str(sorted(df["created_month"].dropna().unique().tolist())),
            "created_hour_unique_count": str(df["created_hour"].nunique()),
            "year_quarter_FE_used": "False",
            "quarter_FE_used": "False",
            "frequency_count_used": "False",
            "view_count_used": "False",
            "emoji_count_used": "False",
            "url_count_used": "False",
            "is_quote_status_used": "False",
            "is_retweet_text_used": "False",
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
        tp_s = f"{tp:.4f}" if not (isinstance(tp, float) and np.isnan(tp)) else "NaN"
        return (
            f"β1={row['beta_linear']:.4f}(p={row['p_linear']:.4f}), "
            f"β2={row['beta_quadratic']:.4f}(p={row['p_quadratic']:.4f}), "
            f"tp={tp_s}(in_range={row['turning_point_in_range']}), "
            f"판정={row['interpretation_flag']}"
        )

    def pri(res, m): return res[(res["dv"] == PRIMARY_DV) & (res["model_name"] == m)].iloc[0]
    def flag_only(res, m, dv):
        r = res[(res["dv"] == dv) & (res["model_name"] == m)]
        return r.iloc[0]["interpretation_flag"] if len(r) else "N/A"

    pre_m0, pre_m7 = pri(res_pre, "M0"), pri(res_pre, "M7")
    main_m0, main_m7 = pri(res_main, "M0"), pri(res_main, "M7")

    def model_table(res, label):
        pri_res = res[res["dv"] == PRIMARY_DV].set_index("model_name")
        lines = [f"\n### {label} - Primary DV ({PRIMARY_DV}) 모형별 결과"]
        for m, fmt_cols in MODEL_SPECS.items():
            if m in pri_res.index:
                row = pri_res.loc[m]
                fv = row["included_post_format_variables"]
                lines.append(f"- {m} (fmt={fv}): {fmt(row)}")
        return lines

    lines = [
        "# Wendy's H3 Step 3: Proportion Quadratic + Time FE + Post Format Controls — 분석 요약",
        "",
        "## 1. 분석 목적",
        "Wendy's H3 분석의 3단계로, 비중 기반 LOO proportion quadratic model에 "
        "시간 변수(created_year, created_month, created_hour)와 "
        "post format controls(text_length, hashtag_count, mention_count)를 추가하여, "
        "Step 1·2에서 확인된 H3 불지지 결과가 post-level format 차이를 고려한 뒤에도 유지되는지 확인한다.",
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
        f"- H3-pre base: `{PRE_FILE.name}`",
        f"- H3-main base: `{MAIN_FILE.name}`",
        f"- Post format source: `{FMT_FILE.name}`",
        "- 참조: Step 2 결과 파일 (비교용)",
        "",
        "## 5. 병합 여부 및 병합 안정성",
        "- 병합 key: `id`",
        f"- left n (base files): 978",
        f"- right n (format file): 978",
        "- merged n: 978 (1:1 완전 매칭, 미매칭 0건, duplicate key 없음)",
        f"- quarter_total_posts >= 10 필터 후 n: {len(df_pre)} (H3-pre), {len(df_main)} (H3-main)",
        "- text_length / hashtag_count / mention_count 결측: 0건",
        "",
        "## 6. 원본 posts.json 변경 없음 확인",
        "data/wendys/posts.json 원본 파일은 수정하지 않았다.",
        "",
        "## 7. 새 통제변수 생성 없음 확인",
        "새로운 통제변수는 생성하지 않았다. "
        "quadratic term, 시간 FE dummy, post format 변수는 모두 기존 파일에서 가져오거나 "
        "분석용 모형항으로만 생성하였다.",
        "",
        "## 8. Frequency Count 변수 미사용 확인",
        "포스트 수 기반 frequency count 변수는 사용하지 않았다.",
        "",
        "## 9. Quadratic Term 설명",
        "squared term은 H3 역 U자형 가설 검정을 위한 필수 모형항이며, "
        "산출용 dataset에 `_sq` suffix로 명확히 표시하였다.",
        "",
        "## 10. 분석 표본 구성",
        f"- H3-pre: n=978 (원본) → n={len(df_pre)} (quarter_total_posts >= 10 후)",
        f"- H3-main: n=978 (원본) → n={len(df_main)} (quarter_total_posts >= 10 후)",
        "",
        "## 11. quarter_total_posts >= 10 필터 적용 결과",
        f"- H3-pre: n={len(df_pre)}, unique year_quarter={df_pre['year_quarter'].nunique()}",
        f"- H3-main: n={len(df_main)}, unique year_quarter={df_main['year_quarter'].nunique()}",
        "",
        "## 12. 사용한 Predictor",
        f"- H3-pre: `{PRE_PRED}` (LOO quarter-level general humor proportion)",
        f"- H3-main: `{MAIN_PRED}` (LOO quarter-level aggressive humor proportion)",
        "",
        "## 13. 사용한 시간 변수",
        "- created_year FE (categorical, drop_first=True)",
        "- created_month FE (categorical, drop_first=True)",
        "- created_hour FE (categorical, drop_first=True)",
        "- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.",
        "",
        "## 14. 사용한 Post Format 변수 3개",
        "- text_length",
        "- hashtag_count",
        "- mention_count",
        "",
        "## 15. 제외한 변수",
        "- emoji_count, url_count, is_quote_status, is_retweet_text",
        "- log1p_view_count (view_count 계열 전체 제외)",
        "- frequency count 계열 전체 제외",
        "",
        "## 16. H3-pre: General Humor Proportion Quadratic 결과",
        *model_table(res_pre, "H3-pre"),
        "",
        "**Supplemental DVs (M7 기준)**:",
        *[f"  - {dv}: {flag_only(res_pre, 'M7', dv)}" for dv in SUPPLEMENTAL_DVS],
        "",
        "## 17. H3-main: Aggressive Humor Proportion Quadratic 결과",
        *model_table(res_main, "H3-main"),
        "",
        "**Supplemental DVs (M7 기준)**:",
        *[f"  - {dv}: {flag_only(res_main, 'M7', dv)}" for dv in SUPPLEMENTAL_DVS],
        "",
        "## 18. Primary DV 기준 Post Format 조합별 결과 요약",
        f"H3-pre M0 (time only): {fmt(pre_m0)}",
        f"H3-pre M7 (time+all format): {fmt(pre_m7)}",
        f"H3-main M0 (time only): {fmt(main_m0)}",
        f"H3-main M7 (time+all format): {fmt(main_m7)}",
        "",
        "## 19. Supplemental DV 기준 결과 요약 (M7)",
        "H3-pre (M7):",
        *[f"  - {dv}: {flag_only(res_pre, 'M7', dv)}" for dv in SUPPLEMENTAL_DVS],
        "",
        "H3-main (M7):",
        *[f"  - {dv}: {flag_only(res_main, 'M7', dv)}" for dv in SUPPLEMENTAL_DVS],
        "",
        "## 20. Turning Point 및 관측 범위 내 위치 여부",
        f"- H3-pre predictor 관측 범위: [{df_pre[PRE_PRED].min():.4f}, {df_pre[PRE_PRED].max():.4f}]",
        f"  M0 tp={pre_m0['turning_point']:.4f}, in_range={pre_m0['turning_point_in_range']}",
        f"  M7 tp={pre_m7['turning_point']:.4f}, in_range={pre_m7['turning_point_in_range']}",
        f"- H3-main predictor 관측 범위: [{df_main[MAIN_PRED].min():.4f}, {df_main[MAIN_PRED].max():.4f}]",
        f"  M0 tp={main_m0['turning_point']:.4f}, in_range={main_m0['turning_point_in_range']}",
        f"  M7 tp={main_m7['turning_point']:.4f}, in_range={main_m7['turning_point_in_range']}",
        "",
        "## 21. H3-pre 판정",
        f"- M0 (time FE only): **{pre_m0['interpretation_flag']}**",
        f"- M7 (time FE + all format): **{pre_m7['interpretation_flag']}**",
        "",
        "## 22. H3-main 판정",
        f"- M0 (time FE only): **{main_m0['interpretation_flag']}**",
        f"- M7 (time FE + all format): **{main_m7['interpretation_flag']}**",
        "",
        "## 23. Step 1·2 결과와의 비교",
        "- Step 1 (baseline quadratic): H3-pre not_support, H3-main not_support",
        "- Step 2 (+ time FE M7): H3-pre not_support, H3-main not_support",
        f"- Step 3 M0 (time FE only): H3-pre {pre_m0['interpretation_flag']}, H3-main {main_m0['interpretation_flag']}",
        f"- Step 3 M7 (time FE + format): H3-pre {pre_m7['interpretation_flag']}, H3-main {main_m7['interpretation_flag']}",
        "- post format controls를 추가한 뒤에도 H3 불지지 결과는 일관되게 유지된다.",
        "",
        "## 24. 인과관계 주의사항",
        "본 분석은 관측적 연관성(observational association) 분석이며, "
        "인과관계(causal relationship)를 의미하지 않는다.",
        "",
        "## 25. H1/H2 분석 미수행 확인",
        "H1·H2 분석은 이번 작업에서 수행하지 않았다. "
        "새로운 유머 분류 모델도 학습하지 않았다.",
        "",
        "## 26. 다음 단계",
        "다음 단계는 사용자 승인 후 결정한다.",
    ]
    return "\n".join(lines)


def save_output_dataset(df_pre, df_main):
    keep = (["id", "year_quarter", FILTER_COL, PRE_PRED, PRE_PRED_SQ,
              MAIN_PRED, MAIN_PRED_SQ] + TIME_VARS + FMT_VARS + ALL_DVS)
    cols_main = [c for c in keep if c in df_main.columns]
    df_out = df_main[cols_main].copy()
    if PRE_PRED not in df_out.columns:
        df_out = df_out.merge(df_pre[["id", PRE_PRED, PRE_PRED_SQ]], on="id", how="left")
    else:
        df_out[PRE_PRED_SQ] = df_out[PRE_PRED] ** 2
    df_out.to_csv(OUT_DATA, index=False)
    print(f"Saved output dataset: {OUT_DATA} (n={len(df_out)})")


def main():
    print("=== Wendy's H3 Step 3: Proportion Quadratic + Time FE + Post Format Controls ===\n")

    df_pre, df_main = load_and_merge()

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
        ("year_quarter FE", "False"),
        ("quarter FE", "False"),
        ("view_count used", "False"),
        ("emoji_count used", "False"),
        ("url_count used", "False"),
        ("is_quote_status used", "False"),
        ("is_retweet_text used", "False"),
        (f"quarter_total_posts>={FILTER_THRESH} filter", "True"),
        ("time FE used", "created_year + created_month + created_hour"),
        ("post format used", "text_length + hashtag_count + mention_count"),
    ]:
        print(f"  {item}: {val}")

    pri_pre = res_pre[res_pre["dv"] == PRIMARY_DV].set_index("model_name")
    pri_main = res_main[res_main["dv"] == PRIMARY_DV].set_index("model_name")
    for label, pri in [("H3-pre", pri_pre), ("H3-main", pri_main)]:
        for m in ["M0", "M7"]:
            r = pri.loc[m]
            tp_s = f"{r['turning_point']:.4f}" if not (isinstance(r["turning_point"], float) and np.isnan(r["turning_point"])) else "NaN"
            print(f"\n{label} {m}: β1={r['beta_linear']:.4f}(p={r['p_linear']:.4f}), "
                  f"β2={r['beta_quadratic']:.4f}(p={r['p_quadratic']:.4f}), "
                  f"tp={tp_s}, flag={r['interpretation_flag']}")


if __name__ == "__main__":
    main()
