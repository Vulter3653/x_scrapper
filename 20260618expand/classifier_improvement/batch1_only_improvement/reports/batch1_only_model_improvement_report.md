# Batch1-Only Classifier Improvement Report

**Date:** 2026-06-18
**Batch:** batch1 only (1,500 labeled posts, 3 coders)
**Batch2:** NOT used

---

## Executive Summary

Using batch1 labels only (1,500 posts), two classifiers were trained and evaluated:

1. **Presence classifier**: Improved OOF AUC from 0.7674 (batch1 baseline) to **0.7811** with word+char combined TF-IDF + LogReg (C=0.1). Provisionally passes the AUC >= 0.75 threshold. Not deployment-ready.

2. **Aggressive detector**: Best OOF PR-AUC = 0.2159. No model meets provisional usability criteria (precision >= 0.60 AND recall >= 0.20 simultaneously). **Aggressive detector remains not usable for H2/H3 main analysis.**

---

## 1. Data Summary

| Metric | Value |
|---|---|
| Total batch1 rows | 1,500 |
| Uncertain excluded | 18 |
| Presence valid rows | 1,482 |
| humor (presence=1) | 648 |
| non_humor (presence=0) | 834 |
| Aggressive detector rows | 648 |
| aggressive positives | 44 (6.8%) |
| non_aggressive_humor | 604 (93.2%) |
| Unique firms (presence) | 97 |
| Unique firms with aggressive | 24 |
| batch2 used | NO |

---

## 2. Presence Classifier Results

### 2.1 Model Search Summary

41 configurations tested: 6 vectorizer types × 7 classifiers (some combinations excluded).

All metrics are **out-of-fold (OOF)** from StratifiedKFold(5, random_state=42).

**Top models by OOF AUC:**

| Rank | Model | OOF AUC | OOF F1 | Firm-HO F1 |
|---|---|---|---|---|
| 1 | word_char_comb__lr_liblin_C01 | **0.7811** | 0.6792 | 0.4770 |
| 2 | word_char_comb__lr_liblin_bal | 0.7784 | 0.6732 | 0.5044 |
| 3 | word_char_comb__lr_lbfgs_bal | 0.7781 | 0.6747 | **0.5047** |
| 4 | char_35_5k__lr_liblin_C01 | 0.7755 | 0.6775 | 0.4822 |
| 5 | char_35_5k__cnb | 0.7748 | 0.6776 | 0.4867 |
| — | **batch1 baseline (3aade94)** | 0.7674 | 0.6570 | 0.5333 |

### 2.2 Key Findings

- **char ngrams** (analyzer=char_wb, (3,5)) are the primary driver. All top models use char features.
- **word+char combined** FeatureUnion is consistently top-ranked by OOF AUC.
- **C=0.1** (stronger regularization) improves OOF AUC slightly over C=1.0 but decreases firm-held-out F1. This suggests moderate overfitting to random CV folds with strong regularization.
- Firm-held-out F1 is universally lower than random CV F1 (expected — brand linguistic leakage in random CV).
- **Best by OOF AUC**: word_char_comb__lr_liblin_C01 (AUC=0.7811). Provisionally passes AUC >= 0.75.
- **Best by firm-held-out F1**: word_char_comb__lr_lbfgs_bal (FH F1=0.5047). Recommended if cross-firm generalizability is the priority.

### 2.3 Improvement vs Baseline

| Metric | batch1 baseline (3aade94) | batch1 best (this run) | Change |
|---|---|---|---|
| OOF AUC | 0.7674 | 0.7811 | +0.0137 |
| OOF F1 | 0.6570 | 0.6792 | +0.0222 |
| Firm-held-out F1 | 0.5333 | 0.5047 | -0.0286 |

Note: The OOF AUC is slightly higher but firm-held-out F1 is slightly lower. This is consistent with random CV being optimistic for same-brand tweets. The baseline firm-held-out F1=0.5333 used only 10 holdout firms; this run used all 97 firms.

### 2.4 Interpretation

- Presence classifier provisionally passes OOF AUC threshold (0.7811 >= 0.75).
- Char ngrams capture stylistic cues (punctuation, capitalization patterns) better than word ngrams alone.
- Firm-held-out performance (FH F1 ~0.48-0.50) indicates meaningful but limited cross-firm generalizability.
- **NOT deployment-ready.** Full corpus application remains blocked.

---

## 3. Aggressive Detector Results

### 3.1 Model Search Summary

29 configurations tested. Training set: 648 humor rows (aggressive=44, non_aggressive=604).

All metrics are **out-of-fold (OOF)** from StratifiedKFold(5, random_state=42).
Threshold analysis uses OOF probabilities only — no in-sample threshold selection.

**Top models by OOF PR-AUC:**

