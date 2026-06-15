# Wendy's 단순 Humor Usage Intensity 사전 점검 결과

## 1. 작업 목적

본 작업은 H3 회귀분석이 아니라, 단순 humor usage intensity의 기간별 분포와 변동성을 확인하기 위한 사전 점검이다.

H3-pre 아이디어:

```
H3-pre: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형 관계를 가질 것이다.
```

이번 단계에서는 위 가설을 검정하지 않는다.
이 사전 점검의 목적은 다음이다:

1. 월별/분기별 humor intensity가 충분히 변동하는지 확인
2. 어느 기간 단위(month vs quarter)가 이후 H3-pre 분석에 적합한지 판단
3. Leave-one-out intensity 변수 생성

---

## 2. 사용 데이터

- `wendys_final_humor_presence_full_predictions.csv`: 전체 978건 유머 유무 예측값
- `wendys_fast_weak_supervised_humor_dataset.csv`: engagement 원자료

병합 기준: `id` (978건 완전 매칭)

---

## 3. 유머 유무 기준

humor_intensity는 모델 기반 유머 유무 예측값인 pred_humor_final_050을 사용해 계산되었으며, 전체 게시글에 대한 확정 사람 코딩 결과가 아니다.

```
pred_humor_final_050 = 1 → model-predicted humor
pred_humor_final_050 = 0 → model-predicted non_humor
```

- predicted humor: 564건 (57.7%)
- predicted non_humor: 414건 (42.3%)
- missing: 0건

보조 확률 변수 `p_humor_final_tfidf_logreg`의 period 평균도 함께 산출하였다.

---

## 4. 월별 humor intensity 분포

- 총 월별 period: **80개**
- period별 total_posts: min=1, median=9.0, mean=12.22, max=50
- period별 humor_posts: min=0, max=37, mean=7.05
- humor_intensity: min=0.0000, max=1.0000, mean=0.5296, sd=0.2523
- total_posts < 10인 period 수: 41개 (전체의 51.2%)

월별 period는 게시글 수가 매우 적은 달이 다수 포함되어 있다.
총 80개 월 중 41개 월이 게시글 10건 미만이다.

---

## 5. 분기별 humor intensity 분포

- 총 분기별 period: **28개**
- period별 total_posts: min=1, median=30.0, mean=34.93, max=110
- period별 humor_posts: min=1, max=78, mean=20.14
- humor_intensity: min=0.2000, max=1.0000, mean=0.5368, sd=0.1966
- total_posts < 10인 period 수: 3개 (전체의 10.7%)

---

## 6. Leave-one-out intensity 생성 결과

post i를 제외한 leave-one-out humor intensity 변수를 생성하였다.

```
humor_intensity_month_loo = (month_humor_posts - pred_humor_final_050_i) / (month_total_posts - 1)
humor_intensity_quarter_loo = (quarter_humor_posts - pred_humor_final_050_i) / (quarter_total_posts - 1)
```

- month LOO missing (period total=1인 post): 3건
- quarter LOO missing (period total=1인 post): 1건

다음 단계에서 H3-pre 회귀분석을 수행할 경우, post i를 제외한 leave-one-out humor_intensity를 사용하는 것이 더 적절하다.

---

## 7. Intensity bin별 descriptive pattern

engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.

H3-pre 기대 패턴: **low < medium > high** (역 U자형)

### 월별 기준 bin

| bin | n_posts | n_periods | mean_intensity | mean_log1p_engagement |
|---|---|---|---|---|
| low | 204 | 27 | 0.299 | 7.3533 |
| medium | 397 | 25 | 0.5567 | 7.1781 |
| high | 377 | 28 | 0.748 | 7.6947 |

### 분기별 기준 bin

| bin | n_posts | n_periods | mean_intensity | mean_log1p_engagement |
|---|---|---|---|---|
| low | 186 | 9 | 0.3334 | 7.2717 |
| medium | 354 | 10 | 0.5452 | 7.2872 |
| high | 438 | 9 | 0.7055 | 7.5764 |

(descriptive pattern only — H3 지지 여부 미판정)

---

## 8. H3-pre 분석 단위 추천

| 기준 | month | quarter |
|---|---|---|
| period 수 | 80 | 28 |
| total_posts 최솟값 | 1 | 1 |
| total_posts 중앙값 | 9.0 | 30.0 |
| intensity sd | 0.2523 | 0.1966 |
| sparse period (<10 posts) 비율 | 51.2% | 10.7% |

**추천 단위: `insufficient`**

월별 period의 게시글 수가 지나치게 작거나 sparse하면 quarter 기준이 더 안정적이다.
반대로 월별 period 수와 post 수가 충분하면 month 기준이 더 세밀한 intensity 분석에 적합하다.

현재 데이터 기준으로는 월별 게시글이 적은 기간이 다수 존재하여 표본 안정성 문제가 있다.
이후 H3-pre 회귀분석에서는 두 단위를 모두 사용하되, 결과를 교차 확인하는 방법이 적절하다.

---

## 9. 해석상 주의사항

- 본 작업은 H3 회귀분석이 아니라, 단순 humor usage intensity의 기간별 분포와 변동성을 확인하기 위한 사전 점검이다.
- humor_intensity는 모델 기반 유머 유무 예측값인 pred_humor_final_050을 사용해 계산되었으며, 전체 게시글에 대한 확정 사람 코딩 결과가 아니다.
- engagement 평균은 descriptive audit 목적으로만 제시되었으며, 본 단계에서는 인과관계나 통계적 유의성을 해석하지 않는다.
- 다음 단계에서 H3-pre 회귀분석을 수행할 경우, post i를 제외한 leave-one-out humor_intensity를 사용하는 것이 더 적절하다.
- self-endogeneity 문제를 방지하기 위해 분석 단위 내 자기 자신의 humor 여부가 period intensity에 포함되지 않도록 LOO 변수를 사전 생성하였다.

---

## 10. 원본 데이터 보호 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2 결과 파일 수정 없음
- H3 회귀분석 미수행

---

*생성일: 2026-06-15*
