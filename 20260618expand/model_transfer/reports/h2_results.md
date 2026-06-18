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


## Analysis Status

**Exploratory model-transfer analysis. Do not use as main hypothesis evidence.**

## H2 Interpretation

H2 predicts aggressive humor has larger engagement effect than other humor types.

aggressive β = -0.1004  SE = 0.0170  p = 0.0000 ***
affiliative β = -0.0331
self-enhancing β = -0.0642
self-defeating β = -0.0419

Under the Wendy's-trained classifier transfer, all humor types have lower engagement than non-humorous posts, and aggressive has the lowest coefficient. H2 is not supported under this specification.

The appropriate framing is:

> Under the Wendy's-classifier transfer specification, aggressive humor posts showed lower engagement than both non-humorous and affiliative posts. These results reflect classifier-transfer sensitivity and should not be interpreted as definitive H2 evidence.

## Domain-Transfer Over-Classification Warning

The Wendy's-trained classifier produced 6,857 aggressive humor posts (10.5% of the Fortune Top 100 sample), compared to 95 posts (0.15%) in the original full_chain_master. This 72x discrepancy strongly suggests that the model is over-classifying Fortune 100 assertive or competitive brand language as aggressive humor. H2 contrast results under this classification should not be used as the primary test of aggressive humor effectiveness.

Do not write: "aggressive humor reduces engagement in Fortune Top 100 firms."
Do write: "Under Wendy's-classifier transfer, posts classified as aggressive humor showed lower engagement; domain-transfer measurement risk is high."

## Claim Boundary

Model-transfer classification from Wendy's TF-IDF LogReg. Not human-validated for Fortune Top 100.
This is a robustness/sensitivity check, not the main empirical test of H2.
Engagement is an engagement-based brand equity proxy.
Observational evidence only.
