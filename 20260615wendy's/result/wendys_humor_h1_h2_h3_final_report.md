# Wendy's Humor Engagement 분석 — H1·H2·H3 최종 결과 보고서

**작성일**: 2026-06-16  
**분석 대상**: Wendy's Twitter (X) 게시물 참여도 데이터  
**원본 파일**: `data/wendys/posts.json` (불변, 수정 없음)  
**산출물 경로**: `20260615wendy's/`

---

## 1. 분석 개요

본 보고서는 Wendy's Twitter 계정의 유머 활용 전략과 게시물 참여도(engagement) 간의 관계를 세 가지 가설(H1, H2, H3)에 따라 검증한 전체 분석의 최종 결과를 요약한다. 모든 수치는 이미 생성된 결과 파일로부터 추출하였으며, 새로운 분석은 수행하지 않았다.

### 공통 분석 설정

| 항목 | 내용 |
|---|---|
| 분석 방법 | OLS 회귀분석 (`statsmodels.OLS`) |
| Primary DV | `log1p_engagement_total` |
| Supplemental DVs | `log1p_engagement_favorite_retweet`, `log1p_favorite_count`, `log1p_retweet_count`, `log1p_reply_count`, `log1p_quote_count`, `log1p_bookmark_count` |
| Time FE | `created_year`, `created_month`, `created_hour` (범주형, `pd.get_dummies`, `drop_first=True`) |
| Post format controls | `text_length`, `hashtag_count`, `mention_count` |
| 제외 변수 | `view_count`, `log1p_view_count`, `emoji_count`, `url_count`, `is_quote_status`, `is_retweet_text`, frequency count 변수, year_quarter FE, quarter FE |
| Primary predictor (H3) | LOO quarter-level proportion (year_quarter FE와 동일 수준이므로 time FE에서 year_quarter는 제외) |
| 필터 (H3) | `quarter_total_posts >= 10` → n=960, 25개 분기 |

---

## 2. H1 결과: 유머 게시물 vs. 비유머 게시물 참여도 차이

### 가설
**H1**: Wendy's의 유머 게시물은 비유머 게시물보다 높은 참여도를 가질 것이다.

### 분석 설계
- **IV**: 이진 유머 더미 변수 (binary humor dummy) — 모델 기반 약지도 학습 분류 결과
- **표본**: 전체 표본(full sample, n=978) + 인간 검증 표본(human validation, n=597)
- **최종 모형**: M7_all_three (time FE + text_length + hashtag_count + mention_count)
- **모형 스펙트럼**: M0(time FE only)~M7(time FE + 3개 format controls), 8개 모형

### 핵심 결과 (Primary DV: log1p_engagement_total, M7_all_three)

| 표본 | n | β | p | R² | 판정 |
|---|---|---|---|---|---|
| Full sample (binary IV) | 978 | 0.2918 | 0.0088 | 0.249 | **supports_H1** |
| Full sample (probability IV) | 978 | 0.8404 | 0.0175 | 0.248 | **supports_H1** |
| Human validation | 597 | 0.3171 | 0.0307 | 0.260 | **supports_H1** |

### 강건성 (8개 모형 전체)
- Full sample binary: M0~M7 전 모형 supports_H1 (β 범위: 0.2285~0.5134, 전부 p<.05)
- Full sample probability: M0~M7 모두 supports_H1 (β 범위: 0.8274~1.5082, 전부 p<.05)  
  단, M3_mention, M6_hashtag_mention에서 일부 DV positive_not_significant
- Human validation: M0, M1, M2, M4, M5, M7 → supports_H1; M3, M6 → weak_support

### Supplemental DV 패턴
- `log1p_favorite_count`, `log1p_retweet_count`: 전반적으로 강한 지지
- `log1p_reply_count`, `log1p_quote_count`: 일부 모형에서 positive_not_significant 또는 weak_support
- `log1p_bookmark_count`: 대부분 not_support 또는 positive_not_significant

