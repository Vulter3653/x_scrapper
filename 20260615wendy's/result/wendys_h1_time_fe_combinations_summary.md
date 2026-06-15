# Wendy's H1 Time Fixed Effects Combination Check 결과

## 1. 분석 목적

유머 게시글 여부(Humor_i)와 post-level engagement 간 관계가 created_year, created_month, created_hour를 1개 / 2개 조합 / 3개 전체로 추가했을 때 각각 어떻게 변화하는지 확인한다. 이번 작업은 H1에만 한정하며, H2와 H3는 수행하지 않았다.

---

## 2. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_final_humor_presence_full_predictions.csv | IV (final_humor_binary, pred_humor_final_050, p_humor_final_tfidf_logreg) |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), 시간 변수 (created_year/month/hour) |

---

## 3. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 4. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 파일에 존재하는 컬럼만 사용하였다. day_of_week 생성 없음. text_length 등 포맷 변수 미사용. quarter_total_posts, month_total_posts 미사용. log1p_view_count 미사용. year_quarter FE 미사용.

---

## 5. 표본 구성

| 항목 | 값 |
|---|---|
| Primary sample | final_humor_label_available=1, n=597 |
| Primary humor=1 | 309 |
| Primary humor=0 | 288 |
| Full sample | n=978 |
| Full predicted humor=1 (pred_humor_final_050) | 564 |
| Full predicted humor=0 | 414 |
| 결측으로 인한 sample 감소 | 없음 |

---

## 6. 사용한 시간 변수 조합

| 변수 | 처리 방식 | primary 기준 범주 | primary 더미 수 |
|---|---|---|---|
| created_year | categorical FE (더미) | 2019 | 7 |
| created_month | categorical FE (더미) | 1 | 11 |
| created_hour | categorical FE (더미) | 00 | 19 |

기준 범주는 각 변수 내 최솟값으로 자동 설정하였다.

모형 구성:

| 모형 | 포함 FE | 시간 변수 수 |
|---|---|---|
| M0_baseline | none | 0 |
| M1_year_fe | year_FE | 1 |
| M2_month_fe | month_FE | 1 |
| M3_hour_fe | hour_FE | 1 |
| M4_year_month_fe | year_FE+month_FE | 2 |
| M5_year_hour_fe | year_FE+hour_FE | 2 |
| M6_month_hour_fe | month_FE+hour_FE | 2 |
| M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 3 |

---

## 7. Primary Human-labeled H1 결과

**표본: n=597, IV=final_humor_binary**

### 7-1. Primary DV: log1p_engagement_total (전체 모형)

| n_time | model | β | p_value | sig | R² | adj_R² | flag |
|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | 0.5043 | 0.0004 | *** | 0.0208 | 0.0192 | supports_H1 |
| 1 | M1_year_fe | 0.3442 | 0.02 | * | 0.1083 | 0.0962 | supports_H1 |
| 1 | M2_month_fe | 0.4348 | 0.002 | ** | 0.0917 | 0.0731 | supports_H1 |
| 1 | M3_hour_fe | 0.4991 | 0.0006 | *** | 0.0587 | 0.026 | supports_H1 |
| 2 | M4_year_month_fe | 0.2848 | 0.0522 | † | 0.1743 | 0.1472 | weak_support |
| 2 | M5_year_hour_fe | 0.3726 | 0.0137 | * | 0.1365 | 0.0956 | supports_H1 |
| 2 | M6_month_hour_fe | 0.4395 | 0.0022 | ** | 0.1243 | 0.0762 | supports_H1 |
| 3 | M7_year_month_hour_fe | 0.3306 | 0.0283 | * | 0.1968 | 0.1421 | supports_H1 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 7-2. M7 (전체 FE) 기준 전체 DV

