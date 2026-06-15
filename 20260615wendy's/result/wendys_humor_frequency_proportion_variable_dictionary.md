# Wendy's Humor Frequency & Proportion 변수 사전

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
| **월별 범위** | min=0.0, max=37.0, mean=12.4693, sd=9.6138 |

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
| **분기별 범위** | min=1.0, max=78.0, mean=31.3804, sd=21.1122 |

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
| **월별 범위** | min=0.0, max=1.0, mean=0.5767, sd=0.189 |

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
| **분기별 범위** | min=0.2, max=1.0, mean=0.5767, sd=0.1544 |

---

## 5. humor_proportion_month_loo

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_month_loo |
| **한국어 설명** | 해당 게시글을 제외한 당월 유머 비율 (leave-one-out) |
| **수식** | (month_humor_posts − pred_humor_final_050_i) / (month_total_posts − 1) |
| **분석 단위** | post-level |
| **해석** | 내 게시글을 제외했을 때, 해당 달의 나머지 게시글 중 유머 비율이 얼마인가 |
| **주의사항** | month_total_posts = 1인 경우 missing. LOO missing: 3건. 기존 humor_intensity_month_loo와 동일한 값. |

---

## 6. humor_proportion_quarter_loo

| 항목 | 내용 |
|---|---|
| **영문 변수명** | humor_proportion_quarter_loo |
| **한국어 설명** | 해당 게시글을 제외한 해당 분기 유머 비율 (leave-one-out) |
| **수식** | (quarter_humor_posts − pred_humor_final_050_i) / (quarter_total_posts − 1) |
| **분석 단위** | post-level |
| **해석** | 내 게시글을 제외했을 때, 해당 분기의 나머지 게시글 중 유머 비율이 얼마인가 |
| **주의사항** | quarter_total_posts = 1인 경우 missing. LOO missing: 1건. H3 회귀분석 primary predictor 후보. 기존 humor_intensity_quarter_loo와 동일한 값. |

---

*생성일: 2026-06-15*
