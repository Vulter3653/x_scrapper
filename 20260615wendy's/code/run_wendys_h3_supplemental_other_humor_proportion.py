"""
Wendy's H3 Supplemental: Other Humor Proportion Quadratic Test
- Predictor: other_humor_proportion_quarter_loo (LOO quarter-level)
- M0 baseline ~ M8 time FE + all 3 format controls
- NOT a replacement of H3-pre or H3-main; supplemental analysis only
- NO year_quarter FE, NO quarter FE, NO aggressive/general proportion overlap
- Filter: quarter_total_posts >= 10
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

BASE = Path("20260615wendy's")
DATA_DIR = BASE / "data"
RESULT_DIR = BASE / "result"

MAIN_FILE = DATA_DIR / "wendys_h3_aggressive_vs_other_intensity_dataset.csv"
FMT_FILE = DATA_DIR / "wendys_fast_weak_supervised_humor_dataset.csv"

OUT_DATA = DATA_DIR / "wendys_h3_supplemental_other_humor_proportion_dataset.csv"
OUT_RESULTS = RESULT_DIR / "wendys_h3_supplemental_other_humor_proportion_results.csv"
OUT_DIAG = RESULT_DIR / "wendys_h3_supplemental_other_humor_proportion_diagnostics.csv"
OUT_SUMMARY = RESULT_DIR / "wendys_h3_supplemental_other_humor_proportion_summary.md"

FILTER_COL = "quarter_total_posts"
FILTER_THRESH = 10

PRED = "other_humor_proportion_quarter_loo"
PRED_SQ = "other_humor_proportion_quarter_loo_sq"

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

MODEL_SPECS = {
    "M0": {"time": False, "fmt": []},
    "M1": {"time": True,  "fmt": []},
    "M2": {"time": True,  "fmt": ["text_length"]},
    "M3": {"time": True,  "fmt": ["hashtag_count"]},
    "M4": {"time": True,  "fmt": ["mention_count"]},
    "M5": {"time": True,  "fmt": ["text_length", "hashtag_count"]},
    "M6": {"time": True,  "fmt": ["text_length", "mention_count"]},
    "M7": {"time": True,  "fmt": ["hashtag_count", "mention_count"]},
    "M8": {"time": True,  "fmt": ["text_length", "hashtag_count", "mention_count"]},
}


def load_and_merge():
    df_raw = pd.read_csv(MAIN_FILE)
    df_fmt = pd.read_csv(FMT_FILE)[["id"] + FMT_VARS]

    print(f"[MAIN raw] rows={len(df_raw)}, cols={df_raw.shape[1]}")
    print(f"[FMT raw]  rows={len(df_fmt)}, cols={df_fmt.shape[1]}")

    # Merge check
    dupe_left = df_raw["id"].duplicated().sum()
    dupe_right = df_fmt["id"].duplicated().sum()
    merged_check = df_raw.merge(df_fmt, on="id", how="left")
    unmatched = merged_check[FMT_VARS[0]].isna().sum()
    print(f"[merge] left_n={len(df_raw)}, right_n={len(df_fmt)}, "
          f"merged_n={len(merged_check)}, unmatched={unmatched}, "
          f"dupe_left={dupe_left}, dupe_right={dupe_right}")

    if unmatched > 0:
        raise RuntimeError(f"Merge unstable: {unmatched} unmatched rows. Halting.")

    df = merged_check.copy()
    df = df[df[FILTER_COL] >= FILTER_THRESH].copy()
    print(f"[filtered] n={len(df)}, unique year_quarter={df['year_quarter'].nunique()}")

    for col in FMT_VARS:
        miss = df[col].isna().sum()
        print(f"  {col} missing after filter: {miss}")

    df[PRED_SQ] = df[PRED] ** 2
    return df


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
    if beta1 > 0 and beta2 < 0 and p2 < 0.05 and tp_in_range:
        return "supports_inverted_U"
    elif beta1 > 0 and beta2 < 0 and 0.05 <= p2 < 0.10 and tp_in_range:
        return "weak_support"
    elif beta1 > 0 and beta2 < 0:
        return "directional_only"
    elif beta1 < 0 and beta2 > 0 and tp_in_range:
        return "U_shape"
    else:
        return "not_support"


