# Wendy's H3-pre Quadratic OLS 분석 결과

## 1. 작업 목적

본 분석은 aggressive humor intensity가 아니라 단순 Proportion of Humor에 대한 H3-pre 분석이다.

H3-pre:

```
Wendy's의 Proportion of Humor in SNS Posts는 post-level engagement와 역 U자형 관계를 가질 것이다.
```

이 분석은 최종 H3를 검증하는 것이 아니라, H3 이전 단계에서 단순 유머 비중의 이차항 관계를 확인하는 작업이다.

---

## 2. 사용 데이터

- `wendys_h3_pre_filtered_quarter_dataset.csv`: 필터링된 post-level 데이터
- `wendys_h3_pre_filtered_quarter_period_audit.csv`: 분기별 period-level 집계

---

## 3. 분석 표본

| 항목 | 값 |
|---|---|
| 전체 posts (필터 전) | 978 |
| 필터 기준 | quarter_total_posts ≥ 10 |
| 제외 분기 | 2009-Q4, 2023-Q4, 2025-Q3 |
| **filtered posts** | **960** |
| **filtered 분기** | **25개** |

---

## 4. Primary predictor 정의

Primary predictor는 post i 자신을 제외한 동일 분기 내 유머 게시글 비중인 humor_proportion_quarter_loo이다.

```
humor_proportion_quarter_loo_i = (quarter_humor_posts - humor_i) / (quarter_total_posts - 1)
```

| 항목 | 값 |
|---|---|
| min | 0.1579 |
| max | 0.9167 |
| mean | 0.5802 |
| sd | 0.153 |
| missing | 0 |

---

## 5. 분석 모형

```
log1p_engagement_total_i = α + β1·x_i + β2·x_i² + ε_i

x = humor_proportion_quarter_loo
```

quarter fixed effects는 사용하지 않았다. humor_proportion_quarter_loo가 quarter-level 기반 변수이므로 quarter fixed effects와 동시에 사용할 경우 식별이 불가능하기 때문이다.

H3-pre 지지는 β1>0, β2<0, turning point가 관측 범위 내에 존재하는지를 기준으로 판단하였다.

turning point = -β1 / (2β2), 관측 범위: [0.1579, 0.9167]

---

## 6. Primary post-level quadratic OLS 결과

| DV | β1(linear) | p | β2(quadratic) | p | turning_point | in_range | H3-pre 지지 |
|---|---|---|---|---|---|---|---|
| log1p_engagement_total | 0.1917(n.s.) | 0.9288 | 0.3153(n.s.) | 0.8708 | -0.304 | False | H3pre_불지지 |
| log1p_engagement_favorite_retweet | 0.9007(n.s.) | 0.6789 | -0.2385(n.s.) | 0.9034 | 1.8886 | False | 방향성만_지지(tp_out_of_range) |
| log1p_favorite_count | 0.2497(n.s.) | 0.9217 | 0.1766(n.s.) | 0.9387 | -0.707 | False | H3pre_불지지 |
| log1p_retweet_count | -1.2437(n.s.) | 0.5711 | 0.8951(n.s.) | 0.6517 | 0.6947 | True | H3pre_불지지 |
| log1p_reply_count | -4.7579(*) | 0.0192 | 4.7182(*) | 0.0102 | 0.5042 | True | H3pre_불지지 |
| log1p_quote_count | -3.8747(†) | 0.0878 | 3.9189(†) | 0.056 | 0.4944 | True | H3pre_불지지 |
| log1p_bookmark_count | -6.9036(***) | 0.0007 | 3.7052(*) | 0.0442 | 0.9316 | False | H3pre_불지지 |
| log1p_view_count | -57.3065(***) | 0.0 | 25.2946(***) | 0.0 | 1.1328 | False | H3pre_불지지 |

* p<.05, ** p<.01, *** p<.001, † p<.10

---

## 7. Turning point 결과

**주요 DV: log1p_engagement_total**

