# Fortune Top 100 X Existing Collection Workflow Structure Analysis

## Purpose

This document statically analyzes the existing X collection workflow structure in `Vulter3653/x_scrapper` before any future Fortune Top 100 collection authorization. It explains how the current repo collects brand posts today, what can be extended for the 100-row human-final Fortune queue, and what controls are still required before any execution.

This is analysis only. It is not collection authorization and it does not execute collection.

## Current Boundary

The active Fortune collection gates remain:

```text
collection_authorized=false
dry_run_only=true
data_mutation_allowed=false
dashboard_sync_allowed=false
```

The Fortune queue has 100 rows and derives from `final_manual_scrape_eligible=true` with `queue_source=human_final_manual_review`. The old `scrape_eligible` field is preliminary/reference only and is not the final collection eligibility signal.

## Files Inspected

| File | Role in current structure |
| --- | --- |
| `scrape_x.py` | Root compatibility entrypoint for the X scraper. |
| `scripts/scrape_x.py` | Script-path compatibility entrypoint for the same scraper implementation. |
| `src/x_scrapper/collection/x_scraper.py` | Existing packaged Playwright/cookie-based profile collection implementation. |
| `.github/workflows/scrape.yml` | Existing scheduled/manual scrape workflow for the three operating brands. |
| `config/fortune2025_top100_verified_x_collection_queue.csv` | Human-final 100-row future Fortune queue. |
| `config/fortune2025_top100_x_collection_readiness_policy.csv` | Dry-run-only readiness policy. |
| `config/fortune2025_top100_x_collection_authorization_proposal.csv` | Pre-execution authorization proposal with output paths undefined. |
| `config/fortune2025_top100_x_collection_method_decision.csv` | Method decision selecting `extend_existing_collection_workflow`. |
| `scripts/validate_fortune_x_collection_queue.py` | Static queue validator. |
| `scripts/validate_fortune_x_collection_readiness.py` | Static readiness validator. |
| `scripts/validate_fortune_x_collection_authorization_proposal.py` | Static proposal validator. |
| `scripts/validate_fortune_x_collection_method_decision.py` | Static method-decision validator. |

## Existing Entry Point Structure

`scrape_x.py` is the backward-compatible root entrypoint. It inserts `src/` into `sys.path`, imports `scrape_profile` from `x_scrapper.collection.x_scraper`, and runs it with `asyncio.run()`.

`scripts/scrape_x.py` is a compatibility entrypoint with the same behavior from the `scripts/` namespace. It resolves the repository root, inserts `src/`, imports the same `scrape_profile`, and runs it.

`src/x_scrapper/collection/x_scraper.py` contains the active implementation. The current call relationship is:

```text
python scrape_x.py
  -> x_scrapper.collection.x_scraper.scrape_profile()

python scripts/scrape_x.py
  -> x_scrapper.collection.x_scraper.scrape_profile()
```

For a future Fortune path, the existing implementation can be extended through a Fortune-specific wrapper or adapter that sets account-specific environment variables and output paths before invoking the same package-level collection primitive. No such execution wrapper is authorized in this analysis.

## Existing Input Structure

The current scraper receives inputs from environment variables:

| Input | Current meaning |
| --- | --- |
| `TARGET_USER` | X screen name to collect, defaulting to `Wendys`. |
| `BRAND_DIR` | Optional output directory override; defaults to `data/<brand_slug>`. |
| `OUTPUT_FILE` | Optional posts output override; defaults to `BRAND_DIR/posts.json`. |
| `STATE_FILE` | Optional scrape-state output override; defaults to `BRAND_DIR/scrape_state.json`. |
| `HEADLESS` | Browser headless mode flag. |
| `MAX_SCROLLS` | Maximum scroll count. |
| `SCROLL_DELAY_SECONDS` | Delay between scrolls. |
| `IDLE_SCROLL_LIMIT` | Stop threshold after scrolls with no new posts. |
| `PAGE_TIMEOUT_MS` | Page/tweet selector timeout. |
| `X_AUTH_TOKEN` | X cookie secret. |
| `X_CT0` | X cookie secret. |

