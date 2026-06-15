# Wendy's H1 Time Fixed Effects Full-sample Comparison 결과

## 1. 작업 목적

기존 H1 time FE combination 분석 결과 중, full-sample (n=978) 결과를 primary human-labeled sample (n=597) 결과와 같은 수준으로 상세 비교한다. 새 회귀분석은 수행하지 않았으며, 기존 결과 파일을 읽어 정리하였다.

---

## 2. 사용한 결과 파일

| 파일 | 역할 |
|---|---|
| wendys_h1_time_fe_combinations_primary_human_results.csv | Primary human-labeled 결과 (n=597) |
| wendys_h1_time_fe_combinations_fullsample_binary_results.csv | Full-sample binary 결과 (n=978) |
| wendys_h1_time_fe_combinations_probability_results.csv | Full-sample probability 결과 (n=978) |
| wendys_h1_time_fe_combinations_diagnostics.csv | 진단 정보 |

---

## 3. 새 회귀분석 수행 없음 확인

이번 작업에서는 새 회귀분석을 수행하지 않았다. 기존 결과 파일의 수치를 읽어서 비교표와 요약문만 작성하였다.

---

## 4. 원본 posts.json 변경 없음 확인

data/wendys/posts.json 변경 여부: **False**

---

## 5. 새 변수 생성 없음 확인

이번 작업에서 새로운 변수를 생성하지 않았다. 추가 통제변수 없음. day_of_week 생성 없음.

---

## 6. 비교 대상 표본 설명

| 표본 구분 | n | IV | 근거 |
|---|---|---|---|
| Primary human-labeled | 597 | final_humor_binary | 사람이 직접 라벨링한 결과 — **primary evidence** |
| Full-sample binary | 978 | pred_humor_final_050 | TF-IDF LogReg 모델 예측값 (이진) — **supplemental evidence** |
| Full-sample probability | 978 | p_humor_final_tfidf_logreg | TF-IDF LogReg 예측 확률값 — **supplemental evidence** |

primary evidence와 supplemental evidence의 구분은 아래 섹션 11에서 상세 설명.

---

## 7. Primary Human-labeled Sample 결과 요약

**DV: log1p_engagement_total, IV: final_humor_binary, n=597**

| n_time | model | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|---|
| 0 | M0_baseline | 0.5043 | 0.0004 | *** | 0.0208 | supports_H1 |
| 1 | M1_year_fe | 0.3442 | 0.02 | * | 0.1083 | supports_H1 |
| 1 | M2_month_fe | 0.4348 | 0.002 | ** | 0.0917 | supports_H1 |
| 1 | M3_hour_fe | 0.4991 | 0.0006 | *** | 0.0587 | supports_H1 |
| 2 | M4_year_month_fe | 0.2848 | 0.0522 | † | 0.1743 | weak_support |
| 2 | M5_year_hour_fe | 0.3726 | 0.0137 | * | 0.1365 | supports_H1 |
| 2 | M6_month_hour_fe | 0.4395 | 0.0022 | ** | 0.1243 | supports_H1 |
| 3 | M7_year_month_hour_fe | 0.3306 | 0.0283 | * | 0.1968 | supports_H1 |

* p<.05, ** p<.01, *** p<.001, † p<.10 (conventional SE 기준)

---

## 8. Full-sample Binary 결과 상세 (primary DV)

**DV: log1p_engagement_total, IV: pred_humor_final_050, n=978**

| n_time | model | FE 포함 | n | IV | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | none | 978 | pred_humor_final_050 | 0.5008 | 0.0 | *** | 0.0197 | 0.0187 | supports_H1 |
| 1 | M1_year_fe | year_FE | 978 | pred_humor_final_050 | 0.4207 | 0.0003 | *** | 0.0573 | 0.0485 | supports_H1 |
| 1 | M2_month_fe | month_FE | 978 | pred_humor_final_050 | 0.5085 | 0.0 | *** | 0.0992 | 0.088 | supports_H1 |
| 1 | M3_hour_fe | hour_FE | 978 | pred_humor_final_050 | 0.5027 | 0.0 | *** | 0.0651 | 0.0436 | supports_H1 |
| 2 | M4_year_month_fe | year_FE+month_FE | 978 | pred_humor_final_050 | 0.443 | 0.0001 | *** | 0.129 | 0.1108 | supports_H1 |
| 2 | M5_year_hour_fe | year_FE+hour_FE | 978 | pred_humor_final_050 | 0.4368 | 0.0002 | *** | 0.1002 | 0.0717 | supports_H1 |
| 2 | M6_month_hour_fe | month_FE+hour_FE | 978 | pred_humor_final_050 | 0.5182 | 0.0 | *** | 0.1377 | 0.1075 | supports_H1 |
| 3 | M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 978 | pred_humor_final_050 | 0.4677 | 0.0 | *** | 0.1646 | 0.128 | supports_H1 |