### H1 판정
> **H1 지지**: 유머 게시물은 비유머 게시물 대비 통계적으로 유의하게 높은 총 참여도(log1p_engagement_total)를 보인다. 이 결과는 binary IV, probability IV, 인간 검증 표본에서 일관되게 재현된다. Time FE 및 post format controls(text_length, hashtag_count, mention_count)를 통제한 최종 모형(M7)에서도 결과는 유지된다.

---

## 3. H2 결과: 공격적 유머 vs. 기타 유머 참여도 차이

### 가설
**H2**: Wendy's의 공격적 유머(aggressive humor) 게시물은 기타 유머(other humor) 게시물보다 높은 참여도를 가질 것이다.

### 분석 설계
- **IV**: 공격적 유머 더미 (aggressive humor dummy) — 1=공격적 유머, 0=기타 유머
- **표본**: 유머 게시물만 포함
  - Model-based: n=564 (공격적 유머 n=200, 기타 유머 n=364)
  - Human validation: n=278 (공격적 유머 n=95, 기타 유머 n=183)
- **최종 모형**: M7_year_month_hour_fe + post format controls M7_time_fe_all_post_format

### 그룹 평균 (Primary DV: log1p_engagement_total, Step 1 기준)

| 표본 | 공격적 유머 n | Mean | 기타 유머 n | Mean | 평균차 |
|---|---|---|---|---|---|
| Model-based (n=564) | 200 | 7.9281 | 364 | 7.4597 | +0.4684 |
| Human validation (n=278) | 95 | 8.3411 | 183 | 7.6338 | +0.7074 |

### Step 1: Baseline (no controls)

| 표본 | n | β | p | 판정 |
|---|---|---|---|---|
| Model-based | 564 | 0.4684 | 0.0021 | **supports_H2** |
| Human validation | 278 | 0.7074 | 0.0007 | **supports_H2** |

### Step 2: Time FE 추가 (8개 모형, Model-based, Primary DV)

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0_baseline | 0.4684 | 0.0021 | supports_H2 |
| M1_year_fe | 0.5463 | 0.0003 | supports_H2 |
| M2_month_fe | 0.3763 | 0.0106 | supports_H2 |
| M3_hour_fe | 0.5301 | 0.0006 | supports_H2 |
| M4_year_month_fe | 0.4663 | 0.0016 | supports_H2 |
| M5_year_hour_fe | 0.6102 | 0.0001 | supports_H2 |
| M6_month_hour_fe | 0.4261 | 0.0043 | supports_H2 |
| M7_year_month_hour_fe | 0.5199 | 0.0006 | **supports_H2** |

Step 2 Human validation (M7): β=0.7261, p=0.0003, **supports_H2** (8개 모형 전부 supports_H2)

### Step 3: Post Format Controls 추가 (8개 모형, Model-based, Primary DV)

| 모형 | β | p | 판정 |
|---|---|---|---|
| M0_time_fe_only | 0.5199 | 0.0006 | supports_H2 |
| M1_time_fe_text | 0.3454 | 0.0229 | supports_H2 |
| M2_time_fe_hashtag | 0.5551 | 0.0002 | supports_H2 |
| M3_time_fe_mention | 0.5005 | 0.0005 | supports_H2 |
| M4_time_fe_text_hashtag | 0.4006 | 0.0087 | supports_H2 |
| M5_time_fe_text_mention | 0.3700 | 0.0115 | supports_H2 |
| M6_time_fe_hashtag_mention | 0.5260 | 0.0002 | supports_H2 |
| M7_time_fe_all_post_format | **0.4056** | **0.0060** | **supports_H2** |

Step 3 Human validation (M7): β=0.6405, p=0.0010, **supports_H2** (8개 모형 전부 supports_H2)

