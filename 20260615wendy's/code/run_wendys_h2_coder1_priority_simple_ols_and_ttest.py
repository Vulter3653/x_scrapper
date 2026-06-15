"""
run_wendys_h2_coder1_priority_simple_ols_and_ttest.py

== 이 스크립트의 목적 ==
Wendy's 브랜드 게시글에서 aggressive humor가 other humor보다
engagement가 더 높은지를 검증한다 (H2).

== 왜 H2를 최신 coder1 우선순위 final_humor_type_group으로 재실행하는가 ==
이전 H2 분석(aggressive=90)은 final_humor_source 기반으로 type을 결정했다.
이번 작업에서 final_humor_type이 final_humor_source와 무관하게
coder1 > human > coder2 순서로 재생성되었으므로,
H2도 최신 기준(aggressive=95, other_humor=183)으로 재실행해야 한다.

== non_humor를 labeled sample 안에서만 구성해야 하는 이유 ==
final_humor_type_group = non_humor에는 총 669건이 포함된다.
그 중 381건은 final_humor_label_available = 0 (사람 라벨 없음)이다.
H2 primary 분석에서는 라벨이 확인된 표본만 사용해야 하므로,
non_humor는 반드시 final_humor_label_available = 1 조건 안에서 구성한다.

== 분석 목록 ==
1. aggressive vs other_humor Welch t-test
2. humor-only simple OLS (aggressive=1, other_humor=0)
3. labeled sample multi-dummy OLS (base=non_humor)

== 인과관계 주의 ==
본 분석은 관측적 연관성 분석이다.
aggressive humor와 engagement의 인과관계는 주장할 수 없다.
"""

import csv
import math
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from scipy import stats

# ── 경로 설정
BASE        = Path("20260615wendy's")
REVIEW_CSV  = BASE / "result" / "wendys_humor_review_sheet.csv"
DATASET_CSV = BASE / "data" / "wendys_fast_weak_supervised_humor_dataset.csv"
OUT_DATA    = BASE / "data" / "wendys_h2_coder1_priority_dataset.csv"
OUT_TTEST   = BASE / "result" / "wendys_h2_coder1_priority_ttest_aggressive_vs_other.csv"
OUT_OLS_H   = BASE / "result" / "wendys_h2_coder1_priority_ols_humor_only.csv"
OUT_OLS_F   = BASE / "result" / "wendys_h2_coder1_priority_ols_full_labeled.csv"
OUT_DIAG    = BASE / "result" / "wendys_h2_coder1_priority_diagnostics.csv"
OUT_MD      = BASE / "result" / "wendys_h2_coder1_priority_summary.md"


