# Wendy's 기존 변수 Inventory 요약

## 1. 검토한 파일 목록

| 파일 | rows | cols |
|---|---|---|
| wendys_final_humor_presence_full_predictions.csv | 978 | 14 |
| wendys_fast_weak_supervised_humor_dataset.csv | 978 | 47 |
| wendys_humor_review_sheet.csv | 978 | 27 |
| wendys_h2_coder1_priority_dataset.csv | 597 | 28 |
| wendys_humor_frequency_proportion_post_level_dataset.csv | 978 | 45 |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | 978 | 65 |

---

## 2. 파일별 row/column 수

| 파일명 | rows | cols |
|---|---|---|
| wendys_final_humor_presence_full_predictions.csv | 978 | 14 |
| wendys_fast_weak_supervised_humor_dataset.csv | 978 | 47 |
| wendys_humor_review_sheet.csv | 978 | 27 |
| wendys_h2_coder1_priority_dataset.csv | 597 | 28 |
| wendys_humor_frequency_proportion_post_level_dataset.csv | 978 | 45 |
| wendys_h3_aggressive_vs_other_intensity_dataset.csv | 978 | 65 |

---

## 3. H1에 이미 존재하는 변수 후보

### A. 핵심 DV/IV

| 역할 | 변수 | 소스 파일 | missing_rate |
|---|---|---|---|
| DV (primary) | log1p_engagement_total | h3_aggressive_vs_other_dataset | 0 |
| DV (secondary) | log1p_favorite_count, log1p_retweet_count 등 | h3_aggressive_vs_other_dataset | 0 |
| IV (human) | final_humor_binary | final_humor_presence_full_predictions | 0 |
| IV (human filter) | final_humor_label_available | final_humor_presence_full_predictions | 0 |
| IV (model) | pred_humor_final_050 | h3_aggressive_vs_other_dataset | 0 |
| IV (prob) | p_humor_final_tfidf_logreg | h3_aggressive_vs_other_dataset | 0 |

### B. 시간 변수 (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| created_year | ✓ | h3_aggressive_vs_other_dataset |
| created_month | ✓ | h3_aggressive_vs_other_dataset |
| created_day | ✓ | h3_aggressive_vs_other_dataset |
| created_time | ✓ | h3_aggressive_vs_other_dataset |
| created_hour | ✓ | h3_aggressive_vs_other_dataset |
| created_date | ✓ | h3_aggressive_vs_other_dataset |
| year_month | ✓ | h3_aggressive_vs_other_dataset |
| year_quarter | ✓ | h3_aggressive_vs_other_dataset |
| **day_of_week** | **✗** | **존재하지 않음 — 이번 작업에서 생성하지 않음** |

### C. Posting intensity (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| quarter_total_posts | ✓ | h3_aggressive_vs_other_dataset |
| month_total_posts | ✓ | h3_aggressive_vs_other_dataset |
| day_total_posts | ✗ | 존재하지 않음 |

### D. Post format (기존 컬럼으로 존재 — wendys_fast_weak_supervised_humor_dataset.csv)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| text_length | ✓ | fast_weak_supervised dataset에만 존재, H3 dataset과 통합 필요 |
| url_count | ✓ | 동일 |
| mention_count | ✓ | 동일 |
| hashtag_count | ✓ | 동일 |
| emoji_count | ✓ | 동일 |
| is_quote_status | ✓ | 동일 |
| is_retweet_text | ✓ | 동일 |

**주의: 위 변수들은 wendys_fast_weak_supervised_humor_dataset.csv에 존재하며, 978건 기준 H3 dataset과 id 기준 병합이 필요하다. 이번 작업에서 병합하지 않았다.**

### E. Exposure (기존 컬럼으로 존재)

| 변수 | 존재 여부 | 비고 |
|---|---|---|
| view_count | ✓ | h3_aggressive_vs_other_dataset, 결측 또는 0 주의 |
| log1p_view_count | ✓ | h3_aggressive_vs_other_dataset |

---

## 4. H2에 이미 존재하는 변수 후보

### 사람 코딩 타입 라벨 (h2_coder1_priority_dataset.csv, 597건)

| 변수 | n_non_missing | 비고 |
|---|---|---|
| final_humor_type | 566 | 4-type 라벨 |
| final_humor_type_group | 597 | aggressive/other_humor/non_humor |
| aggressive_humor | 95 | binary dummy |
| other_humor_flag | 183 | binary dummy |

### H2 사람 코딩 타입 분포

```
H2 human-labeled type_group (type_available=1 기준):
aggressive=95, other_humor=183

H2 model-based (978건 기준):
non_humor=414, aggressive=200, other_humor=364

H2 4-type human (review_sheet, type_available=1 기준):
affiliative=106, aggressive=95, self-defeating=15, self-enhancing=62
```

### 모델 기반 타입 변수 (978건)

| 변수 | 비고 |
|---|---|
| pred_humor_type_group_model | aggressive/other_humor/non_humor |
| p_type_aggressive_model | 확률값 |
| p_type_other_humor_model | 확률값 |
| is_aggressive_humor | binary dummy |
| is_other_humor | binary dummy |

