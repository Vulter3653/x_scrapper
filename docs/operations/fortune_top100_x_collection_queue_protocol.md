# Fortune Top 100 Verified X Collection Queue Protocol

## Purpose

`config/fortune2025_top100_verified_x_collection_queue.csv` is a planning scaffold for a future Fortune 2025 Top 100 X collection run. It is not a scraping command, not an API call list, and not approval to collect timelines.

The queue is derived only from `config/fortune2025_x_account_verification_master.csv` rows that already pass the verification gate.

## Source Rule

A row may enter the queue only when all conditions are true:

- `scrape_eligible=true`
- `official_x_account_status` is `official` or `brand_official`
- `official_x_handle` is not empty
- `official_x_url` is not empty
- `evidence_source_url` is not empty
- `confidence` is `high` or `medium`
- `evidence_strength` is not `none`, `level_6`, `level_7`, or `level_8`
- `evidence_source_type` is not `manual_search_only` or `not_reviewed`

Rows with `unknown`, `ambiguous`, `no_account_found`, `inaccessible`, `subsidiary_only`, or `do_not_scrape` must not enter the queue.

## Default Queue State

Every scaffold row starts with:

- `collection_status=queued_not_collected`
- `collection_priority=top100_verified`
- `collection_scope=timeline_posts_if_accessible`
- `collection_start_policy=to_be_defined_before_collection`
- `collection_end_policy=to_be_defined_before_collection`
- `max_posts_policy=to_be_defined_before_collection`

These defaults intentionally prevent silent collection. Start/end policy, maximum posts, access method, rate controls, and audit output must be defined before any future collection command is authorized.

## Claim Boundaries

This queue authorizes future collection planning only. It does not authorize scraping yet.

Future X post coverage will not be a complete historical archive. It will be limited to retrievable timeline posts under the implemented access method.

Humor classification and sentiment labels remain model-generated unless manual audit evidence exists. Dashboard analytics remain descriptive only and authorize no causal claims.

The unresolved SEC 10-K fetch failure does not affect account queue eligibility. It still blocks financial-text linkage, 10-K based AI disclosure analysis, and fiscal correlation claims where report-body download status is not an audited success.

The current blocked rows remain excluded: 12 `inaccessible` rows and 45 `no_account_found` rows must not enter the queue.

## Validation

Run:

```bash
python scripts/validate_fortune_x_collection_queue.py
```

The validator is local/static only. It does not read secrets, scrape X, call X APIs, download SEC filings, trigger workflows, or modify `data/` or `dashboard/data/`.
