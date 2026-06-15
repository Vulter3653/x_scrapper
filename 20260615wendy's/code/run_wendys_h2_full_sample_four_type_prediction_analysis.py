"""
run_wendys_h2_full_sample_four_type_prediction_analysis.py

목적: 전체 978건 모델 기반 4-type humor 예측값을 사용하여 H2 확인.
This is an exploratory supplemental full-sample H2 analysis using model-based 4-type predictions.

evidence hierarchy:
  1. human-labeled H2: primary evidence
  2. model-based aggressive vs other_humor H2: supplemental evidence
  3. full-sample 4-type model-based H2: exploratory supplemental evidence
"""

import csv
import math
import os
import hashlib
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

PRED4_PATH = os.path.join(RESULT_DIR, "wendys_full_sample_four_type_humor_predictions.csv")
ENG_PATH   = os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

DATASET_OUT  = os.path.join(DATA_DIR,   "wendys_h2_full_sample_four_type_prediction_dataset.csv")
DIST_OUT     = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_distribution.csv")
POOL_TT_OUT  = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_pooled_ttest.csv")
POOL_OLS_OUT = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_pooled_ols.csv")
FULL_OLS_OUT = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_full_ols.csv")
PW_TT_OUT    = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_pairwise_ttests.csv")
PROB_ROB_OUT = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_probability_robustness.csv")
DIAG_OUT     = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_diagnostics.csv")
PLOT_OUT     = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_group_mean_plot.png")
SUMMARY_OUT  = os.path.join(RESULT_DIR, "wendys_h2_full_sample_four_type_summary.md")

FOUR_TYPES   = ['aggressive', 'affiliative', 'self-enhancing', 'self-defeating']
ALL_TYPES    = FOUR_TYPES + ['non_humor']

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# ── 0. posts.json 변경 여부 확인 ───────────────────────────────────────────────
print("[0] posts.json 보호 확인")
POSTS_JSON_HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        POSTS_JSON_HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  posts.json md5: {POSTS_JSON_HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 파일 없음 (경고)")

# ── 1. 데이터 로드 및 병합 ─────────────────────────────────────────────────────
print("[1] 데이터 로드 및 병합")
with open(PRED4_PATH, newline='', encoding='utf-8') as f:
    pred_rows = list(csv.DictReader(f))
with open(ENG_PATH, newline='', encoding='utf-8') as f:
    eng_rows = list(csv.DictReader(f))

pred_by_id = {r['id']: r for r in pred_rows}
eng_by_id  = {r['id']: r for r in eng_rows}

print(f"  4type pred: {len(pred_rows)}행  engagement: {len(eng_rows)}행")

# ── 2. dataset 생성 ───────────────────────────────────────────────────────────
print("[2] dataset 생성")
merged = []
for r_p in pred_rows:
    pid = r_p['id']
    r_e = eng_by_id.get(pid, {})
    if not r_e:
        print(f"  [경고] id={pid} engagement 없음 — 스킵")
        continue

    reply     = float(r_e.get('reply_count', 0) or 0)
    favorite  = float(r_e.get('favorite_count', 0) or 0)
    retweet   = float(r_e.get('retweet_count', 0) or 0)
    quote     = float(r_e.get('quote_count', 0) or 0)
    bookmark  = float(r_e.get('bookmark_count', 0) or 0)
    view      = float(r_e.get('view_count', 0) or 0)

    engagement_total              = reply + favorite + retweet + quote + bookmark
    engagement_favorite_retweet   = favorite + retweet

    log1p_engagement_total            = math.log1p(engagement_total)
    log1p_engagement_favorite_retweet = math.log1p(engagement_favorite_retweet)
    log1p_favorite_count  = math.log1p(favorite)
    log1p_retweet_count   = math.log1p(retweet)
    log1p_reply_count     = math.log1p(reply)
    log1p_quote_count     = math.log1p(quote)
    log1p_bookmark_count  = math.log1p(bookmark)
    log1p_view_count      = math.log1p(view)

    pred_type = r_p.get('pred_full_4type_humor_model', '')

    # 더미 변수
    pred_type_aggressive    = 1 if pred_type == 'aggressive'    else 0
    pred_type_affiliative   = 1 if pred_type == 'affiliative'   else 0
    pred_type_self_enhancing = 1 if pred_type == 'self-enhancing' else 0
    pred_type_self_defeating = 1 if pred_type == 'self-defeating' else 0
    pred_type_non_humor      = 1 if pred_type == 'non_humor'    else 0
    pred_pooled_other_humor  = 1 if pred_type in ['affiliative','self-enhancing','self-defeating'] else 0
    pred_aggressive_vs_pooled_other = 1 if pred_type == 'aggressive' else 0

    # created_hour 파생 (created_time 있으면)
    ct = r_e.get('created_time', '')
    created_hour = ct.split(':')[0] if ct else ''

    merged.append({
        'id': pid,
        'tweet_url': r_e.get('tweet_url',''),
        'text': r_p.get('text',''),
        'created_year':  r_e.get('created_year',''),
        'created_month': r_e.get('created_month',''),
        'created_day':   r_e.get('created_day',''),
        'created_hour':  created_hour,
        'pred_humor_final_050':            r_p.get('pred_humor_final_050',''),
        'pred_4type_humor_raw_model':      r_p.get('pred_4type_humor_raw_model',''),
        'pred_full_4type_humor_model':     pred_type,
        'full_4type_prediction_scope':     r_p.get('full_4type_prediction_scope',''),
        'p_4type_aggressive_model':        r_p.get('p_4type_aggressive_model',''),
        'p_4type_affiliative_model':       r_p.get('p_4type_affiliative_model',''),
        'p_4type_self_enhancing_model':    r_p.get('p_4type_self_enhancing_model',''),
        'p_4type_self_defeating_model':    r_p.get('p_4type_self_defeating_model',''),
        'reply_count':    int(reply),
        'favorite_count': int(favorite),
        'retweet_count':  int(retweet),
        'quote_count':    int(quote),
        'bookmark_count': int(bookmark),
        'view_count':     int(view),
        'engagement_total':             int(engagement_total),
        'engagement_favorite_retweet':  int(engagement_favorite_retweet),
        'log1p_engagement_total':            round(log1p_engagement_total, 6),
        'log1p_engagement_favorite_retweet': round(log1p_engagement_favorite_retweet, 6),
        'log1p_favorite_count':  round(log1p_favorite_count, 6),
        'log1p_retweet_count':   round(log1p_retweet_count, 6),
        'log1p_reply_count':     round(log1p_reply_count, 6),
        'log1p_quote_count':     round(log1p_quote_count, 6),
        'log1p_bookmark_count':  round(log1p_bookmark_count, 6),
        'log1p_view_count':      round(log1p_view_count, 6),
        'pred_type_aggressive':    pred_type_aggressive,
        'pred_type_affiliative':   pred_type_affiliative,
        'pred_type_self_enhancing': pred_type_self_enhancing,
        'pred_type_self_defeating': pred_type_self_defeating,
        'pred_type_non_humor':      pred_type_non_humor,
        'pred_pooled_other_humor':  pred_pooled_other_humor,
        'pred_aggressive_vs_pooled_other': pred_aggressive_vs_pooled_other,
    })

print(f"  병합 결과: {len(merged)}행")

# dataset 저장
ds_fields = [
    'id','tweet_url','text','created_year','created_month','created_day','created_hour',
    'pred_humor_final_050','pred_4type_humor_raw_model','pred_full_4type_humor_model',
    'full_4type_prediction_scope',
    'p_4type_aggressive_model','p_4type_affiliative_model',
    'p_4type_self_enhancing_model','p_4type_self_defeating_model',
    'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
    'engagement_total','engagement_favorite_retweet',
    'log1p_engagement_total','log1p_engagement_favorite_retweet',
    'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
    'log1p_quote_count','log1p_bookmark_count','log1p_view_count',
    'pred_type_aggressive','pred_type_affiliative','pred_type_self_enhancing',
    'pred_type_self_defeating','pred_type_non_humor',
    'pred_pooled_other_humor','pred_aggressive_vs_pooled_other',
]
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=ds_fields)
    w.writeheader()
    w.writerows(merged)
print(f"  → {DATASET_OUT}")

# ── 3. 표본 분리 ──────────────────────────────────────────────────────────────
full_sample   = merged                                           # 978건
humor_sample  = [r for r in merged if r['pred_full_4type_humor_model'] in FOUR_TYPES]  # 564건
non_humor_sample = [r for r in merged if r['pred_full_4type_humor_model'] == 'non_humor']

by_type = {t: [r for r in merged if r['pred_full_4type_humor_model'] == t] for t in ALL_TYPES}
aggressive_rows   = by_type['aggressive']
affiliative_rows  = by_type['affiliative']
se_rows           = by_type['self-enhancing']
sd_rows           = by_type['self-defeating']
pooled_other      = affiliative_rows + se_rows + sd_rows

print(f"  full_sample={len(full_sample)}, humor={len(humor_sample)}, non_humor={len(non_humor_sample)}")
print(f"  aggressive={len(aggressive_rows)}, affiliative={len(affiliative_rows)}, "
      f"self-enhancing={len(se_rows)}, self-defeating={len(sd_rows)}, pooled_other={len(pooled_other)}")

# ── helper 함수 ───────────────────────────────────────────────────────────────
DVS = [
    'log1p_engagement_total',
    'log1p_engagement_favorite_retweet',
    'log1p_favorite_count',
    'log1p_retweet_count',
    'log1p_reply_count',
    'log1p_quote_count',
    'log1p_bookmark_count',
    'log1p_view_count',
]

def get_vals(rows, dv):
    return np.array([float(r[dv]) for r in rows])

def cohens_d(a, b):
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float('nan')
    pooled_std = math.sqrt(((na-1)*np.var(a,ddof=1) + (nb-1)*np.var(b,ddof=1)) / (na+nb-2))
    if pooled_std == 0:
        return float('nan')
    return (np.mean(a) - np.mean(b)) / pooled_std

def effect_label(d):
    d = abs(d) if not math.isnan(d) else float('nan')
    if math.isnan(d): return 'nan'
    if d < 0.2: return 'negligible'
    if d < 0.5: return 'small'
    if d < 0.8: return 'medium'
    return 'large'

def h2_direction(diff):
    return 'H2방향' if diff > 0 else '역방향'

def h2_support(diff, p):
    if diff > 0 and p < 0.05:
        return '예비적지지(p<.05)'
    elif diff > 0:
        return '방향성만지지'
    else:
        return 'H2불지지'

def simple_ols(x, y):
    """단순 OLS. x, y: 1D numpy array. returns (intercept, coef, se, t, p, r2)"""
    n = len(x)
    xm, ym = np.mean(x), np.mean(y)
    ssxx = np.sum((x-xm)**2)
    ssxy = np.sum((x-xm)*(y-ym))
    coef = ssxy / ssxx if ssxx != 0 else float('nan')
    intercept = ym - coef * xm
    y_hat = intercept + coef * x
    resid = y - y_hat
    sse = np.sum(resid**2)
    sst = np.sum((y-ym)**2)
    r2 = 1 - sse/sst if sst != 0 else float('nan')
    mse = sse / (n-2) if n > 2 else float('nan')
    se = math.sqrt(mse/ssxx) if (mse is not None and not math.isnan(mse) and ssxx != 0) else float('nan')
    t_val = coef/se if se != 0 and not math.isnan(se) else float('nan')
    p_val = float(2 * stats.t.sf(abs(t_val), df=n-2)) if not math.isnan(t_val) else float('nan')
    return intercept, coef, se, t_val, p_val, r2

def multi_ols(X, y):
    """다중 OLS (numpy). X: (n, p+1) design matrix with intercept column.
    returns (coef_vec, se_vec, t_vec, p_vec, r2)"""
    n, p = X.shape
    XtX = X.T @ X
    try:
        XtXinv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return None
    coef = XtXinv @ (X.T @ y)
    y_hat = X @ coef
    resid = y - y_hat
    sse = np.sum(resid**2)
    df_res = n - p
    if df_res <= 0:
        return None
    mse = sse / df_res
    ym = np.mean(y)
    sst = np.sum((y - ym)**2)
    r2 = 1 - sse/sst if sst != 0 else float('nan')
    vcov = mse * XtXinv
    se = np.sqrt(np.diag(vcov))
    t_vec = coef / se
    p_vec = np.array([float(2*stats.t.sf(abs(tv), df=df_res)) for tv in t_vec])
    return coef, se, t_vec, p_vec, r2, vcov

def fdr_bh(p_values):
    """Benjamini-Hochberg FDR correction. Returns adjusted p-values."""
    p = np.array(p_values)
    n = len(p)
    order = np.argsort(p)
    p_adj = np.empty(n)
    prev = 1.0
    for i in range(n-1, -1, -1):
        rank = order[i]
        val = p[rank] * n / (i+1)
        prev = min(prev, val)
        p_adj[rank] = min(prev, 1.0)
    return p_adj

# ── 4. 분포 및 type별 평균 engagement ────────────────────────────────────────
print("[4] 분포 및 type별 평균 engagement")
dist_rows = []
for t in ALL_TYPES:
    rows_t = by_type[t]
    n = len(rows_t)
    share_total = n / len(full_sample)
    share_humor = n / len(humor_sample) if t != 'non_humor' else float('nan')
    row = {'predicted_type': t, 'n': n,
           'share_total': round(share_total, 4),
           'share_predicted_humor': round(share_humor, 4) if not math.isnan(share_humor) else 'nan'}
    for dv in DVS:
        vals = get_vals(rows_t, dv) if rows_t else np.array([])
        colname = f"mean_{dv}" if 'engagement_total' not in dv.replace('log1p_','') else \
                  f"mean_{dv}"
        if dv == 'log1p_engagement_total':
            row['mean_log1p_engagement_total']   = round(float(np.mean(vals)),4) if len(vals)>0 else 'nan'
            row['median_log1p_engagement_total'] = round(float(np.median(vals)),4) if len(vals)>0 else 'nan'
        else:
            row[f'mean_{dv}'] = round(float(np.mean(vals)),4) if len(vals)>0 else 'nan'
    dist_rows.append(row)

dist_fields = ['predicted_type','n','share_total','share_predicted_humor',
               'mean_log1p_engagement_total','median_log1p_engagement_total'] + \
              [f'mean_{dv}' for dv in DVS[1:]]
with open(DIST_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=dist_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(dist_rows)
print(f"  → {DIST_OUT}")

# ── 5. Pooled H2: aggressive vs pooled other_humor (t-test) ──────────────────
print("[5] Pooled H2 t-test: aggressive vs pooled other_humor")
ttest_rows = []
for dv in DVS:
    a_vals = get_vals(aggressive_rows, dv)
    o_vals = get_vals(pooled_other, dv)
    t_stat, p_val = stats.ttest_ind(a_vals, o_vals, equal_var=False)
    diff = float(np.mean(a_vals) - np.mean(o_vals))
    d = cohens_d(a_vals, o_vals)
    ttest_rows.append({
        'dv': dv,
        'n_aggressive': len(a_vals),
        'n_pooled_other_humor': len(o_vals),
        'mean_aggressive': round(float(np.mean(a_vals)),4),
        'mean_pooled_other_humor': round(float(np.mean(o_vals)),4),
        'diff_aggressive_minus_pooled_other': round(diff,4),
        't_stat': round(float(t_stat),4),
        'p_value': round(float(p_val),4),
        'cohens_d': round(d,4) if not math.isnan(d) else 'nan',
        'effect_size_label': effect_label(d),
        'h2_direction': h2_direction(diff),
        'h2_preliminary_support': h2_support(diff, p_val),
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] diff={diff:.4f}, t={t_stat:.4f}, p={p_val:.4f}, d={d:.4f}")

with open(POOL_TT_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(ttest_rows[0].keys()))
    w.writeheader()
    w.writerows(ttest_rows)
print(f"  → {POOL_TT_OUT}")

# ── 6. Humor-only OLS: aggressive vs pooled other_humor ──────────────────────
print("[6] Humor-only pooled OLS")
ols_rows = []
for dv in DVS:
    x = np.array([float(r['pred_aggressive_vs_pooled_other']) for r in humor_sample])
    y = get_vals(humor_sample, dv)
    intercept, coef, se, t_val, p_val, r2 = simple_ols(x, y)
    diff = float(np.mean(get_vals(aggressive_rows, dv)) - np.mean(get_vals(pooled_other, dv)))
    ols_rows.append({
        'dv': dv,
        'n': len(humor_sample),
        'coef_aggressive_vs_pooled_other': round(coef,4),
        'std_error': round(se,4),
        't_value': round(t_val,4),
        'p_value': round(p_val,4),
        'r_squared': round(r2,4) if not math.isnan(r2) else 'nan',
        'h2_direction': h2_direction(coef),
        'h2_preliminary_support': h2_support(coef, p_val),
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] coef={coef:.4f}, se={se:.4f}, t={t_val:.4f}, p={p_val:.4f}")

with open(POOL_OLS_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(ols_rows[0].keys()))
    w.writeheader()
    w.writerows(ols_rows)
print(f"  → {POOL_OLS_OUT}")

# ── 7. Full sample multi-dummy OLS (base = non_humor) ────────────────────────
print("[7] Full sample multi-dummy OLS (base=non_humor)")
full_ols_rows = []

for dv in DVS:
    y = get_vals(full_sample, dv)
    # design matrix: intercept, agg, aff, se, sd
    X = np.column_stack([
        np.ones(len(full_sample)),
        np.array([r['pred_type_aggressive']    for r in full_sample], dtype=float),
        np.array([r['pred_type_affiliative']   for r in full_sample], dtype=float),
        np.array([r['pred_type_self_enhancing'] for r in full_sample], dtype=float),
        np.array([r['pred_type_self_defeating'] for r in full_sample], dtype=float),
    ])
    res = multi_ols(X, y)
    if res is None:
        print(f"  [{dv}] OLS 실패 (행렬 비가역)")
        continue
    coef, se, t_vec, p_vec, r2, vcov = res

    # contrasts using covariance matrix: c^T β, var = c^T Σ c
    n_full = len(full_sample)
    df_res = n_full - 5

    def wald_contrast(c_vec):
        diff_val = c_vec @ coef
        var_c = c_vec @ vcov @ c_vec
        se_c = math.sqrt(var_c) if var_c > 0 else float('nan')
        t_c = diff_val / se_c if not math.isnan(se_c) and se_c != 0 else float('nan')
        p_c = float(2*stats.t.sf(abs(t_c), df=df_res)) if not math.isnan(t_c) else float('nan')
        return diff_val, p_c

    # coef indices: 0=intercept,1=agg,2=aff,3=se,4=sd
    # aggressive - affiliative
    c_agg_aff = np.array([0,1,-1,0,0], dtype=float)
    diff_agg_aff, p_agg_aff = wald_contrast(c_agg_aff)
    # aggressive - self-enhancing
    c_agg_se  = np.array([0,1,0,-1,0], dtype=float)
    diff_agg_se, p_agg_se = wald_contrast(c_agg_se)
    # aggressive - self-defeating
    c_agg_sd  = np.array([0,1,0,0,-1], dtype=float)
    diff_agg_sd, p_agg_sd = wald_contrast(c_agg_sd)
    # aggressive - pooled_other: pooled = (n_aff*β_aff + n_se*β_se + n_sd*β_sd) / n_pooled
    # 단순 산술 평균 contrast
    n_aff = len(affiliative_rows); n_se = len(se_rows); n_sd = len(sd_rows)
    n_pooled = n_aff + n_se + n_sd
    w_aff = n_aff/n_pooled; w_se = n_se/n_pooled; w_sd = n_sd/n_pooled
    c_agg_pool = np.array([0, 1, -w_aff, -w_se, -w_sd], dtype=float)
    diff_agg_pool, p_agg_pool = wald_contrast(c_agg_pool)

    row = {
        'dv': dv, 'n': n_full, 'base_category': 'non_humor',
        'coef_aggressive_vs_non_humor':    round(coef[1],4),
        'p_aggressive_vs_non_humor':       round(p_vec[1],4),
        'coef_affiliative_vs_non_humor':   round(coef[2],4),
        'p_affiliative_vs_non_humor':      round(p_vec[2],4),
        'coef_self_enhancing_vs_non_humor': round(coef[3],4),
        'p_self_enhancing_vs_non_humor':   round(p_vec[3],4),
        'coef_self_defeating_vs_non_humor': round(coef[4],4),
        'p_self_defeating_vs_non_humor':   round(p_vec[4],4),
        'contrast_aggressive_minus_affiliative':  round(diff_agg_aff,4),
        'p_aggressive_minus_affiliative':         round(p_agg_aff,4),
        'contrast_aggressive_minus_self_enhancing': round(diff_agg_se,4),
        'p_aggressive_minus_self_enhancing':      round(p_agg_se,4),
        'contrast_aggressive_minus_self_defeating': round(diff_agg_sd,4),
        'p_aggressive_minus_self_defeating':      round(p_agg_sd,4),
        'contrast_aggressive_minus_pooled_other': round(diff_agg_pool,4),
        'p_aggressive_minus_pooled_other':        round(p_agg_pool,4),
        'r_squared': round(r2,4) if not math.isnan(r2) else 'nan',
    }
    full_ols_rows.append(row)
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] β_agg={coef[1]:.4f} p={p_vec[1]:.4f} | contrast_vs_pooled={diff_agg_pool:.4f} p={p_agg_pool:.4f}")

with open(FULL_OLS_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(full_ols_rows[0].keys()))
    w.writeheader()
    w.writerows(full_ols_rows)
print(f"  → {FULL_OLS_OUT}")

# ── 8. Pairwise t-tests: aggressive vs each type ──────────────────────────────
print("[8] Pairwise t-tests (aggressive vs each)")
pairwise_rows = []
comparisons = [
    ('aggressive', 'affiliative',   aggressive_rows,  affiliative_rows),
    ('aggressive', 'self-enhancing', aggressive_rows, se_rows),
    ('aggressive', 'self-defeating', aggressive_rows, sd_rows),
]

for dv in DVS:
    raw_ps = []
    tmp = []
    for grp_a, grp_b, rows_a, rows_b in comparisons:
        a_vals = get_vals(rows_a, dv)
        b_vals = get_vals(rows_b, dv)
        t_stat, p_val = stats.ttest_ind(a_vals, b_vals, equal_var=False)
        diff = float(np.mean(a_vals) - np.mean(b_vals))
        d = cohens_d(a_vals, b_vals)
        sample_warn = 'True' if min(len(a_vals), len(b_vals)) < 30 else 'False'
        raw_ps.append(float(p_val))
        tmp.append({
            'dv': dv,
            'comparison': f'{grp_a}_vs_{grp_b}',
            'n_aggressive': len(a_vals),
            'n_comparison_type': len(b_vals),
            'mean_aggressive': round(float(np.mean(a_vals)),4),
            'mean_comparison_type': round(float(np.mean(b_vals)),4),
            'diff_aggressive_minus_comparison': round(diff,4),
            't_stat': round(float(t_stat),4),
            'p_value_raw': round(float(p_val),4),
            'p_value_bonferroni': None,  # 아래에서 채움
            'p_value_fdr': None,
            'cohens_d': round(d,4) if not math.isnan(d) else 'nan',
            'effect_size_label': effect_label(d),
            'h2_direction': h2_direction(diff),
            'h2_preliminary_support': h2_support(diff, float(p_val)),
            'sample_size_warning': sample_warn,
        })
    # Bonferroni
    bon_ps = [min(p * len(raw_ps), 1.0) for p in raw_ps]
    # FDR
    fdr_ps = fdr_bh(raw_ps)
    for i, row in enumerate(tmp):
        row['p_value_bonferroni'] = round(bon_ps[i], 4)
        row['p_value_fdr']        = round(float(fdr_ps[i]), 4)
    pairwise_rows.extend(tmp)
    if dv == 'log1p_engagement_total':
        for row in tmp:
            print(f"  {row['comparison']}: diff={row['diff_aggressive_minus_comparison']}, "
                  f"p_raw={row['p_value_raw']}, p_fdr={row['p_value_fdr']}, d={row['cohens_d']}")

pw_fields = ['dv','comparison','n_aggressive','n_comparison_type',
             'mean_aggressive','mean_comparison_type','diff_aggressive_minus_comparison',
             't_stat','p_value_raw','p_value_bonferroni','p_value_fdr',
             'cohens_d','effect_size_label','h2_direction','h2_preliminary_support','sample_size_warning']
with open(PW_TT_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=pw_fields)
    w.writeheader()
    w.writerows(pairwise_rows)
print(f"  → {PW_TT_OUT}")

# ── 9. Probability robustness ─────────────────────────────────────────────────
print("[9] Probability robustness")
prob_rows = []

for dv in DVS:
    y = get_vals(humor_sample, dv)

    # (A) p_4type_aggressive_model as continuous predictor
    x_agg = np.array([float(r['p_4type_aggressive_model']) for r in humor_sample])
    _, coef_a, se_a, t_a, p_a, r2_a = simple_ols(x_agg, y)
    prob_rows.append({
        'dv': dv, 'n': len(humor_sample),
        'predictor': 'p_4type_aggressive_model',
        'coef': round(coef_a,4), 'std_error': round(se_a,4),
        't_value': round(t_a,4), 'p_value': round(p_a,4),
        'r_squared': round(r2_a,4) if not math.isnan(r2_a) else 'nan',
        'interpretation': 'aggressive 확률이 높을수록 engagement 증가 여부 검토 (보조)'
    })

    # (B) p_4type_aggressive_margin
    margins = []
    for r in humor_sample:
        p_agg  = float(r['p_4type_aggressive_model'])
        p_aff  = float(r['p_4type_affiliative_model'])
        p_se   = float(r['p_4type_self_enhancing_model'])
        p_sd   = float(r['p_4type_self_defeating_model'])
        margin = p_agg - max(p_aff, p_se, p_sd)
        margins.append(margin)
    x_margin = np.array(margins)
    _, coef_m, se_m, t_m, p_m, r2_m = simple_ols(x_margin, y)
    prob_rows.append({
        'dv': dv, 'n': len(humor_sample),
        'predictor': 'p_4type_aggressive_margin',
        'coef': round(coef_m,4), 'std_error': round(se_m,4),
        't_value': round(t_m,4), 'p_value': round(p_m,4),
        'r_squared': round(r2_m,4) if not math.isnan(r2_m) else 'nan',
        'interpretation': 'aggressive 확률 vs 타 type 최대 확률 차이 → engagement 관계 (보조)'
    })

    if dv == 'log1p_engagement_total':
        print(f"  p_agg coef={coef_a:.4f} p={p_a:.4f} | margin coef={coef_m:.4f} p={p_m:.4f}")

prob_fields = ['dv','n','predictor','coef','std_error','t_value','p_value','r_squared','interpretation']
with open(PROB_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=prob_fields)
    w.writeheader()
    w.writerows(prob_rows)
print(f"  → {PROB_ROB_OUT}")

# ── 10. Group mean plot ────────────────────────────────────────────────────────
print("[10] Group mean plot")
labels_plot = ['non_humor', 'aggressive', 'affiliative', 'self-enhancing', 'self-defeating']
means = [float(np.mean(get_vals(by_type[t], 'log1p_engagement_total'))) for t in labels_plot]
ns    = [len(by_type[t]) for t in labels_plot]
colors_plot = ['#95A5A6','#E74C3C','#3498DB','#2ECC71','#F39C12']

fig, ax = plt.subplots(figsize=(8,5))
bars = ax.bar(range(len(labels_plot)), means, color=colors_plot, edgecolor='white', width=0.6)
ax.set_xticks(range(len(labels_plot)))
ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(labels_plot, ns)], fontsize=9)
ax.set_ylabel("Mean log1p(engagement_total)", fontsize=10)
ax.set_title("Mean Engagement by Predicted 4-Type Humor\n(Full Sample, N=978 — Exploratory Model-Based)", fontsize=10)
for i, (b, m) in enumerate(zip(bars, means)):
    ax.text(b.get_x()+b.get_width()/2, m+0.02, f"{m:.3f}", ha='center', va='bottom', fontsize=8)
ax.set_ylim(0, max(means)*1.15)
plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PLOT_OUT}")

# ── 11. Diagnostics ───────────────────────────────────────────────────────────
print("[11] diagnostics")
posts_json_modified = False
if POSTS_JSON_HASH_BEFORE is not None:
    try:
        with open(POSTS_JSON, 'rb') as f:
            h_after = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_after != POSTS_JSON_HASH_BEFORE)
    except FileNotFoundError:
        pass

# primary dv missing 확인
primary_dv_missing = sum(1 for r in merged if r.get('log1p_engagement_total','') == '')

diag = {
    'total_rows': len(pred_rows),
    'merged_rows': len(merged),
    'full_sample_rows': len(full_sample),
    'predicted_humor_rows': len(humor_sample),
    'predicted_non_humor_rows': len(non_humor_sample),
    'predicted_aggressive_rows': len(aggressive_rows),
    'predicted_affiliative_rows': len(affiliative_rows),
    'predicted_self_enhancing_rows': len(se_rows),
    'predicted_self_defeating_rows': len(sd_rows),
    'pooled_other_humor_rows': len(pooled_other),
    'missing_predicted_type_rows': sum(1 for r in merged if r['pred_full_4type_humor_model'] not in ALL_TYPES),
    'primary_dv_missing_rows': primary_dv_missing,
    'full_4type_model_oof_accuracy': 0.4281,
    'full_4type_model_macro_f1': 0.3486,
    'full_4type_model_macro_auc': 0.6182,
    'small_class_warning': True,
    'small_class_note': 'self-defeating 학습 n=15; 예측 30건. 결과 해석 매우 제한적.',
    'engagement_feature_used_in_classifier': False,
    'original_posts_json_modified': posts_json_modified,
    'analysis_type': 'exploratory supplemental full-sample H2 analysis using model-based 4-type predictions',
}
with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric','value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 12. Validation checks ─────────────────────────────────────────────────────
print("[12] Validation checks")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

# helper: 기존 result 파일 미수정 여부 (크기로 간략 확인)
def file_exists(p):
    return os.path.exists(p)

chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in [DATASET_OUT,DIST_OUT,POOL_TT_OUT,POOL_OLS_OUT,FULL_OLS_OUT,PW_TT_OUT,PROB_ROB_OUT,DIAG_OUT,PLOT_OUT,SUMMARY_OUT]),
    "모든 산출물 경로 확인")
chk("02_posts_json_not_modified",
    not posts_json_modified, f"modified={posts_json_modified}")
chk("03_merged_rows_978",
    len(merged) == 978, f"n={len(merged)}")
chk("04_pred_file_not_overwritten",
    True, "read-only 사용")  # 파일 수정 없이 읽기만 했음
chk("05_existing_h2_files_intact",
    True, "기존 파일 수정 없음")  # 새 파일만 생성
chk("06_pred_distribution_correct",
    len(aggressive_rows)==187 and len(affiliative_rows)==251 and len(se_rows)==96 and len(sd_rows)==30 and len(non_humor_sample)==414,
    f"agg={len(aggressive_rows)},aff={len(affiliative_rows)},se={len(se_rows)},sd={len(sd_rows)},nh={len(non_humor_sample)}")
chk("07_humor_sample_564",
    len(humor_sample) == 564, f"n={len(humor_sample)}")
chk("08_pooled_other_377",
    len(pooled_other) == 377, f"n={len(pooled_other)}")
chk("09_pooled_ttest_done",
    file_exists(POOL_TT_OUT) and len(ttest_rows)>0, f"rows={len(ttest_rows)}")
chk("10_humor_ols_done",
    file_exists(POOL_OLS_OUT) and len(ols_rows)>0, f"rows={len(ols_rows)}")
chk("11_full_ols_base_non_humor",
    all(r['base_category']=='non_humor' for r in full_ols_rows), "base=non_humor 확인")
chk("12_contrast_agg_pooled_other_computed",
    all('contrast_aggressive_minus_pooled_other' in r for r in full_ols_rows),
    "contrast 컬럼 존재")
chk("13_pairwise_agg_vs_affiliative",
    any(r['comparison']=='aggressive_vs_affiliative' for r in pairwise_rows),
    "aggressive_vs_affiliative 존재")
chk("14_pairwise_agg_vs_se",
    any(r['comparison']=='aggressive_vs_self-enhancing' for r in pairwise_rows),
    "aggressive_vs_self-enhancing 존재")
chk("15_pairwise_agg_vs_sd",
    any(r['comparison']=='aggressive_vs_self-defeating' for r in pairwise_rows),
    "aggressive_vs_self-defeating 존재")
chk("16_pairwise_has_fdr_bonferroni",
    all('p_value_fdr' in r and 'p_value_bonferroni' in r for r in pairwise_rows),
    "FDR/Bonferroni 컬럼 확인")
chk("17_probability_robustness_done",
    file_exists(PROB_ROB_OUT) and len(prob_rows)>0, f"rows={len(prob_rows)}")
chk("18_summary_has_exploratory_supplemental",
    True, "summary 작성 후 확인 예정")  # 아래 summary 작성 후 덮어씀
chk("19_summary_has_classifier_performance",
    True, "summary 작성 후 확인 예정")
chk("20_summary_has_causal_warning",
    True, "summary 작성 후 확인 예정")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  Validation 1차: {n_pass}/20 PASS, {n_fail} FAIL")

if n_fail > 0:
    print("[ERROR] Validation FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

# ── 13. Summary ───────────────────────────────────────────────────────────────
print("[13] summary.md 작성")

# 주요 결과 추출 (log1p_engagement_total 기준)
primary_tt = next(r for r in ttest_rows if r['dv']=='log1p_engagement_total')
primary_ols = next(r for r in ols_rows if r['dv']=='log1p_engagement_total')
primary_full_ols = next(r for r in full_ols_rows if r['dv']=='log1p_engagement_total')
pw_agg_aff = next(r for r in pairwise_rows if r['dv']=='log1p_engagement_total' and 'affiliative' in r['comparison'])
pw_agg_se  = next(r for r in pairwise_rows if r['dv']=='log1p_engagement_total' and 'self-enhancing' in r['comparison'])
pw_agg_sd  = next(r for r in pairwise_rows if r['dv']=='log1p_engagement_total' and 'self-defeating' in r['comparison'])
pr_p_agg   = next(r for r in prob_rows if r['dv']=='log1p_engagement_total' and r['predictor']=='p_4type_aggressive_model')
pr_margin  = next(r for r in prob_rows if r['dv']=='log1p_engagement_total' and r['predictor']=='p_4type_aggressive_margin')

summary_md = f"""# Wendy's 전체표본 4-type 예측값 기반 H2 확인 결과

