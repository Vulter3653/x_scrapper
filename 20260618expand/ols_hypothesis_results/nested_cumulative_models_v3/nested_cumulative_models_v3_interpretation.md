# Nested Cumulative Models — Interpretation

> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2 + coder2 batch2 URL fallback)

## Model structure

| | Model 1 | Model 2 | Model 3 | Model 4 |
|:---|:---|:---|:---|:---|
| Humor vars | ✓ | ✓ | ✓ | ✓ |
| Controls | — | ✓ | ✓ | ✓ |
| Time FE (Year+Month / Year+QoY) | — | — | ✓ | ✓ |
| Company dummies (ref=Amazon) | — | — | — | ✓ |

- H1/H2 Full-sample N = 68,039  |  HC N = 3,574 (3074 direct + 500 URL-sid recovered)
- H3 Full-sample firm-quarters = 1,420  |  HC = 925

## H1: Weighted Humor Effect (Full-sample)

| Model | estimate | stars | support |
|:------|--------:|:-----:|:-------:|
| Model 1 | 1.166525 | *** | supported |
| Model 2 | 1.15332 | *** | supported |
| Model 3 | 1.109234 | *** | supported |
| Model 4 | 0.221485 | *** | supported |

## H2-1: Aggressive vs Other humor (Full-sample)

| Model | estimate | stars | support |
|:------|--------:|:-----:|:-------:|
| Model 1 | 0.849484 | *** | supported |
| Model 2 | 0.791973 | *** | supported |
| Model 3 | 0.820063 | *** | supported |
| Model 4 | 0.113958 | *** | supported |

## H2-2: Aggressive vs SELF humor (Full-sample)

| Model | estimate | stars | support |
|:------|--------:|:-----:|:-------:|
| Model 1 | 0.438443 | *** | supported |
| Model 2 | 0.414448 | *** | supported |
| Model 3 | 0.479996 | *** | supported |
| Model 4 | 0.10562 | *** | supported |

## H2 Overall Judgment

H2 is strongly but partially supported. Aggressive humor generates significantly higher engagement than other humor types in aggregate (H2-1, H2-2), but self-defeating humor outperforms aggressive humor in pairwise comparison across all models in the full sample.

H2는 강한 부분 지지로 해석된다. Aggressive humor는 other humor 및 SELF 범주와의 집합적 비교에서는 유의하게 높은 engagement를 보였지만, full-sample의 개별 pairwise 비교에서는 self-defeating humor가 aggressive humor보다 더 높은 engagement를 보였다.

### HC H2-3 Note

Unlike the full-sample results, the human-coded sample shows a positive Aggressive − Self-Defeating contrast in some models. This difference should be interpreted cautiously because the human-coded sample is smaller and may reflect sample composition.

Full-sample과 달리 human-coded sample에서는 일부 모델에서 Aggressive − Self-Defeating contrast가 양수로 나타났다. 이는 표본 크기와 표본 구성 차이에 따른 결과일 수 있으므로 신중하게 해석한다.

## H3: Firm-quarter inverted-U (Full-sample)

| Model | β₁ | β₂ | TP | H3 |
|:------|---:|---:|---:|:---:|
| Model 1 | 12.619846*** | -11.257243*** | 0.560521 | True |
| Model 2 | 9.483818*** | -10.338158*** | 0.45868 | True |
| Model 3 | 9.079711*** | -9.465466*** | 0.479623 | True |
| Model 4 | 0.381347 | -0.548842 | 0.347411 | False |

### H3 Model 4 Note

The disappearance of the inverted-U relationship in Model 4 suggests that the H3 pattern is driven by between-firm heterogeneity: firms that post more aggressively tend to have systematically higher engagement levels, rather than aggressive humor generating a within-firm inverted-U over time.

Model 4에서 역U자형 관계가 사라진 것은 H3 패턴이 기업 내 시계열 변화라기보다 기업 간 이질성(between-firm heterogeneity)에 의해 주도되었을 가능성을 시사한다. 즉, 공격적 유머를 더 많이 사용하는 기업들이 체계적으로 더 높은 engagement 수준을 보였을 수 있다.

## H3: Firm-quarter inverted-U (Human-coded)

| Model | β₁ | β₂ | TP | H3 |
|:------|---:|---:|---:|:---:|
| Model 1 | 7.349*** | -6.253*** | 0.5877 | True |
| Model 2 | 4.226*** | -3.176* | 0.6652 | True (marginal) |
| Model 3 | 3.225** | -2.035 | 0.7922 | False |
| Model 4 | 0.196 | -0.426 | 0.2295 | False |

### H3 Human-coded Model 2 Note

Human-coded H3 Model 2 is supported only at the 10% significance level because β₂ is marginally significant (p = 0.077).

Human-coded H3 Model 2는 β₂가 p=0.077로 10% 유의수준에서만 한계적으로 유의하므로, 강한 지지가 아니라 marginal support로 해석한다.

## H1/H2 Human-coded (Model 4 full spec)

- Weighted Humor Effect (vs non-humorous): 0.218941*** (supported)
- Aggressive − Other humor (weighted avg): 0.333472*** (supported)
- Aggressive − SELF (se+sd weighted avg): 0.355166*** (supported)

## Notes

- Model 4 is the full specification. Humor effects in Model 4 are identified from within-firm, within-time variation.
- Controls (text_length, hashtag_count, mention_count) test whether humor-engagement association is confounded by content format.
- Time FE (Year+Month) absorbs platform-wide temporal trends. Year+QoY for H3 firm-quarter.
- Company dummies absorb firm-level heterogeneity (follower size, account characteristics).
- coder2 Batch2 500건: Excel 정밀도 손상으로 tweet_id 직접 매칭 실패 → URL status_id fallback으로 전량 복구.
- All OLS uses classical SE: s² = SSR/(n−k), Var(β̂) = s²(X'X)⁻¹.