# classifier_improvement — Fortune Top 100 Domain-Adapted Humor Classifier

## Purpose

This subpackage improves the Fortune Top 100 humor classifier beyond the Wendy's-trained baseline (model_transfer/).

The Wendy's-trained classifier produced aggressive humor at 10.5% of Fortune Top 100 posts vs. 0.15% in full_chain_master — a 72x discrepancy indicating domain-transfer over-classification. This package designs and implements a domain-adapted replacement.

## Current Stage

**Batch1 training complete. Type classifier does not yet pass. Batch2 labels required.**

- Presence classifier: provisionally passes random 5-fold CV AUC threshold (AUC=0.7674). Not deployment-ready.
- Type classifier: does not pass provisional threshold (macro-F1=0.3347 < 0.3448 baseline). Not usable.
- NOT yet: full corpus application, H1/H2/H3 re-estimation.

## Diagnostics Row Count Note

`full_chain_source_rows` counts rows in the full_chain_master source file. It is not a post-master match count and may exceed the deduplicated Fortune post master row count. Actual post-master matching is reported separately as `full_chain_post_master_matched_tweet_ids` and must not exceed `input_post_master_rows`.

## Human Labeling Coding Scheme (Numeric)

Coders enter numbers — training scripts map these to model-internal string labels.

| Column | Input Code | Meaning |
|---|---|---|
| 유머_존재여부 | `1` | 유머 (humor) |
| 유머_존재여부 | `0` | 비유머 (non_humor) |
| 유머_존재여부 | `2` | 애매함 / 판단불가 (uncertain — excluded from training) |
| 유머_유형 | `1` | AGGRESSIVE |
| 유머_유형 | `2` | AFFILIATIVE |
| 유머_유형 | `3` | SELF-ENHANCING |
| 유머_유형 | `4` | SELF-DEFEATING |

유머_유형은 유머_존재여부 = 1인 경우에만 입력. 0 또는 2이면 공란.

See `data/human_labeling_template/coder_splits/LABELING_GUIDE.md` for full instructions.

## Architecture

Same two-stage structure as Wendy's classifier:

1. **Presence** (model output): humor / non_humor / uncertain (abstention 0.40–0.60)
2. **Type** (model output): aggressive / affiliative / self_enhancing / self_defeating / uncertain (abstain if max_prob < 0.50)

Training data: Fortune Top 100 human labels (3,000 stratified candidate posts; batch1 1,500 + batch2 1,500).

## Labeling Candidate Design

| Stratum | N | Purpose |
|---|---|---|
| full_chain_aggressive | 95 | Ground truth aggressive |
| wendys_transfer_aggressive | 200 | Identify false positives |
| classifier_disagreement | 200 | Boundary cases |
| humor_presence_uncertain | 200 | Calibrate abstention |
| type_uncertain | 100 | Type boundary cases |
| high_engagement_posts | 150 | H1/H2 coverage |
| low_engagement_posts | 100 | Contrast coverage |
| firm_balanced_sample | 97 | Firm coverage |
| random_fortune_sample | 358 | Base rate coverage |
| **Total** | **1,500** | |

## Batch1 Classifier Training Interpretation Notes

**These notes are mandatory reading before citing any batch1 classifier output.**

### Presence Classifier (batch1)
- Provisionally passes the random stratified 5-fold CV AUC threshold (AUC=0.7674 ≥ 0.75).
- This is a provisional threshold only. The classifier is not final deployment-ready.
- Firm-held-out F1=0.5333 is weaker than random CV F1=0.657. Cross-firm generalization claims must be limited.
- Brand linguistic leakage is possible in random 5-fold CV (same-brand tweets in both train and validation folds).

### Type Classifier (batch1)
- Does not pass the provisional validation threshold (macro-F1=0.3347 < 0.3448 Wendy's baseline).
- Aggressive humor classification is not reliable: CV precision=0.1154, recall=0.0682.
- Aggressive humor classification must NOT be used as H2/H3 main analysis evidence.
- Self-defeating class also unreliable (n=24, CV recall=0.0833).
- Batch2 labels are required before type or aggressive classification can be considered usable.

### Confusion Matrices
- `results/confusion_matrices/presence_in_sample_confusion_matrix.csv` — in-sample final-model diagnostic only.
  Fit on all 1,482 labeled rows, predicted on the same rows. In-sample F1=0.9012 vs CV F1=0.657.
  **Do not cite as validation performance.**
- `results/confusion_matrices/type_in_sample_confusion_matrix.csv` — in-sample final-model diagnostic only.
  Fit on all 648 humor rows, predicted on the same rows. In-sample aggressive precision≈0.98 vs CV precision=0.1154.
  **Do not cite as validation performance.**

### Threshold Sensitivity
- `results/threshold_sensitivity_in_sample_diagnostic.csv` — in-sample calibration diagnostic only.
  Computed by fitting on the full labeled set and sweeping thresholds on the same data.
  F1=0.9012 (threshold=0.5) and F1=0.9812 (abstention) are in-sample artifacts, not held-out validation evidence.
  **Do not cite as classifier generalization performance.**

### What Is and Is Not Permitted

| Permitted claim | Not permitted claim |
|---|---|
| "Presence classifier provisionally passes CV AUC threshold" | "Classifier is ready for full deployment" |
| "Type classifier does not yet pass" | "Type classifier is validated" |
| "Batch2 labels are required" | "H1/H2/H3 can now be tested with final labels" |
| "Aggressive humor presence is uncertain" | "Aggressive humor classification is reliable" |

## Next Steps

1. Receive batch2 labels from 3 coders (500 rows each)
2. Re-train with combined batch1+batch2 (up to 3,000 posts)
3. Re-evaluate: target macro-F1 > 0.3448, aggressive precision ≥ 0.60
4. If thresholds pass: run `apply_domain_adapted_classifier.py` on 65,245 posts
5. Re-estimate H1/H2/H3 with domain-adapted labels (only after step 3 passes)

## Critical Warning: Wendy's Classifier Role

The Wendy's classifier is baseline only. It must NOT be used as:
- Fortune Top 100 final classifier
- H2/H3 main evidence generator
- Aggressive humor ground truth

See `reports/classifier_improvement_plan.md` for full design.
