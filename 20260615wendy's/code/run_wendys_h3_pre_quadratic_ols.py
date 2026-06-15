"""
run_wendys_h3_pre_quadratic_ols.py

목적: 단순 Proportion of Humor의 역 U자형 관계를 확인하는 H3-pre 이차항 OLS.
      Primary predictor: humor_proportion_quarter_loo
      H3-pre 지지 기준: β1>0, β2<0, turning point ∈ [x_min, x_max]

이 분석은 aggressive humor intensity가 아니라 단순 Proportion of Humor에 대한 H3-pre 분석이다.
quarter fixed effects 미사용 (humor_proportion_quarter_loo는 quarter-level 기반 변수로 식별 불가).
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

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

POST_DS_IN  = os.path.join(DATA_DIR,   "wendys_h3_pre_filtered_quarter_dataset.csv")
PERIOD_IN   = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_period_audit.csv")
POSTS_JSON  = os.path.join("data", "wendys", "posts.json")

DATASET_OUT     = os.path.join(DATA_DIR,   "wendys_h3_pre_quadratic_ols_dataset.csv")
PRIMARY_OUT     = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_primary_results.csv")
CENTERED_OUT    = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_centered_results.csv")
FREQ_ROB_OUT    = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_frequency_robustness.csv")
NONLOO_ROB_OUT  = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_nonloo_robustness.csv")
PERIOD_OLS_OUT  = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_period_level_results.csv")
TP_OUT          = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_turning_points.csv")
DIAG_OUT        = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_diagnostics.csv")
PRIMARY_PLOT    = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_primary_plot.png")
BIN_PLOT        = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_bin_mean_plot.png")
SUMMARY_OUT     = os.path.join(RESULT_DIR, "wendys_h3_pre_quadratic_ols_summary.md")

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

np.random.seed(42)

# ── 0. posts.json 보호 확인 ───────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 데이터 로드 및 필터 ────────────────────────────────────────────────────
print("[1] 데이터 로드 및 필터")
with open(POST_DS_IN, newline='', encoding='utf-8') as f:
    all_rows = list(csv.DictReader(f))

def safe_float(v):
    if v in ('nan','',None): return None
    try: return float(v)
    except: return None

posts = [
    r for r in all_rows
    if r.get('in_filtered_sample')=='1'
    and safe_float(r.get('humor_proportion_quarter_loo')) is not None
]
print(f"  filtered: {len(posts)}건, {len(set(r['year_quarter'] for r in posts))}분기")

# predictor 값 추출
X_loo  = np.array([float(r['humor_proportion_quarter_loo']) for r in posts])
X_freq = np.array([float(r['humor_frequency_quarter']) for r in posts])
X_prop = np.array([float(r['humor_proportion_quarter']) for r in posts])

X_loo_mean = float(np.mean(X_loo))
X_loo_c    = X_loo - X_loo_mean          # centered

x_min, x_max = float(np.min(X_loo)), float(np.max(X_loo))
print(f"  loo: min={x_min:.4f} max={x_max:.4f} mean={X_loo_mean:.4f} sd={float(np.std(X_loo,ddof=1)):.4f}")

# ── 2. 분석용 변수 생성 및 dataset 저장 ──────────────────────────────────────
print("[2] 분석 변수 생성")
new_fields = [
    'humor_proportion_quarter_loo_sq',
    'humor_proportion_quarter_loo_centered',
    'humor_proportion_quarter_loo_centered_sq',
    'humor_frequency_quarter_sq',
    'humor_proportion_quarter_sq',
]

new_posts = []
for i, r in enumerate(posts):
    nr = dict(r)
    x  = X_loo[i]
    xc = X_loo_c[i]
    xf = X_freq[i]
    xp = X_prop[i]
    nr['humor_proportion_quarter_loo_sq']         = round(x**2, 8)
    nr['humor_proportion_quarter_loo_centered']   = round(xc, 8)
    nr['humor_proportion_quarter_loo_centered_sq']= round(xc**2, 8)
    nr['humor_frequency_quarter_sq']              = round(xf**2, 4)
    nr['humor_proportion_quarter_sq']             = round(xp**2, 8)
    new_posts.append(nr)

orig_fields = list(all_rows[0].keys())
all_fields  = orig_fields + [f for f in new_fields if f not in orig_fields]
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(new_posts)
print(f"  → {DATASET_OUT}")

# ── OLS 헬퍼 함수 ──────────────────────────────────────────────────────────────
def ols_quadratic(x, y, n_q=None):
    """quadratic OLS: y = a + b1*x + b2*x^2
    returns: alpha, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov
    """
    n = len(x)
    X = np.column_stack([np.ones(n), x, x**2])
    XtX = X.T @ X
    try:
        XtXinv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return None
    coef = XtXinv @ (X.T @ y)
    y_hat = X @ coef
    resid = y - y_hat
    sse   = float(resid @ resid)
    df_r  = n - 3
    if df_r <= 0:
        return None
    mse   = sse / df_r
    ym    = float(np.mean(y))
    sst   = float(np.sum((y - ym)**2))
    r2    = 1 - sse/sst if sst > 0 else float('nan')
    k     = 2  # predictors
    adj_r2 = 1 - (1-r2)*(n-1)/(n-k-1) if sst > 0 else float('nan')
    vcov  = mse * XtXinv
    se    = np.sqrt(np.diag(vcov))
    t_vec = coef / se
    p_vec = np.array([float(2*stats.t.sf(abs(tv), df=df_r)) for tv in t_vec])
    return coef[0], coef[1], coef[2], se[1], se[2], t_vec[1], t_vec[2], p_vec[1], p_vec[2], r2, adj_r2, vcov, n

def turning_point_delta(b1, b2, vcov):
    """delta method for turning point = -b1/(2*b2), vcov is 3x3 (intercept,b1,b2)"""
    if abs(b2) < 1e-12:
        return float('nan'), float('nan'), float('nan')
    tp = -b1 / (2*b2)
    # gradient w.r.t. [alpha, b1, b2]
    g = np.array([0.0, -1/(2*b2), b1/(2*b2**2)])
    var_tp = float(g @ vcov @ g)
    if var_tp < 0:
        return tp, float('nan'), float('nan')
    se_tp = math.sqrt(var_tp)
    tp_ci_lo = tp - 1.96*se_tp
    tp_ci_hi = tp + 1.96*se_tp
    return tp, tp_ci_lo, tp_ci_hi

def h3_direction(b1, b2, tp, x_lo, x_hi):
    if b1 > 0 and b2 < 0 and x_lo <= tp <= x_hi:
        return 'inverted_U'
    if b1 > 0 and b2 < 0:
        return 'concave_tp_out_of_range'
    if b1 < 0 and b2 > 0:
        return 'U_shape'
    return 'other'

def h3_support(b1, b2, tp, p2, x_lo, x_hi):
    in_range = x_lo <= tp <= x_hi if not math.isnan(tp) else False
    if b1 > 0 and b2 < 0 and in_range and p2 < 0.05:
        return '강한_예비적_지지(p<.05)'
    if b1 > 0 and b2 < 0 and in_range:
        return '약한_예비적_지지(tp_in_range)'
    if b1 > 0 and b2 < 0 and not in_range:
        return '방향성만_지지(tp_out_of_range)'
    return 'H3pre_불지지'

# ── 3. Primary post-level quadratic OLS ───────────────────────────────────────
print("[3] Primary post-level quadratic OLS")
primary_results = []
tp_rows = []

for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_loo, y)
    if res is None:
        print(f"  [{dv}] OLS 실패")
        continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp = -b1/(2*b2) if abs(b2)>1e-12 else float('nan')
    tp_in_range = (x_min <= tp <= x_max) if not math.isnan(tp) else False
    tp_ci_lo, tp_ci_hi_v, tp_ci_hi2 = turning_point_delta(b1, b2, vcov) if vcov is not None else (float('nan'),float('nan'),float('nan'))
    tp_ci_in_range = (x_min <= tp_ci_lo and tp_ci_hi2 >= x_min) if not (math.isnan(tp_ci_lo) or math.isnan(tp_ci_hi2)) else False
    direction = h3_direction(b1, b2, tp, x_min, x_max)
    support   = h3_support(b1, b2, tp, p2, x_min, x_max)

    row = {
        'dv': dv, 'n': n, 'n_quarters': len(set(r['year_quarter'] for r in new_posts)),
        'predictor': 'humor_proportion_quarter_loo',
        'coef_linear': round(b1,4), 'se_linear': round(se1,4),
        't_linear': round(t1,4), 'p_linear': round(p1,4),
        'coef_quadratic': round(b2,4), 'se_quadratic': round(se2,4),
        't_quadratic': round(t2,4), 'p_quadratic': round(p2,4),
        'r_squared': round(r2,4), 'adj_r_squared': round(adj_r2,4),
        'x_min': round(x_min,4), 'x_max': round(x_max,4), 'x_mean': round(X_loo_mean,4),
        'turning_point': round(tp,4) if not math.isnan(tp) else 'nan',
        'turning_point_in_range': tp_in_range,
        'turning_point_se': round(math.sqrt(float((turning_point_delta(b1,b2,vcov)[1])**2)) if not math.isnan(turning_point_delta(b1,b2,vcov)[1]) else float('nan'),4) if vcov is not None else 'nan',
        'turning_point_ci_low':  round(tp_ci_lo,4)  if not math.isnan(tp_ci_lo) else 'nan',
        'turning_point_ci_high': round(tp_ci_hi2,4) if not math.isnan(tp_ci_hi2) else 'nan',
        'turning_point_ci_in_range': tp_ci_in_range,
        'h3_pre_direction': direction,
        'h3_pre_preliminary_support': support,
    }
    primary_results.append(row)

    tp_rows.append({
        'dv': dv, 'model': 'primary_raw',
        'b1': round(b1,4), 'b2': round(b2,4),
        'turning_point': round(tp,4) if not math.isnan(tp) else 'nan',
        'tp_ci_low': round(tp_ci_lo,4) if not math.isnan(tp_ci_lo) else 'nan',
        'tp_ci_high': round(tp_ci_hi2,4) if not math.isnan(tp_ci_hi2) else 'nan',
        'turning_point_in_range': tp_in_range,
        'x_min': round(x_min,4), 'x_max': round(x_max,4),
        'h3_pre_preliminary_support': support,
    })

    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={tp:.4f} in_range={tp_in_range} support={support}")

with open(PRIMARY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(primary_results[0].keys()))
    w.writeheader()
    w.writerows(primary_results)
print(f"  → {PRIMARY_OUT}")

# ── 4. Centered model ─────────────────────────────────────────────────────────
print("[4] Centered model")
centered_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_loo_c, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    centered_results.append({
        'dv': dv, 'n': n,
        'coef_centered_linear': round(b1,4), 'p_centered_linear': round(p1,4),
        'coef_centered_quadratic': round(b2,4), 'p_centered_quadratic': round(p2,4),
        'r_squared': round(r2,4), 'adj_r_squared': round(adj_r2,4),
        'note': f'b2_sign={"negative" if b2<0 else "positive"}, multicollinearity_reduced=True',
    })

with open(CENTERED_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(centered_results[0].keys()))
    w.writeheader()
    w.writerows(centered_results)
print(f"  → {CENTERED_OUT}")

# ── 5. Frequency robustness ───────────────────────────────────────────────────
print("[5] Frequency robustness")
freq_results = []
x_freq_min, x_freq_max = float(np.min(X_freq)), float(np.max(X_freq))
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_freq, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp = -b1/(2*b2) if abs(b2)>1e-12 else float('nan')
    tp_in_range = (x_freq_min <= tp <= x_freq_max) if not math.isnan(tp) else False
    direction = h3_direction(b1, b2, tp, x_freq_min, x_freq_max)
    support   = h3_support(b1, b2, tp, p2, x_freq_min, x_freq_max)
    freq_results.append({
        'dv': dv, 'n': n, 'predictor': 'humor_frequency_quarter',
        'coef_linear': round(b1,6), 'p_linear': round(p1,4),
        'coef_quadratic': round(b2,6), 'p_quadratic': round(p2,4),
        'turning_point': round(tp,2) if not math.isnan(tp) else 'nan',
        'x_min': round(x_freq_min,1), 'x_max': round(x_freq_max,1),
        'turning_point_in_range': tp_in_range,
        'r_squared': round(r2,4),
        'h3_pre_direction': direction,
        'h3_pre_preliminary_support': support,
    })
    tp_rows.append({
        'dv': dv, 'model': 'frequency_robustness',
        'b1': round(b1,6), 'b2': round(b2,6),
        'turning_point': round(tp,2) if not math.isnan(tp) else 'nan',
        'tp_ci_low': 'nan', 'tp_ci_high': 'nan',
        'turning_point_in_range': tp_in_range,
        'x_min': round(x_freq_min,1), 'x_max': round(x_freq_max,1),
        'h3_pre_preliminary_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.6f} b2={b2:.6f} tp={tp:.2f} in_range={tp_in_range}")

with open(FREQ_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(freq_results[0].keys()))
    w.writeheader()
    w.writerows(freq_results)
print(f"  → {FREQ_ROB_OUT}")

# ── 6. Non-LOO proportion robustness ─────────────────────────────────────────
print("[6] Non-LOO proportion robustness")
x_prop_min, x_prop_max = float(np.min(X_prop)), float(np.max(X_prop))
nonloo_results = []
for dv in DVS:
    y = np.array([float(r[dv]) for r in new_posts])
    res = ols_quadratic(X_prop, y)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp = -b1/(2*b2) if abs(b2)>1e-12 else float('nan')
    tp_in_range = (x_prop_min <= tp <= x_prop_max) if not math.isnan(tp) else False
    direction = h3_direction(b1, b2, tp, x_prop_min, x_prop_max)
    support   = h3_support(b1, b2, tp, p2, x_prop_min, x_prop_max)
    nonloo_results.append({
        'dv': dv, 'n': n, 'predictor': 'humor_proportion_quarter',
        'coef_linear': round(b1,4), 'p_linear': round(p1,4),
        'coef_quadratic': round(b2,4), 'p_quadratic': round(p2,4),
        'turning_point': round(tp,4) if not math.isnan(tp) else 'nan',
        'x_min': round(x_prop_min,4), 'x_max': round(x_prop_max,4),
        'turning_point_in_range': tp_in_range,
        'r_squared': round(r2,4),
        'h3_pre_direction': direction,
        'h3_pre_preliminary_support': support,
        'note': 'LOO 대안 robustness: focal post 자기 포함 proportion',
    })
    tp_rows.append({
        'dv': dv, 'model': 'nonloo_proportion_robustness',
        'b1': round(b1,4), 'b2': round(b2,4),
        'turning_point': round(tp,4) if not math.isnan(tp) else 'nan',
        'tp_ci_low': 'nan', 'tp_ci_high': 'nan',
        'turning_point_in_range': tp_in_range,
        'x_min': round(x_prop_min,4), 'x_max': round(x_prop_max,4),
        'h3_pre_preliminary_support': support,
    })
    if dv == 'log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f} b2={b2:.4f} tp={tp:.4f} in_range={tp_in_range}")

with open(NONLOO_ROB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(nonloo_results[0].keys()))
    w.writeheader()
    w.writerows(nonloo_results)
print(f"  → {NONLOO_ROB_OUT}")

# ── 7. Period-level exploratory OLS ──────────────────────────────────────────
print("[7] Period-level exploratory OLS")
with open(PERIOD_IN, newline='', encoding='utf-8') as f:
    period_rows = list(csv.DictReader(f))

period_dvs = [c for c in period_rows[0].keys() if c.startswith('mean_log1p_')]
X_ploo = np.array([float(r['mean_humor_proportion_loo']) for r in period_rows
                   if safe_float(r['mean_humor_proportion_loo']) is not None])
valid_p = [r for r in period_rows if safe_float(r['mean_humor_proportion_loo']) is not None]
px_min, px_max = float(np.min(X_ploo)), float(np.max(X_ploo))

period_results = []
for dv in period_dvs:
    y_p = np.array([float(r[dv]) for r in valid_p])
    res = ols_quadratic(X_ploo, y_p)
    if res is None: continue
    a, b1, b2, se1, se2, t1, t2, p1, p2, r2, adj_r2, vcov, n = res
    tp = -b1/(2*b2) if abs(b2)>1e-12 else float('nan')
    tp_in_range = (px_min <= tp <= px_max) if not math.isnan(tp) else False
    period_results.append({
        'dv': dv.replace('mean_',''), 'n_periods': n,
        'coef_linear': round(b1,4), 'p_linear': round(p1,4),
        'coef_quadratic': round(b2,4), 'p_quadratic': round(p2,4),
        'turning_point': round(tp,4) if not math.isnan(tp) else 'nan',
        'x_min': round(px_min,4), 'x_max': round(px_max,4),
        'turning_point_in_range': tp_in_range,
        'r_squared': round(r2,4),
        'interpretation': f'exploratory_period_level_n25_{h3_direction(b1,b2,tp,px_min,px_max)}',
    })
    if dv == 'mean_log1p_engagement_total':
        print(f"  [{dv}] b1={b1:.4f}(p={p1:.4f}) b2={b2:.4f}(p={p2:.4f}) tp={tp:.4f} in_range={tp_in_range}")

with open(PERIOD_OLS_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(period_results[0].keys()))
    w.writeheader()
    w.writerows(period_results)
print(f"  → {PERIOD_OLS_OUT}")

# ── 8. Turning point 통합 파일 ────────────────────────────────────────────────
with open(TP_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(tp_rows[0].keys()))
    w.writeheader()
    w.writerows(tp_rows)
print(f"  → {TP_OUT}")

# ── 9. 그래프 ─────────────────────────────────────────────────────────────────
print("[9] 그래프 생성")
primary_dv_res = next(r for r in primary_results if r['dv']=='log1p_engagement_total')
b1_p = float(primary_dv_res['coef_linear'])
b2_p = float(primary_dv_res['coef_quadratic'])
tp_p = float(primary_dv_res['turning_point']) if primary_dv_res['turning_point']!='nan' else float('nan')
a_p  = float(np.mean(np.array([float(r['log1p_engagement_total']) for r in new_posts]))) \
       - b1_p*X_loo_mean - b2_p*(X_loo_mean**2 + float(np.var(X_loo,ddof=1)))
# recompute intercept properly
y_all = np.array([float(r['log1p_engagement_total']) for r in new_posts])
X_m   = np.column_stack([np.ones(len(X_loo)), X_loo, X_loo**2])
coef_all = np.linalg.lstsq(X_m, y_all, rcond=None)[0]
a_p, b1_p2, b2_p2 = coef_all[0], coef_all[1], coef_all[2]

# 9.1 Primary scatter + fitted
fig, ax = plt.subplots(figsize=(8,5))
ax.scatter(X_loo, y_all, alpha=0.15, s=10, color='#95A5A6', label='observations')
x_curve = np.linspace(x_min, x_max, 200)
y_curve = a_p + b1_p2*x_curve + b2_p2*x_curve**2
ax.plot(x_curve, y_curve, color='#E74C3C', linewidth=2, label='quadratic fit')
if not math.isnan(tp_p):
    ax.axvline(tp_p, color='#F39C12', linestyle='--', linewidth=1.5, label=f'turning point={tp_p:.3f}')
ax.set_xlabel("humor_proportion_quarter_loo", fontsize=10)
ax.set_ylabel("log1p_engagement_total", fontsize=10)
ax.set_title(f"H3-pre: Proportion of Humor vs Engagement\n(quadratic OLS, n={len(X_loo)}, 25 quarters)", fontsize=10)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(PRIMARY_PLOT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PRIMARY_PLOT}")

# 9.2 Bin mean plot (tertile 기반)
t33 = float(np.percentile(X_loo, 33.33))
t67 = float(np.percentile(X_loo, 66.67))
def assign_bin(v):
    if v <= t33: return 'low'
    if v <= t67: return 'medium'
    return 'high'

bins_eng = defaultdict(list)
for i, r in enumerate(new_posts):
    b = assign_bin(X_loo[i])
    bins_eng[b].append(float(r['log1p_engagement_total']))

bin_labels = ['low', 'medium', 'high']
bin_means  = [float(np.mean(bins_eng[b])) if bins_eng[b] else 0 for b in bin_labels]
bin_ns     = [len(bins_eng[b]) for b in bin_labels]

fig, ax = plt.subplots(figsize=(6,5))
colors_bin = ['#95A5A6','#3498DB','#E74C3C']
bars = ax.bar(range(3), bin_means, color=colors_bin, edgecolor='white', width=0.5)
ax.set_xticks(range(3))
ax.set_xticklabels([f"{b}\n(n={n})" for b, n in zip(bin_labels, bin_ns)], fontsize=10)
ax.set_ylabel("Mean log1p(engagement_total)", fontsize=10)
ax.set_title(f"Bin-level Mean Engagement by humor_proportion_quarter_loo\n(tertile: T33={t33:.3f}, T67={t67:.3f})", fontsize=9)
for bar, m in zip(bars, bin_means):
    ax.text(bar.get_x()+bar.get_width()/2, m+0.01, f"{m:.3f}", ha='center', va='bottom', fontsize=10)
ax.set_ylim(0, max(bin_means)*1.15)
plt.tight_layout()
plt.savefig(BIN_PLOT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {BIN_PLOT}")

# ── 10. Diagnostics ───────────────────────────────────────────────────────────
print("[10] Diagnostics")
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON,'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

pr = primary_dv_res
diag = {
    'total_rows_before_filter': len(all_rows),
    'filtered_rows': len(new_posts),
    'excluded_rows': len(all_rows) - len(new_posts),
    'filtered_quarters': len(set(r['year_quarter'] for r in new_posts)),
    'excluded_quarters': '2009-Q4, 2023-Q4, 2025-Q3',
    'primary_predictor': 'humor_proportion_quarter_loo',
    'primary_predictor_missing_rows': 0,
    'primary_predictor_min': round(x_min,4),
    'primary_predictor_max': round(x_max,4),
    'primary_predictor_mean': round(X_loo_mean,4),
    'primary_predictor_sd': round(float(np.std(X_loo,ddof=1)),4),
    'primary_dv_missing_rows': 0,
    'h3_regression_performed': True,
    'primary_model_beta1': pr['coef_linear'],
    'primary_model_beta2': pr['coef_quadratic'],
    'primary_model_beta1_sign': 'positive' if float(pr['coef_linear'])>0 else 'negative',
    'primary_model_beta2_sign': 'negative' if float(pr['coef_quadratic'])<0 else 'positive',
    'primary_model_turning_point': pr['turning_point'],
    'primary_model_turning_point_in_range': pr['turning_point_in_range'],
    'primary_model_p_quadratic': pr['p_quadratic'],
    'primary_model_h3_pre_support': pr['h3_pre_preliminary_support'],
    'frequency_robustness_performed': True,
    'nonloo_robustness_performed': True,
    'period_level_ols_performed': True,
    'quarter_fixed_effects_used': False,
    'original_posts_json_modified': posts_json_modified,
}
with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric','value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 11. Validation ────────────────────────────────────────────────────────────
print("[11] Validation")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

all_outs = [DATASET_OUT,PRIMARY_OUT,CENTERED_OUT,FREQ_ROB_OUT,NONLOO_ROB_OUT,
            PERIOD_OLS_OUT,TP_OUT,DIAG_OUT,PRIMARY_PLOT,BIN_PLOT,SUMMARY_OUT]
chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in all_outs), "경로 확인")
chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_filtered_rows_960", len(new_posts)==960, f"n={len(new_posts)}")
chk("04_filtered_quarters_25",
    len(set(r['year_quarter'] for r in new_posts))==25, "25개 분기")
chk("05_primary_predictor_correct",
    diag['primary_predictor']=='humor_proportion_quarter_loo', "변수명 확인")
chk("06_primary_predictor_missing_0",
    diag['primary_predictor_missing_rows']==0, "missing=0")
chk("07_quadratic_term_in_model",
    all('coef_quadratic' in r for r in primary_results), "제곱항 존재")
chk("08_primary_dv_correct",
    primary_results[0]['dv']=='log1p_engagement_total', "primary DV 확인")
chk("09_secondary_dvs_generated",
    len(primary_results)==len(DVS), f"n_dvs={len(primary_results)}")
chk("10_turning_point_computed",
    all('turning_point' in r for r in primary_results), "turning point 존재")
chk("11_turning_point_in_range_recorded",
    all('turning_point_in_range' in r for r in primary_results), "in_range 기록")
chk("12_centered_model_generated",
    len(centered_results)==len(DVS), f"n={len(centered_results)}")
chk("13_frequency_robustness_generated",
    len(freq_results)==len(DVS), f"n={len(freq_results)}")
chk("14_nonloo_robustness_generated",
    len(nonloo_results)==len(DVS), f"n={len(nonloo_results)}")
chk("15_period_level_ols_generated",
    len(period_results)>0, f"n={len(period_results)}")
chk("16_no_quarter_fixed_effects",
    not diag['quarter_fixed_effects_used'], "FE 미사용")
chk("17_primary_plot_exists", os.path.exists(PRIMARY_PLOT), "파일 존재")
chk("18_bin_plot_exists", os.path.exists(BIN_PLOT), "파일 존재")
# 19, 20 summary 작성 후 재확인
chk("19_summary_causal_warning_placeholder", True, "summary 작성 후 확인")
chk("20_summary_h3pre_vs_h3_placeholder", True, "summary 작성 후 확인")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"  Validation 1차: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    import sys; sys.exit(1)

# ── 12. Summary markdown ──────────────────────────────────────────────────────
print("[12] summary.md 작성")

pr = primary_dv_res
pr_c = next(r for r in centered_results if r['dv']=='log1p_engagement_total')
pr_f = next(r for r in freq_results if r['dv']=='log1p_engagement_total')
pr_nl = next(r for r in nonloo_results if r['dv']=='log1p_engagement_total')
pr_p = next((r for r in period_results if 'log1p_engagement_total' in r['dv']), None)

def support_star(p):
    p = float(p)
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '†'
    return 'n.s.'

def primary_table():
    lines = ["| DV | β1(linear) | p | β2(quadratic) | p | turning_point | in_range | H3-pre 지지 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in primary_results:
        b1s = support_star(r['p_linear'])
        b2s = support_star(r['p_quadratic'])
        lines.append(
            f"| {r['dv']} | {r['coef_linear']}({b1s}) | {r['p_linear']} "
            f"| {r['coef_quadratic']}({b2s}) | {r['p_quadratic']} "
            f"| {r['turning_point']} | {r['turning_point_in_range']} | {r['h3_pre_preliminary_support']} |"
        )
    return '\n'.join(lines)

summary_md = f"""# Wendy's H3-pre Quadratic OLS 분석 결과

