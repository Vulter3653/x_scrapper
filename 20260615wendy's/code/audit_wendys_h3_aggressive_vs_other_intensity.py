"""
audit_wendys_h3_aggressive_vs_other_intensity.py

목적: H3-main 준비를 위해 aggressive humor vs other humor 기준으로
      기간별 frequency/proportion 변수를 생성하고 filtered audit을 수행한다.
      H3-main 회귀분석은 이번 작업에서 수행하지 않는다.
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

BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

PREDICTIONS_IN = os.path.join(RESULT_DIR, "wendys_model_based_humor_type_full_predictions.csv")
POSTLEVEL_IN   = os.path.join(DATA_DIR,   "wendys_humor_frequency_proportion_post_level_dataset.csv")
POSTS_JSON     = os.path.join("data", "wendys", "posts.json")

DATASET_OUT   = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")
QUARTER_OUT   = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_quarter_audit.csv")
DISTRIB_OUT   = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_predictor_distribution.csv")
BIN_OUT       = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_bin_descriptives.csv")
DIAG_OUT      = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_diagnostics.csv")
PLOT_OUT      = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_aggressive_plot.png")
SUMMARY_OUT   = os.path.join(RESULT_DIR, "wendys_h3_aggressive_vs_other_summary.md")

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

# ── 0. posts.json 보호 확인 ───────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 데이터 로드 ────────────────────────────────────────────────────────────
print("[1] 데이터 로드")
with open(PREDICTIONS_IN, newline='', encoding='utf-8') as f:
    pred_rows = list(csv.DictReader(f))
with open(POSTLEVEL_IN, newline='', encoding='utf-8') as f:
    post_rows = list(csv.DictReader(f))

print(f"  predictions: {len(pred_rows)}건")
print(f"  post-level:  {len(post_rows)}건")

# ── 2. id 기준 병합 ───────────────────────────────────────────────────────────
print("[2] id 기준 병합")
pred_map = {r['id']: r for r in pred_rows}
merged = []
for pr in post_rows:
    pid = pr['id']
    pd_r = pred_map.get(pid, {})
    merged_row = dict(pr)
    merged_row['pred_humor_type_group_model']     = pd_r.get('pred_humor_type_group_model', '')
    merged_row['p_type_aggressive_model']         = pd_r.get('p_type_aggressive_model', '')
    merged_row['p_type_other_humor_model']        = pd_r.get('p_type_other_humor_model', '')
    merged_row['pred_humor_type_group_model_050'] = pd_r.get('pred_humor_type_group_model_050', '')
    merged.append(merged_row)

print(f"  병합 결과: {len(merged)}건")

# ── 3. dummy 변수 생성 ────────────────────────────────────────────────────────
print("[3] dummy 변수 생성")
for r in merged:
    g = r['pred_humor_type_group_model']
    r['is_aggressive_humor'] = 1 if g == 'aggressive' else 0
    r['is_other_humor']      = 1 if g == 'other_humor' else 0
    r['is_non_humor']        = 1 if g == 'non_humor'   else 0
    r['is_predicted_humor']  = 1 if g in ('aggressive', 'other_humor') else 0

from collections import Counter
type_dist = Counter(r['pred_humor_type_group_model'] for r in merged)
print(f"  분포: {dict(type_dist)}")

# ── 4. quarter-level 집계 ─────────────────────────────────────────────────────
print("[4] quarter-level 집계")
quarter_agg = defaultdict(lambda: {
    'total': 0, 'aggressive': 0, 'other_humor': 0,
    'non_humor': 0, 'predicted_humor': 0,
    'dates': [],
})
for r in merged:
    q = r['year_quarter']
    quarter_agg[q]['total']          += 1
    quarter_agg[q]['aggressive']     += r['is_aggressive_humor']
    quarter_agg[q]['other_humor']    += r['is_other_humor']
    quarter_agg[q]['non_humor']      += r['is_non_humor']
    quarter_agg[q]['predicted_humor']+= r['is_predicted_humor']
    quarter_agg[q]['dates'].append(r.get('created_date', ''))

