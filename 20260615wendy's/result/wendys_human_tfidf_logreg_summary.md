# Wendy's human-coded seed label 기반 TF-IDF Logistic Regression 유머 분류 검증 요약

생성일시: 2026-06-15 12:55 UTC

> **본 결과는 Wendy's 전체 게시글에서 추출된 랜덤 human-coded sample(68건)을 기반으로 한 exploratory calibration이다.
> 전체 Wendy's 데이터에 대한 최종 확정 분류로 해석하지 않는다.**

---

## 1. 작업 목적

사람이 직접 코딩한 Wendy's 유머 라벨(68건)을 seed label로 사용하여
TF-IDF + Logistic Regression 분류 모델을 검증하고,
전체 978건에 유머 확률(`p_humor_tfidf_logreg_human`)을 확장 예측한 후
H1을 단순 OLS로 재분석한다.

---

## 2. 입력 데이터

| 파일 | 행 수 |
|------|-------|
| `wendys_partial_human_coded_humor_labels.csv` | 69건 |
| `wendys_fast_weak_supervised_humor_dataset.csv` | 978건 |

---

## 3. Human label 정리 방식

| 항목 | 건수 |
|------|------|
| 원본 파일 행 | 69 |
| label 사용 행 | 68 |
| humor = 1 | 37 |
| non_humor/none → 0 | 31 (none 처리: 2건) |
| 결측 제외 | 1 |
| 전체 데이터 병합 성공 | 68 |
| 병합 실패 | 0 |

라벨 변환 규칙:
- `humor` → 1
- `non_humor`, `none` → 0
- 공란 → 분석 제외

---

## 4. 모델 구조

```
TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95, sublinear_tf=True)
→ LogisticRegression(class_weight="balanced", solver="liblinear")
```

텍스트 전처리: 소문자 변환, URL→`<URL>`, @mention→`<MENTION>`, `#` 기호 제거(단어 보존)
engagement 변수는 학습에 사용하지 않음.

---

## 5. Cross-validation 결과 (StratifiedKFold, k=5)

| 지표 | 평균 | 표준편차 |
|------|------|---------|
| accuracy | 0.7066 | 0.1024 |
| precision | 0.7750 | 0.1333 |
| recall | 0.6750 | 0.0662 |
| f1 | 0.7186 | 0.0850 |
| roc_auc | 0.8062 | 0.0709 |
| balanced_accuracy | 0.7065 | 0.1071 |

> **현재 cross-validation 성능은 표본 수가 68건으로 작으므로 참고용으로만 해석한다.**

---

## 6. 오류 분석 (Out-of-fold, threshold=0.5)

| 오류 유형 | 건수 |
|----------|------|
| True Positive  | 25 |
| True Negative  | 23 |
| False Positive | 8 |
| False Negative | 12 |
| 합계 | 68 |

상세 내용은 `wendys_human_tfidf_logreg_error_audit.csv` 참조.

---

## 7. 전체 978개 확장 예측 결과

| 지표 | 값 |
|------|-----|
| 최솟값 | 0.3437 |
| 평균 | 0.4964 |
| 중앙값 | 0.5051 |
| 최댓값 | 0.6479 |
| >= 0.5 (유머 예측) | 519건 (53.1%) |

---

## 8. 기존 `humor_score`, `p_humor_ml`과의 비교

| 지표 | humor_score | p_humor_ml | p_humor_tfidf_logreg_human |
|------|-------------|------------|--------------------------|
| 평균 | 0.0720 | 0.3749 | 0.4964 |
| 0 건수 | 739 | 0 | 0 |

| 상관 | 값 |
|------|-----|
| `p_humor_tfidf_logreg_human` vs `humor_score` | 0.1006 |
| `p_humor_tfidf_logreg_human` vs `p_humor_ml` | 0.3069 |

---

## 9. H1 단순 OLS 재분석 결과

IV: `log1p_p_humor_tfidf_logreg_human`

| 종속변수 | β | p | R² | H1 해석 |
|---|---|---|---|---|
| `log1p_engagement_total` | 6.679812 | 0.000002 | 0.023019 | H1 예비적 지지 |
| `log1p_engagement_favorite_retweet` | 6.596538 | 0.000003 | 0.021827 | H1 예비적 지지 |
| `log1p_favorite_count` | 7.916023 | 0.000002 | 0.023182 | H1 예비적 지지 |
| `log1p_retweet_count` | 4.019080 | 0.005297 | 0.007939 | H1 예비적 지지 |
| `log1p_reply_count` | 6.921235 | 0.000000 | 0.027706 | H1 예비적 지지 |
| `log1p_quote_count` | 1.934285 | 0.197157 | 0.001704 | H1 방향성 지지 |
| `log1p_bookmark_count` | 2.091632 | 0.133264 | 0.002308 | H1 방향성 지지 |


주요 결과 (`log1p_engagement_total`):
β = 6.679812, SE = 1.392952, p = 0.0000, R² = 0.023019

**H1 예비적 지지**

---

## 10. 해석

사람이 코딩한 68건은 Wendy's 전체 게시글에서 추출된 랜덤 샘플이다. 따라서 전체 데이터로 확장할 근거가 있다. 다만 표본 수가 68건으로 작고 단일 코더 기반이므로, 본 결과는 여전히 exploratory calibration으로 해석한다.

랜덤 human-coded sample을 기반으로 TF-IDF + Logistic Regression 유머 분류기를 학습하고 전체 Wendy's 게시글에 확장 예측한 결과, `log1p_p_humor_tfidf_logreg_human`은 `log1p_engagement_total`과 유의한 양의 연관성을 보였다. 이는 H1에 대한 예비적 지지로 해석할 수 있다.

본 분석은 관측적 연관성 분석이며, 유머가 engagement를 증가시킨다는 인과관계를 주장할 수 없다.

`p_humor_tfidf_logreg_human`은 human-coded seed label로 보정된 유머 가능성 점수이다.
기존 `humor_score`(rule-based) 및 `p_humor_ml`(weak-supervised)과의 상관을 보면,
세 측정값이 어느 정도 일치하는지 확인할 수 있다.

(β = 6.6798, p = 0.0000)

---

## 11. 한계

- 68건 랜덤 human-coded sample 기반 — 전체 데이터로 확장할 근거는 있으나, 표본 수가 작기 때문에 exploratory calibration으로 해석한다.
- 표본 수가 68건으로 작아 cross-validation 및 전체 확장 예측의 불확실성이 크다.
- 단일 코더 기반이므로 inter-rater reliability는 검증되지 않았다.
- `p_humor_tfidf_logreg_human`은 human-coded seed label 기반 예측값이며 최종 확정 라벨이 아니다.
- H1 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- engagement 변수는 모델 학습에는 사용하지 않았고, H1의 종속변수로만 사용하였다.
