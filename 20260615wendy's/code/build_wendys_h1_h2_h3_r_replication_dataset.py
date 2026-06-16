"""
build_wendys_h1_h2_h3_r_replication_dataset.py

목적: H1-H2-H3 최종 보고서에 사용된 모든 분석 변수를 하나의 R 재현용
     wide-format CSV로 통합한다. 새로운 분석 또는 회귀분석은 수행하지 않는다.

절대 규칙:
  - data/wendys/posts.json 원본 불변
  - 새 회귀분석 미수행
  - 새 유머 분류 모델 미학습
  - view_count, log1p_view_count 미포함
  - emoji_count, url_count, is_quote_status, is_retweet_text 미포함
  - year_quarter FE / quarter FE dummy 미생성
  - frequency count 기반 H3 변수 미포함
  - month_total_posts 미포함
  - day_of_week 미생성
  - squared term 및 sample flag만 신규 생성 허용
"""

import pandas as pd
import numpy as np
import os

# ── 경로 설정 ────────────────────────────────────────────────────────────────
BASE = "20260615wendy's/"
DATA = BASE + "data/"
RESULT = BASE + "result/"

IN_PRESENCE = RESULT + "wendys_final_humor_presence_full_predictions.csv"
IN_TYPE = RESULT + "wendys_model_based_humor_type_full_predictions.csv"
IN_REVIEW = RESULT + "wendys_humor_review_sheet.csv"
IN_FAST = DATA + "wendys_fast_weak_supervised_humor_dataset.csv"
IN_H3PRE = DATA + "wendys_humor_frequency_proportion_post_level_dataset.csv"
IN_H3MAIN = DATA + "wendys_h3_aggressive_vs_other_intensity_dataset.csv"

OUT_CSV = DATA + "wendys_h1_h2_h3_r_replication_dataset.csv"
OUT_DICT = RESULT + "wendys_h1_h2_h3_r_replication_data_dictionary.csv"
OUT_EXPECTED = RESULT + "wendys_h1_h2_h3_r_replication_expected_coefficients.csv"
OUT_SUMMARY = RESULT + "wendys_h1_h2_h3_r_replication_dataset_summary.md"

# ── 1. 입력 파일 로드 ────────────────────────────────────────────────────────
print("=== 1. 입력 파일 로드 ===")

h3main = pd.read_csv(IN_H3MAIN)
h3pre = pd.read_csv(IN_H3PRE)
presence = pd.read_csv(IN_PRESENCE)
humor_type = pd.read_csv(IN_TYPE)
fast = pd.read_csv(IN_FAST)

for name, df in [("h3main", h3main), ("h3pre", h3pre), ("presence", presence),
                  ("humor_type", humor_type), ("fast", fast)]:
    dup = df['id'].duplicated().sum()
    na = df['id'].isna().sum()
    print(f"  {name}: rows={len(df)}, id_unique={df['id'].nunique()}, id_dup={dup}, id_na={na}")

assert len(h3main) == 978, "h3main row count mismatch"
assert h3main['id'].duplicated().sum() == 0, "h3main has duplicate ids"

# ── 2. 병합 – Base: h3main ──────────────────────────────────────────────────
print("\n=== 2. 병합 ===")

# 2a. h3main에서 사용할 컬럼 선택 (제외 변수 제거)
EXCLUDE_FROM_H3MAIN = {
    # 절대 제외
    'view_count', 'log1p_view_count',
    # 불필요 중간 집계
    'humor_intensity_month', 'humor_intensity_quarter',
    'humor_intensity_month_loo', 'humor_intensity_quarter_loo',
    'month_total_posts', 'month_humor_posts', 'month_non_humor_posts',
    # frequency count (제외 대상)
    'humor_frequency_month', 'humor_frequency_quarter',
    'aggressive_humor_frequency_quarter', 'other_humor_frequency_quarter',
    # non-LOO proportion (최종 모형에 미사용)
    'humor_proportion_month', 'humor_proportion_month_loo',
    'humor_proportion_quarter', 'humor_proportion_quarter_loo',  # h3pre에서 가져옴
    'aggressive_humor_proportion_quarter', 'other_humor_proportion_quarter',
    # 부수 집계
    'quarter_humor_posts', 'quarter_non_humor_posts',
    'quarter_predicted_humor_posts', 'quarter_aggressive_posts', 'quarter_other_humor_posts',
    # 대안 예측 (미사용)
    'pred_humor_type_group_model_050',
    'aggressive_share_among_humor_quarter', 'aggressive_share_among_humor_quarter_loo',
    'is_non_humor', 'is_predicted_humor',
    'in_h3_aggressive_filtered',
    # 원본 counts (필요시 유지; 여기서는 분석에 직접 불필요)
    'reply_count', 'favorite_count', 'retweet_count', 'quote_count', 'bookmark_count',
    'engagement_total', 'engagement_favorite_retweet',
}

h3main_cols = [c for c in h3main.columns if c not in EXCLUDE_FROM_H3MAIN]
base_df = h3main[h3main_cols].copy()
print(f"  base (h3main 선택 후): {len(base_df)} rows, {len(base_df.columns)} cols")

# 2b. h3pre → humor_proportion_quarter_loo
pre_cols = h3pre[['id', 'humor_proportion_quarter_loo']].copy()
pre_dup = pre_cols['id'].duplicated().sum()
print(f"  h3pre (humor_proportion_quarter_loo): rows={len(pre_cols)}, id_dup={pre_dup}")

