# Wendy's H2 Step 3: Aggressive vs Other Humor — Post Format Controls 결과

## 1. 분석 목적

H2 Step 2에서 year/month/hour FE를 모두 추가한 이후에도 aggressive humor > other humor 관계가 유지되었다. Step 3에서는 문헌 기반 post format controls(text_length, hashtag_count, mention_count)를 8개 조합(M0~M7)으로 투입하여 H2 관계의 강건성을 추가 확인한다.

---

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 other humor보다 post-level engagement가 높을 것이다.

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV, is_aggressive_humor, 시간 변수 |
| wendys_fast_weak_supervised_humor_dataset.csv | text_length, hashtag_count, mention_count |
| wendys_humor_review_sheet.csv | final_humor_type_group (human validation) |

---

## 4. 병합 안정성

| 항목 | 값 |
|---|---|
| 병합 key | id |
| left n (H3) | 978 |
| right n (humor dataset) | 978 |
| merged n | 978 |
| unmatched (H3→humor) | 0 |
| unmatched (H3→rv) | 0 |
| duplicate key (H3) | False |
| duplicate key (humor) | False |
| mb n 변화 | 564 (기대 564) |
| hv n 변화 | 278 (기대 278) |

병합 결과 안정적. sample size 변화 없음.

---

## 5. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 6. 새 변수 생성 없음 확인

text_length, hashtag_count, mention_count은 기존 wendys_fast_weak_supervised_humor_dataset.csv의 변수이다. is_aggressive_humor는 기존 H3 파일 변수이다. human validation IV는 in-memory에서만 사용하였다. 새 변수 생성 없음.

---

## 7. Model-based Humor-only Sample 구성

| 항목 | 값 |
|---|---|
| n | 564 |
| aggressive n | 200 |
| other_humor n | 364 |
| non_humor 포함 | False |
| 기준 범주 | other_humor (is_aggressive_humor=0) |

---

## 8. Human-coded Validation Sample 구성

| 항목 | 값 |
|---|---|
| n | 278 |
| aggressive n | 95 |
| other_humor n | 183 |
| non_humor 포함 | False |

---

## 9. 사용한 시간 고정효과

created_year FE, created_month FE, created_hour FE (전체 조합, M0~M7 공통)

---

## 10. 사용한 Post Format 변수

| 변수 | 결측 |
|---|---|
| text_length | 0건 |
| hashtag_count | 0건 |
| mention_count | 0건 |

---

## 11. 제외한 변수

emoji_count, url_count, is_quote_status, is_retweet_text, day_of_week, log1p_view_count, year_quarter FE, posting intensity 변수 전체 미사용.

---

## 12. Model-based H2 결과 (primary DV: log1p_engagement_total)

**표본: n=564, IV=is_aggressive_humor, 기준=other_humor**

| n_pf | model | post_format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.5199 | 0.0006 | *** | 0.2279 | 0.1672 | supports_H2 |
| 1 | M1_time_fe_text | text_length | 0.3454 | 0.0229 | * | 0.2598 | 0.2001 | supports_H2 |
| 1 | M2_time_fe_hashtag | hashtag_count | 0.5551 | 0.0002 | *** | 0.2498 | 0.1893 | supports_H2 |
| 1 | M3_time_fe_mention | mention_count | 0.5005 | 0.0005 | *** | 0.2975 | 0.2409 | supports_H2 |
| 2 | M4_time_fe_text_hashtag | text_length+hashtag_count | 0.4006 | 0.0087 | ** | 0.2695 | 0.2091 | supports_H2 |
| 2 | M5_time_fe_text_mention | text_length+mention_count | 0.37 | 0.0115 | * | 0.3153 | 0.2587 | supports_H2 |
| 2 | M6_time_fe_hashtag_mention | hashtag_count+mention_count | 0.526 | 0.0002 | *** | 0.3074 | 0.2501 | supports_H2 |
| 3 | M7_time_fe_all_post_format | text_length+hashtag_count+mention_count | 0.4056 | 0.006 | ** | 0.3195 | 0.2618 | supports_H2 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 13. Model-based M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.4056 | 0.006 | ** | 0.3195 | supports_H2 |
| log1p_engagement_favorite_retweet | 0.406 | 0.0064 | ** | 0.3269 | supports_H2 |
| log1p_favorite_count | 0.5017 | 0.0024 | ** | 0.3331 | supports_H2 |
| log1p_retweet_count | 0.3891 | 0.0196 | * | 0.23 | supports_H2 |
| log1p_reply_count | 0.2238 | 0.1101 |  | 0.2843 | positive_not_significant |
| log1p_quote_count | 0.4007 | 0.0188 | * | 0.2247 | supports_H2 |
| log1p_bookmark_count | 0.3786 | 0.0119 | * | 0.2295 | supports_H2 |