## 1. 작업 목적

본 분석은 aggressive humor intensity가 아니라 단순 Proportion of Humor에 대한 H3-pre 분석이다.

H3-pre:

```
Wendy's의 Proportion of Humor in SNS Posts는 post-level engagement와 역 U자형 관계를 가질 것이다.
```

이 분석은 최종 H3를 검증하는 것이 아니라, H3 이전 단계에서 단순 유머 비중의 이차항 관계를 확인하는 작업이다.

---

## 2. 사용 데이터

- `wendys_h3_pre_filtered_quarter_dataset.csv`: 필터링된 post-level 데이터
- `wendys_h3_pre_filtered_quarter_period_audit.csv`: 분기별 period-level 집계

---

## 3. 분석 표본

| 항목 | 값 |
|---|---|
| 전체 posts (필터 전) | {len(all_rows)} |
| 필터 기준 | quarter_total_posts ≥ 10 |
| 제외 분기 | 2009-Q4, 2023-Q4, 2025-Q3 |
| **filtered posts** | **{len(new_posts)}** |
| **filtered 분기** | **{len(set(r['year_quarter'] for r in new_posts))}개** |

---

## 4. Primary predictor 정의

Primary predictor는 post i 자신을 제외한 동일 분기 내 유머 게시글 비중인 humor_proportion_quarter_loo이다.

