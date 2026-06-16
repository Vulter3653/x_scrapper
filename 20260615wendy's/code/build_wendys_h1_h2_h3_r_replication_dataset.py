"""
build_wendys_h1_h2_h3_r_replication_dataset.py  (v2 — 한글 컬럼명)

목적: H1-H2-H3 최종 보고서에 사용된 분석 변수를 하나의 R 재현용
     wide-format CSV로 통합한다. 컬럼명은 한글로 변경한다.
     새로운 분석 또는 회귀분석은 수행하지 않는다.

절대 규칙:
  - data/wendys/posts.json 원본 불변
  - 새 회귀분석 미수행 / 새 유머 분류 모델 미학습
  - log1p_view_count 미포함 (view_count 원시값은 참고용으로 포함)
  - emoji_count, url_count, is_quote_status, is_retweet_text 미포함
  - year_quarter FE / quarter FE dummy 미생성
  - frequency count 기반 H3 변수 미포함
  - month_total_posts 미포함 / day_of_week 미생성
  - 로그변환 DV 및 squared term은 R 스크립트 내에서 직접 계산
  - squared term 및 sample flag만 신규 생성 허용
"""

import pandas as pd
import numpy as np

# ── 경로 설정 ────────────────────────────────────────────────────────────────
BASE   = "20260615wendy's/"
DATA   = BASE + "data/"
RESULT = BASE + "result/"

IN_PRESENCE = RESULT + "wendys_final_humor_presence_full_predictions.csv"
IN_TYPE     = RESULT + "wendys_model_based_humor_type_full_predictions.csv"
IN_FAST     = DATA   + "wendys_fast_weak_supervised_humor_dataset.csv"
IN_H3PRE    = DATA   + "wendys_humor_frequency_proportion_post_level_dataset.csv"
IN_H3MAIN   = DATA   + "wendys_h3_aggressive_vs_other_intensity_dataset.csv"

OUT_CSV     = DATA   + "wendys_h1_h2_h3_r_replication_dataset.csv"
OUT_DICT    = RESULT + "wendys_h1_h2_h3_r_replication_data_dictionary.csv"
OUT_EXPECTED= RESULT + "wendys_h1_h2_h3_r_replication_expected_coefficients.csv"
OUT_SUMMARY = RESULT + "wendys_h1_h2_h3_r_replication_dataset_summary.md"

# ── 한글 컬럼명 매핑 ──────────────────────────────────────────────────────────
COL_RENAME = {
    'id':                                     '게시물ID',
    'tweet_url':                              '트윗URL',
    'text':                                   '트윗텍스트',
    'reply_count':                            '답글수',
    'favorite_count':                         '좋아요수',
    'retweet_count':                          '리트윗수',
    'quote_count':                            '인용수',
    'bookmark_count':                         '북마크수',
    'view_count':                             '조회수',
    'created_date':                           '작성일',
    'created_year':                           '작성연도',
    'created_month':                          '작성월',
    'created_hour':                           '작성시간',
    'year_quarter':                           '연도분기',
    'pred_humor_final_050':                   '유머예측이진',
    'p_humor_final_tfidf_logreg':             '유머확률모델',
    'final_humor_label_available':            '인간레이블가용',
    'final_humor_binary':                     '유머레이블최종',
    'pred_humor_type_group_model':            '유머유형모델예측',
    'is_aggressive_humor':                    '공격적유머여부',
    'is_other_humor':                         '기타유머여부',
    'final_humor_type_group':                 '유머유형최종',
    'text_length':                            '텍스트길이',
    'hashtag_count':                          '해시태그수',
    'mention_count':                          '멘션수',
    'quarter_total_posts':                    '분기게시물수',
    'h3_quarter_filter_10':                   'H3분기필터',
    'humor_proportion_quarter_loo':           '유머비율LOO분기',
    'aggressive_humor_proportion_quarter_loo':'공격적유머비율LOO분기',
    'other_humor_proportion_quarter_loo':     '기타유머비율LOO분기',
    'h1_human_validation_flag':               'H1인간검증표본',
    'h2_model_humor_only_flag':               'H2모델유머표본',
    'h2_human_validation_flag':               'H2인간검증표본',
    'h3_analysis_flag':                       'H3분석표본',
    'h2_aggressive_model_dummy':              'H2공격적유머모델더미',
    'h2_aggressive_human_dummy':              'H2공격적유머인간더미',
}

# ── 1. 입력 파일 로드 ────────────────────────────────────────────────────────
print("=== 1. 입력 파일 로드 ===")
h3main   = pd.read_csv(IN_H3MAIN)
h3pre    = pd.read_csv(IN_H3PRE)
presence = pd.read_csv(IN_PRESENCE)
ht       = pd.read_csv(IN_TYPE)
fast     = pd.read_csv(IN_FAST)

for name, df in [("h3main",h3main),("h3pre",h3pre),("presence",presence),("ht",ht),("fast",fast)]:
    print(f"  {name}: rows={len(df)}, id_dup={df['id'].duplicated().sum()}")
assert len(h3main)==978 and h3main['id'].duplicated().sum()==0

# ── 2. Base 선택 (h3main) ────────────────────────────────────────────────────
print("\n=== 2. 컬럼 선택 및 병합 ===")

BASE_COLS = [
    'id','tweet_url','text',
    'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
    'created_date','created_year','created_month','created_hour','year_quarter',
    'pred_humor_final_050','p_humor_final_tfidf_logreg',
    'pred_humor_type_group_model','is_aggressive_humor','is_other_humor',
    'quarter_total_posts',
    'aggressive_humor_proportion_quarter_loo','other_humor_proportion_quarter_loo',
]
base = h3main[BASE_COLS].copy()
print(f"  base: {len(base)} rows")

# h3pre → humor_proportion_quarter_loo
base = base.merge(h3pre[['id','humor_proportion_quarter_loo']], on='id', how='left', validate='1:1')
print(f"  after h3pre merge: {len(base)} rows, NA humor_prop={base['humor_proportion_quarter_loo'].isna().sum()}")

# presence → final_humor_binary, final_humor_label_available
base = base.merge(presence[['id','final_humor_binary','final_humor_label_available']], on='id', how='left', validate='1:1')
print(f"  after presence merge: {len(base)} rows")

# humor_type → final_humor_type_group
base = base.merge(ht[['id','final_humor_type_group']], on='id', how='left', validate='1:1')
print(f"  after ht merge: {len(base)} rows")

# fast → text_length, hashtag_count, mention_count
base = base.merge(fast[['id','text_length','hashtag_count','mention_count']], on='id', how='left', validate='1:1')
print(f"  after fast merge: {len(base)} rows")

assert len(base)==978

# ── 3. 신규 생성 변수 (sample flag, dummy) ───────────────────────────────────
print("\n=== 3. 신규 변수 생성 ===")

base['h3_quarter_filter_10']  = (base['quarter_total_posts'] >= 10).astype(int)
base['h1_human_validation_flag'] = (base['final_humor_label_available'] == 1).astype(int)
base['h2_model_humor_only_flag'] = base['pred_humor_type_group_model'].isin(
    ['aggressive','other_humor']).astype(int)
base['h2_human_validation_flag'] = base['final_humor_type_group'].isin(
    ['aggressive','other_humor']).astype(int)
base['h3_analysis_flag'] = base['h3_quarter_filter_10']

base['h2_aggressive_model_dummy'] = np.where(
    base['pred_humor_type_group_model']=='aggressive', 1,
    np.where(base['pred_humor_type_group_model']=='other_humor', 0, np.nan))

base['h2_aggressive_human_dummy'] = np.where(
    base['final_humor_type_group']=='aggressive', 1,
    np.where(base['final_humor_type_group']=='other_humor', 0, np.nan))

print("  sample flags 및 dummy 생성 완료")

# ── 4. 최종 컬럼 순서 정렬 ──────────────────────────────────────────────────
FINAL_COLS_ENG = [
    'id','tweet_url','text',
    'reply_count','favorite_count','retweet_count','quote_count','bookmark_count','view_count',
    'created_date','created_year','created_month','created_hour','year_quarter',
    'pred_humor_final_050','p_humor_final_tfidf_logreg',
    'final_humor_label_available','final_humor_binary',
    'pred_humor_type_group_model','is_aggressive_humor','is_other_humor',
    'final_humor_type_group',
    'text_length','hashtag_count','mention_count',
    'quarter_total_posts','h3_quarter_filter_10',
    'humor_proportion_quarter_loo',
    'aggressive_humor_proportion_quarter_loo',
    'other_humor_proportion_quarter_loo',
    'h1_human_validation_flag',
    'h2_model_humor_only_flag','h2_human_validation_flag',
    'h3_analysis_flag',
    'h2_aggressive_model_dummy','h2_aggressive_human_dummy',
]
missing = [c for c in FINAL_COLS_ENG if c not in base.columns]
if missing:
    raise ValueError(f"Missing cols: {missing}")

out = base[FINAL_COLS_ENG].copy()

# ── 5. 한글 컬럼명 적용 ──────────────────────────────────────────────────────
out.rename(columns=COL_RENAME, inplace=True)
print(f"\n=== 4. 한글 컬럼명 적용 완료 ===")
print(f"  최종 컬럼 수: {len(out.columns)}")

# ── 6. 제외 변수 검증 ────────────────────────────────────────────────────────
print("\n=== 5. 제외 변수 검증 ===")
EXCLUDED = ['log1p_view_count','emoji_count','url_count','is_quote_status','is_retweet_text',
            'day_of_week','month_total_posts','humor_frequency_quarter',
            'aggressive_humor_frequency_quarter','other_humor_frequency_quarter']
for v in EXCLUDED:
    assert v not in out.columns, f"제외 변수 {v} 포함됨"
    print(f"  {v}: OK (미포함)")

# ── 7. 검증 조건 ─────────────────────────────────────────────────────────────
print("\n=== 6. 검증 조건 확인 ===")
KR = {v: k for k, v in COL_RENAME.items()}  # reverse

checks = {
    "rows": (len(out), 978),
    "H1인간검증표본 합계": (out['H1인간검증표본'].sum(), 597),
    "H2모델유머표본 합계": (out['H2모델유머표본'].sum(), 564),
    "H2공격적유머모델더미=1": ((out['H2공격적유머모델더미']==1).sum(), 200),
    "H2공격적유머모델더미=0": ((out['H2공격적유머모델더미']==0).sum(), 364),
    "H2인간검증표본 합계": (out['H2인간검증표본'].sum(), 278),
    "H2공격적유머인간더미=1": ((out['H2공격적유머인간더미']==1).sum(), 95),
    "H2공격적유머인간더미=0": ((out['H2공격적유머인간더미']==0).sum(), 183),
    "H3분석표본 합계": (out['H3분석표본'].sum(), 960),
    "H3 unique 분기": (out.loc[out['H3분석표본']==1,'연도분기'].nunique(), 25),
    "텍스트길이 NA": (out['텍스트길이'].isna().sum(), 0),
    "해시태그수 NA": (out['해시태그수'].isna().sum(), 0),
    "멘션수 NA": (out['멘션수'].isna().sum(), 0),
}
h3mask = out['H3분석표본']==1
for pred in ['유머비율LOO분기','공격적유머비율LOO분기','기타유머비율LOO분기']:
    checks[f"{pred} H3내 NA"] = (out.loc[h3mask, pred].isna().sum(), 0)

all_ok = True
for name, (actual, expected) in checks.items():
    ok = actual == expected
    print(f"  {name}: {actual} ({'OK' if ok else f'MISMATCH expected={expected}'})")
    if not ok:
        all_ok = False
if not all_ok:
    raise ValueError("검증 실패")
print("  모든 검증 통과")

# ── 8. CSV 저장 ───────────────────────────────────────────────────────────────
out.to_csv(OUT_CSV, index=False, na_rep='NA', encoding='utf-8-sig')
print(f"\n=== 7. 저장 완료 ===")
print(f"  {OUT_CSV}")
print(f"  rows={len(out)}, cols={len(out.columns)}")
print(f"  columns: {list(out.columns)}")

# ── 9. Data Dictionary ────────────────────────────────────────────────────────
print("\n=== 8. Data Dictionary 생성 ===")
dict_rows = []
meta = [
    ('게시물ID','identifier','H1_H2_H3','key','게시물 고유 ID','h3main','character','978개 고유'),
    ('트윗URL','identifier','H1_H2_H3','reference','트윗 URL','h3main','character',''),
    ('트윗텍스트','identifier','H1_H2_H3','reference','트윗 원문 텍스트','h3main','character',''),
    ('답글수','raw_count','H1_H2_H3','raw_dv_source','답글(reply) 수','h3main','integer','R에서 log1p 변환 후 DV로 사용'),
    ('좋아요수','raw_count','H1_H2_H3','raw_dv_source','좋아요(favorite) 수','h3main','integer',''),
    ('리트윗수','raw_count','H1_H2_H3','raw_dv_source','리트윗(retweet) 수','h3main','integer','참여도합계 계산에 필수'),
    ('인용수','raw_count','H1_H2_H3','raw_dv_source','인용(quote) 수','h3main','integer',''),
    ('북마크수','raw_count','H1_H2_H3','raw_dv_source','북마크(bookmark) 수','h3main','integer',''),
    ('조회수','raw_count','reference','reference','조회(view) 수 — 분석에 사용하지 않음','h3main','integer','분석 제외; 참고용'),
    ('작성일','date_time','H1_H2_H3','covariate','게시 날짜 (YYYY-MM-DD)','h3main','character',''),
    ('작성연도','date_time','H1_H2_H3','time_fe','게시 연도; R: factor(작성연도)','h3main','integer',''),
    ('작성월','date_time','H1_H2_H3','time_fe','게시 월 1-12; R: factor(작성월)','h3main','integer',''),
    ('작성시간','date_time','H1_H2_H3','time_fe','게시 시각 0-23; R: factor(작성시간)','h3main','integer',''),
    ('연도분기','date_time','H3','filter','연도-분기 (YYYY-QN); LOO 계산 단위','h3main','character','H3에서 FE로 사용 금지'),
    ('유머예측이진','h1_iv','H1','primary_iv','모델 기반 유머 이진 예측 (threshold=0.50)','presence','integer','0=비유머, 1=유머'),
    ('유머확률모델','h1_iv','H1','primary_iv','모델 기반 유머 확률 (TF-IDF LogReg)','presence','numeric','H1 probability model IV'),
    ('인간레이블가용','h1_validation','H1','sample_flag_source','인간 레이블 가용 여부 (1=가용)','presence','integer','합계=597 → H1인간검증표본 기준'),
    ('유머레이블최종','h1_validation','H1','validation_iv','최종 유머 이진 레이블 (인간+모델 병합)','presence','integer','H1 human validation IV'),
    ('유머유형모델예측','h2_iv','H2','primary_iv','모델 기반 유머 유형 (aggressive/other_humor/non_humor)','h3main','character',''),
    ('공격적유머여부','h2_iv','H2','covariate','공격적 유머 이진 더미 (model-based)','h3main','integer','0/1'),
    ('기타유머여부','h2_iv','H2','covariate','기타 유머 이진 더미 (model-based)','h3main','integer','0/1'),
    ('유머유형최종','h2_validation','H2','validation_iv','최종 유머 유형 그룹 (인간 코딩 우선)','humor_type','character','aggressive/other_humor/non_humor/missing'),
    ('텍스트길이','control_post_format','H1_H2_H3','covariate','텍스트 길이 (문자 수)','fast_ws','integer',''),
    ('해시태그수','control_post_format','H1_H2_H3','covariate','해시태그(#) 수','fast_ws','integer',''),
    ('멘션수','control_post_format','H1_H2_H3','covariate','멘션(@) 수','fast_ws','integer',''),
    ('분기게시물수','filter','H3','filter_source','해당 연도분기 내 총 게시물 수','h3main','integer','H3 필터 기준'),
    ('H3분기필터','filter','H3','filter','분기게시물수>=10이면 1','derived','integer','H3분석표본과 동일'),
    ('유머비율LOO분기','h3_predictor','H3','primary_predictor','전체 유머 비율 LOO (분기 수준)','h3pre','numeric','H3-pre predictor; 1 NA in full sample'),
    ('공격적유머비율LOO분기','h3_predictor','H3','primary_predictor','공격적 유머 비율 LOO (분기 수준)','h3main','numeric','H3-main predictor'),
    ('기타유머비율LOO분기','h3_predictor','H3','primary_predictor','기타 유머 비율 LOO (분기 수준)','h3main','numeric','H3-supplemental predictor'),
    ('H1인간검증표본','sample_flag','H1','sample_flag','인간레이블가용==1이면 1 (n=597)','derived','integer',''),
    ('H2모델유머표본','sample_flag','H2','sample_flag','유머유형모델예측 in {aggressive,other_humor} (n=564)','derived','integer',''),
    ('H2인간검증표본','sample_flag','H2','sample_flag','유머유형최종 in {aggressive,other_humor} (n=278)','derived','integer',''),
    ('H3분석표본','sample_flag','H3','sample_flag','분기게시물수>=10이면 1 (n=960)','derived','integer',''),
    ('H2공격적유머모델더미','h2_iv','H2','r_replication_iv','H2 모델: aggressive=1, other_humor=0, else=NA','derived','numeric','subset(H2모델유머표본==1)에서 사용'),
    ('H2공격적유머인간더미','h2_validation','H2','r_replication_iv','H2 인간: aggressive=1, other_humor=0, else=NA','derived','numeric','subset(H2인간검증표본==1)에서 사용'),
]
for row in meta:
    col = row[0]
    s = out[col]
    dict_rows.append({
        'variable_name': col, 'variable_group': row[1],
        'used_in': row[2], 'role': row[3], 'description': row[4],
        'source_file': row[5], 'expected_type': row[6],
        'missing_n': int(s.isna().sum()), 'non_missing_n': int(s.notna().sum()),
        'unique_n': int(s.nunique(dropna=True)), 'notes': row[7],
    })
pd.DataFrame(dict_rows).to_csv(OUT_DICT, index=False, encoding='utf-8-sig')
print(f"  {OUT_DICT}: {len(dict_rows)} rows")

# ── 10. Expected Coefficients ─────────────────────────────────────────────────
print("\n=== 9. Expected Coefficients 업데이트 ===")
exp_rows = [
    ('H1_binary_M7', 'full sample (n=978)', '유머예측이진', 0.2918, 0.0088, 978,
     'wendys_h1_three_post_format_fullsample_binary_results.csv',
     'M7: factor(작성연도)+factor(작성월)+factor(작성시간)+텍스트길이+해시태그수+멘션수'),
    ('H1_probability_M7', 'full sample (n=978)', '유머확률모델', 0.8404, 0.0175, 978,
     'wendys_h1_three_post_format_fullsample_probability_results.csv', 'M7 동일'),
    ('H1_human_M7', 'H1인간검증표본==1 (n=597)', '유머레이블최종', 0.3171, 0.0307, 597,
     'wendys_h1_three_post_format_human_validation_results.csv', 'M7 동일'),
    ('H2_model_M7', 'H2모델유머표본==1 (n=564)', 'H2공격적유머모델더미', 0.4056, 0.0060, 564,
     'wendys_h2_step3_post_format_model_based_results.csv', 'M7 동일'),
    ('H2_human_M7', 'H2인간검증표본==1 (n=278)', 'H2공격적유머인간더미', 0.6405, 0.0010, 278,
     'wendys_h2_step3_post_format_human_validation_results.csv', 'M7 동일'),
    ('H3_pre_M7_beta1', 'H3분석표본==1 (n=960)', '유머비율LOO분기 (linear)', -6.3289, 0.0103, 960,
     'wendys_h3_step3_general_humor_post_format_results.csv', 'beta2=+4.3189(p=0.0395), U자형→H3기각'),
    ('H3_pre_M7_beta2', 'H3분석표본==1 (n=960)', '유머비율LOO분기제곱 (quadratic)', 4.3189, 0.0395, 960,
     'wendys_h3_step3_general_humor_post_format_results.csv', 'β2>0 → U자형 (역U자형 아님)'),
    ('H3_main_M7_beta1', 'H3분석표본==1 (n=960)', '공격적유머비율LOO분기 (linear)', -1.9777, 0.5532, 960,
     'wendys_h3_step3_aggressive_humor_post_format_results.csv', 'beta2=-3.2814(p=0.6929) not_support'),
    ('H3_main_M7_beta2', 'H3분석표본==1 (n=960)', '공격적유머비율LOO분기제곱 (quadratic)', -3.2814, 0.6929, 960,
     'wendys_h3_step3_aggressive_humor_post_format_results.csv', 'not_support → H3기각'),
    ('H3_other_M8_beta1', 'H3분석표본==1 (n=960)', '기타유머비율LOO분기 (linear)', -6.8614, 0.0043, 960,
     'wendys_h3_supplemental_other_humor_proportion_results.csv', 'beta2=+7.8688(p=0.0047), U_shape'),
    ('H3_other_M8_beta2', 'H3분석표본==1 (n=960)', '기타유머비율LOO분기제곱 (quadratic)', 7.8688, 0.0047, 960,
     'wendys_h3_supplemental_other_humor_proportion_results.csv', 'β2>0 → U자형 → H3기각'),
    ('H3_joint_M2_agg_beta1', 'H3분석표본==1 (n=960)', '공격적유머비율LOO분기 (joint linear)', -2.3560, 0.4944, 960,
     'wendys_h3_joint_aggressive_other_decomposition_results.csv', 'agg_not_support'),
    ('H3_joint_M2_agg_beta2', 'H3분석표본==1 (n=960)', '공격적유머비율LOO분기제곱 (joint quadratic)', -3.7276, 0.6722, 960,
     'wendys_h3_joint_aggressive_other_decomposition_results.csv', 'masking 없음 확인'),
    ('H3_joint_M2_oth_beta1', 'H3분석표본==1 (n=960)', '기타유머비율LOO분기 (joint linear)', -7.7528, 0.0013, 960,
     'wendys_h3_joint_aggressive_other_decomposition_results.csv', 'other_U_shape'),
    ('H3_joint_M2_oth_beta2', 'H3분석표본==1 (n=960)', '기타유머비율LOO분기제곱 (joint quadratic)', 8.1417, 0.0037, 960,
     'wendys_h3_joint_aggressive_other_decomposition_results.csv', 'β2>0 → U자형'),
]
pd.DataFrame(exp_rows, columns=[
    'model_name','sample_filter','focal_variable','expected_coefficient',
    'expected_p_value','expected_n','source_result_file','notes'
]).to_csv(OUT_EXPECTED, index=False, encoding='utf-8-sig')
print(f"  {OUT_EXPECTED}: {len(exp_rows)} rows")

# ── 11. Summary ───────────────────────────────────────────────────────────────
print("\n=== 10. Summary 생성 ===")
cols_str = "\n".join(f"- `{c}` ({i+1})" for i, c in enumerate(out.columns))
summary = f"""# Wendy's H1-H2-H3 R 재현용 데이터셋 (v2 — 한글 컬럼명)

