# Fortune Top 100 X Account Verification Protocol

Last updated: 2026-06-12

## Purpose

This protocol defines the Fortune Top 100 X account verification gate. It is account verification only. It does not authorize X scraping, Fortune 500 collection, SEC downloading, dashboard claims, or financial-text analysis.

## Scope

The master file is `config/fortune2025_x_account_verification_master.csv`. It is initialized from the Fortune 2025 Top 100 source and the existing direct-profile candidate index. Candidate handles are not official-account claims. Official fields must remain empty until manual evidence supports them.

## Controlled Account Status Taxonomy

Allowed `official_x_account_status` values:

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

Do not use uncontrolled labels such as verified, valid, confirmed, or approved as account-status values.

## Evidence Source Type Taxonomy

Allowed `evidence_source_type` values:

```text
not_reviewed
corporate_footer
newsroom
investor_relations
press_page
contact_page
social_directory
x_profile_backlink
cross_platform_official
manual_search_only
not_found
inaccessible
```

`not_reviewed` is the default for initialized rows where no reviewer has assessed evidence yet. Search-result-only evidence is insufficient for `official` or `brand_official` status. `manual_search_only` is valid only after a reviewer has actually performed a search and found only search-result-level evidence; it is a review clue, not proof of account officiality.

## Evidence Strength Taxonomy

Allowed `evidence_strength` values:

```text
level_1
level_2
level_3
level_4
level_5
level_6
level_7
level_8
none
```

Level 1 should represent strongest direct corporate evidence, such as a corporate site footer or official social directory linking to the X account. Level 8 is weak/manual-search-only style evidence and is never scrape-eligible. `not_reviewed` must use `evidence_strength=none` and `confidence=blocked`.

## Confidence Taxonomy

Allowed `confidence` values:

```text
high
medium
low
blocked
```

## Default Unreviewed State

Initialized rows that have not been reviewed must use:

```text
official_x_account_status=unknown
evidence_source_type=not_reviewed
evidence_strength=none
confidence=blocked
scrape_eligible=false
manual_verification_required=false
```

Do not use `manual_search_only` for default initialization. It means a reviewer actually searched and found only search-result-level evidence.

## Human Manual Review Layer

Original Codex-reviewed fields are preserved as preliminary/reference evidence only. They remain useful for audit history, but they are no longer the final source of account eligibility.

The human-review overlay added to the master CSV is the final authority for future collection eligibility:

- `human_candidate_is_actual_official`
- `human_actual_x_url_1`
- `human_actual_x_url_2`
- `human_review_status`
- `human_review_batch`
- `final_manual_x_url_primary`
- `final_manual_x_url_secondary`
- `final_manual_account_status`
- `final_manual_scrape_eligible`

For the current batch, ranks 1-20 are `human_reviewed` and ranks 21-100 remain `pending_human_review`. `final_manual_scrape_eligible` is the only field that should be used for any future collection eligibility decision. Existing `scrape_eligible` must not be treated as final after this human-review policy change.

## Scrape Eligibility Gate

`scrape_eligible=true` is allowed only when all conditions hold:

- `official_x_account_status` is `official` or `brand_official`
- `confidence` is `high` or `medium`
- `evidence_source_url` is not empty
- `official_x_url` is not empty
- `evidence_source_type` is neither `not_reviewed` nor `manual_search_only`
- `evidence_strength` is not `none`, `level_6`, `level_7`, or `level_8`

Rows with `unknown`, `ambiguous`, `subsidiary_only`, `no_account_found`, `inaccessible`, or `do_not_scrape` must not be scrape eligible. `confidence=low` and `confidence=blocked` must not be scrape eligible. Level 8 evidence must never be scrape eligible. Manual-search-only evidence must never be scrape eligible.

## Manual Verification Rule

`manual_verification_required=true` for:

```text
official
brand_official
subsidiary_only
ambiguous
do_not_scrape
```

`manual_verification_required=false` for:

```text
unknown
no_account_found
inaccessible
```

This field indicates whether a human decision has been made and must be preserved for audit, not whether future work is needed.

## Required Review Evidence

Original Codex-reviewed fields remain preliminary/reference evidence; the human-review overlay determines the final account result and future eligibility. For `official` and `brand_official`, reviewers must record:

- `official_x_handle`
- `official_x_url`
- `evidence_source_url`
- `evidence_source_type`
- `evidence_strength`
- `confidence`
- `reviewer`
- `review_date`
- `notes` when `brand_official`

## Expansion Boundary

Fortune 500 expansion is blocked until Top 100 verification is complete and validated. Direct X profile availability and search results are not enough for expansion.

## Claim Boundaries

- X post coverage is not a complete historical archive; it is limited to posts captured under the current scraper protocol.
- Humor and sentiment labels are model-generated unless manual audit evidence exists.
- Dashboard analytics are descriptive only and authorize no causal claims.
- SEC 10-K fetch failure does not block account verification, but financial linkage analysis must be flagged unavailable where SEC fetch failed.
- SEC manifest/audit files are attempted-collection and failure-logging artifacts, not evidence of usable 10-K corpus availability.

## Validation

Run:

```bash
python scripts/validate_fortune_expansion_readiness.py
```

The validator must not scrape X, call external networks, download SEC filings, modify `data/`, or modify `dashboard/data/`.
