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

## Results Summary

| Hypothesis | Result | Note |
|---|---|---|
| H1: humor → engagement | β=-0.052*** (p<.001) | NOT supported; negative direction |
| H2: aggressive > other humor | aggressive β=-0.100, lower than affiliative | NOT supported; aggressive has lowest coefficient |
| H3: inverted-U aggressive intensity | β1=-1.65***, β2=2.53*** (U-shape) | NOT supported; shape is U, not inverted-U |

## Classifier Transfer Caveat

The model was trained on Wendy's fast-food brand voice. Fortune Top 100 posts span
diverse industries. Aggressive humor rate under the transferred model is 10.5% vs
0.15% in the original full_chain_master — likely due to domain mismatch.
All results should be treated as exploratory model-transfer evidence.

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
