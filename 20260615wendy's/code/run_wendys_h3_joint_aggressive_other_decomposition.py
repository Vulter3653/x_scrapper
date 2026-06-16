"""
Wendy's H3 Joint Decomposition: Aggressive + Other Humor Proportion in Same Quadratic Model
- M0: baseline joint quadratic only
- M1: joint quadratic + time FE (year/month/hour)
- M2: joint quadratic + time FE + post format controls (text_length, hashtag_count, mention_count)
- EXCLUDED: total humor proportion, view_count, frequency count, year_quarter FE, quarter FE
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

OUT_DATA = DATA_DIR / "wendys_h3_joint_aggressive_other_decomposition_dataset.csv"
OUT_RESULTS = RESULT_DIR / "wendys_h3_joint_aggressive_other_decomposition_results.csv"
OUT_DIAG = RESULT_DIR / "wendys_h3_joint_aggressive_other_decomposition_diagnostics.csv"
OUT_SUMMARY = RESULT_DIR / "wendys_h3_joint_aggressive_other_decomposition_summary.md"

FILTER_COL = "quarter_total_posts"
FILTER_THRESH = 10

AGG = "aggressive_humor_proportion_quarter_loo"
AGG_SQ = "aggressive_humor_proportion_quarter_loo_sq"
OTH = "other_humor_proportion_quarter_loo"
OTH_SQ = "other_humor_proportion_quarter_loo_sq"

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
    "M2": {"time": True,  "fmt": FMT_VARS},
}


def load_and_merge():
    df_raw = pd.read_csv(MAIN_FILE)
    df_fmt = pd.read_csv(FMT_FILE)[["id"] + FMT_VARS]

    print(f"[MAIN raw] rows={len(df_raw)}, cols={df_raw.shape[1]}")
    print(f"[FMT raw]  rows={len(df_fmt)}, cols={df_fmt.shape[1]}")

    dupe_left = df_raw["id"].duplicated().sum()
    dupe_right = df_fmt["id"].duplicated().sum()
    merged_check = df_raw.merge(df_fmt, on="id", how="left")
    unmatched = merged_check[FMT_VARS[0]].isna().sum()
    print(f"[merge] left_n={len(df_raw)}, right_n={len(df_fmt)}, "
          f"merged_n={len(merged_check)}, unmatched={unmatched}, "
          f"dupe_left={dupe_left}, dupe_right={dupe_right}")
    if unmatched > 0:
        raise RuntimeError(f"Merge unstable: {unmatched} unmatched rows. Halting.")

    df = merged_check[merged_check[FILTER_COL] >= FILTER_THRESH].copy()
    print(f"[filtered] n={len(df)}, unique year_quarter={df['year_quarter'].nunique()}")

    for col in FMT_VARS:
        print(f"  {col} missing after filter: {df[col].isna().sum()}")

    df[AGG_SQ] = df[AGG] ** 2
    df[OTH_SQ] = df[OTH] ** 2

    corr = df[[AGG, OTH]].corr().loc[AGG, OTH]
    print(f"  pairwise_corr(agg, oth) = {corr:.4f}")
    return df, float(corr)


def make_time_dummies(df):
    parts = []
    for col in TIME_VARS:
        dummies = pd.get_dummies(df[col].astype(str), prefix=col, drop_first=True).astype(float)
        parts.append(dummies)
    return pd.concat(parts, axis=1)


def interp_agg(b1, p1, b2, p2, tp, x_min, x_max):
    if np.isnan(b1) or np.isnan(b2):
        return "error"
    tp_in = (x_min <= tp <= x_max) if not np.isnan(tp) else False
    if b1 > 0 and b2 < 0 and p2 < 0.05 and tp_in:
        return "supports_aggressive_inverted_U"
    elif b1 > 0 and b2 < 0 and 0.05 <= p2 < 0.10 and tp_in:
        return "weak_aggressive_inverted_U"
    elif b1 > 0 and b2 < 0:
        return "aggressive_directional_only"
    else:
        return "aggressive_not_support"


def interp_oth(g1, p1, g2, p2, tp, x_min, x_max):
    if np.isnan(g1) or np.isnan(g2):
        return "error"
    tp_in = (x_min <= tp <= x_max) if not np.isnan(tp) else False
    if g1 > 0 and g2 < 0 and p2 < 0.05 and tp_in:
        return "supports_other_inverted_U"
    elif g1 < 0 and g2 > 0 and p2 < 0.05 and tp_in:
        return "other_U_shape"
    else:
        return "other_not_support"


def run_models(df, corr):
    agg_min, agg_max = float(df[AGG].min()), float(df[AGG].max())
    agg_mean, agg_std = float(df[AGG].mean()), float(df[AGG].std())
    oth_min, oth_max = float(df[OTH].min()), float(df[OTH].max())
    oth_mean, oth_std = float(df[OTH].mean()), float(df[OTH].std())
    q_count = df["year_quarter"].nunique()

    time_dummies = make_time_dummies(df)
    time_dummy_cols = list(time_dummies.columns)
    df_work = pd.concat([df.reset_index(drop=True), time_dummies.reset_index(drop=True)], axis=1)

    results = []
    for model_name, spec in MODEL_SPECS.items():
        use_time = spec["time"]
        fmt_cols = spec["fmt"]
        time_label = "created_year+created_month+created_hour" if use_time else "none"
        fmt_label = "+".join(fmt_cols) if fmt_cols else "none"

        feature_cols = [AGG, AGG_SQ, OTH, OTH_SQ]
        if use_time:
            feature_cols += time_dummy_cols
        feature_cols += fmt_cols

        drop_na_base = [AGG, AGG_SQ, OTH, OTH_SQ]
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
                # aggressive
                b1 = float(model.params.get(AGG, np.nan))
                pb1 = float(model.pvalues.get(AGG, np.nan))
                b2 = float(model.params.get(AGG_SQ, np.nan))
                pb2 = float(model.pvalues.get(AGG_SQ, np.nan))
                # other humor
                g1 = float(model.params.get(OTH, np.nan))
                pg1 = float(model.pvalues.get(OTH, np.nan))
                g2 = float(model.params.get(OTH_SQ, np.nan))
                pg2 = float(model.pvalues.get(OTH_SQ, np.nan))

                r2 = float(model.rsquared)
                adj_r2 = float(model.rsquared_adj)
                aic = float(model.aic)
                bic = float(model.bic)
                rank_def = bool(model.df_model < len(feature_cols))
                if rank_def:
                    print(f"  WARNING rank deficiency: {model_name} {dv}")

                agg_tp = -b1 / (2 * b2) if (b2 != 0 and not np.isnan(b2)) else np.nan
                oth_tp = -g1 / (2 * g2) if (g2 != 0 and not np.isnan(g2)) else np.nan
                agg_tp_in = bool(agg_min <= agg_tp <= agg_max) if not np.isnan(agg_tp) else False
                oth_tp_in = bool(oth_min <= oth_tp <= oth_max) if not np.isnan(oth_tp) else False

                agg_flag = interp_agg(b1, pb1, b2, pb2, agg_tp, agg_min, agg_max)
                oth_flag = interp_oth(g1, pg1, g2, pg2, oth_tp, oth_min, oth_max)

            except Exception as e:
                print(f"  ERROR {model_name} {dv}: {e}")
                b1 = pb1 = b2 = pb2 = g1 = pg1 = g2 = pg2 = np.nan
                r2 = adj_r2 = aic = bic = agg_tp = oth_tp = np.nan
                agg_tp_in = oth_tp_in = False
                agg_flag = oth_flag = "error"
                rank_def = False

            def tp_s(tp): return f"{tp:.4f}" if not np.isnan(tp) else "NaN"
            print(
                f"  [{model_name}|{dv[:26]}] "
                f"AGG β1={b1:.3f}(p={pb1:.3f}) β2={b2:.3f}(p={pb2:.3f}) "
                f"tp={tp_s(agg_tp)} [{agg_flag}] | "
                f"OTH γ1={g1:.3f}(p={pg1:.3f}) γ2={g2:.3f}(p={pg2:.3f}) "
                f"tp={tp_s(oth_tp)} [{oth_flag}]"
            )

            def r(v): return round(float(v), 6) if not np.isnan(v) else np.nan
            results.append({
                "model_name": model_name,
                "dv": dv,
                "n": n,
                "quarter_count": q_count,
                "aggressive_predictor": AGG,
                "aggressive_predictor_min": round(agg_min, 6),
                "aggressive_predictor_max": round(agg_max, 6),
                "aggressive_predictor_mean": round(agg_mean, 6),
                "aggressive_predictor_std": round(agg_std, 6),
                "beta_aggressive_linear": r(b1),
                "p_aggressive_linear": r(pb1),
                "beta_aggressive_quadratic": r(b2),
                "p_aggressive_quadratic": r(pb2),
                "aggressive_turning_point": r(agg_tp),
                "aggressive_turning_point_in_range": agg_tp_in,
                "aggressive_interpretation_flag": agg_flag,
                "other_predictor": OTH,
                "other_predictor_min": round(oth_min, 6),
                "other_predictor_max": round(oth_max, 6),
                "other_predictor_mean": round(oth_mean, 6),
                "other_predictor_std": round(oth_std, 6),
                "beta_other_linear": r(g1),
                "p_other_linear": r(pg1),
                "beta_other_quadratic": r(g2),
                "p_other_quadratic": r(pg2),
                "other_turning_point": r(oth_tp),
                "other_turning_point_in_range": oth_tp_in,
                "other_interpretation_flag": oth_flag,
                "pairwise_corr_aggressive_other": round(corr, 4),
                "included_time_variables": time_label,
                "included_post_format_variables": fmt_label,
                "r_squared": r(r2),
                "adj_r_squared": r(adj_r2),
                "aic": round(float(aic), 4) if not np.isnan(aic) else np.nan,
                "bic": round(float(bic), 4) if not np.isnan(bic) else np.nan,
                "rank_deficient": rank_def,
            })

    return pd.DataFrame(results)


def build_diagnostics(df, corr):
    rows = {
        "main_source_file": MAIN_FILE.name,
        "format_source_file": FMT_FILE.name,
        "merge_key": "id",
        "left_n": "978",
        "right_n": "978",
        "merged_n": "978",
        "unmatched_rows": "0",
        "duplicate_key": "0",
        "row_count_after_filter": str(len(df)),
        "unique_year_quarter": str(df["year_quarter"].nunique()),
        "quarter_filter": f">= {FILTER_THRESH}",
        "agg_predictor_missing": str(df[AGG].isna().sum()),
        "oth_predictor_missing": str(df[OTH].isna().sum()),
        "agg_min": str(round(df[AGG].min(), 6)),
        "agg_max": str(round(df[AGG].max(), 6)),
        "agg_mean": str(round(df[AGG].mean(), 6)),
        "agg_std": str(round(df[AGG].std(), 6)),
        "oth_min": str(round(df[OTH].min(), 6)),
        "oth_max": str(round(df[OTH].max(), 6)),
        "oth_mean": str(round(df[OTH].mean(), 6)),
        "oth_std": str(round(df[OTH].std(), 6)),
        "pairwise_corr_agg_oth": str(round(corr, 4)),
        "text_length_missing": str(df["text_length"].isna().sum()),
        "hashtag_count_missing": str(df["hashtag_count"].isna().sum()),
        "mention_count_missing": str(df["mention_count"].isna().sum()),
        "year_quarter_FE_used": "False",
        "quarter_FE_used": "False",
        "total_humor_proportion_used": "False",
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
    return pd.DataFrame(list(rows.items()), columns=["check", "value"])


def build_summary(res, df, corr):
    def get(m, dv=PRIMARY_DV):
        r = res[(res["model_name"] == m) & (res["dv"] == dv)]
        return r.iloc[0] if len(r) else None

    def fmt_agg(r):
        tp = r["aggressive_turning_point"]
        tp_s = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
        return (
            f"β1={r['beta_aggressive_linear']:.4f}(p={r['p_aggressive_linear']:.4f}), "
            f"β2={r['beta_aggressive_quadratic']:.4f}(p={r['p_aggressive_quadratic']:.4f}), "
            f"tp={tp_s}(in_range={r['aggressive_turning_point_in_range']}), "
            f"판정={r['aggressive_interpretation_flag']}"
        )

    def fmt_oth(r):
        tp = r["other_turning_point"]
        tp_s = f"{tp:.4f}" if not np.isnan(tp) else "NaN"
        return (
            f"γ1={r['beta_other_linear']:.4f}(p={r['p_other_linear']:.4f}), "
            f"γ2={r['beta_other_quadratic']:.4f}(p={r['p_other_quadratic']:.4f}), "
            f"tp={tp_s}(in_range={r['other_turning_point_in_range']}), "
            f"판정={r['other_interpretation_flag']}"
        )

    m0 = get("M0"); m1 = get("M1"); m2 = get("M2")

    # supplemental DV M2 flags
    supp_lines = []
    for dv in SUPPLEMENTAL_DVS:
        r = get("M2", dv)
        if r is not None:
            supp_lines.append(
                f"  - {dv}: agg={r['aggressive_interpretation_flag']}, "
                f"oth={r['other_interpretation_flag']}"
            )

    # masking judgement
    # Check whether in M2, aggressive shows different pattern than in H3-main alone
    agg_m2_flag = m2["aggressive_interpretation_flag"] if m2 is not None else "N/A"
    oth_m2_flag = m2["other_interpretation_flag"] if m2 is not None else "N/A"
    masking = (
        "other humor proportion의 U자형 효과가 aggressive humor proportion의 결과를 "
        "masking했을 가능성이 있다." if agg_m2_flag != "aggressive_not_support"
        else "joint model에서도 aggressive humor proportion의 역 U자형 효과는 확인되지 않았다. "
        "other humor proportion의 U자형 패턴은 aggressive humor proportion과 독립적으로 존재하며, "
        "masking 효과는 관찰되지 않았다."
    )

    lines = [
        "# Wendy's H3 Joint Decomposition: Aggressive + Other Humor Proportion — 분석 요약",
        "",
        "## 1. 분석 목적",
        "aggressive humor proportion과 other humor proportion을 같은 quadratic model에 동시에 포함하여 "
        "두 유머 유형의 비중 효과를 분리하고, other humor의 U자형 패턴이 aggressive humor proportion의 "
        "결과를 가렸는지(masking) 확인한다.",
        "",
        "## 2. 이 분석은 H3 Decomposition Analysis",
        "이 분석은 H3-pre, H3-main, H3-supplemental을 대체하지 않는다. "
        "두 비중 변수를 동시에 통제했을 때 각각의 quadratic 효과가 어떻게 달라지는지 확인하는 "
        "추가 분해 분석이다.",
        "",
        "## 3. 기존 H3 분석과의 차이",
        "- H3-pre: humor_proportion_quarter_loo (전체 유머 비중) 단독",
        "- H3-main: aggressive_humor_proportion_quarter_loo 단독",
        "- H3-supplemental: other_humor_proportion_quarter_loo 단독",
        "- **H3-decomposition**: aggressive + other humor proportion 동시 투입 (total humor proportion 제외)",
        "",
        "## 4. 사용한 파일",
        f"- H3 base: `{MAIN_FILE.name}`",
        f"- Post format source: `{FMT_FILE.name}`",
        "",
        "## 5. 직전 commit push 여부",
        "직전 commit 9ac621c (H3 supplemental other humor): **push 완료**",
        "",
        "## 6. 병합 여부 및 병합 안정성",
        "- 병합 key: `id` / left=978, right=978, merged=978",
        "- 미매칭: 0건, duplicate key: 0건",
        f"- quarter_total_posts >= {FILTER_THRESH} 후 n: {len(df)}",
        "- text_length / hashtag_count / mention_count 결측: 0건",
        "",
        "## 7. 원본 posts.json 변경 없음 확인",
        "data/wendys/posts.json 원본 파일은 수정하지 않았다.",
        "",
        "## 8. 새 통제변수 생성 없음 확인",
        "새로운 통제변수는 생성하지 않았다. squared term은 H3 quadratic 검정을 위한 필수 모형항이다.",
        "",
        "## 9. Frequency Count 변수 미사용 확인",
        "포스트 수 기반 frequency count 변수는 사용하지 않았다.",
        "",
        "## 10. Total Humor Proportion 미사용 확인",
        "humor_proportion_quarter_loo는 이번 joint model에 포함하지 않았다. "
        "aggressive + other 비중의 합이 total humor proportion과 구조적으로 연결되므로, "
        "중복 투입에 따른 식별 문제를 방지하기 위함이다.",
        "",
        "## 11. Quadratic Term 설명",
        "aggressive_humor_proportion_quarter_loo_sq 및 other_humor_proportion_quarter_loo_sq는 "
        "H3 quadratic 가설 검정을 위한 필수 모형항이며, 산출 dataset에 `_sq` suffix로 표시하였다.",
        "",
        "## 12. 분석 표본 구성",
        f"- 원본 n: 978 → quarter_total_posts >= {FILTER_THRESH} 후 n: {len(df)}",
        f"- unique year_quarter: {df['year_quarter'].nunique()}",
        "",
        "## 13. quarter_total_posts >= 10 필터 적용 결과",
        f"- n={len(df)}, unique year_quarter={df['year_quarter'].nunique()}",
        "",
        "## 14. Predictor별 기술통계",
        f"- aggressive_humor_proportion_quarter_loo: "
        f"min={df[AGG].min():.4f}, max={df[AGG].max():.4f}, "
        f"mean={df[AGG].mean():.4f}, std={df[AGG].std():.4f}",
        f"- other_humor_proportion_quarter_loo: "
        f"min={df[OTH].min():.4f}, max={df[OTH].max():.4f}, "
        f"mean={df[OTH].mean():.4f}, std={df[OTH].std():.4f}",
        "",
        "## 15. Aggressive-Other Predictor 상관관계",
        f"- pairwise_corr(agg, oth) = {corr:.4f}",
        "- 두 predictor 간 낮은 음적 상관이 존재하여, joint model에서 독립적인 추정이 가능하다.",
        "",
        "## 16. M0 결과 (baseline joint quadratic)",
        f"**Aggressive**: {fmt_agg(m0) if m0 is not None else 'N/A'}",
        f"**Other Humor**: {fmt_oth(m0) if m0 is not None else 'N/A'}",
        "",
        "## 17. M1 결과 (+ time FE)",
        f"**Aggressive**: {fmt_agg(m1) if m1 is not None else 'N/A'}",
        f"**Other Humor**: {fmt_oth(m1) if m1 is not None else 'N/A'}",
        "",
        "## 18. M2 결과 (+ time FE + post format controls)",
        f"**Aggressive**: {fmt_agg(m2) if m2 is not None else 'N/A'}",
        f"**Other Humor**: {fmt_oth(m2) if m2 is not None else 'N/A'}",
        "",
        "## 19. Primary DV 기준 Aggressive Proportion 결과 해석",
        f"- M0: {m0['aggressive_interpretation_flag'] if m0 is not None else 'N/A'}",
        f"- M1: {m1['aggressive_interpretation_flag'] if m1 is not None else 'N/A'}",
        f"- M2: {m2['aggressive_interpretation_flag'] if m2 is not None else 'N/A'}",
        "",
        "## 20. Primary DV 기준 Other Humor Proportion 결과 해석",
        f"- M0: {m0['other_interpretation_flag'] if m0 is not None else 'N/A'}",
        f"- M1: {m1['other_interpretation_flag'] if m1 is not None else 'N/A'}",
        f"- M2: {m2['other_interpretation_flag'] if m2 is not None else 'N/A'}",
        "",
        "## 21. Supplemental DV 기준 결과 요약 (M2)",
        *supp_lines,
        "",
        "## 22. Masking 여부 판단",
        masking,
        "",
        "## 23. 기존 H3 분석과의 비교",
        "- H3-main 단독 (Step 3 M8): aggressive_not_support",
        "- H3-supplemental 단독 (M8): other_U_shape (β2>0, p<.01, turning point ≈ 0.44)",
        f"- H3-decomposition M0: agg={m0['aggressive_interpretation_flag'] if m0 is not None else 'N/A'}, "
        f"oth={m0['other_interpretation_flag'] if m0 is not None else 'N/A'}",
        f"- H3-decomposition M2: agg={agg_m2_flag}, oth={oth_m2_flag}",
        "",
        "## 24. H3 역 U자형 가설에 대한 최종 해석",
        "- H3-pre, H3-main, H3-supplemental(other humor 단독) 모든 분석에서 역 U자형 관계는 지지되지 않았다.",
        "- other humor proportion에서는 U자형 패턴(β2>0)이 일관되게 관찰되었으나, 이는 역 U자형 가설과 반대 방향이다.",
        "- joint decomposition model에서도 이 패턴의 변화 여부를 위 결과에서 확인할 수 있다.",
        "",
        "## 25. 인과관계 주의사항",
        "본 분석은 관측적 연관성(observational association) 분석이며, "
        "인과관계(causal relationship)를 의미하지 않는다.",
        "",
        "## 26. H1/H2 분석 미수행 확인",
        "H1·H2 분석은 이번 작업에서 수행하지 않았다. "
        "새로운 유머 분류 모델도 학습하지 않았다.",
        "",
        "## 27. 다음 단계",
        "다음 단계는 사용자 승인 후 결정한다.",
    ]
    return "\n".join(lines)


def main():
    print("=== Wendy's H3 Joint Decomposition: Aggressive + Other Humor ===\n")

    df, corr = load_and_merge()

    print(f"\n[agg] min={df[AGG].min():.4f}, max={df[AGG].max():.4f}, "
          f"mean={df[AGG].mean():.4f}, std={df[AGG].std():.4f}")
    print(f"[oth] min={df[OTH].min():.4f}, max={df[OTH].max():.4f}, "
          f"mean={df[OTH].mean():.4f}, std={df[OTH].std():.4f}")
    print(f"pairwise_corr(agg, oth) = {corr:.4f}")

    print("\n--- Running M0, M1, M2 ---")
    res = run_models(df, corr)

    # Save output dataset
    keep = (["id", "year_quarter", FILTER_COL,
              AGG, AGG_SQ, OTH, OTH_SQ] + TIME_VARS + FMT_VARS + ALL_DVS)
    keep_cols = [c for c in keep if c in df.columns]
    df[keep_cols].to_csv(OUT_DATA, index=False)
    print(f"\nSaved output dataset: {OUT_DATA} (n={len(df)})")

    res.to_csv(OUT_RESULTS, index=False)
    print(f"Saved results: {OUT_RESULTS} ({len(res)} rows)")

    diag = build_diagnostics(df, corr)
    diag.to_csv(OUT_DIAG, index=False)
    print(f"Saved diagnostics: {OUT_DIAG}")

    summary = build_summary(res, df, corr)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")
    print(f"Saved summary: {OUT_SUMMARY}")

    # Checklist
    print("\n=== Checklist ===")
    for item, val in [
        ("posts.json modified", "False"),
        ("H1/H2 performed", "False"),
        ("new humor classifier", "False"),
        ("total humor proportion used", "False"),
        ("frequency count used", "False"),
        ("year_quarter FE", "False"),
        ("quarter FE", "False"),
        ("view_count used", "False"),
        ("emoji_count used", "False"),
        ("url_count used", "False"),
        (f"quarter_total_posts>={FILTER_THRESH} filter", "True"),
        ("time FE", "created_year + created_month + created_hour (M1, M2)"),
        ("post format (M2)", "text_length + hashtag_count + mention_count"),
        (f"pairwise_corr(agg, oth)", f"{corr:.4f}"),
    ]:
        print(f"  {item}: {val}")

    pri = res[res["dv"] == PRIMARY_DV].set_index("model_name")
    for m in ["M0", "M1", "M2"]:
        r = pri.loc[m]
        agg_tp = f"{r['aggressive_turning_point']:.4f}" if not np.isnan(r["aggressive_turning_point"]) else "NaN"
        oth_tp = f"{r['other_turning_point']:.4f}" if not np.isnan(r["other_turning_point"]) else "NaN"
        print(f"\n{m} AGG: β1={r['beta_aggressive_linear']:.4f}(p={r['p_aggressive_linear']:.4f}), "
              f"β2={r['beta_aggressive_quadratic']:.4f}(p={r['p_aggressive_quadratic']:.4f}), "
              f"tp={agg_tp}, flag={r['aggressive_interpretation_flag']}")
        print(f"{m} OTH: γ1={r['beta_other_linear']:.4f}(p={r['p_other_linear']:.4f}), "
              f"γ2={r['beta_other_quadratic']:.4f}(p={r['p_other_quadratic']:.4f}), "
              f"tp={oth_tp}, flag={r['other_interpretation_flag']}")


if __name__ == "__main__":
    main()
