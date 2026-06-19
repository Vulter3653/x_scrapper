# Simple OLS Model Specification — H1 and H2 Diagnostic

## Model (M1 Simple OLS)

```
log(1 + Engagement_i) = β₀
                      + β₁ Aggressive_i
                      + β₂ Affiliative_i
                      + β₃ SelfEnhancing_i
                      + β₄ SelfDefeating_i
                      + ε_i
```

| Item | Value |
|:---|:---|
| DV | log_total_engagement (log₁₊₁) |
| Reference category | non_humorous (omitted) |
| Controls | NONE |
| Fixed effects | NONE |
| H3 variables | EXCLUDED |
| SE type | Classical OLS (homoskedastic) |
| Stars convention | *** p<.01 / ** p<.05 / * p<.10 (two-sided) |

## Identification Rules Applied

1. `non_humorous` = reference category (omitted dummy)
2. `non_humorous` dummy not included in regression
3. `HumorPresence` dummy not included (avoids perfect multicollinearity)
4. Only four humor type dummies as IVs
5. No numeric company_id covariate
6. No C(company_id) firm fixed effects

## Excluded Variables

- H3: aggressive humor usage intensity, intensity², interaction terms
- Controls: text_length, hashtag_count, mention_count, emoji_count
- Fixed effects: year, month, hour, firm

## Data Source

- Input: `h2_post_level_regression_ready.csv`
- N = 65,245 Fortune100 posts
- Classifier: domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels (batch1+batch2); predictions only — NOT_A_CANDIDATE level evidence; leakage risk: classifier trained on same corpus as regression sample