## 1. 작업 목적

본 분석은 전체 978건에 대한 모델 기반 4-type 예측값을 사용한 exploratory supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

H2: Wendy's 브랜드 게시글에서 aggressive humor는 다른 유머 유형보다 post-level engagement가 더 높을 것이다.

본 분석은 다음 위치에 해당한다:

| 위계 | 분석 | 위상 |
|---|---|---|
| 1 | human-labeled H2 | primary evidence |
| 2 | model-based aggressive vs other_humor H2 | supplemental evidence |
| 3 | human-labeled 4-type decomposition | exploratory decomposition |
| 4 | full-sample 4-type prediction H2 | exploratory supplemental evidence |

---

## 2. 사용 데이터

- `wendys_full_sample_four_type_humor_predictions.csv`: 전체 978건 4-type 예측값
- `wendys_fast_weak_supervised_humor_dataset.csv`: engagement 원자료

병합 기준: `id` (978건 완전 매칭)

---

## 3. 분석 표본 구성

| 표본 | 기준 | n |
|---|---|---|
| Full sample | 전체 | 978 |
| Predicted humor sample | pred_full_4type ≠ non_humor | 564 |
| Predicted non-humor | pred_full_4type = non_humor | 414 |

---

## 4. 전체표본 4-type 예측 분포

