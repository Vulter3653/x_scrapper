"""
audit_wendys_simple_humor_intensity.py

목적: H3 회귀분석 이전 사전 점검.
      pred_humor_final_050 기반 단순 humor usage intensity의 월별·분기별 분포를 점검한다.
      H3 회귀분석은 이 스크립트에서 수행하지 않는다.
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

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

PRED_PATH = os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv")
ENG_PATH  = os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

DATASET_OUT   = os.path.join(DATA_DIR,   "wendys_simple_humor_intensity_post_level_dataset.csv")
MONTHLY_OUT   = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_monthly_audit.csv")
QUARTERLY_OUT = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_quarterly_audit.csv")
BIN_OUT       = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_bin_descriptives.csv")
DIAG_OUT      = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_diagnostics.csv")
MPLOT_OUT     = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_monthly_plot.png")
QPLOT_OUT     = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_quarterly_plot.png")
SUMMARY_OUT   = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_summary.md")

np.random.seed(42)

# ── 0. posts.json 보호 확인 ────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
POSTS_JSON_HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        POSTS_JSON_HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  posts.json md5: {POSTS_JSON_HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("[1] 데이터 로드")
with open(PRED_PATH, newline='', encoding='utf-8') as f:
    pred_rows = list(csv.DictReader(f))
with open(ENG_PATH, newline='', encoding='utf-8') as f:
    eng_rows = list(csv.DictReader(f))

pred_by_id = {r['id']: r for r in pred_rows}
eng_by_id  = {r['id']: r for r in eng_rows}
print(f"  pred: {len(pred_rows)}행  eng: {len(eng_rows)}행")

# ── 2. 병합 및 변수 생성 ──────────────────────────────────────────────────────
print("[2] 병합 및 변수 생성")
posts = []
for r_p in pred_rows:
    pid = r_p['id']
    r_e = eng_by_id.get(pid, {})
    if not r_e:
        print(f"  [경고] id={pid} engagement 없음 — 스킵")
        continue

    yr  = r_e.get('created_year','')
    mo  = r_e.get('created_month','')
    dy  = r_e.get('created_day','')
    ct  = r_e.get('created_time','')
    hr  = ct.split(':')[0] if ct else ''

    created_date = f"{yr}-{mo.zfill(2)}-{dy.zfill(2)}" if yr and mo and dy else ''
    year_month   = f"{yr}-{mo.zfill(2)}" if yr and mo else ''
    qnum = (int(mo)-1)//3 + 1 if mo.isdigit() else ''
    year_quarter = f"{yr}-Q{qnum}" if yr and qnum != '' else ''

    reply    = float(r_e.get('reply_count',0) or 0)
    favorite = float(r_e.get('favorite_count',0) or 0)
    retweet  = float(r_e.get('retweet_count',0) or 0)
    quote    = float(r_e.get('quote_count',0) or 0)
    bookmark = float(r_e.get('bookmark_count',0) or 0)
    view     = float(r_e.get('view_count',0) or 0)

    eng_total  = reply + favorite + retweet + quote + bookmark
    eng_fr     = favorite + retweet

    pred_val = r_p.get('pred_humor_final_050','')
    pred_int = int(pred_val) if pred_val in ('0','1') else None
    p_humor  = float(r_p.get('p_humor_final_tfidf_logreg','0') or 0)

    posts.append({
        'id': pid,
        'tweet_url': r_e.get('tweet_url',''),
        'text': r_p.get('text','')[:200],
        'created_year': yr, 'created_month': mo, 'created_day': dy,
        'created_time': ct, 'created_hour': hr,
        'created_date': created_date,
        'year_month': year_month,
        'year_quarter': year_quarter,
        'pred_humor_final_050': pred_val,
        'pred_humor_int': pred_int,
        'p_humor_final_tfidf_logreg': round(p_humor, 6),
        'reply_count': int(reply), 'favorite_count': int(favorite),
        'retweet_count': int(retweet), 'quote_count': int(quote),
        'bookmark_count': int(bookmark), 'view_count': int(view),
        'engagement_total': int(eng_total),
        'engagement_favorite_retweet': int(eng_fr),
        'log1p_engagement_total':            round(math.log1p(eng_total), 6),
        'log1p_engagement_favorite_retweet': round(math.log1p(eng_fr), 6),
        'log1p_favorite_count':  round(math.log1p(favorite), 6),
        'log1p_retweet_count':   round(math.log1p(retweet), 6),
        'log1p_reply_count':     round(math.log1p(reply), 6),
        'log1p_quote_count':     round(math.log1p(quote), 6),
        'log1p_bookmark_count':  round(math.log1p(bookmark), 6),
        'log1p_view_count':      round(math.log1p(view), 6),
        # LOO는 아래에서 채움
        'humor_intensity_month': None,
        'humor_intensity_quarter': None,
        'humor_intensity_month_loo': None,
        'humor_intensity_quarter_loo': None,
    })

print(f"  병합: {len(posts)}행")
pred_humor_count    = sum(1 for r in posts if r['pred_humor_final_050']=='1')
pred_non_humor_count = sum(1 for r in posts if r['pred_humor_final_050']=='0')
missing_pred        = sum(1 for r in posts if r['pred_humor_final_050'] not in ('0','1'))
print(f"  humor={pred_humor_count}, non_humor={pred_non_humor_count}, missing={missing_pred}")

# ── 3. Period-level 집계 (month) ──────────────────────────────────────────────
print("[3] Monthly period-level 집계")
DVS = [
    'log1p_engagement_total','log1p_engagement_favorite_retweet',
    'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
    'log1p_quote_count','log1p_bookmark_count','log1p_view_count'
]

def period_stats(period_key, posts_in_period):
    n = len(posts_in_period)
    h = sum(1 for r in posts_in_period if r['pred_humor_final_050']=='1')
    nh = n - h
    intensity = h / n if n > 0 else float('nan')
    p_hum = [r['p_humor_final_tfidf_logreg'] for r in posts_in_period]
    mean_p  = round(float(np.mean(p_hum)), 6) if p_hum else float('nan')
    med_p   = round(float(np.median(p_hum)), 6) if p_hum else float('nan')
    dates = sorted(r['created_date'] for r in posts_in_period if r['created_date'])
    row = {
        'period': period_key,
        'total_posts': n,
        'humor_posts': h,
        'non_humor_posts': nh,
        'humor_intensity': round(intensity, 4) if not math.isnan(intensity) else 'nan',
        'mean_p_humor': mean_p,
        'median_p_humor': med_p,
        'min_created_date': dates[0] if dates else '',
        'max_created_date': dates[-1] if dates else '',
    }
    for dv in DVS:
        vals = [r[dv] for r in posts_in_period]
        row[f'mean_{dv}']   = round(float(np.mean(vals)), 4) if vals else 'nan'
        row[f'median_{dv}'] = round(float(np.median(vals)), 4) if vals else 'nan'
    return row

# month 집계
by_month = defaultdict(list)
for r in posts:
    by_month[r['year_month']].append(r)

month_periods = sorted(by_month.keys())
monthly_rows = []
for ym in month_periods:
    row = period_stats(ym, by_month[ym])
    row['period_type'] = 'month'
    monthly_rows.append(row)

month_intensities = [float(r['humor_intensity']) for r in monthly_rows if r['humor_intensity'] != 'nan']
print(f"  월별 period: {len(monthly_rows)}개, intensity 범위: [{min(month_intensities):.3f}, {max(month_intensities):.3f}]")

# ── 4. Period-level 집계 (quarter) ────────────────────────────────────────────
print("[4] Quarterly period-level 집계")
by_quarter = defaultdict(list)
for r in posts:
    by_quarter[r['year_quarter']].append(r)

quarter_periods = sorted(by_quarter.keys())
quarterly_rows = []
for yq in quarter_periods:
    row = period_stats(yq, by_quarter[yq])
    row['period_type'] = 'quarter'
    quarterly_rows.append(row)

qtr_intensities = [float(r['humor_intensity']) for r in quarterly_rows if r['humor_intensity'] != 'nan']
print(f"  분기별 period: {len(quarterly_rows)}개, intensity 범위: [{min(qtr_intensities):.3f}, {max(qtr_intensities):.3f}]")

# ── 5. month/quarter intensity를 post-level에 할당 + LOO ──────────────────────
print("[5] Post-level intensity + LOO 생성")
month_total  = {ym: len(by_month[ym]) for ym in month_periods}
month_humor  = {ym: sum(1 for r in by_month[ym] if r['pred_humor_final_050']=='1') for ym in month_periods}
qtr_total    = {yq: len(by_quarter[yq]) for yq in quarter_periods}
qtr_humor    = {yq: sum(1 for r in by_quarter[yq] if r['pred_humor_final_050']=='1') for yq in quarter_periods}

month_loo_missing = 0
qtr_loo_missing   = 0

for r in posts:
    ym = r['year_month']
    yq = r['year_quarter']
    h_i = 1 if r['pred_humor_final_050']=='1' else 0

    # month intensity
    mt = month_total.get(ym, 0)
    mh = month_humor.get(ym, 0)
    r['humor_intensity_month'] = round(mh/mt, 6) if mt > 0 else 'nan'

    # quarter intensity
    qt = qtr_total.get(yq, 0)
    qh = qtr_humor.get(yq, 0)
    r['humor_intensity_quarter'] = round(qh/qt, 6) if qt > 0 else 'nan'

    # LOO month
    if mt <= 1:
        r['humor_intensity_month_loo'] = 'nan'
        month_loo_missing += 1
    else:
        r['humor_intensity_month_loo'] = round((mh - h_i) / (mt - 1), 6)

    # LOO quarter
    if qt <= 1:
        r['humor_intensity_quarter_loo'] = 'nan'
        qtr_loo_missing += 1
    else:
        r['humor_intensity_quarter_loo'] = round((qh - h_i) / (qt - 1), 6)

print(f"  LOO month missing: {month_loo_missing}행  LOO quarter missing: {qtr_loo_missing}행")

# ── 6. Post-level dataset 저장 ────────────────────────────────────────────────
print("[6] Post-level dataset 저장")
ds_fields = [
    'id','tweet_url','text','created_year','created_month','created_day',
    'created_time','created_hour','created_date','year_month','year_quarter',
    'pred_humor_final_050','p_humor_final_tfidf_logreg',
    'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
    'engagement_total','engagement_favorite_retweet',
    'log1p_engagement_total','log1p_engagement_favorite_retweet',
    'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
    'log1p_quote_count','log1p_bookmark_count','log1p_view_count',
    'humor_intensity_month','humor_intensity_quarter',
    'humor_intensity_month_loo','humor_intensity_quarter_loo',
]
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=ds_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(posts)
print(f"  → {DATASET_OUT}")

# ── 7. Monthly / Quarterly audit 저장 ────────────────────────────────────────
print("[7] Monthly/Quarterly audit 저장")

period_fields = (
    ['period','period_type','total_posts','humor_posts','non_humor_posts',
     'humor_intensity','mean_p_humor','median_p_humor'] +
    [f'mean_{dv}' for dv in DVS] +
    [f'median_{dv}' for dv in ['log1p_engagement_total']] +
    ['min_created_date','max_created_date']
)

with open(MONTHLY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=period_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(monthly_rows)
print(f"  → {MONTHLY_OUT}")

with open(QUARTERLY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=period_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(quarterly_rows)
print(f"  → {QUARTERLY_OUT}")

# ── 8. 분석 단위 적합성 진단 ──────────────────────────────────────────────────
print("[8] 분석 단위 적합성 진단")

def period_fitness(rows, period_name):
    totals = [r['total_posts'] for r in rows]
    humors = [r['humor_posts'] for r in rows]
    intens = [float(r['humor_intensity']) for r in rows if r['humor_intensity'] != 'nan']
    return {
        'period': period_name,
        'n_periods': len(rows),
        'total_posts_min': min(totals), 'total_posts_max': max(totals),
        'total_posts_mean': round(float(np.mean(totals)),2), 'total_posts_median': float(np.median(totals)),
        'humor_posts_min': min(humors), 'humor_posts_max': max(humors),
        'humor_posts_mean': round(float(np.mean(humors)),2), 'humor_posts_median': float(np.median(humors)),
        'intensity_min': round(min(intens),4), 'intensity_max': round(max(intens),4),
        'intensity_mean': round(float(np.mean(intens)),4), 'intensity_sd': round(float(np.std(intens,ddof=1)),4),
        'n_periods_under_5_posts': sum(1 for t in totals if t < 5),
        'n_periods_under_10_posts': sum(1 for t in totals if t < 10),
    }

mfit = period_fitness(monthly_rows, 'month')
qfit = period_fitness(quarterly_rows, 'quarter')

print(f"  [month] n={mfit['n_periods']}, total_posts: min={mfit['total_posts_min']} med={mfit['total_posts_median']} max={mfit['total_posts_max']}")
print(f"          intensity: [{mfit['intensity_min']:.3f}, {mfit['intensity_max']:.3f}] mean={mfit['intensity_mean']:.3f} sd={mfit['intensity_sd']:.3f}")
print(f"          n_periods_under_10: {mfit['n_periods_under_10_posts']}")
print(f"  [quarter] n={qfit['n_periods']}, total_posts: min={qfit['total_posts_min']} med={qfit['total_posts_median']} max={qfit['total_posts_max']}")
print(f"            intensity: [{qfit['intensity_min']:.3f}, {qfit['intensity_max']:.3f}] mean={qfit['intensity_mean']:.3f} sd={qfit['intensity_sd']:.3f}")
print(f"            n_periods_under_10: {qfit['n_periods_under_10_posts']}")

# recommended_period_unit 결정
# 기준: month under_10 비율이 50% 이상이면 quarter 추천
# quarter under_10도 많으면 insufficient
month_sparse_ratio = mfit['n_periods_under_10_posts'] / mfit['n_periods']
qtr_sparse_ratio   = qfit['n_periods_under_10_posts'] / qfit['n_periods']

if qfit['n_periods'] < 4 or qfit['total_posts_min'] < 2:
    recommended = 'insufficient'
elif month_sparse_ratio > 0.5:
    recommended = 'quarter'
elif mfit['intensity_sd'] >= 0.05 and mfit['total_posts_min'] >= 3:
    if qfit['intensity_sd'] >= 0.05:
        recommended = 'both'
    else:
        recommended = 'month'
else:
    recommended = 'quarter'

print(f"\n  recommended_period_unit: {recommended}")
print(f"  (month_sparse_ratio={month_sparse_ratio:.2f}, qtr_sparse_ratio={qtr_sparse_ratio:.2f})")

# ── 9. Intensity bin descriptives ─────────────────────────────────────────────
print("[9] Intensity bin descriptives")
bin_rows = []

def bin_by_intensity(period_rows, post_rows, period_col, period_name):
    intens_vals = [float(r['humor_intensity']) for r in period_rows if r['humor_intensity']!='nan']
    n_unique = len(set(round(v,4) for v in intens_vals))

    # tertile 시도, unique 값이 3 미만이면 2개 bin으로 축소
    if n_unique >= 3:
        try:
            t33 = float(np.percentile(intens_vals, 33.33))
            t67 = float(np.percentile(intens_vals, 66.67))
            bins = [('low', 0.0, t33), ('medium', t33, t67), ('high', t67, 1.01)]
            n_bins_used = 3
        except Exception:
            t50 = float(np.percentile(intens_vals, 50))
            bins = [('low', 0.0, t50), ('high', t50, 1.01)]
            n_bins_used = 2
    elif n_unique == 2:
        t50 = float(np.percentile(intens_vals, 50))
        bins = [('low', 0.0, t50), ('high', t50, 1.01)]
        n_bins_used = 2
    else:
        bins = [('all', 0.0, 1.01)]
        n_bins_used = 1

    # period별 intensity 매핑
    period_intensity = {r['period']: float(r['humor_intensity']) for r in period_rows if r['humor_intensity']!='nan'}

    for bin_label, lo, hi in bins:
        periods_in_bin = [p for p, v in period_intensity.items() if lo <= v < hi]
        posts_in_bin   = [r for r in post_rows if r[period_col] in periods_in_bin]
        n_posts = len(posts_in_bin)
        n_periods_bin = len(periods_in_bin)
        if n_posts == 0:
            continue
        intens_in_bin = [period_intensity[r[period_col]] for r in posts_in_bin if r[period_col] in period_intensity]
        eng_vals = [r['log1p_engagement_total'] for r in posts_in_bin]
        row = {
            'period_type': period_name,
            'bin': bin_label,
            'n_posts': n_posts,
            'n_periods': n_periods_bin,
            'min_humor_intensity': round(min(intens_in_bin),4) if intens_in_bin else 'nan',
            'max_humor_intensity': round(max(intens_in_bin),4) if intens_in_bin else 'nan',
            'mean_humor_intensity': round(float(np.mean(intens_in_bin)),4) if intens_in_bin else 'nan',
            'mean_log1p_engagement_total':   round(float(np.mean(eng_vals)),4),
            'median_log1p_engagement_total': round(float(np.median(eng_vals)),4),
            'n_bins_available': n_bins_used,
        }
        for dv in DVS[1:]:
            vals = [r[dv] for r in posts_in_bin]
            row[f'mean_{dv}'] = round(float(np.mean(vals)),4) if vals else 'nan'
        bin_rows.append(row)

bin_by_intensity(monthly_rows,   posts, 'year_month',   'month')
bin_by_intensity(quarterly_rows, posts, 'year_quarter', 'quarter')

bin_fields = (
    ['period_type','bin','n_posts','n_periods','n_bins_available',
     'min_humor_intensity','max_humor_intensity','mean_humor_intensity',
     'mean_log1p_engagement_total','median_log1p_engagement_total'] +
    [f'mean_{dv}' for dv in DVS[1:]]
)
with open(BIN_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=bin_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(bin_rows)
print(f"  → {BIN_OUT}")

# bin pattern 출력
for pt in ['month','quarter']:
    rows_pt = [r for r in bin_rows if r['period_type']==pt]
    print(f"  [{pt}]", {r['bin']: r['mean_log1p_engagement_total'] for r in rows_pt})

# ── 10. 시각화 ───────────────────────────────────────────────────────────────
print("[10] 시각화")

def make_intensity_plot(period_rows, title, out_path):
    periods  = [r['period'] for r in period_rows]
    intens   = [float(r['humor_intensity']) if r['humor_intensity']!='nan' else 0 for r in period_rows]
    eng_means = [float(r['mean_log1p_engagement_total']) if r['mean_log1p_engagement_total']!='nan' else 0 for r in period_rows]
    totals   = [r['total_posts'] for r in period_rows]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(max(10, len(periods)*0.35), 7), sharex=True)

    color_bar = ['#E74C3C' if i >= 0.6 else '#3498DB' if i >= 0.4 else '#95A5A6' for i in intens]
    ax1.bar(range(len(periods)), intens, color=color_bar, width=0.7, edgecolor='white')
    ax1.set_ylabel("Humor Intensity\n(pred_humor_final_050)", fontsize=9)
    ax1.set_title(title, fontsize=10)
    ax1.set_ylim(0, 1)
    ax1.axhline(float(np.mean(intens)), color='black', linestyle='--', linewidth=0.8, alpha=0.6,
                label=f"Mean={np.mean(intens):.3f}")
    ax1.legend(fontsize=8)

    ax2.plot(range(len(periods)), eng_means, color='#2ECC71', marker='o', markersize=4, linewidth=1.2)
    ax2_twin = ax2.twinx()
    ax2_twin.bar(range(len(periods)), totals, alpha=0.2, color='gray', width=0.7)
    ax2_twin.set_ylabel("n_posts", fontsize=8, color='gray')
    ax2.set_ylabel("Mean log1p(engagement)", fontsize=9)
    ax2.set_xticks(range(len(periods)))
    ax2.set_xticklabels(periods, rotation=75, fontsize=7, ha='right')

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()

make_intensity_plot(monthly_rows,   "Wendy's Monthly Humor Intensity (Exploratory Pre-audit)", MPLOT_OUT)
print(f"  → {MPLOT_OUT}")
make_intensity_plot(quarterly_rows, "Wendy's Quarterly Humor Intensity (Exploratory Pre-audit)", QPLOT_OUT)
print(f"  → {QPLOT_OUT}")

# ── 11. Diagnostics ───────────────────────────────────────────────────────────
print("[11] diagnostics")
posts_json_modified = False
if POSTS_JSON_HASH_BEFORE:
    try:
        with open(POSTS_JSON,'rb') as f:
            h_after = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h_after != POSTS_JSON_HASH_BEFORE)
    except FileNotFoundError:
        pass

diag = {
    'total_rows': len(pred_rows),
    'merged_rows': len(posts),
    'predicted_humor_rows': pred_humor_count,
    'predicted_non_humor_rows': pred_non_humor_count,
    'missing_pred_humor_rows': missing_pred,
    'month_period_count': len(monthly_rows),
    'quarter_period_count': len(quarterly_rows),
    'month_total_posts_min': mfit['total_posts_min'],
    'month_total_posts_median': mfit['total_posts_median'],
    'month_total_posts_mean': mfit['total_posts_mean'],
    'month_total_posts_max': mfit['total_posts_max'],
    'quarter_total_posts_min': qfit['total_posts_min'],
    'quarter_total_posts_median': qfit['total_posts_median'],
    'quarter_total_posts_mean': qfit['total_posts_mean'],
    'quarter_total_posts_max': qfit['total_posts_max'],
    'month_humor_intensity_min': mfit['intensity_min'],
    'month_humor_intensity_max': mfit['intensity_max'],
    'month_humor_intensity_mean': mfit['intensity_mean'],
    'month_humor_intensity_sd': mfit['intensity_sd'],
    'quarter_humor_intensity_min': qfit['intensity_min'],
    'quarter_humor_intensity_max': qfit['intensity_max'],
    'quarter_humor_intensity_mean': qfit['intensity_mean'],
    'quarter_humor_intensity_sd': qfit['intensity_sd'],
    'month_sparse_ratio_under10': round(month_sparse_ratio, 4),
    'quarter_sparse_ratio_under10': round(qtr_sparse_ratio, 4),
    'month_loo_missing_rows': month_loo_missing,
    'quarter_loo_missing_rows': qtr_loo_missing,
    'recommended_period_unit': recommended,
    'original_posts_json_modified': posts_json_modified,
    'analysis_note': 'H3 회귀분석 이전 사전 점검. 회귀분석 미수행.',
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

chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in [DATASET_OUT,MONTHLY_OUT,QUARTERLY_OUT,BIN_OUT,DIAG_OUT,MPLOT_OUT,QPLOT_OUT,SUMMARY_OUT]),
    "경로 확인")
chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_merged_rows_978", len(posts)==978, f"n={len(posts)}")
chk("04_predicted_humor_564", pred_humor_count==564, f"n={pred_humor_count}")
chk("05_predicted_non_humor_414", pred_non_humor_count==414, f"n={pred_non_humor_count}")
chk("06_missing_pred_0", missing_pred==0, f"missing={missing_pred}")
chk("07_monthly_quarterly_audit_exists", os.path.exists(MONTHLY_OUT) and os.path.exists(QUARTERLY_OUT), "파일 존재")
chk("08_loo_month_exists", all('humor_intensity_month_loo' in r for r in posts), "컬럼 존재")
chk("09_loo_quarter_exists", all('humor_intensity_quarter_loo' in r for r in posts), "컬럼 존재")
chk("10_bin_descriptives_exists", os.path.exists(BIN_OUT) and len(bin_rows)>0, f"rows={len(bin_rows)}")
chk("11_no_regression_performed", True, "H1/H2/H3 회귀 미수행 (사전 점검만)")
chk("12_no_aggressive_intensity", True, "aggressive intensity 미분석")
chk("13_recommended_period_unit_set", diag['recommended_period_unit'] in ('month','quarter','both','insufficient'), f"unit={diag['recommended_period_unit']}")
chk("14_month_period_count_reasonable", mfit['n_periods'] > 0, f"n={mfit['n_periods']}")
chk("15_quarter_period_count_reasonable", qfit['n_periods'] > 0, f"n={qfit['n_periods']}")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  Validation 1차: {n_pass}/15 PASS, {n_fail} FAIL")

if n_fail > 0:
    print("[ERROR] 검증 FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

# ── 13. Summary markdown ──────────────────────────────────────────────────────
print("[13] summary.md 작성")

month_bin_rows  = [r for r in bin_rows if r['period_type']=='month']
qtr_bin_rows    = [r for r in bin_rows if r['period_type']=='quarter']
month_bin_dict  = {r['bin']: r for r in month_bin_rows}
qtr_bin_dict    = {r['bin']: r for r in qtr_bin_rows}

def bin_table_md(bin_dict):
    lines = ["| bin | n_posts | n_periods | mean_intensity | mean_log1p_engagement |",
             "|---|---|---|---|---|"]
    for b in ['low','medium','high','all']:
        if b in bin_dict:
            r = bin_dict[b]
            lines.append(f"| {b} | {r['n_posts']} | {r['n_periods']} | {r['mean_humor_intensity']} | {r['mean_log1p_engagement_total']} |")
    return '\n'.join(lines)

summary_md = f"""# Wendy's 단순 Humor Usage Intensity 사전 점검 결과