### H2 판정
> **H2 지지**: 공격적 유머 게시물은 기타 유머 게시물 대비 총 참여도가 통계적으로 유의하게 높다. 이 결과는 time FE 및 post format controls 통제 후에도 안정적으로 유지되며(M7: β=0.4056, p=0.0060), 인간 검증 표본에서도 동일 방향으로 재현된다(M7: β=0.6405, p=0.0010). Step 1~3 총 16개 모형 × 2개 표본 = 32개 모형 조합 전부에서 supports_H2 판정이다.

---

## 4. H3 결과: 유머 사용 강도와 참여도의 역 U자형 관계

### 가설
**H3**: Wendy's의 humor usage intensity는 post-level engagement와 역 U자형(inverted-U) 관계를 가질 것이다. 즉, 낮은 수준에서 중간 수준까지는 engagement가 증가하지만, 일정 수준을 넘어서면 감소할 것이다.

### 분석 설계
- **Predictor**: LOO quarter-level proportion 변수
  - H3-pre: `humor_proportion_quarter_loo` (전체 유머 비율)
  - H3-main: `aggressive_humor_proportion_quarter_loo` (공격적 유머 비율)
  - H3-supplemental: `other_humor_proportion_quarter_loo` (기타 유머 비율)
- **LOO 이유**: focal post가 자신이 속한 분기 비율에 기계적으로 반영되는 편향 제거
- **모형**: OLS 이차함수 (`pred` + `pred_sq`)
- **역 U자형 판정 기준**: β₁>0 AND β₂<0 (p₂<.05) AND turning point가 관측 범위 내
- **필터**: `quarter_total_posts >= 10` → **n=960**, 25개 분기

### 주의: year_quarter FE 미사용 이유
LOO 분기별 비율(predictor)은 year_quarter 수준에서 계산되므로, year_quarter FE를 추가하면 predictor 변동을 FE가 흡수한다. 따라서 H3 분석에서는 year/month/hour FE만 사용하며 year_quarter FE는 제외한다.

---

### Step 1: 기준 이차함수 회귀 (통제변수 없음)

**H3-pre (humor_proportion_quarter_loo, Primary DV)**

| β₁ | p₁ | β₂ | p₂ | Turning point | 범위 내 | 판정 |
|---|---|---|---|---|---|---|
| 0.1917 | 0.9289 | 0.3153 | 0.8708 | -0.3040 | False | **not_support** |

→ β₂>0 (U자형), 유의하지 않음. 역 U자형 미지지.

**H3-main (aggressive_humor_proportion_quarter_loo, Primary DV)**

| β₁ | p₁ | β₂ | p₂ | Turning point | 범위 내 | 판정 |
|---|---|---|---|---|---|---|
| -1.4598 | 0.6530 | 2.5539 | 0.7389 | 0.2858 | True | **not_support** |

→ β₂>0이나 유의하지 않음. 역 U자형 미지지.

---

### Step 2: Time FE 추가 (8개 모형, Primary DV)

**H3-pre (general humor proportion)**

| 모형 | β₁ | p₁ | β₂ | p₂ | TP | TP in range | 판정 |
|---|---|---|---|---|---|---|---|
| M0 (baseline) | 0.1917 | 0.9289 | 0.3153 | 0.8708 | -0.304 | False | not_support |
| M1 (+year) | -4.6777 | 0.0608 | 2.2617 | 0.2818 | 1.034 | False | not_support |
| M2 (+month) | -0.3622 | 0.8661 | 0.9349 | 0.6322 | 0.194 | True | not_support |
| M3 (+hour) | 0.1349 | 0.9502 | 0.3398 | 0.8618 | -0.198 | False | not_support |
| M4 (+year+month) | -6.0393 | 0.0185 | 4.0517 | 0.0631 | 0.745 | True | not_support |
| M5 (+year+hour) | -4.9650 | 0.0493 | 2.5045 | 0.2387 | 0.991 | False | not_support |
| M6 (+month+hour) | -0.5388 | 0.8038 | 1.0519 | 0.5938 | 0.256 | True | not_support |
| **M7 (+year+month+hour)** | **-6.6063** | **0.0114** | **4.5366** | **0.0406** | **0.728** | **True** | **not_support** |