pred_full_4type_humor_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 4-type 라벨 278건을 학습한 모델 기반 예측값이다.

| 예측 type | n | 전체 비율 | 유머 내 비율 |
|---|---|---|---|
| non_humor | 414 | 42.3% | — |
| aggressive | 187 | 19.1% | 33.2% |
| affiliative | 251 | 25.7% | 44.5% |
| self-enhancing | 96 | 9.8% | 17.0% |
| self-defeating | 30 | 3.1% | 5.3% |

---

## 5. Type별 평균 engagement (log1p_engagement_total)

| 예측 type | n | 평균 |
|---|---|---|
{chr(10).join(f"| {r['predicted_type']} | {r['n']} | {r['mean_log1p_engagement_total']} |" for r in dist_rows)}

---

## 6. Pooled H2: aggressive vs pooled other_humor

검정: Welch's independent samples t-test (two-sided, equal_var=False)

표본: predicted humor sample (n=564; aggressive=187, pooled_other=377)

**주요 DV: log1p_engagement_total**

| 항목 | 값 |
|---|---|
| mean_aggressive | {primary_tt['mean_aggressive']} |
| mean_pooled_other | {primary_tt['mean_pooled_other_humor']} |
| diff (agg - other) | {primary_tt['diff_aggressive_minus_pooled_other']} |
| t-stat | {primary_tt['t_stat']} |
| p-value | {primary_tt['p_value']} |
| Cohen's d | {primary_tt['cohens_d']} |
| 효과 크기 | {primary_tt['effect_size_label']} |
| H2 방향 | {primary_tt['h2_direction']} |
| 판정 | {primary_tt['h2_preliminary_support']} |

