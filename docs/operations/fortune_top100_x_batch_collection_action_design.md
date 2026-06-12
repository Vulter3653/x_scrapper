# Fortune Top 100 X Batch Collection Action Design

## Purpose

This document defines the GitHub Actions batch scaffold for the Fortune Top 100 human-final X collection queue. It is designed to make the existing collection workflow executable in controlled batches when the owner explicitly authorizes a workflow_dispatch run.

This document does not execute X collection by itself.

## Current Queue

- Queue file: `config/fortune2025_top100_verified_x_collection_queue.csv`
- Queue row count: 100
- Queue source: `human_final_manual_review`
- Eligibility source field: `final_manual_scrape_eligible`
- Old `scrape_eligible` remains preliminary/reference only.

## Parallel Batch Design

The maximum concurrent accounts is 20.

The scaffold uses 10 batches with 10 accounts per batch. GitHub Actions runs at most two batches run at the same time by setting `strategy.max-parallel: 2`. Inside each batch, the batch runner allows 10 concurrent account subprocesses. Therefore the intended upper bound is:

```text
2 concurrent batches x 10 accounts per batch = 20 concurrent accounts
```

This is the requested upper bound, not a claim that X will allow all 20 profiles to be collected successfully. Access blocks, rate limits, authentication failures, and profile-level failures must be recorded as failures, not as successes.

## Files

| File | Role |
| --- | --- |
| `.github/workflows/collect-fortune-x-batches.yml` | Manual workflow_dispatch scaffold for Fortune batch collection. |
| `scripts/run_fortune_x_collection_batch.py` | Batch runner that reads the 100-row queue and invokes the existing `scrape_x.py` path. |
| `scripts/validate_fortune_x_batch_action.py` | Static validator for the batch workflow and runner controls. |
| `src/x_scrapper/collection/x_scraper.py` | Existing scraper path, extended with a `MAX_POSTS` output cap. |

## Execution Gate

The workflow is manual only. It does not run on `push` or `schedule`. To execute collection, the operator must set `execute_collection=true` and provide the exact confirmation phrase `AUTHORIZE_FORTUNE_X_COLLECTION`. Without that input, the runner performs a dry-run plan and does not invoke `scrape_x.py`.

The workflow validates presence of `X_AUTH_TOKEN` and `X_CT0` only when execution is requested. It does not print cookie values.

## Existing Workflow Extension

The runner does not introduce a new scraper architecture. It invokes the existing root entrypoint:

```text
python scrape_x.py
```

For each account it sets account-isolated environment variables:

```text
TARGET_USER
BRAND_DIR
OUTPUT_FILE
STATE_FILE
MAX_POSTS
MAX_SCROLLS
SCROLL_DELAY_SECONDS
IDLE_SCROLL_LIMIT
PAGE_TIMEOUT_MS
HEADLESS
```

`MAX_POSTS=50` is passed to the existing scraper path and the scraper now caps saved output records accordingly.

## Output Boundaries

When execution is explicitly authorized in the workflow, each account writes to an isolated path under:

```text
data/raw/fortune_x_collection/<run_id>/rankNNN_normalized_company_name/
data/audit/fortune_x_collection/<run_id>/
```

No dashboard sync is performed. `dashboard/data/` is not written by the batch workflow.

## Non-Actions and Boundaries

No X API is introduced.
No MCP is installed.
No new browser automation architecture is introduced.
No GitHub Actions workflow is triggered by adding this scaffold.
No dashboard sync is performed.
No dashboard/data mutation is performed by this scaffold unless a future operator separately adds such behavior, which is outside this design.
No complete historical X coverage claim is allowed. Future outputs must be described as retrievable timeline posts collected under the implemented access method.

## Operational Risk

Running 20 accounts concurrently can increase rate-limit, authentication, or access-block risk. The workflow supports the requested shape, but a safer operational fallback remains reducing `max-parallel` or `concurrency-per-batch` before execution if pilot results show access instability.

## Answer to Concurrency Question

With this scaffold, the configured maximum is 20 concurrently running account collections: 2 batches in parallel and 10 account subprocesses per batch.
