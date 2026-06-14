# H1-H3 × CAR Regression Master Dataset Plan

## A. 목적

이 문서는 H1-H3 humor hypothesis IV와 현재 사용 가능한 market reaction DV인 CAR_m1_p1을 결합한 **regression-ready master dataset** 구축 계획을 정의한다.

회귀분석은 이 단계에서 실행하지 않는다. 이 단계는 회귀분석 실행 직전의 데이터 준비 단계이다.

---

## B. DV 역할 구분 (보류 상태 포함)

| DV | 역할 | 현재 상태 |
|----|------|-----------|
| **Tobin's Q** | Primary Brand Equity DV (장기, level-based) | **보류** — financial statement panel 미확보. Scaffold: `data/derived/brand_equity/tobins_q_brand_equity_panel.csv` |
| **CAR_m1_p1** | Secondary DV — short-window market reaction proxy | **실행 가능** — 580 rows ready |
| **CAR_m3_p3** | Robustness DV — medium-window (placeholder) | **missing** — daily abnormal return 파일 필요. Gemini audit 진행 중. |
| **CAR_m5_p5** | Robustness DV — wide-window (placeholder) | **missing** — daily abnormal return 파일 필요 |

### 허용 표현

- "CAR is a short-window capital market response proxy."
- "CAR is a market-based brand/value response proxy (secondary DV)."
- "CAR is a secondary DV while Tobin's Q is deferred."

### 금지 표현

| 표현 | 금지 이유 |
|------|-----------|
| "CAR = Tobin's Q" | 측정 대상과 시간 지평이 다름 |
| "CAR = direct Brand Equity" | CAR은 market reaction, Brand Equity는 stock of value |
| "CAR = consumer-based brand equity" | 완전히 다른 개념 |
| "CAR → causal brand equity effect" | 이 데이터로 인과 추론 불가 |

### CAR window 이름 혼동 금지

| 혼동 | 이유 |
|------|------|
| CAR_0_p3 → CAR_m3_p3 이름 변경 | Window 자체가 다름: [0,+3] ≠ [-3,+3] |
| CAR_0_p5 → CAR_m5_p5 이름 변경 | Window 자체가 다름: [0,+5] ≠ [-5,+5] |

---

## C. Hypothesis-IV 매핑

### H1: Humor Presence / Usage → CAR

**예측 방향**: 유머 사용 비율이 높은 기업-기간의 10-K filing 이후 CAR이 높다.

| IV | 유형 | 변수 |
|----|------|------|
| 주 IV | continuous | `humor_share`, `humor_presence_any` |
| 보조 IV | count | `humor_count`, `log_humor_count` |
| Ambiguity sensitivity | 3가지 variant | `humor_share_ambiguity_as_zero`, `_excluded`, `_as_missing` |

### H2: Humor Type Effect → CAR

**예측 방향**: aggressive humor type은 Brand/Value 반응에 부정적 영향; affiliative humor는 긍정적 영향.

| IV | 유형 | 변수 |
|----|------|------|
| Aggressive | continuous | `aggressive_share` |
| Affiliative | continuous | `affiliative_share` |
| Self-enhancing | continuous | `self_enhancing_share` |
| Self-defeating | continuous | `self_defeating_share` |
| Composite negative | continuous | `rare_negative_humor_share` |

### H3: Aggressive Humor Intensity (Inverted-U) → CAR

**예측 방향**: aggressive humor intensity와 CAR 간의 역-U 관계 (moderate intensity = peak).

| IV | 유형 | 변수 |
|----|------|------|
| Linear term | continuous | `aggressive_humor_usage_intensity` |
| Quadratic term | continuous | `aggressive_humor_usage_intensity_sq` |

**H3 희소성 경고**: aggressive intensity가 0인 비율 = 98.5% (584 rows 중 9개만 nonzero). 통계적 검정력 매우 낮음. H3는 서술적 분석 또는 robustness로만 활용 권장.

---

## D. Temporal Alignment 전략

### 정렬 방식

