# X Brand Intelligence Scraper and Dashboard

`Vulter3653/x_scrapper`는 X/Twitter 브랜드 계정의 포스트를 수집하고, LDA topic analysis, zero-shot sentiment, HSQ humor classification, research export, Cloudflare Pages dashboard까지 연결하는 데이터 파이프라인입니다.

## Dashboard Links

- Main dashboard: https://x-scrapper.pages.dev/
- Manual review guide dashboard: https://x-scrapper.pages.dev/review.html
- Cloudflare Pages source directory: `dashboard/`

Cloudflare Pages 설정은 다음 구조를 전제로 합니다.

```text
Framework preset: None/static
Build command: empty
Build output directory: dashboard
Functions directory: functions
```

## Current Operating Scope

현재 자동 수집 및 분석 대상 브랜드는 다음 3개입니다.

| Brand | X screen name | Data slug | Data folder |
| --- | --- | --- | --- |
| Wendy's | `Wendys` | `wendys` | `data/wendys/` |
| Coca-Cola | `CocaCola` | `cocacola` | `data/cocacola/` |
| MoonPie | `MoonPie` | `moonpie` | `data/moonpie/` |

Fortune 확장 작업은 현재 예측 기반 Fortune 100 discovery 파일을 제거하고, Fortune 2025 ranking extraction 기준으로만 관리합니다.

| File | Meaning |
| --- | --- |
| `fortune2025_itemListElement_rows.csv` | Fortune 2025 ranking extraction 원본, 1000 data rows. |
| `config/fortune2025_top100_x_account_index.csv` | Fortune 2025 rank 1-100 기준 X direct profile 확인 index. 공식 계정 확정값이 아니라 `unknown` baseline입니다. |
| `config/fortune2025_top100_x_direct_check.csv` | `https://x.com/{normalized_firm_name}` 1차 direct profile 후보 및 확인 상태, top 100 기준. |
| `data/audit/fortune2025_top100_x_direct_profile_audit.csv` | direct X profile 확인 audit 로그, top 100 기준. |
| `config/fortune2025_top100_10k_report_index.csv` | Fortune 2025 top 100의 2025/2024/2023 SEC 10-K manifest. |
| `data/audit/fortune2025_top100_10k_report_audit.csv` | 10-K CIK 매칭/filing 조회/download audit 로그. |

## Repository Map

| Path | Purpose |
| --- | --- |
| `scrape_x.py` | Playwright 기반 X post scraper. X cookies를 주입하고 GraphQL response를 캡처합니다. |
| `analyze_posts.py` | LDA, zero-shot sentiment, HSQ humor classification 실행 entrypoint. |
| `export_research_outputs.py` | 논문/보고서용 joined table, correlation, robustness table, sampling audit candidate export. |
| `sync_dashboard_data.py` | `data/` 결과를 `dashboard/data/`로 복사합니다. `--help` 전용 모드가 없고 실행 즉시 sync합니다. |
| `dashboard/` | Cloudflare Pages 정적 dashboard. React UMD 기반이며 별도 build step이 없습니다. |
| `dashboard/data/` | dashboard가 fetch하는 JSON/CSV 복사본. |
| `data/<brand>/` | 브랜드별 raw scrape 및 analysis 결과. |
| `data/analysis/` | 브랜드 통합 research export 결과. |
| `config/` | analysis label, stopword, Fortune 2025 index 등 설정성 데이터. |
| `docs/paper/` | 논문/보고서 작성용 문서. |
| `.github/workflows/` | GitHub Actions automation. |
| `PROJECT_HISTORY.md` | 전체 작업 이력 ledger. |
| `TROUBLESHOOTING_AND_DEBUGGING_LOG.md` | 트러블슈팅/디버깅 중앙 기록. |
| `WORK_LOG*.md` | 세부 작업별 legacy work log. |


## Repository Organization Update (2026-06-12)