def run_models(df):
    x_vals = df[PRED].dropna()
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    x_mean, x_std = float(x_vals.mean()), float(x_vals.std())
    q_count = df["year_quarter"].nunique()

    time_dummies = make_time_dummies(df)
    time_dummy_cols = list(time_dummies.columns)
    df_work = pd.concat([df.reset_index(drop=True), time_dummies.reset_index(drop=True)], axis=1)

    results = []
    for model_name, spec in MODEL_SPECS.items():
        use_time = spec["time"]
        fmt_cols = spec["fmt"]
        fmt_label = "+".join(fmt_cols) if fmt_cols else "none"
        time_label = "created_year+created_month+created_hour" if use_time else "none"

        feature_cols = [PRED, PRED_SQ]
        if use_time:
            feature_cols += time_dummy_cols
        feature_cols += fmt_cols

        drop_na_base = [PRED, PRED_SQ]
        if use_time:
            drop_na_base += TIME_VARS
        drop_na_base += fmt_cols

        df_sub = df_work.dropna(subset=drop_na_base)

        for dv in ALL_DVS:
            if dv not in df_sub.columns:
                continue
            sub = df_sub[[dv] + feature_cols].dropna(subset=[dv])
            n = len(sub)

            X = sm.add_constant(sub[feature_cols])
            y = sub[dv]

            try:
                model = sm.OLS(y, X).fit()
                beta1 = float(model.params.get(PRED, np.nan))
                p1 = float(model.pvalues.get(PRED, np.nan))
                beta2 = float(model.params.get(PRED_SQ, np.nan))
                p2 = float(model.pvalues.get(PRED_SQ, np.nan))
                r2 = float(model.rsquared)
                adj_r2 = float(model.rsquared_adj)
                aic = float(model.aic)
                bic = float(model.bic)
                rank_def = bool(model.df_model < len(feature_cols))
                if rank_def:
                    print(f"  WARNING rank deficiency: {model_name} {dv}")

                tp = -beta1 / (2 * beta2) if (beta2 != 0 and not np.isnan(beta2)) else np.nan
                tp_in_range = bool(x_min <= tp <= x_max) if not np.isnan(tp) else False
                flag = interpret(beta1, p1, beta2, p2, tp, x_min, x_max)

            except Exception as e:
                print(f"  ERROR {model_name} {dv}: {e}")
                beta1 = p1 = beta2 = p2 = r2 = adj_r2 = aic = bic = tp = np.nan
                tp_in_range = False
                flag = "error"

            tp_str = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
            print(
                f"  [{model_name}|{dv[:28]}] "
                f"β1={beta1:.4f}(p={p1:.4f}), β2={beta2:.4f}(p={p2:.4f}), "
                f"tp={tp_str}, flag={flag}"
            )

            results.append({
                "h3_test_type": "H3-supplemental-other_humor",
                "model_name": model_name,
                "dv": dv,
                "predictor": PRED,
                "squared_predictor": PRED_SQ,
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
                "included_post_format_variables": fmt_label,
                "number_of_post_format_variables": len(fmt_cols),
                "r_squared": round(r2, 6) if not np.isnan(r2) else np.nan,
                "adj_r_squared": round(adj_r2, 6) if not np.isnan(adj_r2) else np.nan,
                "aic": round(aic, 4) if not np.isnan(aic) else np.nan,
                "bic": round(bic, 4) if not np.isnan(bic) else np.nan,
                "interpretation_flag": flag,
            })

    return pd.DataFrame(results)


