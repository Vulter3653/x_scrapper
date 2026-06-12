#!/usr/bin/env python3
"""Validate governance history references.

Static/local only: no secrets, network, scraping, SEC calls, or data mutation.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


def text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    required = ["README.md", "PROJECT_HISTORY.md", "TROUBLESHOOTING_AND_DEBUGGING_LOG.md"]
    for path in required:
        if not (REPO_ROOT / path).exists():
            row("FAIL", "core history file", f"missing {path}")
        else:
            row("PASS", "core history file", f"found {path}")
    if FAILURES:
        return 1

    readme = text("README.md")
    if "## Governance and Validation" in readme and "python scripts/validate_agent_rules.py" in readme:
        row("PASS", "README governance section", "validation commands documented")
    else:
        row("FAIL", "README governance section", "missing Governance and Validation section or validator commands")

    if "File Lock Table" in readme and "Codex" in readme and "Gemini" in readme:
        row("PASS", "README file lock table", "full table is visible")
    elif "AGENT_RULES.md" in readme:
        row("WARN", "README file lock table", "README links to AGENT_RULES.md but does not show full File Lock Table")
    else:
        row("WARN", "README file lock table", "README does not show table or link clearly")

    history = text("PROJECT_HISTORY.md")
    today = datetime.now(timezone.utc).date().isoformat()
    if "Added governance layer" in history or today in history:
        row("PASS", "PROJECT_HISTORY governance entry", "current governance work is recorded or date placeholder exists")
    else:
        row("WARN", "PROJECT_HISTORY governance entry", "current uncommitted governance change is not yet recorded")

    trouble = text("TROUBLESHOOTING_AND_DEBUGGING_LOG.md")
    if "Governance validation was added without data mutation" in trouble or "no issue" in trouble.lower():
        row("PASS", "troubleshooting governance note", "governance note or no-issue note found")
    else:
        row("WARN", "troubleshooting governance note", "no governance/no-issue note found; acceptable if no incident occurred")

    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
