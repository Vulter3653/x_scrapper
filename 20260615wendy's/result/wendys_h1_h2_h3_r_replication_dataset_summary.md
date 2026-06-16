# Wendy's H1-H2-H3 R 재현용 데이터셋 — 생성 요약

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

**39**

---

## 7. 포함한 변수 목록

- `id`
- `created_date`
- `created_year`
- `created_month`
- `created_hour`
- `year_quarter`
- `log1p_engagement_total`
- `log1p_engagement_favorite_retweet`
- `log1p_favorite_count`
- `log1p_retweet_count`
- `log1p_reply_count`
- `log1p_quote_count`
- `log1p_bookmark_count`
- `pred_humor_final_050`
- `p_humor_final_tfidf_logreg`
- `final_humor_label_available`
- `final_humor_binary`
- `pred_humor_type_group_model`
- `is_aggressive_humor`
- `is_other_humor`
- `final_humor_type_group`
- `text_length`
- `hashtag_count`
- `mention_count`
- `quarter_total_posts`
- `h3_quarter_filter_10`
- `humor_proportion_quarter_loo`
- `aggressive_humor_proportion_quarter_loo`
- `other_humor_proportion_quarter_loo`
- `humor_proportion_quarter_loo_sq`
- `aggressive_humor_proportion_quarter_loo_sq`
- `other_humor_proportion_quarter_loo_sq`
- `h1_full_sample_flag`
- `h1_human_validation_flag`
- `h2_model_humor_only_flag`
- `h2_human_validation_flag`
- `h3_analysis_flag`
- `h2_aggressive_model_dummy`
- `h2_aggressive_human_dummy`

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
| row_count | 978 | 978 | OK |
| h1_full_sample_flag 합계 | 978 | 978 | OK |
| h1_human_validation_flag 합계 | 597 | 597 | OK |
| h2_model_humor_only_flag 합계 | 564 | 564 | OK |
| h2_aggressive_model_dummy=1 합계 | 200 | 200 | OK |
| h2_aggressive_model_dummy=0 합계 | 364 | 364 | OK |
| h2_human_validation_flag 합계 | 278 | 278 | OK |
| h2_aggressive_human_dummy=1 합계 | 95 | 95 | OK |
| h2_aggressive_human_dummy=0 합계 | 183 | 183 | OK |
| h3_analysis_flag 합계 | 960 | 960 | OK |
| H3 표본 내 unique year_quarter | 25 | 25 | OK |
| text_length missing | 0 | 0 | OK |
| hashtag_count missing | 0 | 0 | OK |
| mention_count missing | 0 | 0 | OK |
