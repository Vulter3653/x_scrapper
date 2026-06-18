# classifier_improvement — Fortune Top 100 Domain-Adapted Humor Classifier

## Purpose

This subpackage improves the Fortune Top 100 humor classifier beyond the Wendy's-trained baseline (model_transfer/).

The Wendy's-trained classifier produced aggressive humor at 10.5% of Fortune Top 100 posts vs. 0.15% in full_chain_master — a 72x discrepancy indicating domain-transfer over-classification. This package designs and implements a domain-adapted replacement.

## Current Stage

**Scaffold complete. Human labeling pending.**

NOT yet: final H1/H2/H3 re-estimation using domain-adapted labels.

## Diagnostics Row Count Note

`full_chain_source_rows` counts rows in the full_chain_master source file. It is not a post-master match count and may exceed the deduplicated Fortune post master row count. Actual post-master matching is reported separately as `full_chain_post_master_matched_tweet_ids` and must not exceed `input_post_master_rows`.

## Human Labeling Coding Scheme (Numeric)

Coders enter numbers — training scripts map these to model-internal string labels.

| Column | Input Code | Meaning |
|---|---|---|
| 유머_존재여부 | `1` | 유머 (humor) |
| 유머_존재여부 | `0` | 비유머 (non_humor) |
| 유머_존재여부 | `2` | 애매함 / 판단불가 (uncertain — excluded from training) |
| 유머_유형 | `1` | AGGRESSIVE |
| 유머_유형 | `2` | AFFILIATIVE |
| 유머_유형 | `3` | SELF-ENHANCING |
| 유머_유형 | `4` | SELF-DEFEATING |

유머_유형은 유머_존재여부 = 1인 경우에만 입력. 0 또는 2이면 공란.

See `data/human_labeling_template/coder_splits/LABELING_GUIDE.md` for full instructions.

## Architecture

Same two-stage structure as Wendy's classifier:

1. **Presence** (model output): humor / non_humor / uncertain (abstention 0.40–0.60)
2. **Type** (model output): aggressive / affiliative / self_enhancing / self_defeating / uncertain (abstain if max_prob < 0.50)

Training data: Fortune Top 100 human labels (3,000 stratified candidate posts; batch1 1,500 + batch2 1,500).

## Labeling Candidate Design

| Stratum | N | Purpose |
|---|---|---|
| full_chain_aggressive | 95 | Ground truth aggressive |
| wendys_transfer_aggressive | 200 | Identify false positives |
| classifier_disagreement | 200 | Boundary cases |
| humor_presence_uncertain | 200 | Calibrate abstention |
| type_uncertain | 100 | Type boundary cases |
| high_engagement_posts | 150 | H1/H2 coverage |
| low_engagement_posts | 100 | Contrast coverage |
| firm_balanced_sample | 97 | Firm coverage |
| random_fortune_sample | 358 | Base rate coverage |
| **Total** | **1,500** | |

## Next Steps (Human Labeling Required)

1. Fill labels in: `data/human_labeling_template/fortune100_human_labeling_template.csv`
2. `train_domain_adapted_humor_presence_classifier.py`
3. `train_domain_adapted_humor_type_classifier.py`
4. `apply_domain_adapted_classifier.py` (after validation)
5. Re-run H1/H2/H3 with domain-adapted labels

## Critical Warning: Wendy's Classifier Role

The Wendy's classifier is baseline only. It must NOT be used as:
- Fortune Top 100 final classifier
- H2/H3 main evidence generator
- Aggressive humor ground truth

See `reports/classifier_improvement_plan.md` for full design.
