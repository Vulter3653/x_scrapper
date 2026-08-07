# Research Export Summary

## Joined Dataset

- Wendy's: 1005 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2808 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.40 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.05 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.80 | 1274.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12488.34 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8128.57 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 901 | 0.321 | 6421.99 | 715.00 | 0.490 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14930.42 | 2270.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3199.00 | 3199.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 441 | 0.157 | 4485.41 | 805.00 | 0.403 | 0.639 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2985.89 | 1056.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.193 | 2235.23 | 553.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.35 | 490.00 | 862.00 | 16207.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.21 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1753 | 0.624 | 9163.95 | 950.00 | 4012.00 | 11449.00 | 991273.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13046.57 | 2270.50 | 5203.00 | 39380.60 | 99388.00 | 0.323 |
| Self-enhancing humor | 1000 | 0.356 | 3241.07 | 657.50 | 2584.00 | 8187.50 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987223 | 2808 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958662 | -0.958662 | 2808 |
| text_length | word_count | 0.939707 | 0.948578 | 2808 |
| sentiment_negative | sentiment_positive | -0.929501 | -0.929501 | 2808 |
| retweets | total_engagement | 0.916357 | 0.913297 | 2808 |
| likes | retweets | 0.888335 | 0.880033 | 2808 |
| replies | total_engagement | 0.545514 | 0.795768 | 2808 |
| quotes | total_engagement | 0.536096 | 0.624379 | 2808 |
| likes | replies | 0.536068 | 0.772598 | 2808 |
| likes | quotes | 0.510314 | 0.609269 | 2808 |
| total_engagement | is_viral | 0.502503 | 0.350674 | 2808 |
| likes | is_viral | 0.496373 | 0.335909 | 2808 |
| replies | quotes | 0.477721 | 0.718099 | 2808 |
| retweets | quotes | 0.474917 | 0.511528 | 2808 |
| replies | is_viral | 0.468744 | 0.312748 | 2808 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
