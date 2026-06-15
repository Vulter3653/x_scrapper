# Wendy's H2 단순 OLS 및 aggressive vs other humor t-test 결과

생성일시: 2026-06-15 17:36 UTC

---

## 1. 작업 목적

`final_humor_type` 기반으로 H2를 확인한다.

```
H2: aggressive humor 게시글은 다른 유머 유형 게시글보다 engagement가 높을 것이다.
```

본 분석은 관측적 연관성 분석이며, 통제변수와 고정효과가 없는 단순 기저선 분석이다.

---

## 2. H2 가설

```
H2: aggressive humor → other humor 대비 더 높은 engagement
```

H2 해석 기준:

```
β1(aggressive) > β2(other_humor) and β1 p<0.05  → H2 예비적 지지
β1 > β2 and β1 p≥0.05                           → H2 방향성 지지
β1 <= β2                                         → H2 지지 없음
```

---

## 3. 사용 데이터

| 항목 | 건수 |
|------|------|
| 전체 게시글 | 978건 |
| 사람 라벨 유효 (labeled) | 597건 |
| 유머 전용 (humor_only) | 309건 |
| — aggressive | 90건 |
| — other humor | 219건 |
| 비유머 (non-humor, 기준범주) | 288건 |

더미 변수 정의:

```
aggressive_humor = 1 if final_humor_binary=1 AND final_humor_type='aggressive'
other_humor      = 1 if final_humor_binary=1 AND final_humor_type≠'aggressive'
기준범주           = final_humor_binary=0 (non-humor)
```

---

## 4. 분석 1: Welch t-test — aggressive vs other humor (유머 전용)

집단: aggressive=90건 vs other_humor=219건

| DV | aggressive 평균 | other 평균 | 차이 | t | p | d | H2 |
|---|---|---|---|---|---|---|---|
| `log1p_engagement_total` | 8.4124 | 7.5115 | 0.9009 | 4.1479 | 0.000056*** | 0.5420 | H2 예비적 지지 |
| `log1p_engagement_favorite_retweet` | 8.2812 | 7.3782 | 0.9029 | 4.0576 | 0.000079*** | 0.5320 | H2 예비적 지지 |
| `log1p_favorite_count` | 8.2112 | 7.2694 | 0.9418 | 4.1512 | 0.000053*** | 0.5268 | H2 예비적 지지 |
| `log1p_retweet_count` | 5.4629 | 4.4572 | 1.0057 | 4.3037 | 0.000030*** | 0.5692 | H2 예비적 지지 |
| `log1p_reply_count` | 5.3895 | 4.7928 | 0.5967 | 3.1711 | 0.001832** | 0.4108 | H2 예비적 지지 |
| `log1p_quote_count` | 3.9607 | 2.9470 | 1.0137 | 4.1161 | 0.000065*** | 0.5522 | H2 예비적 지지 |
| `log1p_bookmark_count` | 3.3460 | 2.6538 | 0.6922 | 3.3643 | 0.000942*** | 0.4097 | H2 예비적 지지 |


**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| aggressive 평균 | 8.4124 |
| other humor 평균 | 7.5115 |
| 차이 (aggressive − other) | 0.9009 |
| t | 4.1479 |
| p-value | 0.000056*** |
| Cohen's d | 0.5420 (중간) |
| **H2 해석** | **H2 예비적 지지** |

---

## 5. 분석 2: 단순 OLS — 유머 전용 표본, IV=aggressive 더미

표본: 유머 309건 (aggressive=1: 90건, other=0: 219건)

