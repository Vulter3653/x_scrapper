# H1 Temporal Distribution Memo

## Scope

This analysis is descriptive distribution checking for H1 presence-only full corpus classification output.
It is not a regression analysis, not causal evidence, and not an H1 support judgment.

## Input

- Input file: `20260618expand/classifier_improvement/h1_presence_only/full_corpus_classification/data/fortune100_h1_presence_classified_posts.csv`
- Input rows: 65245
- Parsed date rows: 65245
- Missing date rows: 0
- Date range: 2015-07-24 to 2026-06-14

## Descriptive Summary

- Years observed: 12
- Year-month periods observed: 130
- Most active year: 2022
- Most active year-month: 2026-05
- Most active hour: 15
- Highest humor_rate_t50 hour: 3
- Lowest humor_rate_t50 hour: 11

## Interpretation Boundary

The main descriptive threshold is `h1_humor_presence_pred_t50`.
The t40 and t60 rates are included only as threshold-sensitivity reference points.
They should not be interpreted as separate hypothesis tests.

No fixed effects, regressions, causal interpretations, H2/H3 tests, type classifier outputs,
or aggressive detector outputs are produced here.