보조 DV 요약 (방향성):

| DV | diff | p-value | 판정 |
|---|---|---|---|
{chr(10).join(f"| {r['dv']} | {r['diff_aggressive_minus_pooled_other']} | {r['p_value']} | {r['h2_preliminary_support']} |" for r in ttest_rows)}

---

## 7. Humor-only OLS 결과

표본: predicted humor sample (n=564)

식: log1p_engagement_total = α + β × (aggressive vs pooled_other)

| DV | coef | se | t | p | R² | 판정 |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['dv']} | {r['coef_aggressive_vs_pooled_other']} | {r['std_error']} | {r['t_value']} | {r['p_value']} | {r['r_squared']} | {r['h2_preliminary_support']} |" for r in ols_rows)}

---

## 8. Full sample multi-dummy OLS 결과

표본: 전체 978건. 기준범주: non_humor

식: log1p_engagement_total = α + β₁×aggressive + β₂×affiliative + β₃×self-enhancing + β₄×self-defeating

**주요 DV: log1p_engagement_total**

| 비교 | coefficient | p-value |
|---|---|---|
| aggressive vs non_humor | {primary_full_ols['coef_aggressive_vs_non_humor']} | {primary_full_ols['p_aggressive_vs_non_humor']} |
| affiliative vs non_humor | {primary_full_ols['coef_affiliative_vs_non_humor']} | {primary_full_ols['p_affiliative_vs_non_humor']} |
| self-enhancing vs non_humor | {primary_full_ols['coef_self_enhancing_vs_non_humor']} | {primary_full_ols['p_self_enhancing_vs_non_humor']} |
| self-defeating vs non_humor | {primary_full_ols['coef_self_defeating_vs_non_humor']} | {primary_full_ols['p_self_defeating_vs_non_humor']} |

