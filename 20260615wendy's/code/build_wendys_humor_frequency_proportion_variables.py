"""
build_wendys_humor_frequency_proportion_variables.py

목적: H3 분석에 사용할 Frequency of Humor와 Proportion of Humor 변수를 명시적으로 생성한다.
      H3 회귀분석은 이 스크립트에서 수행하지 않는다.

정의:
  Frequency of Humor = 기간 내 유머 게시글의 절대 개수
  Proportion of Humor = 기간 내 전체 SNS 게시글 중 유머 게시글의 비율
"""

import csv
import math
import os
import hashlib
from collections import Counter, defaultdict

import numpy as np

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")

POST_DS_IN   = os.path.join(DATA_DIR,   "wendys_simple_humor_intensity_post_level_dataset.csv")
MONTHLY_IN   = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_monthly_audit.csv")
QUARTERLY_IN = os.path.join(RESULT_DIR, "wendys_simple_humor_intensity_quarterly_audit.csv")
POSTS_JSON   = os.path.join("data", "wendys", "posts.json")

POST_DS_OUT  = os.path.join(DATA_DIR,   "wendys_humor_frequency_proportion_post_level_dataset.csv")
MONTHLY_OUT  = os.path.join(RESULT_DIR, "wendys_humor_frequency_proportion_monthly.csv")
QUARTERLY_OUT= os.path.join(RESULT_DIR, "wendys_humor_frequency_proportion_quarterly.csv")
DIAG_OUT     = os.path.join(RESULT_DIR, "wendys_humor_frequency_proportion_diagnostics.csv")
VARDICT_OUT  = os.path.join(RESULT_DIR, "wendys_humor_frequency_proportion_variable_dictionary.md")
SUMMARY_OUT  = os.path.join(RESULT_DIR, "wendys_humor_frequency_proportion_summary.md")

TOLERANCE = 1e-6

# ── 0. posts.json 보호 확인 ────────────────────────────────────────────────────
print("[0] posts.json 보호 확인")
HASH_BEFORE = None
try:
    with open(POSTS_JSON, 'rb') as f:
        HASH_BEFORE = hashlib.md5(f.read()).hexdigest()
    print(f"  posts.json md5: {HASH_BEFORE}")
except FileNotFoundError:
    print("  posts.json 없음")

# ── 1. 기존 post-level 데이터 로드 ────────────────────────────────────────────
print("[1] 기존 post-level 데이터 로드")
with open(POST_DS_IN, newline='', encoding='utf-8') as f:
    posts = list(csv.DictReader(f))
print(f"  rows: {len(posts)}")

pred_humor       = sum(1 for r in posts if r['pred_humor_final_050']=='1')
pred_non_humor   = sum(1 for r in posts if r['pred_humor_final_050']=='0')
missing_pred     = sum(1 for r in posts if r['pred_humor_final_050'] not in ('0','1'))
print(f"  humor={pred_humor}, non_humor={pred_non_humor}, missing={missing_pred}")

# ── 2. Period 집계 (month / quarter) ─────────────────────────────────────────
print("[2] Period 집계")
by_month   = defaultdict(list)
by_quarter = defaultdict(list)
for r in posts:
    by_month[r['year_month']].append(r)
    by_quarter[r['year_quarter']].append(r)

def period_humor_counts(period_dict):
    result = {}
    for p, rows in period_dict.items():
        total = len(rows)
        humor = sum(1 for r in rows if r['pred_humor_final_050']=='1')
        result[p] = {'total': total, 'humor': humor, 'non_humor': total - humor}
    return result

month_counts   = period_humor_counts(by_month)
quarter_counts = period_humor_counts(by_quarter)

print(f"  월별 period: {len(month_counts)}개")
print(f"  분기별 period: {len(quarter_counts)}개")

# ── 3. Post-level 변수 생성 ────────────────────────────────────────────────────
print("[3] Post-level 변수 생성")
month_loo_missing = 0
qtr_loo_missing   = 0

new_posts = []
for r in posts:
    ym = r['year_month']
    yq = r['year_quarter']
    h_i = 1 if r['pred_humor_final_050']=='1' else 0

    mc = month_counts.get(ym, {'total':0,'humor':0,'non_humor':0})
    qc = quarter_counts.get(yq, {'total':0,'humor':0,'non_humor':0})

    mt, mh = mc['total'], mc['humor']
    qt, qh = qc['total'], qc['humor']

    # Frequency
    humor_frequency_month   = mh
    humor_frequency_quarter = qh

    # Proportion
    humor_proportion_month   = round(mh/mt, 6) if mt > 0 else 'nan'
    humor_proportion_quarter = round(qh/qt, 6) if qt > 0 else 'nan'

    # LOO Proportion
    if mt <= 1:
        humor_proportion_month_loo = 'nan'
        month_loo_missing += 1
    else:
        humor_proportion_month_loo = round((mh - h_i) / (mt - 1), 6)

    if qt <= 1:
        humor_proportion_quarter_loo = 'nan'
        qtr_loo_missing += 1
    else:
        humor_proportion_quarter_loo = round((qh - h_i) / (qt - 1), 6)

    new_r = dict(r)
    new_r['month_total_posts']             = mt
    new_r['month_humor_posts']             = mh
    new_r['month_non_humor_posts']         = mt - mh
    new_r['humor_frequency_month']         = humor_frequency_month
    new_r['humor_proportion_month']        = humor_proportion_month
    new_r['humor_proportion_month_loo']    = humor_proportion_month_loo
    new_r['quarter_total_posts']           = qt
    new_r['quarter_humor_posts']           = qh
    new_r['quarter_non_humor_posts']       = qt - qh
    new_r['humor_frequency_quarter']       = humor_frequency_quarter
    new_r['humor_proportion_quarter']      = humor_proportion_quarter
    new_r['humor_proportion_quarter_loo']  = humor_proportion_quarter_loo
    new_posts.append(new_r)

print(f"  LOO month missing: {month_loo_missing}  LOO quarter missing: {qtr_loo_missing}")

# ── 4. 일치 검증 (vs 기존 humor_intensity_*) ──────────────────────────────────
print("[4] 기존 intensity 변수와의 일치 검증")

def safe_float(v):
    if v == 'nan' or v == '' or v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None

def check_match(new_vals, old_vals, label):
    mismatches = 0
    for nv, ov in zip(new_vals, old_vals):
        nf = safe_float(nv)
        of = safe_float(ov)
        if nf is None and of is None:
            continue
        if nf is None or of is None:
            mismatches += 1
            continue
        if abs(nf - of) > TOLERANCE:
            mismatches += 1
    match = mismatches == 0
    print(f"  {label}: {'MATCH ✓' if match else f'MISMATCH ✗ ({mismatches}건)'}")
    return match

m_prop_old  = [r['humor_intensity_month']        for r in posts]
m_prop_new  = [r['humor_proportion_month']        for r in new_posts]
q_prop_old  = [r['humor_intensity_quarter']       for r in posts]
q_prop_new  = [r['humor_proportion_quarter']      for r in new_posts]
m_loo_old   = [r['humor_intensity_month_loo']     for r in posts]
m_loo_new   = [r['humor_proportion_month_loo']    for r in new_posts]
q_loo_old   = [r['humor_intensity_quarter_loo']   for r in posts]
q_loo_new   = [r['humor_proportion_quarter_loo']  for r in new_posts]

match_m_prop  = check_match(m_prop_new, m_prop_old, 'humor_proportion_month  vs  humor_intensity_month')
match_q_prop  = check_match(q_prop_new, q_prop_old, 'humor_proportion_quarter vs humor_intensity_quarter')
match_m_loo   = check_match(m_loo_new,  m_loo_old,  'humor_proportion_month_loo  vs  humor_intensity_month_loo')
match_q_loo   = check_match(q_loo_new,  q_loo_old,  'humor_proportion_quarter_loo vs humor_intensity_quarter_loo')

all_match = match_m_prop and match_q_prop and match_m_loo and match_q_loo
print(f"  전체 일치: {'PASS' if all_match else 'FAIL'}")

if not all_match:
    print("[ERROR] intensity 일치 검증 실패 — commit 하지 않음.")
    import sys; sys.exit(1)

# ── 5. Post-level dataset 저장 ────────────────────────────────────────────────
print("[5] Post-level dataset 저장")
existing_fields = list(posts[0].keys())
new_fields = [
    'month_total_posts','month_humor_posts','month_non_humor_posts',
    'humor_frequency_month','humor_proportion_month','humor_proportion_month_loo',
    'quarter_total_posts','quarter_humor_posts','quarter_non_humor_posts',
    'humor_frequency_quarter','humor_proportion_quarter','humor_proportion_quarter_loo',
]
all_fields = existing_fields + new_fields

with open(POST_DS_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(new_posts)
print(f"  → {POST_DS_OUT}")

# ── 6. Period-level 파일 생성 ─────────────────────────────────────────────────
print("[6] Period-level 파일 생성")
with open(MONTHLY_IN, newline='', encoding='utf-8') as f:
    monthly_src = list(csv.DictReader(f))
with open(QUARTERLY_IN, newline='', encoding='utf-8') as f:
    quarterly_src = list(csv.DictReader(f))

period_fields = [
    'period','period_type','total_posts','humor_posts','non_humor_posts',
    'humor_frequency','humor_proportion',
    'mean_p_humor','median_p_humor',
    'mean_log1p_engagement_total','median_log1p_engagement_total',
    'min_created_date','max_created_date',
]

def build_period_rows(src_rows):
    out = []
    for r in src_rows:
        total = int(r['total_posts'])
        humor = int(r['humor_posts'])
        prop  = round(humor/total, 6) if total > 0 else 'nan'
        out.append({
            'period':       r['period'],
            'period_type':  r['period_type'],
            'total_posts':  total,
            'humor_posts':  humor,
            'non_humor_posts': int(r['non_humor_posts']),
            'humor_frequency':  humor,
            'humor_proportion': prop,
            'mean_p_humor':   r.get('mean_p_humor',''),
            'median_p_humor': r.get('median_p_humor',''),
            'mean_log1p_engagement_total':   r.get('mean_log1p_engagement_total',''),
            'median_log1p_engagement_total': r.get('median_log1p_engagement_total',''),
            'min_created_date': r.get('min_created_date',''),
            'max_created_date': r.get('max_created_date',''),
        })
    return out

monthly_out   = build_period_rows(monthly_src)
quarterly_out = build_period_rows(quarterly_src)

with open(MONTHLY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=period_fields)
    w.writeheader()
    w.writerows(monthly_out)
print(f"  → {MONTHLY_OUT}")

with open(QUARTERLY_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=period_fields)
    w.writeheader()
    w.writerows(quarterly_out)
print(f"  → {QUARTERLY_OUT}")

# ── 7. Diagnostics ────────────────────────────────────────────────────────────
print("[7] Diagnostics")
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON,'rb') as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2 != HASH_BEFORE)
    except FileNotFoundError:
        pass

def stats(vals):
    v = [float(x) for x in vals if safe_float(x) is not None]
    if not v:
        return {'min':'nan','max':'nan','mean':'nan','sd':'nan','median':'nan'}
    return {
        'min':    round(min(v),4),
        'max':    round(max(v),4),
        'mean':   round(float(np.mean(v)),4),
        'sd':     round(float(np.std(v,ddof=1)),4) if len(v)>1 else 'nan',
        'median': round(float(np.median(v)),4),
    }

mf_vals = [r['humor_frequency_month']   for r in new_posts]
qf_vals = [r['humor_frequency_quarter'] for r in new_posts]
mp_vals = [r['humor_proportion_month']  for r in new_posts]
qp_vals = [r['humor_proportion_quarter'] for r in new_posts]
mt_vals = [r['month_total_posts']        for r in new_posts]
qt_vals = [r['quarter_total_posts']      for r in new_posts]

mf_s  = stats(mf_vals);  qf_s = stats(qf_vals)
mp_s  = stats(mp_vals);  qp_s = stats(qp_vals)
mt_s  = stats(mt_vals);  qt_s = stats(qt_vals)

diag = {
    'total_rows': len(posts),
    'merged_rows': len(new_posts),
    'predicted_humor_rows': pred_humor,
    'predicted_non_humor_rows': pred_non_humor,
    'missing_pred_humor_rows': missing_pred,
    'month_period_count': len(month_counts),
    'quarter_period_count': len(quarter_counts),
    'month_total_posts_min': mt_s['min'],
    'month_total_posts_median': mt_s['median'],
    'month_total_posts_mean': mt_s['mean'],
    'month_total_posts_max': mt_s['max'],
    'quarter_total_posts_min': qt_s['min'],
    'quarter_total_posts_median': qt_s['median'],
    'quarter_total_posts_mean': qt_s['mean'],
    'quarter_total_posts_max': qt_s['max'],
    'month_humor_frequency_min': mf_s['min'],
    'month_humor_frequency_max': mf_s['max'],
    'month_humor_frequency_mean': mf_s['mean'],
    'month_humor_frequency_sd': mf_s['sd'],
    'quarter_humor_frequency_min': qf_s['min'],
    'quarter_humor_frequency_max': qf_s['max'],
    'quarter_humor_frequency_mean': qf_s['mean'],
    'quarter_humor_frequency_sd': qf_s['sd'],
    'month_humor_proportion_min': mp_s['min'],
    'month_humor_proportion_max': mp_s['max'],
    'month_humor_proportion_mean': mp_s['mean'],
    'month_humor_proportion_sd': mp_s['sd'],
    'quarter_humor_proportion_min': qp_s['min'],
    'quarter_humor_proportion_max': qp_s['max'],
    'quarter_humor_proportion_mean': qp_s['mean'],
    'quarter_humor_proportion_sd': qp_s['sd'],
    'month_loo_missing_rows': month_loo_missing,
    'quarter_loo_missing_rows': qtr_loo_missing,
    'month_proportion_matches_existing_intensity': match_m_prop,
    'quarter_proportion_matches_existing_intensity': match_q_prop,
    'month_loo_matches_existing_intensity_loo': match_m_loo,
    'quarter_loo_matches_existing_intensity_loo': match_q_loo,
    'original_posts_json_modified': posts_json_modified,
    'analysis_note': 'H3 회귀분석 미수행. 변수화 작업만 수행.',
}

with open(DIAG_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['metric','value'])
    w.writeheader()
    for k, v in diag.items():
        w.writerow({'metric': k, 'value': v})
print(f"  → {DIAG_OUT}")

# ── 8. Variable Dictionary ────────────────────────────────────────────────────
print("[8] Variable dictionary 작성")
vardict_md = f"""# Wendy's Humor Frequency & Proportion 변수 사전

