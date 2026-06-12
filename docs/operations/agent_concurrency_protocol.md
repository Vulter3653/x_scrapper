# Agent Concurrency Protocol

Last updated: 2026-06-12

## Purpose

This protocol prevents Codex, Gemini, and future agents from overwriting each other or mixing audit work with write work.

## Roles

| Agent | Default role | Write permission |
| --- | --- | --- |
| Codex | Writer | May write when assigned a concrete task. |
| Gemini | Auditor | Should audit, review, and propose unless explicitly assigned as writer. |

## One-Writer Rule

Only one writer may modify repository files at a time. The writer owns the current branch until commit, handoff, or explicit cancellation.

## Branch Protocol

Use branch names that encode ownership and task type:

```text
codex/<short-task>
gemini-audit/<short-task>
docs/<short-topic>
validation/<short-topic>
fortune-gate/<short-topic>
```

## Handoff Protocol

A handoff must include:

- current branch and latest commit
- files changed
- validators run
- unresolved warnings
- explicit no-touch paths

## Conflict Protocol

If another agent or human changed a touched file, stop and inspect the diff. Work with the new content rather than reverting it. Ask for direction only if the conflict makes the task impossible.

## No-Touch Defaults

Unless the task explicitly says otherwise, agents must not modify:

- `data/`
- `dashboard/data/`
- secrets or local credential files
- generated caches
- workflow collection triggers
