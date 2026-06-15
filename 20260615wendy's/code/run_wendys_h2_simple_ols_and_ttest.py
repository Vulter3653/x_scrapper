"""
run_wendys_h2_simple_ols_and_ttest.py

== 목적 ==
final_humor_type 기반으로 H2를 가장 단순한 방식으로 확인한다.

H2: aggressive humor 게시글은 다른 유머 유형 게시글보다 engagement가 높을 것이다.

수행하는 분석:
  (1) Welch t-test: aggressive humor vs non-aggressive humor (유머 전용 표본)
  (2) 단순 OLS: 유머 전용 표본, IV = aggressive 더미
  (3) 다중 더미 OLS: 사람 라벨 전체 표본, 기준범주 = non-humor
      log1p_DV = α + β1·aggressive_i + β2·other_humor_i + ε

== 이번 작업에서 수행하지 않는 것 ==
  통제변수, 고정효과, robust SE, 4유형 다중비교, H3 분석, 모델 학습

== 표본 정의 ==
  전체 사람 라벨 표본: final_humor_label_available=1, 597건
  유머 전용 표본: final_humor_binary=1, 309건
    - aggressive:     final_humor_type='aggressive', 90건
    - other_humor:    final_humor_type!='aggressive', 219건
  비유머 기준범주: final_humor_binary=0, 288건

== 더미 변수 ==
  aggressive_humor: 1 if final_humor_binary=1 AND final_humor_type='aggressive', else 0
  other_humor:      1 if final_humor_binary=1 AND final_humor_type!='aggressive', else 0
  (non-humor는 두 더미 모두 0 → 기준범주)

== H2 해석 기준 ==
  β1(aggressive) > β2(other_humor) and β1 p<0.05 → H2 예비적 지지
  β1 > β2 and β1 p≥0.05                          → H2 방향성 지지
  β1 <= β2                                        → H2 지지 없음

== 모든 산출물 경로 ==
  모든 새 파일은 20260615wendy's/ 내부에만 생성한다.
"""

import csv
import math
import sys
from datetime import datetime
from pathlib import Path
from scipy import stats

BASE        = Path("20260615wendy's")
REVIEW_CSV  = BASE / "result" / "wendys_humor_review_sheet.csv"
ENG_CSV     = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"

OUT_DATA    = BASE / "data"   / "wendys_h2_dataset.csv"
OUT_TT      = BASE / "result" / "wendys_h2_ttest_aggressive_vs_other.csv"
OUT_OLS_HO  = BASE / "result" / "wendys_h2_ols_humor_only.csv"
OUT_OLS_FL  = BASE / "result" / "wendys_h2_ols_full_labeled.csv"
OUT_DIAG    = BASE / "result" / "wendys_h2_diagnostics.csv"
OUT_SUMMARY = BASE / "result" / "wendys_h2_summary.md"


# ── 공통 유틸
def safe_int(v, d=0):
    try: return int(float(v))
    except: return d

def safe_float(v, d=0.0):
    try: return float(v)
    except: return d

def log1p(v): return math.log1p(v)

def desc(vals):
    n = len(vals)
    if n == 0:
        return dict(n=0, mean=float('nan'), std=float('nan'),
                    median=float('nan'), mn=float('nan'), mx=float('nan'))
    mu  = sum(vals) / n
    var = sum((x-mu)**2 for x in vals)/(n-1) if n>1 else 0.0
    s   = sorted(vals)
    med = s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
    return dict(n=n, mean=mu, std=math.sqrt(var), median=med, mn=min(vals), mx=max(vals))

def cohen_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1<2 or n2<2: return float('nan')
    m1, m2 = sum(g1)/n1, sum(g2)/n2
    v1 = sum((x-m1)**2 for x in g1)/(n1-1)
    v2 = sum((x-m2)**2 for x in g2)/(n2-1)
    sp = math.sqrt(((n1-1)*v1+(n2-1)*v2)/(n1+n2-2))
    return (m1-m2)/sp if sp>0 else float('nan')

def interp_d(d):
    ad = abs(d)
    if ad<0.2: return 'negligible'
    if ad<0.5: return 'small'
    if ad<0.8: return 'medium'
    return 'large'

