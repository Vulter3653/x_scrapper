# Fortune Top 100 X Collection Method Decision

## Purpose

This document records the method decision for the Fortune 2025 Top 100 human-final X collection queue. It is a design decision only. It does not authorize collection, execute scraping, call X APIs, install MCP, run browser automation, create raw outputs, create processed outputs, modify `data/`, modify `dashboard/data/`, or sync dashboard outputs.

## Current Queue State

| Item | Value |
| --- | --- |
| Queue file | `config/fortune2025_top100_verified_x_collection_queue.csv` |
| Queue row count | 100 human-final eligible accounts |
| `queue_source` | `human_final_manual_review` |
| `eligibility_source_field` | `final_manual_scrape_eligible` |
| Collection authorization | `collection_authorized=false` |
| Dry-run boundary | `dry_run_only=true` |

The old `scrape_eligible` field is preliminary/reference only. Future collection planning must use `final_manual_scrape_eligible` and the 100-row human-final queue. The machine-readable decision uses `queue_source=human_final_manual_review` and `eligibility_source_field=final_manual_scrape_eligible`.

## Existing Workflow Inspection Summary

Inspection found an existing collection path in the repository:

| Existing file | What it does | Extension relevance |
| --- | --- | --- |
| `scrape_x.py` | Backward-compatible root scraper entrypoint. | Can remain the command wrapper for future collection work. |
| `scripts/scrape_x.py` | Compatibility entrypoint into the packaged scraper. | Can support script-path invocation if a future workflow chooses it. |
| `src/x_scrapper/collection/x_scraper.py` | Existing Playwright/cookie-based X profile collector that captures GraphQL timeline responses and writes `posts.json` plus `scrape_state.json`. | This is the existing repo collection path to extend. |
| `.github/workflows/scrape.yml` | Current brand collection workflow for `Wendys`, `CocaCola`, and `MoonPie`, followed by analysis/export/dashboard sync. | Shows existing environment variables, dependency install, secret validation, artifact handling, and validation conventions. |
| `config/fortune2025_top100_verified_x_collection_queue.csv` | Human-final 100-row future collection queue. | Future execution input, not execution itself. |
| `scripts/validate_fortune_x_collection_queue.py` | Static queue validator. | Existing gate to preserve and extend. |
| `config/fortune2025_top100_x_collection_readiness_policy.csv` | Dry-run-only readiness policy. | Keeps execution disabled until authorization. |
| `config/fortune2025_top100_x_collection_authorization_proposal.csv` | Pre-execution proposal with output paths undefined. | Records future authorization controls. |

What can be extended:

- The existing package entrypoint pattern can be reused for a Fortune-specific collector wrapper later.
- The existing scraper environment style can be extended to read one queued account at a time.
- The existing `OUTPUT_FILE`, `STATE_FILE`, `BRAND_DIR`, scroll limit, timeout, and cookie conventions can inform future execution controls.
- Static validators can continue to block collection until a separate authorization commit defines limits and output paths.

What remains undefined:

- Fixed date window.
- Maximum posts per account.
- Rate-limit policy.
- Retry policy.
- Per-account audit log path and schema.
- Raw output path and processed output path.
- Whether authenticated access is available and approved for the Fortune queue.

## Method Options Comparison

| Method option | Assessment |
| --- | --- |
| Extend existing collection workflow | Preferred. It minimizes architecture churn, preserves current scraper conventions, reuses validators, and can be gated behind explicit authorization. |
| X API | Not selected. It would add credential, tier, endpoint, cost, and policy dependencies before a collection authorization exists. |
| MCP-assisted workflow | Not selected. It would add tool-install and connector-permission risk before method execution controls are approved. |
| Browser automation | Not selected as a new architecture. The existing repo already contains a browser/cookie-based collection path, so any future browser behavior should be an extension of that existing path, not a separate new design. |
| No-collection fallback | Valid fallback if owner authorization is not granted, but it does not advance the future collection plan. |

## Selected Method

`selected_collection_method=extend_existing_collection_workflow`

`selected_access_method=existing_repo_collection_path`

This means future implementation should build on the current `scrape_x.py` / `src/x_scrapper/collection/x_scraper.py` structure, using the 100-row human-final queue as input, while keeping dry-run-only behavior until explicit owner authorization.

## Why This Method

- Least disruptive to the repository architecture; this is the least disruptive option because it extends existing entrypoints and conventions.
- Easiest to validate because it builds on current entrypoints and local validators.
- Avoids new X API credentials at this stage.
- Avoids MCP installation and connector permission risk at this stage.
- Compatible with `collection_authorized=false` and `dry_run_only=true` gating.
- Can be upgraded later if the existing method proves insufficient.

## Required Future Execution Controls

A separate future authorization commit must define all of the following before any collection command exists or runs:

- Explicit collection authorization commit.
- Fixed date window.
- Maximum posts per account.
- Rate-limit handling policy.
- Retry policy.
- Per-account audit log.
- Raw output path.
- Processed output path.
- Failure status taxonomy.
- No dashboard sync by default.
- No complete historical coverage claim. No complete historical X coverage claim is allowed.
- Secret handling and no-secret logging controls.

## Explicit Boundaries

This decision does not authorize collection. This decision does not call X API. This decision does not install MCP. This decision does not run browser automation. This decision does not modify `data/`. This decision does not modify `dashboard/data/`. This decision does not define raw/processed outputs. This decision does not claim complete historical X coverage.

## Validation

Run:

```bash
python scripts/validate_fortune_x_collection_method_decision.py
```

The validator is local/static only. It does not read secrets, scrape X, call X APIs, install MCP, execute browser automation, trigger workflows, or modify `data/` or `dashboard/data/`.
