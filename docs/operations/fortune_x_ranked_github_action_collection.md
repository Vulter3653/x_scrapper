# Fortune 2025 Ranked X GitHub Action Collection

## Purpose

This document describes the workflow_dispatch collection path for Fortune 2025 Top 100 official X accounts. The workflow performs capped browser-based collection of observable public posts using the existing repository Playwright collector.

## Operating State

```text
collection_authorized=true
dry_run_only=false
data_mutation_allowed=true
browser_collection_allowed=true
x_api_collection_allowed=false
github_actions_collection_allowed=true
github_actions_push_allowed=true
dashboard_sync_allowed=false
```

## Workflow

| File | Purpose |
| --- | --- |
| `.github/workflows/collect-fortune-x-ranked.yml` | Manual GitHub Actions workflow for ranked sequential collection. |
| `scripts/run_fortune_x_ranked_collection.py` | Reads the human-final queue and processes ranks in ascending order. |
| `scripts/validate_fortune_x_ranked_collection.py` | Validates scaffold and collection outputs. |

The workflow is `workflow_dispatch` only. It does not run on push or schedule. It does not use a matrix and does not run accounts in parallel.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `max_posts` | `50` | Maximum observable public posts per account. |
| `start_rank` | `1` | First Fortune rank to process. |
| `end_rank` | `100` | Last Fortune rank to process. |
| `commit_results` | `true` | Whether the workflow commits and pushes collection outputs. |

## Source Queue

The collection source is `config/fortune2025_top100_verified_x_collection_queue.csv`. The queue must preserve rank order and uses `queue_source=human_final_manual_review` and `eligibility_source_field=final_manual_scrape_eligible`.

## Output Structure

Each company is written to an independent folder:

```text
data/raw/fortune_x_2025_ranked/001_amazon/posts.csv
data/raw/fortune_x_2025_ranked/001_amazon/audit.json
...
data/raw/fortune_x_2025_ranked/100_company_slug/posts.csv
data/raw/fortune_x_2025_ranked/100_company_slug/audit.json
```

The summary file is:

```text
data/audit/fortune_x_2025_ranked_collection_summary.csv
```

Folder names use three-digit rank prefixes and lowercase company slugs.

## Collection Method

The collection method string is standardized as:

```text
capped browser-based collection of observable public posts
```

The workflow uses the existing Playwright/browser collector through `python scrape_x.py`. It does not create a new official X API collector and does not call X API endpoints.

## Secret Handling

The workflow passes existing secrets to the collector:

```text
X_AUTH_TOKEN
X_CT0
```

The workflow and runner check secret presence without printing secret values. If credentials are unavailable, collection is not attempted and per-account audit rows use `credential_missing`.

## Commit Behavior

When `commit_results=true`, the workflow commits only:

```text
data/raw/fortune_x_2025_ranked/
data/audit/fortune_x_2025_ranked_collection_summary.csv
```

It does not add `dashboard/data/`. It does not commit browser sessions, cookies, screenshots, traces, or cache files.

## Boundaries

- Official X API is not used.
- MCP is not installed.
- Accounts are processed sequentially by Fortune rank.
- Dashboard sync is not performed.
- `dashboard/data/` must remain unchanged.
- No complete historical X coverage claim is allowed.
- Outputs are limited to capped browser-based collection of observable public posts.
