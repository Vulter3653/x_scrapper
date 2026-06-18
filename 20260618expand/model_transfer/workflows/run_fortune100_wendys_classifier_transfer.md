# Workflow Guide: Fortune 100 Wendy's Classifier Transfer

## Purpose

Runs the Wendy's humor classifier on Fortune Top 100 posts and executes H1/H2/H3 regressions.

## Local Execution (all scripts available locally)

```bash
# Step 1: Apply classifier (requires sklearn)
PYTHONPATH=/home/user/.local/pypackages \
  python3 20260618expand/model_transfer/scripts/apply_wendys_classifier_to_fortune100.py

# Step 2: Build regression-ready datasets
python3 20260618expand/model_transfer/scripts/build_hypothesis_datasets_from_new_classification.py

# Step 3: Run regressions
PYTHONPATH=/home/user/.local/pypackages \
  python3 20260618expand/model_transfer/scripts/run_h1_h2_h3_models.py

# Step 4: Validate
python3 20260618expand/model_transfer/scripts/validate_model_transfer_outputs.py
```

## GitHub Actions (manual trigger)

Workflow file: `.github/workflows/run-fortune100-wendys-classifier-transfer.yml`

Navigate to:
```
https://github.com/Vulter3653/x_scrapper/actions/workflows/run-fortune100-wendys-classifier-transfer.yml
```

Click **Run workflow** and select:

| Input | Options | Default |
|---|---|---|
| run_mode | smoke / full | smoke |
| max_posts | number (smoke only) | 500 |
| commit_results | false / true | false |

`run_mode: smoke` → runs on first 500 posts only (quick check).
`run_mode: full` → runs on all 65,245 posts (full production run).
`commit_results: true` → commits outputs back to the branch.

## Input/Output Boundaries

- Input: `20260618expand/data/processed/fortune100_post_master.csv`
- Training labels: `20260615wendy's/result/wendys_humor_review_sheet.csv`
- Outputs: all in `20260618expand/model_transfer/`
- No raw data files are modified.
