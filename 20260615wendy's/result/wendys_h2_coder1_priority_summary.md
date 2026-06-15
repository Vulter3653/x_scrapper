# Wendy's H2 결과: coder1 우선순위 final_humor_type 기준

## 1. 작업 목적

본 분석은 coder1 > human > coder2 우선순위로 생성된 최신 final_humor_type_group을 기준으로 H2를 재검증하였다.
기존 H2 결과(aggressive=90, other_humor=219)는 final_humor_source 기반으로 type을 결정하였으므로 더 이상 최신 기준이 아니다.

## 2. H2 가설

H2: Wendy's 브랜드 게시글에서 aggressive humor는 다른 유머 유형보다 post-level engagement가 더 높을 것이다.

해석: aggressive humor 게시글은 other humor 게시글보다 engagement가 높게 나타나는지 확인한다.
본 분석은 관측적 연관성 분석이며, 인과관계를 주장하지 않는다.

## 3. 사용 데이터

- 입력: `20260615wendy's/result/wendys_humor_review_sheet.csv`
- engagement: `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv`
- H2 dataset: `20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv`

## 4. 최신 humor type 기준

| 기준 | 이전 (final_humor_source 기반) | 최신 (coder1 우선순위) |
|---|---|---|
| aggressive | 90건 | 95건 |
| other_humor | 219건 | 183건 |

H2 분석에서 non_humor 기준범주는 final_humor_label_available = 1인 사람 라벨 표본 안에서만 구성하였다. 라벨이 없는 381건은 H2 primary 분석에서 non_humor로 간주하지 않았다.

## 5. 분석 표본

| 집단 | 건수 |
|---|---|
| 전체 게시글 | 978건 |
| labeled sample (final_humor_label_available=1) | 597건 |
| aggressive | 95건 |
| other_humor | 183건 |
| non_humor (labeled) | 288건 |
| humor_missing_type | 31건 |
| unlabeled | 381건 |

humor_missing_type 31건은 aggressive vs other_humor 직접 비교에서 제외하였다.

## 6. 분석 1: aggressive vs other_humor t-test

- 검정: Welch's independent samples t-test (two-sided, 등분산 가정 없음)
- 주요 DV: log1p_engagement_total
- 대상: aggressive=95건 vs other_humor=183건

| 지표 | 값 |
|---|---|
| 평균 차이 (aggressive − other_humor) | 0.7074 |
| p-value | 0.0012 ** |
| Cohen's d | 0.4359 (small) |
| H2 해석 | **H2 예비적 지지** |

## 7. 분석 2: humor-only simple OLS

- IV: aggressive_humor (1=aggressive, 0=other_humor)
- 표본: aggressive + other_humor (278건)
- 주요 DV: log1p_engagement_total

| 지표 | 값 |
|---|---|
| β (aggressive) | 0.7074 |
| p-value | 0.0007 *** |
| R² | 0.0413 |
| H2 해석 | **H2 예비적 지지** |

## 8. 분석 3: labeled sample multi-dummy OLS

- 기준범주: non_humor (labeled, 288건)
- 표본: aggressive + other_humor + non_humor (566건)
- 주요 DV: log1p_engagement_total

| 지표 | 값 |
|---|---|
| β₁ (aggressive vs non_humor) | 1.0715 (p=0.0000***) |
| β₂ (other_humor vs non_humor) | 0.3642 (p=0.0230*) |
| β₁ − β₂ | 0.7074 (p=0.0012**) |
| H2 해석 | **H2 예비적 지지** |

## 9. 종합 해석

세 가지 분석 모두에서 aggressive humor 게시글은 other humor 게시글보다 log1p_engagement_total이 높게 나타났다.
t-test 차이, simple OLS β, multi-dummy OLS β₁−β₂ 모두 방향성이 일치한다.
통계적 유의성은 각 분석의 p-value로 확인할 수 있다.

단, 본 분석은 관측적 연관성 분석이므로 aggressive humor가 engagement를 증가시킨다는 인과관계를 주장할 수 없다.

## 10. 한계

- 본 분석은 Wendy's 단일 브랜드 게시글만 대상으로 한다.
- H2는 final_humor_type에 의존하므로 유머 타입 코딩 품질에 민감하다.
- 코더 간 type 불일치 가능성이 있으므로 결과는 예비적으로 해석해야 한다.
- 통제변수와 고정효과가 없는 단순 분석이다.
- 관측적 연관성 분석이므로 인과관계를 주장할 수 없다.
- type missing인 유머 게시글은 aggressive vs other_humor 직접 비교에서 제외되었다.
