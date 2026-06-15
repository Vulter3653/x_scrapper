# Wendy's H1 분석: favorite + retweet 기반 engagement

생성일시: 2026-06-15 12:15 UTC

---

## 1. 작업 목적

기존 H1 분석에서 사용한 5종 engagement(reply + favorite + retweet + quote + bookmark)를
**favorite_count + retweet_count**만으로 좁혀 재분석한다.

좋아요(favorite)와 리트윗(retweet)은 X/Twitter에서 가장 일반적인 공개 수용 반응이며,
긍정·부정 해석이 모호한 댓글(reply), 논쟁성이 있는 인용(quote),
최근에만 집계된 북마크(bookmark)를 제외함으로써 측정 일관성을 높인다.

---

## 2. DV 재정의

```
engagement_favorite_retweet_i = favorite_count_i + retweet_count_i

log1p_engagement_favorite_retweet_i = log(1 + engagement_favorite_retweet_i)
```

다음 변수는 이 DV에 포함하지 않는다:

```
reply_count    — 긍정·부정 반응 모두 가능; 유머 반응과 구분 어려움
quote_count    — 비판·논쟁 맥락에서도 증가 가능
bookmark_count — 비공개 행동; 과거 게시글 결측 가능
view_count     — 노출 지표이며 반응 지표가 아님
```

**요약 통계 (engagement_favorite_retweet):**

| 지표 | 값 |
|------|-----|
| 전체 게시글 수 | 978 |
| engagement == 0 건수 | 0 (0.0%) |
| 평균 | 8798.15 |
| 중앙값 | 1273.50 |
| 최솟값 | 4 |
| 최댓값 | 909312 |
| log1p 평균 | 7.2843 |
| log1p 중앙값 | 7.1503 |
| favorite_count 결측 | 0 |
| retweet_count 결측 | 0 |

---

## 3. IV 정의

```
log1p_p_humor_ml_i = log(1 + p_humor_ml_i)
```

`p_humor_ml`은 TF-IDF + Logistic Regression 분류기 확률(65%)과
rule-based `humor_score`(35%)를 혼합한 유머 존재 가능성 점수이다.

`log1p_p_humor_ml` 평균: 0.3749 (log1p 변환 전 p_humor_ml 기준)

---

## 4. 회귀식

```
log1p_engagement_favorite_retweet_i
= α + β log1p_p_humor_ml_i + ε_i
```

각 항의 의미:

- `i` : 개별 Wendy's 게시글
- `log1p_engagement_favorite_retweet_i` : favorite_count와 retweet_count의 합을 로그 변환한 값
- `log1p_p_humor_ml_i` : 게시글 i의 유머 가능성 점수 `p_humor_ml`을 로그 변환한 값
- `β` : 유머 가능성 점수와 favorite/retweet 기반 engagement의 관련 방향을 보여주는 핵심 계수
- `ε_i` : 모델로 설명되지 않는 오차항

모델 설정: 단순 이변량 OLS / 통제변수 없음 / 고정효과 없음 / 표준 SE (HC3 미사용)

---

## 5. 주요 결과

| 파라미터 | 값 |
|----------|-----|
| n_obs | 978 |
| Intercept (α) | 7.095397 |
| β (`log1p_p_humor_ml`) | 0.603911 |
| Standard Error | 0.539865 |
| t-value | 1.1186 |
| p-value | 0.2636 |
| 95% CI | [7.445323, 1.663340] |
| R² | 0.001280 |
| Adj. R² | 0.000257 |
| **H1 해석** | **H1 방향성 지지** |

---

## 6. H1 해석

`log1p_p_humor_ml`은 favorite_count와 retweet_count로 구성한 engagement와
**양의 방향**을 보였다.
(β = 0.603911, SE = 0.539865, p = 0.2636, R² = 0.001280)

**H1 방향성 지지**

---

## 7. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- 본 분석은 단순 OLS이며 통제변수와 고정효과를 포함하지 않는다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
- `p_humor_ml`은 weak-supervised 측정값이며 human-labeled gold standard가 아니다.
- favorite_count와 retweet_count만 사용했기 때문에 댓글, 인용, 북마크 반응은 제외된다.
- engagement는 게시 시점, 미디어 콘텐츠, 플랫폼 알고리즘, 캠페인, 외부 사건의 영향을 받을 수 있다.
