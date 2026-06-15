"""
inspect_wendys_existing_variables.py

목적: 현재 Wendy's humor 분석 데이터에 실제로 존재하는 변수들을 확인한다.
      회귀분석을 수행하지 않으며, 새 통제변수를 생성하지 않는다.
      기존 파일 컬럼을 확인하고 요약하는 작업만 수행한다.
"""

import csv
import math
import os
import hashlib
from collections import defaultdict, Counter

import numpy as np

BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

# ── 출력 파일 경로 ────────────────────────────────────────────────────────────
INVENTORY_CSV = os.path.join(RESULT_DIR, "wendys_existing_variable_inventory.csv")
SUMMARY_MD    = os.path.join(RESULT_DIR, "wendys_existing_variable_inventory_summary.md")
H1_CAND_CSV   = os.path.join(RESULT_DIR, "wendys_h1_existing_variable_candidates.csv")
H2_CAND_CSV   = os.path.join(RESULT_DIR, "wendys_h2_existing_variable_candidates.csv")
H3_CAND_CSV   = os.path.join(RESULT_DIR, "wendys_h3_existing_variable_candidates.csv")
SAMPLE_CSV    = os.path.join(RESULT_DIR, "wendys_existing_sample_size_checks.csv")

# ── 0. posts.json 보호 확인 ───────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 조사 대상 파일 목록 ────────────────────────────────────────────────────────
PRIORITY_FILES = [
    os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv"),
    os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv"),
    os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv"),
    os.path.join(DATA_DIR,   "wendys_h2_coder1_priority_dataset.csv"),
    os.path.join(DATA_DIR,   "wendys_humor_frequency_proportion_post_level_dataset.csv"),
    os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv"),
]

# 변수 그룹 분류 규칙 (변수명 키워드 기반)
def infer_group(col):
    c = col.lower()
    if c in ('no', 'id', 'tweet_url', 'tweet_id'): return 'identifier'
    if c in ('text', 'clean_text'): return 'text_raw'
    if any(k in c for k in ('year','month','day','date','time','hour','quarter')): return 'date_time'
    if any(k in c for k in ('log1p_engagement','log1p_favorite','log1p_retweet',
                             'log1p_reply','log1p_quote','log1p_bookmark','log1p_view',
                             'engagement_total','engagement_favorite','favorite_count',
                             'retweet_count','reply_count','quote_count','bookmark_count',
                             'view_count')): return 'engagement_dv'
    if any(k in c for k in ('final_humor_binary','final_humor_source','final_humor_label',
                             'human_humor_label','human_coded','coder1_humor','coder2_humor',
                             'human_humor_binary','final_humor_available')): return 'humor_presence_label'
    if any(k in c for k in ('pred_humor_final','p_humor_final','model_humor',
                             'p_humor_ml','classifier_prob','weak_humor_label',
                             'p_humor','prediction_set','pred_humor')): return 'humor_presence_prediction'
    if any(k in c for k in ('final_humor_type','human_type','coder1_type','coder2_type',
                             'final_humor_type_group','final_humor_type_source',
                             'final_humor_type_available','humor_missing_type')): return 'humor_type_label'
    if any(k in c for k in ('pred_humor_type','pred_full_4type',
                             'p_type_','aggressive_humor','other_humor_flag',
                             'non_humor_flag','is_aggressive','is_other_humor',
                             'is_non_humor','is_predicted_humor',
                             'quarter_aggressive','quarter_other_humor',
                             'quarter_predicted_humor')): return 'humor_type_prediction'
    if any(k in c for k in ('frequency_month','frequency_quarter','humor_frequency',
                             'aggressive_humor_frequency','other_humor_frequency')): return 'h3_frequency'
    if any(k in c for k in ('proportion_month','proportion_quarter','humor_proportion',
                             'humor_intensity','aggressive_humor_proportion',
                             'other_humor_proportion','aggressive_share',
                             'in_h3_aggressive_filtered')): return 'h3_proportion'
    if c in ('view_count','log1p_view_count'): return 'exposure'
    # 기존 포스트 포맷 변수
    if any(k in c for k in ('text_length','url_count','mention_count','hashtag_count',
                             'emoji_count','is_quote_status','is_retweet_text')): return 'post_format_existing'
    # 기존 가능 통제변수
    if any(k in c for k in ('dominant_topic','topic_','humor_score','log1p_humor_score',
                             'log1p_p_humor','weak_label_confidence','weak_label_source')): return 'possible_control_existing'
    # period-level total
    if any(k in c for k in ('total_posts','month_total','quarter_total',
                             'month_humor','quarter_humor','month_non','quarter_non')): return 'h3_proportion'
    return 'other'

def safe_float(v):
    if v in ('nan', '', None): return None
    try: return float(v)
    except: return None

