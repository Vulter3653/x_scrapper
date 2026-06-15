# Wendy's H3-main 준비: Aggressive Humor vs Other Humor Intensity Audit

## 1. 작업 목적

본 작업은 H3-main 회귀분석이 아니라, aggressive humor와 other humor를 분리한 intensity 변수화 및 사전 audit이다.

이번 작업에서는 다음을 수행하였다.

- aggressive humor와 other humor의 quarter-level frequency/proportion 변수 생성
- leave-one-out(LOO) proportion 변수 생성
- sparse quarter 제외 후 filtered audit 수행
- 각 predictor에 대한 post-level 분포 확인
- low / medium / high tertile bin별 descriptive engagement pattern 확인

H3-main 회귀분석은 이 문서에서 수행하지 않았다.

---

## 2. 사용 데이터

| 파일 | 역할 |
|---|---|
| `wendys_model_based_humor_type_full_predictions.csv` | aggressive/other_humor 타입 예측값 |
| `wendys_humor_frequency_proportion_post_level_dataset.csv` | post-level engagement 및 quarter 변수 |

두 파일은 `id` 기준으로 병합하였다. 병합 결과: 978건.

---

## 3. Aggressive Humor / Other Humor 분류 기준

aggressive humor와 other humor의 구분은 전체 978건에 대한 확정 사람 코딩 결과가 아니라 모델 기반 타입 예측값인 pred_humor_type_group_model을 사용하였다.

| pred_humor_type_group_model | 정의 | n |
|---|---|---|
| `aggressive` | aggressive humor | 200 |
| `other_humor` | affiliative/self-enhancing/self-defeating humor | 364 |
| `non_humor` | 비유머 | 414 |
| 합계 | | 978 |

이 모델은 사람 기반 타입 라벨 278건을 학습한 supplemental model-based prediction이므로, 분류 오류가 포함될 수 있다.

---

## 4. 생성 변수 정의

### 4.1 Aggressive Humor Frequency

```
aggressive_humor_frequency_quarter = quarter 내 aggressive humor 게시글 수
```

### 4.2 Aggressive Humor Proportion

```
aggressive_humor_proportion_quarter = Aggressive Posts_q / Total Posts_q
```

### 4.3 Aggressive Share Among Humor

```
aggressive_share_among_humor_quarter = Aggressive Posts_q / Humor Posts_q
(Humor Posts_q = 0이면 missing)
```

### 4.4 Aggressive Humor Proportion LOO

```
aggressive_humor_proportion_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Total Posts_q - 1)
```

post i 자신을 제외한 동일 분기 내 aggressive 비중. H3-main 회귀 primary predictor 후보.

### 4.5 Aggressive Share Among Humor LOO

```
aggressive_share_among_humor_quarter_loo_i
= (Aggressive Posts_q - Aggressive_i) / (Humor Posts_q - Humor_i)
(분모 = 0이면 missing)
```

### 4.6 Other Humor Proportion LOO

```
other_humor_proportion_quarter_loo_i
= (Other Humor Posts_q - Other_i) / (Total Posts_q - 1)
```

---

## 5. 분석 표본 및 필터 기준

| 항목 | 값 |
|---|---|
| 전체 posts | 978 |
| 전체 quarters | 28 |
| 필터 기준 | quarter_total_posts ≥ 10 |
| **Filtered posts** | **960** |
| **Filtered quarters** | **25** |
| 제외 posts | 18 |
| 제외 quarters | 2009-Q4, 2023-Q4, 2025-Q3 |

---

## 6. Quarter-level 분포

`wendys_h3_aggressive_vs_other_quarter_audit.csv` 참조. (25개 분기)

---

## 7. Aggressive Humor Proportion LOO 분포

filtered sample (n=960) 기준:

| 항목 | 값 |
|---|---|
| min | 0.0 |
| max | 0.337662 |
| mean | 0.20625 |
| sd | 0.070264 |
| missing | 0 |

다음 단계에서 H3-main 회귀분석을 수행할 경우, post i를 제외한 aggressive_humor_proportion_quarter_loo를 primary predictor로 사용할 수 있다.

---

## 8. Other Humor Proportion LOO 분포

