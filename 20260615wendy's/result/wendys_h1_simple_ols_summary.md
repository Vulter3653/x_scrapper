# Wendy's H1 Simple OLS Results

Generated: 2026-06-15 11:26 UTC

---

## 1. H1 Statement

> Higher humor presence in Wendy's brand posts is associated with higher post-level engagement.

---

## 2. Input Dataset

- File: `20260615wendy's/data/wendys_h1_log_humor_input.csv`
- Rows: 978
- IV: `log1p_humor_score`
- humor_score == 0: 739 (75.6%)

---

## 3. Main IV Definition

```
log1p_humor_score = log(1 + humor_score)
```

`log1p` is used because `humor_score` contains many zero values and `log(0)` is undefined.
`humor_score` is a transparent rule-based score (0.000–1.000), not a calibrated probability.

---

## 4. DV Definitions

```
engagement_total        = reply_count + favorite_count + retweet_count + quote_count + bookmark_count
log1p_engagement_total  = log(1 + engagement_total)   ← main DV
log1p_favorite_count    = log(1 + favorite_count)
log1p_retweet_count     = log(1 + retweet_count)
log1p_reply_count       = log(1 + reply_count)
log1p_quote_count       = log(1 + quote_count)
log1p_bookmark_count    = log(1 + bookmark_count)
```

`view_count` is excluded as DV per task specification.

---

## 5. Model Specification

```
DV = α + β × log1p_humor_score + ε
```

- Model type: Simple bivariate OLS (statsmodels OLS)
- Controls: **None**
- Fixed effects: **None**
- Standard errors: **Conventional OLS (not robust, not HC3)**
- Clustering: **None**

---

## 6. Main Result: log1p_engagement_total

| Parameter | Value |
|-----------|-------|
| n_obs | 978 |
| Intercept | 7.391081 |
| β (log1p_humor_score) | 0.378703 |
| Standard Error | 0.429993 |
| t-value | 0.8807 |
| p-value | 0.378686 |
| 95% CI | [7.512751, 1.222521] |
| R² | 0.000794 |
| Adj. R² | -0.000230 |
| Direction | positive |
| H1 Interpretation | **Directional support for H1** |

---

## 7. All DV Results

| DV | beta | SE | t | p | R² | direction | H1 interpretation |
|---|---|---|---|---|---|---|---|
| log1p_engagement_total | 0.378703 | 0.429993 | 0.8807 | 0.378686 | 0.000794 | positive | Directional support for H1 |
| log1p_favorite_count | 0.500438 | 0.507733 | 0.9856 | 0.324558 | 0.000994 | positive | Directional support for H1 |
| log1p_retweet_count | 0.311800 | 0.440615 | 0.7076 | 0.479333 | 0.000513 | positive | Directional support for H1 |
| log1p_reply_count | 0.356173 | 0.406111 | 0.8770 | 0.380683 | 0.000787 | positive | Directional support for H1 |
| log1p_quote_count | 0.650224 | 0.457403 | 1.4216 | 0.155475 | 0.002066 | positive | Directional support for H1 |
| log1p_bookmark_count | 0.312290 | 0.425268 | 0.7343 | 0.462920 | 0.000552 | positive | Directional support for H1 |

---

## 8. H1 Interpretation

The main DV result (`log1p_engagement_total`):

**Directional support for H1**

β = 0.378703, SE = 0.429993, p = 0.378686, R² = 0.000794

Higher `log(1 + humor_score)` is **positively** associated with `log(1 + engagement_total)` in this Wendy's-only simple OLS analysis.

---

## 9. Limitations

- This is a Wendy's-only post-level association test.
- This is not causal evidence.
- This is simple OLS only.
- No controls or fixed effects are included.
- Standard errors are conventional OLS standard errors, not robust standard errors.
- `humor_score` is rule-based and not a calibrated probability.
- `log1p_humor_score` is used because `humor_score` contains many zeros (739/978 = 75.6%).
- Engagement is observational and may be affected by timing, media assets, platform algorithms, campaigns, and external events.