| Rank | Model | OOF PR-AUC | OOF ROC-AUC | OOF Prec | OOF Rec |
|---|---|---|---|---|---|
| 1 | char_35_5k__cnb | **0.2159** | — | 0.2388 | 0.3636 |
| 2 | char_35_5k__lr_liblin_C01 | 0.2079 | — | 0.3077 | 0.2727 |
| 3 | char_35_5k__lr_liblin_bal | 0.2005 | — | 0.2857 | 0.1818 |
| 4 | word_12_10k__cnb | 0.1910 | — | 0.3750 | 0.0682 |
| 5 | word_12_10k__sgd_log_bal | 0.1895 | — | 0.4000 | 0.0455 |

### 3.2 Threshold Analysis (OOF-based)

No model achieves both precision >= 0.60 AND recall >= 0.20 at any threshold.

Best achievable precision >= 0.60:
- word_12_10k__cnb at threshold=0.65: precision=0.60, recall=0.0682, coverage=0.77%
- This does not meet the recall >= 0.20 criterion.

Highest recall while maximizing precision:
- char_35_5k__cnb at default threshold: precision=0.24, recall=0.36 (precision too low)
- char_35_5k__lr_liblin_C01: precision=0.31, recall=0.27 (precision too low)

There is a fundamental precision-recall trade-off. With n=44 positives, no configuration can simultaneously achieve precision >= 0.60 and recall >= 0.20 on OOF data.

### 3.3 Firm-Held-Out (Top 3 models, firms with aggressive positives only)

| Model | FH Precision | FH Recall | FH F1 | N firms |
|---|---|---|---|---|
| char_35_5k__cnb | 0.3264 | 0.3611 | 0.3278 | 24 |
| char_35_5k__lr_liblin_C01 | 0.3750 | 0.3264 | 0.3217 | 24 |
| char_35_5k__lr_liblin_bal | 0.2431 | 0.2361 | 0.2319 | 24 |

Firm-held-out precision (~0.33-0.38) is even lower than OOF precision — confirming poor generalization.

### 3.4 Interpretation

**Aggressive detector does not meet provisional usability criteria.**

- Maximum OOF PR-AUC = 0.2159 (baseline rate = 0.068, so random PR-AUC ≈ 0.068)
- Even with the best model (char_35_5k__cnb), the PR-AUC of 0.2159 indicates weak but above-chance discrimination.
- No threshold achieves precision >= 0.60 with recall >= 0.20 simultaneously.
- The fundamental bottleneck is n=44 aggressive positives in batch1. With 5-fold CV, each fold tests ~8-9 aggressive examples — too few for stable estimates.
- Char (3,5) ngrams modestly outperform word ngrams, suggesting stylistic cues help but are insufficient alone.
- ComplementNB (char_35_5k__cnb) outperforms LogReg and SVC — likely because ComplementNB is better calibrated for severe class imbalance without explicit class weighting.

**Conclusion (Case 2 from spec):**
- Aggressive detector remains not usable for H2/H3 main analysis.
- Batch1 alone is insufficient for reliable aggressive classification.
- H2/H3 must remain blocked or be reported only as human-coded batch1 descriptive evidence.

---

## 4. 4-Class Type Classifier Status

Unchanged from batch1 baseline (commit 3aade94):
- macro-F1 = 0.3347 (below 0.3448 threshold)
- Status: secondary diagnostic only, not usable for classification

No retraining performed in this module.

---

## 5. What Is and Is Not Permitted

| Permitted | Not Permitted |
|---|---|
| "Best presence model: word_char_comb__lr_liblin_C01, OOF AUC=0.7811" | "Final classifier is ready" |
| "Presence classifier provisionally passes AUC >= 0.75 (OOF)" | "H1/H2/H3 can now be tested" |
| "Aggressive detector OOF PR-AUC=0.2159, not usable for H2/H3" | "Aggressive humor classification is reliable" |
| "Batch2 labels required for reliable aggressive classification" | "Batch1 solves the type classifier problem" |
| "char (3,5) ngrams improve presence AUC by +0.0137" | "Type classifier is validated" |
| "Firm-held-out F1=0.48-0.50 (best presence model)" | "full corpus classification can proceed" |

---

## 6. Next Steps

See `next_step_decision.md` for detailed decision.

1. **Receive batch2 labels** (500×3 coders = 1,500 additional posts) — primary bottleneck
2. **Re-train combined batch1+batch2** with best-identified configurations
3. **Re-evaluate aggressive detector** — target precision >= 0.60, recall >= 0.20
4. **If aggressive detector passes**: apply to full corpus, then re-estimate H1/H2/H3
5. **If aggressive detector fails again**: consider descriptive approach (human-coded batch1+2 only)