---

## 5. H3에 이미 존재하는 변수 후보

| 변수 | 존재 여부 | min | max | mean | 비고 |
|---|---|---|---|---|---|
| humor_proportion_quarter_loo | ✓ | 0.0 | 1.0 | ~0.58 | H3-pre primary LOO, quarter FE 식별 불가 |
| aggressive_humor_proportion_quarter_loo | ✓ | 0.0 | 0.3377 | ~0.21 | H3-main primary LOO, quarter FE 식별 불가 |
| other_humor_proportion_quarter_loo | ✓ | 0.0 | 0.6667 | ~0.37 | H3-main 보조 predictor |
| aggressive_share_among_humor_quarter_loo | ✓ | 0.0 | 1.0 | ~0.37 | H3-main 보조 predictor |
| humor_frequency_quarter | ✓ | — | — | — | H3-pre frequency |
| aggressive_humor_frequency_quarter | ✓ | — | — | — | H3-main frequency |
| quarter_total_posts | ✓ | — | — | — | period-level denominator |
| year_quarter | ✓ | — | — | — | period 식별자 (FE 사용 금지) |

---

## 6. 새로 생성하지 말아야 하는 변수 목록

다음 변수들은 이미 컬럼으로 존재하므로 새로 계산하지 않아도 된다.

```
text_length, url_count, mention_count, hashtag_count, emoji_count
is_quote_status, is_retweet_text
log1p_engagement_total, log1p_*_count
view_count, log1p_view_count
humor_proportion_quarter_loo, aggressive_humor_proportion_quarter_loo
month_total_posts, quarter_total_posts
created_year, created_month, created_day, created_hour
```

---

## 7. 결측률이 높아 사용 주의가 필요한 변수

| 변수 | 파일 | missing_rate |
|---|---|---|
| human_type | wendys_humor_review_sheet.csv | 0.9611 |
| coder2_type | wendys_humor_review_sheet.csv | 0.8609 |
| human_humor_label | wendys_humor_review_sheet.csv | 0.8292 |
| human_humor_binary | wendys_humor_review_sheet.csv | 0.8292 |
| weak_humor_label | wendys_fast_weak_supervised_humor_dataset.csv | 0.8221 |
| coder1_type | wendys_humor_review_sheet.csv | 0.8221 |
| coder1_humor | wendys_humor_review_sheet.csv | 0.7444 |
| coder1_humor_binary | wendys_humor_review_sheet.csv | 0.7444 |
| view_count | wendys_fast_weak_supervised_humor_dataset.csv | 0.6483 |
| coder2_humor_binary | wendys_humor_review_sheet.csv | 0.5869 |
| coder2_humor | wendys_humor_review_sheet.csv | 0.5276 |
| final_humor_binary | wendys_final_humor_presence_full_predictions.csv | 0.3896 |
| final_humor_source | wendys_final_humor_presence_full_predictions.csv | 0.3896 |
| final_humor_binary | wendys_humor_review_sheet.csv | 0.3896 |
| final_humor_source | wendys_humor_review_sheet.csv | 0.3896 |


view_count 및 log1p_view_count는 0 또는 결측이 다수 포함될 수 있으므로 노출 통제 시 주의가 필요하다.

---

## 8. Primary model에 바로 넣으면 위험한 변수

| 변수 | 이유 |
|---|---|
| year_quarter (FE) | humor_proportion_quarter_loo / aggressive_humor_proportion_quarter_loo와 동시에 사용 시 식별 불가 |
| engagement_total (log 미변환) | 우편향 분포, log1p 변환 필요 |
| view_count | 다른 engagement DV와 다중공선성 가능, 노출 통제 변수 역할로만 사용 권장 |
| p_humor_final_tfidf_logreg | pred_humor_final_050과 함께 사용 시 다중공선성 |
| humor_score (fast_ds) | 초기 weak supervised 점수, 최종 모델 예측값과 다른 개념 |
| text_length, url_count 등 | fast_ds와 H3 dataset 병합 전까지 직접 사용 불가 |

---

## 9. 다음 단계에서 사용자 승인이 필요한 변수

1. **통제변수 병합**: text_length, url_count 등 fast_ds에만 있는 변수를 H3 dataset에 병합할지 여부
2. **day_of_week**: created_date에서 계산 가능하나 이번 작업에서 생성하지 않음 — 필요 여부 확인 필요
3. **view_count 통제**: H1 regression에서 log1p_view_count를 노출 통제변수로 포함할지 여부 (결측 처리 방식 포함)
4. **H2 표본 기준**: 사람 코딩 type_available=1 기준 인원 수 확인 후 H2 controlled regression 수행 여부

---

## 10. 원본 파일 변경 여부 확인

- `data/wendys/posts.json` 변경 여부: False
- 기존 H1/H2/H3 결과 파일 수정 없음

---

*생성일: 2026-06-15*
