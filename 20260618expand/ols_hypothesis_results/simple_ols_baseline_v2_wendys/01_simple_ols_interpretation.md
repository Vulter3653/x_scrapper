# 01 V2 Simple OLS Interpretation

This v2 run uses `training_labels_v2_with_wendys.csv` for classifier retraining and reclassifies the integrated collected corpus.

Fixed formulas are unchanged from f945aca:

- H1/H2 post-level OLS with aggressive, affiliative, self_enhancing, self_defeating dummies only; non-humorous is the reference category.
- H3 firm-quarter quadratic OLS with aggressive usage intensity and squared intensity only.
- No controls, no fixed effects, no OOF, no firm-month H3.

## V2 label/classification counts

- Full-sample aggressive posts: 2,752
- Full-sample affiliative posts: 12,746
- Full-sample self-enhancing posts: 7,563
- Full-sample self-defeating posts: 271
- Full-sample non-humorous posts: 44,707
- Human-coded v2 aggressive labels: 175

## H3 diagnostic

- beta1 intensity: 10.59015 (p=0.0)
- beta2 intensity squared: -7.841834 (p=2.5e-05)
- turning point: 0.675234
- turning point in observed range: true
- H3 supported by this simple diagnostic: true

Boundary: this is not causal evidence. It is a v2 classifier-based rerun of the already fixed simple OLS baseline.