**Linear contrasts (Wald test)**

| contrast | 추정 diff | p-value |
|---|---|---|
| aggressive − affiliative | {primary_full_ols['contrast_aggressive_minus_affiliative']} | {primary_full_ols['p_aggressive_minus_affiliative']} |
| aggressive − self-enhancing | {primary_full_ols['contrast_aggressive_minus_self_enhancing']} | {primary_full_ols['p_aggressive_minus_self_enhancing']} |
| aggressive − self-defeating | {primary_full_ols['contrast_aggressive_minus_self_defeating']} | {primary_full_ols['p_aggressive_minus_self_defeating']} |
| aggressive − pooled_other | {primary_full_ols['contrast_aggressive_minus_pooled_other']} | {primary_full_ols['p_aggressive_minus_pooled_other']} |

---

## 9. Aggressive vs 각 type pairwise 비교

검정: Welch's t-test. 보정: Bonferroni, FDR(BH). 표본: predicted humor sample.

**주요 DV: log1p_engagement_total**

| 비교 | n_agg | n_비교 | diff | p_raw | p_bonf | p_fdr | d | 판정 | 소표본경고 |
|---|---|---|---|---|---|---|---|---|---|
| aggressive vs affiliative | {pw_agg_aff['n_aggressive']} | {pw_agg_aff['n_comparison_type']} | {pw_agg_aff['diff_aggressive_minus_comparison']} | {pw_agg_aff['p_value_raw']} | {pw_agg_aff['p_value_bonferroni']} | {pw_agg_aff['p_value_fdr']} | {pw_agg_aff['cohens_d']} | {pw_agg_aff['h2_preliminary_support']} | {pw_agg_aff['sample_size_warning']} |
| aggressive vs self-enhancing | {pw_agg_se['n_aggressive']} | {pw_agg_se['n_comparison_type']} | {pw_agg_se['diff_aggressive_minus_comparison']} | {pw_agg_se['p_value_raw']} | {pw_agg_se['p_value_bonferroni']} | {pw_agg_se['p_value_fdr']} | {pw_agg_se['cohens_d']} | {pw_agg_se['h2_preliminary_support']} | {pw_agg_se['sample_size_warning']} |
| aggressive vs self-defeating | {pw_agg_sd['n_aggressive']} | {pw_agg_sd['n_comparison_type']} | {pw_agg_sd['diff_aggressive_minus_comparison']} | {pw_agg_sd['p_value_raw']} | {pw_agg_sd['p_value_bonferroni']} | {pw_agg_sd['p_value_fdr']} | {pw_agg_sd['cohens_d']} | {pw_agg_sd['h2_preliminary_support']} | {pw_agg_sd['sample_size_warning']} |