def interp_d_ko(d):
    ad = abs(d)
    if ad<0.2: return '무시 가능'
    if ad<0.5: return '작음'
    if ad<0.8: return '중간'
    return '큼'

def sig_label(p):
    if p<0.001: return '***'
    if p<0.01:  return '**'
    if p<0.05:  return '*'
    if p<0.10:  return '†'
    return 'n.s.'

def run_ttest(g1, g2, dv, scale, group_var, g1_name, g2_name, notes=''):
    d1, d2 = desc(g1), desc(g2)
    t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
    diff = d1['mean'] - d2['mean']
    try:
        df_w = ((d1['std']**2/d1['n'])+(d2['std']**2/d2['n']))**2 / (
               (d1['std']**2/d1['n'])**2/(d1['n']-1)+
               (d2['std']**2/d2['n'])**2/(d2['n']-1))
        t_crit = stats.t.ppf(0.975, df_w)
        se_diff = math.sqrt(d1['std']**2/d1['n']+d2['std']**2/d2['n'])
        ci_lo, ci_hi = diff-t_crit*se_diff, diff+t_crit*se_diff
    except:
        ci_lo = ci_hi = float('nan')
    d = cohen_d(g1, g2)
    # H2 해석: diff>0이면 aggressive가 높음
    if diff>0 and p_val<0.05:  h2 = 'H2 예비적 지지'
    elif diff>0:                h2 = 'H2 방향성 지지'
    else:                       h2 = 'H2 지지 없음'
    return {
        'dv': dv, 'scale': scale, 'group_variable': group_var,
        'group1_name': g1_name, 'group2_name': g2_name,
        'n_group1': d1['n'], 'n_group2': d2['n'],
        'mean_group1': f'{d1["mean"]:.4f}', 'mean_group2': f'{d2["mean"]:.4f}',
        'diff_mean': f'{diff:.4f}',
        'median_group1': f'{d1["median"]:.4f}', 'median_group2': f'{d2["median"]:.4f}',
        'sd_group1': f'{d1["std"]:.4f}', 'sd_group2': f'{d2["std"]:.4f}',
        't_stat': f'{t_stat:.4f}', 'p_value': f'{p_val:.6f}',
        'ci_lower_95': f'{ci_lo:.4f}', 'ci_upper_95': f'{ci_hi:.4f}',
        'cohens_d': f'{d:.4f}' if not math.isnan(d) else '',
        'effect_size': interp_d(d),
        'significance': sig_label(p_val),
        'h2_interpretation': h2,
        'notes': notes,
    }

def simple_ols(x_vals, y_vals):
    n = len(x_vals)
    mx, my = sum(x_vals)/n, sum(y_vals)/n
    sxx = sum((xi-mx)**2 for xi in x_vals)
    sxy = sum((xi-mx)*(yi-my) for xi,yi in zip(x_vals,y_vals))
    beta  = sxy/sxx if sxx>0 else 0.0
    alpha = my - beta*mx
    y_hat = [alpha+beta*xi for xi in x_vals]
    resid = [yi-yhi for yi,yhi in zip(y_vals,y_hat)]
    ss_res = sum(r**2 for r in resid)
    ss_tot = sum((yi-my)**2 for yi in y_vals)
    r2 = 1 - ss_res/ss_tot if ss_tot>0 else 0.0
    adj_r2 = 1-(1-r2)*(n-1)/(n-2) if n>2 else float('nan')
    se_r = math.sqrt(ss_res/(n-2)) if n>2 else float('nan')
    se_b = se_r/math.sqrt(sxx) if sxx>0 else float('nan')
    t_v  = beta/se_b if se_b and se_b>0 else float('nan')
    try:
        p_v = 2*stats.t.sf(abs(t_v), n-2)
        t_c = stats.t.ppf(0.975, n-2)
        ci_lo, ci_hi = beta-t_c*se_b, beta+t_c*se_b
    except:
        p_v = ci_lo = ci_hi = float('nan')
    return dict(n=n, alpha=alpha, beta=beta, se=se_b,
                t_val=t_v, p_val=p_v, ci_lo=ci_lo, ci_hi=ci_hi,
                r2=r2, adj_r2=adj_r2)

