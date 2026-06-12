#!/usr/bin/env python3
"""Validate data claim boundary documentation.

Static/local only: no secrets, network, scraping, SEC calls, or data mutation.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FAILURES = 0
WARNINGS = 0


def row(status: str, check: str, detail: str) -> None:
    global FAILURES, WARNINGS
    print(f"{status}: {check} - {detail}")
    if status == "FAIL":
        FAILURES += 1
    elif status == "WARN":
        WARNINGS += 1


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def require(path: str, needles: list[str], check: str) -> None:
    text = read(path).lower()
    missing = [needle for needle in needles if needle.lower() not in text]
    if missing:
        row("FAIL", check, f"{path} missing concepts: " + ", ".join(missing))
    else:
        row("PASS", check, f"{path} contains {len(needles)} required concepts")


TAXONOMY = ["unknown", "official", "brand_official", "subsidiary_only", "ambiguous", "no_account_found", "inaccessible", "do_not_scrape"]


def main() -> int:
    path = REPO_ROOT / "DATA_CLAIM_BOUNDARIES.md"
    if not path.exists():
        row("FAIL", "required file", "missing DATA_CLAIM_BOUNDARIES.md")
        return 1
    row("PASS", "required file", "found DATA_CLAIM_BOUNDARIES.md")

    require("DATA_CLAIM_BOUNDARIES.md", ["current scraper protocol", "posts captured under the current scraper protocol", "retrievable timeline posts"], "current scraper protocol wording")
    require("DATA_CLAIM_BOUNDARIES.md", ["not a complete archive", "Do not claim complete historical X coverage", "all posts"], "no complete historical X coverage boundary")
    require("DATA_CLAIM_BOUNDARIES.md", ["manual evidence source URL", "No Fortune official-account claim", "evidence source"], "Fortune official account evidence requirement")
    require("DATA_CLAIM_BOUNDARIES.md", ["No NAICS completeness claim", "source and confidence", "NAICS completeness requires source and confidence fields"], "NAICS source/confidence requirement")
    require("DATA_CLAIM_BOUNDARIES.md", ["HSQ / zero-shot humor labels are model-generated", "manual audit evidence"], "HSQ / zero-shot limitation")
    require("DATA_CLAIM_BOUNDARIES.md", ["do not authorize causal claims", "Do not claim causal effects"], "no causal claim boundary")
    require("DATA_CLAIM_BOUNDARIES.md", ["## SEC 10-K Collection Failure Boundary", "sec_source_fetch_failed", "not evidence of usable 10-K corpus", "no financial-text analysis"], "SEC 10-K collection failure boundary")
    require("DATA_CLAIM_BOUNDARIES.md", ["body collection remains failed or incomplete", "Existing SEC manifest/audit files do not imply a usable 10-K corpus"], "SEC corpus availability boundary")
    require("DATA_CLAIM_BOUNDARIES.md", TAXONOMY, "controlled account-status taxonomy")

    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