A conservative `src/x_scrapper/` package layout has been added before Fortune expansion work. Existing root commands remain compatible and now delegate to the package implementation:

```bash
python scrape_x.py
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
python scripts/collect_fortune2025_10k_reports.py --help
```

New structural documentation and validation live at:

| Path | Purpose |
| --- | --- |
| `src/x_scrapper/paths.py` | Central repository/data/dashboard/config/audit path constants. |
| `docs/architecture/repository_structure.md` | Current file classification, compatibility rules, and namespace plan. |
| `docs/methodology/fortune500_humor_text_analysis_design.md` | Fortune 500 humor text-analysis design, without starting collection. |
| `scripts/validate_repository_state.py` | Static repository structure validator. |
| `config/taxonomies/` | Namespaced copies of humor, sentiment, and LDA taxonomy config. |
| `config/fortune2025/` | Namespaced copies of active Fortune 2025 support CSVs. |
| `config/schemas/` | Future Fortune account verification and humor panel JSON schemas. |

Compatibility note: `data/wendys/`, `data/cocacola/`, `data/moonpie/`, and `dashboard/data/` were not moved. Dashboard fetch paths remain relative to `dashboard/` as `data/...`.


## Governance and Validation

Governance documents define agent roles, change control, claim boundaries, and Fortune expansion gates:

| File | Purpose |
| --- | --- |
| `AGENT_RULES.md` | Codex/Gemini roles, one-writer rule, forbidden commands, secret handling, final report format, Fortune no-scrape gate. |
| `DATA_CLAIM_BOUNDARIES.md` | Limits on what current data, model outputs, Fortune account files, NAICS/SIC fields, dashboard views, and SEC files can claim. |
| `CHANGE_CONTROL.md` | Change classes, pre-change checklist, commit rules, review rules, and rollback rules. |
| `docs/operations/agent_concurrency_protocol.md` | Multi-agent handoff and branch protocol. |
| `docs/operations/validation_protocol.md` | Required static validation commands and validator contract. |
| `docs/operations/fortune_expansion_gatekeeping.md` | Top 100 verification and Fortune 500 expansion gatekeeping. |


### File Lock Table

Only one non-human writer may modify files at a time.

| Agent | Mode | Allowed Files | Forbidden Files | Current Task | Status |
| --- | --- | --- | --- | --- | --- |
| Codex | Writer | task-scoped files | `data/`, `dashboard/data/`, secrets, destructive git operations | active implementation | active or standby |
| Gemini | Auditor | read-only review outputs | all repository files unless explicitly authorized | governance audit / gap review | auditor |
| Human | Owner | all files | secrets must not be exposed | approval and final decision | owner |

Governance validation commands:

```bash
python scripts/validate_repository_state.py
python scripts/validate_agent_rules.py
python scripts/validate_data_claim_boundaries.py
python scripts/validate_history_integrity.py
python scripts/validate_fortune_expansion_readiness.py
```

These validators are local/static checks. They do not read secrets, scrape X, call external networks, run SEC downloads, or modify `data/` or `dashboard/data/`.

## Data Layout

브랜드별 표준 결과 구조는 다음과 같습니다.

```text
data/<account>/posts.json
data/<account>/scrape_state.json
data/<account>/lda_topics.json
data/<account>/lda_topics.md
data/<account>/zero_shot_sentiment.json
data/<account>/zero_shot_sentiment.md
data/<account>/hsq_humor_classification.json
data/<account>/hsq_humor_classification.md
```

Dashboard 배포용 데이터는 다음 위치로 동기화됩니다.

```text
dashboard/data/<account>/posts.json
dashboard/data/<account>/scrape_state.json
dashboard/data/<account>/lda_topics.json
dashboard/data/<account>/zero_shot_sentiment.json
dashboard/data/<account>/hsq_humor_classification.json
dashboard/data/analysis/*.json
dashboard/data/analysis/*.csv
```


## Fortune Top 100 X Account Verification Gate

