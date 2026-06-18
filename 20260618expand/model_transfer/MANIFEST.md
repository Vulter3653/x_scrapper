# Manifest — model_transfer

## Scripts

- `scripts/apply_wendys_classifier_to_fortune100.py`: trains Wendy's TF-IDF LogReg on Wendy's labels, applies to Fortune 100 posts.
- `scripts/build_hypothesis_datasets_from_new_classification.py`: builds H1/H2 post-level and H3 firm-month regression-ready files.
- `scripts/run_h1_h2_h3_models.py`: OLS regressions for H1, H2, H3 with firm/year FE.
- `scripts/validate_model_transfer_outputs.py`: validates required files, columns, formulas, and claim boundaries.

## Classified Data

- `data/classified/fortune100_wendys_model_humor_classification.csv`: 65,245 rows, Wendy's-model humor presence and type labels.

## Regression-Ready

- `data/regression_ready/h1_post_level_regression_ready.csv`: 65,245 rows.
- `data/regression_ready/h2_post_level_regression_ready.csv`: 65,245 rows.
- `data/processed/h3_firm_month_panel.csv`: 3,532 firm-month rows.
- `data/regression_ready/h3_firm_period_regression_ready.csv`: 3,532 rows.

## Diagnostics

- `data/diagnostics/classification_coverage.csv`
- `data/diagnostics/humor_presence_frequency.csv`
- `data/diagnostics/humor_type_frequency.csv`
- `data/diagnostics/aggressive_humor_sparsity.csv`
- `data/diagnostics/regression_sample_inclusion.csv`

## Results

- `results/h1/h1_regression_results.csv`
- `results/h2/h2_regression_results.csv`
- `results/h2/h2_aggressive_contrast_tests.csv`
- `results/h3/h3_regression_results.csv`
- `results/h3/h3_turning_point_diagnostics.csv`

## Reports

- `reports/classifier_transfer_audit.md`
- `reports/h1_results.md`
- `reports/h2_results.md`
- `reports/h3_results.md`
- `reports/limitations.md`
