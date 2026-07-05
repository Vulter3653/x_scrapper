# Research Export Summary

## Joined Dataset

- Wendy's: 981 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2781 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7566.00 | 870.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.50 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4098.16 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3800.40 | 1279.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12670.03 | 1358.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8138.80 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6492.67 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14945.25 | 2277.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 436 | 0.157 | 4543.40 | 848.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.11 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 538 | 0.193 | 2232.48 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5565.88 | 494.00 | 870.00 | 16228.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4036.12 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.624 | 9275.40 | 968.00 | 4121.25 | 11610.60 | 996376.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13059.71 | 2277.50 | 5204.50 | 39480.70 | 99388.00 | 0.323 |
| Self-enhancing humor | 992 | 0.357 | 3261.86 | 661.50 | 2609.25 | 8209.50 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997271 | 0.987189 | 2781 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958301 | -0.958301 | 2781 |
| text_length | word_count | 0.939504 | 0.948466 | 2781 |
| sentiment_negative | sentiment_positive | -0.928822 | -0.928822 | 2781 |
| retweets | total_engagement | 0.916395 | 0.913421 | 2781 |
| likes | retweets | 0.888387 | 0.880031 | 2781 |
| replies | total_engagement | 0.547422 | 0.796009 | 2781 |
| likes | replies | 0.538309 | 0.772985 | 2781 |
| quotes | total_engagement | 0.536487 | 0.624473 | 2781 |
| likes | quotes | 0.510867 | 0.609360 | 2781 |
| total_engagement | is_viral | 0.502819 | 0.350583 | 2781 |
| likes | is_viral | 0.496636 | 0.335651 | 2781 |
| replies | quotes | 0.477705 | 0.718629 | 2781 |
| retweets | quotes | 0.474898 | 0.511483 | 2781 |
| replies | is_viral | 0.467966 | 0.312198 | 2781 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
