# Troubleshooting and Debugging Log

Repository: `Vulter3653/x_scrapper`
Last updated: `2026-06-12`

This file consolidates troubleshooting and debugging history in one place. It is separate from `PROJECT_HISTORY.md`: that file records the project timeline, while this file records failures, symptoms, root causes, fixes, and verification.

## Summary

| Area | Main issue | Current status |
| --- | --- | --- |
| X scraper authentication | Missing or unstable X cookies caused workflow failures. | Workflow validates secrets and emits clearer errors. |
| `twikit` scraper | X client transaction failed with `Couldn't get KEY_BYTE indices`. | Replaced with browser-based/cookie-driven scraping approach in later work. |
| GitHub Actions push | Long-running scrape jobs could fail with non-fast-forward push rejection. | Workflow push logic was hardened with pull/rebase retry behavior. |
| Dashboard boot | Cloudflare dashboard showed blank white screen after React migration. | Added boot fallback, runtime error display, syntax fixes, and cache busting. |
| Dashboard scripts | `dashboard/app.js` had a syntax error: `Unexpected token ')'`. | Fixed syntax and added `node --check` style validation. |
| Dashboard overlays | Older DOM overlay scripts interfered with React dashboard tabs/components. | Deprecated overlay scripts were removed. |
| Mobile charts | Y-axis and labels were too long/small on mobile; some charts failed to load. | Chart dimensions, axis density, font sizing, and responsive handling were adjusted. |
| Local visual verification | Chromium screenshot validation failed in local environment due to runtime/font/DBus errors. | Static and syntax validation were used where screenshot verification was blocked. |
| Fortune account discovery | X search produced login challenges, selector failures, and unrelated repeated handles. | Prediction/discovery artifacts were removed; Fortune work reset to 2025 ranking source. |
| Repository refactor validation | Sandbox `bwrap` prevented normal apply_patch/shell execution; wrapper import paths needed static validation. | Used approved shell execution, py_compile, node syntax checks, help checks, and `scripts/validate_repository_state.py`. |
| Governance validation | Governance validation was added without data mutation. | Static validators document agent rules, claim boundaries, history integrity, and Fortune expansion readiness. |
| Fortune account verification gate | Verification infrastructure was added without scraping or data mutation. | Master CSV initializes all Top 100 rows as `unknown`, `blocked`, and not scrape eligible until manual evidence is recorded. |

## Detailed Incidents

### 1. GitHub Actions Scraper Failure: Missing Secrets

- Period: `2026-05-22`
- Related commits: `140f690`, `64810f4`
- Symptom: GitHub Actions scraper job failed quickly without enough actionable detail.
- Suspected cause: Missing `X_AUTH_TOKEN` or `X_CT0` repository secrets.
- Debugging performed:
  - Added explicit secret presence validation in the workflow.
  - Added clearer failure output and GitHub annotations.
- Fix:
  - Workflow now validates required X cookie secrets before running the scraper.
  - Scraper failures surface the final error line instead of failing silently.
- Verification:
  - GitHub Actions logs showed whether the failure was secret configuration or scraper runtime.

### 2. `twikit` Runtime Failure: `Couldn't get KEY_BYTE indices`

- Period: `2026-05-22`
- Related work log: `WORK_LOG.md`
- Symptom:
  - `python scrape_x.py` failed inside `twikit`.
  - Error:
    - `Fatal scraper error: Exception: Couldn't get KEY_BYTE indices`
- Root cause:
  - `twikit` failed during X client transaction initialization before timeline data could be fetched.
  - This was not a data parsing problem and not a missing-output-file problem.
- Debugging performed:
  - Inspected GitHub Actions logs.
  - Confirmed failure occurred at `client.get_user_by_screen_name`.
  - Compared free scraping approaches.
- Fix:
  - Later work moved away from relying only on the fragile `twikit` transaction path and toward a browser/cookie-driven scraping architecture.
- Verification:
  - Subsequent successful data refresh commits confirmed collection/analysis output could be produced for configured brands.

### 3. GitHub Actions Push Rejection