본 프로젝트에서 Humor Usage Intensity는 개별 게시글의 유머 강도가 아니라, 특정 기간 내 유머 게시글 비중으로 조작화한다.

---

## 변수 개요

Frequency of Humor는 특정 기간 내 유머 게시글의 절대 개수이다.

Proportion of Humor는 특정 기간 내 전체 SNS 게시글 중 유머 게시글이 차지하는 비율이다.

H3 회귀분석에서는 게시글 자기 자신이 기간 비중 계산에 포함되는 문제를 줄이기 위해 leave-one-out proportion 변수를 우선적으로 사용할 수 있다.

유머 유무 기준: `pred_humor_final_050` (모델 기반 예측값, 확정 사람 코딩 아님)

---

## 1. humor_frequency_month

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_frequency_month |
| **한국어 설명** | 해당 게시글이 속한 월의 유머 게시글 절대 개수 |
| **수식** | humor_frequency_month = Σ(pred_humor_final_050 = 1) within year_month |
| **분석 단위** | post-level (해당 월의 집계값을 각 post에 할당) |
| **해석** | 해당 게시글이 게시된 달에 Wendy's가 몇 개의 유머 게시글을 올렸는가 |
| **주의사항** | 절대 개수이므로 게시물 총량이 많은 시기에 자연히 커진다. 비율 기반 humor_proportion_month와 함께 확인해야 한다. pred_humor_final_050은 모델 기반 예측이므로 오류 포함 가능. |
| **월별 범위** | min={mf_s['min']}, max={mf_s['max']}, mean={mf_s['mean']}, sd={mf_s['sd']} |

