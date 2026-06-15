# Wendy's H3-pre Filtered Quarter Audit 결과

## 1. 작업 목적

본 작업은 H3 회귀분석을 수행하기 전에, sparse period를 제외한 filtered sample에서 humor usage 변수의 분포와 descriptive engagement pattern을 확인하는 사전 점검이다.

H3 회귀분석은 본 단계에서 수행하지 않는다.

---

## 2. 필터 기준

```
quarter_total_posts >= 10
```

제외된 분기 (total_posts < 10):

| 분기 | 제외 이유 | n_posts |
|---|---|---|
| 2009-Q4 | total_posts=1 (이상치 period) | 1 |
| 2023-Q4 | total_posts=8 (sparse) | 8 |
| 2025-Q3 | total_posts=9 (sparse) | 9 |

---

## 3. 표본 구성 (필터 후)

| 항목 | 값 |
|---|---|
| 전체 posts (필터 전) | 978 |
| 제외 posts | 18 |
| **filtered posts** | **960** |
| **filtered 분기** | **25개** |
| predicted humor (pred=1) | 557 (58.0%) |
| predicted non_humor (pred=0) | 403 (42.0%) |
| LOO proportion missing | 0 |

---

## 4. humor_proportion_quarter_loo 분포

### Post-level 기준 (n=960)

| 항목 | 값 |
|---|---|
| min | 0.1579 |
| max | 0.9167 |
| mean | 0.5802 |
| sd | 0.153 |
| median | 0.6182 |
| P25 | 0.4815 |
| P75 | 0.6623 |

Tertile 기준: T33=0.5185, T67=0.6562

### Period-level 기준 (n=25분기)

| 항목 | 값 |
|---|---|
| min | 0.2 |
| max | 0.88 |
| mean | 0.5328 |
| sd | 0.1781 |

---

## 5. humor_frequency_quarter 분포

### Post-level 기준 (n=960)

| 항목 | 값 |
|---|---|
| min | 3.0 |
| max | 78.0 |
| mean | 31.9146 |
| sd | 20.9419 |
| median | 28.0 |

Tertile 기준: T33=19.0, T67=35.0

### Period-level 기준 (n=25분기)

| 항목 | 값 |
|---|---|
| min | 3 |
| max | 78 |
| mean | 22.28 |
| sd | 17.4607 |

---

## 6. Bin별 descriptive engagement pattern

H3-pre 기대 패턴: **low < medium > high** (역 U자형)
아래 결과는 descriptive audit 목적으로만 제시하며, 통계적 유의성을 해석하지 않는다.

### humor_proportion_quarter_loo 기준

| bin | n_posts | n_periods | mean_predictor | mean_log1p_engagement_total | median_log1p_engagement_total |
|---|---|---|---|---|---|
| low | 332 | 13 | 0.4006 | 7.2985 | 7.1468 |
| medium | 335 | 8 | 0.6249 | 7.6837 | 7.6788 |
| high | 293 | 7 | 0.7326 | 7.2073 | 7.224 |

패턴 판정 (descriptive only): **inverted_U (low<medium>high)**

### humor_frequency_quarter 기준

| bin | n_posts | n_periods | mean_predictor | mean_log1p_engagement_total | median_log1p_engagement_total |
|---|---|---|---|---|---|
| low | 345 | 14 | 12.458 | 7.3029 | 7.216 |
| medium | 319 | 7 | 29.5893 | 7.6015 | 7.4911 |
| high | 296 | 4 | 57.098 | 7.3124 | 7.236 |

패턴 판정 (descriptive only): **inverted_U (low<medium>high)**

### humor_proportion_quarter 기준 (보조)

| bin | n_posts | n_periods | mean_predictor | mean_log1p_engagement_total | median_log1p_engagement_total |
|---|---|---|---|---|---|
| low | 326 | 12 | 0.3988 | 7.3112 | 7.1511 |
| medium | 325 | 7 | 0.6215 | 7.5705 | 7.4894 |
| high | 309 | 6 | 0.7282 | 7.33 | 7.3556 |