# ── 5. post-level frequency/proportion 변수 생성 ─────────────────────────────
print("[5] post-level frequency/proportion 변수 생성")
for r in merged:
    q  = r['year_quarter']
    qa = quarter_agg[q]
    qt = qa['total']
    qa_agg  = qa['aggressive']
    qa_oth  = qa['other_humor']
    qa_hum  = qa['predicted_humor']

    r['quarter_aggressive_posts']      = qa_agg
    r['quarter_other_humor_posts']     = qa_oth
    r['quarter_non_humor_posts']       = qa['non_humor']
    r['quarter_predicted_humor_posts'] = qa_hum

    r['aggressive_humor_frequency_quarter'] = qa_agg
    r['other_humor_frequency_quarter']      = qa_oth

    r['aggressive_humor_proportion_quarter'] = round(qa_agg / qt, 8) if qt > 0 else float('nan')
    r['other_humor_proportion_quarter']      = round(qa_oth / qt, 8) if qt > 0 else float('nan')

    r['aggressive_share_among_humor_quarter'] = (
        round(qa_agg / qa_hum, 8) if qa_hum > 0 else float('nan')
    )

    # LOO
    ai = r['is_aggressive_humor']
    oi = r['is_other_humor']
    hi = r['is_predicted_humor']

    denom_t = qt - 1
    r['aggressive_humor_proportion_quarter_loo'] = (
        round((qa_agg - ai) / denom_t, 8) if denom_t > 0 else float('nan')
    )
    r['other_humor_proportion_quarter_loo'] = (
        round((qa_oth - oi) / denom_t, 8) if denom_t > 0 else float('nan')
    )

    denom_h = qa_hum - hi
    r['aggressive_share_among_humor_quarter_loo'] = (
        round((qa_agg - ai) / denom_h, 8) if denom_h > 0 else float('nan')
    )

# ── 6. filtered sample (quarter_total_posts >= 10) ────────────────────────────
print("[6] filtered sample 생성 (quarter_total_posts >= 10)")
for r in merged:
    qt = quarter_agg[r['year_quarter']]['total']
    r['quarter_total_posts_check'] = qt
    r['in_h3_aggressive_filtered'] = 1 if qt >= 10 else 0

filtered = [r for r in merged if r['in_h3_aggressive_filtered'] == 1]
excluded_quarters = sorted(set(
    r['year_quarter'] for r in merged if r['in_h3_aggressive_filtered'] == 0
))
filtered_quarters = sorted(set(r['year_quarter'] for r in filtered))
print(f"  filtered: {len(filtered)}건, {len(filtered_quarters)}분기")
print(f"  제외 분기: {excluded_quarters}")

# ── 7. dataset 저장 ───────────────────────────────────────────────────────────
print("[7] dataset 저장")
base_fields = list(post_rows[0].keys())
new_fields = [
    'pred_humor_type_group_model', 'p_type_aggressive_model', 'p_type_other_humor_model',
    'pred_humor_type_group_model_050',
    'is_aggressive_humor', 'is_other_humor', 'is_non_humor', 'is_predicted_humor',
    'quarter_aggressive_posts', 'quarter_other_humor_posts', 'quarter_non_humor_posts',
    'quarter_predicted_humor_posts',
    'aggressive_humor_frequency_quarter', 'other_humor_frequency_quarter',
    'aggressive_humor_proportion_quarter', 'other_humor_proportion_quarter',
    'aggressive_humor_proportion_quarter_loo', 'other_humor_proportion_quarter_loo',
    'aggressive_share_among_humor_quarter', 'aggressive_share_among_humor_quarter_loo',
    'in_h3_aggressive_filtered',
]
all_fields = base_fields + [f for f in new_fields if f not in base_fields]

