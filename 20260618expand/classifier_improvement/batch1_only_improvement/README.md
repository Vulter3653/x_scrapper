# batch1_only_improvement — Batch1-Only Classifier Improvement

## Purpose

Improves humor classifiers using only batch1 human labels (1,500 posts, 3 coders).
Batch2 labels are not available yet; this module maximizes information from batch1.

## Research Axes

### 1. H1-oriented: Humor Presence Classifier
- Binary task: humor (1) vs non_humor (0)
- Uncertain (presence=2) excluded from training
- Training set: 1,482 rows (humor=648, non_humor=834)
- Objective: improve OOF AUC beyond batch1 baseline (0.7674)

### 2. H2/H3-oriented: Aggressive-vs-Non-Aggressive Humor Detector
- Separate binary task: aggressive (1) vs non_aggressive_humor (0)
- Only trained on humor rows (presence=1), n=648
- Aggressive positives: n=44 (6.8% of humor rows)
- Objective: achieve precision >= 0.60 AND recall >= 0.20 (OOF-based)
- This is a NEW task separate from the 4-class type classifier

## Why Separate the Two Tasks

The 4-class type classifier (aggressive/affiliative/self_enhancing/self_defeating) failed
(batch1 macro-F1=0.3347 < 0.3448 baseline). The aggressive class is the critical bottleneck
for H2/H3. Rather than waiting for batch2, we:
1. Improve the presence classifier with a broader feature search
2. Build a dedicated aggressive detector focusing only on the one class needed for H2/H3

## 4-class Type Classifier Status

The original 4-class type classifier (`train_domain_adapted_humor_type_classifier.py`) is
demoted to **secondary diagnostic only** in this module. It is not the primary model.
Its batch1 results are not improved here — the aggressive detector is the replacement path.

## What Remains Blocked

- Full corpus application (`apply_domain_adapted_classifier.py`): BLOCKED
- H1/H2/H3 regression re-estimation: BLOCKED
- These require validated classifiers. Batch1 alone is not sufficient.

## Batch2

Batch2 labels (500 rows × 3 coders = 1,500 additional posts) are not used here.
When batch2 is received, re-training should combine batch1+batch2.

## Directory Structure

```
batch1_only_improvement/
├── README.md
├── data/
│   ├── batch1_presence_training_data.csv      (1,482 rows)
│   ├── batch1_aggressive_detector_training_data.csv (648 rows)
│   └── batch1_training_data_diagnostics.csv
├── results/
│   ├── presence_model_comparison_cv.csv        (OOF AUC across 40+ configs)
│   ├── presence_oof_confusion_matrix.csv       (OOF-based, best model)
│   ├── presence_cv_threshold_sensitivity.csv   (CV-based, NOT in-sample)
│   ├── aggressive_detector_model_comparison_cv.csv
│   ├── aggressive_detector_threshold_cv.csv    (OOF-based sweep)
│   ├── aggressive_detector_oof_confusion_matrix.csv
│   ├── firm_held_out_presence_results.csv
│   └── firm_held_out_aggressive_results.csv
├── reports/
│   ├── batch1_only_model_improvement_report.md
│   ├── claim_boundaries.md
│   └── next_step_decision.md
└── scripts/
    ├── build_batch1_only_training_datasets.py
    ├── run_batch1_presence_model_search.py
    ├── run_batch1_aggressive_detector_search.py
    ├── evaluate_batch1_only_models.py
    └── validate_batch1_only_improvement_outputs.py
```

## Evaluation Design

All metrics are out-of-fold (OOF) or cross-validated. No in-sample metrics are used for
model selection or threshold selection.

- Presence: StratifiedKFold(5) OOF → AUC, F1, PR-AUC, firm-held-out F1
- Aggressive: StratifiedKFold(5) OOF + RepeatedStratifiedKFold(5×5) → PR-AUC, precision, recall
- Threshold selection: OOF probability sweep (not in-sample)
- Firm-held-out: leave-one-firm-out (all firms)

## Provisional Usability Criteria

| Classifier      | Criterion                          | Basis         |
|---|---|---|
| Presence        | OOF AUC >= 0.75                    | OOF 5-fold CV |
| Aggressive det. | precision >= 0.60 AND recall >= 0.20 | OOF 5-fold CV |

Not meeting criteria → "not usable for H2/H3 main analysis."
