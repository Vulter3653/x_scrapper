# Wendy's H2 Step 1: Aggressive vs Other Humor Direct Test 결과

## 1. 분석 목적

H2 분석 1단계로, 전체 978건에서 예측된 model-based humor type을 기준으로 aggressive humor와 other humor 게시글의 post-level engagement를 직접 비교한다. non_humor는 이번 direct test에서 제외하였다. 시간 고정효과 및 post format controls는 이번 작업에서 추가하지 않는다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

판정 기준: β > 0 and p < .05 → supports_H2 / β > 0 and p < .10 → weak_support / β > 0 and p ≥ .10 → positive_not_significant / β ≤ 0 → not_support

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), is_aggressive_humor, pred_humor_type_group_model |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation용) |

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 5. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. is_aggressive_humor는 기존 H3 파일에 이미 존재하는 변수이다. Human validation IV는 final_humor_type_group 문자열 기반으로 in-memory에서만 구분하였으며, 새 컬럼으로 저장하지 않았다.

---

## 6. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| 전체 humor-only n | 564 |
| aggressive n | 200 |
| other_humor n | 364 |
| non_humor 포함 여부 | False |
| 결측으로 sample 감소 | False |
| 기준 범주 | other_humor (is_aggressive_humor=0) |

---

## 7. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| 전체 human humor-only n | 278 |
| aggressive n | 95 |
| other_humor n | 183 |
| non_humor 포함 여부 | False |
| 결측으로 sample 감소 | False |
| 기준 범주 | other_humor |

---

## 8. Model-based H2 Direct Test 결과

**표본: n=564, IV=is_aggressive_humor, 기준=other_humor**

| DV | agg_mean | other_mean | diff | β | p | sig | Welch_t | Welch_p | Welch_sig | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|
| log1p_engagement_total | 7.9281 | 7.4597 | 0.4684 | 0.4684 | 0.0021 | ** | 3.0016 | 0.0029 | ** | supports_H2 |
| log1p_engagement_favorite_retweet | 7.8146 | 7.3327 | 0.4819 | 0.4819 | 0.0018 | ** | 3.0448 | 0.0025 | ** | supports_H2 |
| log1p_favorite_count | 7.7386 | 7.1524 | 0.5862 | 0.5862 | 0.0007 | *** | 3.4615 | 0.0006 | *** | supports_H2 |
| log1p_retweet_count | 4.8844 | 4.4095 | 0.4749 | 0.4749 | 0.0034 | ** | 2.8313 | 0.0049 | ** | supports_H2 |
| log1p_reply_count | 4.908 | 4.706 | 0.202 | 0.202 | 0.1551 |  | 1.4058 | 0.1606 |  | positive_not_significant |
| log1p_quote_count | 3.2164 | 2.8869 | 0.3295 | 0.3295 | 0.0468 | * | 1.9156 | 0.0562 | † | supports_H2 |
| log1p_bookmark_count | 2.8861 | 2.394 | 0.492 | 0.492 | 0.0008 | *** | 3.3091 | 0.001 | ** | supports_H2 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 9. Human-coded Validation H2 결과 (부가 검증)

**표본: n=278, IV=final_humor_type_group(aggressive dummy), 기준=other_humor**

| DV | agg_mean | other_mean | diff | β | p | sig | Welch_t | Welch_p | Welch_sig | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|
| log1p_engagement_total | 8.3411 | 7.6338 | 0.7074 | 0.7074 | 0.0007 | *** | 3.2896 | 0.0012 | ** | supports_H2 |
| log1p_engagement_favorite_retweet | 8.212 | 7.5009 | 0.7111 | 0.7111 | 0.0008 | *** | 3.2304 | 0.0015 | ** | supports_H2 |
| log1p_favorite_count | 8.1418 | 7.3858 | 0.756 | 0.756 | 0.0008 | *** | 3.3352 | 0.001 | ** | supports_H2 |
| log1p_retweet_count | 5.4009 | 4.5306 | 0.8703 | 0.8703 | 0.0001 | *** | 3.7714 | 0.0002 | *** | supports_H2 |
| log1p_reply_count | 5.312 | 4.9438 | 0.3682 | 0.3682 | 0.0439 | * | 1.9551 | 0.0522 | † | supports_H2 |
| log1p_quote_count | 3.8651 | 3.0616 | 0.8035 | 0.8035 | 0.0006 | *** | 3.2933 | 0.0012 | ** | supports_H2 |
| log1p_bookmark_count | 3.3405 | 2.5014 | 0.8391 | 0.8391 | 0.0 | *** | 4.1835 | 0.0 | *** | supports_H2 |

---

## 10. 평균 차이와 회귀 결과 비교 (primary DV: log1p_engagement_total)

| 표본 | agg_mean | other_mean | 차이 | β (OLS) | p | Welch_p | 판정 |
|---|---|---|---|---|---|---|---|
| model-based (n=564) | 7.9281 | 7.4597 | 0.4684 | 0.4684 | 0.0021 | 0.0029 | supports_H2 |
| human-coded (n=278) | 8.3411 | 7.6338 | 0.7074 | 0.7074 | 0.0007 | 0.0012 | supports_H2 |

OLS β와 mean_difference가 동일한 것은 단순 이진 회귀에서 상수가 other_humor 평균이고 β가 평균 차이를 나타내기 때문이다.

---

## 11. H2 주 분석 판정

**Model-based primary DV (log1p_engagement_total) 기준:**

- aggressive mean = 7.9281
- other_humor mean = 7.4597
- β = 0.4684, p = 0.0021
- **판정: supports_H2**

---

## 12. 사람 코딩 결과는 부가 검증

Human validation 결과(n=278)는 부가 검증이며, 주 분석(model-based n=564)을 대체하지 않는다.

---

## 13. Non_humor 제외 확인

H2 direct test에서 non_humor 게시글은 제외하였다. model-based 표본의 non_humor in-sample: 0건, human validation in-sample: 0건.

---

## 14. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 증가/감소시켰다는 주장을 할 수 없다.

---

## 15. 다음 단계

다음 단계에서 시간 고정효과(created_year, created_month, created_hour FE)를 추가할 수 있으나, 사용자 승인 후 진행한다.

---

*생성일: 2026-06-15*