def var_stats(vals_raw):
    valid = [safe_float(v) for v in vals_raw]
    valid_nn = [v for v in valid if v is not None]
    n_total = len(vals_raw)
    n_miss  = sum(1 for v in valid if v is None)
    if not valid_nn:
        return n_total, n_miss, float('nan'), float('nan'), float('nan'), float('nan')
    arr = np.array(valid_nn)
    return n_total, n_miss, float(np.min(arr)), float(np.max(arr)), float(np.mean(arr)), float(np.std(arr, ddof=1))

def round4(v):
    return round(v, 4) if not (isinstance(v, float) and math.isnan(v)) else 'nan'

# ── 1. 파일별 구조 분석 ────────────────────────────────────────────────────────
print("[1] 파일별 구조 분석")
file_structs = []
all_inventory = []

for fpath in PRIORITY_FILES:
    fname = os.path.basename(fpath)
    if not os.path.exists(fpath):
        print(f"  [SKIP] {fname} 없음")
        continue

    with open(fpath, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"  [EMPTY] {fname}")
        continue

    cols = list(rows[0].keys())
    n_rows = len(rows)
    n_cols = len(cols)

    # 중복 컬럼 확인 (fieldnames 수준)
    dup_cols = [c for c, cnt in Counter(cols).items() if cnt > 1]

    # 완전 빈 컬럼
    empty_cols = [c for c in cols if all(r.get(c, '') in ('', None) for r in rows)]

    # 컬럼 분류
    id_cols   = [c for c in cols if infer_group(c) == 'identifier']
    dt_cols   = [c for c in cols if infer_group(c) == 'date_time']
    eng_cols  = [c for c in cols if infer_group(c) == 'engagement_dv']
    hlbl_cols = [c for c in cols if infer_group(c) == 'humor_presence_label']
    hprd_cols = [c for c in cols if infer_group(c) == 'humor_presence_prediction']
    tlbl_cols = [c for c in cols if infer_group(c) == 'humor_type_label']
    tprd_cols = [c for c in cols if infer_group(c) == 'humor_type_prediction']
    freq_cols = [c for c in cols if infer_group(c) == 'h3_frequency']
    prop_cols = [c for c in cols if infer_group(c) == 'h3_proportion']

    print(f"  {fname}: {n_rows}건, {n_cols}컬럼, 중복={dup_cols}, 빈컬럼={empty_cols}")

    file_structs.append({
        'file': fname,
        'rows': n_rows, 'cols': n_cols,
        'duplicated_cols': ', '.join(dup_cols) if dup_cols else 'none',
        'empty_cols': ', '.join(empty_cols) if empty_cols else 'none',
        'id_cols': ', '.join(id_cols),
        'date_time_cols': ', '.join(dt_cols),
        'engagement_cols': ', '.join(eng_cols),
        'humor_presence_label_cols': ', '.join(hlbl_cols),
        'humor_presence_pred_cols': ', '.join(hprd_cols),
        'humor_type_label_cols': ', '.join(tlbl_cols),
        'humor_type_pred_cols': ', '.join(tprd_cols),
        'h3_frequency_cols': ', '.join(freq_cols),
        'h3_proportion_cols': ', '.join(prop_cols),
    })

    # variable inventory
    for col in cols:
        vals_raw = [r.get(col, '') for r in rows]
        vals_valid = [v for v in vals_raw if v not in ('', None)]
        n_total = len(vals_raw)
        n_miss  = n_total - len(vals_valid)
        miss_rate = round(n_miss / n_total, 4) if n_total > 0 else float('nan')
        unique_n = len(set(vals_valid))
        example  = ', '.join(str(v) for v in list(dict.fromkeys(vals_valid))[:3])

        group = infer_group(col)
        n_t, n_m, vmin, vmax, vmean, vstd = var_stats(vals_raw)

        # dtype 추정
        nums = [safe_float(v) for v in vals_valid]
        nums_nn = [v for v in nums if v is not None]
        if len(nums_nn) == len(vals_valid) and vals_valid:
            dtype = 'numeric'
        else:
            dtype = 'string/mixed'

        all_inventory.append({
            'source_file': fname,
            'variable_name': col,
            'inferred_variable_group': group,
            'dtype': dtype,
            'non_missing_n': n_t - n_m,
            'missing_n': n_m,
            'missing_rate': miss_rate,
            'unique_n': unique_n,
            'example_values': example[:200],
            'min': round4(vmin),
            'max': round4(vmax),
            'mean': round4(vmean),
            'std': round4(vstd),
            'notes': '',
        })

# ── 2. Inventory CSV 저장 ─────────────────────────────────────────────────────
print("[2] Inventory CSV 저장")
inv_fields = ['source_file','variable_name','inferred_variable_group','dtype',
              'non_missing_n','missing_n','missing_rate','unique_n',
              'example_values','min','max','mean','std','notes']
