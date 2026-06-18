# MANIFEST — classifier_improvement/

## Scripts

| File | Status | Requires Human Labels | Notes |
|---|---|---|---|
| `scripts/build_fortune_labeling_candidates.py` | COMPLETE — run | No | Output: data/labeling_candidates/ |
| `scripts/build_human_labeling_template.py` | COMPLETE — run | No | Output: data/human_labeling_template/ |
| `scripts/train_domain_adapted_humor_presence_classifier.py` | READY — pending labels | Yes (presence) | AUC + F1 eval |
| `scripts/train_domain_adapted_humor_type_classifier.py` | READY — pending labels | Yes (type) | macro-F1, aggressive precision |
| `scripts/apply_domain_adapted_classifier.py` | READY — pending train | Yes | Apply to 65,245 posts |
| `scripts/validate_classifier_improvement_outputs.py` | COMPLETE | No | Run to check scaffold |

## Data

| File | Status |
|---|---|
| `data/labeling_candidates/fortune100_labeling_candidates.csv` | GENERATED (1,500 rows) |
| `data/labeling_candidates/labeling_candidate_diagnostics.csv` | GENERATED |
| `data/human_labeling_template/fortune100_human_labeling_template.csv` | GENERATED (labels empty) |
| `data/human_labeling_template/labeling_instructions_quick_ref.md` | GENERATED |
| `data/classified/fortune100_domain_adapted_humor_classification.csv` | PENDING |
| `data/evaluation/` | PENDING |
| `data/training/` | PENDING |

## Results

| File | Status |
|---|---|
| `results/presence_classifier_metrics.csv` | PENDING |
| `results/type_classifier_metrics.csv` | PENDING |
| `results/domain_transfer_comparison.csv` | PENDING |
| `results/confusion_matrices/type_confusion_matrix.csv` | PENDING |
| `results/confusion_matrices/presence_confusion_matrix.csv` | PENDING |

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
Stage 2: Human labeling           ⬜ PENDING
Stage 3: Train classifiers        ⬜ PENDING
Stage 4: Evaluate classifiers     ⬜ PENDING
Stage 5: Apply to corpus          ⬜ PENDING
Stage 6: H1/H2/H3 re-estimation  ⬜ PENDING
```
