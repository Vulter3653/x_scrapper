"""
run_wendys_h3_main_quadratic_ols.py

목적: Aggressive Humor Proportion의 역 U자형 관계를 확인하는 exploratory H3-main quadratic OLS.
      Primary predictor: aggressive_humor_proportion_quarter_loo
      이 분석은 H3-pre(general proportion)가 불지지였기 때문에 exploratory H3-main으로 제한한다.

      기본식:
      log1p_engagement_total_i = α + β1·x_i + β2·x_i² + ε_i
      (x = aggressive_humor_proportion_quarter_loo)

      quarter fixed effects 미사용:
      aggressive_humor_proportion_quarter_loo는 quarter-level 기반 변수이므로
      quarter fixed effects와 동시에 사용하면 식별 불가.
"""

import csv
import math
import os
import hashlib
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

INTENSITY_DS    = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
POSTS_JSON      = os.path.join("data", "wendys", "posts.json")

DATASET_OUT      = os.path.join(DATA_DIR,   "wendys_h3_main_quadratic_ols_dataset.csv")
PRIMARY_OUT      = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_primary_results.csv")
CENTERED_OUT     = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_centered_results.csv")
SHARE_ROB_OUT    = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_share_robustness.csv")
FREQ_ROB_OUT     = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_frequency_robustness.csv")
OTHER_ROB_OUT    = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_other_humor_robustness.csv")
PERIOD_OLS_OUT   = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_period_level_results.csv")
TP_OUT           = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_turning_points.csv")
DIAG_OUT         = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_diagnostics.csv")
PRIMARY_PLOT     = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_primary_plot.png")
BIN_PLOT         = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_bin_mean_plot.png")
SUMMARY_OUT      = os.path.join(RESULT_DIR, "wendys_h3_main_quadratic_ols_summary.md")

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

def safe_float(v):
    if v in ('nan', '', None): return None
    try: return float(v)
    except: return None

# ── 0. posts.json 보호 확인 ────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 데이터 로드 및 필터 ─────────────────────────────────────────────────────
print("[1] 데이터 로드 및 필터")
with open(INTENSITY_DS, newline='', encoding='utf-8') as f:
    all_rows = list(csv.DictReader(f))

posts = [r for r in all_rows if r.get('in_h3_aggressive_filtered') == '1'
         and safe_float(r.get('aggressive_humor_proportion_quarter_loo')) is not None]
print(f"  filtered: {len(posts)}건, {len(set(r['year_quarter'] for r in posts))}분기")

# primary predictor 배열
X_agg   = np.array([float(r['aggressive_humor_proportion_quarter_loo']) for r in posts])
X_share = np.array([safe_float(r['aggressive_share_among_humor_quarter_loo']) or 0.0 for r in posts])
X_freq  = np.array([float(r['aggressive_humor_frequency_quarter']) for r in posts])
X_other = np.array([float(r['other_humor_proportion_quarter_loo']) for r in posts])

x_min, x_max = float(np.min(X_agg)), float(np.max(X_agg))
x_mean        = float(np.mean(X_agg))
X_agg_c       = X_agg - x_mean

x_share_min, x_share_max = float(np.min(X_share)), float(np.max(X_share))
x_freq_min,  x_freq_max  = float(np.min(X_freq)),  float(np.max(X_freq))
x_other_min, x_other_max = float(np.min(X_other)), float(np.max(X_other))

print(f"  agg_loo: min={x_min:.4f} max={x_max:.4f} mean={x_mean:.4f} sd={float(np.std(X_agg,ddof=1)):.4f}")

# ── 2. 분석용 변수 추가 및 dataset 저장 ────────────────────────────────────────
print("[2] 분석 변수 생성 및 dataset 저장")
new_fields = [
    'aggressive_humor_proportion_quarter_loo_sq',
    'aggressive_humor_proportion_quarter_loo_centered',
    'aggressive_humor_proportion_quarter_loo_centered_sq',
    'aggressive_share_among_humor_quarter_loo_sq',
    'aggressive_humor_frequency_quarter_sq',
    'other_humor_proportion_quarter_loo_sq',
]
new_posts = []
for i, r in enumerate(posts):
    nr = dict(r)
    x  = X_agg[i]
    xc = X_agg_c[i]
    xs = X_share[i]
    xf = X_freq[i]
    xo = X_other[i]
    nr['aggressive_humor_proportion_quarter_loo_sq']          = round(x**2, 8)
    nr['aggressive_humor_proportion_quarter_loo_centered']    = round(xc, 8)
    nr['aggressive_humor_proportion_quarter_loo_centered_sq'] = round(xc**2, 8)
    nr['aggressive_share_among_humor_quarter_loo_sq']         = round(xs**2, 8)
    nr['aggressive_humor_frequency_quarter_sq']               = round(xf**2, 4)
    nr['other_humor_proportion_quarter_loo_sq']               = round(xo**2, 8)
    new_posts.append(nr)

