# Project History

Repository: `Vulter3653/x_scrapper`
Workspace: `/home/user/marketingstrategy`
Last updated: `2026-06-12`
Timezone note: Git commit timestamps are recorded as shown by Git. Some early commits use `+0900`; most automated commits use `+0000`.

This file is the central project history. It records what work was performed, when it was performed, which files were affected, and what operational decision was made. Detailed legacy notes remain in the `WORK_LOG*.md` files.

## Current Baseline

- The project collects and analyzes X/Twitter posts for selected brand accounts.
- Current brand data pipeline stores account-level files under `data/<account>/`.
- The dashboard consumes synced files under `dashboard/data/`.
- Fortune expansion work has been reset to the verified `fortune2025_itemListElement_rows.csv` source and the derived Fortune top 100 index.
- Predicted Fortune 100 account discovery files were removed on `2026-06-10` to avoid mixing unverified predictions with Fortune 2025 ranking data.

## Active Fortune 2025 Files

| File | Status | Purpose |
| --- | --- | --- |
| `fortune2025_itemListElement_rows.csv` | active | Raw Fortune 2025 ranking extraction, 1000 data rows. |
| `config/fortune2025_top100_x_account_index.csv` | active | Fortune 2025 rank 1-100 direct X profile index. Official account status remains `unknown` until manually verified. |

## Removed Fortune Prediction / Discovery Files

These files were intentionally removed because they were generated from earlier Fortune 100 architecture assumptions or X search candidate predictions, not from finalized manual verification.

| Removed file | Reason |
| --- | --- |
| `.github/workflows/discover-x-accounts.yml` | Removed discovery workflow to stop prediction-based account candidate generation. |
| `scripts/discover_x_account_candidates.py` | Removed X account candidate discovery script. |
| `config/fortune100_account_candidates.csv` | Removed predicted/search-derived candidate table. |
| `config/fortune100_firm_master.csv` | Removed header-only/prediction-era Fortune 100 master file. |
| `config/fortune100_firm_master.schema.json` | Removed schema tied to removed Fortune 100 master. |
| `config/fortune100_firm_master_sample.csv` | Removed sample Fortune 100 cohort file. |
| `data/audit/x_account_discovery_audit.csv` | Removed discovery audit generated from X search candidates. |
| `data/audit/x_account_discovery_recommendations.csv` | Removed recommendation output derived from X search candidate scoring. |
| `data/audit/x_account_manual_review_queue.csv` | Removed manual review queue derived from the removed candidate output. |
| `docs/fortune100_collection_audit_protocol.md` | Removed architecture document tied to old Fortune 100 phase. |
| `docs/fortune100_panel_data_design.md` | Removed architecture document tied to old Fortune 100 phase. |
| `docs/x_account_discovery_audit_report.md` | Removed report derived from predicted X candidate artifact. |
| `docs/x_account_discovery_method.md` | Removed method document tied to deleted discovery script. |

## Timeline