| 항목 | 값 |
|---|---|
| β1 (linear) | 0.1917 (p=0.9288) |
| β2 (quadratic) | 0.3153 (p=0.8708) |
| turning point | -0.304 |
| 관측 범위 | [0.1579, 0.9167] |
| turning point in range | False |
| turning point 95% CI | [-0.304, 9.9922] |
| H3-pre 판정 | **H3pre_불지지** |

---

## 8. Centered model 결과 (robustness)

| 항목 | 값 |
|---|---|
| β1 (centered linear) | 0.5576 (p=0.1603) |
| β2 (centered quadratic) | 0.3153 (p=0.8708) |
| R² | 0.0022 |

Raw 모델과 R², β2 부호가 일치하는지: 불일치 확인 필요

---

## 9. Frequency robustness 결과

predictor: humor_frequency_quarter (절대 개수 기반, 보조 분석)

| 항목 | 값 |
|---|---|
| β1 | 0.015122 (p=0.1288) |
| β2 | -0.000227 (p=0.0483) |
| turning point | 33.32 |
| in range [3.0, 78.0] | True |
| H3-pre 판정 | 강한_예비적_지지(p<.05) |

Frequency는 전체 post 수가 많은 분기에서 자동으로 커질 수 있으므로 primary predictor가 아니라 robustness predictor로 해석한다.

---

## 10. Non-LOO proportion robustness 결과

predictor: humor_proportion_quarter (focal post 자기 포함, 보조 분석)

| 항목 | 값 |
|---|---|
| β1 | -0.5184 (p=0.8132) |
| β2 | 1.0419 (p=0.5984) |
| turning point | 0.2488 |
| in range | True |
| H3-pre 판정 | H3pre_불지지 |

---

## 11. Period-level exploratory OLS 결과 (n=25분기)

| 항목 | 값 |
|---|---|
| β1 | -2.7023 (p=0.5264) |
| β2 | 3.0231 (p=0.4433) |
| turning point | 0.4469 |
| in range | True |
| R² | 0.0462 |

n=25로 표본이 작기 때문에 exploratory descriptive robustness로만 해석한다.

---

## 12. Bin descriptive pattern과의 관계

| bin | n_posts | mean_log1p_engagement_total |
|---|---|---|
| low (≤0.5185) | 332 | 7.2985 |
| medium (0.5185–0.6562) | 335 | 7.6837 |
| high (>0.6562) | 293 | 7.2073 |

Descriptive pattern: low < medium > high (역 U자형) — 회귀 β2 방향과 불일치.

---

## 13. H3-pre 판정

**Primary model (humor_proportion_quarter_loo): H3pre_불지지**

| 판정 기준 | 충족 여부 |
|---|---|
| β1 > 0 (linear) | ✓ |
| β2 < 0 (quadratic) | ✗ |
| turning point in range | ✗ (-0.304) |
| p_quadratic < .05 | ✗ (p=0.8708) |

---

## 14. 해석상 주의사항

본 분석은 관측적 연관성 분석이며, Proportion of Humor가 engagement를 증가시켰다는 인과관계를 주장할 수 없다.

- pred_humor_final_050은 모델 기반 예측값이므로 분류 오류가 포함될 수 있다.
- quarter fixed effects 미사용으로 분기별 시계열 추세가 통제되지 않았다.
- post-level OLS에서 같은 분기 내 게시글은 동일한 humor_proportion_quarter_loo 값을 공유하므로 표준오차가 과소추정될 수 있다 (cluster-robust SE를 사용하지 않음).
- H3-pre는 최종 H3가 아니라 aggressive humor intensity를 제외한 단순 유머 비중의 탐색적 분석이다.
- 본 분석은 aggressive humor intensity가 아니라 단순 Proportion of Humor에 대한 H3-pre 분석이다.

---

## 15. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/H3-pre audit 파일 수정 없음

---

*생성일: 2026-06-15*
