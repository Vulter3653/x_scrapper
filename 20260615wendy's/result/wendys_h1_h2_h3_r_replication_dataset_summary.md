# Wendy's H1-H2-H3 R 재현용 데이터셋 (v2 — 한글 컬럼명)

작성일: 2026-06-16 (v2 재구성)

---

## 1. 작업 목적
최종 보고서 분석 변수를 단일 wide-format CSV로 통합. 컬럼명을 한글로 변경하여
연구자가 R에서 `df$좋아요수` 형태로 직접 참조할 수 있도록 구성함.

## 2. 최종 보고서 경로
`20260615wendy's/result/wendys_humor_h1_h2_h3_final_report.md`

## 3. 사용한 입력 파일
| 파일 | rows | 역할 |
|---|---|---|
| `result/wendys_final_humor_presence_full_predictions.csv` | 978 | H1 IV, 인간 레이블 |
| `result/wendys_model_based_humor_type_full_predictions.csv` | 978 | H2 유머 유형 |
| `data/wendys_fast_weak_supervised_humor_dataset.csv` | 978 | post format controls |
| `data/wendys_humor_frequency_proportion_post_level_dataset.csv` | 978 | H3-pre predictor |
| `data/wendys_h3_aggressive_vs_other_intensity_dataset.csv` | 978 | base (원시집계, 시간변수, H3 main/other predictor) |

## 4. 병합 안정성
- 병합 key: `id` (978개 고유, dup=0, NA=0 — 전 파일 동일)
- 모든 병합: 1:1 left join, 978→978 유지

## 5. 최종 dataset
- rows: **978**
- cols: **36**

## 6. 컬럼 목록
- `게시물ID` (1)
- `트윗URL` (2)
- `트윗텍스트` (3)
- `답글수` (4)
- `좋아요수` (5)
- `리트윗수` (6)
- `인용수` (7)
- `북마크수` (8)
- `조회수` (9)
- `작성일` (10)
- `작성연도` (11)
- `작성월` (12)
- `작성시간` (13)
- `연도분기` (14)
- `유머예측이진` (15)
- `유머확률모델` (16)
- `인간레이블가용` (17)
- `유머레이블최종` (18)
- `유머유형모델예측` (19)
- `공격적유머여부` (20)
- `기타유머여부` (21)
- `유머유형최종` (22)
- `텍스트길이` (23)
- `해시태그수` (24)
- `멘션수` (25)
- `분기게시물수` (26)
- `H3분기필터` (27)
- `유머비율LOO분기` (28)
- `공격적유머비율LOO분기` (29)
- `기타유머비율LOO분기` (30)
- `H1인간검증표본` (31)
- `H2모델유머표본` (32)
- `H2인간검증표본` (33)
- `H3분석표본` (34)
- `H2공격적유머모델더미` (35)
- `H2공격적유머인간더미` (36)

## 7. R에서 파생 변수 계산 (R 스크립트 내)
```r
# 종속변수 (log1p 변환)
df$참여도합계     <- log1p(df$좋아요수 + df$리트윗수 + df$답글수 + df$인용수 + df$북마크수)
# H3 이차항
df$유머비율LOO분기제곱       <- df$유머비율LOO분기^2
df$공격적유머비율LOO분기제곱 <- df$공격적유머비율LOO분기^2
df$기타유머비율LOO분기제곱   <- df$기타유머비율LOO분기^2
```

## 8. 제외 변수 확인
log1p_view_count, emoji_count, url_count, is_quote_status, is_retweet_text,
day_of_week, month_total_posts, frequency count 변수, year_quarter FE dummy
→ 전부 미포함 확인

## 9. 검증 결과
| 조건 | 실제값 | 기대값 |
|---|---|---|
| rows | 978 | 978 |
| H1인간검증표본 합계 | 597 | 597 |
| H2모델유머표본 합계 | 564 | 564 |
| H2공격적유머모델더미=1 | 200 | 200 |
| H2공격적유머모델더미=0 | 364 | 364 |
| H2인간검증표본 합계 | 278 | 278 |
| H2공격적유머인간더미=1 | 95 | 95 |
| H2공격적유머인간더미=0 | 183 | 183 |
| H3분석표본 합계 | 960 | 960 |
| H3 unique 분기 | 25 | 25 |

## 10. 주의사항
- 조회수(view_count)는 참고용으로만 포함; 회귀분석에 사용하지 않음
- 리트윗수는 참여도합계 계산에 필수 (사용자 열 목록에 없었으나 DV 계산상 포함)
- H2 더미 변수: 비유머 행은 NA → subset() 조건 필수
- H3: factor(연도분기) 사용 금지 (LOO 변수와 동일 수준)
- posts.json 변경 없음 / 새 회귀분석 미수행 / 새 분류 모델 미학습
