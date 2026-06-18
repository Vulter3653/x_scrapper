# Validation Report — Classifier Improvement Package

## Current Status

**Scaffold complete. Human labeling pending.**

This report will be updated after human labels are collected and classifiers are trained.

## Scaffold Validation

```
python 20260618expand/classifier_improvement/scripts/validate_classifier_improvement_outputs.py
→ VALIDATION PASS (scaffold check)
```

## What Has Been Completed

- [x] Labeling candidate set generated (1,500 stratified posts)
- [x] Human labeling template created
- [x] Labeling strategy documented with domain-transfer warnings
- [x] Classifier improvement plan documented
- [x] Training scripts written (presence + type)
- [x] Evaluation scripts written
- [x] Apply-to-full-corpus script written
- [x] Validator written
- [x] GitHub Actions workflow written

## What Is Pending

- [ ] Human labeling (fill `human_humor_presence` and `human_humor_type` in template)
- [ ] Run `train_domain_adapted_humor_presence_classifier.py`
- [ ] Run `train_domain_adapted_humor_type_classifier.py`
- [ ] Review classifier metrics against provisional thresholds
- [ ] Run `apply_domain_adapted_classifier.py` (after validation pass)
- [ ] Compare domain_transfer_comparison.csv (aggressive rate before/after)
- [ ] Re-run H1/H2/H3 with domain-adapted labels

## Provisional Acceptance Criteria

These are documented targets, not guaranteed pass/fail gates:

| Criterion | Target | Status |
|---|---|---|
| Presence AUC | ≥ 0.75 | Pending |
| Type macro-F1 | > 0.3448 | Pending |
| Aggressive precision | ≥ 0.60 | Pending |
| Aggressive rate (full corpus) | < 5% | Pending |
| Firm-held-out F1 | Documented | Pending |