### 2026-05-25

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-05-25 14:16:34 +0000` | `151e591` | Updated scraped X posts for MoonPie. | Extended collected brand data. |
| `2026-05-25 14:30:41 +0000` | `1fee613` | Stored brand data in company folders. | Introduced `data/<account>/` style organization. |
| `2026-05-25 14:38:17 +0000` | `91b3bdf` | Added MoonPie dashboard and daily scrape schedule. | Expanded dashboard/account coverage. |
| `2026-05-25 14:43:11 +0000` | `a5e8ac3` | Scheduled daily scrape and analysis at KST midnight. | Automated collection and analysis timing. |
| `2026-05-25 14:49:21 +0000` | `61e7f6e` | Added HSQ zero-shot humor classification. | Added humor classification layer. |
| `2026-05-25 15:25:32 +0000` | `311eca1` | Adjusted scheduled workflow time. | Refined scheduler timing. |
| `2026-05-25 15:59:14 +0000` | `12b1e7c` | Updated scraped and analyzed X data for Wendys. | Data refresh. |
| `2026-05-25 16:10:16 +0000` | `df8715c` | Updated scraped and analyzed X data for CocaCola. | Data refresh. |
| `2026-05-25 16:17:09 +0000` | `0f57728` | Updated scraped and analyzed X data for MoonPie. | Data refresh. |
| `2026-05-25 17:22:38 +0000` | `e880dbd` | Refactored dashboard into React analytics interface. | Dashboard UI migration began. |
| `2026-05-25 17:24:08 +0000` | `3bb8288`, `6ca8162` | Updated scraped and analyzed data for MoonPie and Wendys. | Data refresh. |
| `2026-05-25 17:24:21 +0000` | `1d93d94` | Updated scraped and analyzed data for CocaCola. | Data refresh. |
| `2026-05-25 19:19:11 +0000` | `0ac87f9` | Added current paper results status. | Research documentation layer added. |

### 2026-05-26

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-05-26 01:24-01:27 +0900` | `b924dbf`, `520472e`, `2f32e51` | Continued React dashboard redesign and documented schedule. | Dashboard presentation improved. |
| `2026-05-26 01:28:05 +0900` | `22cf4ec` | Recorded React dashboard redesign work log. | See `WORK_LOG_REACT_DASHBOARD_2026-05-26.md`. |
| `2026-05-26 01:33-01:45 +0900` | `2ea98ea`, `2d8da18`, `186eac8`, `9be8edf`, `e96be2f` | Fixed dashboard loading, React boot scripts, syntax error, cache busting, and documented recovery. | Dashboard stabilization. |
| `2026-05-26 01:48-01:58 +0900` | `adc5b75`, `01cada8`, `0dc5f16`, `b2727bc`, `21c5bee` | Enhanced analytics features and added Korean localization layer. | UX and localization work. |
| `2026-05-26 02:02-02:03 +0900` | `3c54330`, `79008c4`, `13b08c4` | Added HSQ humor 2x2 matrix dashboard and log. | See `WORK_LOG_HSQ_HUMOR_MATRIX_2026-05-26.md`. |
| `2026-05-26 02:08-02:13 +0900` | `d172286`, `5bce6ec`, `bb24dd8`, `3ffa58c` | Added brand-level visualization and stabilized dashboard tabs. | Dashboard reliability work. |
| `2026-05-26 02:23-03:00 +0900` | `00a3671`, `aa300f7`, `2b7a6c4`, `f04fcc2`, `4a2e86a`, `3d8d998`, `f08bc12`, `a1a8296` | Integrated visualizations, added validation workflow, removed deprecated overlay scripts, and recorded stabilization rules. | Validation and maintainability work. |
| `2026-05-26 03:11-03:27 +0900` | `b0ba785`, `f9098d0`, `96cfdcd`, `060b03b` | Added, loaded, validated, and logged low-confidence review dashboard component. | Later converted to guide-only review surface. |
| `2026-05-26 03:35-03:37 +0900` | `fd2c131`, `ea22c65`, `22e12cf`, `9caad38` | Added humor/sentiment/engagement dashboard component and log. | See `WORK_LOG_HUMOR_SENTIMENT_ENGAGEMENT_2026-05-26.md`. |
| `2026-05-26 03:42-03:45 +0900` | `cc38989`, `153b7ce`, `1518964`, `4e523b9`, `4fb901e` | Added robustness and brand interpretation components, strengthened static validation, and logged work. | See `WORK_LOG_ROBUSTNESS_INTERPRETATION_VALIDATION_2026-05-26.md`. |
| `2026-05-26 03:49:51 +0900` | `5f77265` | Preserved English analytical keywords in Korean dashboard. | UI copy consistency. |
| `2026-05-26 03:56-04:01 +0900` | `50082f4`, `a82c317`, `e9f82ff`, `ed4522b`, `acae826` | Added paper writing scope, sampling audit protocol, results structure, brand-level result template, and paper docs index. | Research writing documentation. |
| `2026-05-26 04:50:12 +0000` | `ad73a0b` | Added research export analysis tables. | Research output export support. |
| `2026-05-26 05:04-05:21 +0000` | `2ccebc8`, `0530633`, `4040c11` | Added human review workflow dashboard, separated it, then converted review dashboard to guide. | Human work shifted to guidance-only UI. |
| `2026-05-26 18:19:26 +0000` | `a47149a` | Updated scraped and analyzed X data for Wendys. | Data refresh. |

### 2026-05-27

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-05-27 05:19:13 +0000` | `d4e8e94` | Added Gemini handoff guidelines. | Created instructions for external agent continuation. |
| `2026-05-27 05:23:13 +0000` | `d82dab3` | Documented multi-brand automation fix for Gemini. | Noted failures outside Wendy's and expected fixes. |
| `2026-05-27 05:28:47 +0000` | `d6af6ff` | Refactored workflow to separate scrape and aggregate-analysis jobs. | Parallelized pipeline phases. |
| `2026-05-27 05:33:56 +0000` | `103e41b` | Allowed manual update for all brands via workflow_dispatch. | Added broader manual control. |
| `2026-05-27 05:52:03 +0000` | `af781a0` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-05-27 06:21:44 +0000` | `ab481dc` | Refactored workflow for data consistency, improved dashboard UI and analysis metadata. | Pipeline and dashboard consistency update. |
| `2026-05-27 18:29:30 +0000` | `e11ea6c` | Updated scraped and analyzed X data for all brands. | Data refresh. |

