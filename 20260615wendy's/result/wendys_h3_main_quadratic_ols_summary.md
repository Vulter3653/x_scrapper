# Wendy's H3-main Exploratory Quadratic OLS 분석 결과

## 1. 분석 위치

본 분석은 확증적 H3 검증이 아니라 exploratory H3-main 분석이다.

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았다 (β2=+0.3153, turning point=-0.3040, 관측 범위 밖). 따라서 aggressive humor intensity를 primary predictor로 사용한 이번 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

---

## 2. 분석 목적

aggressive humor proportion이 증가할수록 engagement가 먼저 상승하다가 이후 감소하는 역 U자형 관계가 있는지를 탐색적으로 확인한다.

```
log1p_engagement_total_i = α + β1·x_i + β2·x_i² + ε_i
x = aggressive_humor_proportion_quarter_loo
```

quarter fixed effects는 사용하지 않았다. aggressive_humor_proportion_quarter_loo는 quarter-level 기반 변수이므로 quarter fixed effects와 동시에 사용할 경우 식별이 불가능하기 때문이다.

---

## 3. 사용 데이터

| 항목 | 값 |
|---|---|
| 소스 | `wendys_h3_aggressive_vs_other_intensity_dataset.csv` |
| 전체 rows | 978 |
| 필터 기준 | in_h3_aggressive_filtered=1 |
| **filtered rows** | **960** |
| **filtered quarters** | **25** |

---

## 4. Primary predictor 정의

```
aggressive_humor_proportion_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Total Posts_q - 1)
```

post i 자신을 제외한 동일 분기 내 aggressive humor 비중.
모델 기반 타입 예측값(pred_humor_type_group_model)을 기반으로 산출하였다.

| 항목 | 값 |
|---|---|
| min | 0.0 |
| max | 0.3377 |
| mean | 0.2062 |
| sd | 0.0703 |
| missing | 0 |
| 관측 범위 | [0.0, 0.3377] |

---

## 5. Primary post-level quadratic OLS 결과

| DV | β1 | p(β1) | β2 | p(β2) | turning_point | in_range | 탐색적 지지 |
|---|---|---|---|---|---|---|---|
| log1p_engagement_total | -1.4598(n.s.) | 0.653 | 2.5539(n.s.) | 0.7388 | 0.2858 | True | H3main_불지지 |
| log1p_engagement_favorite_retweet | -1.2461(n.s.) | 0.7051 | 2.4041(n.s.) | 0.7569 | 0.2592 | True | H3main_불지지 |
| log1p_favorite_count | -1.8801(n.s.) | 0.6243 | 1.4932(n.s.) | 0.869 | 0.6295 | False | H3main_불지지 |
| log1p_retweet_count | -2.4857(n.s.) | 0.4538 | 5.2683(n.s.) | 0.5009 | 0.2359 | True | H3main_불지지 |
| log1p_reply_count | -1.7449(n.s.) | 0.5699 | -0.1391(n.s.) | 0.9847 | -6.2712 | False | H3main_불지지 |
| log1p_quote_count | -4.0658(n.s.) | 0.2361 | 6.5645(n.s.) | 0.4174 | 0.3097 | True | H3main_불지지 |
| log1p_bookmark_count | -12.5052(***) | 0.0001 | 23.431(**) | 0.0017 | 0.2669 | True | H3main_불지지 |
| log1p_view_count | -53.8098(***) | 0.0 | 91.4798(***) | 0.0003 | 0.2941 | True | H3main_불지지 |

* p<.05, ** p<.01, *** p<.001, † p<.10

---

## 6. 주요 DV: log1p_engagement_total

| 항목 | 값 |
|---|---|
| β1 (linear) | -1.4598 (p=0.653) |
| β2 (quadratic) | 2.5539 (p=0.7388) |
| turning point | 0.2858 |
| 관측 범위 | [0.0, 0.3377] |
| turning point in range | True |
| turning point 95% CI | [-0.2814, 0.853] |
| R² | 0.0004 |
| **H3-main 탐색적 지지** | **H3main_불지지** |

---

## 7. Centered model robustness

| 항목 | 값 |
|---|---|
| β2 (centered quadratic) | 2.5539 (p=0.7388) |
| β2 부호 | 2.5539 |
| R² | 0.0004 |

---

## 8. 보조 predictors robustness 요약

| predictor | β1 | β2 | turning point | in range | 탐색적 지지 |
|---|---|---|---|---|---|
| aggressive_share_among_humor_loo | -1.0942 | 0.5899 | 0.9275 | True | H3main_불지지 |
| aggressive_frequency | -0.07154 | 0.002103 | 17.01 | True | H3main_불지지 |
| other_humor_proportion_loo | 1.8261 | -1.6771 | 0.5444 | True | 약한_탐색적_지지(tp_in_range) |

---

## 9. Period-level exploratory OLS (n=25 quarters)

| 항목 | 값 |
|---|---|
| β1 | 1.2364 (p=0.8496) |
| β2 | -4.773 (p=0.7812) |
| turning point | 0.1295 |
| in range | True |
| R² | 0.0068 |

n=25로 표본이 작기 때문에 period-level OLS는 descriptive robustness로만 해석한다.

---

## 10. H3-main exploratory support 판정

H3-main exploratory support 기준:

| 기준 | 조건 |
|---|---|
| 강한 탐색적 지지 | β1>0, β2<0, turning_point in range, p_quadratic<.05 |
| 약한 탐색적 지지 | β1>0, β2<0, turning_point in range, p_quadratic≥.05 |
| 방향성만 지지 | β1>0, β2<0, turning_point out of range |
| 불지지 | β2≥0 또는 turning_point 범위 밖 |

**primary model 판정: H3main_불지지**

---

## 11. 이전 H3-pre와의 관계

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았으므로, 본 aggressive intensity 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

| 분석 단계 | predictor | β2 부호 | turning point | 지지 여부 |
|---|---|---|---|---|
| H3-pre (일반) | humor_proportion_quarter_loo | +0.3153 | -0.3040 (범위 밖) | 불지지 |
| H3-main (탐색적) | aggressive_humor_proportion_quarter_loo | 2.5539 | 0.2858 | H3main_불지지 |

---

## 12. 해석상 주의사항

1. 이 분석은 관측적 연관성 분석이며, aggressive humor가 engagement를 증가시켰다는 인과관계를 주장할 수 없다.
2. aggressive_humor_proportion_quarter_loo는 pred_humor_type_group_model(모델 기반 타입 예측값)에서 파생된 변수이므로 분류 오류를 포함할 수 있다.
3. 같은 분기 내 게시글은 동일한 predictor 값을 공유하므로 표준오차가 과소추정될 수 있다 (cluster-robust SE 미적용).
4. quarter fixed effects 미사용으로 분기별 시계열 추세가 통제되지 않았다.
5. H3-pre의 general proportion이 불지지였기 때문에, 이 결과는 exploratory H3-main에 해당하며 확증적 증거가 아니다.

---

## 13. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/H3-pre 파일 수정 없음

---

*생성일: 2026-06-15*