작성일: 2026-06-16 (v2 재구성)

---

## 1. 작업 목적
최종 보고서 분석 변수를 단일 wide-format CSV로 통합. 컬럼명을 한글로 변경하여
연구자가 R에서 `df$좋아요수` 형태로 직접 참조할 수 있도록 구성함.

## 2. 최종 보고서 경로
`20260615wendy's/result/wendys_humor_h1_h2_h3_final_report.md`

## 3. 사용한 입력 파일
| 파일 | rows | 역할 |
|---|---|---|
| `result/wendys_final_humor_presence_full_predictions.csv` | 978 | H1 IV, 인간 레이블 |
| `result/wendys_model_based_humor_type_full_predictions.csv` | 978 | H2 유머 유형 |
| `data/wendys_fast_weak_supervised_humor_dataset.csv` | 978 | post format controls |
| `data/wendys_humor_frequency_proportion_post_level_dataset.csv` | 978 | H3-pre predictor |
| `data/wendys_h3_aggressive_vs_other_intensity_dataset.csv` | 978 | base (원시집계, 시간변수, H3 main/other predictor) |

## 4. 병합 안정성
- 병합 key: `id` (978개 고유, dup=0, NA=0 — 전 파일 동일)
- 모든 병합: 1:1 left join, 978→978 유지