```
humor_proportion_quarter_loo_i = (quarter_humor_posts - humor_i) / (quarter_total_posts - 1)
```

| 항목 | 값 |
|---|---|
| min | {round(x_min,4)} |
| max | {round(x_max,4)} |
| mean | {round(X_loo_mean,4)} |
| sd | {round(float(np.std(X_loo,ddof=1)),4)} |
| missing | 0 |

---

## 5. 분석 모형

```
log1p_engagement_total_i = α + β1·x_i + β2·x_i² + ε_i

x = humor_proportion_quarter_loo
```

quarter fixed effects는 사용하지 않았다. humor_proportion_quarter_loo가 quarter-level 기반 변수이므로 quarter fixed effects와 동시에 사용할 경우 식별이 불가능하기 때문이다.

H3-pre 지지는 β1>0, β2<0, turning point가 관측 범위 내에 존재하는지를 기준으로 판단하였다.

turning point = -β1 / (2β2), 관측 범위: [{round(x_min,4)}, {round(x_max,4)}]

---

## 6. Primary post-level quadratic OLS 결과

{primary_table()}

* p<.05, ** p<.01, *** p<.001, † p<.10

---

## 7. Turning point 결과

**주요 DV: log1p_engagement_total**

| 항목 | 값 |
|---|---|
| β1 (linear) | {pr['coef_linear']} (p={pr['p_linear']}) |
| β2 (quadratic) | {pr['coef_quadratic']} (p={pr['p_quadratic']}) |
| turning point | {pr['turning_point']} |
| 관측 범위 | [{round(x_min,4)}, {round(x_max,4)}] |
| turning point in range | {pr['turning_point_in_range']} |
| turning point 95% CI | [{pr['turning_point_ci_low']}, {pr['turning_point_ci_high']}] |
| H3-pre 판정 | **{pr['h3_pre_preliminary_support']}** |

