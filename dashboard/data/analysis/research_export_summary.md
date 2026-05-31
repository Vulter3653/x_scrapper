# Research Export Summary

## Joined Dataset

- Wendy's: 967 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2765 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7541.00 | 874.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.83 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4038.32 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.40 | 1281.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 756 | 0.273 | 12741.03 | 1358.50 | 0.398 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8119.58 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 886 | 0.320 | 6544.14 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14922.67 | 2287.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3223.00 | 3223.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4567.56 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2959.22 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 534 | 0.193 | 2241.39 | 552.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5557.35 | 494.00 | 874.00 | 16185.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3989.17 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1725 | 0.624 | 9335.80 | 976.00 | 4194.00 | 11694.00 | 1000933.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13041.64 | 2287.50 | 5209.00 | 39594.80 | 98909.00 | 0.323 |
| Self-enhancing humor | 985 | 0.356 | 3277.08 | 672.00 | 2608.00 | 8293.80 | 103121.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997263 | 0.987158 | 2765 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958045 | -0.958045 | 2765 |
| text_length | word_count | 0.939205 | 0.948405 | 2765 |
| sentiment_negative | sentiment_positive | -0.928435 | -0.928435 | 2765 |
| retweets | total_engagement | 0.916673 | 0.914429 | 2765 |
| likes | retweets | 0.888575 | 0.880766 | 2765 |
| replies | total_engagement | 0.547459 | 0.796189 | 2765 |
| likes | replies | 0.538799 | 0.773910 | 2765 |
| quotes | total_engagement | 0.530993 | 0.388328 | 2765 |
| likes | quotes | 0.505163 | 0.369205 | 2765 |
| total_engagement | is_viral | 0.502895 | 0.349979 | 2765 |
| likes | is_viral | 0.496996 | 0.334828 | 2765 |
| retweets | quotes | 0.473001 | 0.373413 | 2765 |
| replies | is_viral | 0.466955 | 0.311103 | 2765 |
| replies | quotes | 0.460082 | 0.439467 | 2765 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
