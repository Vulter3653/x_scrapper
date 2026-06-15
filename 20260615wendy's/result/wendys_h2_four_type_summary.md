# Wendy's H2 기준 4가지 Humor Type 비교 분석 결과

## 1. 작업 목적

본 분석은 기존 H2의 aggressive vs other_humor 비교를 네 가지 humor type으로 세분화한 exploratory decomposition이다.
기존 H2를 대체하는 것이 아니라, 세분화 분석을 통해 어떤 유형 간 차이가 H2를 주도하는지 확인하는 것이 목적이다.

## 2. 사용 데이터

- `20260615wendy's/result/wendys_humor_review_sheet.csv`
- `20260615wendy's/data/wendys_fast_weak_supervised_humor_dataset.csv`
- 사람 기반 final_humor_type 라벨 (coder1 > human > coder2 우선순위)

## 3. 분석 표본 구성

| 유형 | 건수 |
|---|---|
| aggressive | 95건 |
| affiliative | 106건 |
| self-enhancing | 62건 |
| self-defeating | 15건 |
| **합계** | **278건** |

제외: non_humor=288건, missing_type=31건, unlabeled=381건

**small_cell_warning: True** — self-defeating 15건(<20건)이므로 해당 비교는 매우 제한적으로 해석해야 한다.

## 4. 네 가지 humor type 분포

| 유형 | n | mean_log1p_engagement_total |
|---|---|---|
| aggressive | 95 | 8.3411 |
| affiliative | 106 | 7.6505 |
| self-enhancing | 62 | 7.4835 |
| self-defeating | 15 | 8.1366 |


## 5. Type별 평균 engagement

primary DV (log1p_engagement_total) 기준: aggressive=8.341, affiliative=7.651, self-enhancing=7.483, self-defeating=8.137

## 6. 네 type 평균 차이 검정

one-way ANOVA 및 Kruskal-Wallis 검정 결과는 `wendys_h2_four_type_mean_comparison.csv` 참조.

## 7. Aggressive vs 각 type pairwise 비교

### aggressive vs affiliative (primary DV: log1p_engagement_total)
diff=0.6906, p_raw=0.0043**, p_fdr=0.0103*, d=0.4109 (small)

### aggressive vs self-enhancing
diff=0.8576, p_raw=0.0009***, p_fdr=0.0039**, d=0.5250 (medium)

### aggressive vs self-defeating
diff=0.2045, p_raw=0.6823, p_fdr=0.7443, d=0.1150 (negligible)
⚠ self-defeating n=15건 < 20 — 해당 결과는 탐색적 참고로만 해석해야 한다.

다중비교 보정: Bonferroni 및 Benjamini-Hochberg FDR 보정 포함.
다중 pairwise 비교가 수행되었으므로, raw p-value뿐 아니라 FDR 또는 Bonferroni 보정 결과를 함께 확인해야 한다.

## 8. Humor-only OLS 결과 (base=affiliative, log1p_engagement_total)

| 비교 | β | p |
|---|---|---|
| aggressive vs affiliative | 0.6906 | 0.0028** |
| self-enhancing vs affiliative | -0.1670 | 0.5203 |
| self-defeating vs affiliative | 0.4861 | 0.2785 |
| R² | 0.0482 | |

OLS pairwise contrasts (log1p_engagement_total):
- aggressive − self-enhancing: est=0.8576, p=0.0014**
- aggressive − self-defeating: est=0.2045, p=0.6506

## 9. 기존 pooled H2와의 관계

이번 4-type 데이터셋 내에서 aggressive vs pooled other_humor (affiliative+self-enhancing+self-defeating) 재계산 결과:
- diff=0.7074, p=0.0012**

기존 human-labeled H2 (n=278): diff=+0.7074, p=0.0012**

두 분석이 동일한 데이터 기반이므로 수치는 일치해야 한다.

## 10. 해석상 주의사항

본 분석은 기존 H2의 aggressive vs other_humor 비교를 네 가지 humor type으로 세분화한 exploratory decomposition이다.

self-defeating 유형은 표본 수가 작을 가능성이 높으므로, 해당 비교 결과는 매우 제한적으로 해석해야 한다.

본 분석은 관측적 연관성 분석이며, humor type이 engagement를 증가시켰다는 인과적 해석은 할 수 없다.

다중 pairwise 비교가 수행되었으므로, raw p-value뿐 아니라 FDR 또는 Bonferroni 보정 결과를 함께 확인해야 한다.

## 11. 원본 데이터 보호 확인

- `data/wendys/posts.json`: 수정 없음
- 기존 H2 결과 파일: 수정 없음
- 모든 산출물은 `20260615wendy's/` 내부에만 생성됨