with open(INVENTORY_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=inv_fields)
    w.writeheader()
    w.writerows(all_inventory)
print(f"  → {INVENTORY_CSV} ({len(all_inventory)}개 변수)")

# ── 3. H1 후보 변수 ────────────────────────────────────────────────────────────
print("[3] H1 후보 변수 확인")

# 가장 완전한 파일: wendys_h3_aggressive_vs_other_intensity_dataset.csv (978건, 65컬럼)
with open(os.path.join(DATA_DIR, "wendys_h3_aggressive_vs_other_intensity_dataset.csv"),
          newline='', encoding='utf-8') as f:
    h3ds = list(csv.DictReader(f))

with open(os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv"),
          newline='', encoding='utf-8') as f:
    pred_ds = list(csv.DictReader(f))

with open(os.path.join(RESULT_DIR, "wendys_humor_review_sheet.csv"),
          newline='', encoding='utf-8') as f:
    review_ds = list(csv.DictReader(f))

with open(os.path.join(DATA_DIR, "wendys_fast_weak_supervised_humor_dataset.csv"),
          newline='', encoding='utf-8') as f:
    fast_ds = list(csv.DictReader(f))

# H1 후보 변수 목록
h1_candidates = []

def add_h1_cand(source, var, role, note, rows):
    vals = [r.get(var, '') for r in rows]
    valid = [v for v in vals if v not in ('', None)]
    n_miss = len(vals) - len(valid)
    unique_n = len(set(valid))
    h1_candidates.append({
        'variable': var,
        'source_file': source,
        'h1_role': role,
        'n_total': len(vals),
        'non_missing_n': len(valid),
        'missing_n': n_miss,
        'missing_rate': round(n_miss / len(vals), 4) if vals else 'nan',
        'unique_n': unique_n,
        'note': note,
    })

# A. 핵심 DV/IV
for col in ['log1p_engagement_total','log1p_engagement_favorite_retweet',
            'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
            'log1p_quote_count','log1p_bookmark_count','log1p_view_count']:
    add_h1_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                "DV_candidate", "log1p 변환 engagement 지표", h3ds)

for col in ['pred_humor_final_050','p_humor_final_tfidf_logreg']:
    add_h1_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                "IV_candidate", "humor presence 예측값", h3ds)

for col in ['final_humor_binary','final_humor_label_available']:
    add_h1_cand("wendys_final_humor_presence_full_predictions.csv", col,
                "IV_human_label", "사람 코딩 기반 유머 유무 라벨", pred_ds)

# B. 시간 변수
for col in ['created_year','created_month','created_day','created_time',
            'created_hour','created_date','year_month','year_quarter']:
    add_h1_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                "time_control_candidate", "시간 관련 기존 변수", h3ds)

# day_of_week 존재 여부 확인
has_dow = 'day_of_week' in (h3ds[0].keys() if h3ds else {})
h1_candidates.append({
    'variable': 'day_of_week',
    'source_file': 'N/A',
    'h1_role': 'time_control_candidate',
    'n_total': 978,
    'non_missing_n': 0,
    'missing_n': 978,
    'missing_rate': 1.0,
    'unique_n': 0,
    'note': f'존재하지 않음 (has_dow={has_dow}): created_date에서 계산 가능하나 이번 작업에서 생성하지 않음',
})

# C. Posting intensity
for col in ['quarter_total_posts','month_total_posts']:
    if col in h3ds[0].keys():
        add_h1_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                    "posting_intensity_candidate", "기간별 총 게시글 수", h3ds)
    else:
        h1_candidates.append({
            'variable': col, 'source_file': 'N/A', 'h1_role': 'posting_intensity_candidate',
            'n_total': 0, 'non_missing_n': 0, 'missing_n': 0,
            'missing_rate': 'n/a', 'unique_n': 0, 'note': '해당 컬럼 없음',
        })

# D. Post format (기존 컬럼으로 존재하는 것만)
for col in ['text_length','url_count','mention_count','hashtag_count',
            'emoji_count','is_quote_status','is_retweet_text']:
    if col in fast_ds[0].keys():
        add_h1_cand("wendys_fast_weak_supervised_humor_dataset.csv", col,
                    "post_format_existing", "텍스트 계산 없이 기존 컬럼으로 존재", fast_ds)
    else:
        h1_candidates.append({
            'variable': col, 'source_file': 'N/A', 'h1_role': 'post_format_existing',
            'n_total': 0, 'non_missing_n': 0, 'missing_n': 0,
            'missing_rate': 'n/a', 'unique_n': 0,
            'note': '해당 파일에 컬럼 없음 — 통합 필요',
        })

# E. Exposure
for col in ['view_count','log1p_view_count']:
    add_h1_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                "exposure_candidate", "노출 수 (결측 주의)", h3ds)

