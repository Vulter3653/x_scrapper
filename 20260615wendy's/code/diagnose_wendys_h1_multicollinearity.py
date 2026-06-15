"""
diagnose_wendys_h1_multicollinearity.py

목적: H1 controlled regression 전 후보 통제변수 다중공선성 사전 진단.
      회귀분석을 수행하지 않으며, 새 변수를 생성하지 않는다.
"""

import csv
import math
import os
import hashlib
from collections import Counter

import numpy as np
from scipy import stats

BASE       = "20260615wendy's"
DATA_DIR   = os.path.join(BASE, "data")
RESULT_DIR = os.path.join(BASE, "result")
POSTS_JSON = os.path.join("data", "wendys", "posts.json")

PRED_FILE = os.path.join(RESULT_DIR, "wendys_final_humor_presence_full_predictions.csv")
FAST_FILE = os.path.join(DATA_DIR,   "wendys_fast_weak_supervised_humor_dataset.csv")
H3_FILE   = os.path.join(DATA_DIR,   "wendys_h3_aggressive_vs_other_intensity_dataset.csv")

VARSUMM_OUT   = os.path.join(RESULT_DIR, "wendys_h1_multicollinearity_variable_summary.csv")
CORR_OUT      = os.path.join(RESULT_DIR, "wendys_h1_multicollinearity_pairwise_correlations.csv")
VIF_OUT       = os.path.join(RESULT_DIR, "wendys_h1_multicollinearity_vif.csv")
COND_OUT      = os.path.join(RESULT_DIR, "wendys_h1_multicollinearity_condition_number.csv")
RECOM_OUT     = os.path.join(RESULT_DIR, "wendys_h1_multicollinearity_recommendations.md")

def safe_float(v):
    if v in ('nan', '', None): return None
    # boolean string 처리 (is_quote_status, is_retweet_text)
    if isinstance(v, str):
        if v.lower() == 'true':  return 1.0
        if v.lower() == 'false': return 0.0
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

# ── 1. 데이터 로드 및 병합 ────────────────────────────────────────────────────
print("[1] 데이터 로드 및 병합")
with open(PRED_FILE, newline='', encoding='utf-8') as f:
    pred_rows = list(csv.DictReader(f))
with open(FAST_FILE, newline='', encoding='utf-8') as f:
    fast_rows = list(csv.DictReader(f))
with open(H3_FILE, newline='', encoding='utf-8') as f:
    h3_rows   = list(csv.DictReader(f))

fast_map = {r['id']: r for r in fast_rows}
h3_map   = {r['id']: r for r in h3_rows}

merged_all = []
unmatched  = 0
for r in pred_rows:
    pid = r['id']
    fm  = fast_map.get(pid)
    hm  = h3_map.get(pid)
    if fm is None or hm is None:
        unmatched += 1
        continue
    row = {}
    row.update(r)       # pred: final_humor_binary, final_humor_label_available 등
    row.update(fm)      # fast: text_length, url_count 등 (id 중복은 덮어쓰기)
    row.update(hm)      # h3:  created_year/month/hour, quarter/month_total_posts 등
    merged_all.append(row)

print(f"  전체 merged: {len(merged_all)}건, unmatched: {unmatched}")

# Primary sample: final_humor_label_available = 1
primary = [r for r in merged_all if r.get('final_humor_label_available') == '1']
print(f"  primary sample (label_available=1): {len(primary)}건")

# 병합 검증
pred_ids_primary = set(r['id'] for r in primary)
fast_match = sum(1 for r in primary if r['id'] in fast_map)
assert len(primary) == 597, f"primary sample n={len(primary)} (expected 597)"
assert unmatched == 0, f"unmatched={unmatched}"

merge_info = {
    'left_file': 'wendys_final_humor_presence_full_predictions.csv',
    'right_files': 'wendys_fast_weak_supervised_humor_dataset.csv + wendys_h3_aggressive_vs_other_intensity_dataset.csv',
    'merge_key': 'id',
    'left_n': len(pred_rows),
    'right_fast_n': len(fast_rows),
    'right_h3_n': len(h3_rows),
    'merged_n': len(merged_all),
    'unmatched_n': unmatched,
    'primary_n': len(primary),
    'merge_stable': unmatched == 0 and len(primary) == 597,
}
print(f"  병합 안정성: {merge_info['merge_stable']}")

