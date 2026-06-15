# Wendy's Full-Sample 4-Type Humor Classification — 요약 보고서

> **탐색적 모델 기반 전체 표본 분류 (exploratory model-based full-sample classification)**
> 사람 라벨 278건을 학습하여 전체 978개 post에 4-type 유머 분류를 확장함.

---

## 1. 목적

사람 기반 4-type humor 라벨(278건)을 학습 표본으로 사용하여,
전체 Wendy's 978개 post에 대해 모델 기반 4-type humor classification을 생성함.
기존 이진 유머 유무 예측(`pred_humor_final_050`)을 gate로 사용하여 non_humor(414건)를 우선 분리,
나머지 564건에 대해 multinomial logistic regression 기반 타입 예측을 부여함.

---

## 2. 학습 데이터

| 항목 | 값 |
|---|---|
| 학습 표본 수 | 278건 |
| aggressive | 95건 |
| affiliative | 106건 |
| self-enhancing | 62건 |
| self-defeating | 15건 |
| 소표본 경고 | self-defeating n=15 (fold당 약 3건) |

---

## 3. 모델 사양

- **Vectorizer**: TF-IDF (ngram 1-2, min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
- **Classifier**: Multinomial Logistic Regression (class_weight='balanced', solver='lbfgs', max_iter=1000)
- **CV**: Stratified 5-fold
- **Feature**: text only (engagement 변수 및 기존 모델 예측값 feature 미사용)

---

## 4. OOF (Out-of-Fold) 성능

| 지표 | 값 |
|---|---|
| Accuracy | 0.4281 |
| Macro-F1 | 0.3486 |
| Weighted-F1 | 0.4256 |
| Macro-AUC (OvR) | 0.6182 |

**주의**: self-defeating 클래스는 n=15로 소표본임. OOF 성능 해석 시 이 클래스의 결과는 불안정할 수 있음.

---

## 5. 전체 978건 예측 분포

| 카테고리 | pred_full_4type_humor_model | pred_4type_humor_raw_model |
|---|---|---|
| non_humor | 414 (gate) | 0 |
| aggressive | 187 | 270 |
| affiliative | 251 | 466 |
| self-enhancing | 96 | 204 |
| self-defeating | 30 | 38 |
| missing | 0 | - |
| **합계** | **978** | **978** |

---

## 6. Gate 로직

```
pred_humor_final_050 == '0' → pred_full_4type_humor_model = 'non_humor'
pred_humor_final_050 == '1' → pred_full_4type_humor_model = pred_4type_humor_raw_model (argmax)
else                        → pred_full_4type_humor_model = 'missing'
```

non_humor_gate: 414건 / model_predicted: 564건 / missing: 0건

---

## 7. Validation

20개 검증 항목 모두 **PASS** (`20/20`).

---

## 8. 한계점 및 해석 주의사항

1. self-defeating 클래스는 n=15 소표본으로 모델 학습 안정성이 낮음.
2. 본 분석은 exploratory model-based full-sample classification으로,
   사람 판단 기반 분류를 대체하지 않음.
3. TF-IDF 기반 텍스트 특성만 사용하여 문맥, 이미지, 링크 등 비텍스트 정보 미반영.
4. engagement 변수 및 기존 유머 유무 모델 예측값은 feature에서 제외하여
   독립변수-종속변수 순환 편의(circular bias)를 방지함.

---

*생성일: 2026-06-15*
