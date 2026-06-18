# Workflow Guide — Fortune Top 100 Classifier Improvement

## Execution Stages

### Stage 1: Generate Labeling Candidates (runs now)

```bash
python 20260618expand/classifier_improvement/scripts/build_fortune_labeling_candidates.py --sample-size 1500
python 20260618expand/classifier_improvement/scripts/build_human_labeling_template.py
```

### Stage 2: Human Labeling (manual)

Fill in the template:
```
20260618expand/classifier_improvement/data/human_labeling_template/fortune100_human_labeling_template.csv
```

Required columns: `human_humor_presence`, `human_humor_type`, `human_confidence`, `reviewer_id`

Target: ≥500 presence labels, ≥200 typed humor labels

### Stage 3: Train Classifiers

```bash
PYTHONPATH=/home/user/.local/pypackages \
  python 20260618expand/classifier_improvement/scripts/train_domain_adapted_humor_presence_classifier.py

PYTHONPATH=/home/user/.local/pypackages \
  python 20260618expand/classifier_improvement/scripts/train_domain_adapted_humor_type_classifier.py
```

### Stage 4: Apply to Full Corpus (after validation)

```bash
PYTHONPATH=/home/user/.local/pypackages \
  python 20260618expand/classifier_improvement/scripts/apply_domain_adapted_classifier.py
```

### Stage 5: Validate

```bash
python 20260618expand/classifier_improvement/scripts/validate_classifier_improvement_outputs.py
```

## GitHub Actions (manual trigger)

Workflow: `.github/workflows/run-fortune100-classifier-improvement.yml`

Navigate to:
```
https://github.com/Vulter3653/x_scrapper/actions/workflows/run-fortune100-classifier-improvement.yml
```

Inputs:
- `mode`: build_candidates | train_smoke | evaluate | full_apply
- `sample_size`: default 1500
- `commit_results`: default false

## Execution Boundaries

- No X scraping
- No X API calls
- No raw data modification
- All outputs to `20260618expand/classifier_improvement/` only