# ── 2. 후보 변수 목록 ──────────────────────────────────────────────────────────
# 이번 진단에서 사용할 변수 — 모두 기존 컬럼으로 존재하는 것만
CANDIDATES = {
    'final_humor_binary':   'binary_iv',
    'created_year':         'time',
    'created_month':        'time',
    'created_hour':         'time',
    'quarter_total_posts':  'posting_intensity',
    'month_total_posts':    'posting_intensity',
    'text_length':          'post_format',
    'url_count':            'post_format',
    'mention_count':        'post_format',
    'hashtag_count':        'post_format',
    'emoji_count':          'post_format',
    'is_quote_status':      'post_format',
    'is_retweet_text':      'post_format',
    'log1p_view_count':     'exposure_robustness',
}

# ── 3. 변수 기초 진단 ─────────────────────────────────────────────────────────
print("[2] 변수 기초 진단")
varsumm_rows = []

for col, grp in CANDIDATES.items():
    vals_raw_p = [r.get(col, '') for r in primary]
    vals_raw_f = [r.get(col, '') for r in merged_all]

    for sample_label, vals_raw in [('primary_n597', vals_raw_p), ('full_n978', vals_raw_f)]:
        vals_f   = [safe_float(v) for v in vals_raw]
        valid    = [v for v in vals_f if v is not None]
        n_total  = len(vals_raw)
        n_miss   = n_total - len(valid)
        n_zero   = sum(1 for v in valid if v == 0.0)
        unique_n = len(set(vals_raw))

        if valid:
            arr = np.array(valid)
            vmean = float(np.mean(arr))
            vstd  = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            vmin  = float(np.min(arr))
            vmax  = float(np.max(arr))
        else:
            vmean = vstd = vmin = vmax = float('nan')

        miss_rate = round(n_miss / n_total, 4) if n_total > 0 else float('nan')
        zero_rate = round(n_zero / len(valid), 4) if valid else float('nan')

        warnings = []
        if miss_rate > 0.2:   warnings.append('missing_rate>0.2')
        if unique_n <= 1:     warnings.append('unique_n<=1_UNUSABLE')
        if zero_rate > 0.9:   warnings.append('zero_rate>0.9_SPARSE')
        if vstd == 0.0 and valid: warnings.append('std=0_UNUSABLE')

        varsumm_rows.append({
            'variable': col,
            'variable_group': grp,
            'sample': sample_label,
            'n_total': n_total,
            'non_missing_n': len(valid),
            'missing_n': n_miss,
            'missing_rate': miss_rate,
            'unique_n': unique_n,
            'mean': round(vmean, 4) if not math.isnan(vmean) else 'nan',
            'std': round(vstd, 4) if not math.isnan(vstd) else 'nan',
            'min': round(vmin, 4) if not math.isnan(vmin) else 'nan',
            'max': round(vmax, 4) if not math.isnan(vmax) else 'nan',
            'zero_count': n_zero,
            'zero_rate': zero_rate if not (isinstance(zero_rate, float) and math.isnan(zero_rate)) else 'nan',
            'warnings': '; '.join(warnings) if warnings else 'OK',
        })

with open(VARSUMM_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(varsumm_rows[0].keys()))
    w.writeheader(); w.writerows(varsumm_rows)
print(f"  → {VARSUMM_OUT}")

for r in [x for x in varsumm_rows if x['sample']=='primary_n597']:
    print(f"  {r['variable']:30s} miss={r['missing_rate']} zero={r['zero_rate']} std={r['std']} warn={r['warnings']}")

# ── 4. 상관관계 진단 ──────────────────────────────────────────────────────────
print("[3] pairwise 상관관계 진단")

CONT_VARS = ['created_year','created_month','created_hour',
             'quarter_total_posts','month_total_posts',
             'text_length','url_count','mention_count',
             'hashtag_count','emoji_count','log1p_view_count']