### 2026-05-28 to 2026-05-31

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-05-28 18:39:41 +0000` | `cfd4c86` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-05-29 18:34:31 +0000` | `8d98cbd` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-05-30 16:56:17 +0000` | `8fd5978` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-05-31 17:02:11 +0000` | `93338db` | Updated scraped and analyzed X data for all brands. | Data refresh. |

### 2026-06-01

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-06-01 18:38:02 +0000` | `f335c95` | Added Fortune 100 panel architecture. | Designed initial Fortune 100 master/schema/panel architecture. Later removed when user requested Fortune 2025 ranking-only baseline. |
| `2026-06-01 18:51:51 +0000` | `f9bbc46` | Added Fortune 100 X account discovery audit. | Added Playwright/X-search candidate discovery script and audit outputs. Later removed. |
| `2026-06-01 19:02:10 +0000` | `3b11fc1` | Added Fortune X account discovery workflow. | Added manual GitHub Actions workflow for candidate discovery. Later removed. |
| `2026-06-01 20:23:50 +0000` | `d8a907e` | Updated scraped and analyzed X data for all brands. | Data refresh. |

### 2026-06-02 to 2026-06-09

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-06-02 19:22:05 +0000` | `25f0ab0` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-06-04 18:20:10 +0000` | `d1f6592` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-06-06 17:03:15 +0000` | `d99a19c` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-06-07 17:09:05 +0000` | `c6fd83e` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-06-08 18:33:31 +0000` | `46ca91a` | Updated scraped and analyzed X data for all brands. | Data refresh. |
| `2026-06-09 17:55:32 +0000` | `38ca9ff` | Updated scraped and analyzed X data for all brands. | Data refresh. |

### 2026-06-10

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-06-10 09:02:54 +0000` | `d015544` | Added Fortune 2025 X account index. | Added `fortune2025_itemListElement_rows.csv` and `config/fortune2025_top100_x_account_index.csv`. Initial Fortune 500 rows were based on the 2025 ranking CSV; active direct-check scope is now top 100. X account fields remain candidate/unknown unless manually verified. |
| `2026-06-10 09:07:18 +0000` | `b5fca98` | Removed predicted Fortune account discovery files. | Deleted prior Fortune 100 prediction/discovery artifacts, audit outputs, discovery script, and discovery workflow. Preserved Fortune 2025 source/index files. |
| `2026-06-10` | `2db4688` | Expanded README usage documentation. | Added dashboard links, workflow usage, local commands, data layout, document index, and Fortune 2025 status. |
| `2026-06-10` | `this commit` | Added Fortune 2025 direct X profile check. | Added script, manual GitHub Actions workflow, direct check CSV, audit CSV, and regenerated account index around `https://x.com/{normalized_firm_name}` first-pass checks. Scope later narrowed to Fortune top 100 for stability. |
| `2026-06-10` | `pending` | Narrowed Fortune direct X profile check to top 100. | Cancelled the 500-row run, changed workflow/script defaults to rank 100, and regenerated top 100 direct check/account index outputs. |
| `2026-06-10` | `33c899e`, `24351b1`, `ad66490` | Added Fortune top 100 SEC 10-K collection workflow and failure audit. | Added EDGAR 10-K collector script and GitHub Actions workflow. Local and GitHub SEC access both returned HTTP 403, so the workflow now commits 300-row manifest/audit files with `sec_source_fetch_failed` status for 100 firms x 2025/2024/2023. |

### 2026-06-12

