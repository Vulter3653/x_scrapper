# H1 Regression — Claim Boundaries

**Date:** 2026-06-18
**Status:** Simple OLS check — exploratory, NOT confirmatory

---

## Model

```
log_total_engagement = β0 + β1 * h1_humor_presence_pred_t50 + ε
```

- Method: simple OLS
- No fixed effects
- No control variables
- Standard OLS SE

---

## Permitted Claims

- "In the exploratory simple OLS check, humor-classified posts (t50) have on average higher
  log total engagement (β=0.955, SE=0.016, p<0.001) compared to non-humor posts."
- "This is a simple unconditional mean difference with no controls or fixed effects."
- "This is a first exploratory association check based on a provisional batch1-only classifier."
- "The classifier-assigned humor labels contain measurement error."
- "This is preliminary evidence consistent with H1, not confirmation of H1."

---

## Prohibited Claims

| Prohibited claim | Why prohibited |
|---|---|
| "H1 is supported." | Exploratory; provisional classifier; simple OLS |
| "H1 is confirmed." | Same as above |
| "Fortune 100 humor use increases engagement." | Causal claim |
| "Humor causes higher engagement." | Causal claim; simple OLS is not causal |
| "Controlling for X, humor is associated with Y." | This model controls for NOTHING |
| "After removing firm/time effects, humor is associated with Y." | No FE in this model |
| "This is confirmatory evidence." | Exploratory; not pre-registered; provisional labels |
| "H2/H3 can now be addressed." | H2/H3 remain blocked |
| "Aggressive humor is associated with [X]." | Type/aggressive not in scope |

---

## Statistical Significance Caveat

With n=65,245, t=60 is expected for any non-trivial mean difference.
p<0.001 does NOT confirm H1. It only confirms there is a non-zero raw
mean difference in the sample.

---

## What This Model Does NOT Control

- Firm identity (firm-level confounders unaddressed)
- Time period (temporal confounders unaddressed)
- Post characteristics (text length, hashtags, mentions — all omitted)
- Campaign effects, product launches, external events

---

## H2/H3 Boundary

H2/H3 remain BLOCKED.
- Type classifier: failed batch1 threshold
- Aggressive detector: not usable
- H2/H3 regression: not executed; not executable from current outputs

## 2026-06-19 Integrated Corpus Scope Correction

Earlier `full corpus` wording in this H1 presence-only area refers to the Fortune 100 subset based on `20260618expand/data/processed/fortune100_post_master.csv` unless explicitly stated otherwise. Those 65,245-row outputs should be interpreted as Fortune 100 subset classification or Fortune 100 subset simple OLS checks, not as the final integrated collected corpus.

The integrated collected corpus output is maintained separately at `20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/`. It includes Fortune 100 sources plus usable existing legacy brand post datasets such as Wendy's, MoonPie, and Coca-Cola, and reflects the June 18 append workflow audit/raw outputs. Integrated-corpus H1 regression has not been run. H2/H3 remain blocked. Type and aggressive classifiers are not used.