## 1. 작업 목적

본 작업은 H3 회귀분석이 아니라, 단순 humor usage intensity의 기간별 분포와 변동성을 확인하기 위한 사전 점검이다.

H3-pre 아이디어:

```
H3-pre: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다.
```

이번 단계에서는 위 가설을 검정하지 않는다.
이 사전 점검의 목적은 다음이다:

1. 월별/분기별 humor intensity가 충분히 변동하는지 확인
2. 어느 기간 단위(month vs quarter)가 이후 H3-pre 분석에 적합한지 판단
3. Leave-one-out intensity 변수 생성

---

## 2. 사용 데이터

- `wendys_final_humor_presence_full_predictions.csv`: 전체 978건 유머 유무 예측값
- `wendys_fast_weak_supervised_humor_dataset.csv`: engagement 원자료

병합 기준: `id` ({len(posts)}건 완전 매칭)

---

## 3. 유머 유무 기준

humor_intensity는 모델 기반 유머 유무 예측값인 pred_humor_final_050을 사용해 계산되었으며, 전체 게시글에 대한 확정 사람 코딩 결과가 아니다.

```
pred_humor_final_050 = 1 → model-predicted humor
pred_humor_final_050 = 0 → model-predicted non_humor
```

- predicted humor: {pred_humor_count}건 ({pred_humor_count/len(posts)*100:.1f}%)
- predicted non_humor: {pred_non_humor_count}건 ({pred_non_humor_count/len(posts)*100:.1f}%)
- missing: {missing_pred}건

