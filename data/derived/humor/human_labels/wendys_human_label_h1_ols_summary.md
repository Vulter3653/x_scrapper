# Wendy's 사람 코딩 레이블 기반 H1 단순 OLS 분석

생성일시: 2026-06-15 12:39 UTC

---

## 1. 작업 목적

`data/derived/humor/human_labels/wendys_human_label_raw_linked.csv`에 저장된
사람이 직접 코딩한 유머 레이블(`human_humor_binary`)을 IV로 사용하여
Wendy's 게시글 수준 engagement와의 연관성을 탐색적으로 검토한다.

이 분석은 기존 rule-based `humor_score` 및 weak-supervised `p_humor_ml`과 달리,
**사람이 직접 판단한 이진 레이블**을 IV로 사용한다는 점에서 구별된다.

> **중요:** 이 표본은 Wendy's partial human review sample(68건)이며,
> 전체 978건 게시글에 대한 gold label이 아니다.

---

## 2. 표본 구성

| 항목 | 값 |
|------|-----|
| 전체 linked 행 수 | 69건 |
| label 결측 제외 | 1건 |
| **분석 사용 행 수** | **68건** |
| 유머(human_humor_binary = 1) | 37건 (54.4%) |
| 비유머(human_humor_binary = 0) | 31건 (45.6%) |

---

## 3. IV 정의

```
human_humor_binary
  = 1  유머 ('humor')
  = 0  비유머 ('non_humor' 또는 'none')
  제외  공란(label_missing_flag = true)
```

`human_humor_binary`는 연속형 확률값이 아닌 이진 더미 변수이다.
따라서 β는 유머 게시글과 비유머 게시글 간의 log1p engagement 차이를 나타낸다.

---

## 4. 회귀식

```
log1p_DV_i = α + β × human_humor_binary_i + ε_i
```

각 항의 의미:
- `i` : 개별 Wendy's 게시글
- `log1p_DV_i` : engagement 지표의 log(1+x) 변환값
- `human_humor_binary_i` : 사람이 코딩한 유머 더미 (1=유머, 0=비유머)
- `β` : 유머 게시글과 비유머 게시글 간의 log1p engagement 평균 차이
- `ε_i` : 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

---

## 5. 그룹별 평균 비교

| 종속변수 | 유머(1) 평균 | 비유머(0) 평균 | 차이 |
|---|---|---|---|
| `log1p_engagement_total` | 8.9855 | 7.9210 | +1.0645 |
| `log1p_engagement_fav_rt` | 8.8873 | 7.8277 | +1.0596 |
| `log1p_favorite_count` | 8.8166 | 7.7606 | +1.0559 |
| `log1p_retweet_count` | 6.0698 | 4.9670 | +1.1028 |
| `log1p_reply_count` | 5.5801 | 4.9012 | +0.6789 |
| `log1p_quote_count` | 3.9628 | 3.2688 | +0.6940 |
| `log1p_bookmark_count` | 3.1957 | 2.2209 | +0.9748 |


---

## 6. 단순 OLS 결과

| 종속변수 (DV) | β | SE | p-value | R² | H1 해석 |
|---|---|---|---|---|---|
| `log1p_engagement_total` | 1.064493 | 0.375654 | 0.006098 | 0.108468 | H1 예비적 지지 |
| `log1p_engagement_fav_rt` | 1.059604 | 0.379211 | 0.006803 | 0.105785 | H1 예비적 지지 |
| `log1p_favorite_count` | 1.055943 | 0.377192 | 0.006705 | 0.106140 | H1 예비적 지지 |
| `log1p_retweet_count` | 1.102799 | 0.421010 | 0.010917 | 0.094170 | H1 예비적 지지 |
| `log1p_reply_count` | 0.678854 | 0.365660 | 0.067844 | 0.049630 | H1 방향성 지지 |
| `log1p_quote_count` | 0.694019 | 0.522647 | 0.188788 | 0.026021 | H1 방향성 지지 |
| `log1p_bookmark_count` | 0.974798 | 0.405198 | 0.018950 | 0.080621 | H1 예비적 지지 |


주요 결과 (`log1p_engagement_total`):

| 파라미터 | 값 |
|----------|-----|
| n_obs | 68 |
| Intercept (α) | 7.921033 |
| β (`human_humor_binary`) | 1.064493 |
| Standard Error | 0.375654 |
| t-value | 2.8337 |
| p-value | 0.0061 |
| 95% CI | [8.474278, 1.814510] |
| R² | 0.108468 |
| Adj. R² | 0.094960 |
| **H1 해석** | **H1 예비적 지지** |

---

## 7. H1 해석

`human_humor_binary`는 `log1p_engagement_total`과
**양의 방향**을 보였다.
(β = 1.064493, SE = 0.375654, p = 0.0061, R² = 0.108468)

**H1 예비적 지지**

---

## 8. 한계

- 이 분석은 Wendy's partial human review sample(68건)에 국한된다.
  전체 978건에 대한 human label이 아니므로 결과를 일반화할 수 없다.
- 표본이 `review_priority`(false_negative_candidate, high_confidence_humor 등)
  기준으로 선발되었으므로 무작위 표본이 아니다. 선택 편의(selection bias)가 존재한다.
- 단순 OLS이므로 통제변수(게시 시점, 미디어 유형, 캠페인 등)를 포함하지 않는다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- `human_humor_binary`는 단일 코더의 판단이며 inter-rater reliability 미검증 상태이다.
