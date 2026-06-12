# Fortune Expansion Gatekeeping

Last updated: 2026-06-12

## Purpose

This protocol blocks premature Fortune scraping and claim inflation. It must pass before Fortune Top 100 official-account verification can move into collection, and it must pass again before any Fortune 500 expansion.

## Gate 1: Top 100 Verification Protocol

Before scraping any Fortune X accounts, the project must have:

- account status taxonomy documented and validated
- evidence source fields for official-account claims
- manual review rules for ambiguous, inaccessible, subsidiary, and do-not-scrape accounts
- no-scrape exclusions respected
- audit file format defined
- claim boundaries documented

## Gate 2: Top 100 Review Completion

Before expanding beyond Top 100, the Top 100 review must record for each firm:

- status from the controlled taxonomy
- reviewed handle or explicit missing/ambiguous status
- evidence source for `official`, `brand_official`, or `subsidiary_only`
- reviewer notes or audit trail
- `do_not_scrape` rows excluded from collection

## Gate 3: Fortune 500 Expansion

No Fortune 500 scraping before Top 100 official-account verification protocol is validated. Fortune 500 scraping may start only after Gate 1 and Gate 2 are validated and a human explicitly approves expansion. Direct profile checks are not enough.

## Controlled Account Status Taxonomy

Allowed values:

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

Uncontrolled words such as `verified`, `valid`, `confirmed`, and `approved` must not be stored as account-status values. If they are used informally in prose, they must map to one of the controlled statuses before entering CSV, JSON, queue, or schema fields.

Scrape-eligible statuses are only `official` and explicitly allowed `brand_official`. Files with `unknown`, `ambiguous`, `subsidiary_only`, `no_account_found`, `inaccessible`, or `do_not_scrape` must not be treated as scrape-ready or expansion-ready.

## SEC Boundary

SEC 10-K collection is independent from X account verification. Do not retry SEC body download during account verification unless the user starts a dedicated SEC collection task.

## Readiness Result

A readiness validator may return warnings while current files are still pre-verification. It should fail only when governance files, taxonomy, or no-scrape rules are missing, or when account-status fields or scrape-ready files violate the controlled taxonomy.