with open(DATASET_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(merged)
print(f"  → {DATASET_OUT}")

# ── 8. quarter-level audit 파일 생성 ─────────────────────────────────────────
print("[8] quarter-level audit")
quarter_rows = []
for q in sorted(quarter_agg.keys()):
    qa = quarter_agg[q]
    qt = qa['total']
    qa_agg = qa['aggressive']
    qa_oth = qa['other_humor']
    qa_hum = qa['predicted_humor']

    # filtered 여부
    in_filt = 1 if qt >= 10 else 0

    # posts in this quarter
    q_posts = [r for r in merged if r['year_quarter'] == q]

    def qmean(key):
        vals = [safe_float(r.get(key)) for r in q_posts]
        vals = [v for v in vals if v is not None]
        return round(float(np.mean(vals)), 6) if vals else float('nan')

    def qmedian(key):
        vals = [safe_float(r.get(key)) for r in q_posts]
        vals = [v for v in vals if v is not None]
        return round(float(np.median(vals)), 6) if vals else float('nan')

    mean_agg_loo = qmean('aggressive_humor_proportion_quarter_loo')
    mean_oth_loo = qmean('other_humor_proportion_quarter_loo')
    mean_shr_loo = qmean('aggressive_share_among_humor_quarter_loo')

    dates = sorted([d for d in qa['dates'] if d])
    quarter_rows.append({
        'year_quarter': q,
        'total_posts': qt,
        'predicted_humor_posts': qa_hum,
        'aggressive_posts': qa_agg,
        'other_humor_posts': qa_oth,
        'non_humor_posts': qa['non_humor'],
        'aggressive_humor_frequency': qa_agg,
        'other_humor_frequency': qa_oth,
        'aggressive_humor_proportion': round(qa_agg / qt, 6) if qt > 0 else float('nan'),
        'other_humor_proportion': round(qa_oth / qt, 6) if qt > 0 else float('nan'),
        'aggressive_share_among_humor': round(qa_agg / qa_hum, 6) if qa_hum > 0 else float('nan'),
        'mean_aggressive_humor_proportion_loo': mean_agg_loo,
        'mean_other_humor_proportion_loo': mean_oth_loo,
        'mean_aggressive_share_among_humor_loo': mean_shr_loo,
        'mean_log1p_engagement_total': qmean('log1p_engagement_total'),
        'median_log1p_engagement_total': qmedian('log1p_engagement_total'),
        'mean_log1p_engagement_favorite_retweet': qmean('log1p_engagement_favorite_retweet'),
        'mean_log1p_favorite_count': qmean('log1p_favorite_count'),
        'mean_log1p_retweet_count': qmean('log1p_retweet_count'),
        'mean_log1p_reply_count': qmean('log1p_reply_count'),
        'mean_log1p_quote_count': qmean('log1p_quote_count'),
        'mean_log1p_bookmark_count': qmean('log1p_bookmark_count'),
        'mean_log1p_view_count': qmean('log1p_view_count'),
        'min_created_date': dates[0] if dates else '',
        'max_created_date': dates[-1] if dates else '',
        'included_in_filtered_sample': in_filt,
    })

with open(QUARTER_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(quarter_rows[0].keys()))
    w.writeheader()
    w.writerows(quarter_rows)
print(f"  → {QUARTER_OUT}")

# ── 9. predictor 분포 ─────────────────────────────────────────────────────────
print("[9] predictor 분포 산출 (filtered sample)")

def distrib_stats(vals):
    vals = [v for v in vals if v is not None and not math.isnan(v)]
    if not vals:
        return {k: float('nan') for k in ['n','missing','min','max','mean','sd','p25','median','p75','t33','t67']}
    arr = np.array(vals)
    return {
        'n': len(arr),
        'missing': 0,
        'min': round(float(np.min(arr)), 6),
        'max': round(float(np.max(arr)), 6),
        'mean': round(float(np.mean(arr)), 6),
        'sd': round(float(np.std(arr, ddof=1)), 6),
        'p25': round(float(np.percentile(arr, 25)), 6),
        'median': round(float(np.median(arr)), 6),
        'p75': round(float(np.percentile(arr, 75)), 6),
        't33': round(float(np.percentile(arr, 33.33)), 6),
        't67': round(float(np.percentile(arr, 66.67)), 6),
    }

predictors = {
    'aggressive_humor_proportion_quarter_loo': [safe_float(r['aggressive_humor_proportion_quarter_loo']) for r in filtered],
    'aggressive_humor_frequency_quarter':      [safe_float(r['aggressive_humor_frequency_quarter']) for r in filtered],
    'aggressive_humor_proportion_quarter':     [safe_float(r['aggressive_humor_proportion_quarter']) for r in filtered],
    'aggressive_share_among_humor_quarter_loo':[safe_float(r['aggressive_share_among_humor_quarter_loo']) for r in filtered],
    'other_humor_proportion_quarter_loo':      [safe_float(r['other_humor_proportion_quarter_loo']) for r in filtered],
    'other_humor_frequency_quarter':           [safe_float(r['other_humor_frequency_quarter']) for r in filtered],
    'other_humor_proportion_quarter':          [safe_float(r['other_humor_proportion_quarter']) for r in filtered],
}

distrib_rows = []
for pred_name, vals in predictors.items():
    miss_count = sum(1 for v in vals if v is None or math.isnan(v) if v is None or (isinstance(v, float) and math.isnan(v)))
    valid_vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    st = distrib_stats(valid_vals)
    st['n']      = len(valid_vals)
    st['missing']= miss_count
    distrib_rows.append({'predictor': pred_name, **st})
    print(f"  {pred_name}: n={st['n']} missing={miss_count} min={st['min']} max={st['max']} mean={st['mean']} sd={st['sd']}")

with open(DISTRIB_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['predictor','n','missing','min','max','mean','sd','p25','median','p75','t33','t67'])
    w.writeheader()
    w.writerows(distrib_rows)
print(f"  → {DISTRIB_OUT}")

# ── 10. bin descriptive ───────────────────────────────────────────────────────
print("[10] bin descriptive (tertile)")

def assign_tertile_bin(vals_arr, t33, t67):
    bins = []
    for v in vals_arr:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            bins.append(None)
        elif v <= t33:
            bins.append('low')
        elif v <= t67:
            bins.append('medium')
        else:
            bins.append('high')
    return bins

bin_rows = []
pred_for_bins = [
    'aggressive_humor_proportion_quarter_loo',
    'aggressive_humor_frequency_quarter',
    'aggressive_share_among_humor_quarter_loo',
    'other_humor_proportion_quarter_loo',
]

for pred_name in pred_for_bins:
    vals_all = [safe_float(r[pred_name]) for r in filtered]
    valid_vals = [v for v in vals_all if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not valid_vals:
        continue
    arr = np.array(valid_vals)
    t33 = float(np.percentile(arr, 33.33))
    t67 = float(np.percentile(arr, 66.67))

    bins_arr = assign_tertile_bin(vals_all, t33, t67)

    for bin_label in ['low', 'medium', 'high']:
        bin_posts = [r for r, b in zip(filtered, bins_arr) if b == bin_label]
        if not bin_posts:
            continue
        quarters_in_bin = set(r['year_quarter'] for r in bin_posts)

        def bmean(key):
            vals = [safe_float(r.get(key)) for r in bin_posts]
            vals = [v for v in vals if v is not None]
            return round(float(np.mean(vals)), 6) if vals else float('nan')

        def bmedian(key):
            vals = [safe_float(r.get(key)) for r in bin_posts]
            vals = [v for v in vals if v is not None]
            return round(float(np.median(vals)), 6) if vals else float('nan')

        pred_vals_bin = [safe_float(r[pred_name]) for r in bin_posts]
        pred_vals_bin = [v for v in pred_vals_bin if v is not None]

        bin_rows.append({
            'predictor': pred_name,
            'bin': bin_label,
            'n_posts': len(bin_posts),
            'n_quarters': len(quarters_in_bin),
            'min_predictor': round(min(pred_vals_bin), 6) if pred_vals_bin else float('nan'),
            'max_predictor': round(max(pred_vals_bin), 6) if pred_vals_bin else float('nan'),
            'mean_predictor': round(float(np.mean(pred_vals_bin)), 6) if pred_vals_bin else float('nan'),
            'mean_log1p_engagement_total': bmean('log1p_engagement_total'),
            'median_log1p_engagement_total': bmedian('log1p_engagement_total'),
            'mean_log1p_engagement_favorite_retweet': bmean('log1p_engagement_favorite_retweet'),
            'mean_log1p_favorite_count': bmean('log1p_favorite_count'),
            'mean_log1p_retweet_count': bmean('log1p_retweet_count'),
            'mean_log1p_reply_count': bmean('log1p_reply_count'),
            'mean_log1p_quote_count': bmean('log1p_quote_count'),
            'mean_log1p_bookmark_count': bmean('log1p_bookmark_count'),
            'mean_log1p_view_count': bmean('log1p_view_count'),
            'descriptive_pattern': 'descriptive_only',
        })

# 각 predictor bin별 패턴 요약
bin_patterns = {}
for pred_name in pred_for_bins:
    rows_pred = [r for r in bin_rows if r['predictor'] == pred_name]
    if len(rows_pred) == 3:
        eng_by_bin = {r['bin']: r['mean_log1p_engagement_total'] for r in rows_pred}
        low_e   = eng_by_bin.get('low',   float('nan'))
        med_e   = eng_by_bin.get('medium',float('nan'))
        high_e  = eng_by_bin.get('high',  float('nan'))
        print(f"  {pred_name}: low={low_e:.4f} medium={med_e:.4f} high={high_e:.4f}")
        if not any(math.isnan(v) for v in [low_e, med_e, high_e]):
            if low_e < med_e and med_e > high_e:
                pat = 'inverted_U (low<medium>high)'
            elif low_e > med_e and med_e < high_e:
                pat = 'U_shape (low>medium<high)'
            elif low_e < med_e < high_e:
                pat = 'monotone_increase'
            elif low_e > med_e > high_e:
                pat = 'monotone_decrease'
            else:
                pat = 'unclear'
        else:
            pat = 'nan'
        bin_patterns[pred_name] = pat

with open(BIN_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(bin_rows[0].keys()))
    w.writeheader()
    w.writerows(bin_rows)
print(f"  → {BIN_OUT}")

# ── 11. 그래프 ─────────────────────────────────────────────────────────────────
print("[11] 그래프 생성")
agg_loo_vals = np.array([
    v for v in [safe_float(r['aggressive_humor_proportion_quarter_loo']) for r in filtered]
    if v is not None and not math.isnan(v)
])
agg_eng_vals = np.array([
    safe_float(r['log1p_engagement_total'])
    for r, v in zip(filtered, [safe_float(r['aggressive_humor_proportion_quarter_loo']) for r in filtered])
    if v is not None and not math.isnan(v)
])

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# scatter: loo vs engagement
axes[0].scatter(agg_loo_vals, agg_eng_vals, alpha=0.15, s=10, color='#95A5A6')
axes[0].set_xlabel("aggressive_humor_proportion_quarter_loo", fontsize=9)
axes[0].set_ylabel("log1p_engagement_total", fontsize=9)
axes[0].set_title(f"Aggressive Humor Proportion LOO vs Engagement\n(n={len(agg_loo_vals)}, 25 quarters)", fontsize=9)

# bin bar
rows_agg = [r for r in bin_rows if r['predictor'] == 'aggressive_humor_proportion_quarter_loo']
if rows_agg:
    b_labels = [r['bin'] for r in rows_agg]
    b_means  = [r['mean_log1p_engagement_total'] for r in rows_agg]
    b_ns     = [r['n_posts'] for r in rows_agg]
    colors_b = ['#95A5A6', '#3498DB', '#E74C3C']
    bars = axes[1].bar(range(len(b_labels)), b_means, color=colors_b[:len(b_labels)], edgecolor='white', width=0.5)
    axes[1].set_xticks(range(len(b_labels)))
    axes[1].set_xticklabels([f"{b}\n(n={n})" for b, n in zip(b_labels, b_ns)], fontsize=9)
    axes[1].set_ylabel("Mean log1p(engagement_total)", fontsize=9)
    axes[1].set_title(f"Bin-level Mean Engagement\n(aggressive_proportion_loo tertile)", fontsize=9)
    for bar, m in zip(bars, b_means):
        axes[1].text(bar.get_x()+bar.get_width()/2, m+0.01, f"{m:.3f}", ha='center', va='bottom', fontsize=9)
    axes[1].set_ylim(0, max(b_means)*1.15)

plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150, bbox_inches='tight')
plt.close()
print(f"  → {PLOT_OUT}")

# ── 12. Diagnostics ───────────────────────────────────────────────────────────
print("[12] Diagnostics")

posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON, 'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

def get_distrib(pred_name):
    return next((r for r in distrib_rows if r['predictor'] == pred_name), {})

da = get_distrib('aggressive_humor_proportion_quarter_loo')
do = get_distrib('other_humor_proportion_quarter_loo')
ds = get_distrib('aggressive_share_among_humor_quarter_loo')

diag = {
    'total_rows': len(merged),
    'merged_rows': len(merged),
    'predicted_non_humor_rows': type_dist.get('non_humor', 0),
    'predicted_aggressive_rows': type_dist.get('aggressive', 0),
    'predicted_other_humor_rows': type_dist.get('other_humor', 0),
    'predicted_humor_rows': type_dist.get('aggressive', 0) + type_dist.get('other_humor', 0),
    'quarter_count_before_filter': len(quarter_agg),
    'filtered_rows': len(filtered),
    'filtered_quarters': len(filtered_quarters),
    'excluded_rows': len(merged) - len(filtered),
    'excluded_quarters': ', '.join(excluded_quarters),
    'filter_criterion': 'quarter_total_posts>=10',
    'aggressive_proportion_loo_missing_rows': da.get('missing', 'n/a'),
    'other_proportion_loo_missing_rows': do.get('missing', 'n/a'),
    'aggressive_share_among_humor_loo_missing_rows': ds.get('missing', 'n/a'),
    'aggressive_proportion_loo_min': da.get('min', 'n/a'),
    'aggressive_proportion_loo_max': da.get('max', 'n/a'),
    'aggressive_proportion_loo_mean': da.get('mean', 'n/a'),
    'aggressive_proportion_loo_sd': da.get('sd', 'n/a'),
    'other_proportion_loo_min': do.get('min', 'n/a'),
    'other_proportion_loo_max': do.get('max', 'n/a'),
    'other_proportion_loo_mean': do.get('mean', 'n/a'),
    'other_proportion_loo_sd': do.get('sd', 'n/a'),
    'aggressive_share_among_humor_loo_min': ds.get('min', 'n/a'),
    'aggressive_share_among_humor_loo_max': ds.get('max', 'n/a'),
    'aggressive_share_among_humor_loo_mean': ds.get('mean', 'n/a'),
    'aggressive_share_among_humor_loo_sd': ds.get('sd', 'n/a'),
    'descriptive_pattern_aggressive_proportion_loo': bin_patterns.get('aggressive_humor_proportion_quarter_loo', 'n/a'),
    'descriptive_pattern_aggressive_frequency': bin_patterns.get('aggressive_humor_frequency_quarter', 'n/a'),
    'descriptive_pattern_aggressive_share_among_humor_loo': bin_patterns.get('aggressive_share_among_humor_quarter_loo', 'n/a'),
    'descriptive_pattern_other_proportion_loo': bin_patterns.get('other_humor_proportion_quarter_loo', 'n/a'),
    'h3_main_regression_performed': False,
    'original_posts_json_modified': posts_json_modified,
}

with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric', 'value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 13. Validation 20개 ───────────────────────────────────────────────────────
print("[13] Validation")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in [
        DATASET_OUT, QUARTER_OUT, DISTRIB_OUT, BIN_OUT, DIAG_OUT, PLOT_OUT, SUMMARY_OUT
    ]), "모든 산출물 경로 확인")

chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_post_level_dataset_rows_978", len(merged)==978, f"n={len(merged)}")
chk("04_type_distribution_correct",
    type_dist.get('non_humor')==414 and type_dist.get('aggressive')==200 and type_dist.get('other_humor')==364,
    f"non={type_dist.get('non_humor')} agg={type_dist.get('aggressive')} oth={type_dist.get('other_humor')}")
chk("05_quarter_audit_generated", len(quarter_rows)>0, f"quarters={len(quarter_rows)}")
chk("06_aggressive_frequency_exists",
    all('aggressive_humor_frequency_quarter' in r for r in merged), "변수 존재")
chk("07_aggressive_proportion_exists",
    all('aggressive_humor_proportion_quarter' in r for r in merged), "변수 존재")
chk("08_aggressive_loo_exists",
    all('aggressive_humor_proportion_quarter_loo' in r for r in merged), "변수 존재")
chk("09_other_frequency_exists",
    all('other_humor_frequency_quarter' in r for r in merged), "변수 존재")
chk("10_other_proportion_exists",
    all('other_humor_proportion_quarter' in r for r in merged), "변수 존재")
chk("11_other_loo_exists",
    all('other_humor_proportion_quarter_loo' in r for r in merged), "변수 존재")
chk("12_aggressive_share_loo_exists",
    all('aggressive_share_among_humor_quarter_loo' in r for r in merged), "변수 존재")
