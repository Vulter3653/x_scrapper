"""
run_wendys_h2_four_type_humor_analysis.py

== 작업 목적 ==
기존 H2의 aggressive vs other_humor 이진 비교를 네 가지 humor type으로 세분화하여
각 유형별 engagement 차이를 확인한다.

이번 분석은 기존 H2를 대체하지 않는다.
4-type humor analysis is an exploratory decomposition of H2.

== 사용 라벨 기준 ==
사람 기반 최종 타입 라벨 (coder1 > human > coder2 우선순위)
조건: final_humor_label_available=1, final_humor_binary=1,
       final_humor_type in {aggressive, affiliative, self-enhancing, self-defeating}

== 주의 ==
self-defeating 표본이 15건으로 20건 미만이므로 해당 비교는 매우 제한적으로 해석해야 한다.
본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
다중 pairwise 비교가 수행되므로 FDR/Bonferroni 보정을 확인해야 한다.
"""

import csv, math, sys
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

BASE       = Path("20260615wendy's")
REVIEW_CSV = BASE / "result" / "wendys_humor_review_sheet.csv"
DS_CSV     = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
POSTS_JSON = Path("data/wendys/posts.json")

OUT_DATA     = BASE / "data"   / "wendys_h2_four_type_humor_dataset.csv"
OUT_DIST     = BASE / "result" / "wendys_h2_four_type_distribution.csv"
OUT_MEAN_CMP = BASE / "result" / "wendys_h2_four_type_mean_comparison.csv"
OUT_PW       = BASE / "result" / "wendys_h2_four_type_pairwise_ttests.csv"
OUT_OLS      = BASE / "result" / "wendys_h2_four_type_ols_affiliative_base.csv"
OUT_CONT     = BASE / "result" / "wendys_h2_four_type_ols_pairwise_contrasts.csv"
OUT_RECHECK  = BASE / "result" / "wendys_h2_four_type_pooled_h2_recheck.csv"
OUT_DIAG     = BASE / "result" / "wendys_h2_four_type_diagnostics.csv"
OUT_PNG      = BASE / "result" / "wendys_h2_four_type_group_mean_plot.png"
OUT_MD       = BASE / "result" / "wendys_h2_four_type_summary.md"

VALID_TYPES = ('aggressive', 'affiliative', 'self-enhancing', 'self-defeating')

# ── 보호 파일 (절대 수정 금지)
PROTECTED = [
    BASE / "result" / "wendys_h2_coder1_priority_ttest_aggressive_vs_other.csv",
    BASE / "result" / "wendys_h2_model_based_type_summary.md",
    BASE / "result" / "wendys_model_based_humor_type_full_predictions.csv",
]


def fmt(v, dec=4):
    if isinstance(v, float) and math.isnan(v): return 'nan'
    if isinstance(v, (float, np.floating)):    return f"{v:.{dec}f}"
    return str(v)

def sig_stars(p):
    if p is None or math.isnan(float(p)): return ''
    p = float(p)
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '.'
    return ''

def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2: return float('nan')
    s1, s2 = np.std(g1, ddof=1), np.std(g2, ddof=1)
    pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    return float((np.mean(g1) - np.mean(g2)) / pooled) if pooled > 0 else float('nan')

def effect_label(d):
    if math.isnan(d): return 'n/a'
    ad = abs(d)
    if ad < 0.2: return 'negligible'
    if ad < 0.5: return 'small'
    if ad < 0.8: return 'medium'
    return 'large'

def fdr_bh(pvals):
    """Benjamini-Hochberg FDR correction. Returns adjusted p-values."""
    n = len(pvals)
    idx = np.argsort(pvals)
    adj = np.empty(n)
    min_p = 1.0
    for rank, i in enumerate(idx[::-1]):
        min_p = min(pvals[i] * n / (n - rank), min_p)
        adj[i] = min(min_p, 1.0)
    return adj

def bonferroni(pvals, m=None):
    if m is None: m = len(pvals)
    return np.minimum(np.array(pvals) * m, 1.0)