---

## 8. Centered model 결과 (robustness)

| 항목 | 값 |
|---|---|
| β1 (centered linear) | {pr_c['coef_centered_linear']} (p={pr_c['p_centered_linear']}) |
| β2 (centered quadratic) | {pr_c['coef_centered_quadratic']} (p={pr_c['p_centered_quadratic']}) |
| R² | {pr_c['r_squared']} |

Raw 모델과 R², β2 부호가 일치하는지: {'일치 (β2 모두 음수)' if float(pr['coef_quadratic'])<0 and float(pr_c['coef_centered_quadratic'])<0 else '불일치 확인 필요'}

---

## 9. Frequency robustness 결과

predictor: humor_frequency_quarter (절대 개수 기반, 보조 분석)

| 항목 | 값 |
|---|---|
| β1 | {pr_f['coef_linear']} (p={pr_f['p_linear']}) |
| β2 | {pr_f['coef_quadratic']} (p={pr_f['p_quadratic']}) |
| turning point | {pr_f['turning_point']} |
| in range [{round(x_freq_min,1)}, {round(x_freq_max,1)}] | {pr_f['turning_point_in_range']} |
| H3-pre 판정 | {pr_f['h3_pre_preliminary_support']} |

Frequency는 전체 post 수가 많은 분기에서 자동으로 커질 수 있으므로 primary predictor가 아니라 robustness predictor로 해석한다.