| `alignment_type` | 규칙 | 권장 |
|------------------|------|------|
| `prefiling_lag_1m` | humor period == filing_month − 1 | **주 분석 권장** |
| `prefiling_lag_3m` | humor period ∈ {filing_month−3, −2, −1} (lag_1m 제외) | **주 분석 또는 robustness** |
| `same_month` | humor period == filing_date의 YYYY-MM | **보조 sensitivity만** |

### Row 수 현황 (584 rows 기준)

| alignment_type | rows |
|----------------|------|
| prefiling_lag_1m | 141 |
| prefiling_lag_3m | 292 |
| same_month | 151 |
| **recommended 합계** | **433** |

주 분석 데이터셋 필터: `alignment_type in ('prefiling_lag_1m', 'prefiling_lag_3m')` → 433 rows.

---

## E. Dataset 구조

**Unit of observation**: company_name × period × filing_date (0 duplicates confirmed)

**Input 경로**:
```
data/derived/car_event_windows/humor_car_linkage_panel.csv  (584 rows)
data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv  (3,767 rows)
```

**Enrichment**: linkage panel에 없는 컬럼을 humor_vars에서 (company_name, period) 기준 join:
- `log_humor_count`
- `affiliative_share`
- `self_enhancing_share`
- `self_defeating_share`

**Output**: `data/derived/regression/humor_car_hypothesis_regression_master.csv` (584 rows, 36 columns)

---

## F. Industry Control

`industry_homogeneity_control` = `naics_sector_code`

- 6-digit `naics_code`는 현재 korea_uni 파일에 없음 (empty)
- `naics_sector_code`는 273/273 available
- 회귀분석에서 industry FE 또는 cluster variable로 활용

---

## G. CAR_m3_p3 / CAR_m5_p5 Pending 처리

현재 regression master에서:
- `CAR_m3_p3`, `CAR_m5_p5` 컬럼 존재하나 모두 empty
- `join_ready_for_CAR_m3_p3` = false, `join_ready_for_CAR_m5_p5` = false
- `CAR_m3_p3_computed: false`, `CAR_m5_p5_computed: false` (manifest 기록)
- `daily_abnormal_return_required_for_symmetric_long_windows: true` (manifest 기록)

**Gemini audit 완료 후 업데이트 경로**:
1. `event_window_daily_abnormal_returns.csv`가 korea_uni에 있으면 → `data/external/korea_uni/`에 복사
2. `Build CAR Symmetric Event Window Panel` workflow 재실행
3. 이 workflow (`Build Humor CAR Regression Master`) 재실행
4. CAR_m3_p3, CAR_m5_p5 값 자동 채워짐

---

## H. 제약 사항

| 항목 | 상태 |
|------|------|
| 회귀분석 실행 | 금지 (이 단계) |
| causal claim | 금지 |
| human/gold label claim | 금지 |
| CAR을 Tobin's Q로 해석 | 금지 |
| CAR을 direct Brand Equity로 표현 | 금지 |
| CAR_0_p3 → CAR_m3_p3 이름 변경 | 금지 |
| CAR_m3_p3 / CAR_m5_p5 daily AR 없이 계산 | 금지 |
| raw data / humor outputs 수정 | 금지 |
| korea_uni source repo 수정 | 금지 |
| 외부 API 호출 | 금지 |

---

## I. 다음 단계

```
[현재] Regression master dataset 준비 완료 (584 rows, CAR_m1_p1 ready)
  ↓
[Gemini 결과 대기] daily_abnormal_returns.csv 존재 여부 확인
  ├── 존재하면: 파일 복사 → Build CAR Symmetric Event Window Panel 재실행
  │            → Build Humor CAR Regression Master 재실행
  │            → CAR_m3_p3, CAR_m5_p5 활성화
  └── 없으면:  CAR_m1_p1 전용 분석으로 진행
  ↓
[보류] Tobin's Q financial panel 확보 → primary DV 전환
  ↓
[추후] H1-H3 regression script 구성
       주 분석: alignment_type in ('prefiling_lag_1m', 'prefiling_lag_3m')
       DV: CAR_m1_p1 (현재), Tobin's Q (추후)
       Controls: naics_sector_code (industry FE)
       H3: 희소성으로 인해 서술적 분석 권장
```
