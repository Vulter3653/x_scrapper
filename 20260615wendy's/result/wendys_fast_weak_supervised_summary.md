# Wendy's 유머 측정 개선 및 H1 재분석 요약

생성일시: 2026-06-15 12:04 UTC

---

## 1. 작업 목적

기존 규칙 기반 `humor_score`의 false negative(유머를 놓치는) 문제를 개선하기 위해
weak-supervised 방법을 적용하여 `p_humor_ml`을 생성하고,
이를 독립변수로 사용하여 Wendy's H1(유머 존재와 engagement의 연관성)을 재분석한다.

H1 가설:
> Wendy's 브랜드 게시글에서 유머 존재 가능성이 높을수록 게시글 수준의 engagement가 높다.

---

## 2. 참고 방법론

본 작업은 Pamuksuz, Yun, and Humphreys (2021)의 SNS 텍스트 기반 브랜드 성격 예측 절차를
완전히 복제한 것이 아니라, 제한된 시간과 Wendy's 단일 브랜드 표본에 맞게 축소 적용한 것이다.
즉, dictionary/weak label, topic structure, supervised text classification의 논리를 활용하되,
full LDA2Vec, Doc2Vec/KNN, RoBERTa fine-tuning은 수행하지 않았다.

---

## 3. 기존 `humor_score`의 문제

기존 `humor_score`는 규칙 기반으로 만들어졌기 때문에,
명확한 키워드나 패턴이 있는 유머는 잘 잡지만,
짧은 밈형 문장이나 상황적 유머는 놓칠 가능성이 있다.

실제로 전체 978개 게시글 중 739개(75.6%)가
`humor_score = 0`으로 분류되었다.
이는 Wendy's 특유의 짧고 맥락적인 유머가 과소탐지되었을 가능성을 보여준다.

---

## 4. 축소형 weak-supervised 방법

```
단계 1. 텍스트 전처리 (URL → <URL>, 멘션 → <MENTION>, 소문자 변환)
단계 2. TF-IDF + NMF (K=8) 토픽 모델링 — 콘텐츠 구조 파악 (감사용)
단계 3. Weak label 구성 — 텍스트 신호만 사용, engagement 변수 미사용
단계 4. TF-IDF + Logistic Regression 분류기 학습 (weak labeled 행만 사용)
단계 5. 전체 978건에 대해 classifier_prob 예측
단계 6. p_humor_ml = 0.65 × classifier_prob + 0.35 × humor_score (blended)
단계 7. human review sample 생성 (false negative 후보 포함)
단계 8. log1p_p_humor_ml을 IV로 한 단순 OLS 재분석
```

---

## 5. 토픽 모델링 결과 (TF-IDF + NMF, K=8)

각 토픽은 Wendy's 게시글의 주요 콘텐츠 유형을 반영한다.
토픽 자체는 분류기 입력이 아니라 감사(audit) 목적으로 생성하였다.

| topic_id | n_posts | 상위 주요 용어 | mean_humor_score | mean_p_humor_ml | mean_engagement |
|---|---|---|---|---|---|
| 0 | 210 | url, url url, mention url, burger, big | 0.0538 | 0.2458 | 16065.0 |
| 1 | 169 | mention, mention url, mention mention, rt, rt mention | 0.0545 | 0.4080 | 3208.7 |
| 2 | 84 | wendy, wendy url, sir, wendy app, wendy breakfast | 0.0775 | 0.4162 | 10175.8 |
| 3 | 47 | chicken, honey, biscuit, honey butter, butter | 0.0523 | 0.3621 | 5588.9 |
| 4 | 18 | vote, bracket, brand, brand bracket, bestoftweets brand | 0.0517 | 0.2725 | 1333.7 |
| 5 | 357 | breakfast, free, app, got, purchase | 0.0724 | 0.4085 | 9865.5 |
| 6 | 18 | roast, mention roast, mention, hey, hey mention | 0.5312 | 0.7118 | 16424.6 |
| 7 | 75 | frosty, strawberry, fry, strawberry frosty, small | 0.0612 | 0.4078 | 4640.3 |


---

## 6. Weak Label 구성 기준

Weak label은 텍스트 신호만을 이용하여 부여하였다.
engagement 변수는 독립변수-종속변수 순환 편의 방지를 위해 사용하지 않았다.

| 레이블 | 조건 | 게시글 수 |
|--------|------|-----------|
| 1 (유머 가능성 높음) | `humor_score >= 0.60` 또는 강한 유머 cue (sarcasm_irony, roast_teasing, joke_qa_structure, pun_wordplay, absurdity_surrealism, pop_culture_reference) | 92 |
| 0 (비유머 가능성 높음) | `humor_score == 0` AND (`plain_promotion` 또는 `url_only` 포함) | 82 |
| 미분류 | 그 외 — `insufficient_text_signal` 등 false negative 가능성 | 804 |

**중요:** `humor_score == 0` 전체를 비유머(label=0)로 처리하지 않았다.
텍스트 신호가 부족한 경우(insufficient_text_signal)는 false negative일 수 있으므로
분류기가 독자적으로 유머 확률을 판단하게 하였다.

