# Integrated H1 Classification Memo

## Source Composition

The integrated collected corpus combines existing repo post-level data from Fortune 100 processed output, Fortune raw append workflow output, and usable legacy brand post files.

See `data/integrated_corpus_source_diagnostics.csv` for source-level row counts, duplicate removal, date coverage, and usability notes.

## Append Workflow Reflection

The June 18 append workflow is explicitly reflected via:

- `.github/workflows/append-humor-collection-102-companies.yml`
- `data/audit/humor_collection_append_summary.csv`
- `data/audit/humor_collection_append_failed_targets.csv`
- `data/raw/fortune_x_2025_ranked/`
- `data/wendys/posts.json`
- `data/cocacola/posts.json`
- `data/moonpie/posts.json`

Append reflection details are stored in `data/append_workflow_reflection.csv`.

## Dedupe Rule

Deduplication prioritizes stable tweet identity when available. Priority is:

1. processed Fortune 100 post master
2. raw Fortune append output
3. legacy brand post files

Duplicates are removed by the integrated dedupe key, preferring higher-priority sources.

## Final Corpus

- Final integrated rows: 68,039
- Source datasets: 5
- Companies: 99
- Date range: 2009-11-26 to 2026-06-18

## H1 Presence Classification

The batch1-only provisional H1 presence classifier was fit on 1,482 valid human-labeled rows and applied to the integrated corpus.

- Mean humor probability: 0.480987
- humor_rate_t40: 0.856097
- humor_rate_t50: 0.404386
- humor_rate_t60: 0.055071

Fortune-only subset results and integrated corpus results can differ because the integrated corpus includes legacy Wendy's, MoonPie, Coca-Cola, and raw append workflow rows beyond the processed Fortune master.

## Boundary

This is H1 presence-only provisional classification. It is not H1 support evidence. H1 regression was not run. H2/H3 remain blocked. Type and aggressive classifiers were not used.
