# Expanded H1 Presence Model Comparison Scaffold

Purpose: prepare a fixed-structure H1 humor-presence comparison between Model A (`batch1_only`) and Model B (`batch1_plus_wendys_human`). This scaffold does not run integrated corpus classification, H1 regression, H2/H3, or aggressive/type classifiers.

Input:

- `20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_training/data/expanded_h1_presence_training_dataset.csv`

Model structure for both models:

- word-level TF-IDF `ngram_range=(1,2)`
- `char_wb` TF-IDF `ngram_range=(3,5)`
- `FeatureUnion`
- `LogisticRegression(solver=liblinear, C=0.1, class_weight=balanced)`

Model scopes:

- Model A: `batch1_only`, expected valid rows = 1,482
- Model B: `batch1_plus_wendys_human`, expected valid rows = 1,550
- Wendy's-held-out test rows = 68

Stage 1 checks:

```bash
python -m py_compile 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/compare_expanded_h1_presence_models.py 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/validate_expanded_h1_presence_model_comparison.py
python 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/compare_expanded_h1_presence_models.py --help
python 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/compare_expanded_h1_presence_models.py --dry-run
python 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/validate_expanded_h1_presence_model_comparison.py --check-structure
```

Stage 2 full comparison command:

```bash
python 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/compare_expanded_h1_presence_models.py
python 20260618expand/classifier_improvement/h1_presence_only/expanded_h1_presence_model_comparison/scripts/validate_expanded_h1_presence_model_comparison.py
```

Expected full-run outputs:

- `diagnostics/training_data_diagnostics.csv`
- `diagnostics/wendys_leakage_feature_diagnostic.csv`
- `results/model_comparison_metrics.csv`
- `results/model_comparison_confusion_matrices.csv`
- `results/source_aware_subset_metrics.csv`
- `results/wendys_held_out_metrics.csv`
- `results/wendys_held_out_confusion_matrix.csv`
- `results/top_feature_weights.csv`

Scope boundary: this is a model-comparison scaffold only. It does not provide H1 interpretation or hypothesis evidence.
