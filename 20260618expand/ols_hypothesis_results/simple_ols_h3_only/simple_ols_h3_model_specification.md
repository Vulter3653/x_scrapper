# Simple OLS Model Specification — H3 Diagnostic

## Model (M1 Simple Quadratic OLS)

```
mean_log(1+Engagement)_{ft} = α
                              + β₁·AggressiveIntensity_{ft}
                              + β₂·AggressiveIntensity²_{ft}
                              + ε_{ft}
```

| Item | Value |
|:---|:---|
| Unit of analysis | firm × month |
| DV | mean_log_total_engagement (firm-month average) |
| IVs | aggressive_humor_usage_intensity, aggressive_humor_usage_intensity_sq |
| Controls | NONE |
| Fixed effects | NONE |
| H1/H2 variables | EXCLUDED |
| SE type | Classical OLS (homoskedastic) |
| Stars convention | *** p<.01 / ** p<.05 / * p<.10 (two-sided) |

## H3 Acceptance Criteria

1. β₁ > 0
2. β₂ < 0
3. β₂ statistically significant
4. Turning point = −β₁/(2β₂) within observed intensity range

## Excluded Variables

- H1: humor_presence
- H2: aggressive_humor, affiliative_humor, self_enhancing_humor, self_defeating_humor
- Controls: text_length, hashtag_count, mention_count, mean_text_length,
            mean_hashtag_count, mean_mention_count, emoji_count
- Fixed effects: year, month, firm

## Data Source

- Input: `h3_firm_period_regression_ready.csv`
- N = 3532 firm-month observations (97 firms × up to 130 months)
- Classifier: domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels (batch1+batch2); aggressive_humor_usage_intensity = fraction of posts in firm-month classified as aggressive by this model; NOT_A_CANDIDATE level evidence; leakage risk: classifier trained on same corpus as regression sample