→ M7에서 β₂>0, p₂=0.041: U자형 신호 출현. 그러나 역 U자형(β₂<0)이 아니므로 not_support.

**H3-main (aggressive humor proportion)**

| 모형 | β₂ | p₂ | TP in range | 판정 |
|---|---|---|---|---|
| M0 | 2.5539 | 0.7389 | True | not_support |
| M1 (+year) | 9.9964 | 0.2296 | True | not_support |
| M2 (+month) | -11.2573 | 0.1520 | True | **directional_only** |
| M3 (+hour) | 5.3534 | 0.4832 | True | not_support |
| M4 (+year+month) | -3.4880 | 0.6875 | False | not_support |
| M5 (+year+hour) | 13.5347 | 0.1069 | True | not_support |
| M6 (+month+hour) | -8.2050 | 0.2976 | True | **directional_only** |
| **M7 (+year+month+hour)** | **0.7974** | **0.9278** | **False** | **not_support** |

→ M2, M6에서 directional_only(β₂<0이나 p₂>.05). 전반적으로 not_support.

---

### Step 3: Post Format Controls 추가 (8개 모형, Primary DV)

**H3-pre (general humor proportion)**

| 모형 | β₂ | p₂ | 판정 |
|---|---|---|---|
| M0 (time FE only) | 4.5366 | 0.0406 | not_support |
| M1 (+text_length) | 5.2149 | 0.0167 | not_support |
| M2 (+hashtag_count) | 4.2098 | 0.0555 | not_support |
| M3 (+mention_count) | 3.8706 | 0.0662 | not_support |
| M4 (+text+hashtag) | 4.9205 | 0.0237 | not_support |
| M5 (+text+mention) | 4.3822 | 0.0364 | not_support |
| M6 (+hashtag+mention) | 3.7758 | 0.0730 | not_support |
| **M7 (+all three)** | **4.3189** | **0.0395** | **not_support** |

→ 전체 format controls 추가에도 β₂>0 (U자형) 지속. 역 U자형 미지지.

**H3-main (aggressive humor proportion)**

| 모형 | β₂ | p₂ | 판정 |
|---|---|---|---|
| M0 (time FE only) | 0.7974 | 0.9278 | not_support |
| M1 (+text_length) | 1.4334 | 0.8681 | not_support |
| M2 (+hashtag_count) | 0.9722 | 0.9113 | not_support |
| M3 (+mention_count) | -4.2644 | 0.6103 | not_support |
| M4 (+text+hashtag) | 1.4718 | 0.8642 | not_support |
| M5 (+text+mention) | -3.3704 | 0.6848 | not_support |
| M6 (+hashtag+mention) | -3.9878 | 0.6335 | not_support |
| **M7 (+all three)** | **-3.2814** | **0.6929** | **not_support** |

→ 전체 format controls 추가 후에도 일관되게 not_support.

---

### Step 4 (Supplemental): 기타 유머 비율(other_humor_proportion_quarter_loo) 검증

기타 유머 비율(`other_humor_proportion_quarter_loo`)에 대한 이차함수 검증은 H3-pre, H3-main의 supplemental 분석으로 수행되었다.

**H3-supplemental (other humor proportion, Primary DV, 9개 모형)**

