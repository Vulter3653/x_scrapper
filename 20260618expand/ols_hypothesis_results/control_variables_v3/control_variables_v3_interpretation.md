# Control Variable Model — Interpretation (Model 4)

> Generated: 2026-06-19  |  Data: v3 classifier (coder3 batch2)

## Model specification

**H1/H2** (post-level):
$$\log(1+\text{Eng}_i) = \beta_0 + \beta_1\text{Agg} + \beta_2\text{Aff} + \beta_3\text{SE} + \beta_4\text{SD} + \gamma_1\text{text\_length} + \gamma_2\text{hashtag} + \gamma_3\text{mention} + \varepsilon$$

**H3** (firm-quarter):
$$\overline{\log(1+\text{Eng})}_{fq} = \alpha + \beta_1\text{Intensity} + \beta_2\text{Intensity}^2 + \gamma_1\text{mean\_tl} + \gamma_2\text{mean\_ht} + \gamma_3\text{mean\_mn} + \gamma_4\log(1+\text{posts}) + \varepsilon$$

- Full-sample N = 68,039  |  HC N = 3,074 (dropped 500 missing controls)
- H3 firm-quarters: Full=1,420  HC=870
- Classical OLS SE. No company dummies. No time dummies. No emoji_count.

## VIF diagnostics (Full-sample H1/H2)

| Variable | VIF | R² aux |
|:---------|----:|-------:|
| aggressive                |   1.0664 | 0.0623 |
| affiliative               |   1.0771 | 0.0716 |
| self_enhancing            |   1.0656 | 0.0616 |
| self_defeating            |   1.0109 | 0.0108 |
| text_length               |   1.1192 | 0.1065 |
| hashtag_count             |   1.0434 | 0.0416 |
| mention_count             |   1.0242 | 0.0236 |

- Condition number (H1/H2 FS): 2566.1932
- Rank deficient: False

## H1: Weighted Humor Effect

**Full sample**: estimate=1.15332, p=0.0***  → H1 **supported**

**Human-coded**: estimate=1.198429, p=0.0***  → H1 **supported**

## H2-1: Aggressive vs Other humor

**Full sample**: 0.791973***  → **supported**

## H2-2: Aggressive vs SELF humor

**Full sample**: 0.414448***  → **supported**

## H2-3 pairwise (full sample)

| Contrast | estimate | stars | support |
|:---------|--------:|:-----:|:-------:|
| Aggressive − Affiliative | 1.034308 | *** | supported |
| Aggressive − Self-Enhancing | 0.463414 | *** | supported |
| Aggressive − Self-Defeating | -0.236813 | ** | not_supported |

## H3 firm-quarter results (Full-sample)

| Item | Value |
|:----|:------|
| H3_supported | True |
| beta1_intensity | 9.483818*** |
| beta2_intensity_sq | -10.338158*** |
| turning_point | 0.45868 |
| obs_range | [0.0, 1.0] |
| tp_in_range | True |
| R² | 0.29234 |
| cond_number | 10934.4971 |

## Interpretation notes

- **Model 4 vs Model 1**: adds post-level content controls (text_length, hashtag_count, mention_count).
- If H1/H2 estimates change little relative to Model 1, the humor-engagement association is not explained by content format differences.
- Control coefficients for text_length, hashtag_count, mention_count reflect content-format associations with engagement.
- H3 adds firm-quarter mean controls + log(posts), controlling for posting volume and style heterogeneity.
- All results are associations, not causal effects.

> Model 4 does not replace Models 1–3. It adds robustness checks for content-level confounds.