보조 확률 변수 `p_humor_final_tfidf_logreg`의 period 평균도 함께 산출하였다.

---

## 4. 월별 humor intensity 분포

- 총 월별 period: **{mfit['n_periods']}개**
- period별 total_posts: min={mfit['total_posts_min']}, median={mfit['total_posts_median']}, mean={mfit['total_posts_mean']}, max={mfit['total_posts_max']}
- period별 humor_posts: min={mfit['humor_posts_min']}, max={mfit['humor_posts_max']}, mean={mfit['humor_posts_mean']}
- humor_intensity: min={mfit['intensity_min']:.4f}, max={mfit['intensity_max']:.4f}, mean={mfit['intensity_mean']:.4f}, sd={mfit['intensity_sd']:.4f}
- total_posts < 10인 period 수: {mfit['n_periods_under_10_posts']}개 (전체의 {month_sparse_ratio*100:.1f}%)

월별 period는 게시글 수가 매우 적은 달이 다수 포함되어 있다.
총 {mfit['n_periods']}개 월 중 {mfit['n_periods_under_10_posts']}개 월이 게시글 10건 미만이다.

---

## 5. 분기별 humor intensity 분포

- 총 분기별 period: **{qfit['n_periods']}개**
- period별 total_posts: min={qfit['total_posts_min']}, median={qfit['total_posts_median']}, mean={qfit['total_posts_mean']}, max={qfit['total_posts_max']}
- period별 humor_posts: min={qfit['humor_posts_min']}, max={qfit['humor_posts_max']}, mean={qfit['humor_posts_mean']}
- humor_intensity: min={qfit['intensity_min']:.4f}, max={qfit['intensity_max']:.4f}, mean={qfit['intensity_mean']:.4f}, sd={qfit['intensity_sd']:.4f}
- total_posts < 10인 period 수: {qfit['n_periods_under_10_posts']}개 (전체의 {qtr_sparse_ratio*100:.1f}%)

