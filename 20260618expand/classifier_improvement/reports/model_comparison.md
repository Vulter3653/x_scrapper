# Model Comparison Plan

## Models Under Comparison

| Model ID | Stage | Architecture | Status |
|---|---|---|---|
| wendy_tfidf_logreg | Baseline | TF-IDF + LogReg trained on 597 Wendy's labels | Complete (model_transfer/) |
| fortune_tfidf_logreg | Domain-adapted | TF-IDF + LogReg trained on Fortune100 human labels | Pending labels |
| fortune_tfidf_svm | Domain-adapted | TF-IDF + LinearSVC + calibration | Pending labels |

## Key Comparison Metrics

### Presence Classifier

| Metric | Wendy's Transfer (CV) | Target (provisional) |
|---|---|---|
| AUC | 0.7095 | ≥ 0.75 |
| F1 | 0.6937 | Improvement over baseline |
| CV mode | On Wendy's 597 labels | On Fortune100 labels |

### Type Classifier

| Metric | Wendy's Transfer (CV) | Target (provisional) |
|---|---|---|
| macro-F1 | 0.3448 | > 0.3448 |
| aggressive precision | Unknown | ≥ 0.60 (provisional) |
| aggressive recall | Unknown | Documented |

### Distribution Comparison (Full Corpus)

| Metric | Wendy's Transfer | Domain-Adapted (post-labeling) |
|---|---|---|
| humor_presence_rate | 43.2% | TBD |
| aggressive_rate | 10.5% | Expected < 5% |
| affiliative_rate | 29.3% | TBD |
| self_enhancing_rate | 3.1% | TBD |
| self_defeating_rate | 0.3% | TBD |

## Evaluation Modes

1. Random 5-fold CV on labeled Fortune Top 100 data
2. Firm-held-out validation (leave-one-firm-out on subset)
3. Distribution comparison: aggressive rate before/after domain adaptation

## Decision Rule

Domain-adapted classifier should be used as the main Fortune Top 100 classifier if:
- AUC ≥ 0.75 on Fortune Top 100 human labels (provisional)
- macro-F1 > Wendy's transfer model (0.3448)
- aggressive rate plausibly reflects true Fortune 100 aggressive humor usage (expected < 5%)

If these criteria are not met, the classifier should be treated as a further-improved exploratory tool, not the main analysis input.
