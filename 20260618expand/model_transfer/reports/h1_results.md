# H1 Regression Results

## Model

```
log_total_engagement = β0 + β1*humor_presence + γ1*text_length + γ2*hashtag_count + γ3*mention_count
                     + firm FE + year FE + ε
```

Implementation: within-group demeaning (entity FE via Frisch-Waugh).
SE: non-robust standard OLS SE.

## Results (N = 65245)

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
| (FE-absorbed constant) | 0.0 | 0.004884 | 0.0 | 1.0 |  |
| humor_presence | -0.051976 | 0.01057 | -4.9175 | 0.0 | *** |
| text_length | 0.0011 | 4.7e-05 | 23.4066 | 0.0 | *** |
| hashtag_count | 0.07837 | 0.005645 | 13.8835 | 0.0 | *** |
| mention_count | -0.13262 | 0.005363 | -24.7272 | 0.0 | *** |


R² (within) = 0.0205

## H1 Interpretation

H1 predicts β1 > 0 (humor_presence positively associated with engagement).

β1 = -0.0520  SE = 0.0106  p = 0.0000 ***

**H1 not supported** at p<.10.

## Fixed Effects

- Firm fixed effects: 97 firms
- Year fixed effects: 12 years
- Controls: text_length, hashtag_count, mention_count
- emoji_count: excluded

## Claim Boundary

This analysis applies the Wendy's-trained TF-IDF LogReg classifier to Fortune Top 100 posts.
Results reflect model-transfer classification, not human-validated Fortune-wide labels.
