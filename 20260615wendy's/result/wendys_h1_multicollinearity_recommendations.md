# Wendy's H1 후보 변수 다중공선성 진단 결과

## 1. 진단 목적

H1 controlled regression 실행 전, 기존 데이터에 존재하는 후보 통제변수들 사이의 다중공선성을 사전에 진단한다. 이번 작업에서는 회귀분석을 수행하지 않았으며, 새로운 변수를 생성하지 않았다.

---

## 2. 사용한 파일과 표본

| 항목 | 값 |
|---|---|
| pred 파일 | wendys_final_humor_presence_full_predictions.csv |
| fast 파일 | wendys_fast_weak_supervised_humor_dataset.csv |
| h3 파일 | wendys_h3_aggressive_vs_other_intensity_dataset.csv |
| 병합 key | id |
| 전체 병합 행 | 978 |
| **Primary sample** | **final_humor_label_available=1, n=597** |
| Supplemental | 전체 n=978 |

---

## 3. 병합 여부 및 안정성

| 항목 | 값 |
|---|---|
| left n (pred) | 978 |
| right fast n | 978 |
| right h3 n | 978 |
| 전체 merged | 978 |
| unmatched rows | 0 |
| primary n=597 유지 | True |
| 병합 안정성 | STABLE |

모든 978건이 1:1로 병합되었다. primary sample 597건 유지 확인.

---

## 4. 변수별 결측률·희소성·unique value 진단 (primary n=597)

| variable | missing_rate | zero_rate | std | unique_n | warnings |
|---|---|---|---|---|---|
| final_humor_binary | 0.0 | 0.4824 | 0.5001 | 2 | OK |
| created_year | 0.0 | 0.0 | 2.1373 | 8 | OK |
| created_month | 0.0 | 0.0 | 3.3347 | 12 | OK |
| created_hour | 0.0 | 0.0352 | 5.7428 | 20 | OK |
| quarter_total_posts | 0.0 | 0.0 | 23.0781 | 26 | OK |
| month_total_posts | 0.0 | 0.0 | 11.4961 | 28 | OK |
| text_length | 0.0 | 0.0 | 63.7178 | 207 | OK |
| url_count | 0.0 | 0.4958 | 0.582 | 4 | OK |
| mention_count | 0.0 | 0.809 | 0.7321 | 7 | OK |
| hashtag_count | 0.0 | 0.8827 | 0.3608 | 4 | OK |
| emoji_count | 0.0 | 0.8375 | 0.5322 | 5 | OK |
| is_quote_status | 0.0 | 0.8023 | 0.3986 | 2 | OK |
| is_retweet_text | 0.0 | 0.9832 | 0.1284 | 2 | zero_rate>0.9_SPARSE |
| log1p_view_count | 0.0 | 0.5176 | 6.3602 | 289 | OK |


**주목:**
- `is_quote_status` zero_rate = 0.8023 (기준 범주 확인 필요)
- `is_retweet_text` zero_rate = 0.9832 (기준 범주 확인 필요)
- `emoji_count` zero_rate = 0.8375 (희소성 주의)

---

## 5. Pairwise Correlation 주요 결과 (primary n=597, Pearson)

| 변수쌍 | pearson_r | spearman_r | severity |
|---|---|---|---|
| created_year × log1p_view_count | 0.8392 | 0.7658 | serious |
| quarter_total_posts × month_total_posts | 0.8264 | 0.7884 | serious |


**강조 쌍:**

| 쌍 | pearson_r | severity |
|---|---|---|
| quarter_total_posts × month_total_posts | 0.8264 | serious |
| created_year × quarter_total_posts | -0.3431 | OK |
| created_year × month_total_posts | -0.1661 | OK |
| created_month × month_total_posts | -0.2581 | OK |

---

## 6. VIF 주요 결과 (primary n=597)

### Model Set A: Time controls only
rank_deficient=False, condition_number=1.49 (acceptable), n_cols=5
| variable | VIF | severity |
|---|---|---|
| final_humor_binary | 1.0582 | acceptable |
| created_year | 1.162 | acceptable |
| created_month | 1.1073 | acceptable |
| created_hour | 1.0056 | acceptable |

### Model Set B: Time + Posting Intensity
rank_deficient=False, condition_number=3.7 (acceptable), n_cols=7
| variable | VIF | severity |
|---|---|---|
| final_humor_binary | 1.0686 | acceptable |
| created_year | 1.4511 | acceptable |
| created_month | 1.2726 | acceptable |
| created_hour | 1.0062 | acceptable |
| quarter_total_posts | 3.7656 | acceptable |
| month_total_posts | 3.3295 | acceptable |

