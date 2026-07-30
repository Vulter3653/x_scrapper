# Research Export Summary

## Joined Dataset

- Wendy's: 997 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2799 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7558.20 | 864.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.67 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4110.42 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.20 | 1275.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 768 | 0.274 | 12508.67 | 1309.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8130.54 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 897 | 0.320 | 6451.93 | 719.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14933.58 | 2272.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3202.00 | 3202.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4506.32 | 830.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.39 | 1057.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.14 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.00 | 491.00 | 864.00 | 16212.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.38 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1748 | 0.625 | 9192.72 | 957.50 | 4046.25 | 11500.00 | 992371.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13049.50 | 2272.00 | 5203.75 | 39400.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3245.44 | 658.00 | 2584.00 | 8100.50 | 102346.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987217 | 2799 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958520 | -0.958520 | 2799 |
| text_length | word_count | 0.939635 | 0.948542 | 2799 |
| sentiment_negative | sentiment_positive | -0.929291 | -0.929291 | 2799 |
| retweets | total_engagement | 0.916400 | 0.913201 | 2799 |
| likes | retweets | 0.888370 | 0.879885 | 2799 |
| replies | total_engagement | 0.546172 | 0.796112 | 2799 |
| likes | replies | 0.536792 | 0.773047 | 2799 |
| quotes | total_engagement | 0.536115 | 0.624349 | 2799 |
| likes | quotes | 0.510359 | 0.609263 | 2799 |
| total_engagement | is_viral | 0.503050 | 0.349694 | 2799 |
| likes | is_viral | 0.496811 | 0.334842 | 2799 |
| replies | quotes | 0.478008 | 0.717913 | 2799 |
| retweets | quotes | 0.474901 | 0.511428 | 2799 |
| replies | is_viral | 0.468647 | 0.311558 | 2799 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