## 5. 최종 dataset
- rows: **{len(out)}**
- cols: **{len(out.columns)}**

## 6. 컬럼 목록
{cols_str}

## 7. R에서 파생 변수 계산 (R 스크립트 내)
```r
# 종속변수 (log1p 변환)
df$참여도합계     <- log1p(df$좋아요수 + df$리트윗수 + df$답글수 + df$인용수 + df$북마크수)
# H3 이차항
df$유머비율LOO분기제곱       <- df$유머비율LOO분기^2
df$공격적유머비율LOO분기제곱 <- df$공격적유머비율LOO분기^2
df$기타유머비율LOO분기제곱   <- df$기타유머비율LOO분기^2
```

## 8. 제외 변수 확인
log1p_view_count, emoji_count, url_count, is_quote_status, is_retweet_text,
day_of_week, month_total_posts, frequency count 변수, year_quarter FE dummy
→ 전부 미포함 확인

## 9. 검증 결과
| 조건 | 실제값 | 기대값 |
|---|---|---|
| rows | {len(out)} | 978 |
| H1인간검증표본 합계 | {int(out['H1인간검증표본'].sum())} | 597 |
| H2모델유머표본 합계 | {int(out['H2모델유머표본'].sum())} | 564 |
| H2공격적유머모델더미=1 | {int((out['H2공격적유머모델더미']==1).sum())} | 200 |
| H2공격적유머모델더미=0 | {int((out['H2공격적유머모델더미']==0).sum())} | 364 |
| H2인간검증표본 합계 | {int(out['H2인간검증표본'].sum())} | 278 |
| H2공격적유머인간더미=1 | {int((out['H2공격적유머인간더미']==1).sum())} | 95 |
| H2공격적유머인간더미=0 | {int((out['H2공격적유머인간더미']==0).sum())} | 183 |
| H3분석표본 합계 | {int(out['H3분석표본'].sum())} | 960 |
| H3 unique 분기 | {int(out.loc[out['H3분석표본']==1,'연도분기'].nunique())} | 25 |

## 10. 주의사항
- 조회수(view_count)는 참고용으로만 포함; 회귀분석에 사용하지 않음
- 리트윗수는 참여도합계 계산에 필수 (사용자 열 목록에 없었으나 DV 계산상 포함)
- H2 더미 변수: 비유머 행은 NA → subset() 조건 필수
- H3: factor(연도분기) 사용 금지 (LOO 변수와 동일 수준)
- posts.json 변경 없음 / 새 회귀분석 미수행 / 새 분류 모델 미학습
"""
with open(OUT_SUMMARY,'w',encoding='utf-8') as f:
    f.write(summary)
print(f"  {OUT_SUMMARY}")

print("\n=== 완료 ===")
print(f"  CSV: {OUT_CSV}  rows={len(out)}, cols={len(out.columns)}")
