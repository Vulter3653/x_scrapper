# Fortune 500 Humor Text Analysis Design

Last updated: 2026-06-12

This is a design document only. It prepares the next Fortune Top 100 official X account verification stage and the later Fortune 500 extension. It does not authorize new X scraping, SEC re-downloads, or automated official-account claims.

## 1. Research Purpose

The research goal is to measure how large firms use humor in social media communication and whether firm-level humor patterns relate to engagement, sentiment, topic themes, and firm characteristics. The primary unit of text analysis remains the social media post, while the primary inferential unit should be the aggregated firm or firm-period score.

## 2. Fortune 2025 Firm Universe

The firm universe starts from `fortune2025_itemListElement_rows.csv`. Current active automation is limited to the Fortune 2025 top 100 support files. A Fortune 500 expansion should be gated by account verification, schema validation, and audit review, not by direct scraping.

## 3. X Official Account Verification Logic

Official account verification must combine direct X profile checks with manual evidence from official company websites, press pages, verified social links, or investor/brand pages. Direct `https://x.com/{normalized_firm_name}` availability is only a weak candidate signal. Each row should preserve `unknown`, `ambiguous`, or `no_corporate_account` when evidence is insufficient.

Verification fields should include candidate handle, reviewed handle, profile URL, source URLs, reviewer notes, confidence, and manual review status. No candidate should be treated as official until review evidence is recorded.

## 4. Post-Level Data Schema

Post-level rows should include firm id, Fortune year/rank, verified X handle, post id, URL, created timestamp, raw text, normalized text, engagement fields, language, media/link indicators, scrape metadata, and collection/audit status.

Text analysis should treat each social media post as one observation. Dictionary baseline features, open-vocabulary features, topic model assignments, transformer labels, classification confidence, and `NULL` or uncertain classes should be retained together.

## 5. Humor Classification Schema

The current HSQ categories can remain the baseline taxonomy: affiliative, self-enhancing, aggressive, self-defeating, and non-humorous brand message. Future labels should allow dictionary features, weak/self-supervised labels, and open-vocabulary model outputs. LDA, Word2Vec, Doc2Vec, KNN, and transformer approaches are design options for later model comparison rather than required implementations in this refactor.

Every classification row should preserve model name, hypothesis or prompt version, candidate labels, top label, top score, full score distribution, confidence threshold, and uncertain/null assignment.

## 6. Firm-Level Humor Aggregation Rule

Post-level labels should be aggregated to firm-level and firm-period measures. Recommended measures include humor post share, label shares, dominant humor type, mean confidence, uncertain share, engagement-weighted humor share, and robustness variants using alternative confidence thresholds.

Individual post classifications are useful for audit and examples, but aggregate firm-level scores should be treated as more reliable than single-post labels.

## 7. NAICS/SIC Industry Enrichment Rule

Industry enrichment should be a separate audited join. Use documented NAICS/SIC sources and retain match status, source, confidence, and reviewer notes. Ambiguous conglomerates should keep multiple candidate codes or a primary/secondary code rule.

The panel should support firm-level, firm-year, and firm-quarter joins so industry controls can be added without changing post-level data.

## 8. Scatter Plot Design

Initial plots should compare firm-level humor intensity against engagement, sentiment balance, uncertainty share, and industry group. Scatter plots should support firm labels, industry color, Fortune rank size or facet, and confidence filters.

A mechanism table should accompany visual results with columns for theoretical theme, why the mechanism should matter, how it appears in text, expected observable variable, and robustness check.

## 9. Confidence / Audit / Manual Review Rule

The pipeline should keep classification confidence and explicit uncertain classes. Manual review should prioritize low-confidence posts, high-engagement posts, rare humor categories, and firms whose aggregate score is sensitive to threshold choices.

Dictionary-based relevant text extraction is acceptable for identifying candidate humor cues or assurance/CSR-like themes. Topic modeling results should be grouped into higher-level theoretical themes before paper-facing interpretation. Alternative thresholds and robustness checks should be documented before expansion claims are made.

## 10. Known Limitations

X profile availability does not prove official ownership. X scraping is platform-fragile and credential-sensitive. SEC coverage is incomplete for private firms and should not be forced into every Fortune row. Zero-shot labels are noisy at post level, especially for sarcasm, short replies, and context-dependent brand banter. Brand-level aggregates reduce but do not remove these risks.

No Fortune 500 collection, new scraping, or SEC re-download is included in this design step.