---

## 9. Full-sample Probability 결과 상세 (primary DV)

**DV: log1p_engagement_total, IV: p_humor_final_tfidf_logreg, n=978**

| n_time | model | FE 포함 | n | IV | β | p | sig | R² | adj_R² | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | M0_baseline | none | 978 | p_humor_final_tfidf_logreg | 1.2367 | 0.0005 | *** | 0.0125 | 0.0115 | supports_H1 |
| 1 | M1_year_fe | year_FE | 978 | p_humor_final_tfidf_logreg | 0.9511 | 0.0086 | ** | 0.0511 | 0.0423 | supports_H1 |
| 1 | M2_month_fe | month_FE | 978 | p_humor_final_tfidf_logreg | 1.2042 | 0.0005 | *** | 0.0907 | 0.0794 | supports_H1 |
| 1 | M3_hour_fe | hour_FE | 978 | p_humor_final_tfidf_logreg | 1.2295 | 0.0005 | *** | 0.0578 | 0.0361 | supports_H1 |
| 2 | M4_year_month_fe | year_FE+month_FE | 978 | p_humor_final_tfidf_logreg | 0.965 | 0.0065 | ** | 0.1216 | 0.1032 | supports_H1 |
| 2 | M5_year_hour_fe | year_FE+hour_FE | 978 | p_humor_final_tfidf_logreg | 1.0381 | 0.0042 | ** | 0.0945 | 0.0658 | supports_H1 |
| 2 | M6_month_hour_fe | month_FE+hour_FE | 978 | p_humor_final_tfidf_logreg | 1.2175 | 0.0004 | *** | 0.129 | 0.0985 | supports_H1 |
| 3 | M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 978 | p_humor_final_tfidf_logreg | 1.0666 | 0.0027 | ** | 0.1574 | 0.1205 | supports_H1 |

---

## 10. Human vs Full-sample 비교표 (primary DV)

**DV: log1p_engagement_total**

| model | FE | human β | human p | human sig | human 판정 | full_bin β | full_bin p | full_bin sig | full_bin 판정 | full_prob β | full_prob p | full_prob sig | full_prob 판정 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0_baseline | none | 0.5043 | 0.0004 | *** | supports_H1 | 0.5008 | 0.0 | *** | supports_H1 | 1.2367 | 0.0005 | *** | supports_H1 |
| M1_year_fe | year_FE | 0.3442 | 0.02 | * | supports_H1 | 0.4207 | 0.0003 | *** | supports_H1 | 0.9511 | 0.0086 | ** | supports_H1 |
| M2_month_fe | month_FE | 0.4348 | 0.002 | ** | supports_H1 | 0.5085 | 0.0 | *** | supports_H1 | 1.2042 | 0.0005 | *** | supports_H1 |
| M3_hour_fe | hour_FE | 0.4991 | 0.0006 | *** | supports_H1 | 0.5027 | 0.0 | *** | supports_H1 | 1.2295 | 0.0005 | *** | supports_H1 |
| M4_year_month_fe | year_FE+month_FE | 0.2848 | 0.0522 | † | weak_support | 0.443 | 0.0001 | *** | supports_H1 | 0.965 | 0.0065 | ** | supports_H1 |
| M5_year_hour_fe | year_FE+hour_FE | 0.3726 | 0.0137 | * | supports_H1 | 0.4368 | 0.0002 | *** | supports_H1 | 1.0381 | 0.0042 | ** | supports_H1 |
| M6_month_hour_fe | month_FE+hour_FE | 0.4395 | 0.0022 | ** | supports_H1 | 0.5182 | 0.0 | *** | supports_H1 | 1.2175 | 0.0004 | *** | supports_H1 |
| M7_year_month_hour_fe | year_FE+month_FE+hour_FE | 0.3306 | 0.0283 | * | supports_H1 | 0.4677 | 0.0 | *** | supports_H1 | 1.0666 | 0.0027 | ** | supports_H1 |

