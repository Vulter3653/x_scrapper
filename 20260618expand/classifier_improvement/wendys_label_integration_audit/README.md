# Wendy's Label Integration Audit

This folder audits whether legacy Wendy's human-coded labels can be added to the current Fortune combined training labels.

Generated files:

- `wendys_label_source_inventory.csv`: source-level inventory.
- `wendys_label_integration_audit.csv`: row-level Wendy's inclusion audit.
- `training_labels_v2_with_wendys.csv`: candidate v2 training labels, separate from existing baseline outputs.
- `training_labels_v2_distribution.csv`: current vs v2 distribution comparison.
- `wendys_label_integration_audit.md`: concise audit memo.

Boundary: this is not classifier retraining, full-corpus reclassification, or a replacement for `simple_ols_baseline_main/`.
