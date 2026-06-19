# Time Dummy Combination Models — Interpretation (Model 3)

> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2)

## Model specification

$$\log(1+\text{Engagement}_i) = \beta_0 + \beta_1\text{Agg}_i + \beta_2\text{Aff}_i + \beta_3\text{SE}_i + \beta_4\text{SD}_i+ \sum_t \tau_t\text{TimeDummy}_{it} + \varepsilon_i$$

- FWL (Frisch-Waugh-Lovell) + iterative within-group demeaning
- Classical OLS SE: s²=SSR/(n−k). No company dummies. No controls.
- Post-level N = 68,039  |  HC N = 3,574  |  Firm-quarter N = 1,420
- Time fields: year (L=14), month (L=12), week (L=53), date (L=3597), hour (L=24)

## Execution summary

| Item | Count |
|:----|------:|
| H1/H2 combos attempted | 31 |
| H1/H2 full-sample succeeded | 31 |
| H1/H2 skipped (infeasible) | 0 |
| H3 combos | 4 |
| Rank-deficient combos (Date+Year/Month/Week) | 14 |

## H1 consistency across time dummy combinations

**H1 supported in 31 / 31 full-sample combinations**

| Combo | H1 support | estimate | stars |
|:------|:----------:|--------:|:-----:|
| year | supported | 1.155238 | *** |
| month | supported | 1.170907 | *** |
| week | supported | 1.175507 | *** |
| date | supported | 1.098016 | *** |
| hour | supported | 1.118559 | *** |
| year+month | supported | 1.156361 | *** |
| year+week | supported | 1.158017 | *** |
| year+date | supported | 1.098016 | *** |
| year+hour | supported | 1.107803 | *** |
| month+week | supported | 1.175916 | *** |
| month+date | supported | 1.098016 | *** |
| month+hour | supported | 1.126147 | *** |
| week+date | supported | 1.098016 | *** |
| week+hour | supported | 1.131627 | *** |
| date+hour | supported | 1.069182 | *** |
| *(+16 more — see CSV)* | | | |

## H2-1 consistency (Aggressive vs Other humor weighted avg)

**H2-1 supported in 31 / 31 full-sample combinations**

## H2-2 consistency (Aggressive vs SELF humor weighted avg)

**H2-2 supported in 31 / 31 full-sample combinations**

## H2-3 pairwise: self-defeating exception

The Aggressive − Self-Defeating contrast across time dummy combinations:
- Negative direction (Agg < SD): 31 / 31 combos
- Significantly negative (p<.10): 31 / 31 combos

## H3 firm-quarter time dummy results

| Combo | β₁ | β₁ stars | β₂ | β₂ stars | TP | H3 supported |
|:------|---:|:--------:|---:|:--------:|---:|:------------:|
| year | 13.176964 | *** | -11.484962 | *** | 0.573662 | True |
| qoy | 12.622564 | *** | -11.189166 | *** | 0.564053 | True |
| year+qoy | 13.169 | *** | -11.421643 | *** | 0.576493 | True |
| year_quarter | 13.177314 | *** | -11.41725 | *** | 0.577079 | True |

H3 supported combos: year, qoy, year+qoy, year_quarter
H3 not supported: none

## Three-model comparison (H1)

| Model | H1 estimate | H1 stars |
|:------|:-----------:|:--------:|
| Model 1 Simple OLS | see comparison CSV | |
| Model 2 Company Dummy | see comparison CSV | |
| Model 3 Time Dummy (all combos) | supported 31/31 | |

## Rank deficiency notes

Date dummy absorbs Year, Month, Week (since each date uniquely determines year/month/week).
Combinations with Date+Year, Date+Month, Date+Week are rank-deficient.
Effective k_time for these cases uses only Date dimensions (plus Hour if present).
Results from these combinations are valid for the identifiable (Date+Hour) structure.

## Interpretation

Model 3 tests whether the H1/H2/H3 associations are robust to time controls.

- If H1 is supported across ALL time dummy combinations: the humor-engagement association is not driven by temporal confounds (posting seasons, years).
- If H3 collapses under Year/Quarter controls: the inverted-U (or U-shaped) pattern in Model 2 may be a time-specific confound rather than a true dose-response effect.
- All results are associations, not causal effects.

> Model 3 does not replace Model 1 (Simple OLS) or Model 2 (Company Dummy).
> It provides robustness checks against temporal confounding.