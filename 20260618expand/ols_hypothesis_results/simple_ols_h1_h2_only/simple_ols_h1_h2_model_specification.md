# OLS Model Specification — H1 and H2 Diagnostic

## M1 Simple OLS

```
log(1+Engagement_i) = β₀ + β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating + ε_i
```

## M2 Firm FE (FWL within-firm demeaning)

```
log(1+Engagement_i) = β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating
                    + μ_f + ε_i
```

μ_f absorbed via within-firm demeaning (FWL). No intercept after demeaning.

| Item | M1 | M2 |
|:---|:---|:---|
| DV | log_total_engagement | log_total_engagement |
| Reference category | non_humorous (omitted) | non_humorous (omitted) |
| Controls | NONE | NONE |
| Firm FE | NONE | YES (FWL) |
| Time FE | NONE | NONE |
| H3 variables | EXCLUDED | EXCLUDED |
| N | 65,245 | 65,245 |
| Firms | — | 97 |
| df_resid | 65,240 | 65,144 |
| SE type | Classical OLS | Classical OLS (FWL-adjusted df) |

## Identification Rules

1. non_humorous = reference category (omitted)
2. non_humorous dummy not included in regression
3. HumorPresence dummy not included (avoids perfect multicollinearity)
4. No company_id numeric covariate
5. M2 firm FE: within-firm demeaning — df_resid = N − N_firms − k_within

## Data Source

- `h2_post_level_regression_ready.csv` — N=65,245 Fortune100 posts
- Classifier: domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels (batch1+batch2); predictions only — NOT_A_CANDIDATE level evidence; leakage risk: classifier trained on same corpus as regression sample