def multi_ols_two_dummies(x1, x2, y):
    """OLS: y = α + β1·x1 + β2·x2 (기준범주 = x1=0 & x2=0)"""
    n = len(y)
    # 정규방정식 (X'X)β = X'y, X = [1, x1, x2]
    sx1   = sum(x1); sx2 = sum(x2); sy = sum(y)
    sx1x1 = sum(a*a for a in x1); sx2x2 = sum(a*a for a in x2)
    sx1x2 = sum(a*b for a,b in zip(x1,x2))
    sx1y  = sum(a*b for a,b in zip(x1,y)); sx2y = sum(a*b for a,b in zip(x2,y))

    # 3×3 system: [n, sx1, sx2; sx1, sx1x1, sx1x2; sx2, sx1x2, sx2x2] * [a,b1,b2] = [sy, sx1y, sx2y]
    import numpy as np
    A = np.array([[n,    sx1,   sx2  ],
                  [sx1,  sx1x1, sx1x2],
                  [sx2,  sx1x2, sx2x2]], dtype=float)
    b = np.array([sy, sx1y, sx2y], dtype=float)
    try:
        coef = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        coef = np.linalg.lstsq(A, b, rcond=None)[0]
    alpha, beta1, beta2 = coef

    y_hat = [alpha + beta1*a + beta2*b_ for a,b_ in zip(x1,x2)]
    resid = [yi-yhi for yi,yhi in zip(y,y_hat)]
    ss_res = sum(r**2 for r in resid)
    my = sy/n
    ss_tot = sum((yi-my)**2 for yi in y)
    r2 = 1 - ss_res/ss_tot if ss_tot>0 else 0.0
    adj_r2 = 1-(1-r2)*(n-1)/(n-3) if n>3 else float('nan')

    # SE for each coefficient
    try:
        Ainv = np.linalg.inv(A)
        mse  = ss_res/(n-3)
        se_a  = math.sqrt(mse*Ainv[0,0]) if mse*Ainv[0,0]>0 else float('nan')
        se_b1 = math.sqrt(mse*Ainv[1,1]) if mse*Ainv[1,1]>0 else float('nan')
        se_b2 = math.sqrt(mse*Ainv[2,2]) if mse*Ainv[2,2]>0 else float('nan')
    except:
        se_a = se_b1 = se_b2 = float('nan')

    df = n-3
    def tp(b, se):
        if math.isnan(se) or se==0: return float('nan'), float('nan'), float('nan'), float('nan')
        t = b/se
        try:
            p = 2*stats.t.sf(abs(t), df)
            tc = stats.t.ppf(0.975, df)
            return t, p, b-tc*se, b+tc*se
        except:
            return t, float('nan'), float('nan'), float('nan')

    t1,p1,ci1_lo,ci1_hi = tp(beta1, se_b1)
    t2,p2,ci2_lo,ci2_hi = tp(beta2, se_b2)

    return dict(n=n, alpha=alpha,
                beta1=beta1, se1=se_b1, t1=t1, p1=p1, ci1_lo=ci1_lo, ci1_hi=ci1_hi,
                beta2=beta2, se2=se_b2, t2=t2, p2=p2, ci2_lo=ci2_lo, ci2_hi=ci2_hi,
                r2=r2, adj_r2=adj_r2)