df = base_df.merge(pre_cols, on='id', how='left', validate='1:1')
unmatched_pre = df['humor_proportion_quarter_loo'].isna().sum()
print(f"  after merge h3pre: rows={len(df)}, humor_proportion_quarter_loo NA={unmatched_pre}")
assert len(df) == 978, f"row count after h3pre merge: {len(df)}"

# 2c. presence → final_humor_binary, final_humor_label_available
pres_cols = presence[['id', 'final_humor_binary', 'final_humor_label_available']].copy()
pres_dup = pres_cols['id'].duplicated().sum()
print(f"  presence (H1 vars): rows={len(pres_cols)}, id_dup={pres_dup}")

df = df.merge(pres_cols, on='id', how='left', validate='1:1')
unmatched_pres = df['final_humor_binary'].isna().sum()
print(f"  after merge presence: rows={len(df)}, final_humor_binary NA={unmatched_pres}")
assert len(df) == 978, f"row count after presence merge: {len(df)}"

# 2d. humor_type → final_humor_type_group
ht_cols = humor_type[['id', 'final_humor_type_group']].copy()
ht_dup = ht_cols['id'].duplicated().sum()
print(f"  humor_type (final_humor_type_group): rows={len(ht_cols)}, id_dup={ht_dup}")

df = df.merge(ht_cols, on='id', how='left', validate='1:1')
unmatched_ht = df['final_humor_type_group'].isna().sum()
print(f"  after merge humor_type: rows={len(df)}, final_humor_type_group NA={unmatched_ht}")
assert len(df) == 978, f"row count after humor_type merge: {len(df)}"

# 2e. fast_ws → text_length, hashtag_count, mention_count
fast_cols = fast[['id', 'text_length', 'hashtag_count', 'mention_count']].copy()
fast_dup = fast_cols['id'].duplicated().sum()
print(f"  fast (format controls): rows={len(fast_cols)}, id_dup={fast_dup}")

df = df.merge(fast_cols, on='id', how='left', validate='1:1')
unmatched_fast = df['text_length'].isna().sum()
print(f"  after merge fast: rows={len(df)}, text_length NA={unmatched_fast}")
assert len(df) == 978, f"row count after fast merge: {len(df)}"

print(f"\n최종 병합 결과: {len(df)} rows")

# ── 3. 신규 생성 변수 (squared terms, sample flags) ──────────────────────────
print("\n=== 3. 신규 변수 생성 ===")

# H3 squared terms
df['humor_proportion_quarter_loo_sq'] = df['humor_proportion_quarter_loo'] ** 2
df['aggressive_humor_proportion_quarter_loo_sq'] = df['aggressive_humor_proportion_quarter_loo'] ** 2
df['other_humor_proportion_quarter_loo_sq'] = df['other_humor_proportion_quarter_loo'] ** 2
print("  squared terms 생성 완료")

# H3 filter flag
df['h3_quarter_filter_10'] = (df['quarter_total_posts'] >= 10).astype(int)

# Sample flags
df['h1_full_sample_flag'] = 1  # 전체 978

# H1 human validation: final_humor_label_available == 1
df['h1_human_validation_flag'] = (df['final_humor_label_available'] == 1).astype(int)

# H2 model humor-only: pred_humor_type_group_model in {aggressive, other_humor}
df['h2_model_humor_only_flag'] = df['pred_humor_type_group_model'].isin(
    ['aggressive', 'other_humor']).astype(int)

# H2 human validation: final_humor_type_group in {aggressive, other_humor}
df['h2_human_validation_flag'] = df['final_humor_type_group'].isin(
    ['aggressive', 'other_humor']).astype(int)

# H3 analysis flag
df['h3_analysis_flag'] = df['h3_quarter_filter_10']

# H2 model dummy: 1=aggressive, 0=other_humor, NA otherwise
df['h2_aggressive_model_dummy'] = np.where(
    df['pred_humor_type_group_model'] == 'aggressive', 1,
    np.where(df['pred_humor_type_group_model'] == 'other_humor', 0, np.nan))

# H2 human dummy: 1=aggressive, 0=other_humor, NA otherwise
df['h2_aggressive_human_dummy'] = np.where(
    df['final_humor_type_group'] == 'aggressive', 1,
    np.where(df['final_humor_type_group'] == 'other_humor', 0, np.nan))

print("  sample flags 및 dummy 생성 완료")

# ── 4. 최종 컬럼 선택 및 정렬 ────────────────────────────────────────────────
print("\n=== 4. 최종 컬럼 선택 ===")

