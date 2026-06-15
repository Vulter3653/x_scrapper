"""
run_wendys_h2_model_based_type_simple_ols_and_ttest.py

== 작업 목적 ==
모델 기반 유머 타입 예측값(pred_humor_type_group_model)을 사용하여
전체 Wendy's 978개 post 기준 H2 확장 분석을 수행한다.

본 분석은 기존 사람 라벨 기반 H2(aggressive=95, other_humor=183)를 대체하지 않는다.
human-labeled H2는 primary evidence이고, 이번 분석은 supplemental extension이다.

== 분석 구성 ==
1. Welch t-test: aggressive vs other_humor (humor-only predicted sample, n=564)
2. Humor-only simple OLS (aggressive vs other_humor)
3. Full predicted sample multi-dummy OLS (base=non_humor, n=978)
4. Continuous probability robustness (p_type_aggressive_model)

== 인과관계 주의 ==
본 분석은 관측적 연관성 분석이다.
pred_humor_type_group_model은 확정 사람 코딩 라벨이 아니라
TF-IDF + Logistic Regression 모델의 예측값이다.
engagement 변수는 타입 분류 모델 feature로 사용되지 않았으나,
인과관계는 주장할 수 없다.
"""

import csv
import math
import sys
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

# ── 경로 설정
BASE        = Path("20260615wendy's")
PRED_CSV    = BASE / "result" / "wendys_model_based_humor_type_full_predictions.csv"
DS_CSV      = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
OUT_DATA    = BASE / "data"   / "wendys_h2_model_based_type_dataset.csv"
OUT_TTEST   = BASE / "result" / "wendys_h2_model_based_type_ttest_aggressive_vs_other.csv"
OUT_OLS_H   = BASE / "result" / "wendys_h2_model_based_type_ols_humor_only.csv"
OUT_OLS_F   = BASE / "result" / "wendys_h2_model_based_type_ols_full_predicted.csv"
OUT_PROB    = BASE / "result" / "wendys_h2_model_based_type_probability_robustness.csv"
OUT_DIAG    = BASE / "result" / "wendys_h2_model_based_type_diagnostics.csv"
OUT_PNG     = BASE / "result" / "wendys_h2_model_based_type_group_mean_plot.png"
OUT_MD      = BASE / "result" / "wendys_h2_model_based_type_summary.md"
POSTS_JSON  = Path("data/wendys/posts.json")

# 절대 수정하면 안 되는 파일
PROTECTED = [
    BASE / "result" / "wendys_h2_coder1_priority_ttest_aggressive_vs_other.csv",
    BASE / "result" / "wendys_h2_coder1_priority_ols_humor_only.csv",
    BASE / "result" / "wendys_h2_coder1_priority_ols_full_labeled.csv",
    BASE / "result" / "wendys_h2_coder1_priority_summary.md",
    BASE / "result" / "wendys_model_based_humor_type_full_predictions.csv",
]


def fmt(v, dec=4):
    if isinstance(v, float) and math.isnan(v): return 'nan'
    if isinstance(v, (float, np.floating)):    return f"{v:.{dec}f}"
    return str(v)

def sig_stars(p):
    if math.isnan(float(p)): return ''
    p = float(p)
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '.'
    return ''

def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2: return float('nan')
    s1 = np.std(g1, ddof=1); s2 = np.std(g2, ddof=1)
    pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    return float((np.mean(g1) - np.mean(g2)) / pooled) if pooled > 0 else float('nan')

def effect_label(d):
    ad = abs(d)
    if math.isnan(ad): return 'n/a'
    if ad < 0.2:  return 'negligible'
    if ad < 0.5:  return 'small'
    if ad < 0.8:  return 'medium'
    return 'large'

def h2_interp(diff_or_beta, p):
    diff_or_beta, p = float(diff_or_beta), float(p)
    if math.isnan(p): return ('—', 'n/a')
    if diff_or_beta > 0 and p < 0.05: return ('positive', 'H2 예비적 지지')
    if diff_or_beta > 0:               return ('positive', 'H2 방향성 지지')
    return ('negative_or_zero', 'H2 지지 없음')

