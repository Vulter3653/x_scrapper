# Fortune Top 100 X Dry-Run Collection Readiness Protocol

## Purpose

This is a dry-run readiness protocol only. It documents the preconditions and audit design needed before any future Fortune Top 100 X collection run can be considered.

It does not authorize scraping. It does not authorize MCP installation. It does not authorize X API usage. It does not authorize browser automation. It does not authorize dashboard sync. It does not authorize `data/` or `dashboard/data/` mutation.

The current human-reviewed queue contains 100 accounts in `config/fortune2025_top100_verified_x_collection_queue.csv`. All queue rows remain `collection_status=queued_not_collected` and derive from `final_manual_scrape_eligible=true` with `queue_source=human_final_manual_review`.

## Readiness Policy

The active readiness policy is stored in `config/fortune2025_top100_x_collection_readiness_policy.csv` and defaults to:

- `eligible_account_count=100`
- `queue_source=human_final_manual_review`
- `eligibility_source_field=final_manual_scrape_eligible`
- `dry_run_only=true`
- `collection_authorized=false`
- `access_method=to_be_decided`
- `mcp_required=to_be_decided`
- `api_required=to_be_decided`
- `browser_required=to_be_decided`
- `rate_limit_policy=to_be_defined_before_collection`
- `max_posts_per_account=to_be_defined_before_collection`
- `date_window_policy=to_be_defined_before_collection`
- `retry_policy=to_be_defined_before_collection`
- `audit_log_required=true`
- `output_path_policy=no_output_until_collection_authorized`
- `dashboard_sync_default=disabled`
- `data_mutation_allowed=false`

Any future collection run must have an explicit collection authorization commit before execution. That commit must define the collection method, access controls, date window, rate limit policy, retry policy, maximum posts per account, output paths, and audit log destination.

## Scope Boundary

Future collection scope is limited to retrievable timeline posts under the implemented access method. No complete historical X coverage claim is allowed.

The queue and readiness policy do not change data claim boundaries. Humor classification and sentiment labels remain model-generated unless manual audit evidence exists. Dashboard analytics remain descriptive only and authorize no causal claims. SEC 10-K fetch failure remains unresolved and does not affect account queue eligibility, but it still blocks financial-text linkage claims where report-body download status is not audited success.

## Required Future Audit Fields

Any eventually authorized collection run must produce an audit log with at least these fields:

| Field | Meaning |
| --- | --- |
| `fortune_rank` | Fortune 2025 rank for the queued company. |
| `company_name` | Company name from the verified queue. |
| `collection_x_handle` | Human-final X handle derived from `final_manual_x_url_primary`. |
| `collection_x_url` | Human-final X URL from `final_manual_x_url_primary`. |
| `collection_attempted_at` | Timestamp of the attempted collection. |
| `collection_method` | Explicit method used, such as browser workflow or approved API path. |
| `collection_status` | Controlled run result. |
| `posts_requested` | Requested post limit or window size. |
| `posts_collected` | Count of posts actually captured. |
| `earliest_post_date` | Earliest captured post timestamp, if any. |
| `latest_post_date` | Latest captured post timestamp, if any. |
| `failure_reason` | Reason for failure or partial capture. |
| `rate_limit_observed` | Whether rate limiting was encountered. |
| `auth_required` | Whether authentication blocked or changed access. |
| `raw_output_path` | Raw output path, only after collection is authorized. |
| `processed_output_path` | Processed output path, only after collection is authorized. |
| `dashboard_synced` | Must default to false unless dashboard sync is separately authorized. |
| `notes` | Reviewer or operator notes. |

Allowed future failure status values are defined in the readiness policy as `blocked,failed,inaccessible,rate_limited,auth_required`.

## Dry-Run Checklist

Before authorization, a dry-run review may inspect only local config and docs:

1. Confirm the human-final queue passes `python scripts/validate_fortune_x_collection_queue.py`.
2. Confirm the readiness policy passes `python scripts/validate_fortune_x_collection_readiness.py`.
3. Confirm no `data/` or `dashboard/data/` paths are modified.
4. Draft, but do not execute, a future authorization commit with explicit collection settings.

## Validation

Run:

```bash
python scripts/validate_fortune_x_collection_readiness.py
```

The validator is local/static only. It does not read secrets, scrape X, call X APIs, install MCP, download SEC filings, trigger workflows, or modify `data/` or `dashboard/data/`.