---

## 11. Primary Evidence와 Supplemental Evidence 구분

사람이 직접 라벨링한 597건 결과가 **primary evidence**이다. 전체 978건 결과는 모델 예측값을 독립변수로 사용하였으므로 **supplemental evidence**에 해당한다. 전체 데이터 결과가 더 강한 유의성을 보이더라도 사람 라벨 결과를 대체하지 않는다. 모델 예측값의 오분류 가능성이 있으며, 사람 라벨 결과가 측정 정확도 측면에서 우선한다.

---

## 12. 해석

### 질문 1. 사람 라벨 597건에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): M0_baseline, M1_year_fe, M2_month_fe, M3_hour_fe, M5_year_hour_fe, M6_month_hour_fe, M7_year_month_hour_fe

Weak support: M4_year_month_fe

→ M4(year+month FE)에서만 p=0.0522로 weak_support에 그쳤으며, M7(year+month+hour FE) 포함 나머지 모든 모형에서 β>0, p<.05로 H1을 지지한다.

### 질문 2. 전체 978건 binary prediction 기준에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): M0_baseline, M1_year_fe, M2_month_fe, M3_hour_fe, M4_year_month_fe, M5_year_hour_fe, M6_month_hour_fe, M7_year_month_hour_fe

Weak support: 없음

→ 8개 모형 전부 p<.001로 강하게 지지한다.

### 질문 3. 전체 978건 probability 기준에서 H1이 어느 모형에서 지지되는가?

H1 지지 (supports_H1): M0_baseline, M1_year_fe, M2_month_fe, M3_hour_fe, M4_year_month_fe, M5_year_hour_fe, M6_month_hour_fe, M7_year_month_hour_fe

Weak support: 없음

→ 8개 모형 전부 p<.01 이하로 지지한다.

### 질문 4. 사람 라벨 결과와 전체 데이터 결과의 방향성이 일치하는가?

**일치한다.** 세 표본 모두 β>0이며, 유머 게시글이 engagement 점수가 더 높다는 방향성이 동일하다. 8개 모형 어디서도 β가 음수로 전환되지 않았다.

### 질문 5. 사람 라벨 결과와 전체 데이터 결과 중 어느 쪽이 더 강한 유의성을 보이는가?

**전체 978건 결과가 더 강한 유의성을 보인다.** 전체 데이터 결과는 8개 모형 모두 p<.01 이하인 반면, 사람 라벨 597건 결과는 M4에서 p=0.052로 경계에 위치한다. 이는 표본 크기 차이(597 vs 978)에 기인하는 부분이 있으며, 전체 데이터의 강한 유의성이 곧 primary evidence를 강화하는 독립적 근거가 된다.

### 질문 6. M4 year+month 모형에서 사람 라벨 결과가 weak_support였는데, 전체 데이터에서는 어떻게 나타나는가?

사람 라벨 M4: β=0.2848, p=0.0522 (weak_support)

Full-sample binary M4: β=0.443, p=0.0001 (supports_H1)

Full-sample probability M4: β=0.965, p=0.0065 (supports_H1)

→ 전체 데이터 두 가지 모두 M4에서도 p<.01로 강하게 지지된다. 사람 라벨에서 M4가 weak_support인 것은 597건이라는 표본 크기의 한계일 가능성이 있으며, 전체 데이터 결과는 year+month FE를 동시에 통제한 조건에서도 유머가 engagement와 양의 관계를 갖는다는 점을 보충적으로 지지한다.

### 질문 7. 전체 데이터 결과를 primary evidence로 볼 수 있는가?

**볼 수 없다. Supplemental evidence로만 봐야 한다.** 전체 978건 분석의 독립변수는 모델 예측값(pred_humor_final_050, p_humor_final_tfidf_logreg)이며, 사람이 직접 판단한 라벨이 아니다. 모델 예측의 오분류 가능성이 있으므로 측정 타당도 측면에서 사람 라벨이 우선한다. 전체 데이터 결과는 사람 라벨 결과의 방향성과 유의성을 보충적으로 확인하는 역할에 한정된다.