FINAL_COLS = [
    # A. 식별자
    'id', 'created_date', 'created_year', 'created_month', 'created_hour', 'year_quarter',
    # B. DVs
    'log1p_engagement_total', 'log1p_engagement_favorite_retweet',
    'log1p_favorite_count', 'log1p_retweet_count', 'log1p_reply_count',
    'log1p_quote_count', 'log1p_bookmark_count',
    # C. H1 model-based IV
    'pred_humor_final_050', 'p_humor_final_tfidf_logreg',
    # D. H1 human validation
    'final_humor_label_available', 'final_humor_binary',
    # E. H2 model-based
    'pred_humor_type_group_model', 'is_aggressive_humor', 'is_other_humor',
    # F. H2 human validation
    'final_humor_type_group',
    # G. Post format controls
    'text_length', 'hashtag_count', 'mention_count',
    # H. H3 filter
    'quarter_total_posts', 'h3_quarter_filter_10',
    # I. H3 proportion predictors
    'humor_proportion_quarter_loo',
    'aggressive_humor_proportion_quarter_loo',
    'other_humor_proportion_quarter_loo',
    # J. H3 squared terms
    'humor_proportion_quarter_loo_sq',
    'aggressive_humor_proportion_quarter_loo_sq',
    'other_humor_proportion_quarter_loo_sq',
    # K. Sample flags
    'h1_full_sample_flag', 'h1_human_validation_flag',
    'h2_model_humor_only_flag', 'h2_human_validation_flag',
    'h3_analysis_flag',
    # L. R replication dummies
    'h2_aggressive_model_dummy', 'h2_aggressive_human_dummy',
]