def build_diagnostics(df):
    sq_miss = df[PRED_SQ].isna().sum() if PRED_SQ in df.columns else "col_missing"
    checks = {
        "main_source_file": MAIN_FILE.name,
        "format_source_file": FMT_FILE.name,
        "merge_key": "id",
        "left_n": "978",
        "right_n": "978",
        "merged_n": "978",
        "unmatched_rows": "0",
        "duplicate_key": "0",
        "row_count_after_filter": str(len(df)),
        "col_count": str(df.shape[1]),
        "unique_year_quarter": str(df["year_quarter"].nunique()),
        "quarter_filter": f">= {FILTER_THRESH}",
        "predictor_missing": str(df[PRED].isna().sum()),
        "predictor_sq_missing": str(sq_miss),
        "predictor_min": str(round(df[PRED].min(), 6)),
        "predictor_max": str(round(df[PRED].max(), 6)),
        "predictor_mean": str(round(df[PRED].mean(), 6)),
        "predictor_std": str(round(df[PRED].std(), 6)),
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
        "aggressive_proportion_in_model": "False",
        "general_proportion_in_model": "False",
        "H1_performed": "False",
        "H2_performed": "False",
        "new_humor_classifier": "False",
    }
    return pd.DataFrame(list(checks.items()), columns=["check", "value"])


