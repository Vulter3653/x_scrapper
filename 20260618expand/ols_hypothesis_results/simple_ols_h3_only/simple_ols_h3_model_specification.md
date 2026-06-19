# OLS Model Specification — H3 Diagnostic

## M1 Simple Quadratic OLS

```
mean_log(1+Engagement)_{ft} = α + β₁·Intensity_{ft} + β₂·Intensity²_{ft} + ε
```

## M2 Firm FE (FWL within-firm demeaning)

```
mean_log(1+Engagement)_{ft} = β₁·Intensity_{ft} + β₂·Intensity²_{ft} + μ_f + ε
```

μ_f absorbed via within-firm demeaning. No intercept after demeaning.

| Item | M1 | M2 |
|:---|:---|:---|
| Unit of analysis | firm×month | firm×month |
| DV | mean_log_total_engagement | mean_log_total_engagement |
| IVs | Intensity, Intensity² | Intensity, Intensity² |
| Controls | NONE | NONE |
| Firm FE | NONE | YES (FWL) |
| Time FE | NONE | NONE |
| H1/H2 variables | EXCLUDED | EXCLUDED |
| N | 3532 | 3532 |
| Firms | — | 97 |
| df_resid | 3529 | 3433 |

## H3 Acceptance Criteria

β₁>0, β₂<0, β₂ significant (p<.10), turning_point = −β₁/(2β₂) within observed range.

## Data Source

- `h3_firm_period_regression_ready.csv` — N=3532 firm-month obs (97 firms × up to 130 months)
- Classifier: domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels (batch1+batch2); aggressive_humor_usage_intensity = fraction of posts in firm-month classified as aggressive by this model; NOT_A_CANDIDATE level evidence; leakage risk: classifier trained on same corpus as regression sample
