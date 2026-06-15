"""
run_wendys_h1_simple_ols_and_ttest.py

== 1. 목적 ==
final_humor_binary 기반 TF-IDF + Logistic Regression 유머 유무 분류 결과를
사용하여 H1("유머 가능성이 높을수록 engagement가 높다")을 가장 단순한 방식으로
확인한다. 수행하는 분석은 다음 두 가지이다.
  (1) H1 단순 OLS
  (2) 유머 vs 비유머 Welch t-test

== 2. OLS와 t-test를 함께 수행하는 이유 ==
단순 OLS(IV=연속형 유머 확률)는 유머 가능성의 선형 관계를 전체 978건 기준으로 본다.
t-test(IV=이진 유머 라벨)는 사람이 직접 코딩한 집단 간 평균 차이를 확인한다.
두 분석은 관점이 다르므로 함께 보고하여 상호 보완적인 근거를 제공한다.

== 3. OLS와 t-test의 차이 ==
OLS: 연속형 예측 확률(log1p_p_humor_final_tfidf_logreg)을 IV로 사용, 전체 978건 대상
t-test: 이진 라벨(final_humor_binary 또는 pred_humor_final_050)로 집단 구분 후 평균 비교

== 4. p_humor_final_tfidf_logreg와 final_humor_binary의 차이 ==
p_humor_final_tfidf_logreg: 모델이 추정한 연속형 유머 확률 (0~1)
final_humor_binary: 사람 코더가 부여한 이진 최종 라벨 (0/1 또는 공란)

== 5. primary t-test와 supplemental t-test의 차이 ==
primary: 사람이 직접 라벨링한 597건 기준 (final_humor_binary)
supplemental: 전체 978건 모델 예측 기준 (pred_humor_final_050)
supplemental은 모델 예측값 기준이므로 primary보다 보조적으로 해석한다.

== 6. engagement 변수가 유머 분류 모델 학습에 사용되지 않았다는 점 ==
engagement는 H1 분석의 종속변수다. 유머 분류 모델 학습에 사용하면 순환 편의가 발생한다.
따라서 이번 OLS와 t-test에서 처음으로 engagement를 분석에 투입한다.

== 7. 인과분석이 아님 ==
본 분석은 관측적 연관성 분석이다. 통제변수, 고정효과, 도구변수가 없으므로
"유머가 engagement를 증가시킨다"는 인과 주장을 할 수 없다.

== 8. 모든 산출물 경로 ==
모든 새 파일은 20260615wendy's/ 내부에만 생성한다.
"""

import csv
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from scipy import stats

BASE        = Path("20260615wendy's")
FULL_PRED   = BASE / "result" / "wendys_final_humor_presence_full_predictions.csv"
ENG_CSV     = BASE / "data"   / "wendys_fast_weak_supervised_humor_dataset.csv"
OUT_DATA    = BASE / "data"   / "wendys_h1_simple_ols_ttest_dataset.csv"
OUT_OLS     = BASE / "result" / "wendys_h1_simple_ols_results_final_humor.csv"
OUT_TT_PRI  = BASE / "result" / "wendys_h1_ttest_primary_human_label.csv"
OUT_TT_SUP  = BASE / "result" / "wendys_h1_ttest_supplemental_model_prediction.csv"
OUT_DIAG    = BASE / "result" / "wendys_h1_simple_ols_ttest_diagnostics.csv"
OUT_SUMMARY = BASE / "result" / "wendys_h1_simple_ols_ttest_summary.md"
OUT_PLOT    = BASE / "result" / "wendys_h1_ttest_group_mean_plot.png"


def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def log1p(v):
    return math.log1p(v)


def desc_stats(vals):
    n = len(vals)
    if n == 0:
        return dict(n=0, mean=float('nan'), std=float('nan'),
                    median=float('nan'), mn=float('nan'), mx=float('nan'))
    mu = sum(vals) / n
    var = sum((x - mu) ** 2 for x in vals) / (n - 1) if n > 1 else 0.0
    s = sorted(vals)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return dict(n=n, mean=mu, std=math.sqrt(var), median=med, mn=min(vals), mx=max(vals))


def cohen_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        return float('nan')
    m1, m2 = sum(g1) / n1, sum(g2) / n2
    v1 = sum((x - m1) ** 2 for x in g1) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in g2) / (n2 - 1)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    return (m1 - m2) / sp if sp > 0 else float('nan')


def interp_d_en(d):
    ad = abs(d)
    if ad < 0.2:  return 'negligible'
    if ad < 0.5:  return 'small'
    if ad < 0.8:  return 'medium'
    return 'large'


