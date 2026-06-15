# Wendy's H1 Literature-based Post Format Controls 결과

## 1. 분석 목적

H1 분석에서 기존 시간 고정효과 모형(year+month+hour FE)에 문헌 기반 post format 통제변수를 순차적으로 추가하여, 유머 게시글 여부와 post-level engagement 간 관계가 게시글 형식 차이를 고려한 뒤에도 유지되는지 확인한다. 주 분석은 full-sample (n=978)이며, 사람 코딩 597건은 부가 검증이다.

---

## 2. 문헌 기반 Post Format 변수

| 문헌 변수명 | Wendy's 데이터 변수 | 결측 여부 |
|---|---|---|
| Text Length | text_length | 없음 |
| # of Hashtags | hashtag_count | 없음 |
| # of Handle tags | mention_count | 없음 |
| # of Emojis | emoji_count | 없음 |

추가하지 않은 변수: url_count, is_quote_status, is_retweet_text, image/video 관련 변수

---

## 3. 사용한 파일

| 파일 | 역할 |
|---|---|
| wendys_final_humor_presence_full_predictions.csv | IV (final_humor_binary, pred_humor_final_050, p_humor_final_tfidf_logreg) |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | DV (log1p_*), 시간 변수 |
| wendys_fast_weak_supervised_humor_dataset.csv | post format 변수 (text_length 등 4개) |

---

## 4. 병합 안정성 확인

| 항목 | 값 |
|---|---|
| 병합 key | id |
| pred n | 978 |
| H3 n | 978 |
| fast n | 978 |
| 병합 후 n | 978 |
| unmatched (H3) | 0 |
| unmatched (fast) | 0 |
| duplicate key | pred=False, h3=False, fast=False |
| full n=978 유지 | True |
| primary n=597 유지 | True |
| post format 변수 결측으로 sample 감소 | False |

---

## 5. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 6. 새 변수 생성 없음 확인

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 파일의 컬럼만 사용하였다. url_count, is_quote_status, is_retweet_text, day_of_week 미사용. log1p_view_count 미사용. year_quarter FE 미사용.

---

## 7. 표본 구성

| 항목 | 값 |
|---|---|
| Full sample (주 분석) | n=978 |
| Full predicted humor=1 | 564 |
| Full predicted humor=0 | 414 |
| Human-labeled sample (부가 검증) | n=597 |
| Human humor=1 | 309 |
| Human humor=0 | 288 |

---

## 8. 사용한 시간 고정효과

created_year FE + created_month FE + created_hour FE (전 모형 공통 포함)

---

## 9. Post Format 변수 추가 순서

M0 → M1(+text_length) → M2(+hashtag_count) → M3(+mention_count) → M4(+emoji_count)

---

## 10. Full-sample Binary H1 결과

**IV: pred_humor_final_050, n=978**

### 10-1. Primary DV: log1p_engagement_total

| n_fmt | model | included_format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.4677 | 0.0 | *** | 0.1646 | 0.128 | supports_H1 |
| 1 | M1_add_text_length | text_length | 0.5134 | 0.0 | *** | 0.1995 | 0.1635 | supports_H1 |
| 2 | M2_add_hashtag | text_length+hashtag_count | 0.5039 | 0.0 | *** | 0.2044 | 0.1678 | supports_H1 |
| 3 | M3_add_mention | text_length+hashtag_count+mention_count | 0.2918 | 0.0088 | ** | 0.249 | 0.2135 | supports_H1 |
| 4 | M4_add_emoji | text_length+hashtag_count+mention_count+emoji_count | 0.2918 | 0.0088 | ** | 0.2491 | 0.2129 | supports_H1 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

### 10-2. M4 (전체 post format 통제) 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.2918 | 0.0088 | ** | 0.2491 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.3138 | 0.0053 | ** | 0.2545 | supports_H1 |
| log1p_favorite_count | 0.3322 | 0.0109 | * | 0.2615 | supports_H1 |
| log1p_retweet_count | 0.1995 | 0.097 | † | 0.1655 | weak_support |
| log1p_reply_count | 0.1405 | 0.1758 |  | 0.2667 | positive_not_significant |
| log1p_quote_count | 0.0454 | 0.7159 |  | 0.1648 | positive_not_significant |
| log1p_bookmark_count | -0.0376 | 0.7373 |  | 0.2186 | not_support |

---

## 11. Full-sample Probability H1 결과

**IV: p_humor_final_tfidf_logreg, n=978**

### 11-1. Primary DV: log1p_engagement_total

| n_fmt | model | included_format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 1.0666 | 0.0027 | ** | 0.1574 | 0.1205 | supports_H1 |
| 1 | M1_add_text_length | text_length | 1.5082 | 0.0 | *** | 0.1968 | 0.1607 | supports_H1 |
| 2 | M2_add_hashtag | text_length+hashtag_count | 1.4994 | 0.0 | *** | 0.2022 | 0.1655 | supports_H1 |
| 3 | M3_add_mention | text_length+hashtag_count+mention_count | 0.8404 | 0.0175 | * | 0.248 | 0.2125 | supports_H1 |
| 4 | M4_add_emoji | text_length+hashtag_count+mention_count+emoji_count | 0.8392 | 0.0177 | * | 0.2481 | 0.2118 | supports_H1 |

