# H1 Presence Classifier Performance Memo

**Date:** 2026-06-18
**Stage:** Classifier performance review (pre-H1 regression)
**Scope:** H1 only — binary humor presence; H2/H3 excluded

---

## 1. Data Summary

| Metric | Value |
|---|---|
| Total batch1 rows | 1,500 |
| Uncertain excluded (presence=2) | 18 |
| Binary valid rows | 1,482 |
| humor (presence=1) | 648 (43.7%) |
| non_humor (presence=0) | 834 (56.3%) |
| Unique firms | 97 |
| Coding source | 3 human coders, batch1 only |
| batch2 used | NO |

---

## 2. Model Summary

| Item | Value |
|---|---|
| Best model (by OOF AUC) | `word_char_comb__lr_liblin_C01` |
| Vectorizer | word(1,2) + char_wb(3,5) FeatureUnion, max_features=5000+5000 |
| Classifier | LogisticRegression(liblinear, C=0.1, class_weight=balanced) |
| Feature insight | char(3,5) ngrams drove AUC improvement over word-only |
| Evaluation | OOF StratifiedKFold(5, random_state=42) — no in-sample metrics |

---

## 3. Performance Results

### 3.1 OOF Cross-Validation (Primary)

| Metric | Best model | batch1 baseline (3aade94) | Change |
|---|---|---|---|
| OOF AUC | **0.7811** | 0.7674 | +0.0137 |
| OOF F1 | **0.6792** | 0.6570 | +0.0222 |
| OOF Precision | — | — | — |
| OOF Recall | — | — | — |
| Evaluation basis | OOF 5-fold CV | fold-averaged 5-fold CV | (comparable) |

Provisional AUC threshold (>= 0.75): **PASS**

### 3.2 Firm-Held-Out (Secondary, Cross-Firm Generalizability)

| Metric | Best model | batch1 baseline (3aade94) |
|---|---|---|
| Firm-held-out F1 | 0.4770 | 0.5333 |
| N firms evaluated | 97 (all firms) | 10 (first 10 only) |
| Evaluation basis | leave-one-firm-out, all 97 firms | partial (10 firms) |

Note: The baseline firm-held-out F1=0.5333 used only the first 10 firms. When evaluated
on all 97 firms, the best model achieves 0.4770. The gap reflects:
1. The baseline evaluated on a non-representative subset.
2. Brand linguistic leakage in random CV inflates OOF AUC relative to firm-held-out.

Best firm-held-out model: `word_char_comb__lr_lbfgs_bal`, FH F1=0.5047 (97 firms).

### 3.3 OOF vs Firm-Held-Out Gap

- OOF F1 = 0.6792 vs Firm-HO F1 = 0.4770 → gap of 0.2022
- This gap is the primary evidence of **brand linguistic leakage** in random CV.
- Same-brand tweets appear in both train and validation folds in random CV.
- Firm-held-out is the appropriate metric for claiming cross-firm generalizability.
- Cross-firm generalization claims should cite firm-held-out F1 (~0.48-0.50), not OOF F1.

---

## 4. Interpretation Boundary

### What this classifier can support

The batch1-only presence classifier (`word_char_comb__lr_liblin_C01`) is:

- Provisionally passing the OOF AUC threshold (0.7811 >= 0.75).
- Capable of supporting **preliminary H1-oriented interpretation**.
- A useful **diagnostic tool** to characterize humor presence in Fortune 100 posts.

### What this classifier cannot support

- Cross-firm generalization claims beyond OOF AUC (firm-held-out F1 ~0.48).
- Definitive H1 hypothesis testing (requires full corpus application + regression).
- Type-level interpretation (aggressive, affiliative, etc.) — scope excluded.
- Claims about humor rate in the full 65,245-post corpus.

### Key limitation: brand leakage

The OOF AUC (0.7811) is likely optimistic due to same-brand tweets leaking across folds.
The firm-held-out F1 (0.4770-0.5047) is the more conservative and appropriate bound
for claims about generalizability across firms.

---

## 5. Is This Classifier Suitable for Provisional H1 Interpretation?

**Yes, with explicit limitations.**

Conditions:
1. Claims are labeled as **"provisional"** or **"preliminary"**.
2. Metrics cited are OOF AUC (not firm-held-out F1) for in-distribution performance.
3. Cross-firm claims cite firm-held-out F1 (~0.48-0.50) with appropriate caveats.
4. The classifier is described as batch1-only, not final.
5. H1 regression (if run) is reported as **exploratory**, not confirmatory.

**The classifier is not deployment-ready and H1 regression is not yet validated.**

See `h1_claim_boundaries.md` and `h1_next_step_decision.md` for full decision rules.
