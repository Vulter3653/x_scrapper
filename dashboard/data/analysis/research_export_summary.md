# Research Export Summary

## Joined Dataset

- Wendy's: 993 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2795 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7560.40 | 865.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.92 | 466.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4113.21 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.60 | 1276.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 766 | 0.274 | 12544.54 | 1332.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8132.84 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.320 | 6469.91 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14936.25 | 2271.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3203.00 | 3203.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4509.40 | 833.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.44 | 1057.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.71 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.82 | 492.00 | 865.00 | 16217.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.67 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1744 | 0.624 | 9217.15 | 960.50 | 4095.50 | 11524.00 | 993874.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13051.86 | 2271.00 | 5204.00 | 39418.40 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3247.11 | 658.00 | 2584.00 | 8109.50 | 102798.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987203 | 2795 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958486 | -0.958486 | 2795 |
| text_length | word_count | 0.939738 | 0.948688 | 2795 |
| sentiment_negative | sentiment_positive | -0.929192 | -0.929192 | 2795 |
| retweets | total_engagement | 0.916416 | 0.913235 | 2795 |
| likes | retweets | 0.888395 | 0.879885 | 2795 |
| replies | total_engagement | 0.546349 | 0.796299 | 2795 |
| likes | replies | 0.537003 | 0.773216 | 2795 |
| quotes | total_engagement | 0.536288 | 0.624529 | 2795 |
| likes | quotes | 0.510579 | 0.609435 | 2795 |
| total_engagement | is_viral | 0.502979 | 0.349886 | 2795 |
| likes | is_viral | 0.496756 | 0.335010 | 2795 |
| replies | quotes | 0.478267 | 0.717948 | 2795 |
| retweets | quotes | 0.474915 | 0.511485 | 2795 |
| replies | is_viral | 0.468581 | 0.311704 | 2795 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
