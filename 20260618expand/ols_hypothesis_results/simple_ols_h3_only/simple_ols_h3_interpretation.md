# Simple OLS H3 Interpretation

## Model

```text
mean_log1p_engagement ~ aggressive_intensity + aggressive_intensity_sq
```

This file reports H3 only. H1 and H2 are not analyzed. Controls and fixed effects are not included.

## Sample

- Unit of analysis: firm x month
- N: 3,769
- Firms: 99
- Months: 133
- Aggressive intensity range: [0.000000, 1.000000]

## Simple Quadratic OLS Result

- beta1 aggressive_intensity: 10.220228 (p=0.000000, ***)
- beta2 aggressive_intensity_sq: -8.428199 (p=0.000000, ***)
- turning point: 0.606311
- turning point in observed range: true
- pattern: inverted-U
- H3_supported: true

## Interpretation

H3 supported in this simple diagnostic: beta1>0, beta2<0, beta2 statistically significant, and turning point is inside the observed range.

## Boundary

This is a preliminary H3-only simple OLS diagnostic. It excludes all controls and fixed effects by design. Even if coefficients are statistically significant, this result should not be treated as robust evidence or a causal estimate. The aggressive intensity variable is based on classifier-predicted aggressive labels, and classifier leakage / NOT_A_CANDIDATE limitations must be carried forward.
