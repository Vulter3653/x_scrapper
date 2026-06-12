# Data Claim Boundaries

Last updated: 2026-06-12
Repository: `Vulter3653/x_scrapper`

This file defines what the repository may and may not claim from its current artifacts. These boundaries apply to README text, dashboards, papers, commit messages, issue comments, and agent final reports.

## 1. Current Brand Post Data

`data/<brand>/posts.json` is the authoritative source only for posts captured under the current scraper protocol. It records posts observed by the browser/GraphQL capture process for the configured run conditions.

It is not a complete archive of all historical X posts. Do not claim complete historical X coverage or say the dataset contains "all posts." Use "retrievable timeline posts" or "posts captured under the current scraper protocol." X platform behavior, authentication state, scrolling limits, deleted posts, rate limits, and rendering differences can affect capture.

## 2. Analysis Outputs

LDA, zero-shot sentiment, and HSQ humor outputs are model-generated descriptive artifacts. They may support exploratory analysis, review queues, and aggregate summaries.

HSQ / zero-shot humor labels are model-generated unless manual audit evidence exists. Do not claim human-validated humor labels unless a manual audit exists and is linked. A model label alone is not a human-reviewed truth label.

Dashboard outputs are descriptive and do not authorize causal claims. Do not claim causal effects from the descriptive dashboard. Dashboard charts show observed relationships and descriptive summaries only.

## 3. Fortune Official Account Claims

Fortune account officiality requires manual evidence source URL. No Fortune official-account claim is allowed unless evidence source exists. Direct profile availability, normalized-handle matching, or an X page rendering successfully is not enough.

Use the controlled account status taxonomy below for review fields:

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

Uncontrolled words such as `verified`, `valid`, `confirmed`, and `approved` must not be used as account-status values. If they appear in prose, they are informal language only and must map to a controlled status before storage.

| Status | Allowed claim |
| --- | --- |
| `unknown` | No official-account claim. |
| `official` | Official account claim allowed only with evidence source. |
| `brand_official` | Brand account claim allowed only with evidence source; do not imply parent corporate account. |
| `subsidiary_only` | Subsidiary account claim only; do not generalize to parent firm. |
| `ambiguous` | No official-account claim. |
| `no_account_found` | Claim only that review did not find a suitable account. |
| `inaccessible` | No account-status claim beyond access limitation. |
| `do_not_scrape` | Exclude from scraping regardless of candidate availability. |

## 4. Fortune Expansion Boundary

No Fortune 500 scraping before Top 100 verification protocol is validated. The Top 100 protocol must validate account evidence fields, status taxonomy, manual review rules, audit trail, and no-scrape exclusions before expansion.

No Fortune 500 collection, panel creation, or dashboard claim should be described as complete until a dedicated expansion task runs and passes validation.

## 5. Industry Code Boundary

No NAICS completeness claim unless source and confidence exist. NAICS completeness requires source and confidence fields. Industry enrichment must preserve source, match method, confidence, and ambiguous/missing status.

If a firm has multiple business segments, NAICS/SIC assignment must be treated as an audited modeling choice, not a self-evident fact.

## 6. SEC 10-K Boundary

SEC 10-K body collection remains failed or incomplete unless audited success status exists. SEC 10-K body download remains failed unless status is success or an equivalent audited success status.

Existing SEC manifest/audit files do not imply a usable 10-K corpus. Manifest rows with `sec_source_fetch_failed`, `submissions_fetch_failed`, `download_failed`, `not_attempted`, or empty local report paths are not downloaded body text.

Do not claim SEC 10-K text was collected unless the row has a success/found status and a successful download status or verified local body path.

## SEC 10-K Collection Failure Boundary

Current SEC 10-K report body collection is not complete. Existing 10-K manifest/audit rows do not imply successful report-body download. Rows marked `sec_source_fetch_failed` must be treated as missing report body data.

No financial-text analysis, 10-K based AI disclosure analysis, or fiscal correlation claim is allowed until report download status becomes `success` or an equivalent audited success status.

SEC manifest/audit files are evidence of attempted collection and failure logging, not evidence of usable 10-K corpus availability.

## 7. Publication Boundary

Any paper, dashboard note, or final report must distinguish among:

- captured posts
- model-derived labels
- manually audited labels
- official-account evidence
- descriptive associations
- causal claims, which are not supported by this dashboard alone