- Period: `2026-05-22`
- Related work log: `WORK_LOG.md`
- Symptom:
  - Scrape generated result files, committed them, then failed at push.
  - Error:
    - `! [rejected] HEAD -> main (fetch first)`
    - `Updates were rejected because the remote contains work that you do not have locally.`
- Root cause:
  - A concurrent or newer commit reached `origin/main` while the GitHub Actions runner was based on an older commit.
  - This was a non-fast-forward push conflict, not a scraper or analysis failure.
- Fix:
  - Hardened the workflow commit/push step.
  - On push failure, the workflow fetches latest `origin/main`, rebases the generated result commit, and retries push.
- Verification:
  - Later automated data refresh commits were pushed successfully.

### 4. Split Scrape and Analysis Workflows

- Period: `2026-05-22` to `2026-05-27`
- Related commits: `d9c0f6d`, `d6af6ff`, `103e41b`, `ab481dc`
- Symptom:
  - User wanted scraper, LDA, and sentiment to run separately and in parallel where safe.
  - A single long workflow made failure attribution harder.
- Root cause:
  - Scrape and analysis tasks had different failure modes and runtime characteristics.
- Fix:
  - Split scrape and aggregate analysis into separate jobs/workflows.
  - Added manual update support for all brands through `workflow_dispatch`.
  - Improved workflow metadata consistency.
- Verification:
  - Subsequent all-brand update commits were generated from the automated pipeline.

### 5. LDA Topic Count Misconfiguration

- Period: `2026-05-22`
- Related work log: `WORK_LOG.md`
- Symptom:
  - LDA workflow exposed `Number of LDA topics` as a fixed user input.
- Root cause:
  - Fixed topic count was inappropriate for model selection.
- Fix:
  - Changed analysis behavior to search a topic range.
  - User later requested coherence range from minimum 2 to maximum 9.
- Verification:
  - Workflow and analysis settings no longer depended on a single fixed topic count input.

### 6. Dashboard Blank Screen After React Migration

- Period: `2026-05-26`
- Related commits: `2ea98ea`, `2d8da18`, `186eac8`, `9be8edf`, `e96be2f`
- Related work log: `WORK_LOG_REACT_DASHBOARD_2026-05-26.md`
- Symptom:
  - Deployed Cloudflare Pages dashboard showed a blank white screen.
- Debugging performed:
  - Added visible fallback boot message to `dashboard/index.html`.
  - Added visible `Dashboard boot error` display path.
  - Added cache-busting query strings for `styles.css` and `app.js`.
  - Changed React script loading path.
- Root cause:
  - Browser error display revealed a JavaScript syntax error in `dashboard/app.js`, not a Cloudflare deployment problem and not missing data.
- Fix:
  - Fixed `dashboard/app.js` syntax.
  - Bumped cache-busting query to force clients to load the corrected script.
- Verification:
  - Browser no longer showed blank screen after corrected app script loaded.
  - Later logs recorded the dashboard as visible and functioning.

### 7. Dashboard JavaScript Syntax Error

- Period: `2026-05-26`
- Related commit: `186eac8`
- Symptom:
  - Runtime displayed:
    - `Dashboard boot error`
    - `Uncaught SyntaxError: Unexpected token ')'`
- Root cause:
  - Invalid JavaScript syntax inside `dashboard/app.js`.
- Fix:
  - Corrected the malformed JavaScript expression.
  - Added syntax validation expectations for future dashboard changes.
- Verification:
  - `node --check` style validation was used in later dashboard work.

### 8. Dashboard Tab Instability from Overlay Scripts

- Period: `2026-05-26`
- Related commits: `bb24dd8`, `3ffa58c`, `4a2e86a`, `3d8d998`, `f08bc12`, `a1a8296`
- Symptom:
  - Dashboard tabs and React-controlled components were unstable after multiple overlay-based additions.
- Root cause:
  - Deprecated DOM overlay scripts were competing with React-managed state and rendering.
- Fix:
  - Removed deprecated dashboard DOM overlay script.
  - Removed deprecated dashboard humor overlay script.
  - Added dashboard validation workflow and stability rules.
