# Wendy's human-coded 168건 seed label 기반 TF-IDF LogReg 유머 분류 요약 (v2)

생성일시: 2026-06-15 14:02 UTC

> 기존 69건(원본 human labels) + 추가 99건(human_coded_check)을 통합한 **168건**을
> seed label로 재학습한 결과이다.

---

## 1. 작업 목적

기존 69건에서 168건으로 확대된 human-coded seed label을 사용하여
TF-IDF + Logistic Regression 분류 모델을 재학습하고,
전체 978건 유머 확률(`p_humor_human168`)을 재예측한다.
`wendys_humor_review_sheet.csv`의 `model_humor`, `p_humor`, `humor_grade` 컬럼을 업데이트한다.

---

## 2. Human label 현황

| 항목 | 건수 |
|------|------|
| 학습에 사용된 레이블 | 167 |
| humor = 1 | 83 |
| non_humor = 0 | 84 |
| 결측 제외 | 1 |

---

## 3. 모델 구조

```
TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95, sublinear_tf=True)
→ LogisticRegression(class_weight="balanced", solver="liblinear")
```

engagement 변수는 학습에 사용하지 않음.

---

## 4. Cross-validation 결과 (StratifiedKFold, k=5)

| 지표 | 평균 | 표준편차 |
|------|------|---------|
| accuracy | 0.6406 | 0.0376 |
| precision | 0.6355 | 0.0401 |
| recall | 0.6507 | 0.0424 |
| f1 | 0.6426 | 0.0382 |
| roc_auc | 0.7345 | 0.0296 |
| balanced_accuracy | 0.6408 | 0.0376 |

---

## 5. 오류 분석 (Out-of-fold, threshold=0.5)

| 유형 | 건수 |
|------|------|
| True Positive  | 54 |
| True Negative  | 53 |
| False Positive | 31 |
| False Negative | 29 |
| 합계 | 167 |

---

## 6. 978건 전체 예측 결과

| 지표 | 값 |
|------|-----|
| 최솟값 | 0.2262 |
| 평균 | 0.4974 |
| 중앙값 | 0.5086 |
| 최댓값 | 0.6762 |
| >= 0.5 (유머 예측) | 529건 (54.1%) |

---

## 7. 기존 점수 비교

| 상관 | 값 |
|------|-----|
| `p_humor_human168` vs `humor_score` | 0.1117 |
| `p_humor_human168` vs `p_humor_ml`  | 0.3158 |

---

## 8. Model vs Human 일치 (168건 기준)

| 결과 | 건수 |
|------|------|
| match | 167 |
| mismatch | 0 |
| 정확도 (match / 유효라벨) | 100.0% |

---

## 9. H1 단순 OLS 결과

IV: `log1p_p_humor_human168`

| 종속변수 | β | p | R² | H1 해석 |
|---|---|---|---|---|
| `log1p_engagement_total` | 6.584651 | 0.000000 | 0.045329 | H1 예비적 지지 |
| `log1p_engagement_fav_rt` | 6.745283 | 0.000000 | 0.046249 | H1 예비적 지지 |
| `log1p_favorite_count` | 7.926105 | 0.000000 | 0.047097 | H1 예비적 지지 |
| `log1p_retweet_count` | 4.873144 | 0.000001 | 0.023651 | H1 예비적 지지 |
| `log1p_reply_count` | 5.683608 | 0.000000 | 0.037861 | H1 예비적 지지 |
| `log1p_quote_count` | 3.078443 | 0.003421 | 0.008745 | H1 예비적 지지 |
| `log1p_bookmark_count` | 2.667627 | 0.006344 | 0.007608 | H1 예비적 지지 |


주요 결과 (`log1p_engagement_total`):
β = 6.584651, SE = 0.967271, p = 0.0000, R² = 0.045329

**H1 예비적 지지**

---

## 10. 한계

- 168건 human-coded sample 기반 — exploratory calibration
- 단일 코더, inter-rater reliability 미검증
- 통제변수 없음 — 관측적 연관성 분석
