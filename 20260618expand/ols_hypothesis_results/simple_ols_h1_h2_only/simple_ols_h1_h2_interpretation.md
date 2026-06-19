# OLS H1 / H2 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 유형 | N | 비율(전체) | 비율(유머 내) |
|:---|---:|---:|---:|
| Non-humorous (reference) | 42,606 | 62.6% | — |
| Aggressive | 1,807 | 2.7% | 7.1% |
| Affiliative | 13,541 | 19.9% | 53.2% |
| Self-Enhancing | 9,613 | 14.1% | 37.8% |
| Self-Defeating | 472 | 0.7% | 1.9% |
| Humor Total | 25,433 | 37.4% | 100% |
| **Total** | **68,039** | **100%** | — |
| Firms | 99 | — | — |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm dummies |
|:---|:---:|:---:|
| Aggressive (β₁) | +1.6816*** (0.0493) | +0.2250*** (0.0329) |
| Affiliative (β₂) | +0.8389*** (0.0203) | +0.1687*** (0.0141) |
| Self-Enhancing (β₃) | +1.3191*** (0.0232) | +0.2592*** (0.0162) |
| Self-Defeating (β₄) | +2.0410*** (0.0950) | +0.3210*** (0.0618) |
| Intercept | +3.1561 | — (absorbed by firm dummies) |
| N | 68,039 | 68,039 |
| Firms | — | 99 |
| R² | 0.0706 | 0.6247 |
| adj-R² | 0.0705 | 0.6242 |
| df_resid | 68,034 | 67,936 |
| Controls | none | none |
| Firm dummies | no | 99개 (no reference, no intercept) |

*괄호 = classical OLS SE. *** p<.01 / ** p<.05 / * p<.10 (two-sided)*

---

## 3. H1 검정 — 전체 유머 가중평균효과

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 1.102543 | 0.016270 | 67.7642 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M2_firm_dummies | 0.209708 | 0.011978 | 17.5082 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M3_time_fe_year_month | 1.100421 | 0.015718 | 70.0107 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M4_firm_year_month_fe | 0.180299 | 0.011623 | 15.5122 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |

---

## 4. H2-1 검정 — Aggressive vs Other Humor 가중평균

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 0.623296 | 0.050116 | 12.4371 | 0.000000 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M2_firm_dummies | 0.016431 | 0.032502 | 0.5055 | 0.613186 |  | H2-1 지지 불가: 방향 맞으나 유의하지 않음 |
| M3_time_fe_year_month | 0.672294 | 0.048089 | 13.9802 | 0.000000 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M4_firm_year_month_fe | 0.026795 | 0.031473 | 0.8514 | 0.394570 |  | H2-1 지지 불가: 방향 맞으나 유의하지 않음 |

---

## 5. H2-2 검정 — Pairwise Contrasts

| 모델 | Contrast | 추정치 | SE | t | p | Stars | 판정 |
|:---|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | agg vs aff | 0.842701 | 0.051425 | 16.3871 | 0.000000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M1_simple_ols | agg vs se | 0.362495 | 0.052647 | 6.8854 | 0.000000 | *** | H2-2 지지: aggressive > self-enhancing (p<.01) |
| M1_simple_ols | agg vs sd | -0.359481 | 0.106138 | -3.3869 | 0.000707 | *** | H2-2 지지 불가: aggressive <= self-defeating |
| M2_firm_dummies | agg vs aff | 0.056291 | 0.033448 | 1.6829 | 0.092398 | * | H2-2 부분 지지: aggressive > affiliative (p<.10) |
| M2_firm_dummies | agg vs se | -0.034196 | 0.034078 | -1.0034 | 0.315647 |  | H2-2 지지 불가: aggressive <= self-enhancing |
| M2_firm_dummies | agg vs sd | -0.095999 | 0.067810 | -1.4157 | 0.156867 |  | H2-2 지지 불가: aggressive <= self-defeating |
| M3_time_fe_year_month | agg vs aff | 0.878156 | 0.049341 | 17.7975 | 0.000000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M3_time_fe_year_month | agg vs se | 0.440223 | 0.050536 | 8.7110 | 0.000000 | *** | H2-2 지지: aggressive > self-enhancing (p<.01) |
| M3_time_fe_year_month | agg vs sd | -0.507132 | 0.101819 | -4.9807 | 0.000001 | *** | H2-2 지지 불가: aggressive <= self-defeating |
| M4_firm_year_month_fe | agg vs aff | 0.049581 | 0.032391 | 1.5307 | 0.125845 |  | H2-2 지지 불가: aggressive > affiliative 방향이나 유의하지 않음 |
| M4_firm_year_month_fe | agg vs se | 0.000714 | 0.033003 | 0.0216 | 0.982751 |  | H2-2 지지 불가: aggressive > self-enhancing 방향이나 유의하지 않음 |
| M4_firm_year_month_fe | agg vs sd | -0.095716 | 0.065668 | -1.4576 | 0.144964 |  | H2-2 지지 불가: aggressive <= self-defeating |

**H2-2 종합**:
- M1 Simple OLS:        부분 지지 (2/3 유의)
- M2 Firm FE (FWL):     지지 불가
- M3 Time FE:           부분 지지 (2/3 유의)
- M4 Firm+Time FE:      지지 불가

---

## 6. 해석 주의사항

1. **Classifier limitation**: domain-adapted TF-IDF LogReg 예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
2. **Controls 미포함**: text_length, hashtag_count, mention_count 미통제. M2 Firm FE는 기업 수준 고정 이질성을 흡수하지만 시간 FE 및 포스트 속성은 여전히 미통제.
3. **단순 OLS 진단 목적**: causal 또는 robust evidence가 아닌 preliminary diagnostic.