| Time | Commit | Work performed | Notes |
| --- | --- | --- | --- |
| `2026-06-12` | `pending` | Conservatively reorganized repository before Fortune expansion. | Added `src/x_scrapper/` package, path constants, wrapper entrypoints, namespaced config copies, schemas, architecture/methodology docs, and static repository validator. No Fortune 500 collection, new X scraping, or SEC download was run. |
| `2026-06-12` | `pending` | Added governance layer and claim-boundary validators. | Added `AGENT_RULES.md`, `DATA_CLAIM_BOUNDARIES.md`, `CHANGE_CONTROL.md`, operations protocols, File Lock Table, controlled account-status taxonomy checks, SEC 10-K failure boundary, and static validators. No scraping, SEC download, data mutation, or dashboard data mutation was performed. |
| `2026-06-12` | `pending` | Added Fortune Top 100 X account verification gate. | Added `config/fortune2025_x_account_verification_master.csv`, aligned the verification schema enum with governance taxonomy, documented the Top 100 account verification protocol, and strengthened `scripts/validate_fortune_expansion_readiness.py`. No X scraping, Fortune 500 collection, SEC download, `data/`, or `dashboard/data/` mutation was performed. |
| `2026-06-12` | `pending` | Clarified unreviewed Fortune X account evidence state. | Added `not_reviewed` evidence source type, changed initialized Top 100 rows from `manual_search_only` to `not_reviewed`, and strengthened validator scrape-eligibility rules. No X scraping, Fortune 500 collection, SEC download, `data/`, or `dashboard/data/` mutation was performed. |
| `2026-06-12` | `pending` | Ran Fortune Top 100 ranks 1-10 X account verification pilot. | Updated only `config/fortune2025_x_account_verification_master.csv` for ranks 1-10 using official company-source evidence. Ranks 11-100 remain unreviewed. No X post scraping, timeline collection, Fortune 500 expansion, SEC download, `data/`, or `dashboard/data/` mutation was performed. |
| `2026-06-12` | `pending` | Continued Fortune Top 100 ranks 11-30 X account verification. | Updated only `config/fortune2025_x_account_verification_master.csv` for ranks 11-30 using official company-source evidence. Ranks 31-100 remain unreviewed. No X post scraping, timeline collection, Fortune 500 expansion, SEC download, `data/`, or `dashboard/data/` mutation was performed. |
| `2026-06-12` | `pending` | Continued Fortune Top 100 ranks 31-50 X account verification. | Updated only `config/fortune2025_x_account_verification_master.csv` for ranks 31-50 using official company-source evidence. No X post scraping, timeline collection, Fortune 500 expansion, SEC download, `data/`, or `dashboard/data/` mutation was performed. |

## Operational Decisions

1. Fortune work now uses `fortune2025_itemListElement_rows.csv` as the active ranking source.
2. The current Fortune top 100 index does not claim that a candidate handle is an official corporate X account.
3. `official_x_account_status` remains `unknown` until manual verification against official company sources.
4. Prior X search candidate discovery outputs were removed to avoid mixing predicted/unverified results with the Fortune 2025 ranking baseline.
5. Historical commits remain in Git history, but active files should be interpreted according to the current baseline above.
6. Root entrypoints are retained as compatibility wrappers; active implementation now lives under `src/x_scrapper/` for future refactoring.
8. Current data and dashboard outputs are descriptive artifacts with explicit claim boundaries; they do not imply complete X history, official Fortune accounts, human-validated humor, causal effects, complete NAICS/SIC coverage, or successful SEC body downloads.
10. Scrape eligibility requires `official` or `brand_official`, high or medium confidence, evidence source URL, and official X URL; Fortune 500 expansion remains blocked until Top 100 verification is complete and validated.
9. Fortune Top 100 X account verification now uses `config/fortune2025_x_account_verification_master.csv` as the manual review gate; all initialized rows remain `unknown`, `blocked`, and not scrape eligible until evidence is recorded.
7. Governance files now define Codex as Writer and Gemini as Auditor, enforce one-writer change control, and gate Fortune scraping behind Top 100 official-account verification.
11. The rank 1-10 verification pilot records only account officiality evidence and scrape eligibility metadata; it does not authorize scraping or any claim of complete historical X coverage.
12. The rank 11-30 verification batch follows the same official-source-first protocol; candidate handles remain non-official unless supported by a recorded official evidence URL.

## Related Work Logs

- `docs/operations/fortune_top100_x_account_verification_protocol.md`
- `docs/operations/fortune_expansion_gatekeeping.md`
- `docs/operations/validation_protocol.md`
- `CHANGE_CONTROL.md`
- `DATA_CLAIM_BOUNDARIES.md`
- `AGENT_RULES.md`
- `docs/architecture/repository_structure.md`
- `docs/methodology/fortune500_humor_text_analysis_design.md`
- `TROUBLESHOOTING_AND_DEBUGGING_LOG.md`
- `WORK_LOG.md`
- `WORK_LOG_REACT_DASHBOARD_2026-05-26.md`
- `WORK_LOG_DASHBOARD_STABILIZATION_2026-05-26.md`
- `WORK_LOG_HSQ_HUMOR_MATRIX_2026-05-26.md`
- `WORK_LOG_LOW_CONFIDENCE_REVIEW_2026-05-26.md`
- `WORK_LOG_HUMOR_SENTIMENT_ENGAGEMENT_2026-05-26.md`
- `WORK_LOG_ROBUSTNESS_INTERPRETATION_VALIDATION_2026-05-26.md`

## Maintenance Rule

Whenever a new meaningful repository change is made, append one row to this file with:

- date/time,
- commit hash,
- short task name,
- files changed,
- whether the result is active, deprecated, or removed,
- verification performed.