| 모형 | β₁ | p₁ | β₂ | p₂ | 판정 |
|---|---|---|---|---|---|
| M0 (baseline only) | 1.8261 | 0.2659 | -1.6771 | 0.4437 | **directional_only** |
| M1 (+time FE) | -6.4318 | 0.0115 | 7.2371 | 0.0142 | **U_shape** |
| M2 (+time+text) | -6.5285 | 0.0090 | 7.5500 | 0.0091 | **U_shape** |
| M3 (+time+hashtag) | -6.2688 | 0.0131 | 6.8336 | 0.0196 | **U_shape** |
| M4 (+time+mention) | -6.8662 | 0.0045 | 7.7766 | 0.0055 | **U_shape** |
| M5 (+time+text+hashtag) | -6.4140 | 0.0101 | 7.2582 | 0.0120 | **U_shape** |
| M6 (+time+text+mention) | -6.8887 | 0.0041 | 7.9315 | 0.0044 | **U_shape** |
| M7 (+time+hashtag+mention) | -6.7931 | 0.0050 | 7.6167 | 0.0066 | **U_shape** |
| M8 (+time+all format) | -6.8614 | 0.0043 | 7.8688 | 0.0047 | **U_shape** |

→ **중요**: β₂>0이므로 U자형(정 U)이다. 이는 H3가 예측하는 역 U자형(β₂<0)과 반대 방향이다. time FE 추가 시 U_shape이 통계적으로 유의하게 나타남(M1~M8, p₂<.05). M0(통제변수 없음)에서는 directional_only(β₁>0, β₂<0이나 p₂>.05).

---

### Step 5 (Joint): 공격적 유머 + 기타 유머 동시 투입 — 마스킹 효과 검증

기타 유머의 U_shape 패턴이 공격적 유머의 효과를 억제(masking)했는지 검증하기 위해 두 예측변수를 동시에 투입하였다.

**사전 확인**: 두 예측변수 간 상관관계 = **-0.2641** (다중공선성 우려 없음)

**H3-joint 결과 (Primary DV, 3개 모형)**

| 모형 | Aggressive β₂ | p₂ | Aggressive 판정 | Other β₂ | p₂ | Other 판정 |
|---|---|---|---|---|---|---|
| M0 (baseline) | 6.1978 | 0.4442 | aggressive_not_support | -1.4915 | 0.5001 | other_not_support |
| M1 (+time FE) | 0.3261 | 0.9721 | aggressive_not_support | 7.7001 | 0.0096 | **other_U_shape** |
| M2 (+time+all format) | -3.7276 | 0.6722 | aggressive_not_support | 8.1417 | 0.0037 | **other_U_shape** |

→ **마스킹 없음 확인**: 두 변수를 동시에 통제해도 공격적 유머는 전 모형에서 not_support. 기타 유머의 U자형은 time FE 추가 시 독립적으로 나타남. 공격적 유머에 대한 역 U자형 가설(H3-main)은 기타 유머의 억제 효과와 무관하게 기각된다.

---

### H3 최종 판정 요약

| 분석 | 모형 수 | 핵심 패턴 | 판정 |
|---|---|---|---|
| H3-pre (general humor proportion) | Step 1~3, 17개 | β₂>0 일관 (not_support) | **H3 불지지** |
| H3-main (aggressive humor proportion) | Step 1~3, 17개 | β₂ 불유의 (not_support) | **H3 불지지** |
| H3-supplemental (other humor proportion) | Step 4, 9개 | M1~M8 U_shape (β₂>0, 역방향) | H3 불지지 (역방향 U) |
| H3-joint (aggressive+other 동시) | Step 5, 3개 | aggressive not_support, masking 없음 | **H3 불지지** |

> **H3 기각**: 어떤 유머 비율 변수(general, aggressive, other)도 역 U자형 관계를 보이지 않는다. 공격적 유머 비율은 참여도와 유의한 이차함수 관계가 없으며, 기타 유머 비율은 time FE 통제 후 역방향 U자형(정 U)을 보인다. 마스킹 효과 검증 결과, 기타 유머의 패턴이 공격적 유머의 효과를 억제하지 않음을 확인하였다.

---

## 5. 가설별 결과 요약표

| 가설 | 내용 | 핵심 수치 (최종 모형) | 결론 |
|---|---|---|---|
| **H1** | 유머 게시물 > 비유머 게시물 참여도 | β=0.2918, p=0.0088 (n=978, M7) | **지지** |
| **H2** | 공격적 유머 > 기타 유머 참여도 | β=0.4056, p=0.0060 (n=564, M7) | **지지** |
| **H3** | 유머 강도와 참여도 역 U자형 | H3-pre: not_support; H3-main: not_support | **기각** |

