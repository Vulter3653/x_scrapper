# Research Export Summary

## Joined Dataset

- Wendy's: 963 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2761 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7542.20 | 876.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.83 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4036.37 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3803.40 | 1284.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 754 | 0.273 | 12780.68 | 1368.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8122.00 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 885 | 0.321 | 6556.97 | 729.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14927.58 | 2288.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3228.00 | 3228.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4570.33 | 859.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2959.28 | 1057.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 533 | 0.193 | 2245.76 | 555.00 | 0.549 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5557.71 | 493.00 | 876.00 | 16187.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3987.83 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1722 | 0.624 | 9357.54 | 981.50 | 4200.00 | 11768.70 | 1002666.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13046.21 | 2288.50 | 5210.25 | 39630.50 | 98909.00 | 0.323 |
| Self-enhancing humor | 984 | 0.356 | 3281.72 | 674.50 | 2615.00 | 8308.30 | 103206.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997265 | 0.987162 | 2761 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.957994 | -0.957994 | 2761 |
| text_length | word_count | 0.939155 | 0.948331 | 2761 |
| sentiment_negative | sentiment_positive | -0.928334 | -0.928334 | 2761 |
| retweets | total_engagement | 0.916714 | 0.914410 | 2761 |
| likes | retweets | 0.888630 | 0.880763 | 2761 |
| replies | total_engagement | 0.547493 | 0.796160 | 2761 |
| likes | replies | 0.538848 | 0.773910 | 2761 |
| quotes | total_engagement | 0.531051 | 0.388889 | 2761 |
| likes | quotes | 0.505255 | 0.369795 | 2761 |
| total_engagement | is_viral | 0.502810 | 0.350165 | 2761 |
| likes | is_viral | 0.496925 | 0.335012 | 2761 |
| retweets | quotes | 0.473024 | 0.373906 | 2761 |
| replies | is_viral | 0.466925 | 0.311253 | 2761 |
| replies | quotes | 0.460089 | 0.439428 | 2761 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
