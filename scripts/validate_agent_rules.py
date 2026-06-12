#!/usr/bin/env python3
"""Validate governance agent rules.

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


def require(path: str, needles: list[str], check: str, severity: str = "FAIL") -> None:
    text = read(path)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        row(severity, check, f"{path} missing: " + ", ".join(missing))
    else:
        row("PASS", check, f"{path} contains {len(needles)} required items")


TAXONOMY = [
    "unknown",
    "official",
    "brand_official",
    "subsidiary_only",
    "ambiguous",
    "no_account_found",
    "inaccessible",
    "do_not_scrape",
]


def main() -> int:
    path = REPO_ROOT / "AGENT_RULES.md"
    if not path.exists():
        row("FAIL", "required file", "missing AGENT_RULES.md")
        return 1
    row("PASS", "required file", "found AGENT_RULES.md")

    require("AGENT_RULES.md", ["Codex = Writer", "Gemini = Auditor", "Gemini must not edit files while Codex is writer"], "role separation")
    require("AGENT_RULES.md", ["Only one agent may write", "Only one non-human writer may modify files at a time"], "one-writer rule")
    require("AGENT_RULES.md", ["codex/<task-name>-YYYYMMDD", "gemini/<task-name>-YYYYMMDD"], "branch naming")
    require("AGENT_RULES.md", ["git reset --hard", "git clean -fd", "rm -rf data", "rm -rf dashboard/data", "rm -rf config", "bulk `mv` without a written plan"], "forbidden commands")
    require("AGENT_RULES.md", ["Never print, inspect, commit, or summarize", "X cookies", "GitHub tokens", "OpenAI keys", "Gemini keys", "Cloudflare tokens", "service account keys", "Validation scripts must not read secrets"], "secret handling")
    require("AGENT_RULES.md", ["`data/`", "`dashboard/data/`", "Do not directly edit `dashboard/data/`", "Use `python sync_dashboard_data.py` only when dashboard sync is intentionally required"], "data and dashboard protection")
    require("AGENT_RULES.md", ["No Fortune 500 scraping before Top 100 official-account verification protocol is validated", "Do not scrape Fortune X accounts until the Fortune Top 100 official-account verification protocol is validated"], "fortune scraping gate")
    require("AGENT_RULES.md", TAXONOMY, "controlled account-status taxonomy")
    require("AGENT_RULES.md", ["File Lock Table", "Agent", "Mode", "Allowed Files", "Forbidden Files", "Current Task", "Status"], "file lock table")
    require("AGENT_RULES.md", ["scope", "files created", "files updated", "validation results", "risks remaining", "next recommended step"], "final report format")

    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