---

## 6. 증거 계층 (Evidence Hierarchy)

### H1
1. **1차 증거**: Full sample binary (n=978), M7_all_three: β=0.2918, p=0.0088
2. **교차 검증**: Full sample probability (n=978), M7: β=0.8404, p=0.0175
3. **인간 검증**: Human validation (n=597), M7: β=0.3171, p=0.0307
4. **강건성**: 8개 모형 전부 supports_H1 (full sample binary 기준)

### H2
1. **1차 증거**: Model-based (n=564), M7(time+format): β=0.4056, p=0.0060
2. **인간 검증**: Human validation (n=278), M7(time+format): β=0.6405, p=0.0010
3. **강건성**: Step 1~3, model-based + human validation 전 32개 모형 조합 모두 supports_H2

### H3
1. **1차 부정 증거**: H3-pre not_support (17개 모형, β₂>0 일관)
2. **2차 부정 증거**: H3-main not_support (17개 모형, β₂ 불유의)
3. **역방향 패턴**: Other humor proportion에서 time FE 통제 후 U_shape(β₂>0, p<.05) — H3 예측(역 U)과 반대
4. **마스킹 검증**: Joint model에서 masking 없음 확인 — H3 기각의 robustness 확보

---

## 7. 방법론 주의사항

### 관측적 연구의 한계
본 분석은 관측적(observational) 자료를 사용하며, 인과관계(causality)를 주장하지 않는다. 유머 사용과 참여도 간의 관계는 제3의 요인(예: 특정 이벤트, 콘텐츠 주제, 플랫폼 알고리즘 변화)에 의해 매개될 수 있다.

### H3 식별 문제
LOO quarter-level proportion predictor와 year_quarter FE는 동일 수준에서 정의되므로, H3 분석에서 year_quarter FE를 포함할 경우 predictor 변동이 흡수된다. 따라서 H3 분석에서는 year FE, month FE, hour FE만 사용하고 year_quarter FE는 의도적으로 제외한다.

### 유머 분류 방법
유머 분류는 약지도 학습(weak supervised learning) 모델 기반 예측을 primary 증거로 사용하며, 인간 코딩 결과는 교차 검증(cross-validation) 목적으로만 활용한다.

### H3 U_shape 해석
기타 유머 비율에서 관찰된 U자형(β₂>0)은 H3가 예측하는 역 U자형(β₂<0)과 반대 방향이다. 이는 "낮은 강도 또는 높은 강도 수준에서 참여도가 높고, 중간 수준에서 낮다"는 패턴을 의미하나, 이론적 예측과 불일치하므로 H3를 지지하지 않는다.

---

## 8. 분석 강건성 점검 항목

| 점검 항목 | 결과 |
|---|---|
| 원본 posts.json 수정 | 없음 (불변) |
| 신규 유머 분류 모델 학습 | 없음 |
| year_quarter FE 사용 | 없음 (H3에서 제외 확인) |
| view_count 사용 | 없음 |
| frequency count 사용 | 없음 |
| emoji_count, url_count 사용 | 없음 |
| Post format merge 안정성 (H3) | 978→978 (0 unmatched) |
| quarter_total_posts >= 10 필터 | 항상 적용 (n=978→960) |
| LOO 변수 결측 (필터 후) | 0개 |
| Joint model 다중공선성 | corr(agg, oth) = -0.2641, 우려 없음 |

---

## 9. 분석 파일 목록

