# Simple OLS H3 해석 (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반 결과. Controls 및 Fixed Effects 미포함.
> NOT_A_CANDIDATE 수준 증거. Classifier leakage risk 존재.

---

## 1. 표본 구성 (Firm-Month Panel)

| 항목 | 값 |
|:---|---:|
| Total firm-month observations | 3,532 |
| Number of firms | 97 |
| Number of months | 130 |
| Firm-months with nonzero intensity | 747 (21.1%) |
| Firm-months with zero intensity | 2,785 (78.9%) |
| AggressiveIntensity mean | 0.0225 |
| AggressiveIntensity SD | 0.0667 |
| AggressiveIntensity min | 0.0000 |
| AggressiveIntensity p25 | 0.0000 |
| AggressiveIntensity median | 0.0000 |
| AggressiveIntensity p75 | 0.0000 |
| AggressiveIntensity max | 1.0000 |

---

## 2. 회귀 결과 (M1 Simple Quadratic OLS)

```
mean_log(1+Engagement)_{ft} = α + β₁·Intensity + β₂·Intensity² + ε
```

| 변수 | β | SE | t | p (2-sided) | Stars |
|:---|---:|---:|---:|---:|:---:|
| Intercept (α) | +3.4616 | 0.0285 | +121.5412 | 0.0000 | *** |
| AggressiveIntensity (β₁) | +6.4145 | 0.6764 | +9.4829 | 0.0000 | *** |
| AggressiveIntensity² (β₂) | -6.4029 | 1.2540 | -5.1058 | 0.0000 | *** |

N=3,532 (firm-month) | R²=0.0301 | adj-R²=0.0296 | df_resid=3,529
Unit = firm×month | Controls = none | FE = none

---

## 3. H3 역U자형 진단

| 진단 항목 | 결과 | H3 요건 |
|:---|:---|:---|
| β₁ 부호 | **양수** ✓ | 양수 (>0) |
| β₁ 유의성 | *** (p=0.0000) | — |
| β₂ 부호 | **음수** ✓ | 음수 (<0) |
| β₂ 유의성 | *** (p=0.0000) | 유의 필요 |
| 전환점 = −β₁/(2β₂) | 0.5009 | 관측 범위 내 |
| 관측 intensity 범위 | [0.0000, 1.0000] | — |
| 전환점 범위 내 여부 | **예** ✓ | 예 |
| 패턴 | inverted-U | inverted-U |

**H3 지지 여부**: **지지** ✓

**판정**: H3 지지 (p<.01): β₁>0, β₂<0 유의, 전환점 관측 범위 내

---

## 4. 해석 주의사항

1. **단순 OLS 진단**: Controls, Fixed Effects 없는 기초 OLS. Firm-level heterogeneity
   및 시간 트렌드가 통제되지 않아 omitted variable bias 가능성 있음.
2. **Zero-inflation**: 전체 firm-month 중 78.9%가 intensity=0.
   quadratic 추정이 소수 nonzero 관측치에 의존함.
3. **Classifier limitation**: aggressive_humor_usage_intensity는 domain-adapted 분류기
   예측값 기반. 동일 코퍼스 훈련으로 leakage risk 존재.
4. **이 결과는 H3의 기초 OLS baseline**으로만 해석하며, robust causal evidence가 아님.