---

## 2. humor_frequency_quarter

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_frequency_quarter |
| **한국어 설명** | 해당 게시글이 속한 분기의 유머 게시글 절대 개수 |
| **수식** | humor_frequency_quarter = Σ(pred_humor_final_050 = 1) within year_quarter |
| **분석 단위** | post-level (해당 분기의 집계값을 각 post에 할당) |
| **해석** | 해당 게시글이 게시된 분기에 Wendy's가 몇 개의 유머 게시글을 올렸는가 |
| **주의사항** | 분기 기준이 월 기준보다 표본 안정성이 높다. H3 보조 변수로 활용 가능. |
| **분기별 범위** | min={qf_s['min']}, max={qf_s['max']}, mean={qf_s['mean']}, sd={qf_s['sd']} |

---

## 3. humor_proportion_month

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_month |
| **한국어 설명** | 해당 게시글이 속한 월의 전체 게시글 중 유머 게시글 비율 |
| **수식** | humor_proportion_month = humor_frequency_month / month_total_posts |
| **분석 단위** | post-level (0~1 범위의 비율값) |
| **해석** | 해당 게시글이 게시된 달에 Wendy's SNS 게시글의 몇 %가 유머였는가 |
| **주의사항** | 기존 humor_intensity_month와 동일한 값이다. 월 총 게시글 수가 적은 시기(n=1~5)에서는 비율이 불안정하다. |
| **월별 범위** | min={mp_s['min']}, max={mp_s['max']}, mean={mp_s['mean']}, sd={mp_s['sd']} |

