# Wendy's 전체표본 4-type 예측값 기반 H2 확인 결과

## 1. 작업 목적

본 분석은 전체 978건에 대한 모델 기반 4-type 예측값을 사용한 exploratory supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

H2: Wendy's 브랜드 게시글에서 aggressive humor는 다른 유머 유형보다 post-level engagement가 더 높을 것이다.

본 분석은 다음 위치에 해당한다:

| 위계 | 분석 | 위상 |
|---|---|---|
| 1 | human-labeled H2 | primary evidence |
| 2 | model-based aggressive vs other_humor H2 | supplemental evidence |
| 3 | human-labeled 4-type decomposition | exploratory decomposition |
| 4 | full-sample 4-type prediction H2 | exploratory supplemental evidence |

---

## 2. 사용 데이터

- `wendys_full_sample_four_type_humor_predictions.csv`: 전체 978건 4-type 예측값
- `wendys_fast_weak_supervised_humor_dataset.csv`: engagement 원자료

병합 기준: `id` (978건 완전 매칭)

---

## 3. 분석 표본 구성

| 표본 | 기준 | n |
|---|---|---|
| Full sample | 전체 | 978 |
| Predicted humor sample | pred_full_4type ≠ non_humor | 564 |
| Predicted non-humor | pred_full_4type = non_humor | 414 |

---

## 4. 전체표본 4-type 예측 분포

pred_full_4type_humor_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 4-type 라벨 278건을 학습한 모델 기반 예측값이다.

| 예측 type | n | 전체 비율 | 유머 내 비율 |
|---|---|---|---|
| non_humor | 414 | 42.3% | — |
| aggressive | 187 | 19.1% | 33.2% |
| affiliative | 251 | 25.7% | 44.5% |
| self-enhancing | 96 | 9.8% | 17.0% |
| self-defeating | 30 | 3.1% | 5.3% |

---

## 5. Type별 평균 engagement (log1p_engagement_total)

| 예측 type | n | 평균 |
|---|---|---|
| aggressive | 187 | 7.9424 |
| affiliative | 251 | 7.33 |
| self-enhancing | 96 | 7.6327 |
| self-defeating | 30 | 8.1047 |
| non_humor | 414 | 7.125 |

---

## 6. Pooled H2: aggressive vs pooled other_humor

검정: Welch's independent samples t-test (two-sided, equal_var=False)

표본: predicted humor sample (n=564; aggressive=187, pooled_other=377)

**주요 DV: log1p_engagement_total**

| 항목 | 값 |
|---|---|
| mean_aggressive | 7.9424 |
| mean_pooled_other | 7.4687 |
| diff (agg - other) | 0.4737 |
| t-stat | 2.9444 |
| p-value | 0.0035 |
| Cohen's d | 0.2747 |
| 효과 크기 | small |
| H2 방향 | H2방향 |
| 판정 | 예비적지지(p<.05) |

보조 DV 요약 (방향성):

| DV | diff | p-value | 판정 |
|---|---|---|---|
| log1p_engagement_total | 0.4737 | 0.0035 | 예비적지지(p<.05) |
| log1p_engagement_favorite_retweet | 0.4864 | 0.0031 | 예비적지지(p<.05) |
| log1p_favorite_count | 0.5876 | 0.0008 | 예비적지지(p<.05) |
| log1p_retweet_count | 0.4533 | 0.0093 | 예비적지지(p<.05) |
| log1p_reply_count | 0.1939 | 0.1887 | 방향성만지지 |
| log1p_quote_count | 0.3728 | 0.0356 | 예비적지지(p<.05) |
| log1p_bookmark_count | 0.5289 | 0.0005 | 예비적지지(p<.05) |
| log1p_view_count | 1.4661 | 0.0044 | 예비적지지(p<.05) |

---

## 7. Humor-only OLS 결과

표본: predicted humor sample (n=564)

식: log1p_engagement_total = α + β × (aggressive vs pooled_other)

| DV | coef | se | t | p | R² | 판정 |
|---|---|---|---|---|---|---|
| log1p_engagement_total | 0.4737 | 0.1543 | 3.0707 | 0.0022 | 0.0165 | 예비적지지(p<.05) |
| log1p_engagement_favorite_retweet | 0.4864 | 0.1565 | 3.109 | 0.002 | 0.0169 | 예비적지지(p<.05) |
| log1p_favorite_count | 0.5876 | 0.174 | 3.3776 | 0.0008 | 0.0199 | 예비적지지(p<.05) |
| log1p_retweet_count | 0.4533 | 0.1644 | 2.7568 | 0.006 | 0.0133 | 예비적지지(p<.05) |
| log1p_reply_count | 0.1939 | 0.1442 | 1.3449 | 0.1792 | 0.0032 | 방향성만지지 |
| log1p_quote_count | 0.3728 | 0.1679 | 2.2197 | 0.0268 | 0.0087 | 예비적지지(p<.05) |
| log1p_bookmark_count | 0.5289 | 0.1476 | 3.5834 | 0.0004 | 0.0223 | 예비적지지(p<.05) |
| log1p_view_count | 1.4661 | 0.4878 | 3.0053 | 0.0028 | 0.0158 | 예비적지지(p<.05) |