| DV | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.3306 | 0.0283 | * | 0.1968 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.33 | 0.031 | * | 0.2011 | supports_H1 |
| log1p_favorite_count | 0.4629 | 0.007 | ** | 0.1831 | supports_H1 |
| log1p_retweet_count | 0.2538 | 0.1026 |  | 0.1586 | positive_not_significant |
| log1p_reply_count | 0.3009 | 0.0283 | * | 0.1731 | supports_H1 |
| log1p_quote_count | 0.2464 | 0.1363 |  | 0.1448 | positive_not_significant |
| log1p_bookmark_count | 0.1163 | 0.4569 |  | 0.1529 | positive_not_significant |

---

## 8. Supplemental Full-sample Binary H1 결과

**표본: n=978, IV=pred_humor_final_050**

### 8-1. Primary DV: log1p_engagement_total (전체 모형)

| n_time | model | β | p_value | sig | R² | adj_R² | flag |
|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | 0.5008 | 0.0 | *** | 0.0197 | 0.0187 | supports_H1 |
| 1 | M1_year_fe | 0.4207 | 0.0003 | *** | 0.0573 | 0.0485 | supports_H1 |
| 1 | M2_month_fe | 0.5085 | 0.0 | *** | 0.0992 | 0.088 | supports_H1 |
| 1 | M3_hour_fe | 0.5027 | 0.0 | *** | 0.0651 | 0.0436 | supports_H1 |
| 2 | M4_year_month_fe | 0.443 | 0.0001 | *** | 0.129 | 0.1108 | supports_H1 |
| 2 | M5_year_hour_fe | 0.4368 | 0.0002 | *** | 0.1002 | 0.0717 | supports_H1 |
| 2 | M6_month_hour_fe | 0.5182 | 0.0 | *** | 0.1377 | 0.1075 | supports_H1 |
| 3 | M7_year_month_hour_fe | 0.4677 | 0.0 | *** | 0.1646 | 0.128 | supports_H1 |

### 8-2. M7 기준 전체 DV

| DV | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.4677 | 0.0 | *** | 0.1646 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.4751 | 0.0 | *** | 0.1702 | supports_H1 |
| log1p_favorite_count | 0.6036 | 0.0 | *** | 0.1474 | supports_H1 |
| log1p_retweet_count | 0.3068 | 0.0091 | ** | 0.1367 | supports_H1 |
| log1p_reply_count | 0.436 | 0.0001 | *** | 0.1452 | supports_H1 |
| log1p_quote_count | 0.2078 | 0.0893 | † | 0.1346 | weak_support |
| log1p_bookmark_count | 0.1207 | 0.2744 |  | 0.1821 | positive_not_significant |

---

## 9. Probability-based Supplemental H1 결과

**표본: n=978, IV=p_humor_final_tfidf_logreg (0~1 확률값)**

### 9-1. Primary DV: log1p_engagement_total (전체 모형)

| n_time | model | β | p_value | sig | R² | adj_R² | flag |
|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | 1.2367 | 0.0005 | *** | 0.0125 | 0.0115 | supports_H1 |
| 1 | M1_year_fe | 0.9511 | 0.0086 | ** | 0.0511 | 0.0423 | supports_H1 |
| 1 | M2_month_fe | 1.2042 | 0.0005 | *** | 0.0907 | 0.0794 | supports_H1 |
| 1 | M3_hour_fe | 1.2295 | 0.0005 | *** | 0.0578 | 0.0361 | supports_H1 |
| 2 | M4_year_month_fe | 0.965 | 0.0065 | ** | 0.1216 | 0.1032 | supports_H1 |
| 2 | M5_year_hour_fe | 1.0381 | 0.0042 | ** | 0.0945 | 0.0658 | supports_H1 |
| 2 | M6_month_hour_fe | 1.2175 | 0.0004 | *** | 0.129 | 0.0985 | supports_H1 |
| 3 | M7_year_month_hour_fe | 1.0666 | 0.0027 | ** | 0.1574 | 0.1205 | supports_H1 |

### 9-2. M7 기준 전체 DV

