# Integrated Temporal Distribution Memo

## Scope

This memo summarizes temporal diagnostics for the integrated collected corpus after H1 presence-only classification.

It is descriptive only. It is not regression evidence, causal evidence, or H1 support evidence.

## Coverage

- Total posts: 68,039
- Parsed date rows: 68,039
- Missing date rows: 0
- Date range: 2009-11-26 to 2026-06-18
- Year rows: 14
- Year-month rows: 133
- Hour rows: 24

## Descriptive Findings

- Most active year: 2022
- Most active year-month: 2026-05
- Most active hour: 15 UTC
- Highest humor_rate_t50 hour: 3 UTC
- Lowest humor_rate_t50 hour: 11 UTC

Hours are interpreted in the timestamp basis available in the source data, generally UTC for X `created_at` strings. Local-time or business-hour interpretations should be conservative.

## Boundary

Temporal diagnostics describe posting distribution and provisional humor presence distribution only. They do not establish H1 support and do not run fixed effects, controls, robust SE, H2/H3, type classification, or aggressive detection.