# primary sample 기준 numeric 배열 추출
def get_col_arr(col, sample):
    vals = [safe_float(r.get(col,'')) for r in sample]
    return np.array([v if v is not None else float('nan') for v in vals])

corr_rows = []
pairs_checked = []
for i, c1 in enumerate(CONT_VARS):
    for j, c2 in enumerate(CONT_VARS):
        if j <= i: continue
        a1 = get_col_arr(c1, primary)
        a2 = get_col_arr(c2, primary)
        # 둘 다 유효한 행만
        mask = ~(np.isnan(a1) | np.isnan(a2))
        n_valid = int(np.sum(mask))
        if n_valid < 10:
            pearson_r = spearman_r = float('nan')
            pearson_p = spearman_p = float('nan')
        else:
            pearson_r, pearson_p   = stats.pearsonr(a1[mask],  a2[mask])
            spearman_r, spearman_p = stats.spearmanr(a1[mask], a2[mask])

        severity = 'OK'
        if not math.isnan(pearson_r):
            abs_r = abs(pearson_r)
            if abs_r >= 0.90:   severity = 'near_redundancy'
            elif abs_r >= 0.80: severity = 'serious'
            elif abs_r >= 0.70: severity = 'caution'

        corr_rows.append({
            'var1': c1, 'var2': c2,
            'n_valid': n_valid,
            'pearson_r': round(pearson_r, 4) if not math.isnan(pearson_r) else 'nan',
            'pearson_p': round(pearson_p, 4) if not math.isnan(pearson_p) else 'nan',
            'spearman_r': round(spearman_r, 4) if not math.isnan(spearman_r) else 'nan',
            'spearman_p': round(spearman_p, 4) if not math.isnan(spearman_p) else 'nan',
            'severity': severity,
            'sample': 'primary_n597',
        })
        if severity != 'OK':
            pairs_checked.append((c1, c2, pearson_r, severity))

# 강조 페어 출력
print(f"  주목 페어:")
highlighted = [
    ('quarter_total_posts','month_total_posts'),
    ('created_year','quarter_total_posts'),
    ('created_year','month_total_posts'),
    ('created_month','month_total_posts'),
    ('text_length','url_count'),
    ('text_length','mention_count'),
    ('text_length','hashtag_count'),
    ('text_length','emoji_count'),
]
for c1, c2 in highlighted:
    row = next((r for r in corr_rows if (r['var1']==c1 and r['var2']==c2) or
                                         (r['var1']==c2 and r['var2']==c1)), None)
    if row:
        print(f"  {c1:30s} × {c2:30s}: pearson={row['pearson_r']} sev={row['severity']}")

with open(CORR_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(corr_rows[0].keys()))
    w.writeheader(); w.writerows(corr_rows)
print(f"  → {CORR_OUT}")

# ── 5. VIF 계산 ───────────────────────────────────────────────────────────────
print("[4] VIF 계산")

def compute_vif(X):
    """X: (n, p) design matrix (constant 포함). constant 열 제외하여 VIF 계산."""
    n, p = X.shape
    # constant 열 식별 (std=0인 열)
    vifs = []
    for i in range(p):
        xi = X[:, i]
        if np.std(xi) == 0:
            vifs.append(float('inf'))
            continue
        other = np.delete(X, i, axis=1)
        # OLS: xi ~ other
        try:
            XtX = other.T @ other
            if np.linalg.matrix_rank(XtX) < XtX.shape[0]:
                vifs.append(float('inf'))
                continue
            coef = np.linalg.solve(XtX, other.T @ xi)
            xi_hat = other @ coef
            ss_res = float(np.sum((xi - xi_hat)**2))
            ss_tot = float(np.sum((xi - np.mean(xi))**2))
            r2_i = 1 - ss_res/ss_tot if ss_tot > 0 else float('nan')
            if math.isnan(r2_i) or r2_i >= 1.0:
                vifs.append(float('inf'))
            else:
                vifs.append(1/(1 - r2_i))
        except Exception:
            vifs.append(float('inf'))
    return vifs