| DV | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|
| log1p_engagement_total | 1.0666 | 0.0027 | ** | 0.1574 | supports_H1 |
| log1p_engagement_favorite_retweet | 1.0547 | 0.0034 | ** | 0.1626 | supports_H1 |
| log1p_favorite_count | 1.4941 | 0.0004 | *** | 0.1405 | supports_H1 |
| log1p_retweet_count | 0.5736 | 0.1206 |  | 0.1327 | positive_not_significant |
| log1p_reply_count | 1.2521 | 0.0002 | *** | 0.1428 | supports_H1 |
| log1p_quote_count | 0.4552 | 0.2355 |  | 0.1332 | positive_not_significant |
| log1p_bookmark_count | 0.0191 | 0.956 |  | 0.1811 | positive_not_significant |

---

## 10. 시간 변수 1개 추가 결과 비교 (Primary sample, DV=log1p_engagement_total)

| model | included_time_fe | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|---|
| M1_year_fe | year_FE | 0.3442 | 0.02 | * | 0.1083 | supports_H1 |
| M2_month_fe | month_FE | 0.4348 | 0.002 | ** | 0.0917 | supports_H1 |
| M3_hour_fe | hour_FE | 0.4991 | 0.0006 | *** | 0.0587 | supports_H1 |

---

## 11. 시간 변수 2개 조합 결과 비교 (Primary sample, DV=log1p_engagement_total)

| model | included_time_fe | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|---|
| M4_year_month_fe | year_FE+month_FE | 0.2848 | 0.0522 | † | 0.1743 | weak_support |
| M5_year_hour_fe | year_FE+hour_FE | 0.3726 | 0.0137 | * | 0.1365 | supports_H1 |
| M6_month_hour_fe | month_FE+hour_FE | 0.4395 | 0.0022 | ** | 0.1243 | supports_H1 |

---

## 12. 시간 변수 3개 전체 조합 결과 (Primary sample, DV=log1p_engagement_total)

| model | included_time_fe | β | p_value | sig | R² | flag |
|---|---|---|---|---|---|---|
| M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 0.3306 | 0.0283 | * | 0.1968 | supports_H1 |

---

## 13. Baseline 대비 β 및 p-value 변화

**Primary sample, primary DV (log1p_engagement_total)**

| n_time | model | β | p_value | sig | R² | AIC | BIC |
|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | 0.5043 | 0.0004 | *** | 0.0208 | 656.9391 | 665.7229 |
| 1 | M1_year_fe | 0.3442 | 0.02 | * | 0.1083 | 615.065 | 654.5923 |
| 1 | M2_month_fe | 0.4348 | 0.002 | ** | 0.0917 | 634.0585 | 691.1534 |
| 1 | M3_hour_fe | 0.4991 | 0.0006 | *** | 0.0587 | 671.3708 | 763.601 |
| 2 | M4_year_month_fe | 0.2848 | 0.0522 | † | 0.1743 | 591.1327 | 678.971 |
| 2 | M5_year_hour_fe | 0.3726 | 0.0137 | * | 0.1365 | 633.8696 | 756.8432 |
| 2 | M6_month_hour_fe | 0.4395 | 0.0022 | ** | 0.1243 | 650.2673 | 790.8086 |
| 3 | M7_year_month_hour_fe | 0.3306 | 0.0283 | * | 0.1968 | 612.6974 | 783.9822 |

---

## 14. 최종 해석

**Primary model 결과 (M7, primary sample n=597, conventional SE 기준):**

- IV: final_humor_binary
- DV: log1p_engagement_total
- β = 0.3306, p = 0.0283
- **판정: supports_H1**

Baseline (M0)의 β = 0.5043 (p=0.0004)에서 시간 FE 조합에 따른 β의 변화는 위 표(섹션 13)에 정리되어 있다. 어떤 시간 변수 조합을 추가하더라도 β의 방향성과 유의성 유지 여부를 확인하는 것이 이번 분석의 핵심이다.

---

## 15. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다. 시간 고정효과는 연도·월·시간대 수준의 공통 요인을 통제하지만, 관찰되지 않은 개별 게시글의 내용 특성이나 기타 혼동 요인은 통제되지 않는다.

---

## 16. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 17. 다음 단계

다음 단계에서 추가할 수 있는 변수(post format: text_length, is_quote_status 등; posting intensity: quarter_total_posts 등; log1p_view_count 등)는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
