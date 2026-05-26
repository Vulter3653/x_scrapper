# Current Results Status

This document records the current paper-facing status of the X Brand Communication dataset and analysis outputs. It is intended to support the next writing step, not to evaluate the dashboard UI.

## 1. Data and Analysis Coverage

| Brand | Posts | LDA Documents | Selected LDA Topics | NPMI Coherence | Sentiment Results | HSQ Humor Results |
|---|---:|---:|---:|---:|---:|---:|
| Wendy's | 959 | 867 | 6 | 0.2055 | 959 | 959 |
| Coca-Cola | 866 | 832 | 4 | 0.3535 | 866 | 866 |
| MoonPie | 932 | 861 | 9 | 0.1116 | 932 | 932 |
| Total | 2,757 | 2,560 | - | - | 2,757 | 2,757 |

Notes:
- LDA uses a candidate topic range from 2 to 9 topics and selects the highest NPMI coherence result.
- LDA document counts can be lower than post counts because empty, duplicate, or unusable text can be excluded during topic modeling.
- Sentiment and HSQ humor classification are model-generated zero-shot labels and require sampling audit before strong reliability claims.

## 2. Sentiment Label Distribution

| Brand | Positive | Neutral | Negative | Dominant Sentiment |
|---|---:|---:|---:|---|
| Wendy's | 398 | 45 | 516 | Negative |
| Coca-Cola | 548 | 20 | 298 | Positive |
| MoonPie | 379 | 72 | 481 | Negative |
| Total | 1,325 | 137 | 1,295 | Positive |

Paper-facing interpretation:
- Coca-Cola currently shows the clearest positive sentiment skew.
- Wendy's and MoonPie are classified more often as negative than positive, but this should be interpreted as model-generated tone classification, not as consumer emotion.
- Neutral labels are relatively rare across all three brands, suggesting the zero-shot classifier tends to separate posts into positive or negative categories.

## 3. HSQ Humor Type Distribution

| Brand | Affiliative Humor | Self-enhancing Humor | Aggressive Humor | Self-defeating Humor | Dominant Humor Type |
|---|---:|---:|---:|---:|---|
| Wendy's | 22 | 901 | 20 | 16 | Self-enhancing Humor |
| Coca-Cola | 22 | 836 | 6 | 2 | Self-enhancing Humor |
| MoonPie | 25 | 868 | 20 | 19 | Self-enhancing Humor |
| Total | 69 | 2,605 | 46 | 37 | Self-enhancing Humor |

Paper-facing interpretation:
- All three brands are currently dominated by Self-enhancing Humor under the zero-shot HSQ classifier.
- This concentration is analytically useful but also a reliability warning: the classifier may be over-assigning broad positive self-presentation to many posts.
- Sampling audit should oversample non-dominant labels and low-confidence cases to test whether Aggressive, Affiliative, and Self-defeating categories are under-detected.

## 4. Immediate Table and Figure Readiness

| Paper Output | Status | Source |
|---|---|---|
| Table 1. Descriptive Statistics by Brand | Partially ready | `data/*/posts.json`, dashboard derived metrics |
| Table 2. Distribution of Humor Type by Brand | Ready for draft | `data/*/hsq_humor_classification.json` |
| Table 3. Distribution of Sentiment by Brand | Ready for draft | `data/*/zero_shot_sentiment.json` |
| Figure 1. HSQ Humor Type 2x2 Matrix | Ready conceptually | `docs/paper/RESULTS_SECTION_STRUCTURE.md` |
| Table 4. Humor x Sentiment x Engagement Summary | Needs export | joined posts + sentiment + humor labels |
| Table 5. Engagement Robustness by Humor Type | Needs export | joined posts + humor labels + engagement metrics |
| Table 6. Sampling Audit Results | Not ready | manual audit required |

## 5. Next Writing Step

The next substantive paper task is to generate a joined analysis table that merges:

```text
posts.json
zero_shot_sentiment.json
hsq_humor_classification.json
lda_topics.json topic assignments
```

Required derived columns:

```text
brand
post_id
created_at
text
likes
replies
retweets
quotes
total_engagement
log_total_engagement
sentiment_label
sentiment_score
humor_type
humor_score
topic_id
is_viral
```

Once this table exists, Tables 4 and 5 can be produced directly and the Results section can move from template-based writing to data-backed writing.

## 6. Generated Research Export Files

The following paper-facing export files are now generated under `data/analysis/`:

| File | Purpose |
|---|---|
| `joined_posts.csv` / `joined_posts.json` | Post-level joined dataset with brand, source account, engagement, sentiment, HSQ humor, topic proxy, and viral flag |
| `table4_humor_sentiment_engagement.csv` / `.json` | Humor x Sentiment x Engagement Summary for Results Table 4 |
| `table5_engagement_robustness_by_humor.csv` / `.json` | Engagement Robustness by Humor Type for Results Table 5 |
| `correlation_coefficients.csv` / `.json` | Pearson and Spearman correlation coefficients for engagement, text, sentiment, humor, topic proxy, and viral indicators |
| `sampling_audit_candidates.csv` / `.json` | Low-confidence, viral, and non-dominant humor cases for manual sampling audit |
| `research_export_summary.md` | Human-readable summary of joined data, Table 4, Table 5, and strongest correlations |

Each joined post row includes `brand`, `brand_slug`, and `source_account`, so the company associated with every collected tweet can be identified at the tweet level.

Topic assignment note: the current joined table uses a descriptive topic proxy inferred from saved LDA top terms because the existing LDA output does not persist a full document-topic matrix for every post.