---

## 13. 최종 H1 판정

**H1 지지.**

- Primary evidence (사람 라벨 n=597): 8개 모형 중 7개에서 p<.05 (supports_H1), 1개(M4)에서 p=0.052 (weak_support). 최종 모형 M7 기준 β=0.3306, p=0.0283.
- Supplemental evidence (전체 n=978 binary): 8개 모형 전부 p<.001 (supports_H1).
- Supplemental evidence (전체 n=978 probability): 8개 모형 전부 p<.01 이하 (supports_H1).
- β 방향성 일치: 세 표본 × 8개 모형 전부 β>0.
- 시간 FE 조합에 따른 β 감소: baseline β≈0.50에서 year+month+hour FE 모두 포함 시 β≈0.33으로 감소하나 유의성 유지.

본 결과는 관측적 연관성 분석이며, 유머 게시글 여부가 engagement를 인과적으로 증가시켰다는 주장을 할 수 없다.

---

## 14. 주의사항

- conventional SE 기준 결과이며, 향후 HC3 robust SE 적용 시 결과가 달라질 수 있다.
- M4(year+month FE)에서 사람 라벨 p=0.052는 conventional SE 기준으로 경계값이다.
- 전체 데이터(n=978)의 강한 유의성은 더 큰 표본 크기에 의한 효과가 일부 포함되어 있다.
- 이번 작업에서 H2, H3는 수행하지 않았다.

---

## Appendix. M7 전체 FE 기준 Supplemental DV 결과


**primary_human_n597 (n=597, IV=final_humor_binary)**

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.3306 | 0.0283 | * | 0.1968 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.33 | 0.031 | * | 0.2011 | supports_H1 |
| log1p_favorite_count | 0.4629 | 0.007 | ** | 0.1831 | supports_H1 |
| log1p_retweet_count | 0.2538 | 0.1026 |  | 0.1586 | positive_not_significant |
| log1p_reply_count | 0.3009 | 0.0283 | * | 0.1731 | supports_H1 |
| log1p_quote_count | 0.2464 | 0.1363 |  | 0.1448 | positive_not_significant |
| log1p_bookmark_count | 0.1163 | 0.4569 |  | 0.1529 | positive_not_significant |

**fullsample_binary_n978 (n=978, IV=pred_humor_final_050)**

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 0.4677 | 0.0 | *** | 0.1646 | supports_H1 |
| log1p_engagement_favorite_retweet | 0.4751 | 0.0 | *** | 0.1702 | supports_H1 |
| log1p_favorite_count | 0.6036 | 0.0 | *** | 0.1474 | supports_H1 |
| log1p_retweet_count | 0.3068 | 0.0091 | ** | 0.1367 | supports_H1 |
| log1p_reply_count | 0.436 | 0.0001 | *** | 0.1452 | supports_H1 |
| log1p_quote_count | 0.2078 | 0.0893 | † | 0.1346 | weak_support |
| log1p_bookmark_count | 0.1207 | 0.2744 |  | 0.1821 | positive_not_significant |

**probability_n978 (n=978, IV=p_humor_final_tfidf_logreg)**

| DV | β | p | sig | R² | 판정 |
|---|---|---|---|---|---|
| log1p_engagement_total | 1.0666 | 0.0027 | ** | 0.1574 | supports_H1 |
| log1p_engagement_favorite_retweet | 1.0547 | 0.0034 | ** | 0.1626 | supports_H1 |
| log1p_favorite_count | 1.4941 | 0.0004 | *** | 0.1405 | supports_H1 |
| log1p_retweet_count | 0.5736 | 0.1206 |  | 0.1327 | positive_not_significant |
| log1p_reply_count | 1.2521 | 0.0002 | *** | 0.1428 | supports_H1 |
| log1p_quote_count | 0.4552 | 0.2355 |  | 0.1332 | positive_not_significant |
| log1p_bookmark_count | 0.0191 | 0.956 |  | 0.1811 | positive_not_significant |

---

*생성일: 2026-06-15*