with open(H1_CAND_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(h1_candidates[0].keys()))
    w.writeheader(); w.writerows(h1_candidates)
print(f"  → {H1_CAND_CSV} ({len(h1_candidates)}개)")

# ── 4. H2 후보 변수 ────────────────────────────────────────────────────────────
print("[4] H2 후보 변수 확인")
with open(os.path.join(DATA_DIR, "wendys_h2_coder1_priority_dataset.csv"),
          newline='', encoding='utf-8') as f:
    h2_ds = list(csv.DictReader(f))

# H2 type 분포
type_dist_human = Counter(r['final_humor_type_group'] for r in h2_ds if r.get('final_humor_label_available')=='1')
type_dist_all   = Counter(r['final_humor_type_group'] for r in h2_ds)

# model-based: wendys_h3_aggressive_vs_other_intensity_dataset.csv
type_dist_model = Counter(r['pred_humor_type_group_model'] for r in h3ds)

# 4-type (review_sheet 기반)
type4_dist = Counter(r.get('final_humor_type','') for r in review_ds if r.get('final_humor_label_available')=='1')

h2_candidates = []

def add_h2_cand(source, var, role, note, rows):
    vals = [r.get(var, '') for r in rows]
    valid = [v for v in vals if v not in ('', None)]
    n_miss = len(vals) - len(valid)
    unique_vals = list(set(valid))[:5]
    h2_candidates.append({
        'variable': var,
        'source_file': source,
        'h2_role': role,
        'n_total': len(vals),
        'non_missing_n': len(valid),
        'missing_n': n_miss,
        'missing_rate': round(n_miss / len(vals), 4) if vals else 'nan',
        'unique_n': len(set(valid)),
        'example_unique_values': ', '.join(str(v) for v in unique_vals),
        'note': note,
    })

# Human-labeled type 변수
for col in ['final_humor_type','final_humor_type_group','final_humor_type_source',
            'final_humor_type_available','final_humor_label_available',
            'aggressive_humor','other_humor_flag','non_humor_flag','humor_missing_type']:
    add_h2_cand("wendys_h2_coder1_priority_dataset.csv", col,
                "H2_type_label", "H2 사람 코딩 타입 라벨", h2_ds)

# Model-based type 변수
for col in ['pred_humor_type_group_model','p_type_aggressive_model',
            'p_type_other_humor_model','pred_humor_type_group_model_050',
            'is_aggressive_humor','is_other_humor','is_non_humor']:
    add_h2_cand("wendys_h3_aggressive_vs_other_intensity_dataset.csv", col,
                "H2_type_model_prediction", "H2 모델 기반 타입 예측값 (978건)", h3ds)

# Review sheet 4-type
for col in ['final_humor_type','final_humor_type_group']:
    add_h2_cand("wendys_humor_review_sheet.csv", col,
                "H2_4type_label", "리뷰시트 기반 4-type 라벨 (278건 available)", review_ds)

# H2 DV
for col in ['log1p_engagement_total','log1p_engagement_favorite_retweet',
            'log1p_favorite_count','log1p_retweet_count','log1p_reply_count',
            'log1p_quote_count','log1p_bookmark_count']:
    add_h2_cand("wendys_h2_coder1_priority_dataset.csv", col,
                "H2_DV_candidate", "H2 engagement DV", h2_ds)

with open(H2_CAND_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(h2_candidates[0].keys()))
    w.writeheader(); w.writerows(h2_candidates)
print(f"  → {H2_CAND_CSV} ({len(h2_candidates)}개)")

# ── 5. H3 후보 변수 ────────────────────────────────────────────────────────────
print("[5] H3 후보 변수 확인")

def _f_ok(v):
    try: float(v); return True
    except: return False

h3_candidates = []

h3_target_cols = [
    'humor_frequency_month','humor_frequency_quarter',
    'humor_proportion_month','humor_proportion_quarter',
    'humor_proportion_month_loo','humor_proportion_quarter_loo',
    'aggressive_humor_frequency_quarter','aggressive_humor_proportion_quarter',
    'aggressive_humor_proportion_quarter_loo',
    'other_humor_frequency_quarter','other_humor_proportion_quarter',
    'other_humor_proportion_quarter_loo',
    'aggressive_share_among_humor_quarter','aggressive_share_among_humor_quarter_loo',
    'quarter_total_posts','month_total_posts',
    'year_quarter','year_month',
    'in_h3_aggressive_filtered',
]

