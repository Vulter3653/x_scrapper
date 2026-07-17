# Research Export Summary

## Joined Dataset

- Wendy's: 989 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2791 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7561.60 | 867.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.08 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4113.32 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.80 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 763 | 0.273 | 12595.81 | 1340.00 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8134.67 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.321 | 6472.27 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14939.33 | 2273.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3204.00 | 3204.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 438 | 0.157 | 4520.93 | 838.50 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.72 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2228.04 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5564.29 | 493.00 | 867.00 | 16219.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.79 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1741 | 0.624 | 9235.19 | 961.00 | 4105.00 | 11542.00 | 994623.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13054.57 | 2273.50 | 5204.25 | 39440.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 995 | 0.357 | 3251.10 | 658.00 | 2592.00 | 8132.20 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987207 | 2791 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958436 | -0.958436 | 2791 |
| text_length | word_count | 0.939673 | 0.948594 | 2791 |
| sentiment_negative | sentiment_positive | -0.929078 | -0.929078 | 2791 |
| retweets | total_engagement | 0.916412 | 0.913398 | 2791 |
| likes | retweets | 0.888386 | 0.880075 | 2791 |
| replies | total_engagement | 0.546481 | 0.796049 | 2791 |
| likes | replies | 0.537156 | 0.772993 | 2791 |
| quotes | total_engagement | 0.536302 | 0.624775 | 2791 |
| likes | quotes | 0.510610 | 0.609662 | 2791 |
| total_engagement | is_viral | 0.502929 | 0.350065 | 2791 |
| likes | is_viral | 0.496717 | 0.335169 | 2791 |
| replies | quotes | 0.478252 | 0.718273 | 2791 |
| retweets | quotes | 0.474892 | 0.511794 | 2791 |
| replies | is_viral | 0.468515 | 0.311850 | 2791 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