### Model Set C: Time + Posting Intensity + Post Format
rank_deficient=False, condition_number=3.89 (acceptable), n_cols=14
| variable | VIF | severity |
|---|---|---|
| final_humor_binary | 1.1815 | acceptable |
| created_year | 1.4947 | acceptable |
| created_month | 1.3289 | acceptable |
| created_hour | 1.0282 | acceptable |
| quarter_total_posts | 3.8914 | acceptable |
| month_total_posts | 3.3797 | acceptable |
| text_length | 1.3153 | acceptable |
| url_count | 1.2128 | acceptable |
| mention_count | 1.2533 | acceptable |
| hashtag_count | 1.0893 | acceptable |
| emoji_count | 1.0895 | acceptable |
| is_quote_status | 1.1698 | acceptable |
| is_retweet_text | 1.0808 | acceptable |

### Model Set D: Exposure Robustness
rank_deficient=False, condition_number=3.8 (acceptable), n_cols=7
| variable | VIF | severity |
|---|---|---|
| final_humor_binary | 1.1296 | acceptable |
| created_year | 3.675 | acceptable |
| created_month | 1.1277 | acceptable |
| created_hour | 1.0063 | acceptable |
| text_length | 1.0318 | acceptable |
| log1p_view_count | 3.6828 | acceptable |

---

## 7. Condition Number 및 Rank Deficiency (primary n=597)

| model_set | n_cols | rank | deficient | condition_number | severity |
|---|---|---|---|---|---|
| A_time_only | 5 | 5 | False | 1.49 | acceptable |
| B_time_posting_intensity | 7 | 7 | False | 3.7 | acceptable |
| C_time_posting_format | 14 | 14 | False | 3.89 | acceptable |
| D_exposure_robustness | 7 | 7 | False | 3.8 | acceptable |


---

## 8. 다중공선성 위험 변수

- 심각한 다중공선성 없음

- **created_year** × **log1p_view_count**: r=0.8392 (serious)
- **quarter_total_posts** × **month_total_posts**: r=0.8264 (serious)


---

## 9. Primary Model에서 사용 가능한 변수 세트

**[사용자 승인 필요]** 다음은 제안이며 확정이 아니다.

```
반드시 유지:
  final_humor_binary       ← H1 핵심 IV
  created_year             ← 시간 추세 통제
  created_hour             ← 시간대 통제
  text_length              ← 게시글 길이 통제
  is_quote_status          ← 포맷 통제 (0 비율 확인 필요)
  is_retweet_text          ← 포맷 통제 (0 비율 확인 필요)
```

```
quarter_total_posts / month_total_posts 중 하나만 선택:
  → VIF 결과와 correlation 기준으로 둘 중 하나만 포함 권장
  → quarter_total_posts: H3와 일관된 period 단위
  → 사용자 선택 필요
```

```
created_month:
  → month_total_posts와 상관 확인 후 결정
  → 필요 시 created_month 제거하고 quarter_total_posts만 유지
```

---

## 10. Robustness Model로만 사용할 변수 세트

```
log1p_view_count:
  → 노출 통제 목적, primary model에서는 제외
  → view_count가 0인 경우 log1p 적용 후 0이 되므로 결측 처리가 아님
  → robustness only

url_count, mention_count, hashtag_count, emoji_count:
  → text_length와 함께 전부 넣을 경우 상관관계 주의
  → 필요 시 text_length 대신 url_count + mention_count 선택 가능
  → 개별 또는 묶음으로 robustness 확인
```

---

## 11. 사용자 승인 필요한 선택지

| 선택지 | 옵션 1 | 옵션 2 | 비고 |
|---|---|---|---|
| posting intensity | quarter_total_posts만 | month_total_posts만 | 둘 다 넣으면 VIF 상승 위험 |
| created_month | 포함 | 제외 | month_total_posts와 상관 확인 |
| text_length vs 개별 format | text_length 단독 | url+mention+hashtag 개별 | text_length 단독 권장 |
| is_quote_status, is_retweet_text | 포함 | 제외 (zero_rate 주의) | 0 비율이 매우 높으면 제외 권장 |
| log1p_view_count | primary 포함 | robustness only | 노출 통제 필요성 선택 |
| created_year vs created_month | 둘 다 | created_year만 | 동시 포함 시 VIF 확인 |

---

## 12. 회귀분석 수행 여부

이번 작업에서는 H1 회귀분석을 수행하지 않았다.

---

## 13. 새 변수 생성 여부

이번 작업에서는 새로운 변수를 생성하지 않았다. 기존 컬럼으로 존재하는 변수만 사용하였다. day_of_week, has_url 등 텍스트 파생 변수는 생성하지 않았다.

---

## 14. 원본 posts.json 변경 없음 확인

`data/wendys/posts.json` 변경 여부: False

---

*생성일: 2026-06-15*
