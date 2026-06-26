# Research Export Summary

## Joined Dataset

- Wendy's: 980 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2778 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7567.60 | 871.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.67 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4095.00 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.00 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12676.33 | 1358.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8141.94 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6497.16 | 720.50 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14949.08 | 2278.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3210.00 | 3210.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 435 | 0.157 | 4555.74 | 855.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.33 | 1060.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2237.23 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5566.47 | 494.00 | 871.00 | 16233.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4033.96 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.624 | 9280.62 | 969.50 | 4126.25 | 11610.60 | 997838.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13063.36 | 2278.50 | 5205.75 | 39507.30 | 99388.00 | 0.323 |
| Self-enhancing humor | 989 | 0.356 | 3270.65 | 664.00 | 2613.00 | 8250.00 | 102821.00 | 0.483 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997271 | 0.987187 | 2778 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958225 | -0.958225 | 2778 |
| text_length | word_count | 0.939396 | 0.948406 | 2778 |
| sentiment_negative | sentiment_positive | -0.928751 | -0.928751 | 2778 |
| retweets | total_engagement | 0.916414 | 0.913449 | 2778 |
| likes | retweets | 0.888402 | 0.880025 | 2778 |
| replies | total_engagement | 0.547630 | 0.796119 | 2778 |
| likes | replies | 0.538548 | 0.773156 | 2778 |
| quotes | total_engagement | 0.536530 | 0.624558 | 2778 |
| likes | quotes | 0.510936 | 0.609457 | 2778 |
| total_engagement | is_viral | 0.503415 | 0.349261 | 2778 |
| likes | is_viral | 0.497175 | 0.334271 | 2778 |
| replies | quotes | 0.477771 | 0.719053 | 2778 |
| retweets | quotes | 0.474920 | 0.511843 | 2778 |
| replies | is_viral | 0.467133 | 0.310627 | 2778 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