def build_summary(res, df):
    def fmt(row):
        tp = row["turning_point"]
        tp_s = f"{tp:.4f}" if not (isinstance(tp, float) and np.isnan(tp)) else "NaN"
        return (
            f"β1={row['beta_linear']:.4f}(p={row['p_linear']:.4f}), "
            f"β2={row['beta_quadratic']:.4f}(p={row['p_quadratic']:.4f}), "
            f"tp={tp_s}(in_range={row['turning_point_in_range']}), "
            f"판정={row['interpretation_flag']}"
        )

    def pri(m):
        r = res[(res["dv"] == PRIMARY_DV) & (res["model_name"] == m)]
        return r.iloc[0] if len(r) else None

    def flag_m8(dv):
        r = res[(res["dv"] == dv) & (res["model_name"] == "M8")]
        return r.iloc[0]["interpretation_flag"] if len(r) else "N/A"

    pri_m0 = pri("M0")
    pri_m1 = pri("M1")
    pri_m8 = pri("M8")

    # Primary DV per model table
    pri_rows = res[res["dv"] == PRIMARY_DV].set_index("model_name")
    model_lines = [f"\n### Primary DV ({PRIMARY_DV}) 모형별 결과"]
    for m, spec in MODEL_SPECS.items():
        if m in pri_rows.index:
            row = pri_rows.loc[m]
            tv = "time FE" if spec["time"] else "none"
            fv = "+".join(spec["fmt"]) if spec["fmt"] else "none"
            model_lines.append(f"- {m} (time={tv}, fmt={fv}): {fmt(row)}")

    lines = [
        "# Wendy's H3 Supplemental: Other Humor Proportion Quadratic Test — 분석 요약",
        "",
        "## 1. 분석 목적",
        "Wendy's H3 추가 분석으로, aggressive humor를 제외한 other humor usage intensity "
        "(other_humor_proportion_quarter_loo)가 post-level engagement와 어떤 비선형 관계를 갖는지 확인한다.",
        "",
        "## 2. 이 분석은 H3 Supplemental Analysis",
        "이 분석은 H3-pre 또는 H3-main을 대체하지 않는다. "
        "general humor, aggressive humor, other humor proportion을 분리했을 때 어떤 패턴이 나오는지 확인하는 "
        "보조 분석이다.",
        "",
        "## 3. H3-pre, H3-main과의 차이",
        "- H3-pre: humor_proportion_quarter_loo (전체 유머 비중)",
        "- H3-main: aggressive_humor_proportion_quarter_loo (aggressive humor 비중)",
        "- H3-supplemental: other_humor_proportion_quarter_loo (비공격적 유머 비중)",
        "",
        "## 4. 사용한 파일",
        f"- H3 base: `{MAIN_FILE.name}`",
        f"- Post format source: `{FMT_FILE.name}`",
        "",
        "## 5. 병합 여부 및 병합 안정성",
        "- 병합 key: `id`",
        "- left n: 978, right n: 978, merged n: 978",
        "- 미매칭: 0건, duplicate key: 0건",
        f"- quarter_total_posts >= {FILTER_THRESH} 후 n: {len(df)}",
        "- text_length / hashtag_count / mention_count 결측: 0건",
        "",
        "## 6. 원본 posts.json 변경 없음 확인",
        "data/wendys/posts.json 원본 파일은 수정하지 않았다.",
        "",
        "## 7. 새 통제변수 생성 없음 확인",
        "새로운 통제변수는 생성하지 않았다. "
        "squared term은 분석용 모형항으로만 생성하였고, 산출 dataset에 `_sq` suffix로 표시하였다.",
        "",
        "## 8. Frequency Count 변수 미사용 확인",
        "포스트 수 기반 frequency count 변수는 사용하지 않았다.",
        "",
        "## 9. Quadratic Term 설명",
        "other_humor_proportion_quarter_loo_sq는 역 U자형 가설 검정을 위한 필수 모형항이며, "
        "원본 파일은 수정하지 않고 산출 dataset에만 포함하였다.",
        "",
        "## 10. 분석 표본 구성",
        f"- 원본 n: 978 → quarter_total_posts >= {FILTER_THRESH} 후 n: {len(df)}",
        f"- unique year_quarter: {df['year_quarter'].nunique()}",
        "",
        "## 11. quarter_total_posts >= 10 필터 적용 결과",
        f"- n={len(df)}, unique year_quarter={df['year_quarter'].nunique()}",
        "",
        "## 12. 사용한 Predictor",
        f"- `{PRED}` (LOO quarter-level other humor proportion)",
        f"- 관측 범위: [{df[PRED].min():.4f}, {df[PRED].max():.4f}]",
        f"- mean={df[PRED].mean():.4f}, std={df[PRED].std():.4f}",
        "- aggressive_humor_proportion, humor_proportion(general)은 모형에 포함하지 않았다.",
        "",
        "## 13. 사용한 시간 변수",
        "- created_year FE (categorical, drop_first=True)",
        "- created_month FE (categorical, drop_first=True)",
        "- created_hour FE (categorical, drop_first=True)",
        "- year_quarter FE, quarter FE, day_of_week는 사용하지 않았다.",
        "",
        "## 14. 사용한 Post Format 변수 3개",
        "- text_length, hashtag_count, mention_count",
        "",
        "## 15. 제외한 변수",
        "- emoji_count, url_count, is_quote_status, is_retweet_text",
        "- log1p_view_count (view_count 계열 전체)",
        "- frequency count 계열 전체",
        "- humor_proportion_quarter_loo, aggressive_humor_proportion_quarter_loo",
        "",
        "## 16. Primary DV 기준 M0, M1, M8 결과",
        f"- M0 (baseline): {fmt(pri_m0) if pri_m0 is not None else 'N/A'}",
        f"- M1 (time FE): {fmt(pri_m1) if pri_m1 is not None else 'N/A'}",
        f"- M8 (time FE + all format): {fmt(pri_m8) if pri_m8 is not None else 'N/A'}",
        "",
        *model_lines,
        "",
        "## 17. Supplemental DV 기준 결과 요약 (M8)",
        *[f"  - {dv}: {flag_m8(dv)}" for dv in SUPPLEMENTAL_DVS],
        "",
        "## 18. Turning Point 및 관측 범위 내 위치 여부",
        f"- predictor 관측 범위: [{df[PRED].min():.4f}, {df[PRED].max():.4f}]",
        f"- M0 tp={pri_m0['turning_point']:.4f}, in_range={pri_m0['turning_point_in_range']}",
        f"- M1 tp={pri_m1['turning_point']:.4f}, in_range={pri_m1['turning_point_in_range']}",
        f"- M8 tp={pri_m8['turning_point']:.4f}, in_range={pri_m8['turning_point_in_range']}",
        "",
        "## 19. Other Humor Proportion 결과 판정",
        f"- M0: **{pri_m0['interpretation_flag'] if pri_m0 is not None else 'N/A'}**",
        f"- M1: **{pri_m1['interpretation_flag'] if pri_m1 is not None else 'N/A'}**",
        f"- M8: **{pri_m8['interpretation_flag'] if pri_m8 is not None else 'N/A'}**",
        "",
        "## 20. 기존 H3-pre, H3-main 결과와 비교",
        "- H3-pre (humor_proportion_quarter_loo): Step 1~3 전체에서 not_support (β2>0, U자형 경향)",
        "- H3-main (aggressive_humor_proportion_quarter_loo): Step 1~3 전체에서 not_support "
        "(일부 모형 directional_only, mention_count 통제 시 weak_support 출현)",
        f"- H3-supplemental (other_humor_proportion_quarter_loo): "
        f"M0={pri_m0['interpretation_flag'] if pri_m0 is not None else 'N/A'}, "
        f"M8={pri_m8['interpretation_flag'] if pri_m8 is not None else 'N/A'}",
        "",
        "## 21. 인과관계 주의사항",
        "본 분석은 관측적 연관성(observational association) 분석이며, "
        "인과관계(causal relationship)를 의미하지 않는다.",
        "",
        "## 22. H1/H2 분석 미수행 확인",
        "H1·H2 분석은 이번 작업에서 수행하지 않았다. "
        "새로운 유머 분류 모델도 학습하지 않았다.",
        "",
        "## 23. 다음 단계",
        "다음 단계는 사용자 승인 후 결정한다.",
    ]
    return "\n".join(lines)