Brand/account/handle is currently defined by `TARGET_USER`, not by a queue file. The GitHub workflow matrix supplies `Wendys`, `CocaCola`, and `MoonPie` as operating targets.

To connect the Fortune queue later, an adapter would be needed to read `config/fortune2025_top100_verified_x_collection_queue.csv`, select authorized rows, derive `TARGET_USER` from `collection_x_handle`, and set isolated output/audit paths. That adapter must also enforce the owner-approved authorized state and non-dry-run state only after a separate authorization commit. This analysis does not create that adapter.

## Existing Authentication and Cookie Handling

The current scraper requires `X_AUTH_TOKEN` and `X_CT0`. If either is missing, `scrape_profile()` prints an error and exits.

`.github/workflows/scrape.yml` validates repository secrets before the scraper step. It checks `X_AUTH_TOKEN` and `X_CT0` and fails early if either is empty or missing. The workflow passes those values as environment variables to `python scrape_x.py`.

`authentication_required=to_be_confirmed_before_execution` remains appropriate for Fortune collection planning because the current method uses cookies, but future owner approval must confirm whether the same authentication path is available, allowed, and scoped for Fortune accounts before execution.

Secret handling risk remains high enough that any future authorization must prohibit printing, committing, summarizing, or storing cookie values.

## Existing Runtime Behavior

The existing implementation uses Playwright with Chromium. It launches a browser context, injects `auth_token` and `ct0` cookies for `.x.com`, opens `https://x.com/{TARGET_USER}`, waits for rendered tweets, and attaches a response listener.

The response listener watches GraphQL URLs containing `UserTweets`, `UserTweetsAndReplies`, `UserMedia`, or `TweetDetail`. It parses JSON responses, walks nested payloads, extracts tweet records for the target user, merges by tweet id, and saves outputs incrementally.

Runtime controls currently include:

| Control | Current source |
| --- | --- |
| Page timeout | `PAGE_TIMEOUT_MS` |
| Scroll limit | `MAX_SCROLLS` |
| Scroll delay | `SCROLL_DELAY_SECONDS` |
| Idle stop threshold | `IDLE_SCROLL_LIMIT` |
| Headless mode | `HEADLESS` |

There is no Fortune-specific retry policy, rate-limit policy, per-account cap, date-window enforcement, or audit failure taxonomy in the scraper implementation today. Those controls must be added before any Fortune execution is authorized.

## Existing Output Structure

The current scraper writes processed account-level JSON outputs, not a separate raw response archive.

`posts.json` is a list of extracted post records. Each record includes fields such as:

| Field | Meaning |
| --- | --- |
| `id` | X/Twitter tweet id. |
| `tweet_url` | Constructed status URL. |
| `created_at` | Tweet creation timestamp from X payload. |
| `text` | Full text or note tweet text when available. |
| `reply_count`, `favorite_count`, `retweet_count`, `quote_count`, `bookmark_count`, `view_count` | Captured engagement metrics where available. |
| `lang` | Language code. |
| `conversation_id` | Conversation id. |
| `is_quote_status` | Quote-status flag. |
| `source` | Currently `browser_graphql`. |
| `scraped_at` | Unix timestamp when extracted. |

`scrape_state.json` records run state such as `target_user`, `profile_url`, `total_unique_posts`, `last_response_url`, `last_saved_at`, and `last_completed_at`.

The GitHub workflow stages brand outputs under `staging/data/<slug>/` and uploads them as short-retention artifacts before aggregate analysis downloads and processes them.

For Fortune collection, raw output and processed output can be separated later by defining explicit output roots, for example a raw response/audit area and a processed posts area. Those paths are intentionally not defined yet because output creation is not authorized.

## Existing Dashboard Sync Structure

The current `.github/workflows/scrape.yml` aggregate-analysis job runs:

```bash
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
```

`sync_dashboard_data.py` copies data outputs into `dashboard/data/` for the static dashboard. This is appropriate for the current three-brand operating dashboard, but it must remain disabled for Fortune collection planning.

For Fortune collection, `dashboard_sync_allowed=false` must remain in force because queue/account verification and future collection outputs are not dashboard-ready analytical products. A future collection run must default `dashboard_synced=false` in audit logs and require a separate dashboard integration decision.

