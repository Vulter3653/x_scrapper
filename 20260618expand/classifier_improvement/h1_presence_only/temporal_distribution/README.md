# H1 Presence Temporal Distribution

## Purpose

This package checks the temporal distribution of the H1 presence-only full corpus classification output for Fortune 100 X posts.
It summarizes post counts and `h1_humor_presence_pred_t50` humor rates by year, year-month, month of year, day of month, day of week, and hour of day.

This is a descriptive diagnostic only.
It is not a regression analysis, not causal evidence, and not an H1 support judgment.

## Input

Primary input:

```text
20260618expand/classifier_improvement/h1_presence_only/full_corpus_classification/data/fortune100_h1_presence_classified_posts.csv
```

Required fields:

- `created_at` or `date`
- `company_name`
- `source_x_handle` or `x_handle`
- `h1_humor_presence_probability`
- `h1_humor_presence_pred_t50`
- `h1_humor_presence_pred_t40`
- `h1_humor_presence_pred_t60`

## Outputs

Results:

- `results/year_distribution.csv`
- `results/year_month_distribution.csv`
- `results/month_of_year_distribution.csv`
- `results/day_of_month_distribution.csv`
- `results/day_of_week_distribution.csv`
- `results/hour_of_day_distribution.csv`
- `results/temporal_distribution_summary.csv`

Figures:

- `figures/year_post_count.png`
- `figures/year_humor_rate_t50.png`
- `figures/year_month_post_count.png`
- `figures/year_month_humor_rate_t50.png`
- `figures/month_of_year_post_count.png`
- `figures/month_of_year_humor_rate_t50.png`
- `figures/day_of_month_post_count.png`
- `figures/day_of_week_post_count.png`
- `figures/day_of_week_humor_rate_t50.png`
- `figures/hour_of_day_post_count.png`
- `figures/hour_of_day_humor_rate_t50.png`

Report:

- `reports/temporal_distribution_memo.md`

## Interpretation Boundary

The main descriptive threshold is `h1_humor_presence_pred_t50`.
The t40 and t60 columns are threshold-sensitivity reference summaries only.

This package does not:

- retrain classifiers
- reclassify the full corpus
- run H1 regressions
- run H2/H3 analyses
- use type classifier outputs
- use aggressive detector outputs
- produce causal or fixed-effect claims
- establish H1 support

## Run

```bash
python 20260618expand/classifier_improvement/h1_presence_only/temporal_distribution/scripts/build_h1_temporal_distribution.py
python 20260618expand/classifier_improvement/h1_presence_only/temporal_distribution/scripts/validate_h1_temporal_distribution_outputs.py
python 20260618expand/classifier_improvement/scripts/validate_coder_labeling_splits.py
```
