# Simple OLS H3 Model Specification

## Model

```text
mean_log1p_engagement_ft = alpha + beta1 * aggressive_intensity_ft + beta2 * aggressive_intensity_sq_ft + epsilon_ft
```

## Scope

- Hypothesis: H3 only
- Unit of analysis: firm x month
- Dependent variable: firm-month mean log(1 + engagement), stored as `mean_log_total_engagement` in the source panel
- Independent variables: `aggressive_humor_usage_intensity`, `aggressive_humor_usage_intensity_sq`
- Controls included: false
- Fixed effects included: false
- H1 humor presence variables included: false
- H2 humor type dummies included: false
- Post-level aggressive dummy included: false

## Explicit Exclusions

No firm fixed effects, year fixed effects, month fixed effects, text controls, hashtag controls, mention controls, emoji controls, post-format controls, H1 variables, H2 variables, or post-level type dummies are included.

## H3 Criteria

H3 is supported only if beta1 > 0, beta2 < 0, beta2 is statistically significant, and the turning point `-beta1 / (2 * beta2)` lies inside the observed aggressive intensity range.

## Data Source

`20260618expand/classifier_improvement/data/regression_ready/h3_firm_period_regression_ready.csv`

## Limitation

classifier-predicted aggressive labels from the current domain-adapted classifier; preliminary diagnostic evidence only; aggressive/type classifier leakage risk and NOT_A_CANDIDATE limitations remain; not robust or causal evidence. This is a preliminary diagnostic baseline, not robust causal evidence.