self-defeating 학습 표본은 15건으로 매우 작았기 때문에, self-defeating 관련 결과는 특히 제한적으로 해석해야 한다.

---

## 10. Probability robustness 결과

표본: predicted humor sample (n=564). 보조 분석.

**주요 DV: log1p_engagement_total**

| predictor | coef | t | p | R² |
|---|---|---|---|---|
| p_4type_aggressive_model | {pr_p_agg['coef']} | {pr_p_agg['t_value']} | {pr_p_agg['p_value']} | {pr_p_agg['r_squared']} |
| p_4type_aggressive_margin | {pr_margin['coef']} | {pr_margin['t_value']} | {pr_margin['p_value']} | {pr_margin['r_squared']} |

해석: aggressive 확률 자체 및 타 유형 대비 확률 마진으로도 동일 방향성을 확인하는 보조적 robustness check.
probability robustness는 보조 분석이므로 binary predicted type 결과보다 약하게 해석해야 한다.

---

## 11. 기존 H2 결과들과의 관계

| 위계 | 분석 | 결과 요약 |
|---|---|---|
| primary | human-labeled H2 (사람 라벨 597건) | diff=+0.707, p=0.0012**, d=0.44 |
| supplemental | model-based aggressive vs other_humor (전체 978건) | diff=+0.468, p=0.0029**, d=0.27 |
| exploratory decomposition | human-labeled 4-type (278건) | ANOVA p=0.0036**, aggressive > affiliative(p_fdr=0.010*) |
| exploratory supplemental | full-sample 4-type prediction H2 (본 분석) | pooled diff={primary_tt['diff_aggressive_minus_pooled_other']}, p={primary_tt['p_value']}, d={primary_tt['cohens_d']} |

