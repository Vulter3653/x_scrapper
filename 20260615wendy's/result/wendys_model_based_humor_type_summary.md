# Wendy's 모델 기반 유머 타입 분류 결과

## 1. 작업 목적

사람 기반 유머 타입 라벨(coder1 > human > coder2 우선순위)을 이용해
TF-IDF + Logistic Regression 기반 유머 타입 분류기를 학습하고,
전체 Wendy's 978개 post에 대해 유머 타입 예측값을 생성하였다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_humor_review_sheet.csv`
- `20260615wendy's/result/wendys_final_humor_presence_full_predictions.csv`

## 3. 학습 표본 구성

| 항목 | 건수 |
|---|---|
| 전체 학습 표본 | 278건 |
| aggressive | 95건 |
| other_humor | 183건 |
| 제외: non_humor | 288건 |
| 제외: humor_missing_type | 31건 |
| 제외: unlabeled | 381건 |

## 4. 모델 구조

- TF-IDF (ngram 1-2, min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
- Logistic Regression (class_weight=balanced, solver=liblinear)
- feature: text만 사용 (engagement 변수 및 기존 모델 예측값 미포함)
- primary 분류: aggressive vs other_humor (이진)

## 5. 검증 결과 (5-fold Stratified CV + OOF)

| 지표 | CV 평균 | OOF |
|---|---|---|
| accuracy | 0.6868±0.0294 | 0.6871 |
| F1 (aggressive) | 0.5467±0.0527 | 0.5492 |
| ROC-AUC | 0.7403±0.0323 | 0.7428 |
| balanced accuracy | 0.6559±0.0380 | 0.6560 |
| precision | 0.5408±0.0382 | 0.5408 |
| recall | 0.5579±0.0855 | 0.5579 |

OOF confusion matrix:

|  | predicted: other_humor | predicted: aggressive |
|---|---|---|
| actual: other_humor | 138 (TN) | 45 (FP) |
| actual: aggressive | 42 (FN) | 53 (TP) |

### 4-type 탐색적 모델

4-type model은 exploratory 전용. self-defeating=15건(<20건 기준 미달)이므로 primary로 사용하지 않음.

## 6. 전체 978건 예측 결과

| 예측 그룹 | 건수 |
|---|---|
| non_humor (pred_humor_final_050=0) | 414건 |
| aggressive | 200건 |
| other_humor | 364건 |

type_prediction_scope:

| scope | 건수 |
|---|---|
| human_type_labeled_humor | 278건 |
| model_predicted_humor | 297건 |
| model_predicted_non_humor | 403건 |

## 7. 주요 산출 변수

| 변수 | 설명 |
|---|---|
| `p_type_aggressive_model` | aggressive일 확률 (전체 978건) |
| `p_type_other_humor_model` | other_humor일 확률 (전체 978건) |
| `pred_humor_type_group_model` | 최종 예측 그룹 (pred_humor_final_050 결합) |
| `pred_humor_type_group_model_050` | 0.5 임계값 기준 (동일) |
| `type_prediction_scope` | 예측 출처 구분 |

## 8. 해석상 주의사항

본 결과는 사람 기반 타입 라벨을 이용해 학습한 모델 기반 예측값이며, 전체 978건에 대한 확정 사람 코딩 결과가 아니다.

유머 타입 라벨은 coder agreement가 낮았기 때문에, 모델 기반 타입 예측 결과는 예비적 분류값으로 해석해야 한다.

engagement 변수는 모델 feature로 사용하지 않았으므로, 타입 분류 모델은 engagement 결과를 직접 학습한 것이 아니다.

## 9. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음 (original_posts_json_modified = False)
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