- Verification:
  - Static reference validation was strengthened.
  - Dashboard work logs recorded no JavaScript syntax errors after validation.

### 9. Mobile Chart Axis and Readability Problems

- Period: `2026-05-22` and later dashboard UI work
- Related commits: `e92a001`, `c13e5df`
- Related work log: `WORK_LOG.md`
- Symptom:
  - Mobile charts had overly long Y-axes.
  - Text was too small on mobile.
  - Some graph sections appeared to fail or become unreadable.
- Root cause:
  - Chart dimensions and label density were not constrained enough for small mobile widths.
  - Fixed 10px/11px chart fonts were too small.
- Fix:
  - Compressed mobile chart axes.
  - Improved mobile chart readability.
  - Added responsive chart font helpers and mobile-aware label behavior.
- Verification:
  - Static search confirmed fixed small font declarations were replaced by responsive helper behavior.
  - UI was checked against responsive requirements where local browser tooling allowed.

### 10. Local Chromium Screenshot Validation Failure

- Period: dashboard responsive validation work
- Related work log: `WORK_LOG.md`
- Symptom:
  - Local headless Chromium screenshot/DOM validation repeatedly failed or timed out.
- Root cause:
  - The local environment produced DBus/font/Harfbuzz/runtime errors unrelated to dashboard code.
- Fix:
  - Did not treat local Chromium failure as dashboard failure.
  - Used static checks, syntax checks, and code-level responsive validation instead.
- Verification:
  - Static requirement checks verified breakpoints, wrappers, mobile post cards, touch targets, chart tooltip logic, memo cache, pagination, and filter support.

### 11. Human Review Dashboard Confusion

- Period: `2026-05-26`
- Related commits: `2ccebc8`, `0530633`, `4040c11`
- Symptom:
  - Review dashboard gave the impression that human review tasks might be executable/decidable inside the dashboard when the user wanted guide-only presentation.
- Root cause:
  - UI mixed workflow guidance with action-like review controls.
- Fix:
  - Separated human review dashboard.
  - Converted review dashboard to guide-only content with examples and guidelines.
- Verification:
  - Final review surface no longer acted like an execution UI.

### 12. Multi-Brand Automation Ambiguity

- Period: `2026-05-27`
- Related commits: `d82dab3`, `d6af6ff`, `103e41b`, `ab481dc`
- Symptom:
  - Wendy's updates worked more reliably than other brands.
  - User observed that CocaCola and MoonPie had failed or stale update conditions.
- Root cause:
  - Workflow behavior and data consistency across brands needed clearer separation and metadata.
- Fix:
  - Documented multi-brand automation issue for Gemini handoff.
  - Refactored workflow into separate scrape and aggregate-analysis jobs.
  - Added manual all-brand update path.
  - Improved dashboard/analysis metadata consistency.
- Verification:
  - Later commits show repeated `Update scraped and analyzed X data for all brands` results.

### 13. Fortune X Account Discovery Artifacts Were Unreliable for Official Mapping

- Period: `2026-06-01` to `2026-06-10`
- Related commits:
  - Added: `f335c95`, `f9bbc46`, `3b11fc1`, `d015544`
  - Removed: `b5fca98`
- Symptom:
  - X account discovery results contained:
    - `login_challenge`
    - `selector_not_found`
    - multiple ambiguous candidates
    - unrelated repeated `@MoonPie` candidate for non-MoonPie companies
- Root cause:
  - X search UI is unstable and cannot be treated as official account evidence.
  - Some candidate rows reflected search/selector contamination rather than official corporate accounts.
- Fix:
  - Created Fortune 2025 ranking-based file:
    - `fortune2025_itemListElement_rows.csv`
    - `config/fortune2025_fortune500_x_account_index.csv`
  - Removed prediction/discovery artifacts and workflow:
    - `.github/workflows/discover-x-accounts.yml`
    - `scripts/discover_x_account_candidates.py`
    - `config/fortune100_*`
    - `data/audit/x_account_discovery_*`
    - `docs/x_account_discovery_*`