---

## 8. Full sample multi-dummy OLS 결과

표본: 전체 978건. 기준범주: non_humor

식: log1p_engagement_total = α + β₁×aggressive + β₂×affiliative + β₃×self-enhancing + β₄×self-defeating

**주요 DV: log1p_engagement_total**

| 비교 | coefficient | p-value |
|---|---|---|
| aggressive vs non_humor | 0.8174 | 0.0 |
| affiliative vs non_humor | 0.205 | 0.1401 |
| self-enhancing vs non_humor | 0.5077 | 0.0099 |
| self-defeating vs non_humor | 0.9798 | 0.0029 |

**Linear contrasts (Wald test)**

| contrast | 추정 diff | p-value |
|---|---|---|
| aggressive − affiliative | 0.6124 | 0.0003 |
| aggressive − self-enhancing | 0.3096 | 0.1556 |
| aggressive − self-defeating | -0.1624 | 0.6344 |
| aggressive − pooled_other | 0.4737 | 0.0023 |

---

## 9. Aggressive vs 각 type pairwise 비교

검정: Welch's t-test. 보정: Bonferroni, FDR(BH). 표본: predicted humor sample.

**주요 DV: log1p_engagement_total**

| 비교 | n_agg | n_비교 | diff | p_raw | p_bonf | p_fdr | d | 판정 | 소표본경고 |
|---|---|---|---|---|---|---|---|---|---|
| aggressive vs affiliative | 187 | 251 | 0.6124 | 0.0005 | 0.0014 | 0.0014 | 0.3462 | 예비적지지(p<.05) | False |
| aggressive vs self-enhancing | 187 | 96 | 0.3096 | 0.122 | 0.3659 | 0.1829 | 0.1789 | 방향성만지지 | False |
| aggressive vs self-defeating | 187 | 30 | -0.1624 | 0.6517 | 1.0 | 0.6517 | -0.0873 | H2불지지 | False |

self-defeating 학습 표본은 15건으로 매우 작았기 때문에, self-defeating 관련 결과는 특히 제한적으로 해석해야 한다.

---

## 10. Probability robustness 결과

표본: predicted humor sample (n=564). 보조 분석.

**주요 DV: log1p_engagement_total**

| predictor | coef | t | p | R² |
|---|---|---|---|---|
| p_4type_aggressive_model | 2.7427 | 3.925 | 0.0001 | 0.0267 |
| p_4type_aggressive_margin | 1.2094 | 3.2805 | 0.0011 | 0.0188 |

해석: aggressive 확률 자체 및 타 유형 대비 확률 마진으로도 동일 방향성을 확인하는 보조적 robustness check.
probability robustness는 보조 분석이므로 binary predicted type 결과보다 약하게 해석해야 한다.

---

## 11. 기존 H2 결과들과의 관계

| 위계 | 분석 | 결과 요약 |
|---|---|---|
| primary | human-labeled H2 (사람 라벨 597건) | diff=+0.707, p=0.0012**, d=0.44 |
| supplemental | model-based aggressive vs other_humor (전체 978건) | diff=+0.468, p=0.0029**, d=0.27 |
| exploratory decomposition | human-labeled 4-type (278건) | ANOVA p=0.0036**, aggressive > affiliative(p_fdr=0.010*) |
| exploratory supplemental | full-sample 4-type prediction H2 (본 분석) | pooled diff=0.4737, p=0.0035, d=0.2747 |

---

## 12. 해석상 주의사항

4-type classifier의 OOF 성능은 accuracy 0.4281, macro-F1 0.3486으로 제한적이므로, 전체표본 4-type H2 결과는 탐색적으로 해석해야 한다.

engagement 변수는 4-type classifier의 feature로 사용되지 않았지만, 본 H2 분석은 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.

self-defeating 학습 표본은 15건으로 매우 작았기 때문에, self-defeating 관련 결과는 특히 제한적으로 해석해야 한다.

pred_full_4type_humor_model은 확정 사람 코딩 라벨이 아니라, 사람 기반 4-type 라벨 278건을 학습한 모델 기반 예측값이다.

본 분석은 전체 978건에 대한 모델 기반 4-type 예측값을 사용한 exploratory supplemental H2 분석이며, 기존 사람 라벨 기반 H2를 대체하지 않는다.

**허용 해석 표현:**
- 전체표본 4-type 예측값 기반 exploratory supplemental H2 분석에서도 aggressive로 예측된 게시글이 pooled other_humor보다 engagement가 높게 나타나는지 확인하였다.
- 본 결과는 기존 human-labeled H2를 대체하지 않고 보조하는 탐색적 증거이다.
- 4-type classifier 성능과 self-defeating 소표본 문제를 고려하여 제한적으로 해석해야 한다.

---

## 13. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 분석 대상 파일은 읽기 전용으로만 사용
- 기존 결과 파일 수정 없음

---

*생성일: 2026-06-15*