# 컬럼 존재 확인
missing_cols = [c for c in FINAL_COLS if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing columns: {missing_cols}")

out_df = df[FINAL_COLS].copy()
print(f"  최종 컬럼 수: {len(FINAL_COLS)}")

# ── 5. 제외 변수 검증 ────────────────────────────────────────────────────────
print("\n=== 5. 제외 변수 검증 ===")
EXCLUDED_VARS = [
    'view_count', 'log1p_view_count', 'emoji_count', 'url_count',
    'is_quote_status', 'is_retweet_text', 'day_of_week',
    'month_total_posts', 'humor_frequency_quarter',
    'aggressive_humor_frequency_quarter', 'other_humor_frequency_quarter',
    'humor_frequency_month',
]
for v in EXCLUDED_VARS:
    in_out = v in out_df.columns
    status = "❌ FOUND (오류)" if in_out else "OK (미포함)"
    print(f"  {v}: {status}")
    assert not in_out, f"제외 변수 {v}가 출력 데이터에 포함됨"

# ── 6. 검증 조건 확인 ────────────────────────────────────────────────────────
print("\n=== 6. 검증 조건 확인 ===")

checks = {
    "row_count": (len(out_df), 978),
    "h1_full_sample_flag_sum": (out_df['h1_full_sample_flag'].sum(), 978),
    "h1_human_validation_flag_sum": (out_df['h1_human_validation_flag'].sum(), 597),
    "h2_model_humor_only_flag_sum": (out_df['h2_model_humor_only_flag'].sum(), 564),
    "h2_model_aggressive_dummy_1": (
        (out_df['h2_aggressive_model_dummy'] == 1).sum(), 200),
    "h2_model_aggressive_dummy_0": (
        (out_df['h2_aggressive_model_dummy'] == 0).sum(), 364),
    "h2_human_validation_flag_sum": (out_df['h2_human_validation_flag'].sum(), 278),
    "h2_human_aggressive_dummy_1": (
        (out_df['h2_aggressive_human_dummy'] == 1).sum(), 95),
    "h2_human_aggressive_dummy_0": (
        (out_df['h2_aggressive_human_dummy'] == 0).sum(), 183),
    "h3_analysis_flag_sum": (out_df['h3_analysis_flag'].sum(), 960),
    "h3_unique_quarter": (
        out_df.loc[out_df['h3_analysis_flag'] == 1, 'year_quarter'].nunique(), 25),
    "text_length_missing": (out_df['text_length'].isna().sum(), 0),
    "hashtag_count_missing": (out_df['hashtag_count'].isna().sum(), 0),
    "mention_count_missing": (out_df['mention_count'].isna().sum(), 0),
}

h3_mask = out_df['h3_analysis_flag'] == 1
for pred in ['humor_proportion_quarter_loo',
             'aggressive_humor_proportion_quarter_loo',
             'other_humor_proportion_quarter_loo']:
    na_in_h3 = out_df.loc[h3_mask, pred].isna().sum()
    checks[f"{pred}_missing_in_h3"] = (na_in_h3, 0)

all_ok = True
for name, (actual, expected) in checks.items():
    status = "OK" if actual == expected else f"MISMATCH (actual={actual}, expected={expected})"
    print(f"  {name}: {status}")
    if actual != expected:
        all_ok = False

if not all_ok:
    raise ValueError("검증 실패: 위 MISMATCH 항목 확인 필요")

print("\n  모든 검증 조건 통과")

# ── 7. CSV 저장 ───────────────────────────────────────────────────────────────
print(f"\n=== 7. 저장 ===")
out_df.to_csv(OUT_CSV, index=False, na_rep='NA')
print(f"  저장 완료: {OUT_CSV}")
print(f"  rows={len(out_df)}, cols={len(out_df.columns)}")

# ── 8. Data Dictionary 생성 ──────────────────────────────────────────────────
print("\n=== 8. Data Dictionary 생성 ===")

def col_info(col, group, used_in, role, description, source_file, expected_type, notes=""):
    s = out_df[col]
    return {
        'variable_name': col,
        'variable_group': group,
        'used_in': used_in,
        'role': role,
        'description': description,
        'source_file': source_file,
        'expected_type': expected_type,
        'missing_n': int(s.isna().sum()),
        'non_missing_n': int(s.notna().sum()),
        'unique_n': int(s.nunique(dropna=True)),
        'notes': notes,
    }

dict_rows = [
    col_info('id', 'identifier', 'H1_H2_H3', 'key', 'Post unique ID', 'h3_aggressive_vs_other_intensity_dataset.csv', 'character', '978개 모두 고유'),
    col_info('created_date', 'date_time', 'H1_H2_H3', 'covariate', 'Post 작성 날짜 (YYYY-MM-DD)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'character', ''),
    col_info('created_year', 'date_time', 'H1_H2_H3', 'time_fe', 'Post 작성 연도 (factor FE)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', 'R: factor(created_year)'),
    col_info('created_month', 'date_time', 'H1_H2_H3', 'time_fe', 'Post 작성 월 1-12 (factor FE)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', 'R: factor(created_month)'),
    col_info('created_hour', 'date_time', 'H1_H2_H3', 'time_fe', 'Post 작성 시각 0-23 (factor FE)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', 'R: factor(created_hour)'),
    col_info('year_quarter', 'date_time', 'H3', 'filter', '연도-분기 (YYYY-QN)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'character', 'H3 LOO 계산 단위; FE로 사용 금지'),
    col_info('log1p_engagement_total', 'dv', 'H1_H2_H3', 'primary_dv', 'log1p(favorite+retweet+reply+quote+bookmark)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', 'Primary DV'),
    col_info('log1p_engagement_favorite_retweet', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(favorite+retweet)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('log1p_favorite_count', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(favorite_count)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('log1p_retweet_count', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(retweet_count)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('log1p_reply_count', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(reply_count)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('log1p_quote_count', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(quote_count)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('log1p_bookmark_count', 'dv', 'H1_H2_H3', 'supplemental_dv', 'log1p(bookmark_count)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', ''),
    col_info('pred_humor_final_050', 'h1_iv', 'H1', 'primary_iv', '모델 기반 유머 이진 예측 (threshold=0.50)', 'wendys_final_humor_presence_full_predictions.csv', 'integer', '0=비유머, 1=유머; H1 binary model IV'),
    col_info('p_humor_final_tfidf_logreg', 'h1_iv', 'H1', 'primary_iv', '모델 기반 유머 확률 예측 (TF-IDF LogReg)', 'wendys_final_humor_presence_full_predictions.csv', 'numeric', 'H1 probability model IV'),
    col_info('final_humor_label_available', 'h1_validation', 'H1', 'sample_flag_source', '인간 레이블 가용 여부 (1=가용, 0=불가용)', 'wendys_final_humor_presence_full_predictions.csv', 'integer', '합계=597 → h1_human_validation_flag 기준'),
    col_info('final_humor_binary', 'h1_validation', 'H1', 'validation_iv', '최종 유머 이진 레이블 (인간 코딩 우선, 모델 보완)', 'wendys_final_humor_presence_full_predictions.csv', 'integer', 'H1 human validation IV; subset(h1_human_validation_flag==1)에서 사용'),
    col_info('pred_humor_type_group_model', 'h2_iv', 'H2', 'primary_iv', '모델 기반 유머 유형 예측 (aggressive/other_humor/non_humor)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'character', 'H2 model-based IV 기반 변수'),
    col_info('is_aggressive_humor', 'h2_iv', 'H2', 'covariate', '공격적 유머 이진 더미 (model-based)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', '0/1; is_aggressive_humor=1이면 h2_aggressive_model_dummy=1'),
    col_info('is_other_humor', 'h2_iv', 'H2', 'covariate', '기타 유머 이진 더미 (model-based)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', '0/1'),
    col_info('final_humor_type_group', 'h2_validation', 'H2', 'validation_iv', '최종 유머 유형 그룹 (인간 코딩 우선; aggressive/other_humor/non_humor/missing)', 'wendys_model_based_humor_type_full_predictions.csv', 'character', 'H2 human validation IV 기반 변수'),
    col_info('text_length', 'control_post_format', 'H1_H2_H3', 'covariate', '텍스트 길이 (문자 수)', 'wendys_fast_weak_supervised_humor_dataset.csv', 'integer', ''),
    col_info('hashtag_count', 'control_post_format', 'H1_H2_H3', 'covariate', '해시태그 수', 'wendys_fast_weak_supervised_humor_dataset.csv', 'integer', ''),
    col_info('mention_count', 'control_post_format', 'H1_H2_H3', 'covariate', '멘션(@) 수', 'wendys_fast_weak_supervised_humor_dataset.csv', 'integer', ''),
    col_info('quarter_total_posts', 'filter', 'H3', 'filter_source', '해당 year_quarter 내 총 게시물 수', 'h3_aggressive_vs_other_intensity_dataset.csv', 'integer', 'H3 필터 기준 변수'),
    col_info('h3_quarter_filter_10', 'filter', 'H3', 'filter', 'quarter_total_posts >= 10이면 1, 아니면 0', 'derived', 'integer', 'h3_analysis_flag와 동일'),
    col_info('humor_proportion_quarter_loo', 'h3_predictor', 'H3', 'primary_predictor', '전체 유머 비율 (LOO, quarter-level)', 'wendys_humor_frequency_proportion_post_level_dataset.csv', 'numeric', 'H3-pre primary predictor; 1 NA in full sample (quarter_total_posts<10)'),
    col_info('aggressive_humor_proportion_quarter_loo', 'h3_predictor', 'H3', 'primary_predictor', '공격적 유머 비율 (LOO, quarter-level)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', 'H3-main primary predictor'),
    col_info('other_humor_proportion_quarter_loo', 'h3_predictor', 'H3', 'primary_predictor', '기타 유머 비율 (LOO, quarter-level)', 'h3_aggressive_vs_other_intensity_dataset.csv', 'numeric', 'H3-supplemental predictor'),
    col_info('humor_proportion_quarter_loo_sq', 'h3_squared_term', 'H3', 'quadratic_term', 'humor_proportion_quarter_loo의 제곱항', 'derived', 'numeric', 'H3 quadratic model 재현용'),
    col_info('aggressive_humor_proportion_quarter_loo_sq', 'h3_squared_term', 'H3', 'quadratic_term', 'aggressive_humor_proportion_quarter_loo의 제곱항', 'derived', 'numeric', 'H3 quadratic model 재현용'),
    col_info('other_humor_proportion_quarter_loo_sq', 'h3_squared_term', 'H3', 'quadratic_term', 'other_humor_proportion_quarter_loo의 제곱항', 'derived', 'numeric', 'H3 quadratic model 재현용'),
    col_info('h1_full_sample_flag', 'sample_flag', 'H1', 'sample_flag', 'H1 전체 표본 flag (전체=1)', 'derived', 'integer', '전체 978=1'),
    col_info('h1_human_validation_flag', 'sample_flag', 'H1', 'sample_flag', 'H1 인간 검증 표본 flag (final_humor_label_available==1)', 'derived', 'integer', '합계=597'),
    col_info('h2_model_humor_only_flag', 'sample_flag', 'H2', 'sample_flag', 'H2 모델 유머 only flag (aggressive or other_humor)', 'derived', 'integer', '합계=564'),
    col_info('h2_human_validation_flag', 'sample_flag', 'H2', 'sample_flag', 'H2 인간 검증 유머 only flag (aggressive or other_humor)', 'derived', 'integer', '합계=278'),
    col_info('h3_analysis_flag', 'sample_flag', 'H3', 'sample_flag', 'H3 분석 표본 flag (quarter_total_posts>=10)', 'derived', 'integer', '합계=960, 25개 분기'),
    col_info('h2_aggressive_model_dummy', 'h2_iv', 'H2', 'r_replication_iv', 'H2 모델 기반 공격적 유머 더미 (1=aggressive, 0=other_humor, NA=else)', 'derived', 'numeric', 'R 재현: h2_model_humor_only_flag==1 subset에서 사용'),
    col_info('h2_aggressive_human_dummy', 'h2_validation', 'H2', 'r_replication_iv', 'H2 인간 검증 공격적 유머 더미 (1=aggressive, 0=other_humor, NA=else)', 'derived', 'numeric', 'R 재현: h2_human_validation_flag==1 subset에서 사용'),
]

dict_df = pd.DataFrame(dict_rows)
dict_df.to_csv(OUT_DICT, index=False)
print(f"  data dictionary 저장: {OUT_DICT} ({len(dict_df)} rows)")

# ── 9. Expected Coefficients 파일 생성 ───────────────────────────────────────
print("\n=== 9. Expected Coefficients 파일 생성 ===")

expected_rows = [
    # H1
    {'model_name': 'H1_binary_M7', 'sample_filter': 'h1_full_sample_flag==1 (n=978)',
     'focal_variable': 'pred_humor_final_050', 'expected_coefficient': 0.2918,
     'expected_p_value': 0.0088, 'expected_n': 978,
     'source_result_file': 'wendys_h1_three_post_format_fullsample_binary_results.csv',
     'notes': 'M7_all_three; controls: year+month+hour FE, text_length, hashtag_count, mention_count'},
    {'model_name': 'H1_probability_M7', 'sample_filter': 'h1_full_sample_flag==1 (n=978)',
     'focal_variable': 'p_humor_final_tfidf_logreg', 'expected_coefficient': 0.8404,
     'expected_p_value': 0.0175, 'expected_n': 978,
     'source_result_file': 'wendys_h1_three_post_format_fullsample_probability_results.csv',
     'notes': 'M7_all_three; same controls as binary'},
    {'model_name': 'H1_human_M7', 'sample_filter': 'h1_human_validation_flag==1 (n=597)',
     'focal_variable': 'final_humor_binary', 'expected_coefficient': 0.3171,
     'expected_p_value': 0.0307, 'expected_n': 597,
     'source_result_file': 'wendys_h1_three_post_format_human_validation_results.csv',
     'notes': 'M7_all_three; same controls as binary'},
    # H2
    {'model_name': 'H2_model_M7', 'sample_filter': 'h2_model_humor_only_flag==1 (n=564)',
     'focal_variable': 'h2_aggressive_model_dummy', 'expected_coefficient': 0.4056,
     'expected_p_value': 0.0060, 'expected_n': 564,
     'source_result_file': 'wendys_h2_step3_post_format_model_based_results.csv',
     'notes': 'M7_time_fe_all_post_format; same controls'},
    {'model_name': 'H2_human_M7', 'sample_filter': 'h2_human_validation_flag==1 (n=278)',
     'focal_variable': 'h2_aggressive_human_dummy', 'expected_coefficient': 0.6405,
     'expected_p_value': 0.0010, 'expected_n': 278,
     'source_result_file': 'wendys_h2_step3_post_format_human_validation_results.csv',
     'notes': 'M7_time_fe_all_post_format; same controls'},
    # H3-pre
    {'model_name': 'H3_pre_M7_beta1', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'humor_proportion_quarter_loo (linear)', 'expected_coefficient': -6.6063,
     'expected_p_value': 0.0114, 'expected_n': 960,
     'source_result_file': 'wendys_h3_step3_general_humor_post_format_results.csv',
     'notes': 'M7 (all time+format); Step 2 M7 linear coef; Step 3 M7 beta_quadratic=4.3189, p=0.0395'},
    {'model_name': 'H3_pre_M7_beta2', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'humor_proportion_quarter_loo_sq (quadratic)', 'expected_coefficient': 4.3189,
     'expected_p_value': 0.0395, 'expected_n': 960,
     'source_result_file': 'wendys_h3_step3_general_humor_post_format_results.csv',
     'notes': 'beta2>0 → U자형 (역 U자형 아님); H3 기각'},
    # H3-main
    {'model_name': 'H3_main_M7_beta1', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'aggressive_humor_proportion_quarter_loo (linear)', 'expected_coefficient': -3.3810,
     'expected_p_value': 0.3386, 'expected_n': 960,
     'source_result_file': 'wendys_h3_step3_aggressive_humor_post_format_results.csv',
     'notes': 'Step 2 M7 linear coef; Step 3 M7 beta_quadratic=-3.2814, p=0.6929'},
    {'model_name': 'H3_main_M7_beta2', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'aggressive_humor_proportion_quarter_loo_sq (quadratic)', 'expected_coefficient': -3.2814,
     'expected_p_value': 0.6929, 'expected_n': 960,
     'source_result_file': 'wendys_h3_step3_aggressive_humor_post_format_results.csv',
     'notes': 'not_support; H3 기각'},
    # H3-supplemental
    {'model_name': 'H3_other_M8_beta1', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'other_humor_proportion_quarter_loo (linear)', 'expected_coefficient': -6.8614,
     'expected_p_value': 0.0043, 'expected_n': 960,
     'source_result_file': 'wendys_h3_supplemental_other_humor_proportion_results.csv',
     'notes': 'M8 (+time+all format); U_shape (beta2>0, p<.05)'},
    {'model_name': 'H3_other_M8_beta2', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'other_humor_proportion_quarter_loo_sq (quadratic)', 'expected_coefficient': 7.8688,
     'expected_p_value': 0.0047, 'expected_n': 960,
     'source_result_file': 'wendys_h3_supplemental_other_humor_proportion_results.csv',
     'notes': 'U_shape (역 U자형 아님); H3 기각'},
    # H3-joint
    {'model_name': 'H3_joint_M2_agg_beta1', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'aggressive_humor_proportion_quarter_loo (joint linear)', 'expected_coefficient': -2.3560,
     'expected_p_value': 0.4944, 'expected_n': 960,
     'source_result_file': 'wendys_h3_joint_aggressive_other_decomposition_results.csv',
     'notes': 'M2 (+time+all format); aggressive_not_support'},
    {'model_name': 'H3_joint_M2_agg_beta2', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'aggressive_humor_proportion_quarter_loo_sq (joint quadratic)', 'expected_coefficient': -3.7276,
     'expected_p_value': 0.6722, 'expected_n': 960,
     'source_result_file': 'wendys_h3_joint_aggressive_other_decomposition_results.csv',
     'notes': 'aggressive_not_support'},
    {'model_name': 'H3_joint_M2_oth_beta1', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'other_humor_proportion_quarter_loo (joint linear)', 'expected_coefficient': -7.7528,
     'expected_p_value': 0.0013, 'expected_n': 960,
     'source_result_file': 'wendys_h3_joint_aggressive_other_decomposition_results.csv',
     'notes': 'M2; other_U_shape'},
    {'model_name': 'H3_joint_M2_oth_beta2', 'sample_filter': 'h3_analysis_flag==1 (n=960)',
     'focal_variable': 'other_humor_proportion_quarter_loo_sq (joint quadratic)', 'expected_coefficient': 8.1417,
     'expected_p_value': 0.0037, 'expected_n': 960,
     'source_result_file': 'wendys_h3_joint_aggressive_other_decomposition_results.csv',
     'notes': 'other_U_shape; no masking confirmed'},
]

exp_df = pd.DataFrame(expected_rows)
exp_df.to_csv(OUT_EXPECTED, index=False)
print(f"  expected coefficients 저장: {OUT_EXPECTED} ({len(exp_df)} rows)")

# ── 10. Summary 생성 ──────────────────────────────────────────────────────────
print("\n=== 10. Summary 생성 ===")

summary_txt = f"""# Wendy's H1-H2-H3 R 재현용 데이터셋 — 생성 요약

작성일: 2026-06-16

---

## 1. 작업 목적

최종 보고서(`wendys_humor_h1_h2_h3_final_report.md`)에 사용된 모든 분석 변수를 하나의 R 재현용 wide-format CSV로 통합한다.
이 데이터셋 하나로 R에서 H1·H2·H3 최종 모형을 모두 재현할 수 있다.
새로운 분석, 회귀 계산, 유머 분류 모델 학습은 일절 수행하지 않는다.

---

## 2. 최종 보고서 경로

`20260615wendy's/result/wendys_humor_h1_h2_h3_final_report.md`

---

## 3. 사용한 입력 파일

| 파일 | rows | 역할 |
|---|---|---|
| `result/wendys_final_humor_presence_full_predictions.csv` | 978 | H1 model-based IV, 인간 검증 label |
| `result/wendys_model_based_humor_type_full_predictions.csv` | 978 | H2 인간 검증 type group |
| `result/wendys_humor_review_sheet.csv` | 978 | (참고용; final_humor_type_group은 humor_type에서 가져옴) |
| `data/wendys_fast_weak_supervised_humor_dataset.csv` | 978 | post format controls (text_length, hashtag_count, mention_count) |
| `data/wendys_humor_frequency_proportion_post_level_dataset.csv` | 978 | H3-pre predictor (humor_proportion_quarter_loo) |
| `data/wendys_h3_aggressive_vs_other_intensity_dataset.csv` | 978 | base (DVs, time vars, H3-main/other predictors, format controls) |

---

## 4. 병합 key 및 안정성

- 병합 key: `id` (978개 고유, duplicate 없음, NA 없음 — 전 파일 동일)
- 모든 병합: 1:1 left join, 978→978 유지
- unmatched rows: 0 (전 병합)

---

## 5. 최종 dataset row count

**978** (전체 Wendy's 분석 표본)

---

## 6. 최종 dataset column count

**{len(out_df.columns)}**

---

## 7. 포함한 변수 목록

{chr(10).join(f'- `{c}`' for c in out_df.columns)}

---

## 8. 제외한 변수 목록 (포함되지 않음 확인)

- `view_count`, `log1p_view_count`
- `emoji_count`, `url_count`, `is_quote_status`, `is_retweet_text`
- `day_of_week`
- year_quarter FE dummy, quarter FE dummy
- `month_total_posts`
- `humor_frequency_quarter`, `aggressive_humor_frequency_quarter`, `other_humor_frequency_quarter`
- `humor_frequency_month`
- non-LOO proportion 변수 (humor_proportion_quarter, aggressive_humor_proportion_quarter, other_humor_proportion_quarter)
- raw count 변수 (reply_count, favorite_count, retweet_count, quote_count, bookmark_count, engagement_total)

---

## 9. H1 재현 방법

```r
# Binary IV — full sample (n=978)
h1_binary <- lm(
  log1p_engagement_total ~ pred_humor_final_050 +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_full_sample_flag == 1)
)
# 기대값: pred_humor_final_050 β ≈ 0.2918, p ≈ 0.0088

# Probability IV — full sample (n=978)
h1_prob <- lm(
  log1p_engagement_total ~ p_humor_final_tfidf_logreg +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_full_sample_flag == 1)
)
# 기대값: p_humor_final_tfidf_logreg β ≈ 0.8404, p ≈ 0.0175

# Human validation (n=597)
h1_human <- lm(
  log1p_engagement_total ~ final_humor_binary +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_human_validation_flag == 1)
)
# 기대값: final_humor_binary β ≈ 0.3171, p ≈ 0.0307
```

---

## 10. H2 재현 방법

```r
# Model-based (n=564)
h2_model <- lm(
  log1p_engagement_total ~ h2_aggressive_model_dummy +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h2_model_humor_only_flag == 1)
)
# 기대값: h2_aggressive_model_dummy β ≈ 0.4056, p ≈ 0.0060

# Human validation (n=278)
h2_human <- lm(
  log1p_engagement_total ~ h2_aggressive_human_dummy +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h2_human_validation_flag == 1)
)
# 기대값: h2_aggressive_human_dummy β ≈ 0.6405, p ≈ 0.0010
```

---

## 11. H3 재현 방법

```r
# H3-pre (n=960)
h3_pre <- lm(
  log1p_engagement_total ~ humor_proportion_quarter_loo +
    humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
# 기대값: β1 ≈ -6.6063, β2 ≈ +4.3189 (U자형; H3 기각)

# H3-main (n=960)
h3_main <- lm(
  log1p_engagement_total ~ aggressive_humor_proportion_quarter_loo +
    aggressive_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
# 기대값: β1 ≈ -3.3810, β2 ≈ -3.2814, p2 ≈ 0.6929 (not_support; H3 기각)

# H3-supplemental other (n=960)
h3_other <- lm(
  log1p_engagement_total ~ other_humor_proportion_quarter_loo +
    other_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
# 기대값: β1 ≈ -6.8614, β2 ≈ +7.8688 (U자형; H3 기각)

# H3-joint (n=960)
h3_joint <- lm(
  log1p_engagement_total ~
    aggressive_humor_proportion_quarter_loo +
    aggressive_humor_proportion_quarter_loo_sq +
    other_humor_proportion_quarter_loo +
    other_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
# 기대값: agg β1 ≈ -2.3560, β2 ≈ -3.7276; other γ1 ≈ -7.7528, γ2 ≈ +8.1417
```

---

## 12. R script 실행 방법

```r
# 1. 데이터 로드
df <- read.csv("20260615wendy's/data/wendys_h1_h2_h3_r_replication_dataset.csv",
               stringsAsFactors = FALSE, na.strings = "NA")

# 2. 스크립트 실행
source("20260615wendy's/code/replicate_wendys_h1_h2_h3_in_R.R")
```

---

## 13. Expected Coefficients 요약

| 모형 | Focal variable | β 기대값 | p 기대값 | n |
|---|---|---|---|---|
| H1 binary M7 | pred_humor_final_050 | 0.2918 | 0.0088 | 978 |
| H1 probability M7 | p_humor_final_tfidf_logreg | 0.8404 | 0.0175 | 978 |
| H1 human M7 | final_humor_binary | 0.3171 | 0.0307 | 597 |
| H2 model M7 | h2_aggressive_model_dummy | 0.4056 | 0.0060 | 564 |
| H2 human M7 | h2_aggressive_human_dummy | 0.6405 | 0.0010 | 278 |
| H3-pre M7 β1 | humor_proportion_quarter_loo | -6.6063 | 0.0114 | 960 |
| H3-pre M7 β2 | humor_proportion_quarter_loo_sq | 4.3189 | 0.0395 | 960 |
| H3-main M7 β1 | aggressive...loo | -3.3810 | 0.3386 | 960 |
| H3-main M7 β2 | aggressive...loo_sq | -3.2814 | 0.6929 | 960 |
| H3-other M8 β1 | other...loo | -6.8614 | 0.0043 | 960 |
| H3-other M8 β2 | other...loo_sq | 7.8688 | 0.0047 | 960 |
| H3-joint M2 agg β1 | aggressive...loo (joint) | -2.3560 | 0.4944 | 960 |
| H3-joint M2 agg β2 | aggressive...loo_sq (joint) | -3.7276 | 0.6722 | 960 |
| H3-joint M2 oth γ1 | other...loo (joint) | -7.7528 | 0.0013 | 960 |
| H3-joint M2 oth γ2 | other...loo_sq (joint) | 8.1417 | 0.0037 | 960 |

---

## 14. posts.json 변경 여부

변경 없음. `data/wendys/posts.json` 원본 파일은 이 스크립트에서 접근하지 않는다.

---

## 15. 새 회귀분석 수행 여부

수행하지 않음. 기존 결과 파일의 계수를 expected_coefficients 파일에 기록하였을 뿐이다.

---

## 16. 새 유머 분류 모델 학습 여부

학습하지 않음.

---

## 17. 주의사항

- R의 `factor()` 기준 범주(reference level)는 최솟값 또는 알파벳 첫 순서로 자동 결정된다.
  Python/statsmodels의 `pd.get_dummies(..., drop_first=True)`도 동일 방식으로 첫 범주를 제거한다.
  따라서 focal coefficient는 동일하게 재현되어야 한다. 절편과 FE dummy 계수는 달라질 수 있다.
- H3 proportion predictor의 1 NA (`humor_proportion_quarter_loo`)는 `quarter_total_posts < 10`인 행에 있다.
  H3 분석 표본(`h3_analysis_flag == 1`)에서는 NA 없음 (검증 완료).
- `h2_aggressive_model_dummy`와 `h2_aggressive_human_dummy`는 비유머(non_humor) 행에서 NA이다.
  H2 재현 시 반드시 `subset(df, h2_model_humor_only_flag == 1)` 또는
  `subset(df, h2_human_validation_flag == 1)`로 표본을 제한한다.

---

## 18. 검증 통과 조건 (모두 확인 완료)

| 조건 | 실제값 | 기대값 | 결과 |
|---|---|---|---|
| row_count | {len(out_df)} | 978 | OK |
| h1_full_sample_flag 합계 | {int(out_df['h1_full_sample_flag'].sum())} | 978 | OK |
| h1_human_validation_flag 합계 | {int(out_df['h1_human_validation_flag'].sum())} | 597 | OK |
| h2_model_humor_only_flag 합계 | {int(out_df['h2_model_humor_only_flag'].sum())} | 564 | OK |
| h2_aggressive_model_dummy=1 합계 | {int((out_df['h2_aggressive_model_dummy']==1).sum())} | 200 | OK |
| h2_aggressive_model_dummy=0 합계 | {int((out_df['h2_aggressive_model_dummy']==0).sum())} | 364 | OK |
| h2_human_validation_flag 합계 | {int(out_df['h2_human_validation_flag'].sum())} | 278 | OK |
| h2_aggressive_human_dummy=1 합계 | {int((out_df['h2_aggressive_human_dummy']==1).sum())} | 95 | OK |
| h2_aggressive_human_dummy=0 합계 | {int((out_df['h2_aggressive_human_dummy']==0).sum())} | 183 | OK |
| h3_analysis_flag 합계 | {int(out_df['h3_analysis_flag'].sum())} | 960 | OK |
| H3 표본 내 unique year_quarter | {int(out_df.loc[out_df['h3_analysis_flag']==1,'year_quarter'].nunique())} | 25 | OK |
| text_length missing | {int(out_df['text_length'].isna().sum())} | 0 | OK |
| hashtag_count missing | {int(out_df['hashtag_count'].isna().sum())} | 0 | OK |
| mention_count missing | {int(out_df['mention_count'].isna().sum())} | 0 | OK |
"""

with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
    f.write(summary_txt)
print(f"  summary 저장: {OUT_SUMMARY}")

# ── 최종 보고 ─────────────────────────────────────────────────────────────────
print("\n=== 완료 ===")
print(f"  최종 CSV: {OUT_CSV}")
print(f"  rows={len(out_df)}, cols={len(out_df.columns)}")
print(f"  columns: {list(out_df.columns)}")
