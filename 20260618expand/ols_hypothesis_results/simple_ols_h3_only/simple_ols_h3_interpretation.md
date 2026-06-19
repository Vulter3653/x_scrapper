# OLS H3 해석 — M1 Simple OLS + M2 Firm FE (Preliminary Diagnostic)

> **주의**: domain-adapted 분류기 예측값 기반. Controls 미포함. NOT_A_CANDIDATE 수준 증거.

---

## 1. 표본 구성

| 항목 | 값 |
|:---|---:|
| Total firm-month observations | 3,532 |
| Firms | 97 |
| Months | 130 |
| Nonzero intensity firm-months | 747 (21.1%) |
| AggressiveIntensity mean | 0.0225 |
| AggressiveIntensity SD | 0.0667 |
| AggressiveIntensity min/max | 0.0000 / 1.0000 |

---

## 2. 회귀 결과

|  | M1 Simple OLS | M2 Firm FE (FWL) |
|:---|:---:|:---:|
| Intensity (β₁) | +6.4145*** (0.6764) | -1.0235*** (0.3954) |
| Intensity² (β₂) | -6.4029*** (1.2540) | +1.6552** (0.6652) |
| Intercept | +3.4616 | absorbed |
| N | 3,532 | 3,532 |
| Firms | — | 97 |
| R² | 0.0301 | 0.0021 (within) |
| adj-R² | 0.0296 | -0.0264 |
| df_resid | 3,529 | 3,433 |

---

## 3. H3 역U자형 진단

| 진단 항목 | M1 Simple OLS | M2 Firm FE (FWL) | H3 요건 |
|:---|:---:|:---:|:---|
| β₁ 부호 | 양수 ✓ | 음수 ✗ | 양수 |
| β₁ p-value | *** (0.0000) | *** (0.0097) | — |
| β₂ 부호 | 음수 ✓ | 양수 ✗ | 음수 |
| β₂ p-value | *** (0.0000) | ** (0.0129) | 유의 |
| 전환점 | 0.5009 | 0.3092 | 관측 범위 내 |
| 범위 내 여부 | 예 ✓ | 예 ✓ | 예 |
| 패턴 | inverted-U | U-shaped | inverted-U |
| H3 지지 | 지지 ✓ | 지지 불가 ✗ | true |

**판정**:
- M1 Simple OLS: H3 지지 (p<.01): β₁>0, β₂<0 유의, 전환점 관측 범위 내
- M2 Firm FE:    H3 지지 불가: β₂>0 (역U자형 아님)

---

## 4. 해석 주의사항

1. **Zero-inflation**: 전체 firm-month의 78.9%가 intensity=0. quadratic 추정이 nonzero 747개 관측치에 집중.
2. **Classifier limitation**: aggressive_humor_usage_intensity는 domain-adapted 분류기 예측값 기반. Leakage risk 존재.
3. **Controls 미포함**: 시간 FE, 포스트 속성 미통제. M2 Firm FE는 기업 수준 고정 이질성 흡수.
4. **단순 OLS 진단 목적**: preliminary diagnostic. Robust causal evidence 아님.
