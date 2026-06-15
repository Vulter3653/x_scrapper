# Wendy's H1 Three Post Format Controls Combination Check 결과

## 1. 분석 목적

H1 분석에서 시간 FE(year+month+hour) 기반 모형에 text_length, hashtag_count, mention_count 3개 post format 변수를 1개 / 2개 조합 / 3개 전체로 나누어 8가지 모형을 비교한다. 주 분석은 full-sample (n=978)이며, 사람 코딩 597건은 부가 검증이다.

---

## 2. 사용한 Post Format 변수 3개

| 변수 | 설명 |
|---|---|
| text_length | 게시글 텍스트 길이 |
| hashtag_count | 해시태그 수 |
| mention_count | 멘션(@) 수 |

---

## 3. 제외한 변수

emoji_count, url_count, is_quote_status, is_retweet_text

---

## 4. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_final_humor_presence_full_predictions.csv | IV |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV, 시간 변수 |
| wendys_fast_weak_supervised_humor_dataset.csv | post format 변수 |

---

## 5. 병합 안정성 확인

| 항목 | 값 |
|---|---|
| 병합 key | id |
| pred n | 978 |
| H3 n | 978 |
| fast n | 978 |
| 병합 후 n | 978 |
| unmatched (H3) | 0 |
| unmatched (fast) | 0 |
| duplicate key | False |
| full n=978 유지 | True |
| primary n=597 유지 | True |
| post format 결측으로 sample 감소 | False |

---

## 6. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 7. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. 제외 변수(emoji_count 등) 미사용 확인. day_of_week 생성 없음.

---

## 8. 표본 구성

| 항목 | 값 |
|---|---|
| Full sample (주 분석) | n=978 |
| Full predicted humor=1 | 564 |
| Full predicted humor=0 | 414 |
| Human-labeled sample (부가 검증) | n=597 |
| Human humor=1 | 309 |
| Human humor=0 | 288 |

---

## 9. 사용한 시간 고정효과

created_year FE + created_month FE + created_hour FE (전 모형 공통 포함)

---

## 10. Post Format 변수 1개 추가 결과 (Primary DV: log1p_engagement_total)

### Full-sample binary (n=978, IV=pred_humor_final_050)

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Full-sample probability (n=978, IV=p_humor_final_tfidf_logreg)

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Human validation (n=597, IV=final_humor_binary)

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

---

## 11. Post Format 변수 2개 조합 결과 (Primary DV: log1p_engagement_total)

### Full-sample binary

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Full-sample probability

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Human validation

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

---

## 12. Post Format 변수 3개 전체 조합 결과 (Primary DV: log1p_engagement_total)

### Full-sample binary

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Full-sample probability

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

### Human validation

| model | format_vars | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|

---

## 13. Full-sample Binary H1 전체 결과

**IV: pred_humor_final_050, n=978**

### 13-1. Primary DV: log1p_engagement_total (전체 모형)

| n_fmt | model | format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.4677 | 0.0 | *** | 0.1646 | 0.128 | supports_H1 |
| 1 | M1_text_length | text_length | 0.5134 | 0.0 | *** | 0.1995 | 0.1635 | supports_H1 |
| 1 | M2_hashtag | hashtag_count | 0.4601 | 0.0 | *** | 0.1785 | 0.1416 | supports_H1 |
| 1 | M3_mention | mention_count | 0.2285 | 0.0402 | * | 0.2332 | 0.1988 | supports_H1 |
| 2 | M4_text_hashtag | text_length+hashtag_count | 0.5039 | 0.0 | *** | 0.2044 | 0.1678 | supports_H1 |
| 2 | M5_text_mention | text_length+mention_count | 0.2898 | 0.0092 | ** | 0.2486 | 0.214 | supports_H1 |
| 2 | M6_hashtag_mention | hashtag_count+mention_count | 0.2377 | 0.0329 | * | 0.2353 | 0.2001 | supports_H1 |
| 3 | M7_all_three | text_length+hashtag_count+mention_count | 0.2918 | 0.0088 | ** | 0.249 | 0.2135 | supports_H1 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 13-2. M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.2918 | 0.0088 | ** | 0.249 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.3138 | 0.0053 | ** | 0.2543 | supports_H1 |
| log1p_favorite_count | 0.3321 | 0.0109 | * | 0.2612 | supports_H1 |
| log1p_retweet_count | 0.1994 | 0.0968 | † | 0.1654 | weak_support |
| log1p_reply_count | 0.1405 | 0.1758 |  | 0.2663 | positive_not_significant |
| log1p_quote_count | 0.0454 | 0.7157 |  | 0.1648 | positive_not_significant |
| log1p_bookmark_count | -0.0377 | 0.737 |  | 0.2183 | not_support |

---

## 14. Full-sample Probability H1 전체 결과

**IV: p_humor_final_tfidf_logreg, n=978**

### 14-1. Primary DV: log1p_engagement_total

| n_fmt | model | format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 1.0666 | 0.0027 | ** | 0.1574 | 0.1205 | supports_H1 |
| 1 | M1_text_length | text_length | 1.5082 | 0.0 | *** | 0.1968 | 0.1607 | supports_H1 |
| 1 | M2_hashtag | hashtag_count | 1.125 | 0.0015 | ** | 0.1727 | 0.1355 | supports_H1 |
| 1 | M3_mention | mention_count | 0.4463 | 0.197 |  | 0.2311 | 0.1966 | positive_not_significant |
| 2 | M4_text_hashtag | text_length+hashtag_count | 1.4994 | 0.0 | *** | 0.2022 | 0.1655 | supports_H1 |
| 2 | M5_text_mention | text_length+mention_count | 0.8274 | 0.0191 | * | 0.2475 | 0.2129 | supports_H1 |
| 2 | M6_hashtag_mention | hashtag_count+mention_count | 0.5017 | 0.1486 |  | 0.2333 | 0.198 | positive_not_significant |
| 3 | M7_all_three | text_length+hashtag_count+mention_count | 0.8404 | 0.0175 | * | 0.248 | 0.2125 | supports_H1 |

