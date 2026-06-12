# Agent Rules

Last updated: 2026-06-12
Repository: `Vulter3653/x_scrapper`

This file is the operating contract for AI-assisted work in this repository. It applies to Codex, Gemini, and any future automation agent.

## 1. Agent Roles

- Codex = Writer by default. Codex may implement repository changes when explicitly tasked and must run validation before commit.
- Gemini = Auditor by default. Gemini may review, critique, propose plans, and verify claims, but must not edit files while Codex is the active writer.
- A human maintainer remains the Owner and final authority for scope, claim boundaries, credentials, and publication decisions.

## 2. File Lock Table

Only one non-human writer may modify files at a time.

| Agent | Mode | Allowed Files | Forbidden Files | Current Task | Status |
| --- | --- | --- | --- | --- | --- |
| Codex | Writer | task-scoped files | `data/`, `dashboard/data/`, secrets, destructive git operations | active implementation | active or standby |
| Gemini | Auditor | read-only review outputs | all repository files unless explicitly authorized | governance audit / gap review | auditor |
| Human | Owner | all files | secrets must not be exposed | approval and final decision | owner |

## 3. One-Writer Rule

Only one agent may write to the repository at a time. Before a write session starts, the active writer must know the intended scope, target branch, and files to be touched. Other agents should act as auditors until the writer finishes, commits, or explicitly hands off.

Gemini must not edit files while Codex is writer. If Gemini is explicitly promoted from Auditor to Writer, Codex must stop writing first and the handoff must identify touched files and validation state.

If concurrent work is unavoidable, it must happen on separate branches with non-overlapping files and a written merge plan. Do not edit `data/`, `dashboard/data/`, workflow files, or config files concurrently without human approval.

## 4. Branch Naming Rule

Use explicit branch names that identify the agent, task, and date:

```text
codex/<task-name>-YYYYMMDD
gemini/<task-name>-YYYYMMDD
```

Do not do risky work directly on `main` unless the user explicitly asks for a small, bounded change and the worktree is clean.

## 5. Forbidden Commands

The following commands are forbidden unless the human maintainer gives explicit, task-specific approval:

```bash
git reset --hard
git clean -fd
rm -rf data
rm -rf dashboard/data
rm -rf config
```

Also forbidden:

- bulk `mv` without a written plan
- deleting uncertain files instead of documenting them as deprecated or archive candidates
- force push without explicit approval
- running new scraping or SEC download while doing governance-only work

## 6. Secret Handling Rules

- Never print, inspect, commit, or summarize X cookies, GitHub tokens, OpenAI keys, Gemini keys, Cloudflare tokens, service account keys, browser cookies, or browser session material.
- Never read environment variables only to display them.
- Treat `X_AUTH_TOKEN`, `X_CT0`, `GH_TOKEN`, `GITHUB_TOKEN`, Cloudflare tokens, cookies, and browser session material as secrets.
- Validation scripts must not read secrets.
- Logs must report only whether a required secret is present or missing, never the value.

## 7. Data and Dashboard Protection

- Do not directly edit `dashboard/data/`.
- Use `python sync_dashboard_data.py` only when dashboard sync is intentionally required, because it mutates `dashboard/data/`.
- Governance-only tasks must not modify `data/` or `dashboard/data/`.
- Do not change current brand paths `data/wendys/`, `data/cocacola/`, or `data/moonpie/` without a migration plan and compatibility checks.
- Do not rewrite research outputs as part of documentation or governance work.

## 8. Fortune Expansion Gate

No Fortune scraping before verification gate. Specifically:

- No Fortune 500 scraping before Top 100 official-account verification protocol is validated.
- Do not scrape Fortune X accounts until the Fortune Top 100 official-account verification protocol is validated.
- Do not expand from Fortune Top 100 to Fortune 500 until Top 100 verification, audit fields, status taxonomy, and manual review rules pass validation.
- Do not treat direct X profile availability as an official account claim.
- Do not retry SEC 10-K body downloads unless a human explicitly starts a collection task.

## 9. Controlled Account Status Taxonomy

Use only these values for official-account review status:

```text
unknown
official
brand_official
subsidiary_only
ambiguous
no_account_found
inaccessible
do_not_scrape
```

Uncontrolled words such as `verified`, `valid`, `confirmed`, and `approved` must not be used as account-status values. If they appear in prose, they are informal language only and must map to one of the controlled statuses above before being stored in a status field.

| Status | Meaning |
| --- | --- |
| `unknown` | Not reviewed or insufficient evidence. |
| `official` | Evidence-backed official parent/corporate account. |
| `brand_official` | Evidence-backed official brand/product account, not necessarily parent corporate account. |
| `subsidiary_only` | Only a subsidiary/business-unit account has evidence. |
| `ambiguous` | Evidence conflicts or multiple plausible accounts exist. |
| `no_account_found` | Review found no suitable official X account. |
| `inaccessible` | X or source pages could not be accessed enough for a decision. |
| `do_not_scrape` | Account should be excluded from scraping even if discoverable. |

Scrape-eligible statuses are only `official` and explicitly allowed `brand_official`. Rows with `unknown`, `ambiguous`, `subsidiary_only`, `no_account_found`, `inaccessible`, or `do_not_scrape` must not enter scrape queues or expansion-ready files.

## 10. Validation Before Commit

Run the validators relevant to the change. Governance-layer work must run:

```bash
python scripts/validate_repository_state.py
python scripts/validate_agent_rules.py
python scripts/validate_data_claim_boundaries.py
python scripts/validate_history_integrity.py
python scripts/validate_fortune_expansion_readiness.py
```

Also run `git diff --check` and Python compile checks for touched scripts.

## 11. Final Report Format

Governance work must close with scope, files created, files updated, validation results, risks remaining, and next recommended step.

```markdown
# Governance Layer Report

## 1. Final Verdict
PASS / FAIL

## 2. Scope
What changed / what did not change

## 3. Files Created
Table

## 4. Files Updated
Table

## 5. Validation Results
Table

## 6. Gemini Audit Gaps Addressed
Table

## 7. Hard-Fail / Warning Rules
Table

## 8. Remaining Risks
Table

## 9. Next Recommended Step
Fortune Top 100 official X account verification protocol
```
