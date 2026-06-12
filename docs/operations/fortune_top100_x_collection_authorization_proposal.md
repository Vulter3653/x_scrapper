# Fortune Top 100 X Collection Authorization Proposal

## Purpose

This document is an authorization proposal design only. It defines the conditions that must be satisfied before any future Fortune Top 100 X collection run can be authorized. This proposal does not authorize collection, does not scrape X posts, does not collect timelines, does not call X APIs, does not install MCP, does not execute browser automation, and does not create raw or processed outputs.

## Current Human-Final Queue Summary

| Metric | Count |
| --- | ---: |
| Human-reviewed queue accounts | 100 |
| `final_manual_scrape_eligible=true` | 100 |
| `confirmed_candidate_official` | 57 |
| `candidate_rejected_alternate_found` | 43 |

All 100 queued accounts remain `collection_status=queued_not_collected`. The queue derives from `final_manual_scrape_eligible` with `queue_source=human_final_manual_review`. The old `scrape_eligible` field is preliminary/reference only and is not the final eligibility source. The readiness policy remains `collection_authorized=false`, `dry_run_only=true`, `data_mutation_allowed=false`, and `dashboard_sync_default=disabled`.

## Method Options

| Method option | Feasibility | Authentication requirements | Rate-limit risk | Reproducibility | Data quality | Compliance risk | Expected auditability | Avoids dashboard/data mutation by default |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X API | Depends on account tier, endpoint access, policy limits, and cost. | Likely requires approved X developer credentials and scoped tokens. | Medium to high, depending on endpoint quotas. | High if API version, parameters, and response metadata are logged. | Potentially structured, but may be limited by endpoint access and policy. | Medium to high because platform terms and paid access constraints must be reviewed. | High if request IDs, parameters, timestamps, and response counts are logged. | Yes, if output paths remain disabled until authorization. |
| Browser/manual access | Feasible for a limited, controlled run if browser access is explicitly approved later. | May require authenticated browser session and careful secret handling. | Medium because timeline access can throttle or block. | Medium; browser rendering and timeline availability can vary. | Good for retrievable timeline posts, but not complete historical coverage. | Medium; requires strict no-secret logging and access-method documentation. | Medium to high if every account attempt produces an audit row. | Yes, if dry-run/default output policies remain disabled until authorization. |
| MCP-assisted workflow | Feasibility unknown until a specific MCP is reviewed and approved. | To be decided; may require connector authentication. | Unknown until method selection. | Unknown; depends on tool behavior and logs. | Unknown; depends on connector data access and limits. | High until tool permissions and data handling are audited. | Unknown; must be proven before use. | Yes only if connector cannot write `data/` or `dashboard/data/` by default. |
| No-collection fallback | Always feasible. | None. | None. | High. | No new X post data collected. | Lowest. | High; queue remains a planning artifact only. | Yes. |

## Recommended Future Method

For a separate future authorization step, the recommended method is a limited browser/manual-compatible collection workflow only if the owner approves it in a dedicated authorization commit. The method should use the 100-account human-final queue, a fixed date window, a fixed maximum posts per account, and per-account audit logging. It should default to no dashboard sync and no mutation of current brand data.

This recommendation is not execution approval. It is a proposal for the next design step because browser/manual-compatible access most closely matches the current scraper lineage while still requiring explicit authorization, audit controls, and secret-handling review before any run.

## Required Execution Controls

A future execution commit must define all of the following before any collection command exists or runs:

- Explicit collection authorization commit.
- Fixed date window.
- Maximum posts per account.
- Rate-limit handling policy.
- Retry policy.
- Per-account audit log path and schema.
- Failure status taxonomy.
- No dashboard sync by default.
- Raw output and processed output paths defined before run.
- No complete historical coverage claim.
- Secret handling and no-secret logging controls.
- A rollback and cleanup plan for failed partial runs.

## Required Future Audit Fields

Any eventually authorized collection run must produce an audit log with at least these fields:

| Field | Meaning |
| --- | --- |
| `fortune_rank` | Fortune 2025 rank for the queued company. |
| `company_name` | Company name from the verified queue. |
| `collection_x_handle` | Human-final X handle derived from `final_manual_x_url_primary`. |
| `collection_x_url` | Human-final X URL from `final_manual_x_url_primary`. |
| `collection_attempted_at` | Timestamp of the attempted collection. |
| `collection_method` | Explicit method used. |
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

## Explicit Boundaries

This proposal does not authorize collection. This proposal does not install MCP. This proposal does not call X API. This proposal does not execute browser automation. This proposal does not modify `data/`. This proposal does not modify `dashboard/data/`. This proposal does not authorize dashboard sync.

Future collection covers retrievable timeline posts only. No complete historical X archive claim is allowed.

## Proposal Policy File

The machine-readable proposal is `config/fortune2025_top100_x_collection_authorization_proposal.csv`. It intentionally keeps:

- `eligible_account_count=100`
- `queue_source=human_final_manual_review`
- `eligibility_source_field=final_manual_scrape_eligible`
- `collection_authorized=false`
- `dry_run_only=true`
- `dashboard_sync_allowed=false`
- `data_mutation_allowed=false`
- `proposed_raw_output_path=not_defined_until_collection_authorized`
- `proposed_processed_output_path=not_defined_until_collection_authorized`
- `proposed_audit_log_path=not_defined_until_collection_authorized`
- `approval_required_before_execution=true`

## Validation

Run:

```bash
python scripts/validate_fortune_x_collection_authorization_proposal.py
```

The validator is local/static only. It does not read secrets, scrape X, call X APIs, install MCP, execute browser automation, download SEC filings, trigger workflows, or modify `data/` or `dashboard/data/`.