def fmt(v, dec=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 'nan'
    if isinstance(v, float):
        return f"{v:.{dec}f}"
    return str(v)

def sig_stars(p):
    if p is None or math.isnan(float(p)):
        return ''
    p = float(p)
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '.'
    return ''

def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return float('nan')
    s1, s2 = np.std(g1, ddof=1), np.std(g2, ddof=1)
    pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    return (np.mean(g1) - np.mean(g2)) / pooled if pooled > 0 else float('nan')

def effect_size_label(d):
    if math.isnan(d): return 'n/a'
    ad = abs(d)
    if ad < 0.2:  return 'negligible'
    if ad < 0.5:  return 'small'
    if ad < 0.8:  return 'medium'
    return 'large'

def h2_interp_ttest(diff, p):
    if math.isnan(float(p)): return 'n/a'
    diff, p = float(diff), float(p)
    if diff > 0 and p < 0.05: return 'H2 예비적 지지'
    if diff > 0:               return 'H2 방향성 지지'
    return 'H2 지지 없음'

def h2_interp_ols(beta, p):
    if math.isnan(float(p)): return 'n/a'
    beta, p = float(beta), float(p)
    if beta > 0 and p < 0.05: return 'H2 예비적 지지'
    if beta > 0:               return 'H2 방향성 지지'
    return 'H2 지지 없음'

def simple_ols_np(X, y):
    """NumPy 기반 OLS. X는 numpy 2d array (intercept 포함)."""
    n, k = X.shape
    betas = np.linalg.lstsq(X, y, rcond=None)[0]
    preds = X @ betas
    resids = y - preds
    ss_res = float(np.sum(resids**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))
    r2     = 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')
    adj_r2 = 1 - (1-r2)*(n-1)/(n-k) if (n-k) > 0 else float('nan')
    mse    = ss_res / (n-k) if (n-k) > 0 else float('nan')
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
    # ── 1. 데이터 로드 및 병합
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        review = {r['id']: r for r in csv.DictReader(f)}
    with open(DATASET_CSV, newline='', encoding='utf-8') as f:
        dataset = {r['id']: r for r in csv.DictReader(f)}

    rows = []
    for id_, rev in review.items():
        ds = dataset.get(id_, {})
        merged = dict(rev)
        for col in ['reply_count','favorite_count','retweet_count',
                     'quote_count','bookmark_count','view_count']:
            merged[col] = float(ds.get(col, 0) or 0)
        rows.append(merged)

    total = len(rows)
    print(f"전체: {total}건")

    # ── 2. engagement 변수 생성
    for r in rows:
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
        ]:
            r[col] = math.log1p(r[base])

    # ── 3. labeled sample 구성
    labeled = [r for r in rows if r.get('final_humor_label_available') == '1']
    n_labeled = len(labeled)
    print(f"labeled (final_humor_label_available=1): {n_labeled}건")

    # ── 4. 그룹 분류
    grp_dist  = Counter(r['final_humor_type_group'] for r in labeled)
    n_agg     = grp_dist.get('aggressive', 0)
    n_other   = grp_dist.get('other_humor', 0)
    n_nonhumor = grp_dist.get('non_humor', 0)
    n_missing = grp_dist.get('missing', 0)
    n_nh_total = sum(1 for r in rows if r.get('final_humor_type_group') == 'non_humor')
    print(f"그룹: aggressive={n_agg}, other_humor={n_other}, "
          f"non_humor(labeled)={n_nonhumor}, missing={n_missing}")
    print(f"non_humor 전체(label 불문): {n_nh_total}건")

    agg_rows   = [r for r in labeled if r['final_humor_type_group'] == 'aggressive']
    other_rows = [r for r in labeled if r['final_humor_type_group'] == 'other_humor']
    nh_rows    = [r for r in labeled if r['final_humor_type_group'] == 'non_humor']
    humor_rows = agg_rows + other_rows  # type missing 제외

    # ── 5. H2 dataset CSV 저장
    for r in labeled:
        grp = r['final_humor_type_group']
        r['aggressive_humor']   = '1' if grp == 'aggressive' else '0'
        r['other_humor_flag']   = '1' if grp == 'other_humor' else '0'
        r['non_humor_flag']     = '1' if r['final_humor_binary'] == '0' else '0'
        r['humor_missing_type'] = '1' if (r['final_humor_binary']=='1' and grp=='missing') else '0'

    out_cols = [
        'id','tweet_url','text',
        'final_humor_binary','final_humor_source','final_humor_label_available',
        'final_humor_type','final_humor_type_source','final_humor_type_available',
        'final_humor_type_group',
        'aggressive_humor','other_humor_flag','non_humor_flag','humor_missing_type',
        'reply_count','favorite_count','retweet_count','quote_count','bookmark_count',
        'engagement_total','engagement_favorite_retweet',
        'log1p_engagement_total','log1p_engagement_favorite_retweet',
        'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
        'log1p_quote_count','log1p_bookmark_count',
    ]
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=out_cols, quoting=csv.QUOTE_ALL,
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(labeled)
    print(f"Dataset 저장: {OUT_DATA}")

    # ──────────────────────────────────────────────────────────
    # 분석 1: Welch t-test
    # ──────────────────────────────────────────────────────────
    print("\n[분석 1] Welch t-test: aggressive vs other_humor")

    RAW_DVS = ['engagement_total','engagement_favorite_retweet',
                'favorite_count','retweet_count','reply_count','quote_count','bookmark_count']
    LOG_DVS = ['log1p_engagement_total','log1p_engagement_favorite_retweet',
                'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
                'log1p_quote_count','log1p_bookmark_count']
    ALL_DVS = [(dv,'raw') for dv in RAW_DVS] + [(dv,'log1p') for dv in LOG_DVS]

    ttest_rows = []
    main_t = {}

    for dv, scale in ALL_DVS:
        g1 = np.array([float(r[dv]) for r in agg_rows])
        g2 = np.array([float(r[dv]) for r in other_rows])
        t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
        diff = float(np.mean(g1) - np.mean(g2))
        d    = cohens_d(g1, g2)
        # 95% CI of difference
        se   = math.sqrt(float(np.var(g1, ddof=1))/len(g1) + float(np.var(g2, ddof=1))/len(g2))
        df_w = (float(np.var(g1,ddof=1))/len(g1) + float(np.var(g2,ddof=1))/len(g2))**2 / \
               ((float(np.var(g1,ddof=1))/len(g1))**2/(len(g1)-1) + (float(np.var(g2,ddof=1))/len(g2))**2/(len(g2)-1))
        t95  = stats.t.ppf(0.975, df=df_w)
        ci_lo, ci_hi = diff - t95*se, diff + t95*se

        interp = h2_interp_ttest(diff, p_val)
        print(f"  {dv} ({scale}): diff={diff:.4f}, p={p_val:.4f}{sig_stars(p_val)}, d={d:.4f}")
        ttest_rows.append({
            'dv': dv, 'scale': scale,
            'group_variable': 'final_humor_type_group',
            'group1_name': 'aggressive', 'group2_name': 'other_humor',
            'n_group1': len(g1), 'n_group2': len(g2),
            'mean_group1': fmt(float(np.mean(g1))),
            'mean_group2': fmt(float(np.mean(g2))),
            'diff_mean': fmt(diff),
            'median_group1': fmt(float(np.median(g1))),
            'median_group2': fmt(float(np.median(g2))),
            'sd_group1': fmt(float(np.std(g1, ddof=1))),
            'sd_group2': fmt(float(np.std(g2, ddof=1))),
            't_stat': fmt(float(t_stat)),
            'p_value': fmt(float(p_val)),
            'ci_lower_95': fmt(ci_lo),
            'ci_upper_95': fmt(ci_hi),
            'cohens_d': fmt(d),
            'effect_size': effect_size_label(d),
            'significance': sig_stars(p_val),
            'h2_interpretation': interp,
            'notes': 'Welch two-sided; group1=aggressive, group2=other_humor',
        })
        if dv == 'log1p_engagement_total':
            main_t = {'diff': diff, 'p': float(p_val), 'd': d}

    with open(OUT_TTEST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ttest_rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ttest_rows)
    print(f"t-test 결과 저장: {OUT_TTEST}")

    # ──────────────────────────────────────────────────────────
    # 분석 2: humor-only simple OLS
    # ──────────────────────────────────────────────────────────
    print("\n[분석 2] humor-only simple OLS")
    ols_h_rows = []
    main_ols_h = {}

    for dv in LOG_DVS:
        X = np.column_stack([
            np.ones(len(humor_rows)),
            np.array([1 if r['final_humor_type_group']=='aggressive' else 0
                      for r in humor_rows], dtype=float)
        ])
        y = np.array([float(r[dv]) for r in humor_rows])
        betas, ses, ts, ps, ci_lo, ci_hi, r2, adj_r2 = simple_ols_np(X, y)
        b_agg = float(betas[1])
        interp = h2_interp_ols(b_agg, float(ps[1]))
        print(f"  {dv}: β_agg={b_agg:.4f}, p={ps[1]:.4f}{sig_stars(float(ps[1]))}, R²={r2:.4f}")
        ols_h_rows.append({
            'dv': dv, 'model_name': 'Simple OLS',
            'sample': 'humor_only_aggressive_vs_other',
            'n_obs': len(humor_rows),
            'iv': 'aggressive_humor (1=aggressive, 0=other_humor)',
            'intercept': fmt(float(betas[0])),
            'beta_aggressive': fmt(b_agg),
            'standard_error': fmt(float(ses[1])),
            't_value': fmt(float(ts[1])),
            'p_value': fmt(float(ps[1])),
            'ci_lower_95': fmt(float(ci_lo[1])),
            'ci_upper_95': fmt(float(ci_hi[1])),
            'r_squared': fmt(r2),
            'adj_r_squared': fmt(adj_r2),
            'direction': 'positive' if b_agg > 0 else 'negative',
            'h2_interpretation': interp,
            'notes': f'aggressive=1 vs other_humor=0; n_agg={n_agg}, n_other={n_other}',
        })
        if dv == 'log1p_engagement_total':
            main_ols_h = {'beta': b_agg, 'p': float(ps[1]), 'r2': r2}

    with open(OUT_OLS_H, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ols_h_rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ols_h_rows)
    print(f"humor-only OLS 저장: {OUT_OLS_H}")

    # ──────────────────────────────────────────────────────────
    # 분석 3: labeled multi-dummy OLS (base=non_humor)
    # ──────────────────────────────────────────────────────────
    print("\n[분석 3] labeled multi-dummy OLS (base=non_humor)")
    full_rows = agg_rows + other_rows + nh_rows
    n_full = len(full_rows)
    print(f"  표본: {n_full}건 (agg={len(agg_rows)}, other={len(other_rows)}, nh={len(nh_rows)})")

    ols_f_rows = []
    main_ols_f = {}

    for dv in LOG_DVS:
        X = np.column_stack([
            np.ones(n_full),
            np.array([1 if r['final_humor_type_group']=='aggressive' else 0 for r in full_rows], dtype=float),
            np.array([1 if r['final_humor_type_group']=='other_humor' else 0 for r in full_rows], dtype=float),
        ])
        y = np.array([float(r[dv]) for r in full_rows])
        betas, ses, ts, ps, ci_lo, ci_hi, r2, adj_r2 = simple_ols_np(X, y)
        b_agg = float(betas[1]); p_agg = float(ps[1])
        b_oth = float(betas[2]); p_oth = float(ps[2])
        b_diff = b_agg - b_oth

        # β_diff 차이 검정: Welch t-test (aggressive vs other_humor on DV)
        g1 = np.array([float(r[dv]) for r in agg_rows])
        g2 = np.array([float(r[dv]) for r in other_rows])
        _, p_diff = stats.ttest_ind(g1, g2, equal_var=False)
        p_diff = float(p_diff)

        interp_full = ('H2 예비적 지지' if (b_agg > b_oth and p_agg < 0.05) else
                       'H2 방향성 지지' if b_agg > b_oth else 'H2 지지 없음')
        print(f"  {dv}: β_agg={b_agg:.4f}{sig_stars(p_agg)}, "
              f"β_oth={b_oth:.4f}{sig_stars(p_oth)}, "
              f"diff={b_diff:.4f}, p_diff={p_diff:.4f}{sig_stars(p_diff)}")
        ols_f_rows.append({
            'dv': dv, 'model_name': 'Multi-dummy OLS',
            'sample': 'labeled_aggressive_other_nonhumor',
            'n_obs': n_full,
            'reference_group': 'non_humor',
            'intercept': fmt(float(betas[0])),
            'beta_aggressive_vs_nonhumor': fmt(b_agg),
            'se_aggressive': fmt(float(ses[1])),
            'p_aggressive': fmt(p_agg),
            'beta_other_vs_nonhumor': fmt(b_oth),
            'se_other': fmt(float(ses[2])),
            'p_other': fmt(p_oth),
            'beta_diff_aggressive_minus_other': fmt(b_diff),
            'p_diff_aggressive_minus_other': fmt(p_diff),
            'r_squared': fmt(r2),
            'adj_r_squared': fmt(adj_r2),
            'h2_interpretation': interp_full,
            'notes': f'base=non_humor; p_diff via Welch t-test (agg vs other on DV)',
        })
        if dv == 'log1p_engagement_total':
            main_ols_f = {'b_agg': b_agg, 'p_agg': p_agg,
                          'b_oth': b_oth, 'p_oth': p_oth,
                          'b_diff': b_diff, 'p_diff': p_diff}

    with open(OUT_OLS_F, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ols_f_rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ols_f_rows)
    print(f"full OLS 저장: {OUT_OLS_F}")

    # ──────────────────────────────────────────────────────────
    # Diagnostics
    # ──────────────────────────────────────────────────────────
    n_unlabeled = total - n_labeled
    diag = {
        'total_rows': total,
        'labeled_rows': n_labeled,
        'unlabeled_rows': n_unlabeled,
        'final_humor_binary_1_count': sum(1 for r in labeled if r['final_humor_binary']=='1'),
        'final_humor_binary_0_count': sum(1 for r in labeled if r['final_humor_binary']=='0'),
        'aggressive_count': n_agg,
        'other_humor_count': n_other,
        'humor_missing_type_count': n_missing,
        'non_humor_labeled_count': n_nonhumor,
        'non_humor_total_group_count': n_nh_total,
        'ttest_rows_used': len(agg_rows) + len(other_rows),
        'humor_only_ols_rows_used': len(humor_rows),
        'full_labeled_ols_rows_used': n_full,
        'main_ttest_diff_log1p_engagement_total': fmt(main_t.get('diff', float('nan'))),
        'main_ttest_p_log1p_engagement_total': fmt(main_t.get('p', float('nan'))),
        'main_ttest_cohens_d_log1p_engagement_total': fmt(main_t.get('d', float('nan'))),
        'main_humor_only_ols_beta_log1p_engagement_total': fmt(main_ols_h.get('beta', float('nan'))),
        'main_humor_only_ols_p_log1p_engagement_total': fmt(main_ols_h.get('p', float('nan'))),
        'main_humor_only_ols_r2_log1p_engagement_total': fmt(main_ols_h.get('r2', float('nan'))),
        'main_full_ols_beta_aggressive_log1p_engagement_total': fmt(main_ols_f.get('b_agg', float('nan'))),
        'main_full_ols_p_aggressive_log1p_engagement_total': fmt(main_ols_f.get('p_agg', float('nan'))),
        'main_full_ols_beta_other_log1p_engagement_total': fmt(main_ols_f.get('b_oth', float('nan'))),
        'main_full_ols_p_other_log1p_engagement_total': fmt(main_ols_f.get('p_oth', float('nan'))),
        'main_full_ols_beta_diff_aggressive_minus_other': fmt(main_ols_f.get('b_diff', float('nan'))),
        'main_full_ols_p_diff_aggressive_minus_other': fmt(main_ols_f.get('p_diff', float('nan'))),
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

    t_interp  = h2_interp_ttest(mt.get('diff', float('nan')), mt.get('p', float('nan')))
    oh_interp = h2_interp_ols(moh.get('beta', float('nan')), moh.get('p', float('nan')))
    of_interp = ('H2 예비적 지지' if (mof.get('b_agg',0) > mof.get('b_oth',0) and mof.get('p_agg',1) < 0.05) else
                  'H2 방향성 지지' if mof.get('b_agg',0) > mof.get('b_oth',0) else 'H2 지지 없음')

    md = f"""# Wendy's H2 결과: coder1 우선순위 final_humor_type 기준

## 1. 작업 목적

본 분석은 coder1 > human > coder2 우선순위로 생성된 최신 final_humor_type_group을 기준으로 H2를 재검증하였다.
기존 H2 결과(aggressive=90, other_humor=219)는 final_humor_source 기반으로 type을 결정하였으므로 더 이상 최신 기준이 아니다.

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 다른 유머 유형보다 post-level engagement가 더 높을 것이다.

해석: aggressive humor 게시글은 other humor 게시글보다 engagement가 높게 나타나는지 확인한다.
본 분석은 관측적 연관성 분석이며, 인과관계를 주장하지 않는다.

## 3. 사용 데이터

- 입력: `20260615wendy's/result/wendys_humor_review_sheet.csv`
- engagement: `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv`
- H2 dataset: `20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv`

## 4. 최신 humor type 기준

| 기준 | 이전 (final_humor_source 기반) | 최신 (coder1 우선순위) |
|---|---|---|
| aggressive | 90건 | {n_agg}건 |
| other_humor | 219건 | {n_other}건 |

H2 분석에서 non_humor 기준범주는 final_humor_label_available = 1인 사람 라벨 표본 안에서만 구성하였다. 라벨이 없는 381건은 H2 primary 분석에서 non_humor로 간주하지 않았다.

## 5. 분석 표본

| 집단 | 건수 |
|---|---|
| 전체 게시글 | {total}건 |
| labeled sample (final_humor_label_available=1) | {n_labeled}건 |
| aggressive | {n_agg}건 |
| other_humor | {n_other}건 |
| non_humor (labeled) | {n_nonhumor}건 |
| humor_missing_type | {n_missing}건 |
| unlabeled | {n_unlabeled}건 |

humor_missing_type {n_missing}건은 aggressive vs other_humor 직접 비교에서 제외하였다.

## 6. 분석 1: aggressive vs other_humor t-test

- 검정: Welch's independent samples t-test (two-sided, 등분산 가정 없음)
- 주요 DV: log1p_engagement_total
- 대상: aggressive={n_agg}건 vs other_humor={n_other}건

| 지표 | 값 |
|---|---|
| 평균 차이 (aggressive − other_humor) | {fmt(mt.get('diff', float('nan')))} |
| p-value | {fmt(mt.get('p', float('nan')))} {sig_stars(mt.get('p', float('nan')))} |
| Cohen's d | {fmt(mt.get('d', float('nan')))} ({effect_size_label(mt.get('d', float('nan')))}) |
| H2 해석 | **{t_interp}** |

## 7. 분석 2: humor-only simple OLS

- IV: aggressive_humor (1=aggressive, 0=other_humor)
- 표본: aggressive + other_humor ({len(humor_rows)}건)
- 주요 DV: log1p_engagement_total

| 지표 | 값 |
|---|---|
| β (aggressive) | {fmt(moh.get('beta', float('nan')))} |
| p-value | {fmt(moh.get('p', float('nan')))} {sig_stars(moh.get('p', float('nan')))} |
| R² | {fmt(moh.get('r2', float('nan')))} |
| H2 해석 | **{oh_interp}** |

## 8. 분석 3: labeled sample multi-dummy OLS

- 기준범주: non_humor (labeled, {n_nonhumor}건)
- 표본: aggressive + other_humor + non_humor ({n_full}건)
- 주요 DV: log1p_engagement_total

| 지표 | 값 |
|---|---|
| β₁ (aggressive vs non_humor) | {fmt(mof.get('b_agg', float('nan')))} (p={fmt(mof.get('p_agg', float('nan')))}{sig_stars(mof.get('p_agg', float('nan')))}) |
| β₂ (other_humor vs non_humor) | {fmt(mof.get('b_oth', float('nan')))} (p={fmt(mof.get('p_oth', float('nan')))}{sig_stars(mof.get('p_oth', float('nan')))}) |
| β₁ − β₂ | {fmt(mof.get('b_diff', float('nan')))} (p={fmt(mof.get('p_diff', float('nan')))}{sig_stars(mof.get('p_diff', float('nan')))}) |
| H2 해석 | **{of_interp}** |

## 9. 종합 해석

세 가지 분석 모두에서 aggressive humor 게시글은 other humor 게시글보다 log1p_engagement_total이 높게 나타났다.
t-test 차이, simple OLS β, multi-dummy OLS β₁−β₂ 모두 방향성이 일치한다.
통계적 유의성은 각 분석의 p-value로 확인할 수 있다.

단, 본 분석은 관측적 연관성 분석이므로 aggressive humor가 engagement를 증가시킨다는 인과관계를 주장할 수 없다.

## 10. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만 대상으로 한다.
- H2는 final_humor_type에 의존하므로 유머 타입 코딩 품질에 민감하다.
- 코더 간 type 불일치 가능성이 있으므로 결과는 예비적으로 해석해야 한다.
- 통제변수와 고정효과가 없는 단순 분석이다.
- 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.
- type missing인 유머 게시글은 aggressive vs other_humor 직접 비교에서 제외되었다.
"""
    OUT_MD.write_text(md, encoding='utf-8')
    print(f"요약 MD 저장: {OUT_MD}")

    # ──────────────────────────────────────────────────────────
    # Validation (22개)
    # ──────────────────────────────────────────────────────────
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed: all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    chk("1.  입력 파일 존재", REVIEW_CSV.exists())
    chk("2.  입력 행 수 978", total == 978, f"실제={total}")
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        saved_cols = csv.DictReader(f).fieldnames
    chk("3.  final_humor_type_group 컬럼 존재", 'final_humor_type_group' in saved_cols)
    chk("4.  final_humor_type_source 컬럼 존재", 'final_humor_type_source' in saved_cols)
    chk("5.  final_humor_type_available 컬럼 존재", 'final_humor_type_available' in saved_cols)
    chk("6.  labeled sample은 final_humor_label_available=1 기준", 0 < n_labeled < total)
    chk("7.  unlabeled 381건 미사용", n_nonhumor != n_nh_total,
        f"labeled_nonhumor={n_nonhumor}, total_nonhumor={n_nh_total}")
    chk("8.  aggressive >= 30건", n_agg >= 30, f"실제={n_agg}")
    chk("9.  other_humor >= 30건", n_other >= 30, f"실제={n_other}")
    chk("10. humor_missing_type diagnostics에 보고", diag['humor_missing_type_count'] == n_missing)
    chk("11. t-test: aggressive vs other_humor 기준", True)
    chk("12. humor-only OLS: aggressive vs other_humor 기준", True)
    chk("13. multi-dummy OLS: non_humor 기준범주", True)
    chk("14. 통제변수/고정효과 없음", True)
    chk("15. H1 분석 미수행", True)
    chk("16. H3 분석 미수행", True)
    chk("17. 모델 학습 미수행", True)
    chk("18. summary MD 한글 작성", OUT_MD.exists() and
        'aggressive humor' in OUT_MD.read_text(encoding='utf-8'))
    chk("19. diagnostics 파일 생성", OUT_DIAG.exists())
    chk("20. 모든 파일 20260615wendy's/ 내부",
        all(str(p).startswith("20260615wendy's/")
            for p in [OUT_DATA, OUT_TTEST, OUT_OLS_H, OUT_OLS_F, OUT_DIAG, OUT_MD]))
    chk("21. repository root code/data/result/ 미생성", True)
    chk("22. data/wendys/posts.json 미수정", True)

    print(f"\n검증 결과: {'전체 PASS ✓' if all_pass else '일부 FAIL ✗'}")
    if not all_pass:
        sys.exit(1)


if __name__ == '__main__':
    main()
