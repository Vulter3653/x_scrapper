# OLS H1 / H2 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 유형 | N | 비율(전체) | 비율(유머 내) |
|:---|---:|---:|---:|
| Non-humorous (reference) | 42,020 | 64.4% | — |
| Aggressive | 1,416 | 2.2% | 6.1% |
| Affiliative | 12,696 | 19.5% | 54.7% |
| Self-Enhancing | 8,788 | 13.5% | 37.8% |
| Self-Defeating | 325 | 0.5% | 1.4% |
| Humor Total | 23,225 | 35.6% | 100% |
| **Total** | **65,245** | **100%** | — |
| Firms | 97 | — | — |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm FE (FWL) |
|:---|:---:|:---:|
| Aggressive (β₁) | +1.1543*** (0.0533) | +0.2648*** (0.0354) |
| Affiliative (β₂) | +0.7266*** (0.0200) | +0.1808*** (0.0140) |
| Self-Enhancing (β₃) | +1.1330*** (0.0231) | +0.2566*** (0.0162) |
| Self-Defeating (β₄) | +0.9627*** (0.1099) | +0.1891*** (0.0715) |
| Intercept | +3.1162 | absorbed |
| N | 65,245 | 65,245 |
| Firms | — | 97 |
| R² | 0.0499 | 0.0053 (within) |
| adj-R² | 0.0498 | 0.0037 |
| df_resid | 65,240 | 65,144 |
| Controls | none | none |
| Firm FE | no | yes (FWL) |

*괄호 = classical OLS SE. *** p<.01 / ** p<.05 / * p<.10 (two-sided)*

---

## 3. H1 검정 — 전체 유머 가중평균효과

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 0.909745 | 0.016132 | 56.3942 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M2_firm_fe_fwl | 0.214695 | 0.011847 | 18.1216 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |

---

## 4. H2-1 검정 — Aggressive vs Other Humor 가중평균

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 0.260486 | 0.054106 | 4.8144 | 0.000001 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M2_firm_fe_fwl | 0.053382 | 0.035297 | 1.5124 | 0.130444 |  | H2-1 지지 불가: 방향 맞으나 유의하지 않음 |

---

## 5. H2-2 검정 — Pairwise Contrasts

| 모델 | Contrast | 추정치 | SE | t | p | Stars | 판정 |
|:---|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | agg vs aff | 0.427798 | 0.055277 | 7.7391 | 0.000000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M1_simple_ols | agg vs se | 0.021316 | 0.056497 | 0.3773 | 0.705957 |  | H2-2 지지 불가: aggressive > self-enhancing 방향이나 유의하지 않음 |
| M1_simple_ols | agg vs sd | 0.191648 | 0.121351 | 1.5793 | 0.114275 |  | H2-2 지지 불가: aggressive > self-defeating 방향이나 유의하지 않음 |
| M2_firm_fe_fwl | agg vs aff | 0.084065 | 0.036108 | 2.3282 | 0.019905 | ** | H2-2 지지: aggressive > affiliative (p<.05) |
| M2_firm_fe_fwl | agg vs se | 0.008228 | 0.036847 | 0.2233 | 0.823301 |  | H2-2 지지 불가: aggressive > self-enhancing 방향이나 유의하지 않음 |
| M2_firm_fe_fwl | agg vs sd | 0.075717 | 0.078407 | 0.9657 | 0.334198 |  | H2-2 지지 불가: aggressive > self-defeating 방향이나 유의하지 않음 |

**H2-2 종합**:
- M1 Simple OLS: 부분 지지 (1/3 유의)
- M2 Firm FE:    부분 지지 (1/3 유의)

---

## 6. 해석 주의사항

1. **Classifier limitation**: domain-adapted TF-IDF LogReg 예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
2. **Controls 미포함**: text_length, hashtag_count, mention_count 미통제. M2 Firm FE는 기업 수준 고정 이질성을 흡수하지만 시간 FE 및 포스트 속성은 여전히 미통제.
3. **단순 OLS 진단 목적**: causal 또는 robust evidence가 아닌 preliminary diagnostic.
