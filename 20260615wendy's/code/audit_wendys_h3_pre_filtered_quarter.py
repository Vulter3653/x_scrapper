"""
audit_wendys_h3_pre_filtered_quarter.py

목적: quarter_total_posts >= 10 기준으로 sparse period를 제외한 filtered H3-pre audit.
      H3 회귀분석은 수행하지 않는다.
      humor_proportion_quarter_loo 및 humor_frequency_quarter 분포 확인,
      low/medium/high bin별 descriptive engagement pattern 확인.
"""

import csv
import math
import os
import hashlib
from collections import defaultdict, Counter

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

POST_DS_IN  = os.path.join(DATA_DIR,   "wendys_humor_frequency_proportion_post_level_dataset.csv")
POSTS_JSON  = os.path.join("data", "wendys", "posts.json")

DATASET_OUT   = os.path.join(DATA_DIR,   "wendys_h3_pre_filtered_quarter_dataset.csv")
PERIOD_OUT    = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_period_audit.csv")
BIN_OUT       = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_bin_descriptives.csv")
DIAG_OUT      = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_diagnostics.csv")
PLOT_OUT      = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_plot.png")
SUMMARY_OUT   = os.path.join(RESULT_DIR, "wendys_h3_pre_filtered_quarter_summary.md")

FILTER_MIN_POSTS = 10
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
    print(f"  posts.json md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 데이터 로드 ────────────────────────────────────────────────────────────
print("[1] 데이터 로드")
with open(POST_DS_IN, newline='', encoding='utf-8') as f:
    all_posts = list(csv.DictReader(f))
print(f"  전체 rows: {len(all_posts)}")

# ── 2. 필터 적용: quarter_total_posts >= 10 ───────────────────────────────────
print(f"[2] 필터 적용: quarter_total_posts >= {FILTER_MIN_POSTS}")

excluded_posts  = [r for r in all_posts if int(float(r['quarter_total_posts'])) < FILTER_MIN_POSTS]
filtered_posts  = [r for r in all_posts if int(float(r['quarter_total_posts'])) >= FILTER_MIN_POSTS]

excluded_quarters = sorted(set(r['year_quarter'] for r in excluded_posts))
included_quarters = sorted(set(r['year_quarter'] for r in filtered_posts))

print(f"  제외 분기: {excluded_quarters}")
print(f"  제외 posts: {len(excluded_posts)}건")
print(f"  포함 posts: {len(filtered_posts)}건 (분기 {len(included_quarters)}개)")

# 필터된 표본에서 humor/non-humor 분포
pred_humor     = sum(1 for r in filtered_posts if r['pred_humor_final_050']=='1')
pred_non_humor = sum(1 for r in filtered_posts if r['pred_humor_final_050']=='0')
loo_missing    = sum(1 for r in filtered_posts if r['humor_proportion_quarter_loo'] == 'nan')

print(f"  filtered humor={pred_humor}, non_humor={pred_non_humor}, loo_missing={loo_missing}")

# ── 3. 분기별 period-level 집계 (filtered) ────────────────────────────────────
print("[3] 분기별 period-level 집계 (filtered)")
by_qtr = defaultdict(list)
for r in filtered_posts:
    by_qtr[r['year_quarter']].append(r)

period_rows = []
for yq in sorted(by_qtr.keys()):
    rows = by_qtr[yq]
    n     = len(rows)
    h     = sum(1 for r in rows if r['pred_humor_final_050']=='1')
    prop  = round(h/n, 6) if n > 0 else float('nan')
    freq  = h
    # LOO proportion: post에 이미 계산된 값 사용 (대표값: 분기 내 평균)
    loo_vals = [float(r['humor_proportion_quarter_loo']) for r in rows
                if r['humor_proportion_quarter_loo'] != 'nan']
    mean_loo = round(float(np.mean(loo_vals)), 6) if loo_vals else float('nan')
    p_hum_vals = [float(r['p_humor_final_tfidf_logreg']) for r in rows]
    dates = sorted(r['created_date'] for r in rows if r['created_date'])
    pr = {
        'period': yq,
        'total_posts': n,
        'humor_posts': h,
        'non_humor_posts': n - h,
        'humor_frequency': freq,
        'humor_proportion': prop,
        'mean_humor_proportion_loo': mean_loo,
        'mean_p_humor': round(float(np.mean(p_hum_vals)), 4),
        'min_created_date': dates[0] if dates else '',
        'max_created_date': dates[-1] if dates else '',
    }
    for dv in DVS:
        vals = [float(r[dv]) for r in rows]
        pr[f'mean_{dv}']   = round(float(np.mean(vals)), 4)
        pr[f'median_{dv}'] = round(float(np.median(vals)), 4)
    period_rows.append(pr)

period_fields = (
    ['period','total_posts','humor_posts','non_humor_posts',
     'humor_frequency','humor_proportion','mean_humor_proportion_loo','mean_p_humor',
     'min_created_date','max_created_date'] +
    [f'mean_{d}' for d in DVS] +
    [f'median_{d}' for d in ['log1p_engagement_total']]
)
with open(PERIOD_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=period_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(period_rows)
print(f"  → {PERIOD_OUT}")

# ── 4. LOO proportion 분포 확인 (post-level 및 period-level) ──────────────────
print("[4] humor_proportion_quarter_loo 분포 확인")

def safe_float(v):
    if v in ('nan', '', None): return None
    try: return float(v)
    except: return None

def summary_stats(vals):
    v = [x for x in vals if x is not None]
    if not v: return {}
    n = len(v)
    m = sum(v)/n
    sd = math.sqrt(sum((x-m)**2 for x in v)/(n-1)) if n>1 else 0
    v_sorted = sorted(v)
    return {
        'n': n, 'min': round(min(v),4), 'max': round(max(v),4),
        'mean': round(m,4), 'sd': round(sd,4), 'median': round(v_sorted[n//2],4),
        'p25': round(v_sorted[int(n*0.25)],4), 'p75': round(v_sorted[int(n*0.75)],4),
    }

# post-level
loo_post = [safe_float(r['humor_proportion_quarter_loo']) for r in filtered_posts]
freq_post = [safe_float(r['humor_frequency_quarter']) for r in filtered_posts]
prop_post = [safe_float(r['humor_proportion_quarter']) for r in filtered_posts]

loo_stats  = summary_stats(loo_post)
freq_stats = summary_stats(freq_post)
prop_stats = summary_stats(prop_post)

print(f"  [post-level, n={loo_stats['n']}]")
print(f"  loo_proportion: min={loo_stats['min']} max={loo_stats['max']} mean={loo_stats['mean']} sd={loo_stats['sd']}")
print(f"  frequency:      min={freq_stats['min']} max={freq_stats['max']} mean={freq_stats['mean']} sd={freq_stats['sd']}")
print(f"  proportion:     min={prop_stats['min']} max={prop_stats['max']} mean={prop_stats['mean']} sd={prop_stats['sd']}")

# period-level
period_loo  = [safe_float(str(r['mean_humor_proportion_loo'])) for r in period_rows]
period_freq = [r['humor_frequency'] for r in period_rows]
period_prop = [r['humor_proportion'] for r in period_rows]

ploo_stats  = summary_stats(period_loo)
pfreq_stats = summary_stats(period_freq)
pprop_stats = summary_stats(period_prop)

print(f"  [period-level, n={len(period_rows)}분기]")
print(f"  loo_proportion: min={ploo_stats['min']} max={ploo_stats['max']} mean={ploo_stats['mean']} sd={ploo_stats['sd']}")
print(f"  frequency:      min={pfreq_stats['min']} max={pfreq_stats['max']} mean={pfreq_stats['mean']} sd={pfreq_stats['sd']}")

# ── 5. dataset 저장 ───────────────────────────────────────────────────────────
print("[5] filtered post-level dataset 저장")
orig_fields = list(all_posts[0].keys())
extra_fields = ['quarter_filter_applied', 'in_filtered_sample']
with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=orig_fields + extra_fields, extrasaction='ignore')
    w.writeheader()
    filtered_set = set(r['id'] for r in filtered_posts)
    for r in all_posts:
        new_r = dict(r)
        new_r['quarter_filter_applied'] = f'quarter_total_posts>={FILTER_MIN_POSTS}'
        new_r['in_filtered_sample'] = '1' if r['id'] in filtered_set else '0'
        w.writerow(new_r)
print(f"  → {DATASET_OUT}")

# ── 6. Tertile bin descriptives ───────────────────────────────────────────────
print("[6] Tertile bin descriptives")

def tertile_bins(vals_for_cut, filtered_rows, predictor_col, label):
    """
    vals_for_cut: period-level proportion 값 리스트 (25개 분기)
    각 post에 해당 분기의 proportion 값 기반으로 bin 할당
    """
    valid = [v for v in vals_for_cut if v is not None]
    t33 = float(np.percentile(valid, 33.33))
    t67 = float(np.percentile(valid, 66.67))
    n_unique = len(set(round(v,4) for v in valid))
    print(f"  [{label}] t33={t33:.4f} t67={t67:.4f} n_unique={n_unique}")

    # post에 bin 할당 (LOO 값 기준)
    def assign_bin(v):
        if v is None: return 'missing'
        if v <= t33:  return 'low'
        if v <= t67:  return 'medium'
        return 'high'

    bin_data = defaultdict(list)
    for r in filtered_rows:
        v = safe_float(r[predictor_col])
        b = assign_bin(v)
        bin_data[b].append(r)

    bin_rows_out = []
    for b in ['low', 'medium', 'high', 'missing']:
        rows_b = bin_data[b]
        if not rows_b: continue
        eng_vals = [float(r['log1p_engagement_total']) for r in rows_b]
        pred_vals = [safe_float(r[predictor_col]) for r in rows_b if safe_float(r[predictor_col]) is not None]
        row = {
            'predictor': predictor_col,
            'bin_basis': label,
            'bin': b,
            'n_posts': len(rows_b),
            'n_periods': len(set(r['year_quarter'] for r in rows_b)),
            'min_predictor': round(min(pred_vals),4) if pred_vals else 'nan',
            'max_predictor': round(max(pred_vals),4) if pred_vals else 'nan',
            'mean_predictor': round(float(np.mean(pred_vals)),4) if pred_vals else 'nan',
            'mean_log1p_engagement_total': round(float(np.mean(eng_vals)),4),
            'median_log1p_engagement_total': round(float(np.median(eng_vals)),4),
            'tertile_t33': round(t33,4),
            'tertile_t67': round(t67,4),
        }
        for dv in DVS[1:]:
            vals_dv = [float(r[dv]) for r in rows_b]
            row[f'mean_{dv}'] = round(float(np.mean(vals_dv)),4)
        bin_rows_out.append(row)

    pattern = [f"{r['bin']}={r['mean_log1p_engagement_total']}" for r in bin_rows_out if r['bin'] in ('low','medium','high')]
    print(f"    pattern: {' | '.join(pattern)}")
    return bin_rows_out, t33, t67

# (A) humor_proportion_quarter_loo 기준
loo_vals_for_cut = [safe_float(r['humor_proportion_quarter_loo']) for r in filtered_posts]
bin_loo, t33_loo, t67_loo = tertile_bins(
    loo_vals_for_cut, filtered_posts, 'humor_proportion_quarter_loo', 'proportion_loo')

# (B) humor_frequency_quarter 기준
freq_vals_for_cut = [safe_float(r['humor_frequency_quarter']) for r in filtered_posts]
bin_freq, t33_freq, t67_freq = tertile_bins(
    freq_vals_for_cut, filtered_posts, 'humor_frequency_quarter', 'frequency')

# (C) humor_proportion_quarter 기준 (보조)
prop_vals_for_cut = [safe_float(r['humor_proportion_quarter']) for r in filtered_posts]
bin_prop, t33_prop, t67_prop = tertile_bins(
    prop_vals_for_cut, filtered_posts, 'humor_proportion_quarter', 'proportion')

all_bin_rows = bin_loo + bin_freq + bin_prop
bin_fields = (
    ['predictor','bin_basis','bin','n_posts','n_periods',
     'min_predictor','max_predictor','mean_predictor','tertile_t33','tertile_t67',
     'mean_log1p_engagement_total','median_log1p_engagement_total'] +
    [f'mean_{d}' for d in DVS[1:]]
)
with open(BIN_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=bin_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(all_bin_rows)
print(f"  → {BIN_OUT}")

# ── 7. 시각화 ─────────────────────────────────────────────────────────────────
print("[7] 시각화")

fig, axes = plt.subplots(2, 2, figsize=(12, 9))

# 1. LOO proportion 히스토그램
ax = axes[0, 0]
loo_vals_plot = [v for v in loo_post if v is not None]
ax.hist(loo_vals_plot, bins=20, color='#3498DB', edgecolor='white', alpha=0.85)
ax.axvline(t33_loo, color='orange', linestyle='--', linewidth=1.2, label=f'T33={t33_loo:.3f}')
ax.axvline(t67_loo, color='red',    linestyle='--', linewidth=1.2, label=f'T67={t67_loo:.3f}')
ax.set_title(f"humor_proportion_quarter_loo\n(n={len(loo_vals_plot)}, filtered)", fontsize=9)
ax.set_xlabel("LOO Proportion"); ax.set_ylabel("Count"); ax.legend(fontsize=8)

# 2. Frequency 히스토그램
ax = axes[0, 1]
freq_vals_plot = [v for v in freq_post if v is not None]
ax.hist(freq_vals_plot, bins=20, color='#E74C3C', edgecolor='white', alpha=0.85)
ax.axvline(t33_freq, color='orange', linestyle='--', linewidth=1.2, label=f'T33={t33_freq:.0f}')
ax.axvline(t67_freq, color='darkred', linestyle='--', linewidth=1.2, label=f'T67={t67_freq:.0f}')
ax.set_title(f"humor_frequency_quarter\n(n={len(freq_vals_plot)}, filtered)", fontsize=9)
ax.set_xlabel("Frequency"); ax.set_ylabel("Count"); ax.legend(fontsize=8)

# 3. Bin별 평균 engagement (LOO proportion 기준)
ax = axes[1, 0]
loo_bins_plot = {r['bin']: r for r in bin_loo if r['bin'] in ('low','medium','high')}
bin_labels = ['low', 'medium', 'high']
bin_means  = [float(loo_bins_plot[b]['mean_log1p_engagement_total']) if b in loo_bins_plot else 0 for b in bin_labels]
bin_ns     = [loo_bins_plot[b]['n_posts'] if b in loo_bins_plot else 0 for b in bin_labels]
colors_bin = ['#95A5A6','#3498DB','#E74C3C']
bars = ax.bar(range(3), bin_means, color=colors_bin, edgecolor='white', width=0.5)
ax.set_xticks(range(3))
ax.set_xticklabels([f"{b}\n(n={n})" for b, n in zip(bin_labels, bin_ns)], fontsize=9)
ax.set_ylabel("Mean log1p(engagement_total)")
ax.set_title("Bin별 평균 engagement\n(humor_proportion_quarter_loo 기준)", fontsize=9)
for bar, m in zip(bars, bin_means):
    ax.text(bar.get_x()+bar.get_width()/2, m+0.01, f"{m:.3f}", ha='center', va='bottom', fontsize=9)
ax.set_ylim(0, max(bin_means)*1.15 if any(bin_means) else 1)

# 4. Period scatter: proportion_loo vs mean engagement
ax = axes[1, 1]
ploo_vals  = [safe_float(str(r['mean_humor_proportion_loo'])) for r in period_rows]
peng_vals  = [float(r['mean_log1p_engagement_total']) for r in period_rows]
pt_sizes   = [r['total_posts']*2 for r in period_rows]
valid_mask = [v is not None for v in ploo_vals]
ax.scatter(
    [v for v, ok in zip(ploo_vals, valid_mask) if ok],
    [v for v, ok in zip(peng_vals, valid_mask) if ok],
    s=[s for s, ok in zip(pt_sizes, valid_mask) if ok],
    color='#2ECC71', alpha=0.7, edgecolors='white'
)
ax.set_xlabel("Mean LOO Proportion (period-level)")
ax.set_ylabel("Mean log1p(engagement) (period-level)")
ax.set_title(f"Period-level: LOO Proportion vs Engagement\n(n={sum(valid_mask)}분기)", fontsize=9)
for r, x, y, ok in zip(period_rows, ploo_vals, peng_vals, valid_mask):
    if ok:
        ax.annotate(r['period'], (x, y), fontsize=6, alpha=0.6, xytext=(2,2), textcoords='offset points')

plt.suptitle("Wendy's H3-pre Filtered Quarter Audit (quarter_total_posts ≥ 10)\nDescriptive Only — No Regression", fontsize=10, y=1.01)
plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PLOT_OUT}")

# ── 8. Diagnostics ────────────────────────────────────────────────────────────
print("[8] Diagnostics")
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON,'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

# H3-pre pattern 판정 (descriptive only)
def pattern_label(low_m, med_m, high_m):
    if med_m > low_m and med_m > high_m:
        return 'inverted_U (low<medium>high)'
    if low_m < med_m < high_m:
        return 'monotone_increasing'
    if low_m > med_m > high_m:
        return 'monotone_decreasing'
    return 'other'

loo_means = {r['bin']: float(r['mean_log1p_engagement_total']) for r in bin_loo if r['bin'] in ('low','medium','high')}
freq_means = {r['bin']: float(r['mean_log1p_engagement_total']) for r in bin_freq if r['bin'] in ('low','medium','high')}

loo_pattern  = pattern_label(loo_means.get('low',0), loo_means.get('medium',0), loo_means.get('high',0))
freq_pattern = pattern_label(freq_means.get('low',0), freq_means.get('medium',0), freq_means.get('high',0))
print(f"  LOO proportion pattern: {loo_pattern}")
print(f"  Frequency pattern:      {freq_pattern}")

diag = {
    'filter_criterion': f'quarter_total_posts>={FILTER_MIN_POSTS}',
    'total_rows_before_filter': len(all_posts),
    'excluded_posts': len(excluded_posts),
    'excluded_quarters': str(excluded_quarters),
    'filtered_posts': len(filtered_posts),
    'filtered_quarters': len(included_quarters),
    'filtered_humor_posts': pred_humor,
    'filtered_non_humor_posts': pred_non_humor,
    'loo_missing_in_filtered': loo_missing,
    # post-level stats
    'post_loo_proportion_min': loo_stats['min'],
    'post_loo_proportion_max': loo_stats['max'],
    'post_loo_proportion_mean': loo_stats['mean'],
    'post_loo_proportion_sd': loo_stats['sd'],
    'post_loo_proportion_p25': loo_stats['p25'],
    'post_loo_proportion_p75': loo_stats['p75'],
    'post_frequency_min': freq_stats['min'],
    'post_frequency_max': freq_stats['max'],
    'post_frequency_mean': freq_stats['mean'],
    'post_frequency_sd': freq_stats['sd'],
    # period-level stats
    'period_loo_proportion_min': ploo_stats['min'],
    'period_loo_proportion_max': ploo_stats['max'],
    'period_loo_proportion_mean': ploo_stats['mean'],
    'period_loo_proportion_sd': ploo_stats['sd'],
    'period_frequency_min': pfreq_stats['min'],
    'period_frequency_max': pfreq_stats['max'],
    'period_frequency_mean': pfreq_stats['mean'],
    'period_frequency_sd': pfreq_stats['sd'],
    # tertile info
    'loo_tertile_t33': round(t33_loo, 4),
    'loo_tertile_t67': round(t67_loo, 4),
    'freq_tertile_t33': round(t33_freq, 4),
    'freq_tertile_t67': round(t67_freq, 4),
    # bin pattern
    'descriptive_pattern_loo_proportion': loo_pattern,
    'descriptive_pattern_frequency': freq_pattern,
    'h3_regression_performed': False,
    'original_posts_json_modified': posts_json_modified,
}

with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric','value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 9. Validation ─────────────────────────────────────────────────────────────
print("[9] Validation")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in [DATASET_OUT,PERIOD_OUT,BIN_OUT,DIAG_OUT,PLOT_OUT,SUMMARY_OUT]),
    "경로 확인")
chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_excluded_sparse_quarters",
    set(excluded_quarters) == {'2009-Q4','2023-Q4','2025-Q3'},
    f"제외: {excluded_quarters}")
