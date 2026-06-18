# Humor Type Leakage-Filtered Diagnostics

Minimal commands:

```bash
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/build_leakage_token_inventory.py
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/build_leakage_filtered_type_datasets.py
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/evaluate_aggressive_leakage_filtered_detector.py
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/evaluate_type_leakage_filtered_classifier.py
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/summarize_leakage_filtered_results.py
python 20260618expand/classifier_improvement/humor_type_leakage_filtered/scripts/validate_leakage_filtered_experiments.py
```

Scope: classifier diagnostics only. No integrated corpus reclassification, H1/H2/H3 regression, scraping, Playwright, X API, dashboard edits, raw-data edits, workflow edits, yearly backfill edits, or deployment artifact.