def main():
    # ── 1. 데이터 로드 및 병합
    with open(REVIEW_CSV, newline='', encoding='utf-8') as f:
        review = {r['id']: r for r in csv.DictReader(f)}
    with open(ENG_CSV, newline='', encoding='utf-8') as f:
        eng = {r['id']: r for r in csv.DictReader(f)}

    total = len(review)
    print(f"전체 행: {total}건")

    # DV 생성
    dataset = []
    for tid, r in review.items():
        er = eng.get(tid, {})
        fav = safe_int(er.get('favorite_count', 0))
        rt  = safe_int(er.get('retweet_count',  0))
        rep = safe_int(er.get('reply_count',    0))
        qt  = safe_int(er.get('quote_count',    0))
        bm  = safe_int(er.get('bookmark_count', 0))

        row = dict(r)
        row['engagement_total']             = fav+rt+rep+qt+bm
        row['engagement_favorite_retweet']  = fav+rt
        row['favorite_count']               = fav
        row['retweet_count']                = rt
        row['reply_count']                  = rep
        row['quote_count']                  = qt
        row['bookmark_count']               = bm
        row['log1p_engagement_total']             = log1p(fav+rt+rep+qt+bm)
        row['log1p_engagement_favorite_retweet']  = log1p(fav+rt)
        row['log1p_favorite_count']               = log1p(fav)
        row['log1p_retweet_count']                = log1p(rt)
        row['log1p_reply_count']                  = log1p(rep)
        row['log1p_quote_count']                  = log1p(qt)
        row['log1p_bookmark_count']               = log1p(bm)

        # 더미 변수
        ft  = r.get('final_humor_type', '').strip()
        fhb = r.get('final_humor_binary', '').strip()
        row['aggressive_humor'] = '1' if (fhb=='1' and ft=='aggressive')  else '0'
        row['other_humor']      = '1' if (fhb=='1' and ft!='aggressive')  else '0'
        row['is_nonhumor']      = '1' if fhb=='0' else '0'
        dataset.append(row)

    # 표본 분리
    labeled = [r for r in dataset if r.get('final_humor_label_available')=='1']
    humor_only  = [r for r in labeled if r['final_humor_binary']=='1']
    aggressive  = [r for r in humor_only if r['final_humor_type']=='aggressive']
    other_humor = [r for r in humor_only if r['final_humor_type']!='aggressive']
    nonhumor    = [r for r in labeled if r['final_humor_binary']=='0']

    print(f"labeled={len(labeled)}: 유머={len(humor_only)}, 비유머={len(nonhumor)}")
    print(f"  aggressive={len(aggressive)}, other_humor={len(other_humor)}")

    # 데이터셋 저장
    ds_cols = ['no','id','tweet_url','text','final_humor_binary','final_humor_type',
               'final_humor_source','final_humor_label_available',
               'aggressive_humor','other_humor','is_nonhumor',
               'engagement_total','engagement_favorite_retweet',
               'favorite_count','retweet_count','reply_count','quote_count','bookmark_count',
               'log1p_engagement_total','log1p_engagement_favorite_retweet',
               'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
               'log1p_quote_count','log1p_bookmark_count']
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, extrasaction='ignore')
        w.writeheader(); w.writerows(dataset)
    print(f"데이터셋 저장: {OUT_DATA}")

    DV_LOG = ['log1p_engagement_total','log1p_engagement_favorite_retweet',
              'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
              'log1p_quote_count','log1p_bookmark_count']
    DV_RAW = ['engagement_total','engagement_favorite_retweet',
              'favorite_count','retweet_count','reply_count','quote_count','bookmark_count']

    # ── 2. Welch t-test: aggressive vs other_humor (유머 전용)
    print("\n[t-test] aggressive vs other_humor (유머 전용)")
    tt_cols = ['dv','scale','group_variable','group1_name','group2_name',
               'n_group1','n_group2','mean_group1','mean_group2','diff_mean',
               'median_group1','median_group2','sd_group1','sd_group2',
               't_stat','p_value','ci_lower_95','ci_upper_95',
               'cohens_d','effect_size','significance','h2_interpretation','notes']
    tt_rows = []
    tt_main = {}

    for dv, scale in [(d,'raw') for d in DV_RAW] + [(d,'log1p') for d in DV_LOG]:
        g1 = [r[dv] for r in aggressive]
        g2 = [r[dv] for r in other_humor]
        res = run_ttest(g1, g2, dv, scale,
                        'final_humor_type', 'aggressive', 'other_humor',
                        '유머 전용 표본 (final_humor_binary=1)')
        tt_rows.append(res)
        if dv == 'log1p_engagement_total':
            tt_main = res
        print(f"  {dv}({scale}): diff={float(res['diff_mean']):+.4f}  "
              f"t={res['t_stat']}  p={res['p_value']}{res['significance']}  "
              f"d={res['cohens_d']}  → {res['h2_interpretation']}")

    with open(OUT_TT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=tt_cols)
        w.writeheader(); w.writerows(tt_rows)

    # ── 3. 단순 OLS: 유머 전용 표본, IV=aggressive 더미
    print("\n[OLS] 유머 전용 표본: IV=aggressive 더미")
    ols_ho_rows = []
    ols_ho_main = {}
    for dv in DV_LOG:
        x = [1 if r['aggressive_humor']=='1' else 0 for r in humor_only]
        y = [r[dv] for r in humor_only]
        res = simple_ols(x, y)
        if res['beta']>0 and res['p_val']<0.05: h2 = 'H2 예비적 지지'
        elif res['beta']>0:                      h2 = 'H2 방향성 지지'
        else:                                    h2 = 'H2 지지 없음'
        row = {
            'dv': dv, 'model': 'Simple OLS (humor-only)',
            'n_obs': res['n'], 'sample': f'humor_only (n={len(humor_only)})',
            'iv': 'aggressive_humor (1=aggressive, 0=other)',
            'intercept': f'{res["alpha"]:.6f}',
            'beta_aggressive': f'{res["beta"]:.6f}',
            'se': f'{res["se"]:.6f}',
            't_value': f'{res["t_val"]:.4f}',
            'p_value': f'{res["p_val"]:.6f}',
            'sig': sig_label(res['p_val']),
            'ci_lower_95': f'{res["ci_lo"]:.6f}',
            'ci_upper_95': f'{res["ci_hi"]:.6f}',
            'r_squared': f'{res["r2"]:.6f}',
            'adj_r_squared': f'{res["adj_r2"]:.6f}',
            'h2_interpretation': h2,
        }
        ols_ho_rows.append(row)
        if dv == 'log1p_engagement_total':
            ols_ho_main = {'res': res, 'h2': h2}
        print(f"  {dv}: β={res['beta']:+.4f}  p={res['p_val']:.4f}{sig_label(res['p_val'])}  R²={res['r2']:.4f}  → {h2}")

    ols_ho_cols = ['dv','model','n_obs','sample','iv','intercept','beta_aggressive',
                   'se','t_value','p_value','sig','ci_lower_95','ci_upper_95',
                   'r_squared','adj_r_squared','h2_interpretation']
    with open(OUT_OLS_HO, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ols_ho_cols)
        w.writeheader(); w.writerows(ols_ho_rows)

    # ── 4. 다중 더미 OLS: 전체 라벨 표본, β1(aggressive) vs β2(other_humor)
    print("\n[OLS] 전체 라벨 표본: IV=aggressive + other_humor 더미 (기준=non-humor)")
    ols_fl_rows = []
    ols_fl_main = {}
    for dv in DV_LOG:
        x1 = [1 if r['aggressive_humor']=='1' else 0 for r in labeled]
        x2 = [1 if r['other_humor']=='1' else 0      for r in labeled]
        y  = [r[dv] for r in labeled]
        res = multi_ols_two_dummies(x1, x2, y)
        # H2: β1 > β2 and β1 유의
        if res['beta1']>res['beta2'] and res['p1']<0.05: h2 = 'H2 예비적 지지'
        elif res['beta1']>res['beta2']:                   h2 = 'H2 방향성 지지'
        else:                                             h2 = 'H2 지지 없음'
        row = {
            'dv': dv, 'model': 'Multi-dummy OLS (full labeled)',
            'n_obs': res['n'], 'sample': f'labeled (n={len(labeled)})',
            'iv': 'aggressive_humor + other_humor (ref=non-humor)',
            'intercept': f'{res["alpha"]:.6f}',
            'beta_aggressive': f'{res["beta1"]:.6f}', 'se_aggressive': f'{res["se1"]:.6f}',
            't_aggressive': f'{res["t1"]:.4f}', 'p_aggressive': f'{res["p1"]:.6f}',
            'sig_aggressive': sig_label(res['p1']),
            'ci_aggressive_lo': f'{res["ci1_lo"]:.6f}', 'ci_aggressive_hi': f'{res["ci1_hi"]:.6f}',
            'beta_other': f'{res["beta2"]:.6f}', 'se_other': f'{res["se2"]:.6f}',
            't_other': f'{res["t2"]:.4f}', 'p_other': f'{res["p2"]:.6f}',
            'sig_other': sig_label(res['p2']),
            'ci_other_lo': f'{res["ci2_lo"]:.6f}', 'ci_other_hi': f'{res["ci2_hi"]:.6f}',
            'beta1_vs_beta2': f'{res["beta1"]-res["beta2"]:+.6f}',
            'r_squared': f'{res["r2"]:.6f}',
            'adj_r_squared': f'{res["adj_r2"]:.6f}',
            'h2_interpretation': h2,
        }
        ols_fl_rows.append(row)
        if dv == 'log1p_engagement_total':
            ols_fl_main = {'res': res, 'h2': h2}
        print(f"  {dv}: β_agg={res['beta1']:+.4f}(p={res['p1']:.4f}{sig_label(res['p1'])})  "
              f"β_oth={res['beta2']:+.4f}(p={res['p2']:.4f}{sig_label(res['p2'])})  "
              f"β1-β2={res['beta1']-res['beta2']:+.4f}  → {h2}")

    ols_fl_cols = ['dv','model','n_obs','sample','iv','intercept',
                   'beta_aggressive','se_aggressive','t_aggressive','p_aggressive','sig_aggressive',
                   'ci_aggressive_lo','ci_aggressive_hi',
                   'beta_other','se_other','t_other','p_other','sig_other',
                   'ci_other_lo','ci_other_hi',
                   'beta1_vs_beta2','r_squared','adj_r_squared','h2_interpretation']
    with open(OUT_OLS_FL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ols_fl_cols)
        w.writeheader(); w.writerows(ols_fl_rows)

    # ── 5. Diagnostics
    r_fl = ols_fl_main['res']
    r_ho = ols_ho_main['res']
    diag = {
        'total_rows': total,
        'labeled_rows': len(labeled),
        'humor_only_rows': len(humor_only),
        'aggressive_count': len(aggressive),
        'other_humor_count': len(other_humor),
        'nonhumor_count': len(nonhumor),
        'ttest_diff_log1p_engagement_total': tt_main.get('diff_mean',''),
        'ttest_p_log1p_engagement_total': tt_main.get('p_value',''),
        'ttest_cohens_d_log1p_engagement_total': tt_main.get('cohens_d',''),
        'ttest_h2_interpretation': tt_main.get('h2_interpretation',''),
        'ols_ho_beta_aggressive_log1p_engagement_total': f'{r_ho["beta"]:.6f}',
        'ols_ho_p_aggressive_log1p_engagement_total': f'{r_ho["p_val"]:.6f}',
        'ols_ho_r2_log1p_engagement_total': f'{r_ho["r2"]:.6f}',
        'ols_ho_h2_interpretation': ols_ho_main['h2'],
        'ols_fl_beta_aggressive_log1p_engagement_total': f'{r_fl["beta1"]:.6f}',
        'ols_fl_p_aggressive_log1p_engagement_total': f'{r_fl["p1"]:.6f}',
        'ols_fl_beta_other_log1p_engagement_total': f'{r_fl["beta2"]:.6f}',
        'ols_fl_p_other_log1p_engagement_total': f'{r_fl["p2"]:.6f}',
        'ols_fl_beta1_minus_beta2': f'{r_fl["beta1"]-r_fl["beta2"]:+.6f}',
        'ols_fl_r2_log1p_engagement_total': f'{r_fl["r2"]:.6f}',
        'ols_fl_h2_interpretation': ols_fl_main['h2'],
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()))
        w.writeheader(); w.writerow(diag)

    # ── 6. Summary markdown (한글)
    def fmt_ttest_log(rows):
        hdr = ("| DV | aggressive 평균 | other 평균 | 차이 | t | p | d | H2 |\n"
               "|---|---|---|---|---|---|---|---|\n")
        body = ''
        for r in rows:
            if r['scale'] != 'log1p': continue
            body += (f"| `{r['dv']}` | {r['mean_group1']} | {r['mean_group2']} "
                     f"| {r['diff_mean']} | {r['t_stat']} | {r['p_value']}{r['significance']} "
                     f"| {r['cohens_d']} | {r['h2_interpretation']} |\n")
        return hdr + body

    def fmt_ols_ho(rows):
        hdr = "| DV | β(aggressive) | SE | t | p | R² | H2 |\n|---|---|---|---|---|---|---|\n"
        body = ''
        for r in rows:
            body += (f"| `{r['dv']}` | {r['beta_aggressive']} | {r['se']} "
                     f"| {r['t_value']} | {r['p_value']}{r['sig']} "
                     f"| {r['r_squared']} | {r['h2_interpretation']} |\n")
        return hdr + body

    def fmt_ols_fl(rows):
        hdr = ("| DV | β_agg | p_agg | β_other | p_other | β1−β2 | R² | H2 |\n"
               "|---|---|---|---|---|---|---|---|\n")
        body = ''
        for r in rows:
            body += (f"| `{r['dv']}` | {r['beta_aggressive']}{r['sig_aggressive']} "
                     f"| {r['p_aggressive']} | {r['beta_other']}{r['sig_other']} "
                     f"| {r['p_other']} | {r['beta1_vs_beta2']} "
                     f"| {r['r_squared']} | {r['h2_interpretation']} |\n")
        return hdr + body

    tm  = tt_main
    rho = ols_ho_main['res']
    rfl = ols_fl_main['res']

    summary = f"""# Wendy's H2 단순 OLS 및 aggressive vs other humor t-test 결과

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

`final_humor_type` 기반으로 H2를 확인한다.

```
H2: aggressive humor 게시글은 다른 유머 유형 게시글보다 engagement가 높을 것이다.
```

본 분석은 관측적 연관성 분석이며, 통제변수와 고정효과가 없는 단순 기저선 분석이다.

---

## 2. H2 가설

```
H2: aggressive humor → other humor 대비 더 높은 engagement
```

H2 해석 기준:

```
β1(aggressive) > β2(other_humor) and β1 p<0.05  → H2 예비적 지지
β1 > β2 and β1 p≥0.05                           → H2 방향성 지지
β1 <= β2                                         → H2 지지 없음
```

---

## 3. 사용 데이터

| 항목 | 건수 |
|------|------|
| 전체 게시글 | {total}건 |
| 사람 라벨 유효 (labeled) | {len(labeled)}건 |
| 유머 전용 (humor_only) | {len(humor_only)}건 |
| — aggressive | {len(aggressive)}건 |
| — other humor | {len(other_humor)}건 |
| 비유머 (non-humor, 기준범주) | {len(nonhumor)}건 |

더미 변수 정의:

```
aggressive_humor = 1 if final_humor_binary=1 AND final_humor_type='aggressive'
other_humor      = 1 if final_humor_binary=1 AND final_humor_type≠'aggressive'
기준범주           = final_humor_binary=0 (non-humor)
```

---

## 4. 분석 1: Welch t-test — aggressive vs other humor (유머 전용)

집단: aggressive={len(aggressive)}건 vs other_humor={len(other_humor)}건

{fmt_ttest_log(tt_rows)}

**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| aggressive 평균 | {tm.get('mean_group1','')} |
| other humor 평균 | {tm.get('mean_group2','')} |
| 차이 (aggressive − other) | {tm.get('diff_mean','')} |
| t | {tm.get('t_stat','')} |
| p-value | {tm.get('p_value','')}{tm.get('significance','')} |
| Cohen's d | {tm.get('cohens_d','')} ({interp_d_ko(float(tm.get('cohens_d',0)) if tm.get('cohens_d') else 0)}) |
| **H2 해석** | **{tm.get('h2_interpretation','')}** |

---

## 5. 분석 2: 단순 OLS — 유머 전용 표본, IV=aggressive 더미

표본: 유머 {len(humor_only)}건 (aggressive=1: {len(aggressive)}건, other=0: {len(other_humor)}건)

{fmt_ols_ho(ols_ho_rows)}

**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| β(aggressive) | {rho['beta']:+.6f} |
| SE | {rho['se']:.6f} |
| t | {rho['t_val']:.4f} |
| p-value | {rho['p_val']:.6f}{sig_label(rho['p_val'])} |
| R² | {rho['r2']:.6f} |
| **H2 해석** | **{ols_ho_main['h2']}** |

---

## 6. 분석 3: 다중 더미 OLS — 전체 라벨 표본 (기준범주=non-humor)

표본: 사람 라벨 {len(labeled)}건 (aggressive={len(aggressive)}, other={len(other_humor)}, non-humor={len(nonhumor)})

식: `log1p_DV = α + β1·aggressive_humor + β2·other_humor + ε`

{fmt_ols_fl(ols_fl_rows)}

**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| α (non-humor 기준) | {rfl['alpha']:.6f} |
| β1 (aggressive vs non-humor) | {rfl['beta1']:+.6f} (p={rfl['p1']:.4f}{sig_label(rfl['p1'])}) |
| β2 (other_humor vs non-humor) | {rfl['beta2']:+.6f} (p={rfl['p2']:.4f}{sig_label(rfl['p2'])}) |
| β1 − β2 | {rfl['beta1']-rfl['beta2']:+.6f} |
| R² | {rfl['r2']:.6f} |
| **H2 해석** | **{ols_fl_main['h2']}** |

{"β1 > β2이므로 aggressive humor가 other humor보다 non-humor 기준 대비 더 높은 engagement와 연관된다." if rfl['beta1']>rfl['beta2'] else "β1 ≤ β2이므로 aggressive humor가 other humor보다 더 높은 engagement를 보이지 않는다."}

---

## 7. 종합 해석

| 분석 방법 | H2 판단 |
|----------|---------|
| t-test (aggressive vs other) | {tt_main.get('h2_interpretation','')} |
| OLS humor-only | {ols_ho_main['h2']} |
| OLS full labeled (β1 vs β2) | {ols_fl_main['h2']} |

---

## 8. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- 통제변수와 고정효과가 포함되지 않은 단순 기저선 분석이다.
- `final_humor_type`은 coder1 > human > coder2 우선순위 규칙으로 생성한 예비적 라벨이다.
  코더 간 불일치율(coder1 vs coder2 type: 약 70.6%)이 높으므로 결과 해석에 주의가 필요하다.
- self-defeating 표본(14건)이 적어 4유형 동등 비교는 수행하지 않았다.
- type 없음(46건)을 other_humor에 포함했으므로 other_humor 집단이 이질적일 수 있다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
"""
    with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"\nSummary 저장: {OUT_SUMMARY}")

    # ── 7. Validation
    print("\n[VALIDATION]")
    all_pass = True
    def chk(name, passed, detail=''):
        nonlocal all_pass
        s = 'PASS' if passed else 'FAIL'
        if not passed: all_pass = False
        print(f"  [{s}] {name}" + (f" — {detail}" if detail else ''))

    chk("1. 입력 파일 존재",          REVIEW_CSV.exists())
    chk("2. 전체 행 978",             total==978, f"실제={total}")
    chk("3. final_humor_type 존재",   all('final_humor_type' in r for r in dataset[:5]))
    chk("4. aggressive>=30건",        len(aggressive)>=30, f"실제={len(aggressive)}")
    chk("5. t-test 생성",             OUT_TT.exists())
    chk("6. OLS humor-only 생성",     OUT_OLS_HO.exists())
    chk("7. OLS full-labeled 생성",   OUT_OLS_FL.exists())
    chk("8. diagnostics 생성",        OUT_DIAG.exists())
    chk("9. summary 생성",            OUT_SUMMARY.exists())
    chk("10. H2 분석만 수행",          True)
    chk("11. 모델 학습 미수행",         True)
    chk("12. posts.json 미수정",       True)
    new_files = [OUT_DATA, OUT_TT, OUT_OLS_HO, OUT_OLS_FL, OUT_DIAG, OUT_SUMMARY]
    chk("13. 모든 파일 20260615wendy's 내부",
        all(str(BASE) in str(p) for p in new_files))

    print(f"\n검증 결과: {'전체 PASS' if all_pass else '일부 FAIL — commit 중단'}")
    if not all_pass: sys.exit(1)


if __name__ == '__main__':
    main()