### 11-2. M4 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.8392 | 0.0177 | * | 0.2481 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.8952 | 0.0123 | * | 0.2533 | supports_H1 |
| log1p_favorite_count | 1.0534 | 0.011 | * | 0.2615 | supports_H1 |
| log1p_retweet_count | 0.4084 | 0.2846 |  | 0.1641 | positive_not_significant |
| log1p_reply_count | 0.5348 | 0.1046 |  | 0.2674 | positive_not_significant |
| log1p_quote_count | 0.0475 | 0.9046 |  | 0.1647 | positive_not_significant |
| log1p_bookmark_count | -0.3721 | 0.296 |  | 0.2194 | not_support |

---

## 12. Human-labeled Validation 결과 (부가 검증)

**IV: final_humor_binary, n=597**

### 12-1. Primary DV: log1p_engagement_total

| n_fmt | model | included_format_vars | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0 | M0_time_fe_only | none | 0.3306 | 0.0283 | * | 0.1968 | 0.1421 | supports_H1 |
| 1 | M1_add_text_length | text_length | 0.3805 | 0.0099 | ** | 0.2366 | 0.1831 | supports_H1 |
| 2 | M2_add_hashtag | text_length+hashtag_count | 0.3893 | 0.0085 | ** | 0.2377 | 0.1829 | supports_H1 |
| 3 | M3_add_mention | text_length+hashtag_count+mention_count | 0.3171 | 0.0307 | * | 0.26 | 0.2053 | supports_H1 |
| 4 | M4_add_emoji | text_length+hashtag_count+mention_count+emoji_count | 0.3162 | 0.0312 | * | 0.2604 | 0.2044 | supports_H1 |

### 12-2. M4 기준 전체 DV

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.3162 | 0.0312 | * | 0.2604 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.326 | 0.0284 | * | 0.2673 | supports_H1 |
| log1p_favorite_count | 0.4371 | 0.0085 | ** | 0.2588 | supports_H1 |
| log1p_retweet_count | 0.2429 | 0.1155 |  | 0.1959 | positive_not_significant |
| log1p_reply_count | 0.2197 | 0.0937 | † | 0.2673 | weak_support |
| log1p_quote_count | 0.2122 | 0.1998 |  | 0.1686 | positive_not_significant |
| log1p_bookmark_count | 0.0764 | 0.6237 |  | 0.1846 | positive_not_significant |

---

## 13. Post Format 변수 추가 전후 β, p-value 변화 (primary DV)

| model | fb_β | fb_p | fb_sig | fp_β | fp_p | fp_sig | hv_β | hv_p | hv_sig |
|---|---|---|---|---|---|---|---|---|---|
| M0_time_fe_only | 0.4677 | 0.0 | *** | 1.0666 | 0.0027 | ** | 0.3306 | 0.0283 | * |
| M1_add_text_length | 0.5134 | 0.0 | *** | 1.5082 | 0.0 | *** | 0.3805 | 0.0099 | ** |
| M2_add_hashtag | 0.5039 | 0.0 | *** | 1.4994 | 0.0 | *** | 0.3893 | 0.0085 | ** |
| M3_add_mention | 0.2918 | 0.0088 | ** | 0.8404 | 0.0175 | * | 0.3171 | 0.0307 | * |
| M4_add_emoji | 0.2918 | 0.0088 | ** | 0.8392 | 0.0177 | * | 0.3162 | 0.0312 | * |

fb=full_binary, fp=full_probability, hv=human_validation

---

## 14. H1 주 분석 판정

**Full-sample binary 기준 (n=978, IV=pred_humor_final_050, DV=log1p_engagement_total):**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 (time FE only) | 0.4677 | 0.0 | supports_H1 |
| M4 (all format controls) | 0.2918 | 0.0088 | supports_H1 |

**Full-sample probability 기준:**

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0 | 1.0666 | 0.0027 | supports_H1 |
| M4 | 0.8392 | 0.0177 | supports_H1 |

**판정: H1 지지 여부 — full-sample binary M4 기준: supports_H1**

---

## 15. 사람 코딩 결과는 부가 검증

사람 코딩 597건 결과는 부가 검증이며, 주 분석(full-sample n=978)을 대체하지 않는다. Human validation M0 β=0.3306 (p=0.0283), M4 β=0.3162 (p=0.0312).

---

## 16. 인과관계 아님 — 관측적 연관성 분석

본 분석은 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 증가시켰다는 인과관계를 주장할 수 없다. 시간 고정효과 및 post format 변수는 측정 가능한 일부 혼동 요인을 통제하지만, 관찰되지 않은 개별 게시글의 콘텐츠 특성은 통제되지 않는다.

---

## 17. H2/H3 수행 여부

이번 작업에서는 H1 분석만 수행하였으며, H2와 H3는 수행하지 않았다.

---

## 18. 다음 단계

다음 단계에서 추가할 수 있는 변수(posting intensity: quarter_total_posts 등; log1p_view_count 등)는 사용자 승인 후 결정한다.

---

*생성일: 2026-06-15*
