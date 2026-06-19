# Wendy's Label Integration Audit

## Scope

- Purpose: audit whether Wendy's human-coded labels are already reflected in the current 2,498-label training source and prepare a separate v2 training-label candidate.
- This does not replace `simple_ols_baseline_main/` and does not rerun classifier training, full-corpus classification, or OLS.
- Fixed label schema: 0=non-humorous, 1=aggressive, 2=affiliative, 3=self-enhancing, 4=self-defeating.

## Current training labels

- Current training labels path: `20260618expand/classifier_improvement/data/human_labeling_template/fortune100_human_labeling_template_combined.csv`
- Current raw rows: 2,498
- Current valid rows under 0..4 schema: 2,480
- Current excluded rows: 18
- Source interpretation: combined Fortune Top 100 batch1+batch2 coder template used by `simple_ols_baseline_main/run_simple_ols_baseline_main.py`.

## Wendy's candidate sources

| Source file | Raw rows | Usable | Reason if not usable |
|:--|--:|:--|:--|
| `data/derived/humor/human_labels/wendys_human_label_raw_linked.csv` | 69 | true |  |
| `data/manual_labels/wendys_human_humor_labels.csv` | 69 | true |  |
| `20260615wendy's/data/wendys_partial_human_coded_humor_labels.csv` | 69 | true |  |
| `20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv` | 597 | true |  |
| `20260615wendy's/data/wendys_h2_four_type_humor_dataset.csv` | 278 | true |  |
| `20260615wendy's/data/wendys_full_sample_four_type_humor_classifier_dataset.csv` | 278 | true |  |
| `20260615wendy's/data/wendys_h1_time_fe_only_dataset.csv` | 978 | false | model_prediction_only_not_human_label |
| `20260615wendy's/data/wendys_h2_full_sample_four_type_prediction_dataset.csv` | 978 | false | model_prediction_only_not_human_label |
| `20260615wendy's/result/wendys_full_sample_four_type_humor_predictions.csv` | 978 | false | model_prediction_only_not_human_label |
| `20260615wendy's/result/wendys_full_sample_four_type_humor_distribution.csv` | 5 | false | model_prediction_only_not_human_label |

## Integration audit

- Wendy's candidate raw rows scanned: 1,360
- Wendy's valid human labels after schema normalization: 1,326
- Duplicate with existing current training labels: 0
- New Wendy's labels addable to v2: 566
- Final training-label v2 N: 3,046
- Aggressive class increase: 95

### Wendy's exclusion counts

| Reason | N |
|:--|--:|
| duplicate_with_wendys_candidate | 760 |
| excluded_presence | 3 |
| humor_missing_valid_type | 31 |
| included | 566 |

## Class distribution change

| Label | Name | Current valid N | Wendy's added N | v2 N |
|:--|:--|--:|--:|--:|
| 0 | non-humorous | 1,453 | 288 | 1,741 |
| 1 | aggressive | 80 | 95 | 175 |
| 2 | affiliative | 510 | 106 | 616 |
| 3 | self-enhancing | 403 | 62 | 465 |
| 4 | self-defeating | 34 | 15 | 49 |

## Judgment

- Wendy's human-coded labels are not already represented in the current Fortune combined training template by candidate/status/text keys.
- A separate `training_labels_v2_with_wendys.csv` was generated as an integration candidate because valid human-coded Wendy's labels remain after deduplication.
- Model-prediction-only Wendy's files are explicitly excluded and are not treated as human labels.

## Next step boundary

- v2 is a classifier retraining candidate only.
- Retraining, full-corpus reclassification, and fixed simple OLS reruns require separate user approval.