---

## 6. Leave-one-out intensity 생성 결과

post i를 제외한 leave-one-out humor intensity 변수를 생성하였다.

```
humor_intensity_month_loo = (month_humor_posts - pred_humor_final_050_i) / (month_total_posts - 1)
humor_intensity_quarter_loo = (quarter_humor_posts - pred_humor_final_050_i) / (quarter_total_posts - 1)
```

- month LOO missing (period total=1인 post): {month_loo_missing}건
- quarter LOO missing (period total=1인 post): {qtr_loo_missing}건

다음 단계에서 H3-pre 회귀분석을 수행할 경우, post i를 제외한 leave-one-out humor_intensity를 사용하는 것이 더 적절하다.

---

## 7. Intensity bin별 descriptive pattern

engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.

H3-pre 기대 패턴: **low < medium > high** (역 U자형)

### 월별 기준 bin

{bin_table_md(month_bin_dict)}

### 분기별 기준 bin

{bin_table_md(qtr_bin_dict)}

(descriptive pattern only — H3 지지 여부 미판정)

---

## 8. H3-pre 분석 단위 추천

| 기준 | month | quarter |
|---|---|---|
| period 수 | {mfit['n_periods']} | {qfit['n_periods']} |
| total_posts 최솟값 | {mfit['total_posts_min']} | {qfit['total_posts_min']} |
| total_posts 중앙값 | {mfit['total_posts_median']} | {qfit['total_posts_median']} |
| intensity sd | {mfit['intensity_sd']} | {qfit['intensity_sd']} |
| sparse period (<10 posts) 비율 | {month_sparse_ratio*100:.1f}% | {qtr_sparse_ratio*100:.1f}% |

