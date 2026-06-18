# H1 Claim Boundaries

**Scope:** H1 humor presence classifier only
**Date:** 2026-06-18

---

## Permitted Claims

These claims are supported by batch1-only OOF evaluation:

- "The batch1-only humor presence classifier provisionally passes the OOF AUC threshold."
- "The classifier can support preliminary H1-oriented interpretation."
- "Cross-firm generalization remains limited (firm-held-out F1 ≈ 0.48)."
- "Best batch1 presence classifier: word_char_comb__lr_liblin_C01, OOF AUC=0.7811."
- "char (3,5) + word (1,2) features outperform word-only baseline by +0.0137 AUC."
- "This is a provisional classifier trained on batch1 labels only."
- "Full H1 regression requires full corpus application, which has not yet been run."

---

## Prohibited Claims

These claims must NOT appear in any report, paper, or presentation.

| Prohibited claim | Why prohibited |
|---|---|
| "The final H1 classifier is validated." | batch1 only; not deployment-ready; batch2 not yet incorporated |
| "H1 is supported." | H1 regression has not been run |
| "The classifier is deployment-ready." | firm-held-out F1 is low; batch2 not combined |
| "Full Fortune 100 H1 regression can now be treated as final." | full corpus not classified; regression not run |
| "Fortune 100 companies use humor X% of the time." | full corpus not classified |
| "The classifier generalizes well across firms." | firm-held-out F1=0.48, not sufficient for strong claim |
| "H2/H3 analysis can proceed." | type classifier failed; aggressive detector failed; H2/H3 blocked |
| "Aggressive humor is [X%] of Fortune 100 posts." | aggressive detector not usable |

---

## Metric Citation Rules

When citing classifier performance:

| Claim type | Use this metric | Do NOT use |
|---|---|---|
| In-distribution discrimination | OOF AUC = 0.7811 | In-sample AUC (inflated) |
| In-distribution classification | OOF F1 = 0.6792 | In-sample F1 (inflated) |
| Cross-firm generalizability | Firm-held-out F1 ≈ 0.48 | Random CV F1 (leakage) |
| Threshold performance | CV-based threshold CSV | In-sample threshold CSV |

---

## H2/H3 Boundary

H2/H3 are out of scope for this directory entirely.

H2/H3 remain blocked because:
- Type classifier (4-class): macro-F1=0.3347 < 0.3448 baseline (FAIL)
- Aggressive detector: no model meets precision>=0.60 AND recall>=0.20 (FAIL)
- batch2 labels required before either can be reconsidered

Do NOT reference H2/H3 outcomes in any H1-only analysis document.

---

## H1 Regression Boundary

A future H1 regression (if conducted) must be described as:
- **"exploratory"** or **"preliminary"**
- NOT as confirmatory evidence
- With explicit note that the classifier is batch1-only and provisional

H1 regression has NOT been run as of 2026-06-18.

## 2026-06-19 Integrated Corpus Scope Correction

Earlier `full corpus` wording in this H1 presence-only area refers to the Fortune 100 subset based on `20260618expand/data/processed/fortune100_post_master.csv` unless explicitly stated otherwise. Those 65,245-row outputs should be interpreted as Fortune 100 subset classification or Fortune 100 subset simple OLS checks, not as the final integrated collected corpus.

The integrated collected corpus output is maintained separately at `20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/`. It includes Fortune 100 sources plus usable existing legacy brand post datasets such as Wendy's, MoonPie, and Coca-Cola, and reflects the June 18 append workflow audit/raw outputs. Integrated-corpus H1 regression has not been run. H2/H3 remain blocked. Type and aggressive classifiers are not used.

