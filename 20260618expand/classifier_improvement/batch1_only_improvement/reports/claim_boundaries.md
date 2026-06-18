# Claim Boundaries — batch1_only_improvement

## Absolute Prohibited Claims

These claims must NEVER appear in any report, paper, or presentation using this module's outputs.

| Prohibited claim | Why prohibited |
|---|---|
| "Final classifier is ready" | batch1 presence=provisional only; type/agg not validated |
| "H1/H2/H3 can now be tested with final labels" | Full corpus classification is blocked |
| "Type classifier is validated" | 4-class type classifier failed (macro-F1=0.3347 < 0.3448) |
| "Aggressive humor classification is reliable" | n=44 positives; OOF precision unstable |
| "Batch1 solves the type classifier problem" | batch2 still required for reliable type CV |
| "Aggressive detector achieves X precision" (without OOF basis) | In-sample precision is inflated |
| "H2/H3 main analysis can proceed" | Blocked until validated classifier is applied to full corpus |

## H2/H3 Status

**H2/H3 regression is BLOCKED.**

To unblock:
1. Aggressive detector must pass OOF precision >= 0.60 AND recall >= 0.20
2. Validated detector must be applied to full Fortune 100 corpus
3. H1/H2/H3 can then be estimated with domain-adapted labels

Current status: neither condition is met.

## What CAN Be Claimed from batch1_only_improvement

| Permitted claim | Condition |
|---|---|
| "Presence classifier provisionally passes OOF AUC >= 0.75" | Only if OOF AUC >= 0.75 |
| "Aggressive detector achieves precision X at threshold Y (OOF)" | Only if OOF-based, clearly labeled |
| "Best batch1 presence model: [name], OOF AUC=[X]" | Always OK |
| "Aggressive detector does not yet meet provisional criteria" | If precision < 0.60 or recall < 0.20 |
| "Batch2 labels required for reliable aggressive classification" | Always true |
| "4-class type classifier: secondary diagnostic only" | Always |

## Threshold Claims

Thresholds in `aggressive_detector_threshold_cv.csv` are derived from OOF predictions.
Any claim about threshold-tuned precision/recall must cite:
- "OOF-based threshold" or "CV-based threshold"
- The actual threshold value
- The coverage rate at that threshold

In-sample threshold values from the old `threshold_sensitivity_in_sample_diagnostic.csv`
must NOT be cited as validation evidence.

## Firm-Held-Out vs Random CV

Firm-held-out F1 is lower than random 5-fold CV F1 (expected — brand leakage in random CV).
When claiming cross-firm generalizability, cite firm-held-out F1, not random CV F1.

## Full Corpus Application

`apply_domain_adapted_classifier.py` is BLOCKED. No classification of the 65,245 Fortune 100
post corpus is permitted until:
1. Aggressive detector passes provisional criteria
2. Classification script is reviewed and re-enabled
