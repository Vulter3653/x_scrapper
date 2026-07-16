# Research Export Summary

## Joined Dataset

- Wendy's: 987 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2789 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7561.80 | 867.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.08 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4113.37 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.00 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 762 | 0.273 | 12613.32 | 1348.50 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8135.37 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 894 | 0.321 | 6479.96 | 725.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14939.83 | 2274.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3204.00 | 3204.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 438 | 0.157 | 4521.36 | 838.50 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.89 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2228.15 | 553.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5564.35 | 493.00 | 867.00 | 16219.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.88 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1739 | 0.624 | 9246.51 | 963.00 | 4114.50 | 11561.60 | 994934.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13055.00 | 2274.50 | 5204.25 | 39442.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 995 | 0.357 | 3251.35 | 658.00 | 2592.00 | 8135.00 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987202 | 2789 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958419 | -0.958419 | 2789 |
| text_length | word_count | 0.939666 | 0.948579 | 2789 |
| sentiment_negative | sentiment_positive | -0.929029 | -0.929029 | 2789 |
| retweets | total_engagement | 0.916416 | 0.913492 | 2789 |
| likes | retweets | 0.888390 | 0.880137 | 2789 |
| replies | total_engagement | 0.546491 | 0.796161 | 2789 |
| likes | replies | 0.537170 | 0.773118 | 2789 |
| quotes | total_engagement | 0.536277 | 0.624847 | 2789 |
| likes | quotes | 0.510589 | 0.609734 | 2789 |
| total_engagement | is_viral | 0.502906 | 0.350162 | 2789 |
| likes | is_viral | 0.496696 | 0.335259 | 2789 |
| replies | quotes | 0.478263 | 0.718377 | 2789 |
| retweets | quotes | 0.474856 | 0.512097 | 2789 |
| replies | is_viral | 0.468488 | 0.311925 | 2789 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
