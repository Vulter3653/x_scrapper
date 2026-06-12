# Fortune Top 100 Human-Reviewed X Collection Queue Protocol

## Purpose

`config/fortune2025_top100_verified_x_collection_queue.csv` is a planning scaffold for a future Fortune 2025 Top 100 X collection run. It is not a scraping command, not an API call list, and not approval to collect timelines.

The queue now derives only from the completed human manual review overlay in `config/fortune2025_x_account_verification_master.csv`. The old `scrape_eligible` field is preliminary/reference only and must not be used as the final collection eligibility signal.

## Source Rule

A row may enter the queue only when all conditions are true:

- `final_manual_scrape_eligible=true`
- `human_review_status=human_reviewed`
- `final_manual_x_url_primary` is not empty
- `final_manual_account_status` is `confirmed_candidate_official` or `candidate_rejected_alternate_found`

The machine-readable queue must set:

- `queue_source=human_final_manual_review`
- `eligibility_source_field=final_manual_scrape_eligible`
- `collection_x_url=final_manual_x_url_primary`
- `secondary_x_url=final_manual_x_url_secondary` when present

Current queue row count: 100 accounts.

## Default Queue State

Every scaffold row starts with:

- `collection_status=queued_not_collected`
- `collection_authorized=false`
- `dry_run_only=true`
- `data_mutation_allowed=false`
- `dashboard_sync_allowed=false`
- `collection_priority=top100_human_final`
- `collection_scope=timeline_posts_if_accessible`
- `collection_start_policy=to_be_defined_before_collection`
- `collection_end_policy=to_be_defined_before_collection`
- `max_posts_policy=to_be_defined_before_collection`

These defaults intentionally prevent silent collection. Start/end policy, maximum posts, access method, rate controls, and audit output must be defined before any future collection command is authorized.

## Claim Boundaries

This queue authorizes future collection planning only. It does not authorize scraping, X API calls, MCP installation, browser automation, dashboard sync, SEC downloads, or `data/` and `dashboard/data/` mutation.

Future X post coverage will not be a complete historical archive. It will be limited to retrievable timeline posts under the implemented access method.

Humor classification and sentiment labels remain model-generated unless manual audit evidence exists. Dashboard analytics remain descriptive only and authorize no causal claims.

The unresolved SEC 10-K fetch failure does not affect account queue eligibility. It still blocks financial-text linkage, 10-K based AI disclosure analysis, and fiscal correlation claims where report-body download status is not an audited success.

## Validation

Run:

```bash
python scripts/validate_fortune_x_collection_queue.py
```

The validator is local/static only. It does not read secrets, scrape X, call X APIs, download SEC filings, trigger workflows, or modify `data/` or `dashboard/data/`.