---

## 4. humor_proportion_quarter

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_quarter |
| **한국어 설명** | 해당 게시글이 속한 분기의 전체 게시글 중 유머 게시글 비율 |
| **수식** | humor_proportion_quarter = humor_frequency_quarter / quarter_total_posts |
| **분석 단위** | post-level (0~1 범위의 비율값) |
| **해석** | 해당 게시글이 게시된 분기에 Wendy's SNS 게시글의 몇 %가 유머였는가 |
| **주의사항** | 기존 humor_intensity_quarter와 동일한 값이다. 분기 단위가 월 단위보다 안정적. |
| **분기별 범위** | min={qp_s['min']}, max={qp_s['max']}, mean={qp_s['mean']}, sd={qp_s['sd']} |

---

## 5. humor_proportion_month_loo

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_month_loo |
| **한국어 설명** | 해당 게시글을 제외한 당월 유머 비율 (leave-one-out) |
| **수식** | (month_humor_posts − pred_humor_final_050_i) / (month_total_posts − 1) |
| **분석 단위** | post-level |
| **해석** | 내 게시글을 제외했을 때, 해당 달의 나머지 게시글 중 유머 비율이 얼마인가 |
| **주의사항** | month_total_posts = 1인 경우 missing. LOO missing: {month_loo_missing}건. 기존 humor_intensity_month_loo와 동일한 값. |

