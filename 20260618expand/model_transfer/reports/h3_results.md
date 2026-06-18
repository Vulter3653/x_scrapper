# H3 Regression Results

## Status

**confirmatory_candidate**

Non-zero aggressive intensity firm-month rows: 2066 / 3532

H3 has sufficient variation for confirmatory analysis.

## Model

```
mean_log_total_engagement = β0 + β1*aggressive_intensity + β2*aggressive_intensity²
                          + γ1*mean_text_length + γ2*mean_hashtag_count + γ3*mean_mention_count
                          + firm FE + period FE + ε
```

SE: non-robust standard OLS SE.

## Results (N = 3532)

| Variable | Coefficient | SE | t | p | Sig |
|---|---|---|---|---|---|
| (FE-absorbed constant) | 0.0 | 0.011647 | 0.0 | 1.0 |  |
| aggressive_humor_usage_intensity | -1.64683 | 0.197729 | -8.3287 | 0.0 | *** |
| aggressive_humor_usage_intensity_sq | 2.52619 | 0.284073 | 8.8928 | 0.0 | *** |
| mean_text_length | 9.1e-05 | 0.000279 | 0.3261 | 0.7444 |  |
| mean_hashtag_count | -0.082002 | 0.028202 | -2.9077 | 0.0037 | *** |
| mean_mention_count | -0.042607 | 0.02616 | -1.6287 | 0.1035 |  |


R² (within) = 0.0269

## Turning Point Diagnostics

| Item | Value |
|---|---|
| β1 (intensity) | -1.64683 |
| β2 (intensity²) | 2.52619 |
| Turning point | 0.325951 |
| Observed range | [0.0, 1.0] |
| Turning point in range | True |
| Inverted-U shape (β1>0, β2<0) | False |

## H3 Criterion

H3 is supported if:
- β1 > 0 (positive linear term)
- β2 < 0 (negative quadratic term)
- Turning point falls inside observed intensity range

Current: β1=negative  β2=positive

## Claim Boundary

H3 aggressive_humor_usage_intensity is a usage rate (firm-period), not message-level semantic intensity.
This is exploratory evidence due to extreme sparsity in the current dataset.