---

## 7. `p_humor_ml` 생성 방식

TF-IDF + Logistic Regression 분류기가 학습되었다. 5-fold 교차검증 결과: accuracy=0.8222, precision=0.8483, recall=0.8146, F1=0.8291.

최종 혼합 공식:

```
p_humor_ml = 0.65 × classifier_prob + 0.35 × humor_score
```

`p_humor_ml` 요약 통계:

| 지표 | 값 |
|------|-----|
| `p_humor_ml == 0` 건수 | 0 (0.0%) |
| 평균 | 0.3749 |
| 중앙값 | 0.3963 |
| 최솟값 | 0.0801 |
| 최댓값 | 0.8054 |

`log1p_p_humor_ml = log(1 + p_humor_ml)`을 사용한 이유:
`p_humor_ml`이 0인 경우 `log(0)`은 정의되지 않으므로 `log1p`를 사용한다.

---

## 8. Human Review Sample 구성

향후 수동 코딩 효율화를 위해 약 120건의 검토 표본을 생성하였다.

| 유형 | 기준 | 생성 수 |
|------|------|---------|
| false negative 후보 | `humor_score == 0` AND `p_humor_ml >= 0.40` | 40 |
| 유머 고신뢰 | `p_humor_ml >= 0.70` | 30 |
| 비유머 고신뢰 | `p_humor_ml <= 0.10` AND `weak_humor_label == 0` | 30 |
| 경계 케이스 | `0.40 <= p_humor_ml <= 0.60` | 20 |
| **합계** | | **120** |

`human_humor_label` 및 `human_notes` 컬럼은 향후 수동 코딩을 위해 공란으로 제공.

---

## 9. H1 단순 OLS 재분석 결과

H1 회귀식:

```
log1p_engagement_total_i = α + β × log1p_p_humor_ml_i + ε_i
```

각 항의 의미:
- `i` : 개별 Wendy's 게시글
- `log1p_engagement_total_i` : 게시글 i의 전체 engagement를 로그 변환한 값
- `log1p_p_humor_ml_i` : 게시글 i의 유머 가능성 점수(`p_humor_ml`)를 로그 변환한 값
- `β` : 유머 가능성 점수와 engagement의 관련 방향을 보여주는 핵심 계수
- `ε_i` : 모델로 설명되지 않는 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

주요 결과 (`log1p_engagement_total`):

| 파라미터 | 값 |
|----------|-----|
| n_obs | 978 |
| Intercept (α) | 7.246892 |
| β (log1p_p_humor_ml) | 0.533425 |
| Standard Error | 0.532398 |
| t-value | 1.0019 |
| p-value | 0.3166 |
| 95% CI | [7.591979, 1.578201] |
| R² | 0.001027 |
| Adj. R² | 0.000004 |
| **H1 해석** | **H1 방향성 지지** |

전체 DV 결과:

| 종속변수 (DV) | β | SE | t | p-value | R² | 방향 | H1 해석 |
|---|---|---|---|---|---|---|---|
| log1p_engagement_total | 0.533425 | 0.532398 | 1.0019 | 0.316626 | 0.001027 | positive | H1 방향성 지지 |
| log1p_favorite_count | 0.162101 | 0.629017 | 0.2577 | 0.796689 | 0.000068 | positive | H1 방향성 지지 |
| log1p_retweet_count | 0.204152 | 0.545714 | 0.3741 | 0.708411 | 0.000143 | positive | H1 방향성 지지 |
| log1p_reply_count | -0.006846 | 0.503084 | -0.0136 | 0.989145 | 0.000000 | negative | H1 지지 없음 |
| log1p_quote_count | 0.046536 | 0.566986 | 0.0821 | 0.934603 | 0.000007 | positive | H1 방향성 지지 |
| log1p_bookmark_count | -1.733372 | 0.523824 | -3.3091 | 0.000970 | 0.011095 | negative | H1 지지 없음 |


---

## 10. 해석

`log1p_p_humor_ml`은 `log1p_engagement_total`과
**positive한** 방향을 보였다.
(β = 0.533425, p = 0.3166, R² = 0.001027)

본 결과는 Wendy's 단일 브랜드 게시글을 대상으로 한 관측적 연관성 분석이며,
유머가 engagement를 증가시킨다는 인과효과로 해석할 수 없다.

---

## 11. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- `p_humor_ml`은 human-labeled gold standard가 아니라 weak-supervised score이다.
- engagement 변수(`reply_count`, `favorite_count` 등)는 `p_humor_ml` 생성에 사용하지 않았다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- BERTweet/RoBERTa fine-tuning은 이번 fast pipeline에서는 수행하지 않았다.
- 이미지/영상 의존 유머는 여전히 완전히 포착되지 않을 수 있다.
- 단순 OLS 분석에서는 통제변수, 고정효과, robust standard error를 포함하지 않았다.
- `p_humor_ml`의 분포가 여전히 0에 집중될 경우 OLS 설명력이 낮을 수 있다.
