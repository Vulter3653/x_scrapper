# Yearly Humor Backfill — Runbook

## Current Status

Run `27783926736` was a workflow PASS but a 2009 data-quality FAIL:

- `validate-inputs`: success
- `prepare-year-targets`: success
- `collect-year`: success
- `validate-yearly-outputs`: success
- `optional-commit`: skipped

Observed 2009 collection quality:

- `target_company_count = 99`
- `attempted_company_count = 99`
- `success_count = 0`
- `recoverable_failure_count = 99`
- `posts_collected = 0`
- main failures: `recoverable_failed_timeout = 83`, `recoverable_failed_did_not_reach_year = 16`

This means Playwright installation was resolved, but actual 2009 post collection failed. A 99-company run with `max_scrolls=3500` took more than two hours and must be treated as a full historical run, not a smoke test.

## Smoke Test First

Use smoke mode before any full 99-company historical run.

Recommended targeted B smoke toggle:

```text
targeted_b_smoke: true
```

This preset forces `target_year=2009`, `target_scope=all`, `retry_round=0`, `max_posts_per_account=0`, `max_scrolls=300`, `max_parallel_companies=1`, `smoke=true`, `limit_companies=3`, `handles=@Broadcom,@MorganStanley,@WellsFargo`, `per_company_timeout_seconds=300`, `fail_fast_render=true`, and disables commit.

Manual 2009 smoke inputs:

```text
workflow: Yearly Humor Backfill Serial Years
target_year: 2009
start_year: 2009
end_year: 2009
target_scope: all
retry_round: 0
max_posts_per_account: 0
max_scrolls: 300
max_parallel_companies: 1
smoke: true
limit_companies: 3
per_company_timeout_seconds: 180
fail_fast_render: true
commit_results: false
```

Smoke mode effective behavior:

- selected companies default to 3 unless `limit_companies` or `handles` is explicitly supplied.
- `handles` matching is case-insensitive, so `@Broadcom` and `@broadcom` select the same target.
- `max_parallel_companies` is forced to 1.
- `max_scrolls` is capped at 300 even if a larger value is supplied.
- per-company hard timeout defaults to 180 seconds.
- goal runtime is 10-20 minutes.
- goal output is diagnostic artifact/audit data, not historical completeness.

Smoke goals:

- confirm artifact creation
- classify render failure subtype
- record company-level elapsed time
- identify whether failures are auth/login, rate/block, selector, timeout, or unknown render failures

A full 99-company `target_year=2009`, `max_scrolls=3500` run should happen only after smoke output has been reviewed and the user explicitly approves a full run.

## Full Run Policy

Full historical runs are long-running collection jobs. Run them only after smoke diagnostics identify and reduce render/timeout failure causes.

A full run is any run with most/all active companies and high scroll depth, for example:

```text
target_year: 2009
target_scope: all
max_scrolls: 3500
max_parallel_companies: 1
smoke: false
commit_results: false
```

Do not call this a smoke test.

## Oldest-Year-First Collection Principle

Collection order remains:

```text
2009 -> 2010 -> 2011 -> ... -> 2021
```

Move to the next year only after recoverable failures for the current year are understood or resolved.

## Status Codes

### Recoverable

| Status | Meaning | Action |
|---|---|---|
| `recoverable_failed_render` | Browser/render failure | Inspect `failure_subtype`; retry after fixing cause |
| `recoverable_failed_company_timeout` | Company-level hard timeout | Retry with smaller target or improved render path |
| `recoverable_failed_timeout` | Scraper timeout | Retry after diagnosing elapsed time/logs |
| `recoverable_failed_did_not_reach_year` | Scroll did not reach target year | Increase scrolls only after render stability is known |
| `recoverable_failed_network` | Network/DNS issue | Retry |
| `recoverable_failed_browser` | General browser failure | Inspect logs |
| `recoverable_failed_temporary_x_error` | X rate limit / temporary block | Wait and retry |

### Render Failure Subtypes

| failure_subtype | Meaning |
|---|---|
| `render_failure_login_or_auth` | Login/auth/cookie issue suspected |
| `render_failure_rate_limit_or_block` | Rate limit or block suspected |
| `render_failure_selector_missing` | Selector/locator/page structure issue suspected |
| `render_failure_timeout` | Render/navigation/company timeout |
| `render_failure_unknown` | Render-like failure without enough evidence |

### Terminal

| Status | Meaning | Evidence |
|---|---|---|
| `terminal_created_after_year` | Account was created after target year | `account_created_year > target_year` required |
| `terminal_no_observable_posts_for_year` | Successful scrape with no observable posts | Account exists but no observed target-year posts |
| `terminal_account_protected` | Protected/private account | |
| `terminal_account_suspended` | Suspended account | |
| `terminal_account_unavailable` | Deleted/unavailable account | |

`terminal_created_after_year` must not be inferred from earliest observed post date alone. Earliest observed post later than target year usually means the scraper did not scroll back far enough and should remain recoverable.

## Output Schema Additions

Year summary now includes smoke/time-limit diagnostics including:

- `smoke_mode`
- `full_target_company_count`
- `selected_company_count`
- `input_max_scrolls`
- `effective_max_scrolls`
- `max_scrolls_cap_reason`
- `per_company_timeout_seconds`
- `total_elapsed_seconds`
- `median_company_elapsed_seconds`
- `max_company_elapsed_seconds`
- timeout and render failure subtype counts
- min/max seen dates and scroll statistics

Company-level rows now include:

- `company_timeout_triggered`
- `failure_subtype`
- `elapsed_seconds`
- stdout/stderr/combined tail paths
- `exit_status_path`
- `min_date_seen`, `max_date_seen`
- `raw_collected`, `posts_on_or_before_target_year` via `posts_on_or_before_year`
- smoke/max-scroll/time-limit fields

## Directory Structure

```text
data/backfill/yearly_humor/
  audit/
    year_target_summary.csv
  {year}/
    audit/
      year_{year}_target_companies.csv
      year_{year}_failed_targets.csv
      year_{year}_terminal_targets.csv
      year_{year}_summary.csv
    posts/
      y{year}__{group}__{company}__{handle}/
        collected_posts_raw.json
        posts_on_or_before_{year}.json
        scraper_stdout_tail.txt
        scraper_stderr_tail.txt
        scraper_combined_tail.txt
        scraper_exit_status.json
        scrape_metrics.json
```

## Validation

```bash
python scripts/validate_yearly_humor_backfill_outputs.py --allow-empty
python scripts/validate_yearly_humor_backfill_outputs.py --target-year 2009
python scripts/validate_yearly_humor_backfill_outputs.py --target-year 2009 --strict
```

Smoke output can pass validation with `success_count=0` when schema, selected count, recoverable failure status, and subtype diagnostics are internally consistent. That is still a data-quality failure and should not be treated as successful collection.
