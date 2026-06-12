#!/usr/bin/env python3
"""Validate repository structure after the conservative refactor.

This script performs static checks only. It does not scrape X, call SEC, run
model inference, or mutate data outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

REQUIRED_PATHS = [
    REPO_ROOT / "scrape_x.py",
    REPO_ROOT / "analyze_posts.py",
    REPO_ROOT / "export_research_outputs.py",
    REPO_ROOT / "sync_dashboard_data.py",
    REPO_ROOT / "scripts" / "collect_fortune2025_10k_reports.py",
    SRC_ROOT / "x_scrapper" / "paths.py",
    SRC_ROOT / "x_scrapper" / "collection" / "x_scraper.py",
    SRC_ROOT / "x_scrapper" / "analysis" / "pipeline.py",
    SRC_ROOT / "x_scrapper" / "exports" / "research_outputs.py",
    SRC_ROOT / "x_scrapper" / "dashboard" / "sync_data.py",
    SRC_ROOT / "x_scrapper" / "fortune" / "x_account_verification.py",
    SRC_ROOT / "x_scrapper" / "fortune" / "tenk_collector.py",
    SRC_ROOT / "x_scrapper" / "fortune" / "industry_codes.py",
    SRC_ROOT / "x_scrapper" / "fortune" / "humor_panel.py",
    REPO_ROOT / "config" / "taxonomies" / "humor_types.json",
    REPO_ROOT / "config" / "taxonomies" / "sentiment_labels.json",
    REPO_ROOT / "config" / "taxonomies" / "lda_stopwords.txt",
    REPO_ROOT / "config" / "fortune2025" / "fortune2025_top100_x_account_index.csv",
    REPO_ROOT / "config" / "schemas" / "fortune2025_x_account_verification_master.schema.json",
    REPO_ROOT / "config" / "schemas" / "fortune2025_humor_firm_panel.schema.json",
    REPO_ROOT / "docs" / "architecture" / "repository_structure.md",
    REPO_ROOT / "docs" / "methodology" / "fortune500_humor_text_analysis_design.md",
]

PRESERVED_DATA_DIRS = [
    REPO_ROOT / "data" / "wendys",
    REPO_ROOT / "data" / "cocacola",
    REPO_ROOT / "data" / "moonpie",
    REPO_ROOT / "dashboard" / "data",
]

WRAPPERS = [
    REPO_ROOT / "scrape_x.py",
    REPO_ROOT / "analyze_posts.py",
    REPO_ROOT / "export_research_outputs.py",
    REPO_ROOT / "sync_dashboard_data.py",
    REPO_ROOT / "scripts" / "collect_fortune2025_10k_reports.py",
]

SCHEMAS = [
    REPO_ROOT / "config" / "schemas" / "fortune2025_x_account_verification_master.schema.json",
    REPO_ROOT / "config" / "schemas" / "fortune2025_humor_firm_panel.schema.json",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_PATHS + PRESERVED_DATA_DIRS if not path.exists()]
    if missing:
        fail("missing required paths: " + ", ".join(missing))

    for wrapper in WRAPPERS:
        text = wrapper.read_text(encoding="utf-8")
        if "src" not in text or "x_scrapper" not in text:
            fail(f"wrapper does not import src package: {wrapper.relative_to(REPO_ROOT)}")

    for schema in SCHEMAS:
        payload = json.loads(schema.read_text(encoding="utf-8"))
        if payload.get("type") != "object":
            fail(f"schema is not an object schema: {schema.relative_to(REPO_ROOT)}")

    app_js = (REPO_ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    review_js = (REPO_ROOT / "dashboard" / "research-review.js").read_text(encoding="utf-8")
    for needle in ["data/wendys", "data/cocacola", "data/moonpie"]:
        if needle not in app_js:
            fail(f"dashboard app missing fetch reference: {needle}")
    for needle in ["data/analysis/sampling_audit_candidates.json", "data/analysis/joined_posts.json"]:
        if needle not in review_js:
            fail(f"review dashboard missing fetch reference: {needle}")

    print("PASS: repository structure, wrappers, schemas, preserved data dirs, and dashboard references validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