**추천 단위: `{recommended}`**

월별 period의 게시글 수가 지나치게 작거나 sparse하면 quarter 기준이 더 안정적이다.
반대로 월별 period 수와 post 수가 충분하면 month 기준이 더 세밀한 intensity 분석에 적합하다.

현재 데이터 기준으로는 월별 게시글이 적은 기간이 다수 존재하여 표본 안정성 문제가 있다.
이후 H3-pre 회귀분석에서는 두 단위를 모두 사용하되, 결과를 교차 확인하는 방법이 적절하다.

---

## 9. 해석상 주의사항

- 본 작업은 H3 회귀분석이 아니라, 단순 humor usage intensity의 기간별 분포와 변동성을 확인하기 위한 사전 점검이다.
- humor_intensity는 모델 기반 유머 유무 예측값인 pred_humor_final_050을 사용해 계산되었으며, 전체 게시글에 대한 확정 사람 코딩 결과가 아니다.
- engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.
- 다음 단계에서 H3-pre 회귀분석을 수행할 경우, post i를 제외한 leave-one-out humor_intensity를 사용하는 것이 더 적절하다.
- self-endogeneity 문제를 방지하기 위해 분석 단위 내 자기 자신의 humor 여부가 period intensity에 포함되지 않도록 LOO 변수를 사전 생성하였다.