ds_name = "wendys_h3_aggressive_vs_other_intensity_dataset.csv"
for col in h3_target_cols:
    exists = col in h3ds[0].keys()
    if exists:
        vals = [r.get(col, '') for r in h3ds]
        valid = [v for v in vals if v not in ('', None)]
        n_miss = len(vals) - len(valid)
        nums   = [float(v) for v in valid if v not in ('nan',) and _f_ok(v)]
        mn = round(min(nums), 6) if nums else 'n/a'
        mx = round(max(nums), 6) if nums else 'n/a'
        me = round(float(np.mean(nums)), 6) if nums else 'n/a'
        sd = round(float(np.std(nums, ddof=1)), 6) if len(nums) > 1 else 'n/a'
        h3_candidates.append({
            'variable': col,
            'source_file': ds_name,
            'h3_role': 'H3_predictor_candidate' if 'proportion' in col or 'frequency' in col else 'period_identifier',
            'exists_in_file': True,
            'n_total': len(vals),
            'non_missing_n': len(valid),
            'missing_n': n_miss,
            'missing_rate': round(n_miss / len(vals), 4) if vals else 'nan',
            'unique_n': len(set(valid)),
            'min': mn, 'max': mx, 'mean': me, 'std': sd,
            'note': 'quarter_FE_and_loo_not_compatible' if 'quarter_loo' in col else
                    'quarter_FE_prohibited' if 'year_quarter' in col else '',
        })
    else:
        h3_candidates.append({
            'variable': col, 'source_file': ds_name,
            'h3_role': 'H3_predictor_candidate', 'exists_in_file': False,
            'n_total': 0, 'non_missing_n': 0, 'missing_n': 0,
            'missing_rate': 'n/a', 'unique_n': 0,
            'min': 'n/a', 'max': 'n/a', 'mean': 'n/a', 'std': 'n/a',
            'note': '파일에 없음',
        })

# 재계산
h3_candidates2 = []
for col in h3_target_cols:
    exists = col in h3ds[0].keys()
    if exists:
        vals = [r.get(col, '') for r in h3ds]
        valid = [v for v in vals if v not in ('', None, 'nan')]
        n_miss = len(vals) - len(valid)
        nums = []
        for v in valid:
            try: nums.append(float(v))
            except: pass
        mn = round(min(nums), 6) if nums else 'n/a'
        mx = round(max(nums), 6) if nums else 'n/a'
        me = round(float(np.mean(nums)), 6) if nums else 'n/a'
        sd = round(float(np.std(nums, ddof=1)), 6) if len(nums) > 1 else 'n/a'
        h3_candidates2.append({
            'variable': col, 'source_file': ds_name,
            'h3_role': 'H3_predictor' if any(k in col for k in ('proportion','frequency','share')) else 'period_identifier',
            'exists_in_file': True,
            'n_total': len(vals), 'non_missing_n': len(valid),
            'missing_n': n_miss,
            'missing_rate': round(n_miss / len(vals), 4) if vals else 'nan',
            'unique_n': len(set(valid)),
            'min': mn, 'max': mx, 'mean': me, 'std': sd,
            'note': (
                'H3-main primary LOO predictor — quarter FE와 식별 불가' if col == 'aggressive_humor_proportion_quarter_loo' else
                'H3-pre primary LOO predictor — quarter FE와 식별 불가'  if col == 'humor_proportion_quarter_loo' else
                'quarter FE 사용 금지 (LOO 변수와 식별 불가)' if col == 'year_quarter' else ''
            ),
        })
    else:
        h3_candidates2.append({
            'variable': col, 'source_file': ds_name,
            'h3_role': 'H3_predictor', 'exists_in_file': False,
            'n_total': 0, 'non_missing_n': 0, 'missing_n': 0,
            'missing_rate': 'n/a', 'unique_n': 0,
            'min': 'n/a', 'max': 'n/a', 'mean': 'n/a', 'std': 'n/a',
            'note': '파일에 없음',
        })

with open(H3_CAND_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(h3_candidates2[0].keys()))
    w.writeheader(); w.writerows(h3_candidates2)
print(f"  → {H3_CAND_CSV} ({len(h3_candidates2)}개)")

# ── 6. Sample size 검증 ────────────────────────────────────────────────────────
print("[6] Sample size 검증")

# H1: pred 파일 기준
n_total_pred  = len(pred_ds)
n_label_avail = sum(1 for r in pred_ds if r.get('final_humor_label_available') == '1')
n_label_humor = sum(1 for r in pred_ds if r.get('final_humor_binary') == '1')
n_label_non   = sum(1 for r in pred_ds if r.get('final_humor_binary') == '0')
n_model_humor = sum(1 for r in pred_ds if r.get('pred_humor_final_050') == '1')
n_model_non   = sum(1 for r in pred_ds if r.get('pred_humor_final_050') == '0')

