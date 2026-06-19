# OLS H1 / H2 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 유형 | N | 비율(전체) | 비율(유머 내) |
|:---|---:|---:|---:|
| Non-humorous (reference) | 42,009 | 61.7% | — |
| Aggressive | 2,025 | 3.0% | 7.8% |
| Affiliative | 14,027 | 20.6% | 53.9% |
| Self-Enhancing | 9,509 | 14.0% | 36.5% |
| Self-Defeating | 469 | 0.7% | 1.8% |
| Humor Total | 26,030 | 38.3% | 100% |
| **Total** | **68,039** | **100%** | — |
| Firms | 99 | — | — |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm dummies |
|:---|:---:|:---:|
| Aggressive (β₁) | +1.7998*** (0.0465) | +0.3318*** (0.0313) |
| Affiliative (β₂) | +0.8377*** (0.0199) | +0.1950*** (0.0140) |
| Self-Enhancing (β₃) | +1.4391*** (0.0232) | +0.2946*** (0.0163) |
| Self-Defeating (β₄) | +2.1009*** (0.0948) | +0.3874*** (0.0618) |
| Intercept | +3.1263 | — (absorbed by firm dummies) |
| N | 68,039 | 68,039 |
| Firms | — | 99 |
| R² | 0.0806 | 0.6254 |
| adj-R² | 0.0806 | 0.6248 |
| df_resid | 68,034 | 67,936 |
| Controls | none | none |
| Firm dummies | no | 99개 (no reference, no intercept) |

*괄호 = classical OLS SE. *** p<.01 / ** p<.05 / * p<.10 (two-sided)*

---

## 3. H1 검정 — 전체 유머 가중평균효과

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 1.155034 | 0.016108 | 71.7035 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M2_firm_dummies | 0.245512 | 0.012065 | 20.3498 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M3_time_fe_year_month | 1.154838 | 0.015571 | 74.1683 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |
| M4_firm_year_month_fe | 0.214728 | 0.011710 | 18.3370 | 0.000000 | *** | H1 지지: 전체 유머 평균효과 양수 유의 (p<.01) |

---

## 4. H2-1 검정 — Aggressive vs Other Humor 가중평균

| 모델 | 추정치 | SE | t | p | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | 0.699187 | 0.047256 | 14.7957 | 0.000000 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M2_firm_dummies | 0.093612 | 0.030866 | 3.0329 | 0.002423 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M3_time_fe_year_month | 0.763230 | 0.045377 | 16.8198 | 0.000000 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |
| M4_firm_year_month_fe | 0.095497 | 0.029890 | 3.1950 | 0.001399 | *** | H2-1 지지: aggressive > other humor weighted average (p<.01) |

---

## 5. H2-2 검정 — Pairwise Contrasts

| 모델 | Contrast | 추정치 | SE | t | p | Stars | 판정 |
|:---|:---|---:|---:|---:|---:|:---:|:---|
| M1_simple_ols | agg vs aff | 0.962086 | 0.048546 | 19.8180 | 0.000000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M1_simple_ols | agg vs se | 0.360714 | 0.049980 | 7.2172 | 0.000000 | *** | H2-2 지지: aggressive > self-enhancing (p<.01) |
| M1_simple_ols | agg vs sd | -0.301102 | 0.104649 | -2.8773 | 0.004013 | *** | H2-2 지지 불가: aggressive <= self-defeating |
| M2_firm_dummies | agg vs aff | 0.136819 | 0.031792 | 4.3036 | 0.000017 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M2_firm_dummies | agg vs se | 0.037233 | 0.032580 | 1.1428 | 0.253119 |  | H2-2 지지 불가: aggressive > self-enhancing 방향이나 유의하지 않음 |
| M2_firm_dummies | agg vs sd | -0.055561 | 0.067013 | -0.8291 | 0.407043 |  | H2-2 지지 불가: aggressive <= self-defeating |
| M3_time_fe_year_month | agg vs aff | 0.999171 | 0.046610 | 21.4368 | 0.000000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M3_time_fe_year_month | agg vs se | 0.471614 | 0.048008 | 9.8237 | 0.000000 | *** | H2-2 지지: aggressive > self-enhancing (p<.01) |
| M3_time_fe_year_month | agg vs sd | -0.380843 | 0.100356 | -3.7949 | 0.000148 | *** | H2-2 지지 불가: aggressive <= self-defeating |
| M4_firm_year_month_fe | agg vs aff | 0.121264 | 0.030788 | 3.9386 | 0.000082 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| M4_firm_year_month_fe | agg vs se | 0.066118 | 0.031553 | 2.0955 | 0.036132 | ** | H2-2 지지: aggressive > self-enhancing (p<.05) |
| M4_firm_year_month_fe | agg vs sd | -0.079520 | 0.064910 | -1.2251 | 0.220549 |  | H2-2 지지 불가: aggressive <= self-defeating |

**H2-2 종합**:
- M1 Simple OLS:        부분 지지 (2/3 유의)
- M2 Firm FE (FWL):     부분 지지 (1/3 유의)
- M3 Time FE:           부분 지지 (2/3 유의)
- M4 Firm+Time FE:      부분 지지 (2/3 유의)

---

## 6. 해석 주의사항

1. **Classifier limitation**: domain-adapted TF-IDF LogReg 예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
2. **Controls 미포함**: text_length, hashtag_count, mention_count 미통제. M2 Firm FE는 기업 수준 고정 이질성을 흡수하지만 시간 FE 및 포스트 속성은 여전히 미통제.
3. **단순 OLS 진단 목적**: causal 또는 robust evidence가 아닌 preliminary diagnostic.
