# Wendy's final_humor_binary 기반 유머 유무 분류 모델 요약

생성일시: 2026-06-15 17:07 UTC

---

## 1. 작업 목적

`wendys_humor_review_sheet.csv`에 통합된 최종 사람 코딩 결과(`final_humor_binary`)를
기준 라벨로 사용하여, Wendy's 전체 트위터 게시글의 유머 유무(humor presence)를
분류하는 TF-IDF + Logistic Regression 모델을 학습·검증·예측한다.

이번 작업에서는 **유머 유무만 분류**한다. 유머 타입 분류는 수행하지 않는다.

---

## 2. 입력 데이터

| 항목 | 값 |
|------|-----|
| 입력 파일 | `wendys_humor_review_sheet.csv` |
| 전체 게시글 수 | 978건 |
| 기준 라벨 | `final_humor_binary` |

---

## 3. 최종 라벨 기준

`final_humor_binary`는 세 사람 코더의 레이블을 다음 우선순위로 통합한 최종 라벨이다.

```
우선순위: coder1 > human > coder2
```

---

## 4. 라벨 분포

| 항목 | 건수 | 비율 |
|------|------|------|
| 라벨 유효 (final_humor_label_available=1) | 597건 | 61.0% |
| — 유머 (final_humor_binary=1) | 309건 | 51.8% |
| — 비유머 (final_humor_binary=0) | 288건 | 48.2% |
| 라벨 없음 | 381건 | 39.0% |

라벨 출처:

| 출처 | 건수 |
|------|------|
| coder1 | 250건 |
| human | 99건 |
| coder2 | 248건 |

---

## 5. 모델 구조

```
TfidfVectorizer(
    lowercase=True, ngram_range=(1, 2),
    min_df=2, max_df=0.95, sublinear_tf=True
)
+ LogisticRegression(
    class_weight="balanced", solver="liblinear",
    max_iter=1000, random_state=42
)
```

vocabulary 크기: 1705개
min_df 사용값: 2

입력 변수: `text` (전처리 후)
라벨: `final_humor_binary`
engagement 변수: 학습에 사용하지 않음

---

## 6. 교차검증 결과 (Stratified 5-fold)

| 지표 | 평균 | 표준편차 |
|------|------|---------|
| Accuracy | 0.6600 | 0.0261 |
| Precision | 0.6503 | 0.0260 |
| Recall | 0.7443 | 0.0330 |
| F1 | 0.6937 | 0.0235 |
| ROC-AUC | 0.7095 | 0.0337 |
| Balanced Accuracy | 0.6568 | 0.0261 |

---

## 7. Out-of-fold 오류 분석

OOF confusion matrix (threshold=0.5):

| | 예측: 유머 | 예측: 비유머 |
|---|---|---|
| **실제: 유머** | 230 (TP) | 79 (FN) |
| **실제: 비유머** | 124 (FP) | 164 (TN) |

| 지표 | 값 |
|------|-----|
| OOF Accuracy | 0.6600 |
| OOF Precision | 0.6497 |
| OOF Recall | 0.7443 |
| OOF F1 | 0.6938 |

---

## 8. 전체 978건 확장 예측 결과

| 항목 | 값 |
|------|-----|
| 예측 유머 (pred_humor_final_050=1) | 564건 (57.7%) |
| 예측 비유머 (pred_humor_final_050=0) | 414건 (42.3%) |
| p_humor_final_tfidf_logreg 최솟값 | 0.0455 |
| p_humor_final_tfidf_logreg 평균 | 0.5116 |
| p_humor_final_tfidf_logreg 중앙값 | 0.5324 |
| p_humor_final_tfidf_logreg 최댓값 | 0.7926 |

---

## 9. 기존 모델과의 비교

| 항목 | 기존 | 신규 |
|------|------|------|
| 유머 예측 건수 | 529건 (54.1%) | 564건 (57.7%) |
| p_humor 평균 | 0.4974 | 0.5116 |
| p_humor 중앙값 | 0.5086 | 0.5324 |

신규 예측값과 기존 예측값 상관:

| 비교 | Pearson r |
|------|-----------|
| p_humor vs p_humor_final_tfidf_logreg | 0.7039 |
| p_humor_ml vs p_humor_final_tfidf_logreg | 0.4845 |

---

## 10. 주요 feature 해석

**유머 방향 상위 10 feature (coefficient 기준):**

```
  1. love
  2. up
  3. it
  4. your
  5. wendy
  6. here
  7. nationalroastday
  8. at
  9. was
  10. means
```

**비유머 방향 상위 10 feature:**

```
  1. url
  2. vote
  3. mention url
  4. mention
  5. url url
  6. does
  7. see
  8. tomorrow
  9. play
  10. order
```

---

## 11. 해석

- ROC-AUC 0.7095는 랜덤(0.5) 대비 유의미한 판별력을 보인다.
- F1 0.6937는 유머/비유머 클래스 불균형을 감안할 때 적절한 수준이다.
- `class_weight="balanced"` 적용으로 소수 클래스 편향을 완화하였다.

---

## 12. 한계

- `final_humor_binary`는 사람 코더 및 기존 human label을 우선순위 규칙으로 병합한 최종 유머 유무 라벨이다.
- 라벨 유효 표본은 전체 978건 중 597건이며, 나머지 381건은 모델 예측으로만 분류된다.
- 본 모델은 유머 유무만 분류하며, 유머 타입은 분류하지 않는다.
- TF-IDF Logistic Regression은 텍스트 기반 모델이므로 이미지, 영상, 외부 맥락 의존 유머를 완전히 포착하지 못할 수 있다.
- 단일 모델 기반 예측값은 최종 확정 라벨이 아니라 예측 확률로 해석해야 한다.
- engagement 변수는 모델 학습에 사용하지 않았다.
