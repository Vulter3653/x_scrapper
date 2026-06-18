# model_transfer — Wendy's Classifier Transfer to Fortune Top 100

This subpackage applies the same TF-IDF + Logistic Regression humor classifier
used in `20260615wendy's/` to the Fortune Top 100 post dataset, then runs
H1/H2/H3 regressions on the transferred labels.

## Classifier Architecture

Two-stage:

1. **Binary humor presence**: TF-IDF(ngram 1-2, min_df=2, sublinear_tf) + LogisticRegression(class_weight=balanced, solver=liblinear)
2. **Four-type humor**: TF-IDF(max_features=5000) + LogisticRegression(solver=lbfgs, class_weight=balanced)

Training data: `20260615wendy's/result/wendys_humor_review_sheet.csv`
- Binary labels: 597 rows
- Four-type labels: 278 humorous rows

No saved model artifact. Model retrained from Wendy's labels at runtime.

## Analysis Status

**This is an exploratory model-transfer analysis. These results should NOT be used as the main hypothesis evidence for Fortune Top 100.**

The Wendy's-trained classifier was applied to Fortune Top 100 posts as a robustness/sensitivity check. Due to domain mismatch (Wendy's fast-food brand voice vs. diverse Fortune Top 100 industries), aggressive humor classification is substantially over-estimated (10.5% vs. 0.15% in the original full_chain_master). All results reflect classifier-transfer sensitivity, not definitive hypothesis testing.

## Results Summary (Exploratory Model-Transfer)

| Hypothesis | Under-transfer result | Appropriate framing |
|---|---|---|
| H1: humor → engagement | β=-0.052*** | Wendy's-classifier transfer shows humor-labeled posts associated with lower engagement; H1 not supported under this specification |
| H2: aggressive > other humor | aggressive β=-0.100, lower than affiliative*** | Aggressive over-classified at 10.5%; H2 not supported under this specification |
| H3: inverted-U aggressive intensity | β1<0, β2>0 (U-shape, not inverted-U) | U-shape exploratory association observed; H3 not supported under this specification |

These results should be reported as:

> As an exploratory model-transfer analysis, we applied the Wendy's-trained humor classifier to the Fortune Top 100 post sample. The transferred classifier produced substantially different aggressive-humor prevalence from the full-chain classification (10.5% vs. 0.15%), suggesting domain-transfer measurement risk. Under this transferred-classifier specification, H1, H2, and H3 were not supported. These results should be interpreted as evidence of classifier-transfer sensitivity rather than definitive hypothesis evidence.

## Classifier Transfer Warning

| Metric | Value |
|---|---|
| Binary AUC (on Wendy's labeled data) | 0.7095 |
| Four-type macro-F1 (on Wendy's labeled data) | 0.3448 |
| Aggressive humor rate (full_chain_master) | 0.15% (95 posts) |
| Aggressive humor rate (this transfer) | 10.5% (6,857 posts) |

The four-type macro-F1 of 0.34 is low. Wendy's aggressive humor patterns (competitive fast-food roasting language) likely match assertive but non-humorous Fortune 100 brand language. Over-classification of aggressive humor contaminates H2 and H3 results.

## Execution (smoke test)

```bash
PYTHONPATH=/home/user/.local/pypackages python3 20260618expand/model_transfer/scripts/apply_wendys_classifier_to_fortune100.py
python3 20260618expand/model_transfer/scripts/build_hypothesis_datasets_from_new_classification.py
PYTHONPATH=/home/user/.local/pypackages python3 20260618expand/model_transfer/scripts/run_h1_h2_h3_models.py
python3 20260618expand/model_transfer/scripts/validate_model_transfer_outputs.py
```

## Boundaries

- No X scraping, API calls, or new raw data collection.
- No modification to `20260615wendy's/`, `dashboard/data/`, or `data/raw/`.
- All outputs isolated to `20260618expand/model_transfer/`.
