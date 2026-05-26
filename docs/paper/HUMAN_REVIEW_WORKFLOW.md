# Human Review Workflow for Classification and Topic Improvement

This document defines the human-in-the-loop workflow for improving zero-shot classification and LDA topic quality.

## 1. Open Review Dashboard

Use the deployed dashboard section `Research Review Workspace` or open the local dashboard. The review workspace supports:

- Sampling Audit editing
- Human sentiment label selection
- Human HSQ humor label selection
- Human notes for ambiguous cases
- LDA stopword editing
- LDA topic review CSV export
- Humor label configuration export

Because the dashboard is static on Cloudflare Pages, edits are kept in the browser until downloaded. Downloaded files should be committed back into the repository.

## 2. Sampling Audit

Start with `data/analysis/sampling_audit_candidates.csv`. The dashboard loads the same data from `dashboard/data/analysis/sampling_audit_candidates.json`.

Fill these fields during review:

```text
human_sentiment_label
human_humor_type
human_notes
```

Prioritize rows marked as:

```text
low_confidence
viral
non_dominant_humor
```

Recommended first pass: 100-150 posts.

## 3. Zero-shot Label Improvement

Current labels are controlled by:

```text
config/sentiment_labels.json
config/humor_labels.json
```

The HSQ humor configuration includes `Non-humorous brand message` so plain promotional or informational posts are not forced into one of the four humor categories.

After human review, update the config files if repeated error patterns appear. Examples:

- Add or rename labels only when a recurring conceptual category is missing.
- Refine `hypothesis_template` if the classifier systematically overuses one label.
- Add label notes when coders repeatedly disagree about a category.

## 4. LDA Stopword Improvement

Additional stopwords are controlled by:

```text
config/lda_stopwords.txt
```

Add terms only when they reduce topic interpretability. Avoid removing domain-specific words that help identify campaigns, products, or brand voice.

The dashboard can export `lda_stopwords_reviewed.txt`. Copy reviewed terms back to `config/lda_stopwords.txt` before rerunning LDA.

## 5. LDA Topic Review

The dashboard exports `lda_topic_review.csv` with these human fields:

```text
human_topic_label
remove_terms
merge_with_topic
split_needed
notes
```

Use this file to decide whether new stopwords are needed or whether a topic count range should be adjusted.

## 6. Reanalysis

After updating config files, rerun:

```bash
python analyze_posts.py --task all
python export_research_outputs.py
python sync_dashboard_data.py
```

For all brands, run `analyze_posts.py` with `TARGET_USER` set to each account or trigger the scheduled GitHub Action.

## 7. Reporting

Report human review outcomes using:

- Agreement rate for Sentiment
- Agreement rate for Humor Type
- Low-confidence error rate
- Ambiguity share
- Main reasons for relabeling

The results should be written as a classification reliability check, not as proof that the model labels are objectively correct.
