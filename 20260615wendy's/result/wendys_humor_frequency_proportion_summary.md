# Wendy's Frequency of Humor / Proportion of Humor 변수화 결과

## 1. 작업 목적

본 작업은 H3 회귀분석이 아니라, H3 분석에 사용할 Frequency of Humor와 Proportion of Humor 변수를 명시적으로 생성하는 변수화 작업이다.

Frequency of Humor는 기간 내 유머 게시글 수이며, Proportion of Humor는 기간 내 전체 SNS 게시글 중 유머 게시글의 비율이다.

---

## 2. 사용 데이터

- `wendys_simple_humor_intensity_post_level_dataset.csv`: 기존 post-level 데이터 (978행)
- `wendys_simple_humor_intensity_monthly_audit.csv`: 기존 월별 period 집계
- `wendys_simple_humor_intensity_quarterly_audit.csv`: 기존 분기별 period 집계

---

## 3. 유머 유무 기준

pred_humor_final_050은 모델 기반 유머 유무 예측값이므로, Frequency와 Proportion 역시 확정 사람 코딩값이 아니라 모델 기반 분류값을 바탕으로 계산된 변수이다.

| 항목 | n |
|---|---|
| 전체 post | 978 |
| predicted humor (pred=1) | 564 |
| predicted non_humor (pred=0) | 414 |
| missing | 0 |

---

## 4. Frequency of Humor 변수 정의

Frequency of Humor는 특정 기간 내 유머 게시글의 절대 개수이다.

```
humor_frequency_month   = 해당 월의 pred_humor_final_050 = 1인 게시글 수
humor_frequency_quarter = 해당 분기의 pred_humor_final_050 = 1인 게시글 수
```

Frequency 변수는 게시물 총량(활동 수준)의 영향을 받는다.
따라서 H3 주 분석에서는 Proportion 변수를 우선하되, Frequency는 보조 변수로 활용한다.

---

## 5. Proportion of Humor 변수 정의

Proportion of Humor는 특정 기간 내 전체 SNS 게시글 중 유머 게시글이 차지하는 비율이다.

```
humor_proportion_month   = humor_frequency_month   / month_total_posts
humor_proportion_quarter = humor_frequency_quarter / quarter_total_posts
```

Proportion of Humor는 기존 humor_intensity와 동일한 값이며, 본 작업에서는 이론적 해석을 명확히 하기 위해 변수명을 분리하였다.

---

## 6. Leave-one-out Proportion 변수 정의

```
humor_proportion_month_loo   = (month_humor_posts - pred_humor_final_050_i)   / (month_total_posts - 1)
humor_proportion_quarter_loo = (quarter_humor_posts - pred_humor_final_050_i) / (quarter_total_posts - 1)
```

- month LOO missing (period n=1): 3건
- quarter LOO missing (period n=1): 1건

---

## 7. 월별 변수 분포

| 항목 | Frequency (count) | Proportion (rate) |
|---|---|---|
| 최솟값 | 0.0 | 0.0 |
| 최댓값 | 37.0 | 1.0 |
| 평균 | 12.4693 | 0.5767 |
| 표준편차 | 9.6138 | 0.189 |

월별 period 수: 80개 (total_posts: min=1.0, max=50.0)

---

## 8. 분기별 변수 분포

| 항목 | Frequency (count) | Proportion (rate) |
|---|---|---|
| 최솟값 | 1.0 | 0.2 |
| 최댓값 | 78.0 | 1.0 |
| 평균 | 31.3804 | 0.5767 |
| 표준편차 | 21.1122 | 0.1544 |

분기별 period 수: 28개 (total_posts: min=1.0, max=110.0)

---

## 9. 기존 humor_intensity 변수와의 일치 검증

| 검증 항목 | 결과 |
|---|---|
| humor_proportion_month == humor_intensity_month | PASS ✓ |
| humor_proportion_quarter == humor_intensity_quarter | PASS ✓ |
| humor_proportion_month_loo == humor_intensity_month_loo | PASS ✓ |
| humor_proportion_quarter_loo == humor_intensity_quarter_loo | PASS ✓ |

허용 오차: |diff| ≤ 1e-06

---

## 10. H3 분석에서의 사용 방향

| 변수 | H3 역할 | 우선순위 |
|---|---|---|
| humor_proportion_quarter_loo | H3 primary predictor 후보 | 1순위 |
| humor_proportion_month_loo | H3 보조 predictor | 2순위 |
| humor_proportion_quarter | LOO 대안 (표본 안정성) | 보조 |
| humor_frequency_quarter | 보조 변수 (절대 개수 기반) | 보조 |
| humor_frequency_month | 보조 변수 (절대 개수, 월별) | 보조 |

H3 회귀분석에서는 게시글 자기 자신이 기간 비중 계산에 포함되는 문제를 줄이기 위해 leave-one-out proportion 변수를 우선적으로 사용할 수 있다.

---

## 11. 해석상 주의사항

- 본 작업은 변수화 작업이며 H3 회귀분석은 수행하지 않았다.
- 인과관계를 주장하지 않는다. Frequency와 Proportion은 기술통계적 기간 집계 변수이다.
- pred_humor_final_050은 모델 기반 예측이므로 분류 오류가 포함되어 있다.
- 2009-11 (n=1) 등 극소 period는 Proportion을 불안정하게 만든다. 이후 H3 분석 시 이상치 period 처리 방안을 별도 결정해야 한다.
- Frequency는 총 게시량 변화의 영향을 받으므로 Proportion과 함께 해석해야 한다.

---

## 12. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/intensity 파일 수정 없음

---

*생성일: 2026-06-15*
