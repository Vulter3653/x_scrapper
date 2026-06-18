# H1 Regression — Claim Boundaries

**Date:** 2026-06-18
**Status:** Exploratory regression on provisional classifier labels

---

## Permitted Claims

These formulations are supported by the current output:

- "In the exploratory H1 regression, humor-classified posts (t50 threshold) are positively associated with log total engagement (β=0.225, SE=0.012, p<0.001) after firm and month fixed effects."
- "The positive association is consistent across t40, t60, and continuous probability predictor robustness checks."
- "All 7 robustness specifications are statistically significant at the 5% level."
- "These results are exploratory and based on a provisional batch1-only classifier (OOF AUC=0.7811)."
- "The classifier-assigned humor labels contain measurement error, which attenuates estimated effects toward zero."
- "This is preliminary evidence consistent with H1, not confirmation of H1."

---

## Prohibited Claims

These must NEVER appear in any report, paper, or presentation.

| Prohibited claim | Why prohibited |
|---|---|
| "H1 is supported." | Exploratory regression; provisional classifier; cannot confirm hypothesis |
| "H1 is confirmed." | Same as above |
| "Fortune 100 humor use increases engagement." | Causal claim; no causal identification |
| "Humor causes higher engagement." | Causal claim; OLS with FE is not causal |
| "The final H1 classifier is validated." | Classifier is batch1-only and provisional |
| "This is confirmatory evidence." | Exploratory only; not pre-registered; provisional labels |
| "The result at p<0.001 confirms H1." | Large n drives low p-value; significance ≠ confirmation |
| "H2/H3 can now be addressed." | H2/H3 remain blocked |
| "Aggressive humor is associated with [X]." | Type/aggressive not in scope |

---

## Statistical Significance Caveat

With n=65,245, even small effects and label noise will produce highly significant t-statistics.
A p-value < 0.001 with 65,245 observations does NOT by itself confirm H1.

When reporting p-values, always accompany with:
- "exploratory result"
- "provisional classifier"
- "n=65,245 — high statistical power expected"

---

## H2/H3 Boundary

H2/H3 remain BLOCKED. This regression output cannot be used to address H2 or H3.

- Type classifier (4-class): failed batch1 threshold
- Aggressive detector: not usable
- H2/H3 regression: not executed; not executable from current outputs

---

## Future Path to Stronger H1 Claims

To move from "exploratory" to "preliminary":
1. batch2 labels received → classifier retrained with batch1+2
2. Improved classifier applied to full corpus
3. H1 regression re-run with improved labels
4. Label as "preliminary" (still not confirmatory)

To move to confirmatory H1:
- Requires causal identification strategy (exogenous humor variation)
- OR: RCT design
- OLS with FE is not sufficient for causal confirmation
