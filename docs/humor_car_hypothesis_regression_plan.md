# H1-H3 × CAR Hypothesis Regression Plan

## A. 목적 및 DV 역할 구분

이 단계는 **Gate 2: Hypothesis Testing**에 해당한다. Gate 1(regression-ready master dataset)은 PASS 판정.

### DV 위계

| DV | 역할 | 현재 상태 |
|----|------|-----------|
| **Tobin's Q** | Primary Brand Equity DV (장기, level-based) | **보류** — financial statement panel 미확보 |
| **CAR_m1_p1** `[-1,+1]` | Secondary DV — short-window market reaction proxy | **활성** — 430 rows ready (primary sample) |
| CAR_m3_p3 `[-3,+3]` | Robustness DV (placeholder) | **missing** — daily AR 파일 필요 |
| CAR_m5_p5 `[-5,+5]` | Robustness DV (placeholder) | **missing** — daily AR 파일 필요 |

**금지 해석**: CAR ≠ Tobin's Q, CAR ≠ direct Brand Equity, CAR ≠ causal Brand Equity effect.

---

## B. Sample 정의

### Primary sample (주 분석)

```
alignment_type in ('prefiling_lag_1m', 'prefiling_lag_3m')
AND join_ready_for_CAR_m1_p1 == True
→ N = 430 rows, 78 companies, 3 fiscal years (2023/2024/2025), 8 NAICS sectors
```

### Robustness / Sensitivity samples

| Sample | Filter | N |
|--------|--------|---|
| lag_1m only | prefiling_lag_1m | 140 |
| lag_3m only | prefiling_lag_3m | 290 |
| same_month | same_month | 150 (simultaneity 주의) |

---

## C. Fixed Effects 구조

| 모델 | Period FE | Industry FE | Company FE |
|------|-----------|-------------|------------|
| 주 모델 (H1a, H1b, H2a, H2b, H3) | target_report_year (3년→2 dummies) | naics_sector_code (8→7 dummies) | 없음 |
| H1a_compFE (robustness) | target_report_year | 없음 | company_name (78→77 dummies) |

Company FE를 주 모델에 사용하지 않는 이유: 430 rows에서 78개 company dummy를 포함하면 DoF를 과도하게 흡수한다. H1a_compFE에서 R²=0.49가 되지만 humor_share 계수가 소멸 (β=-0.0001, p=0.99).

---

## D. Controls

모든 모델에 공통 적용:
- `log_humor_count`: posting volume 통제
- `ambiguity_rate`: 분류 불확실성 통제
- `high_ambiguity_flag`: 고불확실성 firm-period 통제
- `source_x_handle_count`: 계정 수 통제

---

## E. 모델 명세

### H1a (기본 모델)
```
CAR_m1_p1 = β₁·humor_share + controls + year_FE + naics_FE + ε
```

### H1b (이진 지표)
```
CAR_m1_p1 = β₁·humor_presence_any + controls + year_FE + naics_FE + ε
```

### H2a (humor type-share 모델)
```
CAR_m1_p1 = β₁·aggressive_share + β₂·self_enhancing_share + β₃·self_defeating_share
           + controls + year_FE + naics_FE + ε

[affiliative_share = reference category, 제외됨]
[humor_share와 type-share를 동시에 포함하지 않음]
```

### H2b (rare-negative composite)
```
CAR_m1_p1 = β₁·rare_negative_humor_share + controls + year_FE + naics_FE + ε
```

### H3 (inverted-U, exploratory)
```
CAR_m1_p1 = β₁·aggressive_humor_usage_intensity
           + β₂·aggressive_humor_usage_intensity_sq
           + controls + year_FE + naics_FE + ε

판정 기준: β₁ > 0 AND β₂ < 0 → inverted-U 방향 지지
[EXPLORATORY ONLY — primary sample 내 nonzero rows: 5/430, zero share: 98.8%]
```

---

## F. 결과 요약 (Gate 2 실행 기준)

### 전체 모델 현황

| 모델 | N | R² | 비고 |
|------|---|-----|------|
| H1a | 430 | 0.053 | |
| H1b | 430 | 0.054 | |
| H2a | 430 | 0.057 | 3 focal IVs |
| H2b | 430 | 0.052 | |
| H3 | 430 | 0.052 | EXPLORATORY |
| H1a_lag1m | 140 | 0.078 | robustness |
| H1a_lag3m | 290 | 0.046 | robustness |
| H1a_samemon | 150 | 0.059 | sensitivity (simultaneity 주의) |
| H1a_compFE | 430 | 0.491 | company FE robustness |