---

## 6. humor_proportion_quarter_loo

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_quarter_loo |
| **한국어 설명** | 해당 게시글을 제외한 해당 분기 유머 비율 (leave-one-out) |
| **수식** | (quarter_humor_posts − pred_humor_final_050_i) / (quarter_total_posts − 1) |
| **분석 단위** | post-level |
| **해석** | 내 게시글을 제외했을 때, 해당 분기의 나머지 게시글 중 유머 비율이 얼마인가 |
| **주의사항** | quarter_total_posts = 1인 경우 missing. LOO missing: {qtr_loo_missing}건. H3 회귀분석 primary predictor 후보. 기존 humor_intensity_quarter_loo와 동일한 값. |

---

*생성일: 2026-06-15*
"""

with open(VARDICT_OUT, 'w', encoding='utf-8') as f:
    f.write(vardict_md)
print(f"  → {VARDICT_OUT}")

# ── 9. Summary markdown ────────────────────────────────────────────────────────
print("[9] summary.md 작성")

m_rows_sorted = sorted(monthly_out, key=lambda r: r['period'])
q_rows_sorted = sorted(quarterly_out, key=lambda r: r['period'])

summary_md = f"""# Wendy's Frequency of Humor / Proportion of Humor 변수화 결과

## 1. 작업 목적

본 작업은 H3 회귀분석이 아니라, H3 분석에 사용할 Frequency of Humor와 Proportion of Humor 변수를 명시적으로 생성하는 변수화 작업이다.

Frequency of Humor는 기간 내 유머 게시글 수이며, Proportion of Humor는 기간 내 전체 SNS 게시글 중 유머 게시글의 비율이다.

---

## 2. 사용 데이터

- `wendys_simple_humor_intensity_post_level_dataset.csv`: 기존 post-level 데이터 (978행)
- `wendys_simple_humor_intensity_monthly_audit.csv`: 기존 월별 period 집계
- `wendys_simple_humor_intensity_quarterly_audit.csv`: 기존 분기별 period 집계

---

## 3. 유머 유무 기준

pred_humor_final_050은 모델 기반 유머 유무 예측값이므로, Frequency와 Proportion 역시 확정 사람 코딩값이 아니라 모델 기반 분류값을 바탕으로 계산된 변수이다.

