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

Aggressive humor sparsity notice: The current Fortune Top 100 collected data contain only 95 aggressive humor posts (0.15% of the post-level sample). H2 aggressive-humor coefficient comparisons should be interpreted with caution given this extreme sparsity.

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

Current data status: The current Fortune Top 100 collected data contain only 95 aggressive humor posts, approximately 0.15% of the deduplicated post-level sample. At the firm-month level, only 84 out of 3,532 firm-month rows have aggressive_humor_usage_intensity greater than zero. Therefore, H3 is not treated as confirmatory inverted-U evidence. It is reported only as exploratory/readiness evidence.

Ambiguous denominator notice: Ambiguous humor_presence rows account for 31,456 posts, or 48.2% of the deduplicated post-level sample. In the current package, all-post denominator usage rates include ambiguous posts in the denominator, while humor and aggressive humor counts only count binary classified humor labels. Therefore, all-post denominator intensity should be interpreted as a conservative lower-bound measure. Because ambiguous rows are large and aggressive humor is extremely sparse, H3 is reported only as exploratory/readiness evidence.

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

Current data trigger: The 84 non-zero firm-month rows and 95 aggressive posts already trigger this rule. H3 is classified as exploratory/readiness for the current Fortune Top 100 collected dataset.