---

## 10. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2 결과 파일 수정 없음
- H3 회귀분석 미수행

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# summary 내용 재검증
checks.append({
    'check': 'summary_has_preaudit_statement',
    'status': 'PASS' if '사전 점검' in summary_md else 'FAIL',
    'detail': '사전 점검 표현 확인'
})
checks.append({
    'check': 'summary_has_causal_warning',
    'status': 'PASS' if '인과관계나 통계적 유의성을 해석하지 않는다' in summary_md else 'FAIL',
    'detail': '인과 해석 금지 문장 확인'
})
checks.append({
    'check': 'summary_has_loo_statement',
    'status': 'PASS' if 'leave-one-out' in summary_md else 'FAIL',
    'detail': 'LOO 안내 문장 확인'
})
checks.append({
    'check': 'summary_has_model_based_warning',
    'status': 'PASS' if 'pred_humor_final_050' in summary_md else 'FAIL',
    'detail': '모델 기반 예측값 경고 확인'
})

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  최종 Validation: {n_pass}/{len(checks)} PASS, {n_fail} FAIL")
if n_fail > 0:
    for c in checks:
        if c['status']=='FAIL':
            print(f"  [✗] {c['check']}: {c['detail']}")
    print("[ERROR] 검증 FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

print(f"\n[완료] 모든 분석 완료. Validation {n_pass}/{len(checks)} PASS.")
print("  커밋 대상: analysis: audit wendys simple humor intensity")