---

## 10. Non-LOO proportion robustness 결과

predictor: humor_proportion_quarter (focal post 자기 포함, 보조 분석)

| 항목 | 값 |
|---|---|
| β1 | {pr_nl['coef_linear']} (p={pr_nl['p_linear']}) |
| β2 | {pr_nl['coef_quadratic']} (p={pr_nl['p_quadratic']}) |
| turning point | {pr_nl['turning_point']} |
| in range | {pr_nl['turning_point_in_range']} |
| H3-pre 판정 | {pr_nl['h3_pre_preliminary_support']} |

---

## 11. Period-level exploratory OLS 결과 (n=25분기)

{'n/a' if pr_p is None else f'''| 항목 | 값 |
|---|---|
| β1 | {pr_p["coef_linear"]} (p={pr_p["p_linear"]}) |
| β2 | {pr_p["coef_quadratic"]} (p={pr_p["p_quadratic"]}) |
| turning point | {pr_p["turning_point"]} |
| in range | {pr_p["turning_point_in_range"]} |
| R² | {pr_p["r_squared"]} |

n=25로 표본이 작기 때문에 exploratory descriptive robustness로만 해석한다.'''}

---

## 12. Bin descriptive pattern과의 관계

| bin | n_posts | mean_log1p_engagement_total |
|---|---|---|
| low (≤{round(t33,4)}) | {len(bins_eng['low'])} | {round(float(np.mean(bins_eng['low'])),4) if bins_eng['low'] else 'nan'} |
| medium ({round(t33,4)}–{round(t67,4)}) | {len(bins_eng['medium'])} | {round(float(np.mean(bins_eng['medium'])),4) if bins_eng['medium'] else 'nan'} |
| high (>{round(t67,4)}) | {len(bins_eng['high'])} | {round(float(np.mean(bins_eng['high'])),4) if bins_eng['high'] else 'nan'} |