chk("04_filtered_posts_count",
    len(filtered_posts) == len(all_posts) - len(excluded_posts),
    f"filtered={len(filtered_posts)}")
chk("05_filtered_quarters_count",
    len(included_quarters) == 25,
    f"quarters={len(included_quarters)}")
chk("06_loo_missing_reasonable",
    loo_missing == 0,
    f"loo_missing={loo_missing}")
chk("07_humor_in_filtered_correct",
    pred_humor + pred_non_humor == len(filtered_posts),
    f"sum={pred_humor+pred_non_humor}")
chk("08_period_audit_generated",
    os.path.exists(PERIOD_OUT) and len(period_rows)==25,
    f"periods={len(period_rows)}")
chk("09_bin_descriptives_generated",
    os.path.exists(BIN_OUT) and len(all_bin_rows)>0,
    f"rows={len(all_bin_rows)}")
chk("10_loo_bins_low_medium_high_all_exist",
    all(b in {r['bin'] for r in bin_loo} for b in ('low','medium','high')),
    "low/medium/high 모두 존재")
chk("11_freq_bins_low_medium_high_all_exist",
    all(b in {r['bin'] for r in bin_freq} for b in ('low','medium','high')),
    "low/medium/high 모두 존재")
chk("12_no_h3_regression",
    True, "H3 회귀분석 미수행")