### H1 결과

| 모델 | IV | β | SE | t | p |
|------|-----|---|-----|---|---|
| H1a | humor_share | +0.013 | 0.018 | +0.71 | 0.478 |
| H1b | humor_presence_any | +0.009 | 0.010 | +0.98 | 0.328 |
| H1a_lag1m | humor_share | +0.006 | 0.060 | +0.10 | 0.918 |
| H1a_lag3m | humor_share | +0.011 | 0.020 | +0.56 | 0.578 |
| H1a_samemon | humor_share | -0.003 | 0.039 | -0.09 | 0.932 |
| H1a_compFE | humor_share | -0.0001 | 0.018 | -0.01 | 0.994 |

**해석**: H1에 대한 통계적으로 유의한 증거 없음. humor_share와 humor_presence_any 모두 p > 0.10. 방향은 주 모델(H1a, H1b)에서 양(+)이지만 유의하지 않음.

### H2 결과

| 모델 | IV | β | SE | t | p |
|------|-----|---|-----|---|---|
| H2a | aggressive_share | +0.159 | 0.564 | +0.28 | 0.778 |
| H2a | self_enhancing_share | +0.032 | 0.022 | +1.43 | 0.154 |
| H2a | self_defeating_share | -0.325 | 0.595 | -0.55 | 0.585 |
| H2b | rare_negative_humor_share | -0.095 | 0.414 | -0.23 | 0.818 |

**해석**: H2에 대한 통계적으로 유의한 증거 없음. self_enhancing_share의 β=+0.032이 p=0.154로 가장 유의에 가깝지만 관례적 임계값 미달. aggressive_share, self_defeating_share는 극단적 희소성(각 5, 4 nonzero rows)으로 계수 불안정.

### H3 결과 (EXPLORATORY)

| IV | β | SE | t | p |
|-----|---|-----|---|---|
| aggressive_humor_usage_intensity | +1.606 | 2.963 | +0.54 | 0.588 |
| aggressive_humor_usage_intensity_sq | -27.768 | 55.298 | -0.50 | 0.616 |

**해석**: β₁ > 0, β₂ < 0으로 inverted-U 방향과 일치하나, 통계적으로 유의하지 않음. **primary sample 내 nonzero rows = 5/430 (98.8% zero).** H3는 탐색적 관찰 수준에서만 보고 가능.

---

## G. 해석 범위 (Interpretation Scope)

모든 모델에 적용:

1. **관찰적 상관관계** (correlational association) — 인과 해석 불가
2. **단기 시장 반응** (short-window market reaction proxy) — Brand Equity 직접 측정값이 아님
3. **표본 소규모** — 80개 기업 × 최대 3 filing events
4. **Fortune 100 convenience sample** — representativeness 제한

---

## H. 제약 사항

| 항목 | 상태 |
|------|------|
| causal claim | 금지 (모든 결과는 correlational) |
| CAR = Tobin's Q | 금지 |
| CAR = direct Brand Equity | 금지 |
| CAR_m3_p3 / CAR_m5_p5 사용 | 금지 (all missing) |
| CAR_0_p3 / CAR_0_p5 → symmetric window 대체 | 금지 |
| raw data / humor outputs 수정 | 금지 |
| korea_uni source repo 수정 | 금지 |
| H3 확증적 해석 | 금지 (exploratory만) |

---

## I. 다음 단계

```
[현재] Gate 2 완료 — H1-H3 결과 산출 (CAR_m1_p1 기반)
  ↓
[Gemini audit 결과 대기] daily_abnormal_returns.csv 여부
  → 존재하면: CAR_m3_p3, CAR_m5_p5 활성화 후 robustness 재실행
  → 없으면: CAR_m1_p1 전용 결과로 보고
  ↓
[보류] Tobin's Q financial panel 확보
  → primary DV 전환 후 전체 분석 재실행
  ↓
[추후] 논문용 결과 테이블 구성
  주 분석: H1a, H2a (primary sample)
  Robustness: alignment 별 sample, company FE
  Sensitivity: same_month (simultaneity note 포함)
```