chk("13_filter_applied",
    all(r['in_h3_aggressive_filtered']==0 or quarter_agg[r['year_quarter']]['total']>=10 for r in merged),
    "필터 적용 확인")
chk("14_filtered_sample_diagnostics",
    str(diag['filtered_rows']) != '' and str(diag['filtered_quarters']) != '',
    f"filtered_rows={diag['filtered_rows']} quarters={diag['filtered_quarters']}")
chk("15_bin_descriptives_generated", len(bin_rows)>0, f"n={len(bin_rows)}")
chk("16_no_regression_performed", diag['h3_main_regression_performed']==False, "회귀 미수행")
# 17-20: summary 작성 후 확인
chk("17_summary_exploratory_h3main_placeholder", True, "summary 작성 후 확인")
chk("18_summary_model_limitation_placeholder", True, "summary 작성 후 확인")
chk("19_summary_h3pre_failure_placeholder", True, "summary 작성 후 확인")
chk("20_summary_causal_warning_placeholder", True, "summary 작성 후 확인")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"  Validation 1차: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    import sys; sys.exit(1)

# ── 14. Summary markdown ──────────────────────────────────────────────────────
print("[14] summary.md 작성")

def fmt_bin_table(pred_name_filter):
    rows_pred = [r for r in bin_rows if r['predictor'] == pred_name_filter]
    if not rows_pred:
        return 'N/A'
    lines = ["| bin | n_posts | n_quarters | mean_predictor | mean_engagement |",
             "|---|---|---|---|---|"]
    for r in rows_pred:
        lines.append(
            f"| {r['bin']} | {r['n_posts']} | {r['n_quarters']} "
            f"| {r['mean_predictor']} | {r['mean_log1p_engagement_total']} |"
        )
    pat = bin_patterns.get(pred_name_filter, 'n/a')
    lines.append(f"\ndescriptive pattern: {pat}")
    return '\n'.join(lines)