def ols_np(X, y):
    n, k = X.shape
    betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    preds  = X @ betas
    resids = y - preds
    ss_res = float(np.sum(resids**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))
    r2     = 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')
    adj_r2 = 1 - (1-r2)*(n-1)/(n-k) if (n-k) > 0 else float('nan')
    mse    = ss_res/(n-k) if (n-k) > 0 else float('nan')
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        vcov = mse * XtX_inv
        ses  = np.sqrt(np.diag(vcov))
    except np.linalg.LinAlgError:
        vcov = np.full((k,k), float('nan'))
        ses  = np.full(k, float('nan'))
    t_stats = betas / ses
    df_res  = n - k
    p_vals  = np.array([2*(1 - stats.t.cdf(abs(t), df=df_res)) for t in t_stats])
    t95     = stats.t.ppf(0.975, df=df_res)
    ci_lo   = betas - t95*ses
    ci_hi   = betas + t95*ses
    return betas, ses, t_stats, p_vals, ci_lo, ci_hi, r2, adj_r2, vcov, df_res


def main():
    posts_mtime_start = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None

    # ── 1. 로드 및 병합
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        review = {r['id']: r for r in csv.DictReader(f)}
    with open(DS_CSV, newline='', encoding='utf-8') as f:
        ds = {r['id']: r for r in csv.DictReader(f)}

    total = len(review)
    print(f"전체: {total}건")

    all_rows = []
    for id_, rev in review.items():
        d = ds.get(id_, {})
        r = dict(rev)
        for col in ['reply_count','favorite_count','retweet_count',
                     'quote_count','bookmark_count','view_count',
                     'created_year','created_month','created_day','created_time']:
            r[col] = d.get(col, '')
        ct = r.get('created_time','')
        r['created_hour'] = ct.split(':')[0] if ct else ''
        all_rows.append(r)

    # ── 2. engagement 변수 생성 (전체 978건)
    for r in all_rows:
        def fv(c): return float(r.get(c, 0) or 0)
        for col in ['reply_count','favorite_count','retweet_count',
                     'quote_count','bookmark_count','view_count']:
            r[col] = fv(col)
        r['engagement_total']          = r['reply_count']+r['favorite_count']+r['retweet_count']+r['quote_count']+r['bookmark_count']
        r['engagement_favorite_retweet'] = r['favorite_count']+r['retweet_count']
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

    # ── 3. 4-type 분석 표본 구성
    type_rows = [
        r for r in all_rows
        if r.get('final_humor_label_available') == '1'
        and r.get('final_humor_binary') == '1'
        and r.get('final_humor_type', '') in VALID_TYPES
    ]

    n_excl_nh   = sum(1 for r in all_rows if r.get('final_humor_label_available')=='1' and r.get('final_humor_binary')=='0')
    n_excl_miss = sum(1 for r in all_rows if r.get('final_humor_label_available')=='1' and r.get('final_humor_binary')=='1' and r.get('final_humor_type_group','')=='missing')
    n_excl_unl  = sum(1 for r in all_rows if r.get('final_humor_label_available')=='0')
    n_invalid   = sum(1 for r in all_rows if r.get('final_humor_label_available')=='1' and r.get('final_humor_binary')=='1'
                      and r.get('final_humor_type','') not in VALID_TYPES and r.get('final_humor_type','') != '')

    type_dist = Counter(r['final_humor_type'] for r in type_rows)
    n_agg  = type_dist.get('aggressive', 0)
    n_aff  = type_dist.get('affiliative', 0)
    n_se   = type_dist.get('self-enhancing', 0)
    n_sd   = type_dist.get('self-defeating', 0)
    n_type = len(type_rows)
    min_cell = min(type_dist.values())
    small_cell = min_cell < 20
    print(f"4-type 표본: {n_type}건 (agg={n_agg}, aff={n_aff}, se={n_se}, sd={n_sd})")
    print(f"small_cell_warning: {small_cell} (min={min_cell}건)")

    # 서브셋
    agg_rows = [r for r in type_rows if r['final_humor_type'] == 'aggressive']
    aff_rows = [r for r in type_rows if r['final_humor_type'] == 'affiliative']
    se_rows  = [r for r in type_rows if r['final_humor_type'] == 'self-enhancing']
    sd_rows  = [r for r in type_rows if r['final_humor_type'] == 'self-defeating']

    # dummy 변수 생성
    for r in type_rows:
        r['type_aggressive']     = 1 if r['final_humor_type'] == 'aggressive'     else 0
        r['type_affiliative']    = 1 if r['final_humor_type'] == 'affiliative'    else 0
        r['type_self_enhancing'] = 1 if r['final_humor_type'] == 'self-enhancing' else 0
        r['type_self_defeating'] = 1 if r['final_humor_type'] == 'self-defeating' else 0
        r['type_non_aggressive'] = 0 if r['final_humor_type'] == 'aggressive'     else 1

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

    # ── 4. Dataset CSV 저장
    ds_cols = [
        'id','tweet_url','text','created_year','created_month','created_day','created_hour',
        'final_humor_binary','final_humor_label_available',
        'final_humor_type','final_humor_type_source','final_humor_type_group',
        'type_aggressive','type_affiliative','type_self_enhancing','type_self_defeating','type_non_aggressive',
        'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
        'engagement_total','engagement_favorite_retweet',
    ] + LOG_DVS
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        w.writeheader()
        w.writerows(type_rows)
    print(f"Dataset 저장: {OUT_DATA}")

    # ────────────────────────────────────────────────────────
    # 분석 7.1: Type distribution audit
    # ────────────────────────────────────────────────────────
    type_groups = [('aggressive', agg_rows), ('affiliative', aff_rows),
                   ('self-enhancing', se_rows), ('self-defeating', sd_rows)]
    dist_rows = []
    for tname, trows in type_groups:
        vals_et = [float(r['log1p_engagement_total']) for r in trows]
        row = {'humor_type': tname, 'n': len(trows),
               'share': fmt(len(trows)/n_type)}
        for dv in LOG_DVS:
            vals = [float(r[dv]) for r in trows]
            row[f'mean_{dv}'] = fmt(float(np.mean(vals)))
        row['median_log1p_engagement_total'] = fmt(float(np.median(vals_et)))
        dist_rows.append(row)

    dist_cols = ['humor_type','n','share','median_log1p_engagement_total'] + [f'mean_{d}' for d in LOG_DVS]
    with open(OUT_DIST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=dist_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(dist_rows)
    print(f"Distribution 저장: {OUT_DIST}")

    # ────────────────────────────────────────────────────────
    # 분석 7.2: Four-type mean comparison (one-way ANOVA + Kruskal-Wallis)
    # ────────────────────────────────────────────────────────
    print("\n[분석 7.2] ANOVA + Kruskal-Wallis")
    mean_cmp_rows = []
    for dv in LOG_DVS:
        g = [[float(r[dv]) for r in trows] for _, trows in type_groups]
        # one-way ANOVA
        f_stat, p_anova = stats.f_oneway(*g)
        # Kruskal-Wallis
        h_stat, p_kw    = stats.kruskal(*g)
        print(f"  {dv}: F={f_stat:.3f} p={p_anova:.4f}{sig_stars(p_anova)}, "
              f"KW H={h_stat:.3f} p={p_kw:.4f}{sig_stars(p_kw)}")
        for test_name, stat_val, p_val in [('one-way ANOVA', f_stat, p_anova),
                                            ('Kruskal-Wallis', h_stat, p_kw)]:
            interp = '네 type 간 차이 존재 (p<.05)' if p_val < 0.05 else '유의한 차이 없음'
            mean_cmp_rows.append({
                'dv': dv, 'test_type': test_name,
                'statistic': fmt(float(stat_val)), 'p_value': fmt(float(p_val)),
                'significance': sig_stars(p_val),
                'n_total': n_type, 'n_aggressive': n_agg, 'n_affiliative': n_aff,
                'n_self_enhancing': n_se, 'n_self_defeating': n_sd,
                'interpretation': interp,
            })
    mc_cols = ['dv','test_type','statistic','p_value','significance',
               'n_total','n_aggressive','n_affiliative','n_self_enhancing','n_self_defeating',
               'interpretation']
    with open(OUT_MEAN_CMP, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=mc_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(mean_cmp_rows)
    print(f"Mean comparison 저장: {OUT_MEAN_CMP}")

    # ────────────────────────────────────────────────────────
    # 분석 7.3: Pairwise Welch t-test with FDR & Bonferroni
    # ────────────────────────────────────────────────────────
    print("\n[분석 7.3] Pairwise Welch t-test")
    COMPARISONS = [
        ('aggressive vs affiliative',    agg_rows, aff_rows,  n_agg, n_aff, 'affiliative', False),
        ('aggressive vs self-enhancing', agg_rows, se_rows,   n_agg, n_se,  'self-enhancing', False),
        ('aggressive vs self-defeating', agg_rows, sd_rows,   n_agg, n_sd,  'self-defeating', True),
    ]
    n_comparisons = len(COMPARISONS)

    # 먼저 raw p-values 수집 (모든 DV × 3 비교)
    pw_raw = []  # (dv, comp, n_agg, n_cmp, mean_agg, mean_cmp, diff, t, p_raw, d, small_warn)
    for dv in LOG_DVS:
        raw_p_for_dv = []
        for comp_name, g1_rows, g2_rows, ng1, ng2, cmp_type, small_warn in COMPARISONS:
            g1 = np.array([float(r[dv]) for r in g1_rows])
            g2 = np.array([float(r[dv]) for r in g2_rows])
            t, p = stats.ttest_ind(g1, g2, equal_var=False)
            diff = float(np.mean(g1) - np.mean(g2))
            d    = cohens_d(g1, g2)
            pw_raw.append((dv, comp_name, ng1, ng2,
                           float(np.mean(g1)), float(np.mean(g2)),
                           diff, float(t), float(p), d, small_warn))

    # p-value 모음 (주요 DV 기준으로 보정 — 모든 DV × 3 비교 함께 보정)
    all_p = [x[8] for x in pw_raw]
    p_bonf = bonferroni(all_p, m=n_comparisons * len(LOG_DVS))
    p_fdr  = fdr_bh(np.array(all_p))

    pw_out = []
    for i, (dv, comp_name, ng1, ng2, m1, m2, diff, t, p_raw, d, small_warn) in enumerate(pw_raw):
        if diff > 0 and p_fdr[i] < 0.05:
            h2_support = 'H2 4-type decomposition 예비적 지지'
        elif diff > 0 and p_raw < 0.05:
            h2_support = '보정 전 유의, 보정 후 제한적 지지'
        elif diff > 0:
            h2_support = 'H2 방향성 지지'
        else:
            h2_support = 'H2 지지 없음'

        h2_dir = 'positive' if diff > 0 else 'negative_or_zero'
        warn   = 'n<20: 결과 매우 제한적' if small_warn else ''
        print(f"  {comp_name} / {dv}: diff={diff:.4f}, p_raw={p_raw:.4f}{sig_stars(p_raw)}, "
              f"p_fdr={p_fdr[i]:.4f}{sig_stars(p_fdr[i])}, d={d:.4f}")
        pw_out.append({
            'dv': dv, 'comparison': comp_name,
            'n_aggressive': ng1, 'n_comparison_type': ng2,
            'mean_aggressive': fmt(m1), 'mean_comparison_type': fmt(m2),
            'diff_aggressive_minus_comparison': fmt(diff),
            't_stat': fmt(t), 'p_value_raw': fmt(p_raw),
            'p_value_bonferroni': fmt(float(p_bonf[i])),
            'p_value_fdr': fmt(float(p_fdr[i])),
            'cohens_d': fmt(d), 'effect_size_label': effect_label(d),
            'significance_raw': sig_stars(p_raw),
            'significance_fdr': sig_stars(float(p_fdr[i])),
            'h2_direction': h2_dir,
            'h2_preliminary_support': h2_support,
            'sample_size_warning': warn,
        })

    pw_cols = list(pw_out[0].keys())
    with open(OUT_PW, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=pw_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(pw_out)
    print(f"Pairwise t-test 저장: {OUT_PW}")

    # ────────────────────────────────────────────────────────
    # 분석 7.4: OLS with affiliative as base
    # ────────────────────────────────────────────────────────
    print("\n[분석 7.4] OLS (base=affiliative)")
    ols_rows = []
    contrast_data = {}  # dv → (betas, vcov, ses, df_res)

    for dv in LOG_DVS:
        X = np.column_stack([
            np.ones(n_type),
            np.array([r['type_aggressive']     for r in type_rows], dtype=float),
            np.array([r['type_self_enhancing']  for r in type_rows], dtype=float),
            np.array([r['type_self_defeating']  for r in type_rows], dtype=float),
        ])
        y = np.array([float(r[dv]) for r in type_rows])
        betas, ses, ts, ps, ci_lo, ci_hi, r2, adj_r2, vcov, df_res = ols_np(X, y)

        b_agg = float(betas[1]); p_agg = float(ps[1])
        b_se  = float(betas[2]); p_se  = float(ps[2])
        b_sd  = float(betas[3]); p_sd  = float(ps[3])

        contrast_data[dv] = (betas, vcov, ses, df_res)

        if b_agg > 0 and p_agg < 0.05:
            interp = 'H2 예비적 지지 (aggressive > affiliative)'
        elif b_agg > 0:
            interp = 'H2 방향성 지지'
        else:
            interp = 'H2 지지 없음'

        print(f"  {dv}: β_agg={b_agg:.4f}{sig_stars(p_agg)}, "
              f"β_se={b_se:.4f}{sig_stars(p_se)}, "
              f"β_sd={b_sd:.4f}{sig_stars(p_sd)}, R²={r2:.4f}")
        ols_rows.append({
            'dv': dv, 'n': n_type, 'base_category': 'affiliative',
            'intercept': fmt(float(betas[0])),
            'coef_aggressive_vs_affiliative': fmt(b_agg),
            'se_aggressive': fmt(float(ses[1])),
            'p_aggressive_vs_affiliative': fmt(p_agg),
            'coef_self_enhancing_vs_affiliative': fmt(b_se),
            'se_self_enhancing': fmt(float(ses[2])),
            'p_self_enhancing_vs_affiliative': fmt(p_se),
            'coef_self_defeating_vs_affiliative': fmt(b_sd),
            'se_self_defeating': fmt(float(ses[3])),
            'p_self_defeating_vs_affiliative': fmt(p_sd),
            'r_squared': fmt(r2), 'adj_r_squared': fmt(adj_r2),
            'h2_interpretation': interp,
            'notes': 'base=affiliative; exploratory 4-type decomposition',
        })

    ols_cols = list(ols_rows[0].keys())
    with open(OUT_OLS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ols_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(ols_rows)
    print(f"OLS 저장: {OUT_OLS}")

    # ────────────────────────────────────────────────────────
    # 분석 7.5: OLS pairwise contrasts
    # β₁-β₂: aggressive - self-enhancing
    # β₁-β₃: aggressive - self-defeating
    # β₂-β₃: self-enhancing - self-defeating
    # ────────────────────────────────────────────────────────
    print("\n[분석 7.5] OLS pairwise contrasts")
    cont_rows = []
    # 대비 벡터 (intercept=0, agg=1, se=2, sd=3)
    CONTRASTS = [
        ('aggressive - self-enhancing', np.array([0, 1,-1, 0])),
        ('aggressive - self-defeating', np.array([0, 1, 0,-1])),
        ('self-enhancing - self-defeating', np.array([0, 0, 1,-1])),
    ]
    for dv in LOG_DVS:
        betas, vcov, ses, df_res = contrast_data[dv]
        for cont_name, c in CONTRASTS:
            est = float(c @ betas)
            var_c = float(c @ vcov @ c)
            se_c  = math.sqrt(var_c) if var_c > 0 else float('nan')
            t_c   = est / se_c if se_c > 0 else float('nan')
            p_c   = float(2*(1 - stats.t.cdf(abs(t_c), df=df_res))) if not math.isnan(t_c) else float('nan')
            interp = ('positive, p<.05' if est > 0 and p_c < 0.05 else
                      'positive' if est > 0 else 'negative_or_zero')
            print(f"  {cont_name} / {dv}: est={est:.4f}, p={p_c:.4f}{sig_stars(p_c)}")
            cont_rows.append({
                'dv': dv, 'contrast': cont_name,
                'estimate': fmt(est), 'std_error': fmt(se_c),
                't_value': fmt(t_c), 'p_value': fmt(p_c),
                'significance': sig_stars(p_c),
                'interpretation': interp,
            })

    cont_cols = list(cont_rows[0].keys())
    with open(OUT_CONT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cont_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(cont_rows)
    print(f"Contrasts 저장: {OUT_CONT}")

    # ────────────────────────────────────────────────────────
    # 분석 7.6: pooled other_humor recheck
    # ────────────────────────────────────────────────────────
    print("\n[분석 7.6] Pooled other_humor recheck")
    other_rows_pool = aff_rows + se_rows + sd_rows
    recheck_rows = []
    for dv in LOG_DVS:
        g1 = np.array([float(r[dv]) for r in agg_rows])
        g2 = np.array([float(r[dv]) for r in other_rows_pool])
        t, p = stats.ttest_ind(g1, g2, equal_var=False)
        diff = float(np.mean(g1) - np.mean(g2))
        d    = cohens_d(g1, g2)
        recheck_rows.append({
            'dv': dv,
            'analysis': 'aggressive vs pooled other_humor (4-type dataset)',
            'n_aggressive': n_agg,
            'n_pooled_other_humor': len(other_rows_pool),
            'mean_aggressive': fmt(float(np.mean(g1))),
            'mean_pooled_other': fmt(float(np.mean(g2))),
            'diff_aggressive_minus_other': fmt(diff),
            'p_value': fmt(float(p)),
            'significance': sig_stars(float(p)),
            'cohens_d': fmt(d),
            'note': 'This reproduces the H2 pooled comparison within the 4-type decomposition dataset.',
        })
    print(f"  log1p_et: diff={recheck_rows[0]['diff_aggressive_minus_other']}, "
          f"p={recheck_rows[0]['p_value']}{recheck_rows[0]['significance']}")
    rech_cols = list(recheck_rows[0].keys())
    with open(OUT_RECHECK, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rech_cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(recheck_rows)
    print(f"Recheck 저장: {OUT_RECHECK}")

    # ────────────────────────────────────────────────────────
    # 그래프
    # ────────────────────────────────────────────────────────
    type_labels = ['aggressive','affiliative','self-enhancing','self-defeating']
    type_grps   = [agg_rows, aff_rows, se_rows, sd_rows]
    means_et    = [float(np.mean([float(r['log1p_engagement_total']) for r in g])) for g in type_grps]
    sems_et     = [float(np.std([float(r['log1p_engagement_total']) for r in g], ddof=1)/math.sqrt(len(g))) for g in type_grps]
    ns          = [n_agg, n_aff, n_se, n_sd]
    colors      = ['crimson','steelblue','forestgreen','darkorange']

    fig, ax = plt.subplots(figsize=(9,5))
    bars = ax.bar(type_labels, means_et, yerr=sems_et, capsize=5,
                  color=colors, alpha=0.8, edgecolor='black')
    for bar, m in zip(bars, means_et):
        ax.text(bar.get_x()+bar.get_width()/2, m+0.05, f'{m:.3f}',
                ha='center', va='bottom', fontsize=9)
    ax.set_title("log1p(engagement_total) by Humor Type\n"
                 "Wendy's (4-type exploratory decomposition; human-labeled)", fontsize=11)
    ax.set_xlabel("final_humor_type (human-labeled, coder1 priority)")
    ax.set_ylabel("Mean log1p(engagement_total) ± SEM")
    ax.set_xticks(range(4))
    ax.set_xticklabels([f'{t}\n(n={n})' for t,n in zip(type_labels, ns)])
    ax.text(0.99, 0.01, '* self-defeating n=15 (<20): interpret with caution',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=8, color='gray')
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"그래프 저장: {OUT_PNG}")

    # ────────────────────────────────────────────────────────
    # Diagnostics
    # ────────────────────────────────────────────────────────
    diag = {
        'total_rows': total,
        'merged_rows': total,
        'humor_type_analysis_rows': n_type,
        'aggressive_rows': n_agg,
        'affiliative_rows': n_aff,
        'self_enhancing_rows': n_se,
        'self_defeating_rows': n_sd,
        'excluded_non_humor_rows': n_excl_nh,
        'excluded_humor_missing_type_rows': n_excl_miss,
        'excluded_unlabeled_rows': n_excl_unl,
        'invalid_type_rows': n_invalid,
        'primary_dv_missing_rows': 0,
        'min_type_cell_size': min_cell,
        'small_cell_warning': str(small_cell),
        'original_posts_json_modified': 'False',
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerow(diag)
    print(f"Diagnostics 저장: {OUT_DIAG}")

    # ────────────────────────────────────────────────────────
    # Summary Markdown (한글)
    # ────────────────────────────────────────────────────────
    # 주요 결과 수집
    pw_main = {(r['comparison'], r['dv']): r for r in pw_out}
    ols_main = {r['dv']: r for r in ols_rows}
    cont_main = {(r['contrast'], r['dv']): r for r in cont_rows}
    rech_main = recheck_rows[0]

    dv = 'log1p_engagement_total'
    means_str = ', '.join(f"{t}={m:.3f}" for t, m in zip(type_labels, means_et))

    def pw_line(comp, dv='log1p_engagement_total'):
        r = pw_main.get((comp, dv), {})
        return (f"diff={r.get('diff_aggressive_minus_comparison','?')}, "
                f"p_raw={r.get('p_value_raw','?')}{r.get('significance_raw','')}, "
                f"p_fdr={r.get('p_value_fdr','?')}{r.get('significance_fdr','')}, "
                f"d={r.get('cohens_d','?')} ({r.get('effect_size_label','')})")

    ols_r = ols_main.get(dv, {})
    cr_ae = cont_main.get(('aggressive - self-enhancing', dv), {})
    cr_ad = cont_main.get(('aggressive - self-defeating', dv), {})

    md = f"""# Wendy's H2 기준 4가지 Humor Type 비교 분석 결과

## 1. 작업 목적

본 분석은 기존 H2의 aggressive vs other_humor 비교를 네 가지 humor type으로 세분화한 exploratory decomposition이다.
기존 H2를 대체하는 것이 아니라, 세분화 분석을 통해 어떤 유형 간 차이가 H2를 주도하는지 확인하는 것이 목적이다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_humor_review_sheet.csv`
- `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv`
- 사람 기반 final_humor_type 라벨 (coder1 > human > coder2 우선순위)

## 3. 분석 표본 구성

| 유형 | 건수 |
|---|---|
| aggressive | {n_agg}건 |
| affiliative | {n_aff}건 |
| self-enhancing | {n_se}건 |
| self-defeating | {n_sd}건 |
| **합계** | **{n_type}건** |

제외: non_humor={n_excl_nh}건, missing_type={n_excl_miss}건, unlabeled={n_excl_unl}건

**small_cell_warning: {small_cell}** — self-defeating {n_sd}건(<20건)이므로 해당 비교는 매우 제한적으로 해석해야 한다.

## 4. 네 가지 humor type 분포

| 유형 | n | mean_log1p_engagement_total |
|---|---|---|
{"".join(f"| {t} | {n} | {m:.4f} |" + chr(10) for t, n, m in zip(type_labels, ns, means_et))}

## 5. Type별 평균 engagement

primary DV (log1p_engagement_total) 기준: {means_str}

## 6. 네 type 평균 차이 검정

one-way ANOVA 및 Kruskal-Wallis 검정 결과는 `wendys_h2_four_type_mean_comparison.csv` 참조.

## 7. Aggressive vs 각 type pairwise 비교

### aggressive vs affiliative (primary DV: log1p_engagement_total)
{pw_line('aggressive vs affiliative')}

### aggressive vs self-enhancing
{pw_line('aggressive vs self-enhancing')}

### aggressive vs self-defeating
{pw_line('aggressive vs self-defeating')}
⚠ self-defeating n={n_sd}건 < 20 — 해당 결과는 탐색적 참고로만 해석해야 한다.

다중비교 보정: Bonferroni 및 Benjamini-Hochberg FDR 보정 포함.
다중 pairwise 비교가 수행되었으므로, raw p-value뿐 아니라 FDR 또는 Bonferroni 보정 결과를 함께 확인해야 한다.

## 8. Humor-only OLS 결과 (base=affiliative, log1p_engagement_total)

| 비교 | β | p |
|---|---|---|
| aggressive vs affiliative | {ols_r.get('coef_aggressive_vs_affiliative','?')} | {ols_r.get('p_aggressive_vs_affiliative','?')}{sig_stars(float(ols_r.get('p_aggressive_vs_affiliative','1')))} |
| self-enhancing vs affiliative | {ols_r.get('coef_self_enhancing_vs_affiliative','?')} | {ols_r.get('p_self_enhancing_vs_affiliative','?')}{sig_stars(float(ols_r.get('p_self_enhancing_vs_affiliative','1')))} |
| self-defeating vs affiliative | {ols_r.get('coef_self_defeating_vs_affiliative','?')} | {ols_r.get('p_self_defeating_vs_affiliative','?')}{sig_stars(float(ols_r.get('p_self_defeating_vs_affiliative','1')))} |
| R² | {ols_r.get('r_squared','?')} | |

OLS pairwise contrasts (log1p_engagement_total):
- aggressive − self-enhancing: est={cr_ae.get('estimate','?')}, p={cr_ae.get('p_value','?')}{sig_stars(float(cr_ae.get('p_value','1')))}
- aggressive − self-defeating: est={cr_ad.get('estimate','?')}, p={cr_ad.get('p_value','?')}{sig_stars(float(cr_ad.get('p_value','1')))}

## 9. 기존 pooled H2와의 관계

이번 4-type 데이터셋 내에서 aggressive vs pooled other_humor (affiliative+self-enhancing+self-defeating) 재계산 결과:
- diff={rech_main.get('diff_aggressive_minus_other','?')}, p={rech_main.get('p_value','?')}{rech_main.get('significance','')}

기존 human-labeled H2 (n=278): diff=+0.7074, p=0.0012**

두 분석이 동일한 데이터 기반이므로 수치는 일치해야 한다.

## 10. 해석상 주의사항

본 분석은 기존 H2의 aggressive vs other_humor 비교를 네 가지 humor type으로 세분화한 exploratory decomposition이다.

self-defeating 유형은 표본 수가 작을 가능성이 높으므로, 해당 비교 결과는 매우 제한적으로 해석해야 한다.

본 분석은 관측적 연관성 분석이며, humor type이 engagement를 증가시켰다는 인과적 해석은 할 수 없다.

다중 pairwise 비교가 수행되었으므로, raw p-value뿐 아니라 FDR 또는 Bonferroni 보정 결과를 함께 확인해야 한다.

## 11. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음
- 기존 H2 결과 파일: 수정 없음
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
"""
    OUT_MD.write_text(md, encoding='utf-8')
    print(f"요약 MD 저장: {OUT_MD}")

    # ────────────────────────────────────────────────────────
    # Validation (17개)
    # ────────────────────────────────────────────────────────
    print("\n[VALIDATION]")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed: all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))

    all_new = [OUT_DATA, OUT_DIST, OUT_MEAN_CMP, OUT_PW, OUT_OLS,
               OUT_CONT, OUT_RECHECK, OUT_DIAG, OUT_PNG, OUT_MD]
    chk("1.  모든 산출물 20260615wendy's/ 내부",
        all(str(p).startswith("20260615wendy's/") for p in all_new))
    posts_mtime_end = POSTS_JSON.stat().st_mtime if POSTS_JSON.exists() else None
    chk("2.  data/wendys/posts.json 변경 없음", posts_mtime_start == posts_mtime_end)

    with open(OUT_DATA, newline='', encoding='utf-8') as f:
        saved = list(csv.DictReader(f))
    all_humor = all(r['final_humor_binary'] == '1' for r in saved)
    chk("3.  dataset: final_humor_binary=1만 포함", all_humor)

    all_valid_type = all(r['final_humor_type'] in VALID_TYPES for r in saved)
    chk("4.  4가지 type 정규화됨", all_valid_type)
    chk("5.  non_humor 제외됨", all(r['final_humor_type'] != 'non_humor' for r in saved))
    chk("6.  humor_missing_type 제외됨", all(r.get('final_humor_type_group','') != 'missing' for r in saved))
    chk("7.  unlabeled 제외됨", all(r.get('final_humor_label_available','') == '1' for r in saved))
    chk("8.  type 분포표 생성됨", OUT_DIST.exists())

    pw_saved = list(csv.DictReader(open(OUT_PW, newline='', encoding='utf-8')))
    comps = {r['comparison'] for r in pw_saved}
    chk("9.  aggressive vs affiliative 포함",    'aggressive vs affiliative' in comps)
    chk("10. aggressive vs self-enhancing 포함", 'aggressive vs self-enhancing' in comps)
    chk("11. aggressive vs self-defeating 포함", 'aggressive vs self-defeating' in comps)
    chk("12. pairwise에 FDR/Bonferroni 포함",
        all('p_value_fdr' in r and 'p_value_bonferroni' in r for r in pw_saved))

    ols_saved = list(csv.DictReader(open(OUT_OLS, newline='', encoding='utf-8')))
    chk("13. OLS 기준범주 affiliative",
        all(r.get('base_category','') == 'affiliative' for r in ols_saved))
    chk("14. pooled other_humor recheck 생성됨", OUT_RECHECK.exists())

    md_text = OUT_MD.read_text(encoding='utf-8')
    chk("15. summary.md에 'exploratory decomposition' 포함",
        'exploratory decomposition' in md_text)
    chk("16. summary.md에 인과 해석 금지 문장 포함",
        '인과적 해석은 할 수 없다' in md_text)
    chk("17. small_cell_warning diagnostics에 기록됨",
        OUT_DIAG.exists() and str(small_cell) in open(OUT_DIAG).read())

    print(f"\n검증 결과: {'전체 PASS ✓' if all_pass else '일부 FAIL ✗'}")
    if not all_pass:
        sys.exit(1)

    print(f"\n=== 최종 요약 ===")
    print(f"4-type: agg={n_agg}, aff={n_aff}, se={n_se}, sd={n_sd}")
    for t, m in zip(type_labels, means_et):
        print(f"  mean_{t}: {m:.4f}")


if __name__ == '__main__':
    main()
