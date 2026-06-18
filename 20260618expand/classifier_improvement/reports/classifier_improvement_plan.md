# Classifier Improvement Plan — Fortune Top 100 Domain-Adapted Humor Classifier

## Current Stage

**Classifier improvement and human-labeling preparation.**

NOT yet: final H1/H2/H3 re-estimation using domain-adapted labels.

---

## Problem Statement

The Wendy's-trained TF-IDF + Logistic Regression classifier (model_transfer) produced:
- Aggressive humor rate: 10.5% (6,857 posts)
- Full-chain_master aggressive rate: 0.15% (95–105 posts)
- Discrepancy: ~72x

The root cause is domain mismatch. The model was trained on Wendy's fast-food competitive roasting language and over-matches Fortune 100 assertive corporate brand voice.

---

## Improvement Strategy

### Wendy's Classifier Role (baseline only)

| Allowed use | Prohibited use |
|---|---|
| Baseline classifier | Fortune Top 100 final classifier |
| Weak label generator for candidate selection | H1/H2/H3 main evidence generator |
| Active-learning disagreement signal | Aggressive humor final ground truth |
| Domain-transfer sensitivity benchmark | |

### Two-Stage Target Architecture

```
Stage 1: Humor Presence
  humor / non_humor / uncertain (abstention zone)

Stage 2: Humor Type (humor posts only)
  aggressive / affiliative / self_enhancing / self_defeating / uncertain
```

---

## Labeling Plan

| Stratum | Target N | Purpose |
|---|---|---|
| full_chain_aggressive | ~120 (all) | Ground truth aggressive humor cases |
| wendys_transfer_aggressive | 200 | Identify false positives |
| classifier_disagreement | 200 | Boundary cases |
| humor_presence_uncertain | 200 | Calibrate abstention zone |
| type_uncertain | 100 | Improve type boundaries |
| high_engagement_posts | 150 | H1/H2 relevance coverage |
| low_engagement_posts | 100 | Contrast coverage |
| firm_balanced_sample | ~97 | Firm coverage |
| random_fortune_sample | remainder | Background base rate |
| **Total** | **~1,500** | |

---

## Model Training Plan

### Presence Classifier

| Model | Status |
|---|---|
| TF-IDF + LogReg | Script ready — needs human labels |
| TF-IDF + LinearSVC + calibration | Script ready — needs human labels |

Provisional acceptance criteria (not hard gates):

```
AUC >= 0.75
F1 improvement over Wendy's transfer (CV AUC=0.7095)
```

### Type Classifier

| Model | Status |
|---|---|
| TF-IDF + Multinomial LogReg | Script ready — needs typed labels |
| TF-IDF + LinearSVC + calibration | Script ready — needs typed labels |

Provisional acceptance criteria:

```
macro-F1 > Wendy's transfer macro-F1 (0.3448)
aggressive precision >= 0.60 (provisional)
```

These are provisional thresholds. They should not be treated as fixed pass/fail gates before seeing the actual data distribution.

---

## H1/H2/H3 Connection

H1/H2/H3 main analysis should use the domain-adapted classifier only after Fortune-labeled validation demonstrates acceptable performance.

Specifically:
- **H1 main evidence**: requires domain-adapted presence classifier with AUC ≥ 0.75 on Fortune Top 100 human labels
- **H2 main evidence**: requires aggressive precision high enough to distinguish aggressive from non-humor baseline; current Wendy's transfer is unsuitable
- **H3 main evidence**: requires aggressive humor usage rate that reflects genuine Fortune Top 100 brand behavior (target: < 5%, vs. 10.5% from Wendy's transfer)

---

## Current Status

```
Stage 1 (labeling candidates): COMPLETE
Stage 2 (human labeling): PENDING — requires human reviewer input
Stage 3 (model training): PENDING — scripts ready
Stage 4 (model validation): PENDING
Stage 5 (full classification): PENDING
Stage 6 (H1/H2/H3 re-estimation): NOT YET STARTED
```

---

## Abstention Design

Presence abstention zone:

```
humor_probability >= 0.60 → humor
humor_probability <= 0.40 → non_humor
0.40 < humor_probability < 0.60 → uncertain
```

Type abstention:

```
max_type_probability >= 0.50 → assign type
max_type_probability < 0.50 → uncertain
```

This prevents over-confident misclassification, especially for aggressive humor.