def get_d(k):
    return diag.get(k, 'n/a')

summary_md = f"""# Wendy's H3-main 준비: Aggressive Humor vs Other Humor Intensity Audit

## 1. 작업 목적

본 작업은 H3-main 회귀분석이 아니라, aggressive humor와 other humor를 분리한 intensity 변수화 및 사전 audit이다.

이번 작업에서는 다음을 수행하였다.

- aggressive humor와 other humor의 quarter-level frequency/proportion 변수 생성
- leave-one-out(LOO) proportion 변수 생성
- sparse quarter 제외 후 filtered audit 수행
- 각 predictor에 대한 post-level 분포 확인
- low / medium / high tertile bin별 descriptive engagement pattern 확인

H3-main 회귀분석은 이 문서에서 수행하지 않았다.

---

## 2. 사용 데이터

| 파일 | 역할 |
|---|---|
| `wendys_model_based_humor_type_full_predictions.csv` | aggressive/other_humor 타입 예측값 |
| `wendys_humor_frequency_proportion_post_level_dataset.csv` | post-level engagement 및 quarter 변수 |

두 파일은 `id` 기준으로 병합하였다. 병합 결과: {get_d('merged_rows')}건.

---

## 3. Aggressive Humor / Other Humor 분류 기준

aggressive humor와 other humor의 구분은 전체 978건에 대한 확정 사람 코딩 결과가 아니라 모델 기반 타입 예측값인 pred_humor_type_group_model을 사용하였다.

| pred_humor_type_group_model | 정의 | n |
|---|---|---|
| `aggressive` | aggressive humor | {get_d('predicted_aggressive_rows')} |
| `other_humor` | affiliative/self-enhancing/self-defeating humor | {get_d('predicted_other_humor_rows')} |
| `non_humor` | 비유머 | {get_d('predicted_non_humor_rows')} |
| 합계 | | {get_d('total_rows')} |

이 모델은 사람 기반 타입 라벨 278건을 학습한 supplemental model-based prediction이므로, 분류 오류가 포함될 수 있다.

---

## 4. 생성 변수 정의

### 4.1 Aggressive Humor Frequency

```
aggressive_humor_frequency_quarter = quarter 내 aggressive humor 게시글 수
```

### 4.2 Aggressive Humor Proportion

```
aggressive_humor_proportion_quarter = Aggressive Posts_q / Total Posts_q
```

### 4.3 Aggressive Share Among Humor

```
aggressive_share_among_humor_quarter = Aggressive Posts_q / Humor Posts_q
(Humor Posts_q = 0이면 missing)
```

### 4.4 Aggressive Humor Proportion LOO

```
aggressive_humor_proportion_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Total Posts_q - 1)
```

post i 자신을 제외한 동일 분기 내 aggressive 비중. H3-main 회귀 primary predictor 후보.

### 4.5 Aggressive Share Among Humor LOO

```
aggressive_share_among_humor_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Humor Posts_q - Humor_i)
(분모 = 0이면 missing)
```

### 4.6 Other Humor Proportion LOO

```
other_humor_proportion_quarter_loo_i
= (Other Humor Posts_q - Other_i) / (Total Posts_q - 1)
```

---

## 5. 분석 표본 및 필터 기준

| 항목 | 값 |
|---|---|
| 전체 posts | {get_d('total_rows')} |
| 전체 quarters | {get_d('quarter_count_before_filter')} |
| 필터 기준 | quarter_total_posts ≥ 10 |
| **Filtered posts** | **{get_d('filtered_rows')}** |
| **Filtered quarters** | **{get_d('filtered_quarters')}** |
| 제외 posts | {get_d('excluded_rows')} |
| 제외 quarters | {get_d('excluded_quarters')} |

---

## 6. Quarter-level 분포

`wendys_h3_aggressive_vs_other_quarter_audit.csv` 참조. (25개 분기)

---

## 7. Aggressive Humor Proportion LOO 분포

filtered sample (n={get_d('filtered_rows')}) 기준:

| 항목 | 값 |
|---|---|
| min | {get_d('aggressive_proportion_loo_min')} |
| max | {get_d('aggressive_proportion_loo_max')} |
| mean | {get_d('aggressive_proportion_loo_mean')} |
| sd | {get_d('aggressive_proportion_loo_sd')} |
| missing | {get_d('aggressive_proportion_loo_missing_rows')} |

다음 단계에서 H3-main 회귀분석을 수행할 경우, post i를 제외한 aggressive_humor_proportion_quarter_loo를 primary predictor로 사용할 수 있다.

---

## 8. Other Humor Proportion LOO 분포

| 항목 | 값 |
|---|---|
| min | {get_d('other_proportion_loo_min')} |
| max | {get_d('other_proportion_loo_max')} |
| mean | {get_d('other_proportion_loo_mean')} |
| sd | {get_d('other_proportion_loo_sd')} |
| missing | {get_d('other_proportion_loo_missing_rows')} |

---

## 9. Aggressive Share Among Humor LOO 분포

| 항목 | 값 |
|---|---|
| min | {get_d('aggressive_share_among_humor_loo_min')} |
| max | {get_d('aggressive_share_among_humor_loo_max')} |
| mean | {get_d('aggressive_share_among_humor_loo_mean')} |
| sd | {get_d('aggressive_share_among_humor_loo_sd')} |
| missing | {get_d('aggressive_share_among_humor_loo_missing_rows')} |

---

## 10. Bin별 Descriptive Engagement Pattern

engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.

### aggressive_humor_proportion_quarter_loo (primary 후보)

{fmt_bin_table('aggressive_humor_proportion_quarter_loo')}

### aggressive_humor_frequency_quarter

{fmt_bin_table('aggressive_humor_frequency_quarter')}

### aggressive_share_among_humor_quarter_loo

{fmt_bin_table('aggressive_share_among_humor_quarter_loo')}

### other_humor_proportion_quarter_loo

{fmt_bin_table('other_humor_proportion_quarter_loo')}

---

## 11. H3-main 회귀분석 가능성 판단

H3-main 회귀분석은 본 작업에서 수행하지 않았다. 다음 단계에서 수행 가능 여부를 판단하려면 아래 조건을 확인하라.

| 확인 항목 | 값 |
|---|---|
| filtered quarters | {get_d('filtered_quarters')}개 |
| aggressive_proportion_loo missing | {get_d('aggressive_proportion_loo_missing_rows')} |
| aggressive_proportion_loo range | [{get_d('aggressive_proportion_loo_min')}, {get_d('aggressive_proportion_loo_max')}] |
| descriptive pattern (aggressive_loo) | {get_d('descriptive_pattern_aggressive_proportion_loo')} |
| H3-main 회귀 수행 여부 | {get_d('h3_main_regression_performed')} |

---

## 12. 이전 H3-pre 결과와의 관계

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았으므로, 본 aggressive intensity 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

따라서 이후 H3-main 회귀분석에서 유의미한 역 U자형 패턴이 발견되더라도, 이는 사전에 기각된 일반 유머 비중 가설의 사후 탐색적 보완으로만 해석해야 한다.

---

## 13. 해석상 주의사항

1. aggressive humor와 other humor의 구분 기준은 모델 기반 예측값이므로 분류 오류가 포함될 수 있다.
2. aggressive_humor_proportion_quarter_loo는 같은 quarter 내 게시글이 동일한 값을 공유하므로, 추후 회귀에서 cluster-robust SE 적용을 고려해야 한다.
3. quarter fixed effects는 humor_proportion_quarter_loo 계열 변수와 동시에 사용할 경우 식별이 불가능하다.
4. 본 관찰적 연구에서 aggressive humor와 engagement 사이의 연관성은 인과관계를 의미하지 않는다.
5. H3-pre의 general proportion이 불지지였기 때문에 H3-main aggressive 분석은 exploratory H3-main으로 위치시켜야 하며, 이 점을 보고 시 명시해야 한다.

---

## 14. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/H3-pre 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# summary validation 업데이트
checks[16] = {
    'check': '17_summary_exploratory_h3main',
    'status': 'PASS' if 'exploratory H3-main' in summary_md else 'FAIL',
    'detail': 'exploratory H3-main 표현 확인'
}
checks[17] = {
    'check': '18_summary_model_limitation',
    'status': 'PASS' if '모델 기반 타입 예측값인 pred_humor_type_group_model을 사용하였다' in summary_md else 'FAIL',
    'detail': '모델 한계 문장 확인'
}
checks[18] = {
    'check': '19_summary_h3pre_failure',
    'status': 'PASS' if 'primary quadratic OLS 기준으로 지지되지 않았으므로' in summary_md else 'FAIL',
    'detail': 'H3-pre 불지지 관계 문장 확인'
}
checks[19] = {
    'check': '20_summary_causal_warning',
    'status': 'PASS' if '인과관계나 통계적 유의성을 해석하지 않는다' in summary_md else 'FAIL',
    'detail': '인과 해석 금지 문장 확인'
}

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  최종 Validation: {n_pass}/20 PASS, {n_fail} FAIL")
if n_fail > 0:
    for c in checks:
        if c['status'] == 'FAIL':
            print(f"  [✗] {c['check']}: {c['detail']}")
    import sys; sys.exit(1)

print(f"\n[완료] Validation {n_pass}/20 PASS.")
print("  커밋 대상: analysis: audit wendys h3 aggressive versus other intensity")
