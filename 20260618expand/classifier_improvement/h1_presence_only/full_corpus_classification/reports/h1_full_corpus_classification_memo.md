# H1 Full Corpus Classification Memo

**Date:** 2026-06-18
**Stage:** H1 presence-only full corpus classification (NOT H1 regression)
**Scope:** Binary humor presence only — H2/H3 excluded

---

## Purpose

This document describes the application of the batch1-only H1 presence classifier
to the full Fortune 100 collected post corpus (65,245 posts).

**This is NOT H1 regression analysis.** This step generates provisional humor presence
labels for each post. H1 regression (relating humor presence to engagement outcomes)
has NOT been run and is a separate future step.

---

## Classifier

| Item | Value |
|---|---|
| Model | `word_char_comb__lr_liblin_C01` |
| Vectorizer | word(1,2) + char_wb(3,5) FeatureUnion, max_features=5000+5000 |
| Classifier | LogisticRegression(liblinear, C=0.1, class_weight=balanced) |
| Training scope | batch1 only (1,482 valid rows) |
| OOF AUC | 0.7811 (provisionally passes >= 0.75 threshold) |
| OOF F1 | 0.6792 |
| Firm-held-out F1 | 0.4770 (97 firms) |
| Status | **provisional / exploratory** |

### Cross-firm generalization limitation

The OOF AUC (0.7811) is measured in random CV where same-brand tweets may appear in
both train and validation folds (brand leakage). The firm-held-out F1 (0.4770) is the
more conservative estimate of cross-firm generalizability. Cross-firm generalization
claims must cite firm-held-out F1, not OOF F1.

---

## Classification Output

| Metric | Value |
|---|---|
| Total posts | 65,245 |
| Classified posts | 65,245 |
| Missing text posts | 0 |
| Mean humor probability | 0.4779 |
| Humor rate (threshold=0.40) | 85.0% (n=55,482) |
| Humor rate (threshold=0.50) | 38.6% (n=25,189) |
| Humor rate (threshold=0.60) | 4.8% (n=3,166) |

### Threshold interpretation

Three threshold columns are provided as robustness candidates:
- **t40 (>= 0.40):** Broader humor definition; high recall, lower precision.
- **t50 (>= 0.50):** Balanced default; 38.6% humor rate.
- **t60 (>= 0.60):** Conservative; higher precision, lower recall (4.8% humor rate).

The large spread (4.8% – 85.0%) reflects the fact that this is a provisionally trained
classifier with imperfect calibration. The t40 rate is likely an overestimate;
t60 may under-detect. The t50 rate (38.6%) is consistent with the batch1 human-coded
sample rate (43.7%), allowing for sampling design differences.

None of these rates should be reported as a final estimated humor prevalence. They are
candidate inputs for an exploratory H1 regression if one is conducted later.

---

## What This Is and Is Not

| This is | This is not |
|---|---|
| Provisional humor presence labeling for all 65,245 posts | H1 hypothesis test |
| Exploratory input for future H1 regression | Confirmatory evidence |
| A batch1-only classifier output | A validated final classifier |
| Three threshold-based binary labels per post | Humour type/aggressive labels |

---

## H2/H3 Status

Type classifier and aggressive detector are out of scope for this document.
- type classifier: secondary diagnostic only (failed batch1 threshold)
- aggressive detector: not usable (failed batch1 criteria)
- H2/H3 regression: BLOCKED

---

## Next Step

To proceed to H1 regression:
1. Select a threshold (t40/t50/t60) for humor presence label
2. Run H1 regression with `h1_humor_presence_pred_tXX` as the key independent variable
3. Clearly label the regression as **exploratory/provisional**
4. Cite classifier limitations (batch1-only, firm-held-out F1=0.4770)

H1 regression is NOT authorized in this step.

## 2026-06-19 Integrated Corpus Scope Correction

Earlier `full corpus` wording in this H1 presence-only area refers to the Fortune 100 subset based on `20260618expand/data/processed/fortune100_post_master.csv` unless explicitly stated otherwise. Those 65,245-row outputs should be interpreted as Fortune 100 subset classification or Fortune 100 subset simple OLS checks, not as the final integrated collected corpus.

The integrated collected corpus output is maintained separately at `20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/`. It includes Fortune 100 sources plus usable existing legacy brand post datasets such as Wendy's, MoonPie, and Coca-Cola, and reflects the June 18 append workflow audit/raw outputs. Integrated-corpus H1 regression has not been run. H2/H3 remain blocked. Type and aggressive classifiers are not used.