- Verification:
  - Confirmed only Fortune 2025 ranking source/index remained for Fortune work.
  - Worktree was clean after deletion commit.

### 14. Local Sandbox `bwrap` Errors During File Inspection/Validation

- Period: `2026-06-10`
- Symptom:
  - Some shell reads or validation commands failed with:
    - `bwrap: Unexpected capabilities but not setuid, old file caps config?`
- Root cause:
  - Local sandbox environment issue, not repository code.
- Fix:
  - Re-ran affected commands with approved escalated execution when required.
- Verification:
  - File generation, CSV row checks, and Git status checks completed successfully after rerun.

### 15. Local SEC EDGAR HTTP 403

- Period: `2026-06-10`
- Symptom:
  - Local requests to `https://www.sec.gov/files/company_tickers.json` and `https://data.sec.gov/submissions/CIK0000320193.json` returned HTTP 403 even with an explicit User-Agent.
  - GitHub Actions run `27269441863` also failed at `company_tickers.json` with HTTP 403.
  - Follow-up run `27269654293` succeeded operationally after the script was changed to write `sec_source_fetch_failed` manifest/audit rows.
- Root cause:
  - SEC rejected the current local execution environment/IP. This is an access-environment issue, not a CSV parsing issue.
- Fix:
  - Added `scripts/collect_fortune2025_10k_reports.py` and `.github/workflows/collect-fortune-10k.yml` so collection can run from GitHub Actions with SEC request headers.
  - Added failure-mode output so SEC source access failures produce 300 manifest/audit rows instead of terminating without files.
- Verification:
  - Script compiles locally.
  - GitHub Actions run `27269654293` completed successfully and pushed `ad66490`, but all 300 target rows are currently `sec_source_fetch_failed`; no report HTML files were downloaded.

## Verification Commands Used Across Debugging

Representative commands used during troubleshooting:

```bash
git status --short
git diff --check
git log --oneline
node --check dashboard/app.js
python -m py_compile scripts/discover_x_account_candidates.py
python analyze_posts.py --help
wc -l <csv-file>
head -20 <file>
find . -name '<pattern>'
rg '<pattern>'
```

## Debugging Maintenance Rule

When a future issue occurs, append a new section to this file with:

1. date/time,
2. symptom,
3. affected command/workflow/file,
4. observed error text,
5. suspected cause,
6. fix applied,
7. verification result,
8. commit hash.

### 15. Repository Refactor Validation and Sandbox Workaround

- Period: `2026-06-12`
- Symptom:
  - Normal sandboxed shell commands and `apply_patch` failed with:
    - `bwrap: Unexpected capabilities but not setuid, old file caps config?`
- Root cause:
  - Local execution sandbox failed before command/file operations could start. This was an environment issue, not a repository syntax or pipeline issue.
- Fix:
  - Used approved escalated shell commands to inspect files and apply the conservative refactor.
  - Kept root entrypoints as wrappers and added `scripts/validate_repository_state.py` for static compatibility checks.
- Verification:
  - Ran `git diff --check`, Python compile checks, Node syntax checks, help commands, and repository validator.
  - No X scraping, SEC download, or Fortune expansion collection was run.

### 16. Governance Validation Added Without Data Mutation

- Period: `2026-06-12`
- Scope:
  - Added governance documents and local/static validators.
  - No scraping, SEC download, `data/` mutation, or `dashboard/data/` mutation was performed.
- Verification:
  - Governance validators were added to check agent rules, claim boundaries, history integrity, and Fortune expansion readiness without reading secrets or calling external services.

### 17. Fortune Top 100 Verification Gate Added Without Collection

- Period: `2026-06-12`
- Scope:
  - Added account verification master CSV, schema alignment, protocol documentation, and validator rules.
  - No X scraping, Fortune 500 collection, SEC download, `data/` mutation, or `dashboard/data/` mutation was performed.
- Boundary:
  - Candidate X handles are not official-account claims.
  - SEC 10-K fetch failure does not block account verification, but financial linkage analysis remains unavailable where SEC fetch failed.