chk("13_pattern_recorded",
    diag['descriptive_pattern_loo_proportion'] != '',
    f"pattern={loo_pattern}")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  Validation: {n_pass}/13 PASS, {n_fail} FAIL")

if n_fail > 0:
    print("[ERROR] 검증 FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

# ── 10. Summary markdown ──────────────────────────────────────────────────────
print("[10] summary.md 작성")

# bin 표 생성 함수
def bin_table(bin_rows_list, primary_dv='log1p_engagement_total'):
    lines = [f"| bin | n_posts | n_periods | mean_predictor | mean_{primary_dv} | median_{primary_dv} |",
             "|---|---|---|---|---|---|"]
    for r in bin_rows_list:
        if r['bin'] in ('low','medium','high'):
            lines.append(f"| {r['bin']} | {r['n_posts']} | {r['n_periods']} | {r['mean_predictor']} | {r['mean_log1p_engagement_total']} | {r['median_log1p_engagement_total']} |")
    return '\n'.join(lines)

summary_md = f"""# Wendy's H3-pre Filtered Quarter Audit 결과

## 1. 작업 목적

본 작업은 H3 회귀분석을 수행하기 전에, sparse period를 제외한 filtered sample에서 humor usage 변수의 분포와 descriptive engagement pattern을 확인하는 사전 점검이다.

H3 회귀분석은 본 단계에서 수행하지 않는다.

---

## 2. 필터 기준

```
quarter_total_posts >= {FILTER_MIN_POSTS}
```

제외된 분기 (total_posts < 10):

| 분기 | 제외 이유 | n_posts |
|---|---|---|
| 2009-Q4 | total_posts=1 (이상치 period) | 1 |
| 2023-Q4 | total_posts=8 (sparse) | 8 |
| 2025-Q3 | total_posts=9 (sparse) | 9 |

---

## 3. 표본 구성 (필터 후)

| 항목 | 값 |
|---|---|
| 전체 posts (필터 전) | {len(all_posts)} |
| 제외 posts | {len(excluded_posts)} |
| **filtered posts** | **{len(filtered_posts)}** |
| **filtered 분기** | **{len(included_quarters)}개** |
| predicted humor (pred=1) | {pred_humor} ({pred_humor/len(filtered_posts)*100:.1f}%) |
| predicted non_humor (pred=0) | {pred_non_humor} ({pred_non_humor/len(filtered_posts)*100:.1f}%) |
| LOO proportion missing | {loo_missing} |

---

## 4. humor_proportion_quarter_loo 분포

### Post-level 기준 (n={loo_stats['n']})

| 항목 | 값 |
|---|---|
| min | {loo_stats['min']} |
| max | {loo_stats['max']} |
| mean | {loo_stats['mean']} |
| sd | {loo_stats['sd']} |
| median | {loo_stats['median']} |
| P25 | {loo_stats['p25']} |
| P75 | {loo_stats['p75']} |

Tertile 기준: T33={t33_loo:.4f}, T67={t67_loo:.4f}

### Period-level 기준 (n={len(period_rows)}분기)

| 항목 | 값 |
|---|---|
| min | {ploo_stats['min']} |
| max | {ploo_stats['max']} |
| mean | {ploo_stats['mean']} |
| sd | {ploo_stats['sd']} |

---

## 5. humor_frequency_quarter 분포

### Post-level 기준 (n={freq_stats['n']})

| 항목 | 값 |
|---|---|
| min | {freq_stats['min']} |
| max | {freq_stats['max']} |
| mean | {freq_stats['mean']} |
| sd | {freq_stats['sd']} |
| median | {freq_stats['median']} |

Tertile 기준: T33={t33_freq:.1f}, T67={t67_freq:.1f}

### Period-level 기준 (n={len(period_rows)}분기)

| 항목 | 값 |
|---|---|
| min | {pfreq_stats['min']} |
| max | {pfreq_stats['max']} |
| mean | {pfreq_stats['mean']} |
| sd | {pfreq_stats['sd']} |

---

## 6. Bin별 descriptive engagement pattern

H3-pre 기대 패턴: **low < medium > high** (역 U자형)
아래 결과는 descriptive audit 목적으로만 제시하며, 통계적 유의성을 해석하지 않는다.

### humor_proportion_quarter_loo 기준

{bin_table(bin_loo)}

패턴 판정 (descriptive only): **{loo_pattern}**

### humor_frequency_quarter 기준

{bin_table(bin_freq)}

패턴 판정 (descriptive only): **{freq_pattern}**

### humor_proportion_quarter 기준 (보조)

{bin_table(bin_prop)}

---

## 7. 포함된 분기 목록 (25개)

| 분기 | total_posts | humor_frequency | humor_proportion | mean_loo_proportion | mean_engagement |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['period']} | {r['total_posts']} | {r['humor_frequency']} | {r['humor_proportion']} | {r['mean_humor_proportion_loo']} | {r['mean_log1p_engagement_total']} |" for r in period_rows)}

---

## 8. H3 회귀분석 준비 상태

| 항목 | 상태 |
|---|---|
| H3 primary predictor | `humor_proportion_quarter_loo` |
| Filtered sample | {len(filtered_posts)}건, {len(included_quarters)}분기 |
| LOO missing in filtered sample | {loo_missing}건 |
| Descriptive pattern (LOO proportion) | {loo_pattern} |
| H3 회귀분석 수행 여부 | 미수행 |

---

## 9. 해석상 주의사항

- 본 결과는 descriptive audit이며, H3 가설 지지 여부를 판정하지 않는다.
- humor_proportion_quarter_loo는 모델 기반 pred_humor_final_050을 사용하여 계산한 값이며, 확정 사람 코딩 결과가 아니다.
- engagement 평균은 기술통계 목적으로만 제시되었으며, 인과관계나 통계적 유의성을 해석하지 않는다.
- 두 집계 기준(post-level vs period-level)의 평균값 차이는 집계 단위 차이에서 발생한 것이며, 변수 생성 오류가 아니다.
- 이후 H3 회귀분석에서는 quadratic term(humor_proportion_quarter_loo²)을 포함한 OLS를 수행할 수 있다.

---

## 10. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/intensity/proportion 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

print(f"\n[완료] Validation {n_pass}/13 PASS. 커밋 대상: analysis: audit wendys h3 pre filtered quarter")
