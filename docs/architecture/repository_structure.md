# Repository Structure

Last updated: 2026-06-12

This document records the conservative repository organization completed before any Fortune Top 100 or Fortune 500 expansion work. The refactor preserves the active three-brand pipeline and keeps root entrypoints compatible with existing GitHub Actions workflows.

## Current Classification

| Category | Current files/directories | Status |
| --- | --- | --- |
| Root entrypoints | `scrape_x.py`, `analyze_posts.py`, `export_research_outputs.py`, `sync_dashboard_data.py` | Backward-compatible wrappers that import `src/x_scrapper/...`. |
| Scraper code | `src/x_scrapper/collection/x_scraper.py`, `scripts/scrape_x.py` | Active implementation copied from the root scraper. No scraping was run. |
| Analysis code | `src/x_scrapper/analysis/pipeline.py`, `scripts/analyze_posts.py` | Active LDA, zero-shot sentiment, and HSQ humor analysis implementation. |
| Export code | `src/x_scrapper/exports/research_outputs.py`, `scripts/export_research_outputs.py` | Active paper/research export implementation. |
| Dashboard code | `dashboard/`, `src/x_scrapper/dashboard/sync_data.py`, `scripts/sync_dashboard_data.py` | Active Cloudflare Pages static dashboard and data sync implementation. |
| Fortune account verification code | `scripts/check_fortune2025_x_direct_profiles.py`, `src/x_scrapper/fortune/x_account_verification.py` | Existing direct-profile checker preserved. It does not certify official accounts. |
| Fortune 10-K collection code | `scripts/collect_fortune2025_10k_reports.py`, `src/x_scrapper/fortune/tenk_collector.py` | Existing collector preserved behind script wrapper. No SEC download was run. |
| Config files | `config/*.json`, `config/*.txt`, `config/*.csv`, `config/taxonomies/`, `config/fortune2025/`, `config/schemas/` | Compatibility files retained; namespaced copies added. |
| Current brand data | `data/wendys/`, `data/cocacola/`, `data/moonpie/` | Not moved. |
| Dashboard data | `dashboard/data/` | Not moved; dashboard fetch paths remain `data/...` relative to `dashboard/`. |
| Audit files | `data/audit/` | Not moved. Future Fortune namespace can be added after compatibility review. |
| Paper/research docs | `docs/paper/` | Existing paper docs retained. |
| Work logs | `WORK_LOG*.md`, `PROJECT_HISTORY.md`, `TROUBLESHOOTING_AND_DEBUGGING_LOG.md` | Root legacy logs retained and linked from README/history. |
| Deprecated or legacy files | Root one-off markdown outputs such as `wendys_lda_topics.md`, `cocacola_zero_shot_sentiment.md` | Not deleted. Treat as legacy outputs unless a future audit confirms migration. |

## New Package Layout

```text
src/x_scrapper/
├── paths.py
├── collection/x_scraper.py
├── analysis/pipeline.py
├── exports/research_outputs.py
├── dashboard/sync_data.py
├── fortune/x_account_verification.py
├── fortune/tenk_collector.py
├── fortune/industry_codes.py
├── fortune/humor_panel.py
└── utils/
```

The `src/x_scrapper/paths.py` module centralizes repository, data, dashboard, config, audit, analysis, brand, and Fortune 2025 path constants. Existing scripts still allow environment-variable path overrides where they already existed.

## Compatibility Rules

- Root entrypoints remain present for GitHub Actions and local commands.
- `scripts/` entrypoints exist for the target architecture and import the same `src` modules.
- Existing `config/*.json`, `config/*.txt`, and `config/*.csv` files remain in place because workflows and legacy docs may reference them directly.
- Namespaced config copies were added under `config/taxonomies/` and `config/fortune2025/` for future migration.
- `data/wendys`, `data/cocacola`, `data/moonpie`, and `dashboard/data` were not moved.

## Namespace Plan, Not Yet Executed

Future migration can move or re-point data only after workflow and dashboard consumers are updated together:

| Current path | Future namespace candidate | Migration status |
| --- | --- | --- |
| `data/wendys/` | `data/brands/wendys/` or retained current path | Planned only. |
| `data/cocacola/` | `data/brands/cocacola/` or retained current path | Planned only. |
| `data/moonpie/` | `data/brands/moonpie/` or retained current path | Planned only. |
| `dashboard/data/` | Retain as deployment-facing mirror | Planned only; fetch paths should remain stable. |
| `data/audit/fortune2025_*` | `data/fortune2025/.../audit/` | Planned only. |
| `data/sec_10k/` | `data/fortune2025/sec_10k/` | Planned only; no movement in this refactor. |

## Validation Boundary

The repository validator checks structure, compatibility wrappers, schemas, dashboard references, and preserved data directories. It intentionally does not perform scraping, X account checks, SEC collection, model inference, or dashboard build/deploy.
