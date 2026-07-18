# Research Export Summary

## Joined Dataset

- Wendy's: 990 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2792 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7561.40 | 867.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.08 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4113.58 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.80 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 764 | 0.274 | 12579.21 | 1339.50 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8134.48 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.321 | 6472.19 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14939.42 | 2274.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3204.00 | 3204.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 438 | 0.157 | 4520.74 | 838.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.72 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.97 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5564.24 | 493.00 | 867.00 | 16219.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4048.00 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1742 | 0.624 | 9229.79 | 961.00 | 4102.50 | 11536.00 | 994571.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13054.64 | 2274.50 | 5204.25 | 39439.40 | 99388.00 | 0.323 |
| Self-enhancing humor | 995 | 0.356 | 3250.97 | 658.00 | 2592.00 | 8133.60 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987206 | 2792 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958444 | -0.958444 | 2792 |
| text_length | word_count | 0.939692 | 0.948614 | 2792 |
| sentiment_negative | sentiment_positive | -0.929107 | -0.929107 | 2792 |
| retweets | total_engagement | 0.916417 | 0.913416 | 2792 |
| likes | retweets | 0.888393 | 0.880097 | 2792 |
| replies | total_engagement | 0.546481 | 0.796125 | 2792 |
| likes | replies | 0.537153 | 0.773079 | 2792 |
| quotes | total_engagement | 0.536313 | 0.624678 | 2792 |
| likes | quotes | 0.510622 | 0.609564 | 2792 |
| total_engagement | is_viral | 0.502936 | 0.350024 | 2792 |
| likes | is_viral | 0.496723 | 0.335129 | 2792 |
| replies | quotes | 0.478249 | 0.718216 | 2792 |
| retweets | quotes | 0.474899 | 0.511707 | 2792 |
| replies | is_viral | 0.468528 | 0.311815 | 2792 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