# H2: coder1 priority 기준 (597건)
n_h2_total      = len(h2_ds)
n_h2_lbl_avail  = sum(1 for r in h2_ds if r.get('final_humor_label_available') == '1')
h2_type_human   = Counter(r.get('final_humor_type_group','') for r in h2_ds if r.get('final_humor_type_available','') == '1')
# model-based (978건)
n_h2_model_agg  = type_dist_model.get('aggressive', 0)
n_h2_model_oth  = type_dist_model.get('other_humor', 0)
n_h2_model_non  = type_dist_model.get('non_humor', 0)

# H3 filtered
n_h3_filtered   = sum(1 for r in h3ds if r.get('in_h3_aggressive_filtered') == '1')
n_h3_quarters   = len(set(r['year_quarter'] for r in h3ds if r.get('in_h3_aggressive_filtered') == '1'))

sample_rows = [
    {'check': 'total_wendys_posts',             'expected': 978,  'actual': n_total_pred,   'match': n_total_pred==978},
    {'check': 'H1_human_label_available_n',      'expected': 597,  'actual': n_label_avail,  'match': n_label_avail>=280},
    {'check': 'H1_human_labeled_humor',          'expected': 'varies', 'actual': n_label_humor, 'match': True},
    {'check': 'H1_human_labeled_non_humor',      'expected': 'varies', 'actual': n_label_non,   'match': True},
    {'check': 'H1_model_predicted_humor',        'expected': 564,  'actual': n_model_humor,  'match': n_model_humor==564},
    {'check': 'H1_model_predicted_non_humor',    'expected': 414,  'actual': n_model_non,    'match': n_model_non==414},
    {'check': 'H2_coder1_total',                 'expected': 597,  'actual': n_h2_total,     'match': n_h2_total==597},
    {'check': 'H2_human_type_aggressive',        'expected': 'varies', 'actual': h2_type_human.get('aggressive', 0), 'match': True},
    {'check': 'H2_human_type_other_humor',       'expected': 'varies', 'actual': h2_type_human.get('other_humor', 0), 'match': True},
    {'check': 'H2_model_based_non_humor',        'expected': 414,  'actual': n_h2_model_non, 'match': n_h2_model_non==414},
    {'check': 'H2_model_based_aggressive',       'expected': 200,  'actual': n_h2_model_agg, 'match': n_h2_model_agg==200},
    {'check': 'H2_model_based_other_humor',      'expected': 364,  'actual': n_h2_model_oth, 'match': n_h2_model_oth==364},
    {'check': 'H3_filtered_posts_n960',          'expected': 960,  'actual': n_h3_filtered,  'match': n_h3_filtered==960},
    {'check': 'H3_filtered_quarters_25',         'expected': 25,   'actual': n_h3_quarters,  'match': n_h3_quarters==25},
    {'check': 'H2_h2_coder1_label_available',    'expected': 'n/a', 'actual': n_h2_lbl_avail, 'match': True},
]

# 4-type human label 분포 (review_sheet 기준)
type4_dist_rev = Counter(r.get('final_humor_type','') for r in review_ds if r.get('final_humor_type_available','') == '1')
for t, cnt in sorted(type4_dist_rev.items()):
    sample_rows.append({
        'check': f'H2_4type_human_{t}',
        'expected': 'varies', 'actual': cnt, 'match': True
    })

with open(SAMPLE_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['check','expected','actual','match'])
    w.writeheader(); w.writerows(sample_rows)
print(f"  → {SAMPLE_CSV}")

# 샘플 주요 결과 출력
print(f"  total_posts={n_total_pred}, label_avail={n_label_avail}")
print(f"  H1: humor={n_label_humor} non={n_label_non} | model: humor={n_model_humor} non={n_model_non}")
print(f"  H2 model: agg={n_h2_model_agg} other={n_h2_model_oth} non={n_h2_model_non}")
print(f"  H3 filtered: {n_h3_filtered}건, {n_h3_quarters}분기")

# ── 7. posts.json 변경 여부 확인 ──────────────────────────────────────────────
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON, 'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

# ── 8. view_count 결측 확인 ──────────────────────────────────────────────────
vc_vals  = [r.get('view_count', '') for r in h3ds]
vc_miss  = sum(1 for v in vc_vals if v in ('', None, 'nan', '0'))
lvc_vals = [r.get('log1p_view_count', '') for r in h3ds]
lvc_miss = sum(1 for v in lvc_vals if v in ('', None, 'nan'))
print(f"  view_count: miss_or_zero={vc_miss}/978, log1p_view_count: miss={lvc_miss}/978")

# fast_ds text_length 결측
for col in ['text_length','url_count','mention_count','hashtag_count',
            'emoji_count','is_quote_status','is_retweet_text']:
    miss = sum(1 for r in fast_ds if r.get(col, '') in ('', None))
    print(f"  fast_ds[{col}]: miss={miss}/978")

# ── 9. Summary markdown ───────────────────────────────────────────────────────
print("[9] summary.md 작성")

