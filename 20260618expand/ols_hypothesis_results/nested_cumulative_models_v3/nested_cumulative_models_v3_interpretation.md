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

## H3: Firm-quarter inverted-U (Full-sample)

| Model | β₁ | β₂ | TP | H3 |
|:------|---:|---:|---:|:---:|
| Model 1 | 12.619846*** | -11.257243*** | 0.560521 | True |
| Model 2 | 9.483818*** | -10.338158*** | 0.45868 | True |
| Model 3 | 9.079711*** | -9.465466*** | 0.479623 | True |
| Model 4 | 0.381347 | -0.548842 | 0.347411 | False |

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