def condition_number(X):
    """condition number를 column-standardized 행렬 기준으로 계산한다.
    created_year 같은 대형 수치가 constant 열과 상호작용하여
    condition number를 인위적으로 높이는 것을 방지한다."""
    try:
        # constant 열(std=0) 제외하고 나머지만 표준화
        Xs = X.copy().astype(float)
        for j in range(Xs.shape[1]):
            col_std = float(np.std(Xs[:, j], ddof=1))
            if col_std > 0:
                Xs[:, j] = (Xs[:, j] - np.mean(Xs[:, j])) / col_std
        sv = np.linalg.svd(Xs, compute_uv=False)
        if sv[-1] == 0 or np.isnan(sv[-1]):
            return float('inf')
        return float(sv[0] / sv[-1])
    except np.linalg.LinAlgError:
        return float('nan')
    except Exception:
        return float('nan')

def build_design(cols, sample, add_constant=True):
    """지정된 컬럼으로 design matrix를 구성한다.
    is_quote_status, is_retweet_text는 binary 처리.
    created_year, created_month, created_hour는 정수로 처리."""
    arrays = []
    col_labels = []
    for c in cols:
        arr = get_col_arr(c, sample)
        nan_mask = np.isnan(arr)
        if nan_mask.any():
            arr[nan_mask] = float(np.nanmean(arr))
        arrays.append(arr)
        col_labels.append(c)
    X = np.column_stack(arrays) if arrays else np.empty((len(sample), 0))
    if add_constant:
        X = np.column_stack([np.ones(len(sample)), X])
        col_labels = ['_const'] + col_labels
    return X, col_labels

# rank 확인 함수
def rank_check(X, col_labels):
    rank = np.linalg.matrix_rank(X)
    ncols = X.shape[1]
    deficient = rank < ncols
    cond = condition_number(X)
    return rank, ncols, deficient, cond

MODEL_SETS = {
    'A_time_only': [
        'final_humor_binary','created_year','created_month','created_hour'
    ],
    'B_time_posting_intensity': [
        'final_humor_binary','created_year','created_month','created_hour',
        'quarter_total_posts','month_total_posts'
    ],
    'C_time_posting_format': [
        'final_humor_binary','created_year','created_month','created_hour',
        'quarter_total_posts','month_total_posts',
        'text_length','url_count','mention_count','hashtag_count','emoji_count',
        'is_quote_status','is_retweet_text'
    ],
    'D_exposure_robustness': [
        'final_humor_binary','created_year','created_month','created_hour',
        'text_length','log1p_view_count'
    ],
}

vif_rows  = []
cond_rows = []

for mname, cols in MODEL_SETS.items():
    for sample_label, sample in [('primary_n597', primary), ('full_n978', merged_all)]:
        X, col_labels = build_design(cols, sample, add_constant=True)
        rank, ncols, deficient, cond = rank_check(X, col_labels)

        if deficient:
            print(f"  [{mname}][{sample_label}] RANK DEFICIENT: rank={rank}/{ncols} cond={cond:.1f}")
            vif_vals = [float('inf')] * len(col_labels)
        else:
            vif_vals = compute_vif(X)

        cond_sev = 'acceptable' if cond < 30 else ('caution' if cond < 100 else 'serious')
        cond_rows.append({
            'model_set': mname,
            'sample': sample_label,
            'n_rows': len(sample),
            'n_cols_with_const': ncols,
            'rank': rank,
            'rank_deficient': deficient,
            'condition_number': round(cond, 2) if not math.isinf(cond) else 'inf',
            'condition_severity': 'inf' if math.isinf(cond) else cond_sev,
        })

        for cname, vf in zip(col_labels, vif_vals):
            vif_sev = 'acceptable' if vf < 5 else ('caution' if vf < 10 else 'serious')
            if math.isinf(vf): vif_sev = 'infinite_FAIL'
            vif_rows.append({
                'model_set': mname,
                'sample': sample_label,
                'variable': cname,
                'vif': round(vf, 4) if not (math.isinf(vf) or math.isnan(vf)) else ('inf' if math.isinf(vf) else 'nan'),
                'vif_severity': vif_sev,
            })

        # primary sample 주요 결과 출력
        if sample_label == 'primary_n597':
            max_vif_val = max(v for v in vif_vals if not math.isinf(v)) if any(not math.isinf(v) for v in vif_vals) else float('inf')
            max_vif_col = col_labels[vif_vals.index(max(vif_vals, key=lambda v: float('inf') if math.isinf(v) else v))]
            print(f"  [{mname}] rank={rank}/{ncols} deficient={deficient} cond={cond:.1f} max_vif={max_vif_val:.2f}({max_vif_col})")

