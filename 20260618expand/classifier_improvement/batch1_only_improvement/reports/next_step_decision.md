# Next Step Decision — batch1-Only Improvement

**Date:** 2026-06-18
**Status:** batch1 improvement complete

---

## Decision Tree

### Presence Classifier

**OOF AUC = 0.7811** → Provisionally passes (>= 0.75).

Decision: **Accept as improved presence classifier for H1 (provisionally).**
- Best config: word_char_comb__lr_liblin_C01 (highest OOF AUC)
- Alt config:  word_char_comb__lr_lbfgs_bal (highest firm-held-out F1 = 0.5047)
- Full corpus application: BLOCKED (pending validated aggressive detector)
- H1 estimation: BLOCKED (pending full corpus classification)

### Aggressive Detector

**OOF PR-AUC = 0.2159, no model meets precision >= 0.60 AND recall >= 0.20.**

Decision: **Aggressive detector remains not usable for H2/H3 main analysis.**

### 4-Class Type Classifier

**macro-F1 = 0.3347 (below 0.3448 baseline).** Status unchanged.
Decision: Secondary diagnostic only.

---

## What Is Blocked and Why

| Item | Status | Unblock Condition |
|---|---|---|
| Apply classifier to 65,245 posts | BLOCKED | validated aggressive detector |
| H1/H2/H3 re-estimation | BLOCKED | full corpus classification complete |
| Aggressive detector for H2/H3 | BLOCKED | precision >= 0.60 AND recall >= 0.20 (OOF) |
| Type classifier (4-class) | BLOCKED | macro-F1 > 0.3448 |

---

## Path to Unblock

### Primary path: batch2 receipt and combined training

1. Receive batch2 coder labels (500 rows × 3 coders = 1,500 additional posts)
2. Combine batch1 + batch2 (up to 3,000 labeled posts)
3. Re-train aggressive detector — expected ~88 aggressive positives (vs 44 now)
4. With n≈88 positives, 5-fold CV will have ~17 per fold — more stable estimates
5. Re-evaluate: if precision >= 0.60 AND recall >= 0.20, proceed to full corpus application
6. Apply validated classifier → re-estimate H1/H2/H3

### Alternative path if batch2 not available: descriptive only

If batch2 is delayed indefinitely:
- Report H1 estimate using human-coded batch1 labels only (648 humor / 1,482 total)
- Report H2/H3 as descriptive statistics from batch1 human labels only:
  - In batch1 humor: aggressive=44 (6.8%), affiliative=321 (49.5%), self_enhancing=259 (40.0%), self_defeating=24 (3.7%)
- Clearly label these as "batch1 human-coded descriptive sample statistics"
- Do NOT use automated classifier predictions for H2/H3 claims

---

## Recommended Configurations for batch1+2 Training

Based on batch1 search results:
- **Presence**: word_char_comb__lr_liblin_C01 or word_char_comb__lr_lbfgs_bal
- **Aggressive detector**: char_35_5k__lr_liblin_C01 or char_35_5k__cnb

With more data (batch2), higher max_features and lower min_df may also be viable.
