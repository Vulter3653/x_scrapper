# Research Export Summary

## Joined Dataset

- Wendy's: 981 posts
- MoonPie: 933 posts
- Coca-Cola: 866 posts
- Total: 2780 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7566.60 | 870.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.58 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4097.53 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3800.80 | 1279.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12671.86 | 1359.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8139.53 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6493.87 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14946.83 | 2278.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 436 | 0.157 | 4544.22 | 848.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.11 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 537 | 0.193 | 2233.51 | 548.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5566.12 | 494.00 | 870.00 | 16230.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4035.71 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.624 | 9276.85 | 968.00 | 4123.75 | 11610.60 | 996711.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13061.07 | 2278.00 | 5204.50 | 39492.60 | 99388.00 | 0.323 |
| Self-enhancing humor | 991 | 0.356 | 3263.82 | 659.00 | 2610.50 | 8233.00 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997271 | 0.987187 | 2780 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958275 | -0.958275 | 2780 |
| text_length | word_count | 0.939403 | 0.948420 | 2780 |
| sentiment_negative | sentiment_positive | -0.928801 | -0.928801 | 2780 |
| retweets | total_engagement | 0.916389 | 0.913414 | 2780 |
| likes | retweets | 0.888379 | 0.880007 | 2780 |
| replies | total_engagement | 0.547546 | 0.796147 | 2780 |
| likes | replies | 0.538454 | 0.773143 | 2780 |
| quotes | total_engagement | 0.536511 | 0.624558 | 2780 |
| likes | quotes | 0.510901 | 0.609424 | 2780 |
| total_engagement | is_viral | 0.502810 | 0.350621 | 2780 |
| likes | is_viral | 0.496632 | 0.335694 | 2780 |
| replies | quotes | 0.477676 | 0.718980 | 2780 |
| retweets | quotes | 0.474896 | 0.511629 | 2780 |
| replies | is_viral | 0.467901 | 0.312205 | 2780 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
