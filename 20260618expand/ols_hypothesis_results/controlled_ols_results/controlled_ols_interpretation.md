# Controlled OLS 분석 해석 (Controls: text_length, hashtag_count, mention_count)

**생성일**: 2026-06-19
**SE**: Classical OLS
**분석 성격**: PRELIMINARY DIAGNOSTIC ONLY
**금지 controls**: emoji_count ← 사용하지 않음

---

## 1. H1: 유머 포스트 → 더 높은 engagement

### H1 Batch1

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 1.24004 | 0.134358 | 0.0 | *** |
| Time FE(ym)+ctrl | 1.018589 | 0.124173 | 0.0 | *** |
| Firm dummy+ctrl  | 0.227296 | 0.084014 | 0.006905 | *** |
| Firm+YM FE+ctrl  | 0.171119 | 0.130037 | 0.188826 | ns |

### H1 Full (예측 레이블)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 1.145154 | 0.01674 | 0.0 | *** |
| Time FE(ym)+ctrl | 1.097634 | 0.015878 | 0.0 | *** |
| Firm dummy+ctrl  | 0.253389 | 0.012224 | 0.0 | *** |
| Firm+YM FE+ctrl  | 0.209034 | 0.011588 | 0.0 | *** |

### H1 요약
- **양수 방향 유지**: Controls 추가 후에도 β > 0 유지 여부 → 파일에서 확인
- **Full 유의성**: Controls 추가 후 Full 유의성 유지 여부 확인

---

## 2. H2-1: Aggressive vs Other humor

### H2-1 Batch1

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 0.649363 | 0.423465 | 0.125656 | ns |
| Time FE(ym)+ctrl | 0.738705 | 0.404797 | 0.06857 | * |
| Firm dummy+ctrl  | 0.115144 | 0.277796 | 0.678675 | ns |
| Firm+YM FE+ctrl  | 0.349255 | 0.478192 | 0.466248 | ns |

### H2-1 Full (⚠ NOT_A_CANDIDATE)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 0.103452 | 0.030011 | 0.000567 | *** |
| Time FE(ym)+ctrl | 0.046519 | 0.027307 | 0.088475 | * |
| Firm dummy+ctrl  | -0.071555 | 0.017226 | 3.3e-05 | *** |
| Firm+YM FE+ctrl  | -0.064106 | 0.01647 | 0.0001 | *** |

---

## 3. H2-2: Four humor types (ref=affiliative)

### H2-2 Batch1 aggressive coefficient

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 0.76056 | 0.437943 | 0.082927 | * |
| Time FE(ym)+ctrl | 0.783143 | 0.418342 | 0.061745 | * |
| Firm dummy+ctrl  | 0.220593 | 0.290694 | 0.448265 | ns |
| Firm+YM FE+ctrl  | 0.49896 | 0.499836 | 0.319705 | ns |

### H2-2 Full predicted_aggressive coefficient (⚠ NOT_A_CANDIDATE)

| 모델 | β | SE | p | 판정 |
|---|---|---|---|---|
| Plain OLS + ctrl | 0.125208 | 0.030454 | 3.9e-05 | *** |
| Time FE(ym)+ctrl | 0.048176 | 0.027725 | 0.082284 | * |
| Firm dummy+ctrl  | -0.077539 | 0.01751 | 1e-05 | *** |
| Firm+YM FE+ctrl  | -0.070074 | 0.016747 | 2.9e-05 | *** |

---

## 4. H3: Aggressive intensity → engagement (역 U자형 가설)

### H3 Full

| 모델 | β1 | β2 | β1_판정 | 전환점 |
|---|---|---|---|---|
| Plain OLS+ctrl | 0.307199 | 0.975744 | ns | -0.1574 |
| YM FE+ctrl | 0.519745 | 0.747196 | ns | success |
| Firm dummy+ctrl | -2.055619 | 2.865421 | *** | 0.3587 |
| Firm+Year FE+ctrl | -0.971195 | 1.46244 | *** | 0.332 |

Batch1: not_applicable (firm cross-section)

---

## 5. 핵심 해석 요점

### 5.1 H1 controls 추가 후 방향 유지 여부
참조: h1_controlled_results.csv — coefficient 열 부호 확인.
Plain OLS → Firm+YM FE까지 양수 유지 여부가 핵심.

### 5.2 H1 Full controls 추가 후 유의성
Full 샘플 n=68,039 → controls 추가 후에도 충분한 파워 유지 예상.

### 5.3 H2-1 firm FE 포함 시 방향 역전
Firm dummy only (no-control): Full β=−0.101***
Firm dummy only (controlled): 위 표 참조 → 역전 유지 여부.

### 5.4 H2-2 aggressive coefficient controls 후 변화
Firm dummy only (no-control): Batch1 β=0.206 ns, Full β=−0.112***
Controls 추가 후 Full 역전 유지 여부.

### 5.5 H3 역U자형 / U자형 패턴 변화
No-control: firm dummy 후 U자형(β1<0, β2>0).
Controls 추가: 위 표 참조.

### 5.6 Controls 추가로 β 크기 변화
비교 파일: controlled_vs_no_control_comparison.csv → beta_no_control vs beta_controlled

### 5.7 Full H2/H3 Classifier NOT_A_CANDIDATE
Full H2와 H3 full sample 결과는 classifier가 NOT_A_CANDIDATE 상태 (leakage 가능)로,
controls 추가 여부와 무관하게 공식 가설 검증에 사용할 수 없다.
결과는 방향성 참고 수준에만 활용한다.

### 5.8 Batch1 소표본 limitation
- H1 batch1: n=1,482 → firm+YM FE에서 df_resid 급감
- H2-1 batch1: n=648, n_agg=44 → 극단적 저파워
- H2-2 batch1: n=648, 4유형 분할 시 각 셀 n이 더 작아짐

---

## 6. 금지사항 준수

- [x] emoji_count 미사용 (`emoji_count_used=false`)
- [x] company_id_used_as_numeric=false
- [x] c_company_formula_used=false
- [x] controls_included=true (text_length, hashtag_count, mention_count)
- [x] 기존 no-control 결과 파일 미수정
- [x] data/raw 미수정
- [x] dashboard/data 미수정
- [x] classifier 결과 파일 미수정
- [x] integrated corpus 미수정

*생성 스크립트*: `run_controlled_ols_hypotheses.py`
*출력 폴더*: `controlled_ols_results/`
*생성일*: 2026-06-19
