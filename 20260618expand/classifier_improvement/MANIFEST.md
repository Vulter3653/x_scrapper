# MANIFEST — classifier_improvement/

## Scripts

| File | Status | Requires Human Labels | Notes |
|---|---|---|---|
| `scripts/build_fortune_labeling_candidates.py` | COMPLETE — run | No | Output: data/labeling_candidates/ |
| `scripts/build_human_labeling_template.py` | COMPLETE — run | No | Output: data/human_labeling_template/ |
| `scripts/train_domain_adapted_humor_presence_classifier.py` | COMPLETE — batch1 trained | Yes (presence) | AUC + F1 eval; confusion matrix is in-sample |
| `scripts/train_domain_adapted_humor_type_classifier.py` | COMPLETE — batch1 trained | Yes (type) | macro-F1, aggressive precision; does not yet pass |
| `scripts/apply_domain_adapted_classifier.py` | BLOCKED — type/aggressive not validated | Yes | Full 2-stage type application; blocked pending validated type classifier |
| `h1_presence_only/full_corpus_classification/scripts/apply_h1_presence_only_classifier.py` | COMPLETE — presence-only provisional | Yes | Applied to 65,245 posts; H1 presence labels only; H1 regression not yet run |
| `scripts/validate_classifier_improvement_outputs.py` | COMPLETE | No | Run to check scaffold |

## Data

| File | Status |
|---|---|
| `data/labeling_candidates/fortune100_labeling_candidates.csv` | GENERATED (1,500 rows) |
| `data/labeling_candidates/labeling_candidate_diagnostics.csv` | GENERATED |
| `data/human_labeling_template/fortune100_human_labeling_template.csv` | COMPLETE — batch1 labels injected (1,482 binary + 18 uncertain) |
| `data/human_labeling_template/labeling_instructions_quick_ref.md` | GENERATED |
| `data/classified/fortune100_domain_adapted_humor_classification.csv` | PENDING |
| `data/evaluation/` | PENDING |
| `data/training/` | PENDING |

## Results

| File | Status |
|---|---|
| `results/presence_classifier_metrics.csv` | COMPLETE — batch1 CV metrics (5-fold stratified) |
| `results/type_classifier_metrics.csv` | COMPLETE — batch1 CV metrics; does not pass provisional threshold |
| `results/threshold_sensitivity_in_sample_diagnostic.csv` | COMPLETE — IN-SAMPLE ONLY; not held-out validation |
| `results/domain_transfer_comparison.csv` | PENDING |
| `results/confusion_matrices/presence_in_sample_confusion_matrix.csv` | COMPLETE — IN-SAMPLE ONLY; not CV performance |
| `results/confusion_matrices/type_in_sample_confusion_matrix.csv` | COMPLETE — IN-SAMPLE ONLY; not CV performance |

## Reports

| File | Status |
|---|---|
| `reports/classifier_improvement_plan.md` | COMPLETE |
| `reports/labeling_strategy.md` | COMPLETE |
| `reports/model_comparison.md` | COMPLETE |
| `reports/limitations.md` | COMPLETE |
| `reports/validation_report.md` | COMPLETE (will update post-labeling) |

## Workflows

| File | Status |
|---|---|
| `.github/workflows/run-fortune100-classifier-improvement.yml` | COMPLETE |
| `workflows/run_classifier_improvement_workflow.md` | COMPLETE |

## Execution Status

```
Stage 1: Generate candidates      ✓ DONE
Stage 2: Human labeling           ✓ DONE (batch1: 1,500 posts, 3 coders)
Stage 3: Train classifiers        ✓ DONE (batch1) — presence PROVISIONAL PASS; type FAIL
Stage 4: Evaluate classifiers     ⚠ PARTIAL — presence OOF AUC=0.7811 (improved); type FAIL; agg FAIL
Stage 5a: Presence-only corpus    ✓ DONE (provisional) — 65,245 posts classified; H1 labels at t40/t50/t60
Stage 5b: Type/aggressive corpus  ⬜ BLOCKED — type classifier not validated; aggressive detector not usable
Stage 6a: H1 exploratory reg.     ⬜ PENDING — classification output ready; regression not yet run
Stage 6b: H2/H3 re-estimation     ⬜ BLOCKED — requires validated type/aggressive classifier
```