The Fortune Top 100 verification gate is account verification only. It does not scrape X, expand to Fortune 500, download SEC filings, or create dashboard claims.

| File | Purpose |
| --- | --- |
| `config/fortune2025_x_account_verification_master.csv` | Top 100 review master initialized with candidate X handles, no official-account claims, and `scrape_eligible=false`. |
| `config/schemas/fortune2025_x_account_verification_master.schema.json` | Controlled schema for status, evidence source type, evidence strength, confidence, and scrape eligibility. |
| `docs/operations/fortune_top100_x_account_verification_protocol.md` | Manual verification protocol and scrape eligibility gate. |

Scrape eligibility requires all of the following: `official_x_account_status` is `official` or `brand_official`, `confidence` is `high` or `medium`, `evidence_source_url` is present, and `official_x_url` is present. `not_reviewed` is the default evidence source type for initialized, unreviewed rows. `manual_search_only` is reserved for rows where a reviewer actually searched and found only search-result-level evidence. Search-result-only evidence is insufficient for official status, and Level 8 evidence is never scrape-eligible.

Fortune 500 expansion remains blocked until Top 100 verification is complete and validated. X post coverage is not a complete historical archive; humor and sentiment labels are model-generated unless manually audited; dashboard analytics are descriptive only and authorize no causal claims. SEC 10-K fetch failure does not block account verification, but financial linkage analysis remains unavailable where SEC fetch failed.

Validation:

```bash
python scripts/validate_fortune_expansion_readiness.py
```

## GitHub Actions Workflows

| Workflow | File | Trigger | Purpose |
| --- | --- | --- | --- |
| Scrape X Posts | `.github/workflows/scrape.yml` | schedule, manual | Scrape brands, run all analyses, export research tables, sync dashboard data, commit/push. |
| Run LDA Analysis | `.github/workflows/lda.yml` | manual | Re-run LDA only for an existing `data/<account>/posts.json`. |
| Run Zero-Shot Sentiment | `.github/workflows/sentiment.yml` | manual | Re-run sentiment only. |
| Run HSQ Humor Classification | `.github/workflows/humor.yml` | manual | Re-run HSQ zero-shot humor classification only. |
| Dashboard Check | `.github/workflows/dashboard-check.yml` | dashboard changes, manual | Validate static dashboard files and JavaScript syntax. |
| Check Fortune 2025 Direct X Profiles | `.github/workflows/check-fortune-x-direct.yml` | manual | Check `https://x.com/{normalized company name}` candidates for Fortune 2025 rows using X cookies. |
| Collect Fortune 2025 Top 100 10-K Reports | `.github/workflows/collect-fortune-10k.yml` | workflow file push, manual | Collect SEC EDGAR 10-K manifest/audit and upload report files as an artifact. |

### Scheduled Run

`Scrape X Posts` runs daily at Korean time 00:37.

```text
UTC cron: 37 15 * * *
KST: daily 00:37
```

Scheduled runs use a matrix for `Wendys`, `CocaCola`, and `MoonPie`. After scrape artifacts are collected, the aggregate-analysis job runs:

```bash
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
```

The workflow then validates scripts/dashboard files and commits results back to `main`.

### Manual Scrape Run

In GitHub Actions, open `Scrape X Posts` and use `Run workflow`.

Inputs:

| Input | Default | Meaning |
| --- | --- | --- |
| `target_user` | `ALL` | `ALL`, `Wendys`, `CocaCola`, or `MoonPie`. |
| `max_scrolls` | `2500` | Maximum browser scroll attempts. |
| `scroll_delay_seconds` | `1.25` | Delay after each scroll. |
| `idle_scroll_limit` | `60` | Stop after this many scrolls without new posts. |

Required repository secrets:

```text
X_AUTH_TOKEN
X_CT0
```

Secrets must come from an authenticated browser session on `x.com`. They must not be committed to this repository.

## Local Setup