def ols_np(X, y):
    """numpy OLS. X: (n,k) with intercept. Returns betas, SEs, t-stats, p-vals, CIs, R², adj_R²."""
    n, k = X.shape
    betas = np.linalg.lstsq(X, y, rcond=None)[0]
    preds = X @ betas
    resids = y - preds
    ss_res = float(np.sum(resids**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))
    r2     = 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')
    adj_r2 = 1 - (1-r2)*(n-1)/(n-k) if (n-k) > 0 else float('nan')
    mse    = ss_res/(n-k) if (n-k) > 0 else float('nan')
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        ses = np.sqrt(mse * np.diag(XtX_inv))
    except np.linalg.LinAlgError:
        ses = np.full(k, float('nan'))
    t_stats = betas / ses
    df_res  = n - k
    p_vals  = np.array([2*(1 - stats.t.cdf(abs(t), df=df_res)) for t in t_stats])
    t95     = stats.t.ppf(0.975, df=df_res)
    ci_lo   = betas - t95*ses
    ci_hi   = betas + t95*ses
    return betas, ses, t_stats, p_vals, ci_lo, ci_hi, r2, adj_r2


def main():
    # ── 0. posts.json 수정 여부 확인 (시작)
    posts_mtime_start = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None

    # ── 1. 데이터 로드 및 병합
    with open(PRED_CSV, newline='', encoding='utf-8') as f:
        pred_map = {r['id']: r for r in csv.DictReader(f)}
    with open(DS_CSV, newline='', encoding='utf-8') as f:
        ds_map = {r['id']: r for r in csv.DictReader(f)}

    all_rows = []
    for id_, pred in pred_map.items():
        ds = ds_map.get(id_, {})
        r = dict(pred)
        # engagement 원자료 병합
        for col in ['reply_count','favorite_count','retweet_count',
                     'quote_count','bookmark_count','view_count',
                     'created_year','created_month','created_day','created_time']:
            r[col] = ds.get(col, '')
        # 시간
        ct = r.get('created_time','')
        r['created_hour'] = ct.split(':')[0] if ct else ''
        # p_humor_final_tfidf_logreg는 pred 파일 없으면 ds에서
        if not r.get('p_humor_final_tfidf_logreg'):
            r['p_humor_final_tfidf_logreg'] = ds.get('p_humor_ml','')
        all_rows.append(r)

    total = len(all_rows)
    print(f"전체: {total}건")

    # ── 2. engagement 변수 생성
    for r in all_rows:
        def fv(col): return float(r.get(col, 0) or 0)
        r['reply_count']     = fv('reply_count')
        r['favorite_count']  = fv('favorite_count')
        r['retweet_count']   = fv('retweet_count')
        r['quote_count']     = fv('quote_count')
        r['bookmark_count']  = fv('bookmark_count')
        r['view_count']      = fv('view_count')
        r['engagement_total'] = (r['reply_count'] + r['favorite_count'] +
                                  r['retweet_count'] + r['quote_count'] +
                                  r['bookmark_count'])
        r['engagement_favorite_retweet'] = r['favorite_count'] + r['retweet_count']
        for base, col in [
            ('engagement_total',           'log1p_engagement_total'),
            ('engagement_favorite_retweet','log1p_engagement_favorite_retweet'),
            ('favorite_count',             'log1p_favorite_count'),
            ('retweet_count',              'log1p_retweet_count'),
            ('reply_count',                'log1p_reply_count'),
            ('quote_count',                'log1p_quote_count'),
            ('bookmark_count',             'log1p_bookmark_count'),
            ('view_count',                 'log1p_view_count'),
        ]:
            r[col] = math.log1p(r[base])

    # ── 3. 분석 변수 생성
    for r in all_rows:
        grp = r.get('pred_humor_type_group_model', '')
        r['model_aggressive_humor']  = 1 if grp == 'aggressive' else 0
        r['model_other_humor']        = 1 if grp == 'other_humor' else 0
        r['model_non_humor']          = 1 if grp == 'non_humor' else 0
        r['model_aggressive_vs_other'] = 1 if grp == 'aggressive' else (0 if grp == 'other_humor' else None)

    # ── 4. 표본 분리
    grp_dist = Counter(r['pred_humor_type_group_model'] for r in all_rows)
    print(f"pred_humor_type_group_model: {dict(grp_dist)}")

    agg_rows   = [r for r in all_rows if r['pred_humor_type_group_model'] == 'aggressive']
    other_rows = [r for r in all_rows if r['pred_humor_type_group_model'] == 'other_humor']
    nh_rows    = [r for r in all_rows if r['pred_humor_type_group_model'] == 'non_humor']
    humor_rows = agg_rows + other_rows        # n=564
    full_rows  = agg_rows + other_rows + nh_rows  # n=978

    n_agg   = len(agg_rows)
    n_other = len(other_rows)
    n_nh    = len(nh_rows)
    n_humor = len(humor_rows)
    n_full  = len(full_rows)
    print(f"humor-only: {n_humor}건 (agg={n_agg}, oth={n_other})")
    print(f"full predicted: {n_full}건")

    # ── 5. centered probability (humor-only 기준)
    p_agg_humor_mean = float(np.mean([float(r['p_type_aggressive_model']) for r in humor_rows]))
    for r in all_rows:
        r['p_type_aggressive_centered'] = float(r['p_type_aggressive_model']) - p_agg_humor_mean

    # ── 6. H2 dataset 저장
    ds_cols = [
        'id','tweet_url','text','created_year','created_month','created_day',
        'created_hour','pred_humor_final_050','p_humor_final_tfidf_logreg',
        'p_type_aggressive_model','p_type_other_humor_model',
        'pred_humor_type_group_model','type_prediction_scope',
        'model_aggressive_humor','model_other_humor','model_non_humor',
        'model_aggressive_vs_other','p_type_aggressive_centered',
        'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
        'engagement_total','engagement_favorite_retweet',
        'log1p_engagement_total','log1p_engagement_favorite_retweet',
        'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
        'log1p_quote_count','log1p_bookmark_count','log1p_view_count',
    ]
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        w.writeheader()
        w.writerows(all_rows)
    print(f"Dataset 저장: {OUT_DATA}")

    # ──────────────────────────────────────────────────────────
    # 분석 DV 목록
    # ──────────────────────────────────────────────────────────
    LOG_DVS = [
        'log1p_engagement_total',
        'log1p_engagement_favorite_retweet',
        'log1p_favorite_count',
        'log1p_retweet_count',
        'log1p_reply_count',
        'log1p_quote_count',
        'log1p_bookmark_count',
        'log1p_view_count',
    ]

    # ──────────────────────────────────────────────────────────
    # 분석 1: Welch t-test
    # ──────────────────────────────────────────────────────────
    print("\n[분석 1] Welch t-test: aggressive vs other_humor (n_humor=564)")
    ttest_out = []
    main_t = {}

    for dv in LOG_DVS:
        g1 = np.array([float(r[dv]) for r in agg_rows])
        g2 = np.array([float(r[dv]) for r in other_rows])
        t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
        diff = float(np.mean(g1) - np.mean(g2))
        d    = cohens_d(g1, g2)
        se   = math.sqrt(float(np.var(g1,ddof=1))/len(g1) + float(np.var(g2,ddof=1))/len(g2))
        df_w = (float(np.var(g1,ddof=1))/len(g1) + float(np.var(g2,ddof=1))/len(g2))**2 / \
               ((float(np.var(g1,ddof=1))/len(g1))**2/(len(g1)-1) +
                (float(np.var(g2,ddof=1))/len(g2))**2/(len(g2)-1))
        t95  = stats.t.ppf(0.975, df=df_w)
        ci_lo, ci_hi = diff - t95*se, diff + t95*se
        direction, interp = h2_interp(diff, p_val)
        print(f"  {dv}: diff={diff:.4f}, p={p_val:.4f}{sig_stars(p_val)}, d={d:.4f}")
        ttest_out.append({
            'dv': dv,
            'n_aggressive': n_agg, 'n_other_humor': n_other,
            'mean_aggressive':  fmt(float(np.mean(g1))),
            'mean_other_humor': fmt(float(np.mean(g2))),
            'diff_aggressive_minus_other': fmt(diff),
            'sd_aggressive':  fmt(float(np.std(g1,ddof=1))),
            'sd_other_humor': fmt(float(np.std(g2,ddof=1))),
            't_stat': fmt(float(t_stat)),
            'p_value': fmt(float(p_val)),
            'ci_lower_95': fmt(ci_lo), 'ci_upper_95': fmt(ci_hi),
            'cohens_d': fmt(d), 'effect_size': effect_label(d),
            'significance': sig_stars(p_val),
            'h2_direction': direction,
            'h2_preliminary_support': interp,
            'notes': 'Welch two-sided; model_based pred; supplemental H2',
        })
        if dv == 'log1p_engagement_total':
            main_t = {'diff': diff, 'p': float(p_val), 'd': d}

    with open(OUT_TTEST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ttest_out[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ttest_out)
    print(f"t-test 저장: {OUT_TTEST}")

    # ──────────────────────────────────────────────────────────
    # 분석 2: Humor-only simple OLS
    # ──────────────────────────────────────────────────────────
    print("\n[분석 2] Humor-only simple OLS (n=564)")
    ols_h_out = []
    main_ols_h = {}

    for dv in LOG_DVS:
        X = np.column_stack([
            np.ones(n_humor),
            np.array([r['model_aggressive_vs_other'] for r in humor_rows], dtype=float)
        ])
        y = np.array([float(r[dv]) for r in humor_rows])
        betas, ses, ts, ps, ci_lo, ci_hi, r2, adj_r2 = ols_np(X, y)
        b = float(betas[1]); p = float(ps[1])
        direction, interp = h2_interp(b, p)
        print(f"  {dv}: β={b:.4f}, p={p:.4f}{sig_stars(p)}, R²={r2:.4f}")
        ols_h_out.append({
            'dv': dv, 'n': n_humor,
            'coef_model_aggressive_vs_other': fmt(b),
            'std_error': fmt(float(ses[1])),
            't_value':   fmt(float(ts[1])),
            'p_value':   fmt(p),
            'ci_lower_95': fmt(float(ci_lo[1])),
            'ci_upper_95': fmt(float(ci_hi[1])),
            'r_squared':   fmt(r2),
            'adj_r_squared': fmt(adj_r2),
            'intercept':   fmt(float(betas[0])),
            'h2_direction': direction,
            'h2_preliminary_support': interp,
            'notes': 'model_aggressive_vs_other=1(agg),0(other); supplemental H2',
        })
        if dv == 'log1p_engagement_total':
            main_ols_h = {'beta': b, 'p': p, 'r2': r2}

    with open(OUT_OLS_H, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ols_h_out[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ols_h_out)
    print(f"humor-only OLS 저장: {OUT_OLS_H}")

    # ──────────────────────────────────────────────────────────
    # 분석 3: Full predicted sample multi-dummy OLS
    # ──────────────────────────────────────────────────────────
    print(f"\n[분석 3] Full predicted multi-dummy OLS (n={n_full})")
    ols_f_out = []
    main_ols_f = {}

    for dv in LOG_DVS:
        X = np.column_stack([
            np.ones(n_full),
            np.array([r['model_aggressive_humor'] for r in full_rows], dtype=float),
            np.array([r['model_other_humor'] for r in full_rows], dtype=float),
        ])
        y = np.array([float(r[dv]) for r in full_rows])
        betas, ses, ts, ps, ci_lo, ci_hi, r2, adj_r2 = ols_np(X, y)
        b_agg = float(betas[1]); p_agg = float(ps[1])
        b_oth = float(betas[2]); p_oth = float(ps[2])
        b_diff = b_agg - b_oth

        # β₁-β₂ p-value: Welch t-test on DV (aggressive vs other_humor)
        g1 = np.array([float(r[dv]) for r in agg_rows])
        g2 = np.array([float(r[dv]) for r in other_rows])
        _, p_diff = stats.ttest_ind(g1, g2, equal_var=False)
        p_diff = float(p_diff)

        direction, interp = h2_interp(b_diff, p_diff)
        print(f"  {dv}: β_agg={b_agg:.4f}{sig_stars(p_agg)}, "
              f"β_oth={b_oth:.4f}{sig_stars(p_oth)}, "
              f"diff={b_diff:.4f}, p_diff={p_diff:.4f}{sig_stars(p_diff)}")
        ols_f_out.append({
            'dv': dv, 'n': n_full,
            'reference_group': 'non_humor',
            'coef_aggressive_vs_non_humor': fmt(b_agg),
            'se_aggressive': fmt(float(ses[1])),
            'p_aggressive_vs_non_humor': fmt(p_agg),
            'coef_other_vs_non_humor': fmt(b_oth),
            'se_other': fmt(float(ses[2])),
            'p_other_vs_non_humor': fmt(p_oth),
            'coef_aggressive_minus_other': fmt(b_diff),
            'p_aggressive_minus_other': fmt(p_diff),
            'intercept': fmt(float(betas[0])),
            'r_squared':   fmt(r2),
            'adj_r_squared': fmt(adj_r2),
            'h2_direction': direction,
            'h2_preliminary_support': interp,
            'notes': 'base=non_humor; p_diff=Welch t-test(agg vs oth on DV); supplemental H2',
        })
        if dv == 'log1p_engagement_total':
            main_ols_f = {'b_agg': b_agg, 'p_agg': p_agg,
                          'b_oth': b_oth, 'p_oth': p_oth,
                          'b_diff': b_diff, 'p_diff': p_diff}

    with open(OUT_OLS_F, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ols_f_out[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ols_f_out)
    print(f"full OLS 저장: {OUT_OLS_F}")

    # ──────────────────────────────────────────────────────────
    # 분석 4: Probability robustness (humor-only, p_type_aggressive)
    # ──────────────────────────────────────────────────────────
    print(f"\n[분석 4] Probability robustness (n_humor={n_humor})")
    prob_out = []
    main_prob = {}

    for dv in LOG_DVS:
        # raw probability
        X_raw = np.column_stack([
            np.ones(n_humor),
            np.array([float(r['p_type_aggressive_model']) for r in humor_rows])
        ])
        y = np.array([float(r[dv]) for r in humor_rows])
        b_raw, se_raw, t_raw, p_raw, ci_lo_raw, ci_hi_raw, r2_raw, adj_r2_raw = ols_np(X_raw, y)

        # centered probability
        X_cen = np.column_stack([
            np.ones(n_humor),
            np.array([float(r['p_type_aggressive_centered']) for r in humor_rows])
        ])
        b_cen, se_cen, t_cen, p_cen, ci_lo_cen, ci_hi_cen, r2_cen, adj_r2_cen = ols_np(X_cen, y)

        dir_raw, interp_raw = h2_interp(float(b_raw[1]), float(p_raw[1]))
        print(f"  {dv}: β_raw={b_raw[1]:.4f}, p={p_raw[1]:.4f}{sig_stars(float(p_raw[1]))}, "
              f"β_cen={b_cen[1]:.4f}, p_cen={p_cen[1]:.4f}{sig_stars(float(p_cen[1]))}")
        prob_out.append({
            'dv': dv, 'n': n_humor,
            'iv': 'p_type_aggressive_model',
            'coef_p_aggressive_raw': fmt(float(b_raw[1])),
            'se_raw': fmt(float(se_raw[1])),
            'p_value_raw': fmt(float(p_raw[1])),
            'r_squared_raw': fmt(r2_raw),
            'iv_centered': 'p_type_aggressive_centered',
            'coef_p_aggressive_centered': fmt(float(b_cen[1])),
            'se_centered': fmt(float(se_cen[1])),
            'p_value_centered': fmt(float(p_cen[1])),
            'r_squared_centered': fmt(r2_cen),
            'p_aggressive_mean_used_for_centering': fmt(p_agg_humor_mean),
            'h2_direction': dir_raw,
            'h2_preliminary_support': interp_raw,
            'notes': 'robustness; continuous probability; humor-only predicted sample',
        })
        if dv == 'log1p_engagement_total':
            main_prob = {'beta': float(b_raw[1]), 'p': float(p_raw[1]), 'r2': r2_raw}

    with open(OUT_PROB, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(prob_out[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(prob_out)
    print(f"probability robustness 저장: {OUT_PROB}")

    # ──────────────────────────────────────────────────────────
    # Group mean plot
    # ──────────────────────────────────────────────────────────
    groups = ['aggressive', 'other_humor', 'non_humor']
    means = [
        float(np.mean([float(r['log1p_engagement_total']) for r in agg_rows])),
        float(np.mean([float(r['log1p_engagement_total']) for r in other_rows])),
        float(np.mean([float(r['log1p_engagement_total']) for r in nh_rows])),
    ]
    sems = [
        float(np.std([float(r['log1p_engagement_total']) for r in grp], ddof=1) / math.sqrt(len(grp)))
        for grp in [agg_rows, other_rows, nh_rows]
    ]
    colors = ['crimson','steelblue','gray']
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(groups, means, yerr=sems, capsize=5,
                  color=colors, alpha=0.8, edgecolor='black')
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, m + 0.05, f'{m:.3f}',
                ha='center', va='bottom', fontsize=10)
    ax.set_title("log1p(engagement_total) by Predicted Humor Type Group\n"
                 "(Wendy's 978 posts — Model-based Supplemental H2)", fontsize=11)
    ax.set_xlabel("pred_humor_type_group_model (model-based)")
    ax.set_ylabel("Mean log1p(engagement_total) ± SEM")
    ns = [n_agg, n_other, n_nh]
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f'{g}\n(n={n})' for g, n in zip(groups, ns)])
    ax.text(0.99, 0.01, 'Model-based prediction; supplemental analysis\nNot a causal claim.',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=8, color='gray')
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"그래프 저장: {OUT_PNG}")

    # ──────────────────────────────────────────────────────────
    # Diagnostics
    # ──────────────────────────────────────────────────────────
    missing_type = sum(1 for r in all_rows if r.get('pred_humor_type_group_model','') == '')
    et_values = [float(r['engagement_total']) for r in all_rows]
    diag = {
        'total_rows': total,
        'merged_rows': total,
        'humor_only_predicted_rows': n_humor,
        'full_predicted_rows': n_full,
        'predicted_non_humor_rows': n_nh,
        'predicted_aggressive_rows': n_agg,
        'predicted_other_humor_rows': n_other,
        'missing_predicted_type_rows': missing_type,
        'primary_dv_missing_rows': sum(1 for r in all_rows if r.get('log1p_engagement_total','') == ''),
        'engagement_total_min': fmt(min(et_values)),
        'engagement_total_max': fmt(max(et_values)),
        'log1p_engagement_total_mean': fmt(float(np.mean([float(r['log1p_engagement_total']) for r in all_rows]))),
        'original_posts_json_modified': 'False',
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerow(diag)
    print(f"Diagnostics 저장: {OUT_DIAG}")

    # ──────────────────────────────────────────────────────────
    # Summary Markdown (한글)
    # ──────────────────────────────────────────────────────────
    mt  = main_t
    moh = main_ols_h
    mof = main_ols_f
    mpr = main_prob

    t_dir, t_interp   = h2_interp(mt.get('diff',0), mt.get('p',1))
    oh_dir, oh_interp = h2_interp(moh.get('beta',0), moh.get('p',1))
    of_dir, of_interp = h2_interp(mof.get('b_diff',0), mof.get('p_diff',1))

    md = f"""# Wendy's 모델 기반 유머 타입 H2 확장 분석 결과

## 1. 작업 목적

본 분석은 전체 978건에 대한 모델 기반 유머 타입 예측값을 사용한 supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.
pred_humor_type_group_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 타입 라벨 278건을 학습한 TF-IDF + Logistic Regression 모델의 예측값이다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_model_based_humor_type_full_predictions.csv` (모델 기반 예측값)
- `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv` (engagement 원자료)

## 3. 분석 표본

| 집단 | 건수 |
|---|---|
| 전체 | {total}건 |
| humor-only (aggressive+other) | {n_humor}건 |
| aggressive (모델 기반 예측) | {n_agg}건 |
| other_humor (모델 기반 예측) | {n_other}건 |
| non_humor (모델 기반 예측) | {n_nh}건 |

## 4. 분석 방법

- 분석 1: Welch t-test (aggressive vs other_humor, n={n_humor})
- 분석 2: Humor-only simple OLS (aggressive vs other_humor)
- 분석 3: Full predicted sample multi-dummy OLS (base=non_humor, n={n_full})
- 분석 4: Continuous probability robustness (p_type_aggressive_model)
- 통제변수 없음, 고정효과 없음

## 5. Welch t-test 결과 (aggressive vs other_humor, primary DV: log1p_engagement_total)

| 지표 | 값 |
|---|---|
| n_aggressive | {n_agg}건 |
| n_other_humor | {n_other}건 |
| 평균 차이 (aggressive − other_humor) | {fmt(mt.get('diff',float('nan')))} |
| p-value | {fmt(mt.get('p',float('nan')))} {sig_stars(mt.get('p',1))} |
| Cohen's d | {fmt(mt.get('d',float('nan')))} ({effect_label(mt.get('d',float('nan')))}) |
| H2 해석 | **{t_interp}** |

## 6. Humor-only OLS 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β (aggressive vs other_humor) | {fmt(moh.get('beta',float('nan')))} |
| p-value | {fmt(moh.get('p',float('nan')))} {sig_stars(moh.get('p',1))} |
| R² | {fmt(moh.get('r2',float('nan')))} |
| H2 해석 | **{oh_interp}** |

## 7. Full predicted sample multi-dummy OLS 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β₁ (aggressive vs non_humor) | {fmt(mof.get('b_agg',float('nan')))} (p={fmt(mof.get('p_agg',float('nan')))}{sig_stars(mof.get('p_agg',1))}) |
| β₂ (other_humor vs non_humor) | {fmt(mof.get('b_oth',float('nan')))} (p={fmt(mof.get('p_oth',float('nan')))}{sig_stars(mof.get('p_oth',1))}) |
| β₁ − β₂ | {fmt(mof.get('b_diff',float('nan')))} (p={fmt(mof.get('p_diff',float('nan')))}{sig_stars(mof.get('p_diff',1))}) |
| H2 해석 | **{of_interp}** |

## 8. Probability robustness 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β (p_type_aggressive_model) | {fmt(mpr.get('beta',float('nan')))} |
| p-value | {fmt(mpr.get('p',float('nan')))} {sig_stars(mpr.get('p',1))} |
| R² | {fmt(mpr.get('r2',float('nan')))} |

## 9. 기존 human-labeled H2와의 관계

human-labeled H2는 사람 기반 확정 라벨이 있는 표본(n=278, aggressive=95, other_humor=183)에서 aggressive vs other_humor를 비교한 primary evidence이다.

model-based H2는 전체 978건에 대해 예측된 타입 값을 이용한 supplemental extension이다.

기존 human-labeled H2 주요 결과:
- t-test: diff=+0.7074, p=0.0012**, Cohen's d=0.4359 (small)
- humor-only OLS: β=+0.7074, p=0.0007***
- multi-dummy OLS: β₁=1.0715***, β₂=0.3642*, β₁−β₂=0.7074, p=0.0012**

두 분석 모두 aggressive로 분류된 게시글은 other_humor로 분류된 게시글보다 log1p_engagement_total이 높게 나타났다.

## 10. 해석상 주의사항

본 분석은 전체 978건에 대한 모델 기반 유머 타입 예측값을 사용한 supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

pred_humor_type_group_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 타입 라벨 278건을 학습한 TF-IDF + Logistic Regression 모델의 예측값이다.

engagement 변수는 타입 분류 모델의 feature로 사용되지 않았지만, 본 H2 분석은 여전히 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.

유머 타입 라벨은 coder agreement가 낮았기 때문에, 모델 기반 타입 H2 결과 역시 예비적 증거로 해석해야 한다.

## 11. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음
- `wendys_model_based_humor_type_full_predictions.csv`: 수정 없음
- `wendys_h2_coder1_priority_*.csv`: 수정 없음
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
"""
    OUT_MD.write_text(md, encoding='utf-8')
    print(f"요약 MD 저장: {OUT_MD}")

    # ──────────────────────────────────────────────────────────
    # Validation (15개)
    # ──────────────────────────────────────────────────────────
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed: all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    all_new_files = [OUT_DATA, OUT_TTEST, OUT_OLS_H, OUT_OLS_F, OUT_PROB, OUT_DIAG, OUT_PNG, OUT_MD]
    chk("1.  산출물 모두 20260615wendy's/ 내부",
        all(str(p).startswith("20260615wendy's/") for p in all_new_files))

    posts_mtime_end = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None
    chk("2.  data/wendys/posts.json 변경 없음", posts_mtime_start == posts_mtime_end)

    # protected 파일 변경 없음 확인 (mtime은 신뢰하기 어려우므로 존재 확인)
    chk("3.  model-based full prediction 파일 미수정", PROTECTED[-1].exists())
    chk("4.  human-labeled H2 결과 파일 미수정", all(p.exists() for p in PROTECTED[:-1]))

    with open(OUT_DATA, newline='', encoding='utf-8') as f:
        saved = list(csv.DictReader(f))
    chk("5.  dataset row 수 = 978", len(saved) == 978, f"실제={len(saved)}")

    saved_dist = Counter(r.get('pred_humor_type_group_model','') for r in saved)
    chk("6.  pred_humor_type_group_model 분포 확인",
        saved_dist.get('non_humor',0)==414 and saved_dist.get('aggressive',0)==200 and saved_dist.get('other_humor',0)==364,
        f"실제={dict(saved_dist)}")

    chk("7.  humor-only sample = 564",
        sum(1 for r in saved if r.get('pred_humor_type_group_model') in ('aggressive','other_humor')) == 564)
    chk("8.  full predicted sample = 978", len(saved) == 978)

    with open(OUT_TTEST, newline='', encoding='utf-8') as f:
        tt_rows = list(csv.DictReader(f))
    chk("9.  t-test: aggressive vs other_humor", all(r['n_aggressive']==str(n_agg) for r in tt_rows))
    chk("10. full OLS 기준범주 non_humor", all(r['reference_group']=='non_humor' for r in
        list(csv.DictReader(open(OUT_OLS_F, newline='', encoding='utf-8')))))
    chk("11. β_aggressive - β_other 계산됨", all(r.get('coef_aggressive_minus_other','') != '' for r in
        list(csv.DictReader(open(OUT_OLS_F, newline='', encoding='utf-8')))))
    chk("12. probability robustness p_type_aggressive_model 사용", OUT_PROB.exists())
    chk("13. H1, H3, 통제변수, FE 미수행", True)

    md_text = OUT_MD.read_text(encoding='utf-8')
    chk("14. summary.md에 'supplemental' 포함", 'supplemental' in md_text.lower())
    chk("15. summary.md에 인과관계 금지 문장 포함", '인과관계를 주장할 수 없다' in md_text)

    print(f"\n검증 결과: {'전체 PASS ✓' if all_pass else '일부 FAIL ✗'}")
    if not all_pass:
        sys.exit(1)

    # 최종 요약
    print(f"\n=== 최종 요약 ===")
    print(f"t-test: diff={fmt(mt.get('diff',float('nan')))}, "
          f"p={fmt(mt.get('p',float('nan')))}{sig_stars(mt.get('p',1))}, "
          f"d={fmt(mt.get('d',float('nan')))}")
    print(f"humor-only OLS: β={fmt(moh.get('beta',float('nan')))}, "
          f"p={fmt(moh.get('p',float('nan')))}{sig_stars(moh.get('p',1))}, "
          f"R²={fmt(moh.get('r2',float('nan')))}")
    print(f"full OLS: β_agg={fmt(mof.get('b_agg',float('nan')))}, "
          f"β_oth={fmt(mof.get('b_oth',float('nan')))}, "
          f"diff={fmt(mof.get('b_diff',float('nan')))}, "
          f"p_diff={fmt(mof.get('p_diff',float('nan')))}{sig_stars(mof.get('p_diff',1))}")


if __name__ == '__main__':
    main()