---

## 7. 포함된 분기 목록 (25개)

| 분기 | total_posts | humor_frequency | humor_proportion | mean_loo_proportion | mean_engagement |
|---|---|---|---|---|---|
| 2019-Q4 | 28 | 14 | 0.5 | 0.5 | 8.0283 |
| 2020-Q1 | 50 | 32 | 0.64 | 0.64 | 9.0855 |
| 2020-Q2 | 110 | 78 | 0.709091 | 0.709091 | 7.0126 |
| 2020-Q3 | 65 | 43 | 0.661538 | 0.661538 | 7.6371 |
| 2020-Q4 | 56 | 35 | 0.625 | 0.625 | 7.8386 |
| 2021-Q1 | 78 | 51 | 0.653846 | 0.653847 | 7.5882 |
| 2021-Q2 | 48 | 24 | 0.5 | 0.5 | 7.7101 |
| 2021-Q3 | 43 | 36 | 0.837209 | 0.837209 | 7.0883 |
| 2021-Q4 | 25 | 22 | 0.88 | 0.88 | 8.3284 |
| 2022-Q1 | 42 | 28 | 0.666667 | 0.666667 | 7.0939 |
| 2022-Q2 | 24 | 18 | 0.75 | 0.75 | 7.7597 |
| 2022-Q3 | 39 | 24 | 0.615385 | 0.615385 | 7.311 |
| 2022-Q4 | 32 | 19 | 0.59375 | 0.59375 | 7.6756 |
| 2023-Q1 | 19 | 9 | 0.473684 | 0.473684 | 8.3629 |
| 2023-Q2 | 32 | 11 | 0.34375 | 0.34375 | 6.7563 |
| 2023-Q3 | 12 | 3 | 0.25 | 0.25 | 7.2599 |
| 2024-Q1 | 18 | 7 | 0.388889 | 0.388889 | 7.278 |
| 2024-Q2 | 27 | 10 | 0.37037 | 0.37037 | 7.1685 |
| 2024-Q3 | 41 | 18 | 0.439024 | 0.439024 | 6.3626 |
| 2024-Q4 | 20 | 4 | 0.2 | 0.2 | 7.7059 |
| 2025-Q1 | 21 | 9 | 0.428571 | 0.428571 | 7.1793 |
| 2025-Q2 | 14 | 4 | 0.285714 | 0.285714 | 8.3338 |
| 2025-Q4 | 11 | 6 | 0.545455 | 0.545455 | 6.7529 |
| 2026-Q1 | 46 | 17 | 0.369565 | 0.369566 | 6.9429 |
| 2026-Q2 | 59 | 35 | 0.59322 | 0.59322 | 6.2758 |

---

## 8. H3 회귀분석 준비 상태

| 항목 | 상태 |
|---|---|
| H3 primary predictor | `humor_proportion_quarter_loo` |
| Filtered sample | 960건, 25분기 |
| LOO missing in filtered sample | 0건 |
| Descriptive pattern (LOO proportion) | inverted_U (low<medium>high) |
| H3 회귀분석 수행 여부 | 미수행 |

---

## 9. 해석상 주의사항

- 본 결과는 descriptive audit이며, H3 가설 지지 여부를 판정하지 않는다.
- humor_proportion_quarter_loo는 모델 기반 pred_humor_final_050을 사용하여 계산한 값이며, 확정 사람 코딩 결과가 아니다.
- engagement 평균은 기술통계 목적으로만 제시되었으며, 인과관계나 통계적 유의성을 해석하지 않는다.
- 두 집계 기준(post-level vs period-level)의 평균값 차이는 집계 단위 차이에서 발생한 것이며, 변수 생성 오류가 아니다.
- 이후 H3 회귀분석에서는 quadratic term(humor_proportion_quarter_loo²)을 포함한 OLS를 수행할 수 있다.

---

## 10. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/intensity/proportion 파일 수정 없음

---

*생성일: 2026-06-15*