Install dependencies by task type.

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-scrape.txt
pip install -r requirements-lda.txt
pip install -r requirements-sentiment.txt
python -m playwright install chromium
```

For local scraping, set X cookie values first.

```bash
export X_AUTH_TOKEN='browser auth_token cookie value'
export X_CT0='browser ct0 cookie value'
export TARGET_USER='Wendys'
export MAX_SCROLLS='2500'
export SCROLL_DELAY_SECONDS='1.25'
export IDLE_SCROLL_LIMIT='60'
export HEADLESS='true'
python scrape_x.py
```

Scraper outputs are written to:

```text
data/<target_user_slug>/posts.json
data/<target_user_slug>/scrape_state.json
```

## Analysis Usage

`analyze_posts.py` supports one required mode selector:

```bash
python analyze_posts.py --task all
python analyze_posts.py --task lda
python analyze_posts.py --task sentiment
python analyze_posts.py --task humor
```

Common environment variables:

| Variable | Default | Used by | Meaning |
| --- | --- | --- | --- |
| `TARGET_USER` | `Wendys` | all analysis tasks | Brand/account to analyze. |
| `ANALYSIS_MAX_POSTS` | `0` in workflows | all analysis tasks | `0` means all posts. Smaller number is useful for tests. |
| `LDA_MIN_TOPICS` | `2` | LDA | Minimum candidate topic count. |
| `LDA_MAX_TOPICS` | `9` | LDA | Maximum candidate topic count. |
| `SENTIMENT_LABELS` | `positive,neutral,negative` | sentiment | Comma-separated zero-shot labels. |

Example:

```bash
export TARGET_USER='MoonPie'
export ANALYSIS_MAX_POSTS='0'
export LDA_MIN_TOPICS='2'
export LDA_MAX_TOPICS='9'
python analyze_posts.py --task lda
```

### LDA Output

```text
data/<account>/lda_topics.json
data/<account>/lda_topics.md
```

LDA topic count is selected automatically by coherence over the configured candidate range. It is not a fixed manual topic number.

### Zero-Shot Sentiment Output

```text
data/<account>/zero_shot_sentiment.json
data/<account>/zero_shot_sentiment.md
```

Default labels are:

```text
positive, neutral, negative
```

### HSQ Humor Classification Output

```text
data/<account>/hsq_humor_classification.json
data/<account>/hsq_humor_classification.md
```

Codebook:

```text
HSQ_zero_shot_humor_classification_codebook.md
```

Primary labels:

```text
Affiliative humor
Self-enhancing humor
Aggressive humor
Self-defeating humor
```

## Research Export Usage

Run research export after scrape/analysis outputs exist.

```bash
python export_research_outputs.py
```

Optional arguments:

```bash
python export_research_outputs.py --brands wendys,cocacola,moonpie --audit-limit 150
```

Key outputs:

```text
data/analysis/joined_posts.csv
data/analysis/joined_posts.json
data/analysis/correlation_coefficients.csv
data/analysis/correlation_coefficients.json
data/analysis/table4_humor_sentiment_engagement.csv
data/analysis/table4_humor_sentiment_engagement.json
data/analysis/table5_engagement_robustness_by_humor.csv
data/analysis/table5_engagement_robustness_by_humor.json
data/analysis/sampling_audit_candidates.csv
data/analysis/sampling_audit_candidates.json
data/analysis/research_export_summary.md
```

Then sync dashboard data:

```bash
python sync_dashboard_data.py
```

## Dashboard Usage

The dashboard is static and reads files from `dashboard/data/` by browser `fetch()`.

Main files:

| File | Purpose |
| --- | --- |
| `dashboard/index.html` | Main dashboard shell. |
| `dashboard/app.js` | Main React dashboard logic. |
| `dashboard/styles.css` | Main styling. |
| `dashboard/brand-visual.css` | Brand visualization styling. |
| `dashboard/review.html` | Manual review guide page. |
| `dashboard/research-review.js` | Manual review guide logic. |

Dashboard sections include:

- Overview / Dataset status
- Brand comparison
- Descriptive statistics
- Model-free evidence
- Posting volume
- Engagement mix
- LDA topics
- Zero-shot sentiment
- HSQ humor analysis
- Post Explorer
- Research review guide

Run local static preview from the repository root:

```bash
python -m http.server 4173 -d dashboard
```

Open:

```text
http://127.0.0.1:4173/
http://127.0.0.1:4173/review.html
```

## Dashboard Validation

Use Node syntax checks for dashboard JavaScript.

```bash
node --check dashboard/app.js
node --check dashboard/localize-ko.js
node --check dashboard/low-confidence-review.js
node --check dashboard/humor-sentiment-engagement.js
node --check dashboard/engagement-robustness.js
node --check dashboard/brand-interpretation.js
node --check dashboard/research-review.js
```

Use Python compile checks for core scripts.

```bash
python -m py_compile scrape_x.py analyze_posts.py export_research_outputs.py sync_dashboard_data.py
```

The dashboard should not load deprecated overlay scripts:

```text
dashboard/brand-view-ko.js
dashboard/humor-matrix.js
```

## Fortune 2025 Workflow Status

The active Fortune file flow is intentionally conservative.

1. `fortune2025_itemListElement_rows.csv` provides the source ranking rows.
2. `config/fortune2025_top100_x_account_index.csv` keeps rank 1-100 rows and X direct profile candidate columns.
3. `official_x_account_status` stays `unknown` until manual verification.
4. Previous prediction-based Fortune 100 discovery files and workflow were removed.

Do not treat `x_handle_candidate` as an official corporate account until manually checked against company website/social links and the X profile external URL.



## Fortune 2025 Top 100 10-K Reports

Official X account confirmation is currently paused. The active financial-document task is SEC 10-K collection for Fortune 2025 top 100 companies.

Target years:

```text
2025, 2024, 2023
```

Collector script:

```bash
python scripts/collect_fortune2025_10k_reports.py --rank-limit 100 --years 2025,2024,2023
```

The script uses official SEC EDGAR data endpoints:

```text
https://www.sec.gov/files/company_tickers.json
https://data.sec.gov/submissions/CIK##########.json
https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primaryDocument}
```

Outputs tracked in git:

```text
config/fortune2025_top100_10k_report_index.csv
data/audit/fortune2025_top100_10k_report_audit.csv
```

Report HTML files are not committed because they can be large. When the workflow runs with `download_reports=true`, report files are uploaded as the GitHub Actions artifact:

```text
fortune-2025-top100-10k-reports
```

Manual GitHub Actions run:

1. Open `Collect Fortune 2025 Top 100 10-K Reports`.
2. Use `rank_limit=100`.
3. Use `years=2025,2024,2023`.
4. Use `download_reports=true` to include primary 10-K documents in the artifact.
5. Use `commit_manifest=true` to commit only the manifest/audit CSV files.

Current status: both the local environment and the GitHub Actions runner returned SEC HTTP 403 for `www.sec.gov/files/company_tickers.json`. The workflow now records this as `sec_source_fetch_failed` in the 300-row top100 x 3-year manifest/audit instead of failing silently. Actual 10-K report files still require an SEC-accessible execution environment or a provided SEC source/cache.

## Fortune 2025 Direct X Profile Check

The first-pass X account check follows this rule:

```text
Firm name -> normalized handle candidate -> https://x.com/{candidate}
Example: Amazon -> @amazon -> https://x.com/amazon
```

Run locally:

```bash
export X_AUTH_TOKEN='browser auth_token cookie value'
export X_CT0='browser ct0 cookie value'
python scripts/check_fortune2025_x_direct_profiles.py --rank-limit 100
```

If `X_AUTH_TOKEN` or `X_CT0` is missing, the script still generates all direct URL candidates, but marks every row as:

```text
direct_profile_exists=unknown
direct_check_status=not_checked_missing_credentials
```

Outputs:

```text
config/fortune2025_top100_x_direct_check.csv
data/audit/fortune2025_top100_x_direct_profile_audit.csv
config/fortune2025_top100_x_account_index.csv
```

GitHub Actions:

1. Open `Check Fortune 2025 Direct X Profiles`.
2. Keep `rank_limit=100` for the stable Fortune top 100 scope.
3. Keep `commit_results=true` if the checked CSV outputs should be pushed to `main`.
4. The workflow uses repository secrets `X_AUTH_TOKEN` and `X_CT0`.

Important: this direct URL check confirms whether a profile URL appears accessible. It still does not prove the profile is the official corporate account.

## Documentation Index

| File | What it contains |
| --- | --- |
| `PROJECT_HISTORY.md` | Central chronological project history. |
| `TROUBLESHOOTING_AND_DEBUGGING_LOG.md` | Consolidated debugging and troubleshooting ledger. |
| `WORK_LOG.md` | Original long-form work log for scraper, GitHub Actions, LDA, sentiment, dashboard, and Fortune transitions. |
| `WORK_LOG_REACT_DASHBOARD_2026-05-26.md` | React dashboard redesign and boot recovery details. |
| `WORK_LOG_DASHBOARD_STABILIZATION_2026-05-26.md` | Dashboard stability and validation notes. |
| `WORK_LOG_HSQ_HUMOR_MATRIX_2026-05-26.md` | HSQ 2x2 humor matrix work. |
| `WORK_LOG_LOW_CONFIDENCE_REVIEW_2026-05-26.md` | Low-confidence review dashboard work. |
| `WORK_LOG_HUMOR_SENTIMENT_ENGAGEMENT_2026-05-26.md` | Humor-sentiment-engagement component notes. |
| `WORK_LOG_ROBUSTNESS_INTERPRETATION_VALIDATION_2026-05-26.md` | Robustness, interpretation, and validation notes. |
| `docs/paper/README.md` | Paper/research documentation index. |
| `docs/paper/CURRENT_RESULTS_STATUS.md` | Current paper-facing result status. |
| `docs/paper/PAPER_WRITING_SCOPE.md` | Writing scope. |
| `docs/paper/SAMPLING_AUDIT_PROTOCOL.md` | Sampling audit protocol. |
| `docs/paper/RESULTS_SECTION_STRUCTURE.md` | Results section structure. |
| `docs/paper/BRAND_LEVEL_RESULT_WRITING_TEMPLATE.md` | Brand-level result writing template. |
| `docs/paper/HUMAN_REVIEW_WORKFLOW.md` | Human review workflow guidance. |
| `HSQ_zero_shot_humor_classification_codebook.md` | HSQ humor classification codebook. |
| `README_SCRAPER.md` | Prior detailed scraper/dashboard operation notes. |
| `dashboard/README.md` | Cloudflare Pages dashboard deployment note. |

## Safety Notes

- Never commit `X_AUTH_TOKEN`, `X_CT0`, browser cookies, or session files.
- X metrics can change after collection; likes/replies/retweets/views are point-in-time captures.
- X may impose login challenges, rate limits, or UI/API changes.
- LDA, zero-shot sentiment, and HSQ humor labels are model-based analytical estimates, not ground truth.
- Manual review is required before using account mapping or classification outputs as verified evidence.

## Quick Commands

```bash
# Scrape one brand locally
TARGET_USER='Wendys' python scrape_x.py

# Run all analysis for one brand
TARGET_USER='Wendys' ANALYSIS_MAX_POSTS='0' python analyze_posts.py --task all

# Export research tables
python export_research_outputs.py

# Sync dashboard data
python sync_dashboard_data.py

# Validate core scripts
python -m py_compile scrape_x.py analyze_posts.py export_research_outputs.py sync_dashboard_data.py
node --check dashboard/app.js
```