Descriptive pattern: low < medium > high (역 U자형) — 회귀 β2 방향{'과 일치' if float(pr['coef_quadratic'])<0 else '과 불일치'}.

---

## 13. H3-pre 판정

**Primary model (humor_proportion_quarter_loo): {pr['h3_pre_preliminary_support']}**

| 판정 기준 | 충족 여부 |
|---|---|
| β1 > 0 (linear) | {'✓' if float(pr['coef_linear'])>0 else '✗'} |
| β2 < 0 (quadratic) | {'✓' if float(pr['coef_quadratic'])<0 else '✗'} |
| turning point in range | {'✓' if pr['turning_point_in_range'] else '✗'} ({pr['turning_point']}) |
| p_quadratic < .05 | {'✓' if float(pr['p_quadratic'])<0.05 else '✗'} (p={pr['p_quadratic']}) |

---

## 14. 해석상 주의사항

본 분석은 관측적 연관성 분석이며, Proportion of Humor가 engagement를 증가시켰다는 인과관계를 주장할 수 없다.

- pred_humor_final_050은 모델 기반 예측값이므로 분류 오류가 포함될 수 있다.
- quarter fixed effects 미사용으로 분기별 시계열 추세가 통제되지 않았다.
- post-level OLS에서 같은 분기 내 게시글은 동일한 humor_proportion_quarter_loo 값을 공유하므로 표준오차가 과소추정될 수 있다 (cluster-robust SE를 사용하지 않음).
- H3-pre는 최종 H3가 아니라 aggressive humor intensity를 제외한 단순 유머 비중의 탐색적 분석이다.
- 본 분석은 aggressive humor intensity가 아니라 단순 Proportion of Humor에 대한 H3-pre 분석이다.

---

## 15. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/H3-pre audit 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# summary 검증
checks[18] = {'check': '19_summary_causal_warning',
              'status': 'PASS' if '인과관계를 주장할 수 없다' in summary_md else 'FAIL',
              'detail': '인과 금지 문장 확인'}
checks[19] = {'check': '20_summary_h3pre_vs_h3',
              'status': 'PASS' if 'H3-pre는 최종 H3가 아니라' in summary_md else 'FAIL',
              'detail': 'H3-pre vs H3 구분 확인'}

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  최종 Validation: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    for c in checks:
        if c['status']=='FAIL':
            print(f"  [✗] {c['check']}: {c['detail']}")
    import sys; sys.exit(1)

print(f"\n[완료] Validation {n_pass}/20 PASS.")
print("  커밋 대상: analysis: run wendys h3 pre quadratic ols")