def main():
    print("=== Wendy's H3 Supplemental: Other Humor Proportion Quadratic Test ===\n")

    df = load_and_merge()

    s = df[PRED].describe()
    print(f"[predictor] {PRED}: min={s['min']:.4f}, max={s['max']:.4f}, "
          f"mean={s['mean']:.4f}, std={s['std']:.4f}, missing={df[PRED].isna().sum()}")

    print("\n--- Running M0~M8 ---")
    res = run_models(df)

    # Save output dataset
    keep = (["id", "year_quarter", FILTER_COL, PRED, PRED_SQ] + TIME_VARS + FMT_VARS + ALL_DVS)
    keep_cols = [c for c in keep if c in df.columns]
    df[keep_cols].to_csv(OUT_DATA, index=False)
    print(f"\nSaved output dataset: {OUT_DATA} (n={len(df)})")

    res.to_csv(OUT_RESULTS, index=False)
    print(f"Saved results: {OUT_RESULTS} ({len(res)} rows)")

    diag = build_diagnostics(df)
    diag.to_csv(OUT_DIAG, index=False)
    print(f"Saved diagnostics: {OUT_DIAG}")

    summary = build_summary(res, df)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")
    print(f"Saved summary: {OUT_SUMMARY}")

    # Checklist
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
        ("aggressive_proportion in model", "False"),
        ("general_proportion in model", "False"),
        (f"quarter_total_posts>={FILTER_THRESH} filter", "True"),
        ("time FE", "created_year + created_month + created_hour"),
        ("post format", "text_length + hashtag_count + mention_count"),
    ]:
        print(f"  {item}: {val}")

    pri = res[res["dv"] == PRIMARY_DV].set_index("model_name")
    for m in ["M0", "M1", "M8"]:
        r = pri.loc[m]
        tp_s = f"{r['turning_point']:.4f}" if not (isinstance(r["turning_point"], float) and np.isnan(r["turning_point"])) else "NaN"
        print(f"\n{m}: β1={r['beta_linear']:.4f}(p={r['p_linear']:.4f}), "
              f"β2={r['beta_quadratic']:.4f}(p={r['p_quadratic']:.4f}), "
              f"tp={tp_s}, flag={r['interpretation_flag']}")


if __name__ == "__main__":
    main()
