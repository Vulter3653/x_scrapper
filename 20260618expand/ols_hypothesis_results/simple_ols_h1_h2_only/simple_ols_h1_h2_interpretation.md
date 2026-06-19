# Simple OLS H1 / H2 해석 (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반 결과. Controls 및 Fixed Effects 미포함.
> NOT_A_CANDIDATE 수준 증거. Classifier leakage risk 존재.

---

## 1. 표본 구성

| 유형 | N | 전체 비율 | 유머 내 비율 |
|:---|---:|---:|---:|
| Non-humorous (reference) | 42,020 | 64.4% | — |
| Aggressive | 1,416 | 2.2% | 6.1% |
| Affiliative | 12,696 | 19.5% | 54.7% |
| Self-Enhancing | 8,788 | 13.5% | 37.8% |
| Self-Defeating | 325 | 0.5% | 1.4% |
| Humor Total | 23,225 | 35.6% | 100% |
| **Total** | **65,245** | **100%** | — |

---

## 2. 회귀 결과 (M1 Simple OLS)

```
log(1 + Engagement) = β₀ + β₁·Aggressive + β₂·Affiliative + β₃·SelfEnhancing + β₄·SelfDefeating
```

| 변수 | β | SE | t | p (2-sided) | Stars |
|:---|---:|---:|---:|---:|:---:|
| Intercept | +3.1162 | 0.0096 | +323.7669 | 0.0000 | *** |
| Aggressive (β₁) | +1.1543 | 0.0533 | +21.6548 | 0.0000 | *** |
| Affiliative (β₂) | +0.7266 | 0.0200 | +36.3624 | 0.0000 | *** |
| Self-Enhancing (β₃) | +1.1330 | 0.0231 | +48.9590 | 0.0000 | *** |
| Self-Defeating (β₄) | +0.9627 | 0.1099 | +8.7628 | 0.0000 | *** |

N=65,245 | R²=0.0499 | adj-R²=0.0498 | df_resid=65,240
Reference category = non_humorous | Controls = none | FE = none

---

## 3. H1 검정 결과

**명제**: 유머 포스트가 비유머 포스트보다 engagement가 높다.

| 유형 | β | 방향 | 유의 |
|:---|---:|:---:|:---:|
| Aggressive (β₁) | +1.1543 | ✓ | *** |
| Affiliative (β₂) | +0.7266 | ✓ | *** |
| Self-Enhancing (β₃) | +1.1330 | ✓ | *** |
| Self-Defeating (β₄) | +0.9627 | ✓ | *** |

**전체 유머 평균효과** (가중치 = 유머 내 유형 비율):

- 추정치: +0.9097  SE=0.0161  t=+56.3942  p=0.0000 ***
- **H1 지지: 전체 유머 평균효과 양수 유의 (p<.01)**

---

## 4. H2-1 검정 결과

**명제**: Aggressive humor가 other humor types보다 engagement가 높다.

- Contrast: β₁ − (w_aff·β₂ + w_se·β₃ + w_sd·β₄)
- Other-humor weights: affiliative=0.5821, self-enhancing=0.4030, self-defeating=0.0149
- 추정치: +0.2605  SE=0.0541  t=+4.8144  p=0.0000 ***
- **H2-1 지지: aggressive > other humor weighted average (p<.01)**

---

## 5. H2-2 검정 결과 (Pairwise Contrasts)

**명제**: Aggressive humor가 각 유머 유형보다 engagement가 높다.

| Contrast | 추정치 | SE | t | p (2-sided) | Stars | 판정 |
|:---|---:|---:|---:|---:|:---:|:---|
| β₁ − β₂ (agg vs. affiliative) | +0.4278 | 0.0553 | +7.7391 | 0.0000 | *** | H2-2 지지: aggressive > affiliative (p<.01) |
| β₁ − β₃ (agg vs. self-enhancing) | +0.0213 | 0.0565 | +0.3773 | 0.7060 |  | H2-2 지지 불가: aggressive > self-enhancing 방향이나 유의하지 않음 |
| β₁ − β₄ (agg vs. self-defeating) | +0.1916 | 0.1214 | +1.5793 | 0.1143 |  | H2-2 지지 불가: aggressive > self-defeating 방향이나 유의하지 않음 |

**H2-2 종합 판정**: 부분 지지 (partial support): 세 대비 중 1개 유의

---

## 6. 해석 주의사항

1. **Classifier limitation**: 결과는 domain-adapted TF-IDF LogReg 예측값 기반이며, 동일 코퍼스에서 훈련된 분류기를 적용했으므로 leakage risk 존재.
2. **Controls/FE 미포함**: 기업 특성, 시간 트렌드, 포스트 속성이 통제되지 않아 추정치에 omitted variable bias가 있을 수 있음.
3. **단순 OLS 진단 목적**: 이 결과는 "기초 OLS 진단"으로 해석하며, causal 또는 robust evidence로 단정하지 않음.
