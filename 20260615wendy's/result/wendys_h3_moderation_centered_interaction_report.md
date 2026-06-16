# H3 Centered Moderation Model Report
## Wendy's Twitter Humor Intensity × Humor Presence Moderation

---

## 1. H3 모형 수식

```
log(Engagement_i) =
  β0
+ β1  · Humor_i
+ β2  · IntensityCentered_i
+ β3  · IntensityCentered_i²
+ β4  · (Humor_i × IntensityCentered_i)
+ β5  · (Humor_i × IntensityCentered_i²)
+ γ   · Controls_i
+ λ_t · Time FE
+ ε_i
```

**H3 지지 조건:** β4 > 0 AND β5 < 0, both p < .05  
*즉, 유머 게시물의 engagement 효과가 humor usage intensity에 따라 역 U자형(inverted-U)으로 조절되는지 검증.*

---

## 2. 변수 정의

| 변수 | 컬럼 / 계산 방법 | 설명 |
|---|---|---|
| Humor_i | `유머예측이진` | 유머 게시물 = 1, 비유머 = 0 |
| Intensity_i | `유머비율LOO분기` | 동일 분기 내 focal post 제외 유머 비율 (LOO) |
| IntensityCentered_i | `유머비율LOO분기` − mean(H3 sample) | 평균중심화된 intensity |
| IntensityCentered_i² | IntensityCentered_i² | 이차항 |
| Humor × IC | `유머예측이진` × IntensityCentered_i | 조절 상호작용항 (β4) |
| Humor × IC² | `유머예측이진` × IntensityCentered_i² | 이차 조절 상호작용항 (β5) |
| 텍스트길이 | `텍스트길이` | post format control |
| 해시태그수 | `해시태그수` | post format control |
| 멘션수 | `멘션수` | post format control |
| Year/Month/Hour FE | `작성연도`, `작성월`, `작성시간` dummies | 시간 고정효과 |
| DV | log1p(좋아요수+리트윗수+답글수+인용수+북마크수) | primary engagement |

---

## 3. 표본 수 검증

| 항목 | 기대값 | 실제값 | 통과 |
|---|---|---|---|
| H3분석표본 n | 960 | **960** | ✓ |
| quarter_count | 25 | **25** | ✓ |
| humor_n | — | **557** | — |
| nonhumor_n | — | **403** | — |
| 유머비율LOO분기 결측 | 0 | **0** | ✓ |
| 유머예측이진 범위 | {0, 1} | **{0, 1}** | ✓ |

---

## 4. 평균중심화 방식

- 평균중심화는 **H3분석표본(n = 960) 내부에서** 계산
- raw mean(유머비율LOO분기) = **0.5802** (range: 0.1579 ~ 0.9167)
- IntensityCentered mean after centering = **1.93e-15 ≈ 0** ✓
- 평균중심화 후 IC 값 범위: −0.4223 ~ +0.3365 (approx.)

---

## 5. M0, M1, M2 결과표

### DV: log1p_engagement_total, n = 960

| Coefficient | M0: Simple OLS | M1: Time FE | M2: Time FE + Controls (Primary) |
|---|:---:|:---:|:---:|
| **Humor (β1)** | .5447\*\*\* | .4237\*\* | .2459\* |
| | (SE = .147, p = .0002) | (SE = .145, p = .0035) | (SE = .140, p = .0799) |
| **IntensityCentered (β2)** | −.7579 | −2.4916\*\* | −2.3131\*\* |
| | (SE = .687, p = .2701) | (SE = .883, p = .0049) | (SE = .844, p = .0063) |
| **IntensityCentered² (β3)** | .0351 | 2.1714 | 2.4663 |
| | (SE = 3.261, p = .9914) | (SE = 3.254, p = .5047) | (SE = 3.099, p = .4263) |
| **Humor × IC (β4)** | 1.6488 | 1.5893 | 1.4176 |
| | (SE = .860, p = .0555) | (SE = .841, p = .0591) | (SE = .800, p = .0766) |
| **Humor × IC² (β5)** | −1.4275 | 2.3622 | 1.9648 |
| | (SE = 4.091, p = .7272) | (SE = 4.068, p = .5616) | (SE = 3.866, p = .6114) |
| **R²** | .026 | .175 | .260 |
| **Adj R²** | .021 | .136 | .222 |
| **n** | 960 | 960 | 960 |
| **Year FE** | Not included | Included | Included |
| **Month FE** | Not included | Included | Included |
| **Hour FE** | Not included | Included | Included |
| **Post Format Controls** | Not included | Not included | Included |
| **H3 interpretation** | weak\_support | **not\_support** | **not\_support** |

Significance: \*\*\* p < .01, \*\* p < .05, \* p < .10

---

## 6. H3 판정

**H3 판정: 지지되지 않음 (not\_support)**

Primary model (M2)에서:
- β4 (Humor × IntensityCentered) = **+1.4176**, p = .077 → 양수이나 p ≥ .05 (미유의)
- β5 (Humor × IntensityCentered²) = **+1.9648**, p = .611 → **양수** (H3 예측과 반대 방향), p 미유의

H3 지지 조건(β4 > 0 AND β5 < 0, both p < .05)을 충족하지 못함.

β5가 예측과 반대 방향(양수)으로 추정되어, humor usage intensity가 높아질수록 유머 게시물의 engagement 효과가 역 U자형으로 조절된다는 가설이 확인되지 않는다.

M0에서는 β4 > 0, β5 < 0 조건을 방향상 충족하지만(β4 p = .056, β5 p = .727), 시간 고정효과 투입 후(M1) β5 부호가 전환되어 구조적으로 지지되지 않는다.

---

## 7. 기존 H3 quadratic intensity model과의 비교

| 구분 | 기존 H3 (quadratic intensity) | 이번 H3 (moderation model) |
|---|---|---|
| 분석 단위 | 분기-수준 (quarter-level) | 개별 post-level |
| 핵심 예측변수 | 분기별 유머 비율 (LOO) 및 제곱항 | Humor dummy × 평균중심화 강도 × 제곱 상호작용 |
| 연구 질문 | 유머 강도(분기 비율)가 engagement에 역 U자형 효과를 갖는가? | 개별 유머 게시물의 효과가 humor intensity에 따라 역 U자형으로 조절되는가? |
| 결과 파일 | `wendys_h3_main_quadratic_ols_*` | `wendys_h3_moderation_centered_interaction_*` |
| 결과 | 별도 참조 | **H3 not\_support** |

*기존 H3 파일은 수정하지 않았음.*

---

## 8. Not-support 해석

β5의 부호가 양수(+1.9648)로 추정된 것은, 시간 고정효과 통제 후 humor usage intensity가 높은 분기에서도 humor posts의 engagement가 감소하지 않는다는 것을 시사한다. 역 U자형 조절 효과를 예측한 H3는 이 데이터에서 지지되지 않는다. β4의 양수 방향(humor posts가 intensity 증가에 따라 더 높은 engagement를 보임)은 일부 일관성을 보이나 유의수준 .05 기준을 충족하지 못한다.
