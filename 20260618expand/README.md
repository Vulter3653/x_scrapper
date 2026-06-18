# 20260618 Fortune Top 100 Expansion

## Purpose

This isolated package extends the Wendy's-only humor and engagement analysis structure from `20260615wendy's/` to the existing Fortune Top 100 X collection data already present in the repository.

No new X collection, X API call, Playwright collection, SEC download, dashboard sync, or model inference is part of this package.

## Reference Folder

Reference folder: `20260615wendy's/`

Reused logic:

- post-level engagement proxy based on engagement counts
- full-sample model-based humor presence/type as primary empirical evidence
- human-coded labels as supplemental validation only
- post format controls limited here to `text_length`, `hashtag_count`, and `mention_count`
- H3 usage intensity as firm/period humor usage rate, not semantic intensity

## Expansion Target

Current repository data:

- `data/raw/fortune_x_2025_ranked/`
- `data/audit/fortune_x_2025_ranked_collection_summary.csv`
- `config/fortune2025_top100_verified_x_collection_queue.csv`
- `config/fortune2025_x_account_verification_master.csv`
- `data/derived/humor/`

## Outputs

- `data/processed/fortune100_post_master.csv`
- `data/processed/fortune100_post_master.json`
- `data/processed/fortune100_humor_variables.csv`
- `data/processed/fortune100_firm_period_panel.csv`
- `data/regression_ready/fortune100_post_level_regression_ready.csv`
- `data/regression_ready/fortune100_firm_period_regression_ready.csv`
- `data/regression_ready/fortune100_h1_h2_h3_regression_ready.csv`
- `data/diagnostics/fortune100_collection_coverage.csv`
- `data/diagnostics/fortune100_missingness_summary.csv`
- `data/diagnostics/fortune100_duplicate_tweet_audit.csv`
- `data/diagnostics/fortune100_humor_classification_coverage.csv`

## Analysis Units

- H1: post-level
- H2: post-level
- H3: firm-month by default, subject to coverage diagnostics

## Execution

Run in order:

```bash
python 20260618expand/scripts/build_fortune100_post_master.py
python 20260618expand/scripts/build_fortune100_humor_variables.py
python 20260618expand/scripts/build_fortune100_firm_period_panel.py
python 20260618expand/scripts/build_fortune100_regression_ready.py
python 20260618expand/scripts/validate_20260618expand_outputs.py
```

For a long or CI-controlled run, use GitHub Actions manual execution with the same commands. The workflow should not include collection, scraping, model inference, SEC download, or dashboard sync steps.

## Validation

The validation script checks required outputs, required columns, JSON parseability, and package isolation. It is a static validation of generated artifacts, not a regression result validator.

## Claim Boundary

The resulting datasets are observational hypothesis-testing inputs based on already collected observable X posts. They should not be described as the full X archive, and engagement metrics should be treated as point-in-time captures.