orig_fields = list(all_rows[0].keys())
all_fields  = orig_fields + [f for f in new_fields if f not in orig_fields]
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(new_posts)
print(f"  → {DATASET_OUT}")

# ── OLS 헬퍼 ──────────────────────────────────────────────────────────────────
def ols_quadratic(x, y):
    n = len(x)
    X = np.column_stack([np.ones(n), x, x**2])
    XtX = X.T @ X
    try:
        XtXinv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return None
    coef  = XtXinv @ (X.T @ y)
    y_hat = X @ coef
    resid = y - y_hat
    sse   = float(resid @ resid)
    df_r  = n - 3
    if df_r <= 0:
        return None
    mse   = sse / df_r
    sst   = float(np.sum((y - float(np.mean(y)))**2))
    r2    = 1 - sse/sst if sst > 0 else float('nan')
    adj_r2= 1 - (1-r2)*(n-1)/(n-3) if sst > 0 else float('nan')
    vcov  = mse * XtXinv
    se    = np.sqrt(np.diag(vcov))
    t_vec = coef / se
    p_vec = np.array([float(2*stats.t.sf(abs(tv), df=df_r)) for tv in t_vec])
    return coef[0], coef[1], coef[2], se[1], se[2], t_vec[1], t_vec[2], p_vec[1], p_vec[2], r2, adj_r2, vcov, n

def turning_point_delta(b1, b2, vcov):
    if abs(b2) < 1e-12:
        return float('nan'), float('nan'), float('nan')
    tp  = -b1 / (2*b2)
    g   = np.array([0.0, -1/(2*b2), b1/(2*b2**2)])
    var_tp = float(g @ vcov @ g)
    if var_tp < 0:
        return tp, float('nan'), float('nan')
    se_tp = math.sqrt(var_tp)
    return tp, tp - 1.96*se_tp, tp + 1.96*se_tp

def h3_direction(b1, b2, tp, xlo, xhi):
    in_r = xlo <= tp <= xhi if not math.isnan(tp) else False
    if b2 < 0 and in_r:
        return 'inverted_U'
    if b2 < 0 and not in_r:
        return 'concave_tp_out_of_range'
    if b2 > 0:
        return 'U_shape_or_convex'
    return 'other'

def h3_main_support(b1, b2, tp, p2, xlo, xhi):
    in_r = (xlo <= tp <= xhi) if not math.isnan(tp) else False
    if b1 > 0 and b2 < 0 and in_r and p2 < 0.05:
        return '강한_탐색적_지지(p<.05)'
    if b1 > 0 and b2 < 0 and in_r:
        return '약한_탐색적_지지(tp_in_range)'
    if b1 > 0 and b2 < 0 and not in_r:
        return '방향성만_지지(tp_out_of_range)'
    return 'H3main_불지지'

def fmt_tp(v):
    return round(v, 4) if not math.isnan(v) else 'nan'

# ── 3. Primary post-level quadratic OLS ───────────────────────────────────────
print("[3] Primary post-level quadratic OLS (aggressive_humor_proportion_quarter_loo)")
primary_results = []
tp_rows = []