with open(VIF_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(vif_rows[0].keys()))
    w.writeheader(); w.writerows(vif_rows)
print(f"  → {VIF_OUT}")

with open(COND_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(cond_rows[0].keys()))
    w.writeheader(); w.writerows(cond_rows)
print(f"  → {COND_OUT}")

# ── 6. posts.json 변경 확인 ───────────────────────────────────────────────────
posts_json_modified = False
if HASH_BEFORE:
    try:
        with open(POSTS_JSON, 'rb') as f:
            h2_h = hashlib.md5(f.read()).hexdigest()
        posts_json_modified = (h2_h != HASH_BEFORE)
    except FileNotFoundError:
        pass

# ── 7. Recommendation markdown ────────────────────────────────────────────────
print("[5] Recommendations 작성")

# 주요 VIF 요약 (primary)
primary_vif = [r for r in vif_rows if r['sample']=='primary_n597' and r['variable']!='_const']
primary_cond = [r for r in cond_rows if r['sample']=='primary_n597']

def get_vif(mset, var):
    row = next((r for r in primary_vif if r['model_set']==mset and r['variable']==var), None)
    return row['vif'] if row else 'n/a'

def get_cond(mset):
    row = next((r for r in primary_cond if r['model_set']==mset), None)
    if not row: return 'n/a', 'n/a', 'n/a', 'n/a'
    return row['condition_number'], row['condition_severity'], row['rank_deficient'], row['n_cols_with_const']

# 높은 VIF 변수 찾기
high_vif = [(r['model_set'], r['variable'], r['vif'], r['vif_severity'])
            for r in primary_vif if r['vif_severity'] in ('caution','serious','infinite_FAIL')]
high_vif.sort(key=lambda x: str(x[2]), reverse=True)

# 상관관계 높은 쌍
high_corr = [(r['var1'], r['var2'], r['pearson_r'], r['severity'])
             for r in corr_rows if r['severity'] in ('caution','serious','near_redundancy')]
high_corr.sort(key=lambda x: abs(float(x[2])) if x[2]!='nan' else 0, reverse=True)

# 조합별 cond/vif 테이블
def mset_summary_table(mset):
    cond_n, cond_s, deficient, ncols = get_cond(mset)
    vars_in = [r['variable'] for r in primary_vif if r['model_set']==mset]
    lines = [f"rank_deficient={deficient}, condition_number={cond_n} ({cond_s}), n_cols={ncols}",
             "| variable | VIF | severity |",
             "|---|---|---|"]
    for v in vars_in:
        vf = get_vif(mset, v)
        sev = next((r['vif_severity'] for r in primary_vif if r['model_set']==mset and r['variable']==v), 'n/a')
        lines.append(f"| {v} | {vf} | {sev} |")
    return '\n'.join(lines)

# is_quote_status, is_retweet_text zero_rate 확인
def get_zero_rate(col):
    row = next((r for r in varsumm_rows if r['variable']==col and r['sample']=='primary_n597'), None)
    return row['zero_rate'] if row else 'n/a'

# quarter vs month 상관
qt_mt_corr = next((r for r in corr_rows if (r['var1']=='quarter_total_posts' and r['var2']=='month_total_posts')), None)
yr_qt_corr = next((r for r in corr_rows if (r['var1']=='created_year' and r['var2']=='quarter_total_posts')), None)
yr_mt_corr = next((r for r in corr_rows if (r['var1']=='created_year' and r['var2']=='month_total_posts')), None)
mo_mt_corr = next((r for r in corr_rows if (r['var1']=='created_month' and r['var2']=='month_total_posts')), None)

