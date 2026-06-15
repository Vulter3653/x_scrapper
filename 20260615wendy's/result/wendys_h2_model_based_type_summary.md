# Wendy's 모델 기반 유머 타입 H2 확장 분석 결과

## 1. 작업 목적

본 분석은 전체 978건에 대한 모델 기반 유머 타입 예측값을 사용한 supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.
pred_humor_type_group_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 타입 라벨 278건을 학습한 TF-IDF + Logistic Regression 모델의 예측값이다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_model_based_humor_type_full_predictions.csv` (모델 기반 예측값)
- `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv` (engagement 원자료)

## 3. 분석 표본

| 집단 | 건수 |
|---|---|
| 전체 | 978건 |
| humor-only (aggressive+other) | 564건 |
| aggressive (모델 기반 예측) | 200건 |
| other_humor (모델 기반 예측) | 364건 |
| non_humor (모델 기반 예측) | 414건 |

## 4. 분석 방법

- 분석 1: Welch t-test (aggressive vs other_humor, n=564)
- 분석 2: Humor-only simple OLS (aggressive vs other_humor)
- 분석 3: Full predicted sample multi-dummy OLS (base=non_humor, n=978)
- 분석 4: Continuous probability robustness (p_type_aggressive_model)
- 통제변수 없음, 고정효과 없음

## 5. Welch t-test 결과 (aggressive vs other_humor, primary DV: log1p_engagement_total)

| 지표 | 값 |
|---|---|
| n_aggressive | 200건 |
| n_other_humor | 364건 |
| 평균 차이 (aggressive − other_humor) | 0.4684 |
| p-value | 0.0029 ** |
| Cohen's d | 0.2716 (small) |
| H2 해석 | **H2 예비적 지지** |

## 6. Humor-only OLS 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β (aggressive vs other_humor) | 0.4684 |
| p-value | 0.0021 ** |
| R² | 0.0167 |
| H2 해석 | **H2 예비적 지지** |

## 7. Full predicted sample multi-dummy OLS 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β₁ (aggressive vs non_humor) | 0.8031 (p=0.0000***) |
| β₂ (other_humor vs non_humor) | 0.3347 (p=0.0075**) |
| β₁ − β₂ | 0.4684 (p=0.0029**) |
| H2 해석 | **H2 예비적 지지** |

## 8. Probability robustness 결과 (log1p_engagement_total)

| 지표 | 값 |
|---|---|
| β (p_type_aggressive_model) | 2.7026 |
| p-value | 0.0000 *** |
| R² | 0.0325 |

## 9. 기존 human-labeled H2와의 관계

human-labeled H2는 사람 기반 확정 라벨이 있는 표본(n=278, aggressive=95, other_humor=183)에서 aggressive vs other_humor를 비교한 primary evidence이다.

model-based H2는 전체 978건에 대해 예측된 타입 값을 이용한 supplemental extension이다.

기존 human-labeled H2 주요 결과:
- t-test: diff=+0.7074, p=0.0012**, Cohen's d=0.4359 (small)
- humor-only OLS: β=+0.7074, p=0.0007***
- multi-dummy OLS: β₁=1.0715***, β₂=0.3642*, β₁−β₂=0.7074, p=0.0012**

두 분석 모두 aggressive로 분류된 게시글은 other_humor로 분류된 게시글보다 log1p_engagement_total이 높게 나타났다.

## 10. 해석상 주의사항

본 분석은 전체 978건에 대한 모델 기반 유머 타입 예측값을 사용한 supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

pred_humor_type_group_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 타입 라벨 278건을 학습한 TF-IDF + Logistic Regression 모델의 예측값이다.

engagement 변수는 타입 분류 모델의 feature로 사용되지 않았지만, 본 H2 분석은 여전히 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.

유머 타입 라벨은 coder agreement가 낮았기 때문에, 모델 기반 타입 H2 결과 역시 예비적 증거로 해석해야 한다.

## 11. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음
- `wendys_model_based_humor_type_full_predictions.csv`: 수정 없음
- `wendys_h2_coder1_priority_*.csv`: 수정 없음
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