| 항목 | n |
|---|---|
| 전체 post | {len(posts)} |
| predicted humor (pred=1) | {pred_humor} |
| predicted non_humor (pred=0) | {pred_non_humor} |
| missing | {missing_pred} |

---

## 4. Frequency of Humor 변수 정의

Frequency of Humor는 특정 기간 내 유머 게시글의 절대 개수이다.

```
humor_frequency_month   = 해당 월의 pred_humor_final_050 = 1인 게시글 수
humor_frequency_quarter = 해당 분기의 pred_humor_final_050 = 1인 게시글 수
```

Frequency 변수는 게시물 총량(활동 수준)의 영향을 받는다.
따라서 H3 주 분석에서는 Proportion 변수를 우선하되, Frequency는 보조 변수로 활용한다.

---

## 5. Proportion of Humor 변수 정의

Proportion of Humor는 특정 기간 내 전체 SNS 게시글 중 유머 게시글이 차지하는 비율이다.

```
humor_proportion_month   = humor_frequency_month   / month_total_posts
humor_proportion_quarter = humor_frequency_quarter / quarter_total_posts
```

Proportion of Humor는 기존 humor_intensity와 동일한 값이며, 본 작업에서는 이론적 해석을 명확히 하기 위해 변수명을 분리하였다.

---

## 6. Leave-one-out Proportion 변수 정의

```
humor_proportion_month_loo   = (month_humor_posts - pred_humor_final_050_i)   / (month_total_posts - 1)
humor_proportion_quarter_loo = (quarter_humor_posts - pred_humor_final_050_i) / (quarter_total_posts - 1)
```

- month LOO missing (period n=1): {month_loo_missing}건
- quarter LOO missing (period n=1): {qtr_loo_missing}건

---

## 7. 월별 변수 분포

| 항목 | Frequency (count) | Proportion (rate) |
|---|---|---|
| 최솟값 | {mf_s['min']} | {mp_s['min']} |
| 최댓값 | {mf_s['max']} | {mp_s['max']} |
| 평균 | {mf_s['mean']} | {mp_s['mean']} |
| 표준편차 | {mf_s['sd']} | {mp_s['sd']} |

월별 period 수: {len(month_counts)}개 (total_posts: min={mt_s['min']}, max={mt_s['max']})

---

## 8. 분기별 변수 분포

| 항목 | Frequency (count) | Proportion (rate) |
|---|---|---|
| 최솟값 | {qf_s['min']} | {qp_s['min']} |
| 최댓값 | {qf_s['max']} | {qp_s['max']} |
| 평균 | {qf_s['mean']} | {qp_s['mean']} |
| 표준편차 | {qf_s['sd']} | {qp_s['sd']} |

분기별 period 수: {len(quarter_counts)}개 (total_posts: min={qt_s['min']}, max={qt_s['max']})

---

## 9. 기존 humor_intensity 변수와의 일치 검증

| 검증 항목 | 결과 |
|---|---|
| humor_proportion_month == humor_intensity_month | {'PASS ✓' if match_m_prop else 'FAIL ✗'} |
| humor_proportion_quarter == humor_intensity_quarter | {'PASS ✓' if match_q_prop else 'FAIL ✗'} |
| humor_proportion_month_loo == humor_intensity_month_loo | {'PASS ✓' if match_m_loo else 'FAIL ✗'} |
| humor_proportion_quarter_loo == humor_intensity_quarter_loo | {'PASS ✓' if match_q_loo else 'FAIL ✗'} |

허용 오차: |diff| ≤ {TOLERANCE}

---

## 10. H3 분석에서의 사용 방향

| 변수 | H3 역할 | 우선순위 |
|---|---|---|
| humor_proportion_quarter_loo | H3 primary predictor 후보 | 1순위 |
| humor_proportion_month_loo | H3 보조 predictor | 2순위 |
| humor_proportion_quarter | LOO 대안 (표본 안정성) | 보조 |
| humor_frequency_quarter | 보조 변수 (절대 개수 기반) | 보조 |
| humor_frequency_month | 보조 변수 (절대 개수, 월별) | 보조 |

H3 회귀분석에서는 게시글 자기 자신이 기간 비중 계산에 포함되는 문제를 줄이기 위해 leave-one-out proportion 변수를 우선적으로 사용할 수 있다.