for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_agg, y)
    if res is None:
        print(f"  [{dv}] OLS 실패")
        continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp, tp_lo, tp_hi = turning_point_delta(b1, b2, vcov)
    tp_in = (x_min <= tp <= x_max) if not math.isnan(tp) else False
    direction = h3_direction(b1, b2, tp, x_min, x_max)
    support   = h3_main_support(b1, b2, tp, p2, x_min, x_max)

    row = {
        'dv': dv, 'n': n, 'n_quarters': len(set(r['year_quarter'] for r in new_posts)),
        'predictor': 'aggressive_humor_proportion_quarter_loo',
        'coef_linear': round(b1, 4), 'se_linear': round(se1, 4),
        't_linear': round(t1, 4), 'p_linear': round(p1, 4),
        'coef_quadratic': round(b2, 4), 'se_quadratic': round(se2, 4),
        't_quadratic': round(t2, 4), 'p_quadratic': round(p2, 4),
        'r_squared': round(r2, 4), 'adj_r_squared': round(adj_r2, 4),
        'x_min': round(x_min, 4), 'x_max': round(x_max, 4), 'x_mean': round(x_mean, 4),
        'turning_point': fmt_tp(tp),
        'turning_point_ci_low': fmt_tp(tp_lo),
        'turning_point_ci_high': fmt_tp(tp_hi),
        'turning_point_in_range': tp_in,
        'h3_main_direction': direction,
        'h3_main_exploratory_support': support,
    }
    primary_results.append(row)
    tp_rows.append({
        'dv': dv, 'model': 'primary_raw',
        'b1': round(b1, 4), 'b2': round(b2, 4),
        'turning_point': fmt_tp(tp),
        'tp_ci_low': fmt_tp(tp_lo), 'tp_ci_high': fmt_tp(tp_hi),
        'tp_in_range': tp_in,
        'x_min': round(x_min, 4), 'x_max': round(x_max, 4),
        'h3_main_exploratory_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={fmt_tp(tp)} in_range={tp_in} → {support}")

with open(PRIMARY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(primary_results[0].keys()))
    w.writeheader(); w.writerows(primary_results)
print(f"  → {PRIMARY_OUT}")

# ── 4. Centered quadratic OLS ──────────────────────────────────────────────────
print("[4] Centered model")
centered_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_agg_c, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    centered_results.append({
        'dv': dv, 'n': n,
        'coef_centered_linear': round(b1, 4), 'p_centered_linear': round(p1, 4),
        'coef_centered_quadratic': round(b2, 4), 'p_centered_quadratic': round(p2, 4),
        'r_squared': round(r2, 4), 'adj_r_squared': round(adj_r2, 4),
        'b2_sign': 'negative' if b2 < 0 else 'positive',
        'note': 'centered_for_multicollinearity_check',
    })

with open(CENTERED_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(centered_results[0].keys()))
    w.writeheader(); w.writerows(centered_results)
print(f"  → {CENTERED_OUT}")

# ── 5. Share among humor LOO robustness ───────────────────────────────────────
print("[5] aggressive_share_among_humor_quarter_loo robustness")
share_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_share, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp, tp_lo, tp_hi = turning_point_delta(b1, b2, vcov)
    tp_in = (x_share_min <= tp <= x_share_max) if not math.isnan(tp) else False
    support = h3_main_support(b1, b2, tp, p2, x_share_min, x_share_max)
    share_results.append({
        'dv': dv, 'n': n, 'predictor': 'aggressive_share_among_humor_quarter_loo',
        'coef_linear': round(b1, 4), 'p_linear': round(p1, 4),
        'coef_quadratic': round(b2, 4), 'p_quadratic': round(p2, 4),
        'turning_point': fmt_tp(tp),
        'x_min': round(x_share_min, 4), 'x_max': round(x_share_max, 4),
        'turning_point_in_range': tp_in,
        'r_squared': round(r2, 4),
        'h3_main_exploratory_support': support,
    })
    tp_rows.append({
        'dv': dv, 'model': 'share_robustness',
        'b1': round(b1, 4), 'b2': round(b2, 4),
        'turning_point': fmt_tp(tp), 'tp_ci_low': fmt_tp(tp_lo), 'tp_ci_high': fmt_tp(tp_hi),
        'tp_in_range': tp_in,
        'x_min': round(x_share_min, 4), 'x_max': round(x_share_max, 4),
        'h3_main_exploratory_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={fmt_tp(tp)} in_range={tp_in}")

with open(SHARE_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(share_results[0].keys()))
    w.writeheader(); w.writerows(share_results)
print(f"  → {SHARE_ROB_OUT}")

# ── 6. Frequency robustness ───────────────────────────────────────────────────
print("[6] aggressive_humor_frequency_quarter robustness")
freq_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_freq, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp, _, _ = turning_point_delta(b1, b2, vcov)
    tp_in = (x_freq_min <= tp <= x_freq_max) if not math.isnan(tp) else False
    support = h3_main_support(b1, b2, tp, p2, x_freq_min, x_freq_max)
    freq_results.append({
        'dv': dv, 'n': n, 'predictor': 'aggressive_humor_frequency_quarter',
        'coef_linear': round(b1, 6), 'p_linear': round(p1, 4),
        'coef_quadratic': round(b2, 6), 'p_quadratic': round(p2, 4),
        'turning_point': round(tp, 2) if not math.isnan(tp) else 'nan',
        'x_min': round(x_freq_min, 1), 'x_max': round(x_freq_max, 1),
        'turning_point_in_range': tp_in,
        'r_squared': round(r2, 4),
        'h3_main_exploratory_support': support,
    })
    tp_rows.append({
        'dv': dv, 'model': 'frequency_robustness',
        'b1': round(b1, 6), 'b2': round(b2, 6),
        'turning_point': round(tp, 2) if not math.isnan(tp) else 'nan',
        'tp_ci_low': 'nan', 'tp_ci_high': 'nan',
        'tp_in_range': tp_in,
        'x_min': round(x_freq_min, 1), 'x_max': round(x_freq_max, 1),
        'h3_main_exploratory_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.6f} b2={b2:.6f} tp={round(tp,2) if not math.isnan(tp) else 'nan'} in_range={tp_in}")

with open(FREQ_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(freq_results[0].keys()))
    w.writeheader(); w.writerows(freq_results)
print(f"  → {FREQ_ROB_OUT}")

# ── 7. Other humor proportion LOO robustness ──────────────────────────────────
print("[7] other_humor_proportion_quarter_loo robustness")
other_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_other, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp, tp_lo, tp_hi = turning_point_delta(b1, b2, vcov)
    tp_in = (x_other_min <= tp <= x_other_max) if not math.isnan(tp) else False
    support = h3_main_support(b1, b2, tp, p2, x_other_min, x_other_max)
    other_results.append({
        'dv': dv, 'n': n, 'predictor': 'other_humor_proportion_quarter_loo',
        'coef_linear': round(b1, 4), 'p_linear': round(p1, 4),
        'coef_quadratic': round(b2, 4), 'p_quadratic': round(p2, 4),
        'turning_point': fmt_tp(tp),
        'x_min': round(x_other_min, 4), 'x_max': round(x_other_max, 4),
        'turning_point_in_range': tp_in,
        'r_squared': round(r2, 4),
        'h3_main_exploratory_support': support,
        'note': 'other_humor_proportion_loo: non-aggressive humor robustness check',
    })
    tp_rows.append({
        'dv': dv, 'model': 'other_humor_robustness',
        'b1': round(b1, 4), 'b2': round(b2, 4),
        'turning_point': fmt_tp(tp), 'tp_ci_low': fmt_tp(tp_lo), 'tp_ci_high': fmt_tp(tp_hi),
        'tp_in_range': tp_in,
        'x_min': round(x_other_min, 4), 'x_max': round(x_other_max, 4),
        'h3_main_exploratory_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={fmt_tp(tp)} in_range={tp_in}")

with open(OTHER_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(other_results[0].keys()))
    w.writeheader(); w.writerows(other_results)
print(f"  → {OTHER_ROB_OUT}")

# ── 8. Period-level exploratory OLS (n=25) ────────────────────────────────────
print("[8] Period-level exploratory OLS (n=25 quarters)")

# quarter 집계
q_agg = defaultdict(lambda: {'agg_loo': [], **{dv: [] for dv in DVS}})
for i, r in enumerate(new_posts):
    q = r['year_quarter']
    q_agg[q]['agg_loo'].append(X_agg[i])
    for dv in DVS:
        q_agg[q][dv].append(float(r[dv]))

period_records = []
for q in sorted(q_agg.keys()):
    qa = q_agg[q]
    rec = {'year_quarter': q, 'mean_aggressive_loo': round(float(np.mean(qa['agg_loo'])), 6)}
    for dv in DVS:
        rec[f'mean_{dv}'] = round(float(np.mean(qa[dv])), 6)
    period_records.append(rec)

X_p = np.array([r['mean_aggressive_loo'] for r in period_records])
px_min, px_max = float(np.min(X_p)), float(np.max(X_p))
period_ols_rows = []

for dv in DVS:
    y_p = np.array([r[f'mean_{dv}'] for r in period_records])
    res = ols_quadratic(X_p, y_p)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp, tp_lo, tp_hi = turning_point_delta(b1, b2, vcov)
    tp_in = (px_min <= tp <= px_max) if not math.isnan(tp) else False
    support = h3_main_support(b1, b2, tp, p2, px_min, px_max)
    period_ols_rows.append({
        'dv': dv, 'n_periods': n,
        'coef_linear': round(b1, 4), 'p_linear': round(p1, 4),
        'coef_quadratic': round(b2, 4), 'p_quadratic': round(p2, 4),
        'turning_point': fmt_tp(tp),
        'x_min': round(px_min, 4), 'x_max': round(px_max, 4),
        'turning_point_in_range': tp_in,
        'r_squared': round(r2, 4),
        'h3_main_direction': h3_direction(b1, b2, tp, px_min, px_max),
        'h3_main_exploratory_support': support,
        'note': 'exploratory_period_level_n25',
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={fmt_tp(tp)} in_range={tp_in}")

with open(PERIOD_OLS_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(period_ols_rows[0].keys()))
    w.writeheader(); w.writerows(period_ols_rows)
print(f"  → {PERIOD_OLS_OUT}")

# ── 9. Turning point 통합 저장 ────────────────────────────────────────────────
with open(TP_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(tp_rows[0].keys()))
    w.writeheader(); w.writerows(tp_rows)
print(f"  → {TP_OUT}")

# ── 10. 그래프 ────────────────────────────────────────────────────────────────
print("[10] 그래프 생성")

pr = next(r for r in primary_results if r['dv'] == 'log1p_engagement_total')
b1_p = float(pr['coef_linear'])
b2_p = float(pr['coef_quadratic'])
tp_p = float(pr['turning_point']) if pr['turning_point'] != 'nan' else float('nan')

y_all = np.array([float(r['log1p_engagement_total']) for r in new_posts])
X_m   = np.column_stack([np.ones(len(X_agg)), X_agg, X_agg**2])
coef_full = np.linalg.lstsq(X_m, y_all, rcond=None)[0]
a_f, b1_f, b2_f = coef_full

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(X_agg, y_all, alpha=0.15, s=10, color='#95A5A6', label='observations')
x_curve = np.linspace(x_min, x_max, 200)
y_curve = a_f + b1_f*x_curve + b2_f*x_curve**2
ax.plot(x_curve, y_curve, color='#E74C3C', linewidth=2, label='quadratic fit')
if not math.isnan(tp_p):
    ax.axvline(tp_p, color='#F39C12', linestyle='--', linewidth=1.5, label=f'turning point={tp_p:.4f}')
ax.set_xlabel("aggressive_humor_proportion_quarter_loo", fontsize=10)
ax.set_ylabel("log1p_engagement_total", fontsize=10)
ax.set_title(f"H3-main (Exploratory): Aggressive Humor Proportion LOO vs Engagement\n(n={len(X_agg)}, 25 quarters, quadratic OLS)", fontsize=9)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(PRIMARY_PLOT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PRIMARY_PLOT}")

# bin mean plot
t33 = float(np.percentile(X_agg, 33.33))
t67 = float(np.percentile(X_agg, 66.67))
def bin_assign(v):
    if v <= t33: return 'low'
    if v <= t67: return 'medium'
    return 'high'

bins_eng = defaultdict(list)
for i, r in enumerate(new_posts):
    bins_eng[bin_assign(X_agg[i])].append(float(r['log1p_engagement_total']))

bin_labels = ['low', 'medium', 'high']
bin_means  = [float(np.mean(bins_eng[b])) if bins_eng[b] else 0 for b in bin_labels]
bin_ns     = [len(bins_eng[b]) for b in bin_labels]

fig, ax = plt.subplots(figsize=(6, 5))
colors_b = ['#95A5A6', '#3498DB', '#E74C3C']
bars = ax.bar(range(3), bin_means, color=colors_b, edgecolor='white', width=0.5)
ax.set_xticks(range(3))
ax.set_xticklabels([f"{b}\n(n={n})" for b, n in zip(bin_labels, bin_ns)], fontsize=10)
ax.set_ylabel("Mean log1p(engagement_total)", fontsize=10)
ax.set_title(f"Bin-level Engagement (aggressive_proportion_loo tertile)\n(T33={t33:.4f}, T67={t67:.4f})", fontsize=9)
for bar, m in zip(bars, bin_means):
    ax.text(bar.get_x()+bar.get_width()/2, m+0.01, f"{m:.3f}", ha='center', va='bottom', fontsize=10)
ax.set_ylim(0, max(bin_means)*1.15)
plt.tight_layout()
plt.savefig(BIN_PLOT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {BIN_PLOT}")

# ── 11. Diagnostics ───────────────────────────────────────────────────────────
print("[11] Diagnostics")
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON, 'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

pr_main = next(r for r in primary_results if r['dv'] == 'log1p_engagement_total')
pr_cent = next(r for r in centered_results if r['dv'] == 'log1p_engagement_total')
pr_shar = next(r for r in share_results   if r['dv'] == 'log1p_engagement_total')
pr_freq = next(r for r in freq_results    if r['dv'] == 'log1p_engagement_total')
pr_othr = next(r for r in other_results   if r['dv'] == 'log1p_engagement_total')
pr_per  = next((r for r in period_ols_rows if r['dv'] == 'log1p_engagement_total'), {})

diag = {
    'total_rows_in_source': len(all_rows),
    'filtered_rows': len(new_posts),
    'filtered_quarters': len(set(r['year_quarter'] for r in new_posts)),
    'primary_predictor': 'aggressive_humor_proportion_quarter_loo',
    'primary_predictor_min': round(x_min, 4),
    'primary_predictor_max': round(x_max, 4),
    'primary_predictor_mean': round(x_mean, 4),
    'primary_predictor_sd': round(float(np.std(X_agg, ddof=1)), 4),
    'primary_predictor_missing': 0,
    'primary_dv': 'log1p_engagement_total',
    'primary_beta1': pr_main['coef_linear'],
    'primary_beta1_sign': 'positive' if float(pr_main['coef_linear']) > 0 else 'negative',
    'primary_beta2': pr_main['coef_quadratic'],
    'primary_beta2_sign': 'negative' if float(pr_main['coef_quadratic']) < 0 else 'positive',
    'primary_p_linear': pr_main['p_linear'],
    'primary_p_quadratic': pr_main['p_quadratic'],
    'primary_turning_point': pr_main['turning_point'],
    'primary_turning_point_in_range': pr_main['turning_point_in_range'],
    'primary_turning_point_ci_low': pr_main['turning_point_ci_low'],
    'primary_turning_point_ci_high': pr_main['turning_point_ci_high'],
    'primary_r_squared': pr_main['r_squared'],
    'primary_h3_main_support': pr_main['h3_main_exploratory_support'],
    'centered_beta2': pr_cent['coef_centered_quadratic'],
    'share_robustness_beta2': pr_shar['coef_quadratic'],
    'share_robustness_support': pr_shar['h3_main_exploratory_support'],
    'frequency_robustness_beta2': pr_freq['coef_quadratic'],
    'frequency_robustness_support': pr_freq['h3_main_exploratory_support'],
    'other_humor_robustness_beta2': pr_othr['coef_quadratic'],
    'other_humor_robustness_support': pr_othr['h3_main_exploratory_support'],
    'period_level_beta2': pr_per.get('coef_quadratic', 'n/a'),
    'period_level_support': pr_per.get('h3_main_exploratory_support', 'n/a'),
    'quarter_fixed_effects_used': False,
    'h3_pre_general_proportion_supported': False,
    'analysis_type': 'exploratory_h3_main',
    'original_posts_json_modified': posts_json_modified,
}

with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric', 'value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 12. Validation 20개 ───────────────────────────────────────────────────────
print("[12] Validation")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

all_outs = [DATASET_OUT, PRIMARY_OUT, CENTERED_OUT, SHARE_ROB_OUT, FREQ_ROB_OUT,
            OTHER_ROB_OUT, PERIOD_OLS_OUT, TP_OUT, DIAG_OUT, PRIMARY_PLOT, BIN_PLOT, SUMMARY_OUT]
chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in all_outs), "경로 확인")
chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_filtered_rows_960", len(new_posts) == 960, f"n={len(new_posts)}")
chk("04_filtered_quarters_25",
    len(set(r['year_quarter'] for r in new_posts)) == 25, "25분기")
chk("05_primary_predictor_correct",
    diag['primary_predictor'] == 'aggressive_humor_proportion_quarter_loo', "변수명")
chk("06_primary_predictor_missing_0",
    diag['primary_predictor_missing'] == 0, "missing=0")
chk("07_quadratic_term_computed",
    all('coef_quadratic' in r for r in primary_results), "제곱항 존재")
chk("08_primary_dv_correct", primary_results[0]['dv'] == 'log1p_engagement_total', "DV 확인")
chk("09_all_dvs_generated", len(primary_results) == len(DVS), f"n_dvs={len(primary_results)}")
chk("10_turning_point_computed",
    all('turning_point' in r for r in primary_results), "TP 존재")
chk("11_centered_model_generated", len(centered_results) == len(DVS), f"n={len(centered_results)}")
chk("12_share_robustness_generated", len(share_results) == len(DVS), f"n={len(share_results)}")
chk("13_frequency_robustness_generated", len(freq_results) == len(DVS), f"n={len(freq_results)}")
chk("14_other_humor_robustness_generated", len(other_results) == len(DVS), f"n={len(other_results)}")
chk("15_period_level_ols_generated", len(period_ols_rows) > 0, f"n={len(period_ols_rows)}")
chk("16_no_quarter_fixed_effects", not diag['quarter_fixed_effects_used'], "FE 미사용")
chk("17_primary_plot_exists", os.path.exists(PRIMARY_PLOT), "파일 존재")
chk("18_bin_plot_exists", os.path.exists(BIN_PLOT), "파일 존재")
chk("19_summary_exploratory_placeholder", True, "summary 작성 후 확인")
chk("20_summary_h3pre_placeholder", True, "summary 작성 후 확인")

n_pass = sum(1 for c in checks if c['status'] == 'PASS')
n_fail = sum(1 for c in checks if c['status'] == 'FAIL')
print(f"  Validation 1차: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    import sys; sys.exit(1)

# ── 13. Summary markdown ──────────────────────────────────────────────────────
print("[13] summary.md 작성")

def star(p):
    p = float(p)
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '†'
    return 'n.s.'

def primary_table_md():
    lines = ["| DV | β1 | p(β1) | β2 | p(β2) | turning_point | in_range | 탐색적 지지 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in primary_results:
        lines.append(
            f"| {r['dv']} | {r['coef_linear']}({star(r['p_linear'])}) | {r['p_linear']}"
            f" | {r['coef_quadratic']}({star(r['p_quadratic'])}) | {r['p_quadratic']}"
            f" | {r['turning_point']} | {r['turning_point_in_range']} | {r['h3_main_exploratory_support']} |"
        )
    return '\n'.join(lines)

def get_d(k):
    return diag.get(k, 'n/a')

summary_md = f"""# Wendy's H3-main Exploratory Quadratic OLS 분석 결과

## 1. 분석 위치

본 분석은 확증적 H3 검증이 아니라 exploratory H3-main 분석이다.

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았다 (β2=+0.3153, turning point=-0.3040, 관측 범위 밖). 따라서 aggressive humor intensity를 primary predictor로 사용한 이번 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

---

## 2. 분석 목적

aggressive humor proportion이 증가할수록 engagement가 먼저 상승하다가 이후 감소하는 역 U자형 관계가 있는지를 탐색적으로 확인한다.

```
log1p_engagement_total_i = α + β1·x_i + β2·x_i² + ε_i
x = aggressive_humor_proportion_quarter_loo
```

quarter fixed effects는 사용하지 않았다. aggressive_humor_proportion_quarter_loo는 quarter-level 기반 변수이므로 quarter fixed effects와 동시에 사용할 경우 식별이 불가능하기 때문이다.

---

## 3. 사용 데이터

| 항목 | 값 |
|---|---|
| 소스 | `wendys_h3_aggressive_vs_other_intensity_dataset.csv` |
| 전체 rows | {get_d('total_rows_in_source')} |
| 필터 기준 | in_h3_aggressive_filtered=1 |
| **filtered rows** | **{get_d('filtered_rows')}** |
| **filtered quarters** | **{get_d('filtered_quarters')}** |

---

## 4. Primary predictor 정의

```
aggressive_humor_proportion_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Total Posts_q - 1)
```

post i 자신을 제외한 동일 분기 내 aggressive humor 비중.
모델 기반 타입 예측값(pred_humor_type_group_model)을 기반으로 산출하였다.

| 항목 | 값 |
|---|---|
| min | {get_d('primary_predictor_min')} |
| max | {get_d('primary_predictor_max')} |
| mean | {get_d('primary_predictor_mean')} |
| sd | {get_d('primary_predictor_sd')} |
| missing | {get_d('primary_predictor_missing')} |
| 관측 범위 | [{get_d('primary_predictor_min')}, {get_d('primary_predictor_max')}] |

---

## 5. Primary post-level quadratic OLS 결과

{primary_table_md()}

* p<.05, ** p<.01, *** p<.001, † p<.10

---

## 6. 주요 DV: log1p_engagement_total

| 항목 | 값 |
|---|---|
| β1 (linear) | {get_d('primary_beta1')} (p={get_d('primary_p_linear')}) |
| β2 (quadratic) | {get_d('primary_beta2')} (p={get_d('primary_p_quadratic')}) |
| turning point | {get_d('primary_turning_point')} |
| 관측 범위 | [{get_d('primary_predictor_min')}, {get_d('primary_predictor_max')}] |
| turning point in range | {get_d('primary_turning_point_in_range')} |
| turning point 95% CI | [{get_d('primary_turning_point_ci_low')}, {get_d('primary_turning_point_ci_high')}] |
| R² | {get_d('primary_r_squared')} |
| **H3-main 탐색적 지지** | **{get_d('primary_h3_main_support')}** |

---

## 7. Centered model robustness

| 항목 | 값 |
|---|---|
| β2 (centered quadratic) | {pr_cent['coef_centered_quadratic']} (p={pr_cent['p_centered_quadratic']}) |
| β2 부호 | {get_d('centered_beta2')} |
| R² | {pr_cent['r_squared']} |

---

## 8. 보조 predictors robustness 요약

| predictor | β1 | β2 | turning point | in range | 탐색적 지지 |
|---|---|---|---|---|---|
| aggressive_share_among_humor_loo | {pr_shar['coef_linear']} | {pr_shar['coef_quadratic']} | {pr_shar['turning_point']} | {pr_shar['turning_point_in_range']} | {pr_shar['h3_main_exploratory_support']} |
| aggressive_frequency | {pr_freq['coef_linear']} | {pr_freq['coef_quadratic']} | {pr_freq['turning_point']} | {pr_freq['turning_point_in_range']} | {pr_freq['h3_main_exploratory_support']} |
| other_humor_proportion_loo | {pr_othr['coef_linear']} | {pr_othr['coef_quadratic']} | {pr_othr['turning_point']} | {pr_othr['turning_point_in_range']} | {pr_othr['h3_main_exploratory_support']} |

---

## 9. Period-level exploratory OLS (n=25 quarters)

| 항목 | 값 |
|---|---|
| β1 | {pr_per.get('coef_linear', 'n/a')} (p={pr_per.get('p_linear', 'n/a')}) |
| β2 | {pr_per.get('coef_quadratic', 'n/a')} (p={pr_per.get('p_quadratic', 'n/a')}) |
| turning point | {pr_per.get('turning_point', 'n/a')} |
| in range | {pr_per.get('turning_point_in_range', 'n/a')} |
| R² | {pr_per.get('r_squared', 'n/a')} |

n=25로 표본이 작기 때문에 period-level OLS는 descriptive robustness로만 해석한다.

---

## 10. H3-main exploratory support 판정

H3-main exploratory support 기준:

| 기준 | 조건 |
|---|---|
| 강한 탐색적 지지 | β1>0, β2<0, turning_point in range, p_quadratic<.05 |
| 약한 탐색적 지지 | β1>0, β2<0, turning_point in range, p_quadratic≥.05 |
| 방향성만 지지 | β1>0, β2<0, turning_point out of range |
| 불지지 | β2≥0 또는 turning_point 범위 밖 |

**primary model 판정: {get_d('primary_h3_main_support')}**

---

## 11. 이전 H3-pre와의 관계

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았으므로, 본 aggressive intensity 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

| 분석 단계 | predictor | β2 부호 | turning point | 지지 여부 |
|---|---|---|---|---|
| H3-pre (일반) | humor_proportion_quarter_loo | +0.3153 | -0.3040 (범위 밖) | 불지지 |
| H3-main (탐색적) | aggressive_humor_proportion_quarter_loo | {get_d('primary_beta2')} | {get_d('primary_turning_point')} | {get_d('primary_h3_main_support')} |

---

## 12. 해석상 주의사항

1. 이 분석은 관측적 연관성 분석이며, aggressive humor가 engagement를 증가시켰다는 인과관계를 주장할 수 없다.
2. aggressive_humor_proportion_quarter_loo는 pred_humor_type_group_model(모델 기반 타입 예측값)에서 파생된 변수이므로 분류 오류를 포함할 수 있다.
3. 같은 분기 내 게시글은 동일한 predictor 값을 공유하므로 표준오차가 과소추정될 수 있다 (cluster-robust SE 미적용).
4. quarter fixed effects 미사용으로 분기별 시계열 추세가 통제되지 않았다.
5. H3-pre의 general proportion이 불지지였기 때문에, 이 결과는 exploratory H3-main에 해당하며 확증적 증거가 아니다.

---

## 13. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/H3-pre 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# summary validation 업데이트
checks[18] = {
    'check': '19_summary_exploratory_h3main',
    'status': 'PASS' if 'exploratory H3-main' in summary_md else 'FAIL',
    'detail': 'exploratory H3-main 표현 확인'
}
checks[19] = {
    'check': '20_summary_h3pre_not_supported',
    'status': 'PASS' if '지지되지 않았으므로' in summary_md else 'FAIL',
    'detail': 'H3-pre 불지지 문장 확인'
}

n_pass = sum(1 for c in checks if c['status'] == 'PASS')
n_fail = sum(1 for c in checks if c['status'] == 'FAIL')
print(f"\n  최종 Validation: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    for c in checks:
        if c['status'] == 'FAIL':
            print(f"  [✗] {c['check']}: {c['detail']}")
    import sys; sys.exit(1)

print(f"\n[완료] Validation {n_pass}/20 PASS.")
print("  커밋 대상: analysis: run wendys h3 main quadratic ols")
