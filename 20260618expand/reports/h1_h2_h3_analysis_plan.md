# H1 H2 H3 Analysis Plan

No regression is executed by this package. The scripts prepare datasets and diagnostics for a later manual GitHub Actions run or reviewed local run.

## H1

Post-level baseline:

```text
log_total_engagement_ij = beta0 + beta1 humor_presence_ij
  + gamma text_length_ij
  + gamma hashtag_count_ij
  + gamma mention_count_ij
  + firm fixed effects + error_ij
```

Prepared dataset: `data/regression_ready/fortune100_post_level_regression_ready.csv`.

Readiness checks:

- `h1_sample_inclusion_flag == 1`
- nonmissing `log_total_engagement`
- nonmissing model-based `humor_presence`
- enough within-firm variation for firm fixed effects
- account and period fixed effects only if coverage diagnostics support them

## H2

Post-level type comparison:

```text
log_total_engagement_ij = beta0
  + beta1 aggressive_humor_ij
  + beta2 affiliative_humor_ij
  + beta3 self_enhancing_humor_ij
  + beta4 self_defeating_humor_ij
  + gamma controls_ij
  + firm fixed effects + error_ij
```

The contrast table should compare aggressive humor against affiliative, self-enhancing, and self-defeating humor. Baseline can be non-humorous or an omitted humor type, but the contrast table must make the aggressive-versus-other comparison explicit.

## H3

Firm-period baseline:

```text
mean_log_total_engagement_it = beta0
  + beta1 aggressive_humor_usage_intensity_it
  + beta2 aggressive_humor_usage_intensity_sq_it
  + gamma controls_it
  + firm fixed effects
  + period fixed effects
  + error_it
```

Interpretation rule:

- beta1 > 0
- beta2 < 0
- turning point falls inside the observed `aggressive_humor_usage_intensity` range

If firm-month observations are sparse, H3 must be reported as exploratory/readiness evidence rather than confirmatory hypothesis evidence.
