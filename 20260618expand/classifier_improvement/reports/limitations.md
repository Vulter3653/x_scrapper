# Limitations — Classifier Improvement Package

## Domain-Transfer Risk

The Wendy's-trained classifier was built on 597 labeled Wendy's posts from a single fast-food brand with a distinctive aggressive/competitive brand voice. Applying it to Fortune Top 100 companies across diverse industries introduces systematic domain-transfer measurement error:

- Wendy's aggressive humor patterns (competitive taunting, fast-food roasting) do not map cleanly onto Fortune 100 corporate assertive language.
- The 72x discrepancy in aggressive humor rate (10.5% vs 0.15%) is evidence of over-transfer.
- H2 and H3 results from model_transfer should not be cited as main evidence.

## Human Label Coverage

Even after collecting 1,500 human-labeled posts, this covers only 2.3% of the 65,245-post Fortune Top 100 sample. The domain-adapted classifier must generalize from this labeled sample to the full corpus. Generalization quality should be assessed with firm-held-out validation.

## Aggressive Humor Rarity

The full_chain_master has only 95–105 aggressive humor posts across the full corpus. Even with aggressive oversampling, the labeled set will contain few genuine aggressive humor cases. The type classifier aggressive precision and recall should be interpreted with caution given the small true positive count.

## Provisional Acceptance Thresholds

The acceptance thresholds stated in classifier_improvement_plan.md are provisional estimates, not validated benchmarks. They should not be treated as guaranteed quality gates before seeing the actual Fortune Top 100 labeled data.

## Observational Evidence

Even after domain adaptation, the analysis remains observational. It does not support unrestricted causal claims about humor and engagement.

## Engagement DV

total_engagement excludes bookmark_count in Fortune Top 100. This may differ from Wendy's-only analysis DV. Direct coefficient comparison requires accounting for this difference.