recom_md = f"""# Wendy's H1 후보 변수 다중공선성 진단 결과

## 1. 진단 목적

H1 controlled regression 실행 전, 기존 데이터에 존재하는 후보 통제변수들 사이의 다중공선성을 사전에 진단한다. 이번 작업에서는 회귀분석을 수행하지 않았으며, 새로운 변수를 생성하지 않았다.

---

## 2. 사용한 파일과 표본

| 항목 | 값 |
|---|---|
| pred 파일 | wendys_final_humor_presence_full_predictions.csv |
| fast 파일 | wendys_fast_weak_supervised_humor_dataset.csv |
| h3 파일 | wendys_h3_aggressive_vs_other_intensity_dataset.csv |
| 병합 key | id |
| 전체 병합 행 | {len(merged_all)} |
| **Primary sample** | **final_humor_label_available=1, n={len(primary)}** |
| Supplemental | 전체 n=978 |

---

## 3. 병합 여부 및 안정성

| 항목 | 값 |
|---|---|
| left n (pred) | {len(pred_rows)} |
| right fast n | {len(fast_rows)} |
| right h3 n | {len(h3_rows)} |
| 전체 merged | {len(merged_all)} |
| unmatched rows | {unmatched} |
| primary n=597 유지 | {len(primary)==597} |
| 병합 안정성 | {'STABLE' if unmatched==0 else 'UNSTABLE'} |

모든 978건이 1:1로 병합되었다. primary sample 597건 유지 확인.

---

## 4. 변수별 결측률·희소성·unique value 진단 (primary n=597)

| variable | missing_rate | zero_rate | std | unique_n | warnings |
|---|---|---|---|---|---|
{"".join(f"| {r['variable']} | {r['missing_rate']} | {r['zero_rate']} | {r['std']} | {r['unique_n']} | {r['warnings']} |{chr(10)}" for r in varsumm_rows if r['sample']=='primary_n597')}

**주목:**
- `is_quote_status` zero_rate = {get_zero_rate('is_quote_status')} (기준 범주 확인 필요)
- `is_retweet_text` zero_rate = {get_zero_rate('is_retweet_text')} (기준 범주 확인 필요)
- `emoji_count` zero_rate = {next((r['zero_rate'] for r in varsumm_rows if r['variable']=='emoji_count' and r['sample']=='primary_n597'), 'n/a')} (희소성 주의)

---

## 5. Pairwise Correlation 주요 결과 (primary n=597, Pearson)

| 변수쌍 | pearson_r | spearman_r | severity |
|---|---|---|---|
{"".join(f"| {r['var1']} × {r['var2']} | {r['pearson_r']} | {r['spearman_r']} | {r['severity']} |{chr(10)}" for r in corr_rows if r['severity'] != 'OK')}

**강조 쌍:**

| 쌍 | pearson_r | severity |
|---|---|---|
| quarter_total_posts × month_total_posts | {qt_mt_corr['pearson_r'] if qt_mt_corr else 'n/a'} | {qt_mt_corr['severity'] if qt_mt_corr else 'n/a'} |
| created_year × quarter_total_posts | {yr_qt_corr['pearson_r'] if yr_qt_corr else 'n/a'} | {yr_qt_corr['severity'] if yr_qt_corr else 'n/a'} |
| created_year × month_total_posts | {yr_mt_corr['pearson_r'] if yr_mt_corr else 'n/a'} | {yr_mt_corr['severity'] if yr_mt_corr else 'n/a'} |
| created_month × month_total_posts | {mo_mt_corr['pearson_r'] if mo_mt_corr else 'n/a'} | {mo_mt_corr['severity'] if mo_mt_corr else 'n/a'} |

---

## 6. VIF 주요 결과 (primary n=597)

### Model Set A: Time controls only
{mset_summary_table('A_time_only')}

### Model Set B: Time + Posting Intensity
{mset_summary_table('B_time_posting_intensity')}

### Model Set C: Time + Posting Intensity + Post Format
{mset_summary_table('C_time_posting_format')}

### Model Set D: Exposure Robustness
{mset_summary_table('D_exposure_robustness')}

---

## 7. Condition Number 및 Rank Deficiency (primary n=597)

| model_set | n_cols | rank | deficient | condition_number | severity |
|---|---|---|---|---|---|
{"".join(f"| {r['model_set']} | {r['n_cols_with_const']} | {r['rank']} | {r['rank_deficient']} | {r['condition_number']} | {r['condition_severity']} |{chr(10)}" for r in primary_cond)}

---

## 8. 다중공선성 위험 변수

{"".join(f"- **{m}** > **{v}**: VIF={vf} ({s}){chr(10)}" for m,v,vf,s in high_vif[:10]) if high_vif else "- 심각한 다중공선성 없음"}

{"".join(f"- **{v1}** × **{v2}**: r={r} ({s}){chr(10)}" for v1,v2,r,s in high_corr[:10]) if high_corr else "- 심각한 상관관계 없음"}

---

## 9. Primary Model에서 사용 가능한 변수 세트

**[사용자 승인 필요]** 다음은 제안이며 확정이 아니다.

```
반드시 유지:
  final_humor_binary       ← H1 핵심 IV
  created_year             ← 시간 추세 통제
  created_hour             ← 시간대 통제
  text_length              ← 게시글 길이 통제
  is_quote_status          ← 포맷 통제 (0 비율 확인 필요)
  is_retweet_text          ← 포맷 통제 (0 비율 확인 필요)
```

```
quarter_total_posts / month_total_posts 중 하나만 선택:
  → VIF 결과와 correlation 기준으로 둘 중 하나만 포함 권장
  → quarter_total_posts: H3와 일관된 period 단위
  → 사용자 선택 필요
```

```
created_month:
  → month_total_posts와 상관 확인 후 결정
  → 필요 시 created_month 제거하고 quarter_total_posts만 유지
```

---

## 10. Robustness Model로만 사용할 변수 세트

```
log1p_view_count:
  → 노출 통제 목적, primary model에서는 제외
  → view_count가 0인 경우 log1p 적용 후 0이 되므로 결측 처리가 아님
  → robustness only

url_count, mention_count, hashtag_count, emoji_count:
  → text_length와 함께 전부 넣을 경우 상관관계 주의
  → 필요 시 text_length 대신 url_count + mention_count 선택 가능
  → 개별 또는 묶음으로 robustness 확인
```

---

## 11. 사용자 승인 필요한 선택지

| 선택지 | 옵션 1 | 옵션 2 | 비고 |
|---|---|---|---|
| posting intensity | quarter_total_posts만 | month_total_posts만 | 둘 다 넣으면 VIF 상승 위험 |
| created_month | 포함 | 제외 | month_total_posts와 상관 확인 |
| text_length vs 개별 format | text_length 단독 | url+mention+hashtag 개별 | text_length 단독 권장 |
| is_quote_status, is_retweet_text | 포함 | 제외 (zero_rate 주의) | 0 비율이 매우 높으면 제외 권장 |
| log1p_view_count | primary 포함 | robustness only | 노출 통제 필요성 선택 |
| created_year vs created_month | 둘 다 | created_year만 | 동시 포함 시 VIF 확인 |

---

## 12. 회귀분석 수행 여부

이번 작업에서는 H1 회귀분석을 수행하지 않았다.

---

## 13. 새 변수 생성 여부

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 컬럼으로 존재하는 변수만 사용하였다. day_of_week, has_url 등 텍스트 파생 변수는 생성하지 않았다.

---

## 14. 원본 posts.json 변경 없음 확인

`data/wendys/posts.json` 변경 여부: {posts_json_modified}

---

*생성일: 2026-06-15*
"""

with open(RECOM_OUT, 'w', encoding='utf-8') as f:
    f.write(recom_md)
print(f"  → {RECOM_OUT}")
print(f"\n[완료] posts.json 변경={posts_json_modified}, 회귀분석=False, 새변수생성=False")
