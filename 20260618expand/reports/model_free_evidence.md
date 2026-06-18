# Model-Free Evidence

This package prepares model-free diagnostics but does not present them as the main empirical test of H1/H2/H3.

## Humor Classification Frequency Table

Counts from `data/processed/fortune100_humor_variables.csv` (deduplicated post-level sample, n=65,245):

| humor_presence | count |
|---|---|
| humor (1) | 9,475 |
| non_humor (0) | 24,314 |
| ambiguous | 31,456 |

| humor_type | count |
|---|---|
| aggressive | 95 |
| affiliative | 4,668 |
| self_enhancing | 4,887 |
| self_defeating | 41 |

Summary: aggressive: 95, affiliative: 4668, self_enhancing: 4887, self_defeating: 41, ambiguous: 31456

Aggressive humor is extremely sparse in the current Fortune Top 100 collected data. H2 aggressive-humor coefficient comparisons should be interpreted with caution, and H3 inverted-U testing should be treated as exploratory/readiness analysis rather than confirmatory evidence.

## Recommended Diagnostics After Running Builders

- engagement distribution by `humor_presence`
- engagement distribution by `humor_type`
- firm-level and account-level post counts
- classification coverage by firm/account
- aggressive humor usage intensity distribution by firm-month
- missingness in text and engagement metrics

## Evidence Level Note

The primary empirical evidence remains full-sample model-based classification linked to regression-ready datasets. Human-coded labels are supplemental validation evidence, not main results.