---

## 11. 해석상 주의사항

- 본 작업은 변수화 작업이며 H3 회귀분석은 수행하지 않았다.
- 인과관계를 주장하지 않는다. Frequency와 Proportion은 기술통계적 기간 집계 변수이다.
- pred_humor_final_050은 모델 기반 예측이므로 분류 오류가 포함되어 있다.
- 2009-11 (n=1) 등 극소 period는 Proportion을 불안정하게 만든다. 이후 H3 분석 시 이상치 period 처리 방안을 별도 결정해야 한다.
- Frequency는 총 게시량 변화의 영향을 받으므로 Proportion과 함께 해석해야 한다.

---

## 12. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: {posts_json_modified}
- 기존 H1/H2/intensity 파일 수정 없음

---

*생성일: 2026-06-15*
"""

with open(SUMMARY_OUT, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print(f"  → {SUMMARY_OUT}")

# ── 10. Validation checks ─────────────────────────────────────────────────────
print("[10] Validation checks")
checks = []
def chk(name, passed, detail=""):
    s = "PASS" if passed else "FAIL"
    checks.append({'check': name, 'status': s, 'detail': detail})
    print(f"  [{'✓' if passed else '✗'}] {name}: {detail}")
    return passed

all_out = [POST_DS_OUT, MONTHLY_OUT, QUARTERLY_OUT, DIAG_OUT, VARDICT_OUT, SUMMARY_OUT]
chk("01_all_outputs_in_folder",
    all(p.startswith("20260615wendy's/") for p in all_out), "경로 확인")
chk("02_posts_json_not_modified", not posts_json_modified, f"modified={posts_json_modified}")
chk("03_post_level_rows_978", len(new_posts)==978, f"n={len(new_posts)}")
chk("04_predicted_humor_564", pred_humor==564, f"n={pred_humor}")
chk("05_predicted_non_humor_414", pred_non_humor==414, f"n={pred_non_humor}")
chk("06_missing_pred_0", missing_pred==0, f"missing={missing_pred}")
chk("07_humor_frequency_month_exists",
    all('humor_frequency_month' in r for r in new_posts), "컬럼 존재")
chk("08_humor_frequency_quarter_exists",
    all('humor_frequency_quarter' in r for r in new_posts), "컬럼 존재")
chk("09_humor_proportion_month_exists",
    all('humor_proportion_month' in r for r in new_posts), "컬럼 존재")
chk("10_humor_proportion_quarter_exists",
    all('humor_proportion_quarter' in r for r in new_posts), "컬럼 존재")
chk("11_humor_proportion_month_loo_exists",
    all('humor_proportion_month_loo' in r for r in new_posts), "컬럼 존재")
chk("12_humor_proportion_quarter_loo_exists",
    all('humor_proportion_quarter_loo' in r for r in new_posts), "컬럼 존재")
chk("13_proportion_month_matches_intensity", match_m_prop, "일치 검증 PASS")
chk("14_proportion_quarter_matches_intensity", match_q_prop, "일치 검증 PASS")
chk("15_proportion_month_loo_matches_intensity", match_m_loo, "일치 검증 PASS")
chk("16_proportion_quarter_loo_matches_intensity", match_q_loo, "일치 검증 PASS")
chk("17_variable_dictionary_exists", os.path.exists(VARDICT_OUT), "파일 존재")
chk("18_summary_has_frequency_proportion_diff",
    'Frequency of Humor는 기간 내 유머 게시글 수이며' in summary_md, "표현 확인")
chk("19_summary_has_h3_not_performed",
    'H3 회귀분석이 아니라' in summary_md, "미수행 명시 확인")
chk("20_summary_has_causal_warning",
    '인과관계를 주장하지 않는다' in summary_md, "인과 해석 금지 확인")

n_pass = sum(1 for c in checks if c['status']=='PASS')
n_fail = sum(1 for c in checks if c['status']=='FAIL')
print(f"\n  Validation: {n_pass}/20 PASS, {n_fail} FAIL")

if n_fail > 0:
    print("[ERROR] 검증 FAIL — commit 하지 않음.")
    import sys; sys.exit(1)

print(f"\n[완료] 모든 작업 완료. Validation {n_pass}/20 PASS.")
print("  커밋 대상: analysis: define wendys humor frequency and proportion variables")
