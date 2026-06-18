# H2 Regression Results

## Model

```
log_total_engagement = β0 + β1*aggressive + β2*affiliative + β3*self_enhancing
                     + β4*self_defeating
                     + γ1*text_length + γ2*hashtag_count + γ3*mention_count
                     + firm FE + year FE + ε
```

Reference group: non_humorous posts.
humor_presence and humor_presence × type interactions are NOT included (avoids perfect collinearity).
SE: non-robust standard OLS SE.

## Results (N = 65245)

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
| (FE-absorbed constant) | 0.0 | 0.004883 | 0.0 | 1.0 |  |
| aggressive_humor | -0.100402 | 0.016995 | -5.9078 | 0.0 | *** |
| affiliative_humor | -0.033131 | 0.011825 | -2.8019 | 0.0051 | *** |
| self_enhancing_humor | -0.064177 | 0.028907 | -2.2201 | 0.0264 | ** |
| self_defeating_humor | -0.041928 | 0.083608 | -0.5015 | 0.616 |  |
| text_length | 0.00108 | 4.7e-05 | 22.8183 | 0.0 | *** |
| hashtag_count | 0.077973 | 0.005646 | 13.8114 | 0.0 | *** |
| mention_count | -0.132783 | 0.005364 | -24.7552 | 0.0 | *** |


R² (within) = 0.0207

## Contrast Tests (Aggressive vs Other Types)

| Contrast | Difference | SE | t | p | Sig | Direction |
|---|---|---|---|---|---|---|
| aggressive_vs_affiliative | -0.06727 | 0.017885 | -3.7612 | 0.0002 | *** | aggressive ≤ other |
| aggressive_vs_self_enhancing | -0.036225 | 0.031895 | -1.1357 | 0.2561 |  | aggressive ≤ other |
| aggressive_vs_self_defeating | -0.058473 | 0.08462 | -0.691 | 0.4896 |  | aggressive ≤ other |


## H2 Interpretation

H2 predicts aggressive humor has larger engagement effect than other humor types.

aggressive β = -0.1004  SE = 0.0170  p = 0.0000 ***
affiliative β = -0.0331
self-enhancing β = -0.0642
self-defeating β = -0.0419

## Aggressive Humor Sparsity Warning

The Wendy's-trained classifier may yield a different number of aggressive humor posts
for Fortune Top 100 than the original full_chain_master. If aggressive humor posts are
fewer than 200, H2 contrast interpretations should be treated with caution.

## Claim Boundary

Model-transfer classification from Wendy's TF-IDF LogReg. Not human-validated for Fortune Top 100.
Engagement is an engagement-based brand equity proxy.
Observational evidence only.