| 항목 | 값 |
|---|---|
| min | 0.0 |
| max | 0.666667 |
| mean | 0.373958 |
| sd | 0.155747 |
| missing | 0 |

---

## 9. Aggressive Share Among Humor LOO 분포

| 항목 | 값 |
|---|---|
| min | 0.0 |
| max | 1.0 |
| mean | 0.374577 |
| sd | 0.165106 |
| missing | 0 |

---

## 10. Bin별 Descriptive Engagement Pattern

engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.

### aggressive_humor_proportion_quarter_loo (primary 후보)

| bin | n_posts | n_quarters | mean_predictor | mean_engagement |
|---|---|---|---|---|
| low | 337 | 14 | 0.137728 | 7.333679 |
| medium | 304 | 12 | 0.197558 | 7.602834 |
| high | 319 | 11 | 0.286922 | 7.291956 |

descriptive pattern: inverted_U (low<medium>high)

### aggressive_humor_frequency_quarter

| bin | n_posts | n_quarters | mean_predictor | mean_engagement |
|---|---|---|---|---|
| low | 437 | 16 | 5.837529 | 7.478356 |
| medium | 254 | 5 | 9.358268 | 7.458511 |
| high | 269 | 4 | 19.739777 | 7.235472 |

descriptive pattern: monotone_decrease

### aggressive_share_among_humor_quarter_loo

| bin | n_posts | n_quarters | mean_predictor | mean_engagement |
|---|---|---|---|---|
| low | 327 | 9 | 0.220342 | 7.258999 |
| medium | 336 | 11 | 0.344876 | 7.667723 |
| high | 297 | 12 | 0.577991 | 7.268679 |

descriptive pattern: inverted_U (low<medium>high)

### other_humor_proportion_quarter_loo

| bin | n_posts | n_quarters | mean_predictor | mean_engagement |
|---|---|---|---|---|
| low | 341 | 15 | 0.204498 | 7.253292 |
| medium | 322 | 8 | 0.38846 | 7.548062 |
| high | 297 | 6 | 0.552801 | 7.424231 |

descriptive pattern: inverted_U (low<medium>high)

---

## 11. H3-main 회귀분석 가능성 판단

H3-main 회귀분석은 본 작업에서 수행하지 않았다. 다음 단계에서 수행 가능 여부를 판단하려면 아래 조건을 확인하라.

| 확인 항목 | 값 |
|---|---|
| filtered quarters | 25개 |
| aggressive_proportion_loo missing | 0 |
| aggressive_proportion_loo range | [0.0, 0.337662] |
| descriptive pattern (aggressive_loo) | inverted_U (low<medium>high) |
| H3-main 회귀 수행 여부 | False |

---

## 12. 이전 H3-pre 결과와의 관계

이전 H3-pre 분석에서 general Proportion of Humor의 역 U자형 관계는 primary quadratic OLS 기준으로 지지되지 않았으므로, 본 aggressive intensity 분석은 exploratory H3-main으로 제한하여 해석해야 한다.

따라서 이후 H3-main 회귀분석에서 유의미한 역 U자형 패턴이 발견되더라도, 이는 사전에 기각된 일반 유머 비중 가설의 사후 탐색적 보완으로만 해석해야 한다.

---

## 13. 해석상 주의사항

1. aggressive humor와 other humor의 구분 기준은 모델 기반 예측값이므로 분류 오류가 포함될 수 있다.
2. aggressive_humor_proportion_quarter_loo는 같은 quarter 내 게시글이 동일한 값을 공유하므로, 추후 회귀에서 cluster-robust SE 적용을 고려해야 한다.
3. quarter fixed effects는 humor_proportion_quarter_loo 계열 변수와 동시에 사용할 경우 식별이 불가능하다.
4. 본 관찰적 연구에서 aggressive humor와 engagement 사이의 연관성은 인과관계를 의미하지 않는다.
5. H3-pre의 general proportion이 불지지였기 때문에 H3-main aggressive 분석은 exploratory H3-main으로 위치시켜야 하며, 이 점을 보고 시 명시해야 한다.

---

## 14. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/H3-pre 파일 수정 없음

---

*생성일: 2026-06-15*