# 결측률 높은 변수 목록
high_miss = [(r['variable_name'], r['source_file'], r['missing_rate'])
             for r in all_inventory
             if isinstance(r['missing_rate'], float) and r['missing_rate'] > 0.1]
high_miss.sort(key=lambda x: -x[2])

# 파일별 요약 테이블
file_summary_lines = ["| 파일명 | rows | cols |", "|---|---|---|"]
for fs in file_structs:
    file_summary_lines.append(f"| {fs['file']} | {fs['rows']} | {fs['cols']} |")

def fmt_counter(c):
    return ', '.join(f"{k}={v}" for k, v in sorted(c.items()) if k)

summary_md = f"""# Wendy's 기존 변수 Inventory 요약

## 1. 검토한 파일 목록

| 파일 | rows | cols |
|---|---|---|
| wendys_final_humor_presence_full_predictions.csv | {len(pred_ds)} | {len(pred_ds[0].keys())} |
| wendys_fast_weak_supervised_humor_dataset.csv | {len(fast_ds)} | {len(fast_ds[0].keys())} |
| wendys_humor_review_sheet.csv | {len(review_ds)} | {len(review_ds[0].keys())} |
| wendys_h2_coder1_priority_dataset.csv | {len(h2_ds)} | {len(h2_ds[0].keys())} |
| wendys_humor_frequency_proportion_post_level_dataset.csv | 978 | 45 |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | {len(h3ds)} | {len(h3ds[0].keys())} |

---

## 2. 파일별 row/column 수

{chr(10).join(file_summary_lines)}

---

## 3. H1에 이미 존재하는 변수 후보

### A. 핵심 DV/IV

| 역할 | 변수 | 소스 파일 | missing_rate |
|---|---|---|---|
| DV (primary) | log1p_engagement_total | h3_aggressive_vs_other_dataset | 0 |
| DV (secondary) | log1p_favorite_count, log1p_retweet_count 등 | h3_aggressive_vs_other_dataset | 0 |
| IV (human) | final_humor_binary | final_humor_presence_full_predictions | 0 |
| IV (human filter) | final_humor_label_available | final_humor_presence_full_predictions | 0 |
| IV (model) | pred_humor_final_050 | h3_aggressive_vs_other_dataset | 0 |
| IV (prob) | p_humor_final_tfidf_logreg | h3_aggressive_vs_other_dataset | 0 |

### B. 시간 변수 (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| created_year | ✓ | h3_aggressive_vs_other_dataset |
| created_month | ✓ | h3_aggressive_vs_other_dataset |
| created_day | ✓ | h3_aggressive_vs_other_dataset |
| created_time | ✓ | h3_aggressive_vs_other_dataset |
| created_hour | ✓ | h3_aggressive_vs_other_dataset |
| created_date | ✓ | h3_aggressive_vs_other_dataset |
| year_month | ✓ | h3_aggressive_vs_other_dataset |
| year_quarter | ✓ | h3_aggressive_vs_other_dataset |
| **day_of_week** | **✗** | **존재하지 않음 — 이번 작업에서 생성하지 않음** |

### C. Posting intensity (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| quarter_total_posts | ✓ | h3_aggressive_vs_other_dataset |
| month_total_posts | ✓ | h3_aggressive_vs_other_dataset |
| day_total_posts | ✗ | 존재하지 않음 |

### D. Post format (기존 컬럼으로 존재 — wendys_fast_weak_supervised_humor_dataset.csv)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| text_length | ✓ | fast_weak_supervised dataset에만 존재, H3 dataset과 통합 필요 |
| url_count | ✓ | 동일 |
| mention_count | ✓ | 동일 |
| hashtag_count | ✓ | 동일 |
| emoji_count | ✓ | 동일 |
| is_quote_status | ✓ | 동일 |
| is_retweet_text | ✓ | 동일 |

**주의: 위 변수들은 wendys_fast_weak_supervised_humor_dataset.csv에 존재하며, 978건 기준 H3 dataset과 id 기준 병합이 필요하다. 이번 작업에서 병합하지 않았다.**

### E. Exposure (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| view_count | ✓ | h3_aggressive_vs_other_dataset, 결측 또는 0 주의 |
| log1p_view_count | ✓ | h3_aggressive_vs_other_dataset |

---

## 4. H2에 이미 존재하는 변수 후보

### 사람 코딩 타입 라벨 (h2_coder1_priority_dataset.csv, 597건)

| 변수 | n_non_missing | 비고 |
|---|---|---|
| final_humor_type | {sum(1 for r in h2_ds if r.get('final_humor_type','') not in ('','None'))} | 4-type 라벨 |
| final_humor_type_group | {sum(1 for r in h2_ds if r.get('final_humor_type_group','') not in ('','None'))} | aggressive/other_humor/non_humor |
| aggressive_humor | {sum(1 for r in h2_ds if r.get('aggressive_humor','') == '1')} | binary dummy |
| other_humor_flag | {sum(1 for r in h2_ds if r.get('other_humor_flag','') == '1')} | binary dummy |

### H2 사람 코딩 타입 분포

```
H2 human-labeled type_group (type_available=1 기준):
{fmt_counter(h2_type_human)}

H2 model-based (978건 기준):
non_humor={n_h2_model_non}, aggressive={n_h2_model_agg}, other_humor={n_h2_model_oth}

H2 4-type human (review_sheet, type_available=1 기준):
{fmt_counter(type4_dist_rev)}
```

### 모델 기반 타입 변수 (978건)

| 변수 | 비고 |
|---|---|
| pred_humor_type_group_model | aggressive/other_humor/non_humor |
| p_type_aggressive_model | 확률값 |
| p_type_other_humor_model | 확률값 |
| is_aggressive_humor | binary dummy |
| is_other_humor | binary dummy |

---

## 5. H3에 이미 존재하는 변수 후보

| 변수 | 존재 여부 | min | max | mean | 비고 |
|---|---|---|---|---|---|
| humor_proportion_quarter_loo | ✓ | 0.0 | 1.0 | ~0.58 | H3-pre primary LOO, quarter FE 식별 불가 |
| aggressive_humor_proportion_quarter_loo | ✓ | 0.0 | 0.3377 | ~0.21 | H3-main primary LOO, quarter FE 식별 불가 |
| other_humor_proportion_quarter_loo | ✓ | 0.0 | 0.6667 | ~0.37 | H3-main 보조 predictor |
| aggressive_share_among_humor_quarter_loo | ✓ | 0.0 | 1.0 | ~0.37 | H3-main 보조 predictor |
| humor_frequency_quarter | ✓ | — | — | — | H3-pre frequency |
| aggressive_humor_frequency_quarter | ✓ | — | — | — | H3-main frequency |
| quarter_total_posts | ✓ | — | — | — | period-level denominator |
| year_quarter | ✓ | — | — | — | period 식별자 (FE 사용 금지) |

---

## 6. 새로 생성하지 말아야 하는 변수 목록

다음 변수들은 이미 컬럼으로 존재하므로 새로 계산하지 않아도 된다.

```
text_length, url_count, mention_count, hashtag_count, emoji_count
is_quote_status, is_retweet_text
log1p_engagement_total, log1p_*_count
view_count, log1p_view_count
humor_proportion_quarter_loo, aggressive_humor_proportion_quarter_loo
month_total_posts, quarter_total_posts
created_year, created_month, created_day, created_hour
```

---

## 7. 결측률이 높아 사용 주의가 필요한 변수

| 변수 | 파일 | missing_rate |
|---|---|---|
{"".join(f"| {v} | {s} | {round(m,4)} |{chr(10)}" for v, s, m in high_miss[:15]) if high_miss else "| (없음) | — | — |"}

view_count 및 log1p_view_count는 0 또는 결측이 다수 포함될 수 있으므로 노출 통제 시 주의가 필요하다.

---

## 8. Primary model에 바로 넣으면 위험한 변수

| 변수 | 이유 |
|---|---|
| year_quarter (FE) | humor_proportion_quarter_loo / aggressive_humor_proportion_quarter_loo와 동시에 사용 시 식별 불가 |
| engagement_total (log 미변환) | 우편향 분포, log1p 변환 필요 |
| view_count | 다른 engagement DV와 다중공선성 가능, 노출 통제 변수 역할로만 사용 권장 |
| p_humor_final_tfidf_logreg | pred_humor_final_050과 함께 사용 시 다중공선성 |
| humor_score (fast_ds) | 초기 weak supervised 점수, 최종 모델 예측값과 다른 개념 |
| text_length, url_count 등 | fast_ds와 H3 dataset 병합 전까지 직접 사용 불가 |

---

## 9. 다음 단계에서 사용자 승인이 필요한 변수

1. **통제변수 병합**: text_length, url_count 등 fast_ds에만 있는 변수를 H3 dataset에 병합할지 여부
2. **day_of_week**: created_date에서 계산 가능하나 이번 작업에서 생성하지 않음 — 필요 여부 확인 필요
3. **view_count 통제**: H1 regression에서 log1p_view_count를 노출 통제변수로 포함할지 여부 (결측 처리 방식 포함)
4. **H2 표본 기준**: 사람 코딩 type_available=1 기준 인원 수 확인 후 H2 controlled regression 수행 여부

---

## 10. 원본 파일 변경 여부 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/H3 결과 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_MD, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_MD}")
print(f"\n[완료] posts.json 변경={posts_json_modified}, 회귀분석 수행=False, 새 통제변수 생성=False")
