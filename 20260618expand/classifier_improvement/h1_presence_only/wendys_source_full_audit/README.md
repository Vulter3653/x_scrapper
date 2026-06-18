# Wendy's Humor Label Source Full Audit

## 목적

repo 전체에서 Wendy's humor presence / humor type 라벨 파일과 분류 산출물을 전수조사하여
슬라이드 숫자(987/564/414/187/251/96/30/597)의 출처와 불일치 원인을 확인한다.

## 실행

```bash
python -m py_compile scripts/audit_wendys_humor_label_sources.py
python scripts/audit_wendys_humor_label_sources.py
```

## 산출물 목록

| 파일 | 내용 |
|---|---|
| `diagnostics/wendys_file_inventory.csv` | 399개 후보 파일 전수 목록 (schema/count/column) |
| `diagnostics/wendys_presence_distribution_by_file.csv` | presence label 분포 (58개 컬럼 분석) |
| `diagnostics/wendys_type_distribution_by_file.csv` | type label 분포 (24개 컬럼 분석) |
| `diagnostics/wendys_slide_number_match_audit.csv` | 슬라이드 숫자와 파일별 매칭 결과 |
| `diagnostics/wendys_cross_file_overlap_audit.csv` | 파일 간 tweet_id/text 중복 분석 |
| `diagnostics/wendys_audit_summary.csv` | 핵심 결론 요약 |

## 핵심 결론

### 597건 코딩

- 파일: `20260615wendy's/data/wendys_final_humor_presence_dataset.csv`
- 내용: 수동 코딩 최종 (coder1 우선순위) presence label
- 분포: humor=309 / non_humor=288

### 987건 전체 데이터

- **repo 내 존재하지 않음** (978이 실제 raw 수집 수)
- 원본: `20260615wendy's/data/wendys_posts_raw.json` → 978 posts
- 987은 dedup 전 수집 수로 추정 (9건 중복 제거 → 978)

### Humor 564 / Non Humor 414

- **모델 예측 결과** (manual label 아님)
- 출처: `pred_humor_final_050` 컬럼 (978-row h1 데이터셋 다수에 공통)
- 해당 컬럼: 978개 전체 포스트에 대한 t50 기준 이진 분류 예측값
- 확인 파일: `20260615wendy's/result/wendys_full_sample_four_type_humor_distribution.csv`
- 564 + 414 = 978 (not 987)

### 987 - 978 = 9건 불일치 원인

- 슬라이드 987은 dedup 전 raw 수집 수
- repo 내 실제 raw 수 = 978
- 차이 9건 = 중복 제거된 포스트 수

### Humor Type 187/251/96/30

- **전체 샘플 four-type 분류기 예측 결과** (manual label 아님)
- 출처: `20260615wendy's/result/wendys_full_sample_four_type_humor_distribution.csv`
- 컬럼: `pred_full_4type_count`
- 978개 전체 포스트 → 564 humor 예측 → 각 type 분류
- aggressive=187 / affiliative=251 / self-enhancing=96 / self-defeating=30 = 564

### 수동 코딩 type label (실제 human labels)

- **파일**: `20260615wendy's/data/wendys_h2_four_type_humor_dataset.csv` (278 rows)
- **파일**: `20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv` (597 rows, type 컬럼 포함)
- 분포: aggressive=95 / affiliative=106 / self-enhancing=62 / self-defeating=15 = 278
- 이 숫자가 실제 인간 코딩 type 라벨 수

### Type classifier 학습에 사용 가능한 파일

| 파일 | rows | type 컬럼 | 비고 |
|---|---|---|---|
| `wendys_h2_four_type_humor_dataset.csv` | 278 | final_humor_type | humor 포스트만, 수동 코딩 |
| `wendys_full_sample_four_type_humor_classifier_dataset.csv` | 278 | label | 동일 278 rows, 학습용 형식 |
| `wendys_h2_coder1_priority_dataset.csv` | 597 | final_humor_type | 전체 597 rows, non_humor 포함 |

## 주의

- 이 작업은 scraping, model training, integrated corpus reclassification을 하지 않음
- 모든 파일은 read-only로 분석
- 슬라이드의 187/251/96/30 은 model prediction이며 human label이 아님
- type classifier 보강 시 반드시 `final_humor_type` 컬럼 기반 human-coded 278 rows를 사용할 것