---

## 14. Human-coded Validation 결과 (primary DV, 부가 검증)

**표본: n=278, IV=final_humor_type_group(aggressive dummy)**

| n_pf | model | post_format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.7261 | 0.0003 | *** | 0.3813 | 0.2829 | supports_H2 |
| 1 | M1_time_fe_text | text_length | 0.6087 | 0.0021 | ** | 0.4134 | 0.3173 | supports_H2 |
| 1 | M2_time_fe_hashtag | hashtag_count | 0.7539 | 0.0002 | *** | 0.392 | 0.2923 | supports_H2 |
| 1 | M3_time_fe_mention | mention_count | 0.7196 | 0.0002 | *** | 0.4308 | 0.3376 | supports_H2 |
| 2 | M4_time_fe_text_hashtag | text_length+hashtag_count | 0.6359 | 0.0014 | ** | 0.4172 | 0.3188 | supports_H2 |
| 2 | M5_time_fe_text_mention | text_length+mention_count | 0.63 | 0.0011 | ** | 0.4491 | 0.3561 | supports_H2 |
| 2 | M6_time_fe_hashtag_mention | hashtag_count+mention_count | 0.7343 | 0.0001 | *** | 0.4335 | 0.3379 | supports_H2 |
| 3 | M7_time_fe_all_post_format | text_length+hashtag_count+mention_count | 0.6405 | 0.001 | ** | 0.4497 | 0.354 | supports_H2 |

---

## 15. Human-coded Validation M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.6405 | 0.001 | ** | 0.4497 | supports_H2 |
| log1p_engagement_favorite_retweet | 0.64 | 0.0012 | ** | 0.4515 | supports_H2 |
| log1p_favorite_count | 0.6654 | 0.0018 | ** | 0.4315 | supports_H2 |
| log1p_retweet_count | 0.7902 | 0.0003 | *** | 0.3894 | supports_H2 |
| log1p_reply_count | 0.2825 | 0.1221 |  | 0.3491 | positive_not_significant |
| log1p_quote_count | 0.798 | 0.0006 | *** | 0.3664 | supports_H2 |
| log1p_bookmark_count | 0.7369 | 0.0004 | *** | 0.3484 | supports_H2 |

---

## 16. Time FE only 대비 Post Format 추가 후 β, p-value 변화 (primary DV)

| n_pf | model | mb_β | mb_p | mb_sig | hv_β | hv_p | hv_sig |
|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | 0.5199 | 0.0006 | *** | 0.7261 | 0.0003 | *** |
| 1 | M1_time_fe_text | 0.3454 | 0.0229 | * | 0.6087 | 0.0021 | ** |
| 1 | M2_time_fe_hashtag | 0.5551 | 0.0002 | *** | 0.7539 | 0.0002 | *** |
| 1 | M3_time_fe_mention | 0.5005 | 0.0005 | *** | 0.7196 | 0.0002 | *** |
| 2 | M4_time_fe_text_hashtag | 0.4006 | 0.0087 | ** | 0.6359 | 0.0014 | ** |
| 2 | M5_time_fe_text_mention | 0.37 | 0.0115 | * | 0.63 | 0.0011 | ** |
| 2 | M6_time_fe_hashtag_mention | 0.526 | 0.0002 | *** | 0.7343 | 0.0001 | *** |
| 3 | M7_time_fe_all_post_format | 0.4056 | 0.006 | ** | 0.6405 | 0.001 | ** |

mb=model_based, hv=human_validation

---

## 17. H2 주 분석 판정

**Model-based M7 (Time FE + all post format controls) 기준:**

| 표본 | β | p | 판정 |
|---|---|---|---|
| Model-based (n=564) | 0.4056 | 0.006 | supports_H2 |
| Human validation (n=278) | 0.6405 | 0.001 | supports_H2 |

---

## 18. 사람 코딩 결과는 부가 검증

Human validation 결과(n=278)는 부가 검증이다. primary evidence는 model-based 결과이며, 사람 코딩은 전체 데이터 분류의 기준 라벨 및 검증층으로 해석한다.

---

## 19. Non_humor 제외 확인

H2 direct test에서 non_humor는 제외하였다. model-based in-sample: 0건, human validation in-sample: 0건.

---

## 20. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, aggressive humor 여부가 engagement를 인과적으로 변화시켰다는 주장을 할 수 없다.

---

## 21. H1/H3 수행하지 않음 확인

이번 작업에서 H1 및 H3 분석은 수행하지 않았다. H2 direct test만 실시하였다.

---

## 22. 다음 단계

다음 단계는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