## Fortune Queue Integration Implications

The 100-row Fortune queue is ready as a planning input, but not as an execution command. A future adapter would need to:

- Read only `final_manual_scrape_eligible=true` queue rows.
- Use `collection_x_handle` or `collection_x_url` to derive the target account.
- Enforce method decision `selected_collection_method=extend_existing_collection_workflow`.
- Require an owner-approved authorized state and non-dry-run state from a future authorization file before running.
- Set account-isolated output paths to avoid collisions with `data/wendys`, `data/cocacola`, and `data/moonpie`.
- Write a per-account audit row whether collection succeeds, fails, is skipped, is rate-limited, or requires auth.
- Keep dashboard sync disabled by default.

No adapter is created in this analysis.

## Dry-Run and Authorization Gate Implications

With `collection_authorized=false`, any future Fortune command must refuse to collect and may only perform local/static checks. With `dry_run_only=true`, allowed commands should be limited to reading config, validating queue/policy files, counting planned accounts, and reporting missing execution controls.

A future authorization commit must provide guard conditions such as:

- Refuse execution unless both the authorized state and non-dry-run state are present in the owner-approved policy.
- Refuse execution unless output paths are explicit and outside existing brand folders.
- Refuse execution unless max accounts, max posts, date window, rate limits, retry policy, and audit path are defined.
- Refuse execution if dashboard sync is enabled by default.
- Refuse execution if secrets are missing or if logging would expose secret values.

## Risk Points

| Risk | Why it matters | Required mitigation before execution |
| --- | --- | --- |
| Accidental scraping risk | Existing `python scrape_x.py` executes immediately when secrets are present. | Fortune-specific command must default to dry-run and gate execution on authorization. |
| Cookie/auth leakage risk | Current method depends on X cookies. | Never print, store, commit, or summarize cookie values; redact logs. |
| Output path collision risk | Current defaults write to `data/<brand_slug>/`. | Fortune outputs must use explicit isolated paths defined before execution. |
| Dashboard sync accidental mutation risk | Existing workflow syncs `data/` into `dashboard/data/`. | Fortune workflow must keep dashboard sync disabled unless separately authorized. |
| `data/` or `dashboard/data/` mutation risk | Current scraper writes directly to output paths. | Dry-run commands must not call scraper execution code. |
| Duplicate run risk | Queue has 100 accounts and no run lock yet. | Add per-run id, audit log, and duplicate-run detection. |
| Partial run risk | Long runs may fail after some accounts. | Add per-account status and resumable audit behavior. |
| Retry failure risk | Existing scraper has idle stopping but no Fortune retry taxonomy. | Define retry policy and failure status taxonomy before execution. |
| Rate-limit/access-block risk | X may throttle or block timeline access. | Define rate limits, backoff, max accounts per run, and `rate_limited`/`auth_required` statuses. |
| Complete-history overclaim risk | Timeline retrieval may be partial. | Keep claim boundary: retrievable timeline posts only, no complete historical X coverage claim. |

## Required Controls Before Future Authorization

Before any future execution, the owner-approved authorization commit must define:

- Fixed date window.
- Maximum posts per account.
- Maximum accounts per run.
- Rate limit policy.
- Retry policy.
- Failure status taxonomy.
- Raw output path.
- Processed output path.
- Per-account audit log path.
- Secret handling and no-secret logging rules.
- Artifact retention rules.
- Dashboard sync block by default.
- Output path collision prevention.
- Resumability and duplicate-run behavior.
- Claim boundary text for retrievable timeline posts only.

## Human Recheck Candidates

Rank 5 Alphabet uses `@Alphabetlnc` / `https://x.com/Alphabetlnc` with `secondary_x_url=https://x.com/google`.

This was not changed because external account verification was out of scope and no X access was performed.

## Non-Actions Confirmed

No X scraping was executed.
No X timeline collection was executed.
No X API call was made.
No MCP was installed.
No browser automation was executed.
No GitHub Actions workflow was triggered.
No data/ files were modified.
No dashboard/data/ files were modified.
No dashboard output sync was performed.
collection_authorized remains false.
dry_run_only remains true.
