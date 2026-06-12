# Validation Protocol

Last updated: 2026-06-12

## Purpose

Validation must prove the requested scope is safe without starting out-of-scope collection. Governance validation is static and local.

## Governance Validation Commands

```bash
git status --short
git diff --check
python -m py_compile scripts/validate_repository_state.py
python -m py_compile scripts/validate_agent_rules.py
python -m py_compile scripts/validate_data_claim_boundaries.py
python -m py_compile scripts/validate_history_integrity.py
python -m py_compile scripts/validate_fortune_expansion_readiness.py
python scripts/validate_repository_state.py
python scripts/validate_agent_rules.py
python scripts/validate_data_claim_boundaries.py
python scripts/validate_history_integrity.py
python scripts/validate_fortune_expansion_readiness.py
```

## Validator Contract

Governance validators must:

- use only the Python standard library
- avoid external network calls
- avoid reading or printing secrets
- avoid scraping, analysis execution, SEC download, or data mutation
- print `PASS`, `WARN`, or `FAIL` rows
- exit `1` only for hard failures

## Scope Rules

Governance-only work must not run:

```bash
python scrape_x.py
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
python scripts/check_fortune2025_x_direct_profiles.py
python scripts/collect_fortune2025_10k_reports.py --download
```

Help and compile checks are allowed when they do not mutate files or call external services.

## Failure Handling

Fix hard failures before commit. Warnings may remain only if they are documented in the final report and do not violate the requested scope.
