# Wendy's H2 Step 2: Aggressive vs Other Humor with Time Fixed Effects 결과

## 1. 분석 목적

H2 Step 1에서 확인한 aggressive humor > other humor 관계가 Year FE, Month FE, Hour FE를 순차적으로 추가했을 때에도 유지되는지 확인한다. 8개 시간 FE 조합 모형(M0~M7)을 비교한다. post format controls는 이번 단계에서 추가하지 않는다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV, is_aggressive_humor, 시간 변수 |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation) |

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 5. 새 변수 생성 없음 확인

새로운 변수를 생성하지 않았다. is_aggressive_humor는 기존 H3 파일의 변수이다. Human validation IV는 in-memory에서만 사용하였다. post format 변수 미사용.

---

## 6. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| n | 564 |
| aggressive n | 200 |
| other_humor n | 364 |
| non_humor 포함 | False |
| 기준 범주 | other_humor (is_aggressive_humor=0) |
| 기준 연도 (year FE) | 2009 |
| 기준 월 (month FE) | 1 |
| 기준 시간 (hour FE) | 00 |

---

## 7. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| n | 278 |
| aggressive n | 95 |
| other_humor n | 183 |
| non_humor 포함 | False |

---

## 8. 사용한 시간 고정효과 조합

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

## 9. Model-based H2 결과 (primary DV)

**표본: n=564, IV=is_aggressive_humor, 기준=other_humor**

| n_time | model | included_FE | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | none | 0.4684 | 0.0021 | ** | 0.0167 | 0.0149 | supports_H2 |
| 1 | M1_year_fe | year_FE | 0.5463 | 0.0003 | *** | 0.0867 | 0.0719 | supports_H2 |
| 1 | M2_month_fe | month_FE | 0.3763 | 0.0106 | * | 0.1252 | 0.1062 | supports_H2 |
| 1 | M3_hour_fe | hour_FE | 0.5301 | 0.0006 | *** | 0.0879 | 0.0508 | supports_H2 |
| 2 | M4_year_month_fe | year_FE+month_FE | 0.4663 | 0.0016 | ** | 0.1775 | 0.1472 | supports_H2 |
| 2 | M5_year_hour_fe | year_FE+hour_FE | 0.6102 | 0.0001 | *** | 0.1556 | 0.108 | supports_H2 |
| 2 | M6_month_hour_fe | month_FE+hour_FE | 0.4261 | 0.0043 | ** | 0.1837 | 0.1329 | supports_H2 |
| 3 | M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 0.5199 | 0.0006 | *** | 0.2279 | 0.1672 | supports_H2 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 10. Model-based M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.5199 | 0.0006 | *** | 0.2279 | supports_H2 |
| log1p_engagement_favorite_retweet | 0.5407 | 0.0004 | *** | 0.233 | supports_H2 |
| log1p_favorite_count | 0.6504 | 0.0002 | *** | 0.2092 | supports_H2 |
| log1p_retweet_count | 0.4636 | 0.0047 | ** | 0.1891 | supports_H2 |
| log1p_reply_count | 0.223 | 0.1212 |  | 0.1769 | positive_not_significant |
| log1p_quote_count | 0.4178 | 0.0117 | * | 0.2018 | supports_H2 |
| log1p_bookmark_count | 0.4064 | 0.0057 | ** | 0.1997 | supports_H2 |

---

## 11. Human-coded Validation 결과 (primary DV, 부가 검증)

**표본: n=278, IV=final_humor_type_group(aggressive dummy)**

| n_time | model | included_FE | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | none | 0.7074 | 0.0007 | *** | 0.0413 | 0.0378 | supports_H2 |
| 1 | M1_year_fe | year_FE | 0.8195 | 0.0 | *** | 0.1881 | 0.164 | supports_H2 |
| 1 | M2_month_fe | month_FE | 0.5298 | 0.0112 | * | 0.1303 | 0.0909 | supports_H2 |
| 1 | M3_hour_fe | hour_FE | 0.8428 | 0.0 | *** | 0.2048 | 0.1429 | supports_H2 |
| 2 | M4_year_month_fe | year_FE+month_FE | 0.6082 | 0.0018 | ** | 0.2875 | 0.235 | supports_H2 |
| 2 | M5_year_hour_fe | year_FE+hour_FE | 0.9197 | 0.0 | *** | 0.3194 | 0.2459 | supports_H2 |
| 2 | M6_month_hour_fe | month_FE+hour_FE | 0.6971 | 0.001 | ** | 0.2658 | 0.1733 | supports_H2 |
| 3 | M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 0.7261 | 0.0003 | *** | 0.3813 | 0.2829 | supports_H2 |

---

## 12. Human-coded Validation M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.7261 | 0.0003 | *** | 0.3813 | supports_H2 |
| log1p_engagement_favorite_retweet | 0.7419 | 0.0003 | *** | 0.378 | supports_H2 |
| log1p_favorite_count | 0.7733 | 0.0005 | *** | 0.3596 | supports_H2 |
| log1p_retweet_count | 0.853 | 0.0001 | *** | 0.3415 | supports_H2 |
| log1p_reply_count | 0.2705 | 0.1435 |  | 0.2966 | positive_not_significant |
| log1p_quote_count | 0.8143 | 0.0004 | *** | 0.3538 | supports_H2 |
| log1p_bookmark_count | 0.7727 | 0.0002 | *** | 0.3122 | supports_H2 |

---

## 13. Baseline 대비 시간 FE 추가 후 β, p-value 변화 (primary DV)

| n_time | model | mb_β | mb_p | mb_sig | hv_β | hv_p | hv_sig |
|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | 0.4684 | 0.0021 | ** | 0.7074 | 0.0007 | *** |
| 1 | M1_year_fe | 0.5463 | 0.0003 | *** | 0.8195 | 0.0 | *** |
| 1 | M2_month_fe | 0.3763 | 0.0106 | * | 0.5298 | 0.0112 | * |
| 1 | M3_hour_fe | 0.5301 | 0.0006 | *** | 0.8428 | 0.0 | *** |
| 2 | M4_year_month_fe | 0.4663 | 0.0016 | ** | 0.6082 | 0.0018 | ** |
| 2 | M5_year_hour_fe | 0.6102 | 0.0001 | *** | 0.9197 | 0.0 | *** |
| 2 | M6_month_hour_fe | 0.4261 | 0.0043 | ** | 0.6971 | 0.001 | ** |
| 3 | M7_year_month_hour_fe | 0.5199 | 0.0006 | *** | 0.7261 | 0.0003 | *** |

mb=model_based, hv=human_validation

---

## 14. H2 주 분석 판정

**Model-based M7 (전체 시간 FE) 기준:**

| 표본 | β | p | 판정 |
|---|---|---|---|
| Model-based (n=564) | 0.5199 | 0.0006 | supports_H2 |
| Human validation (n=278) | 0.7261 | 0.0003 | supports_H2 |

---

## 15. 사람 코딩 결과는 부가 검증

Human validation 결과(n=278)는 부가 검증이며 주 분석을 대체하지 않는다.

---

## 16. Non_humor 제외 확인

H2 direct test에서 non_humor는 제외하였다. model-based in-sample: 0건, human validation in-sample: 0건.

---

## 17. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 변화시켰다는 주장을 할 수 없다.

---

## 18. 다음 단계

다음 단계에서 post format controls(text_length, hashtag_count, mention_count 등)를 추가할 수 있으나, 사용자 승인 후 진행한다.

---

*생성일: 2026-06-15*