### 코드 파일 (`20260615wendy's/code/`)
- `run_wendys_h1_three_post_format_controls.py` — H1 최종 분석
- `run_wendys_h2_step1_direct_test.py` — H2 Step 1
- `run_wendys_h2_step2_time_fe_models.py` — H2 Step 2
- `run_wendys_h2_step3_post_format_controls.py` — H2 Step 3
- `run_wendys_h3_step1_quadratic_intensity.py` — H3 Step 1
- `run_wendys_h3_step2_proportion_time_variables.py` — H3 Step 2
- `run_wendys_h3_step3_proportion_post_format_controls.py` — H3 Step 3
- `run_wendys_h3_supplemental_other_humor_proportion.py` — H3 Supplemental
- `run_wendys_h3_joint_aggressive_other_decomposition.py` — H3 Joint

### 주요 결과 파일 (`20260615wendy's/result/`)

**H1**
- `wendys_h1_three_post_format_fullsample_binary_results.csv`
- `wendys_h1_three_post_format_fullsample_probability_results.csv`
- `wendys_h1_three_post_format_human_validation_results.csv`
- `wendys_h1_three_post_format_summary.md`

**H2**
- `wendys_h2_step1_model_based_direct_results.csv`
- `wendys_h2_step1_human_validation_results.csv`
- `wendys_h2_step2_time_fe_model_based_results.csv`
- `wendys_h2_step2_time_fe_human_validation_results.csv`
- `wendys_h2_step3_post_format_model_based_results.csv`
- `wendys_h2_step3_post_format_human_validation_results.csv`

**H3**
- `wendys_h3_step1_general_humor_quadratic_results.csv`
- `wendys_h3_step1_aggressive_humor_quadratic_results.csv`
- `wendys_h3_step2_general_humor_time_results.csv`
- `wendys_h3_step2_aggressive_humor_time_results.csv`
- `wendys_h3_step3_general_humor_post_format_results.csv`
- `wendys_h3_step3_aggressive_humor_post_format_results.csv`
- `wendys_h3_supplemental_other_humor_proportion_results.csv`
- `wendys_h3_joint_aggressive_other_decomposition_results.csv`

---

## 10. Git 커밋 이력 (H3 분석 관련)

| 커밋 | 내용 |
|---|---|
| 8b5e4bc | analysis: run wendys h3 step1 quadratic intensity test |
| 51fb79c | analysis: add time variables to wendys h3 proportion test |
| 786bf1f | analysis: add post format controls to wendys h3 proportion test |
| 9ac621c | analysis: test other humor proportion in wendys h3 |
| 08bf92e | analysis: decompose aggressive and other humor proportions in wendys h3 |

---

## 11. 결론

Wendy's Twitter 데이터 분석 결과, **H1과 H2는 지지되고 H3는 기각**된다.

- **H1 (지지)**: 유머 게시물은 비유머 게시물 대비 통계적으로 유의하게 높은 총 참여도를 보인다 (β=0.2918, p<.01, n=978). 이 결과는 post format 통제 후에도, 인간 검증 표본에서도 재현된다.

- **H2 (지지)**: 공격적 유머 게시물은 기타 유머 게시물 대비 통계적으로 유의하게 높은 참여도를 보인다 (β=0.4056, p<.01, n=564). 이 결과는 time FE 및 format controls 통제에도 안정적이며, 인간 검증 표본에서 더욱 강한 효과를 보인다 (β=0.6405, p<.01, n=278).

- **H3 (기각)**: 유머 강도(quarter-level LOO proportion)와 engagement 간의 역 U자형 관계는 어떤 유머 유형에서도, 어떤 통제변수 조합에서도 나타나지 않는다. 공격적 유머 비율은 유의한 이차함수 관계가 없고, 기타 유머 비율은 time FE 통제 후 역방향(정 U자형)을 보인다. 마스킹 효과 검증에서도 결론이 변하지 않는다.

이상의 결과는 Wendy's의 유머 활용 전략에서 "유머 자체의 존재"와 "공격적 유머의 유형"이 참여도에 긍정적 영향을 미치는 반면, "유머 사용 비율의 최적 수준"이라는 역 U자형 가설은 본 데이터에서 지지되지 않음을 시사한다.