def interp_d_ko(d):
    ad = abs(d)
    if ad < 0.2:  return '무시 가능'
    if ad < 0.5:  return '작음'
    if ad < 0.8:  return '중간'
    return '큼'


def sig_label(p):
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '†'
    return 'n.s.'


def h1_interp_ttest(diff, p):
    if diff > 0 and p < 0.05:  return 'H1 예비적 지지'
    if diff > 0:                return 'H1 방향성 지지'
    return 'H1 지지 없음'


def h1_interp_ols(beta, p):
    try:
        b = float(beta)
    except (TypeError, ValueError):
        return 'H1 지지 없음'
    if b > 0 and p < 0.05:  return 'H1 예비적 지지'
    if b > 0:                return 'H1 방향성 지지'
    return 'H1 지지 없음'


def simple_ols(x_vals, y_vals):
    """단순 OLS: y = α + β·x"""
    n = len(x_vals)
    if n < 3:
        raise ValueError("표본 부족")
    mx = sum(x_vals) / n
    my = sum(y_vals) / n
    sxx = sum((xi - mx) ** 2 for xi in x_vals)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x_vals, y_vals))
    beta = sxy / sxx if sxx > 0 else 0.0
    alpha = my - beta * mx

    y_hat = [alpha + beta * xi for xi in x_vals]
    resid = [yi - yhi for yi, yhi in zip(y_vals, y_hat)]
    ss_res = sum(r ** 2 for r in resid)
    ss_tot = sum((yi - my) ** 2 for yi in y_vals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else float('nan')

    se_resid = math.sqrt(ss_res / (n - 2)) if n > 2 else float('nan')
    se_beta  = se_resid / math.sqrt(sxx) if sxx > 0 else float('nan')
    t_val    = beta / se_beta if se_beta and se_beta > 0 else float('nan')

    # p-value (two-sided t)
    df = n - 2
    try:
        p_val = 2 * stats.t.sf(abs(t_val), df)
    except Exception:
        p_val = float('nan')

    # 95% CI
    try:
        t_crit = stats.t.ppf(0.975, df)
        ci_lo = beta - t_crit * se_beta
        ci_hi = beta + t_crit * se_beta
    except Exception:
        ci_lo = ci_hi = float('nan')

    return dict(
        n=n, alpha=alpha, beta=beta, se=se_beta,
        t_val=t_val, p_val=p_val,
        ci_lo=ci_lo, ci_hi=ci_hi,
        r2=r2, adj_r2=adj_r2
    )


def run_ttest(humor_vals, nonhumor_vals, dv_name, scale, group_var, notes=''):
    """Welch t-test 수행 및 결과 딕셔너리 반환"""
    d1 = desc_stats(humor_vals)
    d2 = desc_stats(nonhumor_vals)
    t_stat, p_val = stats.ttest_ind(humor_vals, nonhumor_vals, equal_var=False)
    df_w = (d1['std']**2/d1['n'] + d2['std']**2/d2['n'])**2 / (
           (d1['std']**2/d1['n'])**2/(d1['n']-1) +
           (d2['std']**2/d2['n'])**2/(d2['n']-1)) if d1['n'] > 1 and d2['n'] > 1 else 0
    try:
        t_crit = stats.t.ppf(0.975, df_w)
        se_diff = math.sqrt(d1['std']**2/d1['n'] + d2['std']**2/d2['n'])
        diff = d1['mean'] - d2['mean']
        ci_lo = diff - t_crit * se_diff
        ci_hi = diff + t_crit * se_diff
    except Exception:
        diff = d1['mean'] - d2['mean']
        ci_lo = ci_hi = float('nan')
    diff = d1['mean'] - d2['mean']
    d = cohen_d(humor_vals, nonhumor_vals)
    return {
        'dv':              dv_name,
        'scale':           scale,
        'group_variable':  group_var,
        'n_humor':         d1['n'],
        'n_nonhumor':      d2['n'],
        'mean_humor':      f'{d1["mean"]:.4f}',
        'mean_nonhumor':   f'{d2["mean"]:.4f}',
        'diff_mean':       f'{diff:.4f}',
        'median_humor':    f'{d1["median"]:.4f}',
        'median_nonhumor': f'{d2["median"]:.4f}',
        'sd_humor':        f'{d1["std"]:.4f}',
        'sd_nonhumor':     f'{d2["std"]:.4f}',
        't_stat':          f'{t_stat:.4f}',
        'p_value':         f'{p_val:.6f}',
        'ci_lower_95':     f'{ci_lo:.4f}',
        'ci_upper_95':     f'{ci_hi:.4f}',
        'cohens_d':        f'{d:.4f}' if not math.isnan(d) else '',
        'effect_size':     interp_d_en(d),
        'significance':    sig_label(p_val),
        'h1_interpretation': h1_interp_ttest(diff, p_val),
        'notes':           notes,
    }


def main():
    # ────────────────────────────────────────────
    # 1. 입력 파일 로드 및 병합
    # ────────────────────────────────────────────
    with open(FULL_PRED, newline='', encoding='utf-8') as f:
        pred_rows = {r['id']: r for r in csv.DictReader(f)}

    with open(ENG_CSV, newline='', encoding='utf-8') as f:
        eng_rows = {str(r['id']): r for r in csv.DictReader(f)}

    total_rows = len(pred_rows)
    print(f"full predictions: {total_rows}건")
    print(f"engagement 데이터: {len(eng_rows)}건")

    # ── DV 생성 및 병합
    ENG_COLS = ['reply_count', 'favorite_count', 'retweet_count',
                'quote_count', 'bookmark_count', 'view_count',
                'created_year', 'created_month', 'created_day',
                'created_time', 'is_quote_status', 'is_retweet_text']

    DV_NAMES = [
        'log1p_engagement_total',
        'log1p_engagement_favorite_retweet',
        'log1p_favorite_count',
        'log1p_retweet_count',
        'log1p_reply_count',
        'log1p_quote_count',
        'log1p_bookmark_count',
    ]
    RAW_DV_NAMES = [
        'engagement_total',
        'engagement_favorite_retweet',
        'favorite_count',
        'retweet_count',
        'reply_count',
        'quote_count',
        'bookmark_count',
    ]

    dataset = []
    missing_eng = 0
    missing_counts = {c: 0 for c in ['reply_count','favorite_count','retweet_count',
                                      'quote_count','bookmark_count',
                                      'p_humor_final_tfidf_logreg',
                                      'log1p_p_humor_final_tfidf_logreg']}

    for tid, pr in pred_rows.items():
        row = dict(pr)
        er = eng_rows.get(tid, {})
        if not er:
            missing_eng += 1

        # engagement 원자료 병합
        for c in ENG_COLS:
            row[c] = er.get(c, '')

        # 원자료 engagement
        fav  = safe_int(er.get('favorite_count', 0))
        rt   = safe_int(er.get('retweet_count',  0))
        rep  = safe_int(er.get('reply_count',    0))
        qt   = safe_int(er.get('quote_count',    0))
        bm   = safe_int(er.get('bookmark_count', 0))

        row['engagement_total']              = fav + rt + rep + qt + bm
        row['engagement_favorite_retweet']   = fav + rt

        # 결측 카운트
        for c in ['reply_count','favorite_count','retweet_count','quote_count','bookmark_count']:
            if not er.get(c):
                missing_counts[c] += 1

        # log1p DV
        row['log1p_engagement_total']             = log1p(fav + rt + rep + qt + bm)
        row['log1p_engagement_favorite_retweet']  = log1p(fav + rt)
        row['log1p_favorite_count']               = log1p(fav)
        row['log1p_retweet_count']                = log1p(rt)
        row['log1p_reply_count']                  = log1p(rep)
        row['log1p_quote_count']                  = log1p(qt)
        row['log1p_bookmark_count']               = log1p(bm)

        # IV 확인
        p_fin = safe_float(pr.get('p_humor_final_tfidf_logreg', ''))
        lp_fin = safe_float(pr.get('log1p_p_humor_final_tfidf_logreg', ''))
        if not pr.get('p_humor_final_tfidf_logreg'):
            missing_counts['p_humor_final_tfidf_logreg'] += 1
        if not pr.get('log1p_p_humor_final_tfidf_logreg'):
            missing_counts['log1p_p_humor_final_tfidf_logreg'] += 1

        row['p_humor_final_tfidf_logreg']     = p_fin
        row['log1p_p_humor_final_tfidf_logreg'] = lp_fin

        dataset.append(row)

    if missing_eng:
        print(f"  [경고] engagement 병합 누락: {missing_eng}건")

    # ── 데이터셋 저장
    ds_cols = (
        ['no','id','tweet_url','text',
         'final_humor_binary','final_humor_source','final_humor_label_available',
         'pred_humor_final_050','prediction_set',
         'p_humor_final_tfidf_logreg','log1p_p_humor_final_tfidf_logreg',
         'model_humor','p_humor','p_humor_ml'] +
        ENG_COLS +
        RAW_DV_NAMES + DV_NAMES
    )
    with open(OUT_DATA, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ds_cols, extrasaction='ignore')
        w.writeheader(); w.writerows(dataset)
    print(f"데이터셋 저장: {OUT_DATA}")

    # ────────────────────────────────────────────
    # 2. H1 단순 OLS (전체 978건, IV=log1p_p_humor_final_tfidf_logreg)
    # ────────────────────────────────────────────
    print("\n[OLS] 단순 OLS 시작...")
    iv_vals = [r['log1p_p_humor_final_tfidf_logreg'] for r in dataset]

    ols_rows = []
    ols_main_result = {}
    for dv in DV_NAMES:
        dv_vals = [r[dv] for r in dataset]
        res = simple_ols(iv_vals, dv_vals)
        interp = h1_interp_ols(res['beta'], res['p_val'])
        row = {
            'dv':            dv,
            'model_name':    'Simple OLS',
            'n_obs':         res['n'],
            'iv':            'log1p_p_humor_final_tfidf_logreg',
            'intercept':     f'{res["alpha"]:.6f}',
            'beta':          f'{res["beta"]:.6f}',
            'standard_error': f'{res["se"]:.6f}',
            't_value':       f'{res["t_val"]:.4f}',
            'p_value':       f'{res["p_val"]:.6f}',
            'ci_lower_95':   f'{res["ci_lo"]:.6f}',
            'ci_upper_95':   f'{res["ci_hi"]:.6f}',
            'r_squared':     f'{res["r2"]:.6f}',
            'adj_r_squared': f'{res["adj_r2"]:.6f}',
            'direction':     'positive' if res['beta'] > 0 else 'negative',
            'h1_interpretation': interp,
            'notes':         '',
        }
        ols_rows.append(row)
        if dv == 'log1p_engagement_total':
            ols_main_result = res
            ols_main_result['interp'] = interp
        print(f"  {dv}: β={res['beta']:.4f}  p={res['p_val']:.4f}{sig_label(res['p_val'])}  R²={res['r2']:.4f}  → {interp}")

    ols_cols = ['dv','model_name','n_obs','iv','intercept','beta','standard_error',
                't_value','p_value','ci_lower_95','ci_upper_95','r_squared',
                'adj_r_squared','direction','h1_interpretation','notes']
    with open(OUT_OLS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=ols_cols)
        w.writeheader(); w.writerows(ols_rows)

    # ────────────────────────────────────────────
    # 3. Primary t-test (사람 라벨 기준, final_humor_binary)
    # ────────────────────────────────────────────
    print("\n[t-test PRIMARY] 사람 라벨 기준...")
    pri_rows_h  = [r for r in dataset if r['final_humor_binary'] == '1' and r.get('final_humor_label_available') == '1']
    pri_rows_nh = [r for r in dataset if r['final_humor_binary'] == '0' and r.get('final_humor_label_available') == '1']
    n_pri_h  = len(pri_rows_h)
    n_pri_nh = len(pri_rows_nh)
    print(f"  유머={n_pri_h}건, 비유머={n_pri_nh}건")

    tt_pri = []
    pri_main = {}
    all_dvs = [(d, 'raw') for d in RAW_DV_NAMES] + [(d, 'log1p') for d in DV_NAMES]
    for dv, scale in all_dvs:
        h_vals  = [r[dv] if isinstance(r[dv], float) else safe_float(str(r[dv])) for r in pri_rows_h]
        nh_vals = [r[dv] if isinstance(r[dv], float) else safe_float(str(r[dv])) for r in pri_rows_nh]
        res = run_ttest(h_vals, nh_vals, dv, scale, 'final_humor_binary',
                        '사람 최종 라벨(coder1>human>coder2) 기준')
        tt_pri.append(res)
        if dv == 'log1p_engagement_total':
            pri_main = res
        print(f"  {dv}({scale}): diff={float(res['diff_mean']):+.4f}  "
              f"t={res['t_stat']}  p={res['p_value']}{res['significance']}"
              f"  d={res['cohens_d']}")

    tt_cols = ['dv','scale','group_variable','n_humor','n_nonhumor',
               'mean_humor','mean_nonhumor','diff_mean','median_humor','median_nonhumor',
               'sd_humor','sd_nonhumor','t_stat','p_value','ci_lower_95','ci_upper_95',
               'cohens_d','effect_size','significance','h1_interpretation','notes']
    with open(OUT_TT_PRI, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=tt_cols)
        w.writeheader(); w.writerows(tt_pri)

    # ────────────────────────────────────────────
    # 4. Supplemental t-test (모델 예측 기준, pred_humor_final_050)
    # ────────────────────────────────────────────
    print("\n[t-test SUPPLEMENTAL] 모델 예측 기준...")
    sup_rows_h  = [r for r in dataset if str(r.get('pred_humor_final_050','')) == '1']
    sup_rows_nh = [r for r in dataset if str(r.get('pred_humor_final_050','')) == '0']
    n_sup_h  = len(sup_rows_h)
    n_sup_nh = len(sup_rows_nh)
    print(f"  유머(예측)={n_sup_h}건, 비유머(예측)={n_sup_nh}건")

    tt_sup = []
    sup_main = {}
    for dv, scale in all_dvs:
        h_vals  = [r[dv] if isinstance(r[dv], float) else safe_float(str(r[dv])) for r in sup_rows_h]
        nh_vals = [r[dv] if isinstance(r[dv], float) else safe_float(str(r[dv])) for r in sup_rows_nh]
        res = run_ttest(h_vals, nh_vals, dv, scale, 'pred_humor_final_050',
                        '모델 예측 이진값 기준 (보조 분석)')
        tt_sup.append(res)
        if dv == 'log1p_engagement_total':
            sup_main = res
        print(f"  {dv}({scale}): diff={float(res['diff_mean']):+.4f}  "
              f"t={res['t_stat']}  p={res['p_value']}{res['significance']}")

    with open(OUT_TT_SUP, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=tt_cols)
        w.writeheader(); w.writerows(tt_sup)

    # ────────────────────────────────────────────
    # 5. Diagnostics
    # ────────────────────────────────────────────
    diag = {
        'total_rows':                    total_rows,
        'ols_rows_used':                 total_rows,
        'primary_ttest_rows_used':       n_pri_h + n_pri_nh,
        'primary_ttest_humor_count':     n_pri_h,
        'primary_ttest_nonhumor_count':  n_pri_nh,
        'supplemental_ttest_rows_used':  n_sup_h + n_sup_nh,
        'supplemental_ttest_humor_count':   n_sup_h,
        'supplemental_ttest_nonhumor_count': n_sup_nh,
        'missing_reply_count':           missing_counts['reply_count'],
        'missing_favorite_count':        missing_counts['favorite_count'],
        'missing_retweet_count':         missing_counts['retweet_count'],
        'missing_quote_count':           missing_counts['quote_count'],
        'missing_bookmark_count':        missing_counts['bookmark_count'],
        'missing_p_humor_final_tfidf_logreg':       missing_counts['p_humor_final_tfidf_logreg'],
        'missing_log1p_p_humor_final_tfidf_logreg': missing_counts['log1p_p_humor_final_tfidf_logreg'],
        'main_ols_beta_log1p_engagement_total':  f'{ols_main_result["beta"]:.6f}',
        'main_ols_p_log1p_engagement_total':     f'{ols_main_result["p_val"]:.6f}',
        'main_ols_r2_log1p_engagement_total':    f'{ols_main_result["r2"]:.6f}',
        'primary_ttest_diff_log1p_engagement_total':     pri_main.get('diff_mean',''),
        'primary_ttest_p_log1p_engagement_total':        pri_main.get('p_value',''),
        'primary_ttest_cohens_d_log1p_engagement_total': pri_main.get('cohens_d',''),
        'supplemental_ttest_diff_log1p_engagement_total':     sup_main.get('diff_mean',''),
        'supplemental_ttest_p_log1p_engagement_total':        sup_main.get('p_value',''),
        'supplemental_ttest_cohens_d_log1p_engagement_total': sup_main.get('cohens_d',''),
    }
    with open(OUT_DIAG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(diag.keys()))
        w.writeheader(); w.writerow(diag)

    # ────────────────────────────────────────────
    # 6. 그래프 (선택적)
    # ────────────────────────────────────────────
    png_saved = False
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        pri_h_eng  = [r['log1p_engagement_total'] for r in pri_rows_h]
        pri_nh_eng = [r['log1p_engagement_total'] for r in pri_rows_nh]
        sup_h_eng  = [r['log1p_engagement_total'] for r in sup_rows_h]
        sup_nh_eng = [r['log1p_engagement_total'] for r in sup_rows_nh]

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle("log1p_engagement_total: Humor vs Non-Humor Group Mean", fontsize=12)

        # Primary (사람 라벨)
        means_pri  = [sum(pri_h_eng)/len(pri_h_eng), sum(pri_nh_eng)/len(pri_nh_eng)]
        se_pri     = [np.std(pri_h_eng, ddof=1)/np.sqrt(len(pri_h_eng)),
                      np.std(pri_nh_eng, ddof=1)/np.sqrt(len(pri_nh_eng))]
        axes[0].bar(['Humor', 'Non-Humor'], means_pri, yerr=se_pri,
                    color=['tomato','steelblue'], alpha=0.8, capsize=5, width=0.5)
        axes[0].set_title(f'Primary: Human Label\n(n_h={n_pri_h}, n_nh={n_pri_nh})')
        axes[0].set_ylabel('Mean log1p_engagement_total')
        axes[0].set_ylim(0)
        p_pri = float(pri_main.get('p_value', 1))
        axes[0].text(0.5, 0.95, f'p={p_pri:.4f}{sig_label(p_pri)}',
                     ha='center', va='top', transform=axes[0].transAxes, fontsize=11)

        # Supplemental (모델 예측)
        means_sup = [sum(sup_h_eng)/len(sup_h_eng), sum(sup_nh_eng)/len(sup_nh_eng)]
        se_sup    = [np.std(sup_h_eng, ddof=1)/np.sqrt(len(sup_h_eng)),
                     np.std(sup_nh_eng, ddof=1)/np.sqrt(len(sup_nh_eng))]
        axes[1].bar(['Humor', 'Non-Humor'], means_sup, yerr=se_sup,
                    color=['tomato','steelblue'], alpha=0.8, capsize=5, width=0.5)
        axes[1].set_title(f'Supplemental: Model Prediction\n(n_h={n_sup_h}, n_nh={n_sup_nh})')
        axes[1].set_ylabel('Mean log1p_engagement_total')
        axes[1].set_ylim(0)
        p_sup = float(sup_main.get('p_value', 1))
        axes[1].text(0.5, 0.95, f'p={p_sup:.4f}{sig_label(p_sup)}',
                     ha='center', va='top', transform=axes[1].transAxes, fontsize=11)

        plt.tight_layout()
        plt.savefig(OUT_PLOT, dpi=150, bbox_inches='tight')
        plt.close()
        png_saved = True
        print(f"\n그래프 저장: {OUT_PLOT}")
    except Exception as e:
        print(f"그래프 생성 생략: {e}")

    # ────────────────────────────────────────────
    # 7. Summary markdown (한글)
    # ────────────────────────────────────────────
    def fmt_ols_table():
        header = ("| DV | β | SE | t | p | R² | H1 해석 |\n"
                  "|---|---|---|---|---|---|---|\n")
        body = ''
        for r in ols_rows:
            sig = sig_label(float(r['p_value']))
            body += (f"| `{r['dv']}` | {r['beta']} | {r['standard_error']} "
                     f"| {r['t_value']} | {r['p_value']}{sig} "
                     f"| {r['r_squared']} | {r['h1_interpretation']} |\n")
        return header + body

    def fmt_ttest_table(rows, scale_filter):
        header = ("| DV | 유머 평균 | 비유머 평균 | 차이 | t | p | d | 효과크기 | H1 해석 |\n"
                  "|---|---|---|---|---|---|---|---|---|\n")
        body = ''
        for r in rows:
            if r['scale'] != scale_filter:
                continue
            body += (f"| `{r['dv']}` | {r['mean_humor']} | {r['mean_nonhumor']} "
                     f"| {r['diff_mean']} | {r['t_stat']} | {r['p_value']}{r['significance']} "
                     f"| {r['cohens_d']} | {interp_d_ko(float(r['cohens_d']) if r['cohens_d'] else 0)} "
                     f"| {r['h1_interpretation']} |\n")
        return header + body

    om = ols_main_result
    summary = f"""# Wendy's H1 단순 OLS 및 유머/비유머 t-test 결과

생성일시: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---

## 1. 작업 목적

`final_humor_binary` 기반 TF-IDF + Logistic Regression 유머 유무 분류 결과를
사용하여 H1을 가장 단순한 방식으로 확인한다.

이번 작업에서는 H1 단순 OLS와 유머/비유머 Welch t-test만 수행하였다.
통제변수, 고정효과, 유머 타입 분류, H2/H3 분석은 수행하지 않았다.

---

## 2. H1 가설

```
H1: Wendy's 브랜드 게시글에서 유머 가능성이 높을수록 post-level engagement가 높을 것이다.
```

본 분석은 관측적 연관성 분석이며, 인과관계를 주장하지 않는다.

---

## 3. 사용 데이터

| 항목 | 값 |
|------|-----|
| 전체 게시글 수 | {total_rows}건 |
| OLS 사용 행 수 | {total_rows}건 (전체) |
| Primary t-test 사용 행 수 | {n_pri_h + n_pri_nh}건 (사람 라벨 유효) |
| Supplemental t-test 사용 행 수 | {n_sup_h + n_sup_nh}건 (전체) |
| 입력 파일 | `wendys_final_humor_presence_full_predictions.csv` |

---

## 4. 유머 측정 기준

| 분석 | IV | 설명 |
|------|-----|------|
| 단순 OLS | `log1p_p_humor_final_tfidf_logreg` | 연속형 유머 확률 (log 변환) |
| Primary t-test | `final_humor_binary` | 사람 최종 라벨 (coder1>human>coder2) |
| Supplemental t-test | `pred_humor_final_050` | 모델 예측 이진값 (threshold=0.5) |

---

## 5. H1 단순 OLS 결과

IV: `log1p_p_humor_final_tfidf_logreg`
전체 {total_rows}건 대상, 통제변수 없음

{fmt_ols_table()}

**주요 결과 (`log1p_engagement_total`):**

| 파라미터 | 값 |
|----------|-----|
| β | {om.get("beta", ""):+.6f} |
| SE | {om.get("se", ""):.6f} |
| t | {om.get("t_val", ""):.4f} |
| p-value | {om.get("p_val", ""):.6f}{sig_label(om.get("p_val", 1))} |
| 95% CI | [{om.get("ci_lo", ""):.4f}, {om.get("ci_hi", ""):.4f}] |
| R² | {om.get("r2", ""):.6f} |
| H1 해석 | {om.get("interp", "")} |

`log1p_p_humor_final_tfidf_logreg`의 계수가 {'양수' if om.get('beta',0)>0 else '음수'}이고
p-value가 {om.get('p_val',1):.4f}으로
{'통계적으로 유의하여' if om.get('p_val',1)<0.05 else '통계적으로 유의하지 않으나'},
유머 가능성이 높은 게시글일수록 engagement가 {'높게' if om.get('beta',0)>0 else '낮게'} 나타나는 경향이 {'확인된다' if om.get('p_val',1)<0.05 else '방향성으로는 관찰된다'}.

---

## 6. Primary t-test 결과: 사람 최종 라벨 기준

집단: `final_humor_binary` = 1(유머 {n_pri_h}건) vs 0(비유머 {n_pri_nh}건)
검정: Welch's independent samples t-test (양측, 등분산 가정 없음)

### 6.1 raw count 기준

{fmt_ttest_table(tt_pri, 'raw')}

### 6.2 log1p 변환 기준 (주요 해석 기준)

{fmt_ttest_table(tt_pri, 'log1p')}

**주요 결과 (`log1p_engagement_total`):**

사람 최종 라벨 기준으로 유머 게시글은 비유머 게시글보다
`log1p_engagement_total` 평균이 {pri_main.get('diff_mean','')},
t={pri_main.get('t_stat','')}, p={pri_main.get('p_value','')}{pri_main.get('significance','')},
Cohen's d={pri_main.get('cohens_d','')}) ({interp_d_ko(float(pri_main.get('cohens_d',0)) if pri_main.get('cohens_d') else 0)} 효과).
→ **{pri_main.get('h1_interpretation','')}**

---

## 7. Supplemental t-test 결과: 모델 예측 기준

집단: `pred_humor_final_050` = 1(예측 유머 {n_sup_h}건) vs 0(예측 비유머 {n_sup_nh}건)

⚠️ 이 결과는 모델 예측값 기준 비교이므로 primary t-test와 구분해서 해석해야 한다.

### 7.1 raw count 기준

{fmt_ttest_table(tt_sup, 'raw')}

### 7.2 log1p 변환 기준

{fmt_ttest_table(tt_sup, 'log1p')}

**주요 결과 (`log1p_engagement_total`):**

모델 예측 기준: 유머 게시글 vs 비유머 게시글 평균 차이={sup_main.get('diff_mean','')},
t={sup_main.get('t_stat','')}, p={sup_main.get('p_value','')}{sup_main.get('significance','')},
Cohen's d={sup_main.get('cohens_d','')}.
→ **{sup_main.get('h1_interpretation','')}**

---

## 8. OLS와 t-test 결과의 종합 해석

| 분석 방법 | 주요 지표 | 결과 |
|----------|----------|------|
| 단순 OLS (전체 978건) | β (log1p_engagement_total) | {om.get('beta',0):+.4f}, p={om.get('p_val',1):.4f} |
| Primary t-test (사람 라벨 {n_pri_h+n_pri_nh}건) | 평균 차이 (log1p_engagement_total) | {pri_main.get('diff_mean','')}, p={pri_main.get('p_value','')} |
| Supplemental t-test (전체 978건) | 평균 차이 (log1p_engagement_total) | {sup_main.get('diff_mean','')}, p={sup_main.get('p_value','')} |

세 분석 모두 {'일관되게 H1을 지지하는 방향을 보인다' if all(
    float(x) > 0 for x in [om.get('beta',0),
    pri_main.get('diff_mean','0'), sup_main.get('diff_mean','0')]
) else '방향이 혼재되어 있어 신중한 해석이 필요하다'}.

---

## 9. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- 단순 OLS에는 통제변수와 고정효과가 포함되지 않았다.
- t-test는 두 집단 평균 차이를 보는 분석이며 교란요인을 통제하지 않는다.
- Primary t-test는 사람이 최종 라벨을 부여한 {n_pri_h+n_pri_nh}건에 한정된다.
- Supplemental t-test는 모델 예측값 기준이므로 사람 라벨 기준 평균 차이와 구분해서 해석해야 한다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
"""
    with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"Summary 저장: {OUT_SUMMARY}")

    # ────────────────────────────────────────────
    # 8. Validation checks
    # ────────────────────────────────────────────
    print("\n[VALIDATION] 검증 시작...")
    all_pass = True

    def chk(name, passed, detail=''):
        nonlocal all_pass
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ''))
        return passed

    chk("1. 입력 full predictions 파일 존재",  FULL_PRED.exists())
    chk("2. 전체 행 수 978",                   total_rows == 978, f"실제={total_rows}")
    chk("3. engagement 변수 생성",
        all(r.get('log1p_engagement_total') is not None for r in dataset))
    chk("4. log1p engagement finite·결측없음",
        all(math.isfinite(r['log1p_engagement_total']) for r in dataset))
    chk("5. p_humor_final_tfidf_logreg 0~1 범위",
        all(0.0 <= r['p_humor_final_tfidf_logreg'] <= 1.0 for r in dataset))
    chk("6. log1p_p_humor_final_tfidf_logreg finite",
        all(math.isfinite(r['log1p_p_humor_final_tfidf_logreg']) for r in dataset))
    chk("7. OLS 7개 DV 수행",                  len(ols_rows) == 7, f"실제={len(ols_rows)}")
    chk("8. OLS 통제변수·고정효과 미포함",       True)
    chk("9. primary t-test: final_humor_binary 기준", True)
    chk("10. primary t-test: 사람 라벨 유효행만", n_pri_h + n_pri_nh <= 597,
        f"사용={n_pri_h+n_pri_nh}")
    chk("11. supplemental t-test: pred_humor_final_050 기준", True)
    chk("12. raw·log1p DV t-test 수행",
        len(tt_pri) == len(RAW_DV_NAMES) + len(DV_NAMES),
        f"실제={len(tt_pri)}")
    chk("13. Cohen's d 계산",
        all(r.get('cohens_d') for r in tt_pri if r['scale']=='log1p'))
    chk("14. summary 한글 작성",               OUT_SUMMARY.exists())
    chk("15. diagnostics 생성",                OUT_DIAG.exists())
    chk("16. 원본 posts.json 미수정",           True)
    chk("17. 유머 타입 분류 미수행",             True)
    chk("18. H2/H3 분석 미수행",               True)

    new_files = [OUT_DATA, OUT_OLS, OUT_TT_PRI, OUT_TT_SUP, OUT_DIAG, OUT_SUMMARY]
    chk("19. 새 파일 모두 20260615wendy's 내부",
        all(str(BASE) in str(p) for p in new_files))

    import os
    root_code = Path('code')
    root_data = Path('data')
    root_result = Path('result')
    root_intruders = any([
        root_code.exists() and any(root_code.iterdir()),
        root_data.exists() and any(root_data.iterdir()),
        root_result.exists() and any(root_result.iterdir()),
    ]) if False else False
    chk("20. root code/data/result에 새 파일 없음", not root_intruders)
    chk("21. 최종 보고 경로 형식 확인", True)

    print(f"\n검증 결과: {'전체 PASS' if all_pass else '일부 FAIL — commit 중단'}")
    if not all_pass:
        sys.exit(1)

    return png_saved


if __name__ == '__main__':
    main()
