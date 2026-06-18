# Integrated Collected Corpus H1 Presence Classification

## Purpose

This package builds an integrated collected post corpus from post-level data already present in the repository, then applies the provisional H1 presence-only classifier to that integrated corpus.

This is not limited to the Fortune 100 processed master. Fortune 100 is one source within the integrated collected corpus.

## Included Sources

Included usable post-level sources:

- `20260618expand/data/processed/fortune100_post_master.csv`
- `data/raw/fortune_x_2025_ranked/`
- `data/wendys/posts.json`
- `data/cocacola/posts.json`
- `data/moonpie/posts.json`

The June 18 append workflow reflection is documented in:

- `data/append_workflow_reflection.csv`

## Classifier

- Model: `word_char_comb__lr_liblin_C01`
- Vectorizer: word(1,2) + char_wb(3,5) `FeatureUnion`
- Classifier: `LogisticRegression(liblinear, C=0.1, class_weight=balanced)`
- Training scope: batch1 human labels only
- Valid training rows: 1,482
- Humor labels: 648
- Non-humor labels: 834
- Uncertain labels excluded: 18
- Status: provisional / H1 presence-only

## Outputs

Data:

- `data/integrated_collected_post_corpus.csv`
- `data/integrated_corpus_source_diagnostics.csv`
- `data/append_workflow_reflection.csv`
- `data/integrated_h1_presence_classified_posts.csv`
- `data/integrated_h1_presence_classification_summary.csv`
- `data/integrated_h1_presence_by_source_summary.csv`
- `data/integrated_h1_presence_by_firm_summary.csv`

Temporal results and figures are under `results/` and `figures/`.

Reports:

- `reports/integrated_h1_classification_memo.md`
- `reports/integrated_temporal_distribution_memo.md`
- `reports/integrated_h1_claim_boundaries.md`

## Scope Boundary

This output provides provisional H1 humor-presence labels for future analysis.
It does not run H1 regression, H2/H3 analysis, type classification, aggressive detection, fixed effects, controls, robust standard errors, or causal interpretation.
