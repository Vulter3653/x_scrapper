# Change Control

Last updated: 2026-06-12
Repository: `Vulter3653/x_scrapper`

This file defines how changes should be proposed, validated, committed, and audited.

## 1. Change Classes

| Class | Examples | Required validation |
| --- | --- | --- |
| Governance/docs | Agent rules, claim boundaries, validation protocols | Governance validators and history integrity check. |
| Code refactor | Moving implementation into `src/`, wrappers, path constants | Compile checks, repository validator, command compatibility checks. |
| Dashboard | `dashboard/*.js`, `dashboard/*.html`, styles | `node --check`, dashboard reference validation, visual review when feasible. |
| Data generation | Scraping, analysis, export, sync | Explicit user scope, no secret output, data diff review. |
| Fortune expansion | Account verification, SEC workflow, Fortune 500 panel | Gatekeeping protocol and dedicated human approval. |

## 2. Pre-Change Checklist

- Confirm the worktree is clean or identify unrelated user changes.
- Confirm whether the task is governance-only, code-only, dashboard-only, or data-generating.
- Identify forbidden paths for the task. Governance-only tasks must not modify `data/` or `dashboard/data/`.
- Confirm whether network calls, scraping, or SEC downloads are out of scope.

## 3. Commit Rules

- Keep one coherent task per commit.
- Use concise commit messages such as `chore: add governance rules and claim boundary checks`.
- Do not mix generated data refreshes with governance or refactor commits.
- Do not commit secrets, browser cookies, local caches, or `__pycache__` files.

## 4. Review Rules

The reviewer or auditor should check:

- stated scope matches changed files
- claim boundaries are preserved
- validators were run
- no forbidden command or data mutation occurred
- README/history/troubleshooting notes match reality

## 5. Rollback Rules

Do not use `git reset --hard` or destructive cleanup by default. Prefer a new revert commit or targeted edit after human approval.