| DV | β(aggressive) | SE | t | p | R² | H2 |
|---|---|---|---|---|---|---|
| `log1p_engagement_total` | 0.900917 | 0.208139 | 4.3284 | 0.000020*** | 0.057517 | H2 예비적 지지 |
| `log1p_engagement_favorite_retweet` | 0.902922 | 0.212499 | 4.2491 | 0.000029*** | 0.055543 | H2 예비적 지지 |
| `log1p_favorite_count` | 0.941776 | 0.223847 | 4.2072 | 0.000034*** | 0.054514 | H2 예비적 지지 |
| `log1p_retweet_count` | 1.005701 | 0.221243 | 4.5457 | 0.000008*** | 0.063063 | H2 예비적 지지 |
| `log1p_reply_count` | 0.596684 | 0.181856 | 3.2811 | 0.001153** | 0.033879 | H2 예비적 지지 |
| `log1p_quote_count` | 1.013666 | 0.229844 | 4.4102 | 0.000014*** | 0.059581 | H2 예비적 지지 |
| `log1p_bookmark_count` | 0.692207 | 0.211524 | 3.2725 | 0.001188** | 0.033707 | H2 예비적 지지 |


**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| β(aggressive) | +0.900917 |
| SE | 0.208139 |
| t | 4.3284 |
| p-value | 0.000020*** |
| R² | 0.057517 |
| **H2 해석** | **H2 예비적 지지** |

---

## 6. 분석 3: 다중 더미 OLS — 전체 라벨 표본 (기준범주=non-humor)

표본: 사람 라벨 597건 (aggressive=90, other=219, non-humor=288)

식: `log1p_DV = α + β1·aggressive_humor + β2·other_humor + ε`

| DV | β_agg | p_agg | β_other | p_other | β1−β2 | R² | H2 |
|---|---|---|---|---|---|---|---|
| `log1p_engagement_total` | 1.142836*** | 0.000000 | 0.241918n.s. | 0.114440 | +0.900917 | 0.049274 | H2 예비적 지지 |
| `log1p_engagement_favorite_retweet` | 1.157565*** | 0.000000 | 0.254643n.s. | 0.102716 | +0.902922 | 0.048755 | H2 예비적 지지 |
| `log1p_favorite_count` | 1.281883*** | 0.000000 | 0.340107* | 0.049363 | +0.941776 | 0.048714 | H2 예비적 지지 |
| `log1p_retweet_count` | 1.039269*** | 0.000001 | 0.033567n.s. | 0.828520 | +1.005701 | 0.043379 | H2 예비적 지지 |
| `log1p_reply_count` | 0.849481*** | 0.000006 | 0.252797† | 0.068368 | +0.596684 | 0.033988 | H2 예비적 지지 |
| `log1p_quote_count` | 1.071735*** | 0.000001 | 0.058069n.s. | 0.722855 | +1.013666 | 0.040782 | H2 예비적 지지 |
| `log1p_bookmark_count` | 0.310274n.s. | 0.143716 | -0.381933* | 0.015506 | +0.692207 | 0.018988 | H2 방향성 지지 |


**주요 결과 (`log1p_engagement_total`):**

| 항목 | 값 |
|------|-----|
| α (non-humor 기준) | 7.269567 |
| β1 (aggressive vs non-humor) | +1.142836 (p=0.0000***) |
| β2 (other_humor vs non-humor) | +0.241918 (p=0.1144n.s.) |
| β1 − β2 | +0.900917 |
| R² | 0.049274 |
| **H2 해석** | **H2 예비적 지지** |

β1 > β2이므로 aggressive humor가 other humor보다 non-humor 기준 대비 더 높은 engagement와 연관된다.

---

## 7. 종합 해석

| 분석 방법 | H2 판단 |
|----------|---------|
| t-test (aggressive vs other) | H2 예비적 지지 |
| OLS humor-only | H2 예비적 지지 |
| OLS full labeled (β1 vs β2) | H2 예비적 지지 |

---

## 8. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만을 대상으로 한다.
- 통제변수와 고정효과가 포함되지 않은 단순 기저선 분석이다.
- `final_humor_type`은 coder1 > human > coder2 우선순위 규칙으로 생성한 예비적 라벨이다.
  코더 간 불일치율(coder1 vs coder2 type: 약 70.6%)이 높으므로 결과 해석에 주의가 필요하다.
- self-defeating 표본(14건)이 적어 4유형 동등 비교는 수행하지 않았다.
- type 없음(46건)을 other_humor에 포함했으므로 other_humor 집단이 이질적일 수 있다.
- 본 분석은 관측적 연관성 분석이며 인과관계를 주장할 수 없다.
