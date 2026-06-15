# Wendy's final_humor_type 정리 결과 (coder1 우선순위)

## 작업 개요
- `final_humor_type`을 `final_humor_source`와 **무관하게** coder1 → human → coder2 우선순위로 재생성함.
- 신규 컬럼 3개 추가: `final_humor_type_source`, `final_humor_type_available`, `final_humor_type_group`

## 행 수 요약
- 전체: **978건**
- 유머 (final_humor_binary=1): **309건**
- 비유머 (final_humor_binary=0): **669건**

## final_humor_type 분포 (유머 행 기준)
- affiliative: **106건**
- aggressive: **95건**
- self-enhancing: **62건**
- self-defeating: **15건**
- 타입 없음 (missing): **31건**

## final_humor_type_source 분포 (유머 행 기준)
- coder1: **173건**
- human: **0건**
- coder2: **105건**
- missing: **31건**

## final_humor_type_group 분포 (전체)
- aggressive: **95건**
- other_humor: **183건**
- non_humor: **669건**
- missing: **31건**

## type 정규화 수정 건수
- coder1_type: 0건
- human_type: 0건
- coder2_type: 0건

## final_humor_type 변경 건수
- 이전(final_humor_source 기반) 대비 변경: **684건**

## H2 분석 시사점
- aggressive 그룹: **95건** → H2 t-test 대상
- other_humor 그룹: **183건** → 비교 기준
- non_humor 및 missing 행은 H2 분석에서 제외됨.

## 출처
- 입력: `wendys_humor_review_sheet.csv`
- Audit: `wendys_final_humor_type_coder1_priority_audit.csv`
- 스크립트: `normalize_wendys_final_humor_type_coder1_priority.py`