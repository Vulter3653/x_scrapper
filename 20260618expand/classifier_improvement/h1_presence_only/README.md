# h1_presence_only — H1 Humor Presence Classifier Review

## Purpose

This directory documents the **classifier performance review** for H1 hypothesis testing.

The scope is limited to:
- Binary humor presence classification (humor vs non_humor)
- batch1 human labels only (1,500 posts, 3 coders)
- Performance evaluation of the best-identified presence classifier

## What This Is NOT

- This is NOT a H1 regression analysis.
- This is NOT full corpus classification.
- type classifier, aggressive detector, H2/H3 are entirely excluded from this scope.

## Research Scope Reduction

Prior scope:
- H1: humor presence
- H2: aggressive vs other humor type
- H3: aggressive intensity / moderation

Current scope (this directory):
- **H1 only** — binary humor presence classification
- type classifier: NOT used
- aggressive detector: NOT used
- H2/H3: BLOCKED / future work

## Current Stage

**Stage 1 (complete):** Classifier performance review — see `h1_presence_classifier_performance_memo.md`.

**Stage 2 (complete):** Full corpus H1 presence classification — see `full_corpus_classification/`.
- The batch1-only presence classifier was applied to all 65,245 Fortune 100 posts.
- Output is provisional / exploratory only.
- H1 regression has NOT been run.
- Classification output is the input for a future exploratory H1 regression.

**Stage 3 (pending):** H1 exploratory regression — NOT yet executed.

## Source Results

All performance numbers referenced here come from:
- `../batch1_only_improvement/results/presence_model_comparison_cv.csv`
- `../batch1_only_improvement/results/firm_held_out_presence_results.csv`
- `../batch1_only_improvement/results/presence_cv_threshold_sensitivity.csv`

Source files are not modified. This directory contains interpretation documents only.

## Files

| File | Content |
|---|---|
| `h1_presence_classifier_performance_memo.md` | Data, model, metrics, interpretation boundary |
| `h1_claim_boundaries.md` | Permitted and prohibited claims |
| `h1_next_step_decision.md` | Decision options for next stage |

## full_corpus_classification/

| File | Content |
|---|---|
| `scripts/apply_h1_presence_only_classifier.py` | Fits model on batch1 labels, classifies 65,245 posts |
| `scripts/validate_h1_full_corpus_classification.py` | Validates all outputs |
| `data/fortune100_h1_presence_classified_posts.csv` | 65,245 posts with h1_humor_presence_probability + t40/t50/t60 labels |
| `data/fortune100_h1_presence_classification_summary.csv` | Corpus-level summary stats |
| `data/fortune100_h1_presence_by_firm_summary.csv` | Firm-level humor rate summary (97 firms) |
| `reports/h1_full_corpus_classification_memo.md` | Classification memo and threshold guidance |
| `reports/h1_full_corpus_classification_claim_boundaries.md` | Permitted / prohibited claims |

**H2/H3 remain BLOCKED. H1 regression is not yet executed.**

## 2026-06-19 Integrated Corpus Scope Correction

Earlier `full corpus` wording in this H1 presence-only area refers to the Fortune 100 subset based on `20260618expand/data/processed/fortune100_post_master.csv` unless explicitly stated otherwise. Those 65,245-row outputs should be interpreted as Fortune 100 subset classification or Fortune 100 subset simple OLS checks, not as the final integrated collected corpus.

The integrated collected corpus output is maintained separately at `20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/`. It includes Fortune 100 sources plus usable existing legacy brand post datasets such as Wendy's, MoonPie, and Coca-Cola, and reflects the June 18 append workflow audit/raw outputs. Integrated-corpus H1 regression has not been run. H2/H3 remain blocked. Type and aggressive classifiers are not used.

