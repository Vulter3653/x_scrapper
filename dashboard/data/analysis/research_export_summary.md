# Research Export Summary

## Joined Dataset

- Wendy's: 967 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2765 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7541.40 | 876.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.75 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4038.63 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.60 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 756 | 0.273 | 12743.53 | 1359.00 | 0.398 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8120.42 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 886 | 0.320 | 6546.60 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14924.83 | 2288.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3225.00 | 3225.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4568.67 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2959.17 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 534 | 0.193 | 2241.53 | 552.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5557.41 | 493.00 | 876.00 | 16185.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3989.46 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1725 | 0.624 | 9338.20 | 976.00 | 4194.00 | 11706.60 | 1001768.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13043.64 | 2288.00 | 5209.50 | 39612.30 | 98909.00 | 0.323 |
| Self-enhancing humor | 985 | 0.356 | 3277.64 | 672.00 | 2608.00 | 8298.80 | 103152.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997264 | 0.987157 | 2765 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958045 | -0.958045 | 2765 |
| text_length | word_count | 0.939205 | 0.948405 | 2765 |
| sentiment_negative | sentiment_positive | -0.928435 | -0.928435 | 2765 |
| retweets | total_engagement | 0.916693 | 0.914474 | 2765 |
| likes | retweets | 0.888603 | 0.880801 | 2765 |
| replies | total_engagement | 0.547475 | 0.796385 | 2765 |
| likes | replies | 0.538822 | 0.774130 | 2765 |
| quotes | total_engagement | 0.531024 | 0.388376 | 2765 |
| likes | quotes | 0.505209 | 0.369255 | 2765 |
| total_engagement | is_viral | 0.502864 | 0.349981 | 2765 |
| likes | is_viral | 0.496969 | 0.334842 | 2765 |
| retweets | quotes | 0.473020 | 0.373446 | 2765 |
| replies | is_viral | 0.466951 | 0.311111 | 2765 |
| replies | quotes | 0.460089 | 0.439384 | 2765 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