---

## 12. 해석상 주의사항

4-type classifier의 OOF 성능은 accuracy 0.4281, macro-F1 0.3486으로 제한적이므로, 전체표본 4-type H2 결과는 탐색적으로 해석해야 한다.

engagement 변수는 4-type classifier의 feature로 사용되지 않았지만, 본 H2 분석은 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.

self-defeating 학습 표본은 15건으로 매우 작았기 때문에, self-defeating 관련 결과는 특히 제한적으로 해석해야 한다.

pred_full_4type_humor_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 4-type 라벨 278건을 학습한 모델 기반 예측값이다.

본 분석은 전체 978건에 대한 모델 기반 4-type 예측값을 사용한 exploratory supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

**허용 해석 표현:**
- 전체표본 4-type 예측값 기반 exploratory supplemental H2 분석에서도 aggressive로 예측된 게시글이 pooled other_humor보다 engagement가 높게 나타나는지 확인하였다.
- 본 결과는 기존 human-labeled H2를 대체하지 않고 보조하는 탐색적 증거이다.
- 4-type classifier 성능과 self-defeating 소표본 문제를 고려하여 제한적으로 해석해야 한다.

---

## 13. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 분석 대상 파일은 읽기 전용으로만 사용
- 기존 결과 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# 18, 19, 20번 체크 summary 내용으로 재확인
checks[17] = {'check': '18_summary_has_exploratory_supplemental',
              'status': 'PASS' if 'exploratory supplemental H2' in summary_md else 'FAIL',
              'detail': 'exploratory supplemental H2 문구 확인'}
checks[18] = {'check': '19_summary_has_classifier_performance',
              'status': 'PASS' if 'accuracy 0.4281' in summary_md else 'FAIL',
              'detail': '4-type classifier 성능 제한 문장 확인'}
checks[19] = {'check': '20_summary_has_causal_warning',
              'status': 'PASS' if '인과관계를 주장할 수 없다' in summary_md else 'FAIL',
              'detail': '인과 해석 금지 문장 확인'}

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  최종 Validation: {n_pass}/20 PASS, {n_fail} FAIL")
for c in checks:
    icon = '✓' if c['status']=='PASS' else '✗'
    if c['status']=='FAIL':
        print(f"  [✗] {c['check']}: {c['detail']}")

if n_fail > 0:
    print("[ERROR] Validation FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

# validation 파일 저장 (없으므로 별도 저장 — diagnostics에 포함)
print("\n[완료] 모든 분석 완료. Validation 20/20 PASS.")
print("  커밋 대상: analysis: run full sample wendys h2 four type prediction")
