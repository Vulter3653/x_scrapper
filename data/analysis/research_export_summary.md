# Research Export Summary

## Joined Dataset

- Wendy's: 986 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2788 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7562.00 | 867.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.00 | 466.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4112.26 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.00 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 762 | 0.273 | 12613.79 | 1348.50 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8135.67 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 894 | 0.321 | 6480.26 | 725.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14940.25 | 2275.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 437 | 0.157 | 4531.46 | 843.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.89 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2228.21 | 553.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5564.35 | 492.00 | 867.00 | 16219.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.00 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1739 | 0.624 | 9246.88 | 963.00 | 4114.50 | 11561.60 | 995037.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13055.43 | 2275.50 | 5204.50 | 39444.30 | 99388.00 | 0.323 |
| Self-enhancing humor | 994 | 0.357 | 3254.54 | 658.50 | 2600.00 | 8152.90 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987199 | 2788 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958394 | -0.958394 | 2788 |
| text_length | word_count | 0.939662 | 0.948584 | 2788 |
| sentiment_negative | sentiment_positive | -0.929000 | -0.929000 | 2788 |
| retweets | total_engagement | 0.916414 | 0.913489 | 2788 |
| likes | retweets | 0.888387 | 0.880134 | 2788 |
| replies | total_engagement | 0.546513 | 0.796071 | 2788 |
| likes | replies | 0.537199 | 0.773016 | 2788 |
| quotes | total_engagement | 0.536378 | 0.624714 | 2788 |
| likes | quotes | 0.510699 | 0.609602 | 2788 |
| total_engagement | is_viral | 0.502894 | 0.350212 | 2788 |
| likes | is_viral | 0.496688 | 0.335305 | 2788 |
| replies | quotes | 0.478261 | 0.718328 | 2788 |
| retweets | quotes | 0.474967 | 0.511973 | 2788 |
| replies | is_viral | 0.468485 | 0.311960 | 2788 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