### 14-2. M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.8404 | 0.0175 | * | 0.248 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.8967 | 0.0121 | * | 0.2531 | supports_H1 |
| log1p_favorite_count | 1.0553 | 0.0108 | * | 0.2612 | supports_H1 |
| log1p_retweet_count | 0.4094 | 0.2832 |  | 0.164 | positive_not_significant |
| log1p_reply_count | 0.5367 | 0.1033 |  | 0.2669 | positive_not_significant |
| log1p_quote_count | 0.0475 | 0.9045 |  | 0.1647 | positive_not_significant |
| log1p_bookmark_count | -0.3703 | 0.2981 |  | 0.2191 | not_support |

---

## 15. Human-labeled Validation 전체 결과 (부가 검증)

**IV: final_humor_binary, n=597**

### 15-1. Primary DV: log1p_engagement_total

| n_fmt | model | format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.3306 | 0.0283 | * | 0.1968 | 0.1421 | supports_H1 |
| 1 | M1_text_length | text_length | 0.3805 | 0.0099 | ** | 0.2366 | 0.1831 | supports_H1 |
| 1 | M2_hashtag | hashtag_count | 0.3529 | 0.0193 | * | 0.2021 | 0.1462 | supports_H1 |
| 1 | M3_mention | mention_count | 0.257 | 0.0812 | † | 0.2379 | 0.1845 | weak_support |
| 2 | M4_text_hashtag | text_length+hashtag_count | 0.3893 | 0.0085 | ** | 0.2377 | 0.1829 | supports_H1 |
| 2 | M5_text_mention | text_length+mention_count | 0.3116 | 0.033 | * | 0.2596 | 0.2064 | supports_H1 |
| 2 | M6_hashtag_mention | hashtag_count+mention_count | 0.2723 | 0.0658 | † | 0.2396 | 0.1849 | weak_support |
| 3 | M7_all_three | text_length+hashtag_count+mention_count | 0.3171 | 0.0307 | * | 0.26 | 0.2053 | supports_H1 |

### 15-2. M7 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.3171 | 0.0307 | * | 0.26 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.327 | 0.0278 | * | 0.2667 | supports_H1 |
| log1p_favorite_count | 0.4379 | 0.0083 | ** | 0.2584 | supports_H1 |
| log1p_retweet_count | 0.2435 | 0.1143 |  | 0.1956 | positive_not_significant |
| log1p_reply_count | 0.2202 | 0.0926 | † | 0.2671 | weak_support |
| log1p_quote_count | 0.2128 | 0.1981 |  | 0.1684 | positive_not_significant |
| log1p_bookmark_count | 0.0771 | 0.6203 |  | 0.1843 | positive_not_significant |

---

## 16. Post Format 변수 추가 전후 β, p-value 변화 (primary DV)

| model | format_vars | fb_β | fb_p | fb_sig | fp_β | fp_p | fp_sig | hv_β | hv_p | hv_sig |
|---|---|---|---|---|---|---|---|---|---|---|
| M0_time_fe_only | none | 0.4677 | 0.0 | *** | 1.0666 | 0.0027 | ** | 0.3306 | 0.0283 | * |
| M1_text_length | text_length | 0.5134 | 0.0 | *** | 1.5082 | 0.0 | *** | 0.3805 | 0.0099 | ** |
| M2_hashtag | hashtag_count | 0.4601 | 0.0 | *** | 1.125 | 0.0015 | ** | 0.3529 | 0.0193 | * |
| M3_mention | mention_count | 0.2285 | 0.0402 | * | 0.4463 | 0.197 |  | 0.257 | 0.0812 | † |
| M4_text_hashtag | text_length+hashtag_count | 0.5039 | 0.0 | *** | 1.4994 | 0.0 | *** | 0.3893 | 0.0085 | ** |
| M5_text_mention | text_length+mention_count | 0.2898 | 0.0092 | ** | 0.8274 | 0.0191 | * | 0.3116 | 0.033 | * |
| M6_hashtag_mention | hashtag_count+mention_count | 0.2377 | 0.0329 | * | 0.5017 | 0.1486 |  | 0.2723 | 0.0658 | † |
| M7_all_three | text_length+hashtag_count+mention_count | 0.2918 | 0.0088 | ** | 0.8404 | 0.0175 | * | 0.3171 | 0.0307 | * |

fb=full_binary, fp=full_probability, hv=human_validation

---

## 17. H1 주 분석 판정

**Full-sample binary 기준 (n=978, IV=pred_humor_final_050, DV=log1p_engagement_total):**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 (time FE only) | 0.4677 | 0.0 | supports_H1 |
| M7 (all 3 format) | 0.2918 | 0.0088 | supports_H1 |

**Full-sample probability 기준:**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 | 1.0666 | 0.0027 | supports_H1 |
| M7 | 0.8404 | 0.0175 | supports_H1 |

**판정: H1 지지 여부 — full-sample binary M7 기준: supports_H1**

---

## 18. 사람 코딩 결과는 부가 검증

Human validation M0 β=0.3306 (p=0.0283), M7 β=0.3171 (p=0.0307). 사람 코딩 결과는 주 분석(full-sample)을 대체하지 않는다.

---

## 19. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다.

---

## 20. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 21. 다음 단계

다음 단계에서 추가할 수 있는 변수는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
