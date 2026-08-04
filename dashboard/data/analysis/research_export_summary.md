# Research Export Summary

## Joined Dataset

- Wendy's: 1002 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2804 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7557.00 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.42 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.60 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12489.71 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8129.02 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 899 | 0.321 | 6436.48 | 719.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14931.75 | 2270.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3200.00 | 3200.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 440 | 0.157 | 4495.40 | 817.50 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.00 | 1056.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 540 | 0.193 | 2223.09 | 551.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.53 | 490.00 | 862.00 | 16209.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.46 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1751 | 0.624 | 9175.15 | 952.00 | 4021.50 | 11482.00 | 991640.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13047.79 | 2270.50 | 5203.25 | 39388.30 | 99388.00 | 0.323 |
| Self-enhancing humor | 998 | 0.356 | 3238.67 | 657.50 | 2561.50 | 8063.90 | 102281.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987223 | 2804 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958595 | -0.958595 | 2804 |
| text_length | word_count | 0.939764 | 0.948663 | 2804 |
| sentiment_negative | sentiment_positive | -0.929411 | -0.929411 | 2804 |
| retweets | total_engagement | 0.916373 | 0.913237 | 2804 |
| likes | retweets | 0.888349 | 0.879957 | 2804 |
| replies | total_engagement | 0.546006 | 0.795993 | 2804 |
| likes | replies | 0.536610 | 0.772905 | 2804 |
| quotes | total_engagement | 0.536083 | 0.624114 | 2804 |
| likes | quotes | 0.510314 | 0.609038 | 2804 |
| total_engagement | is_viral | 0.502457 | 0.350900 | 2804 |
| likes | is_viral | 0.496352 | 0.336142 | 2804 |
| replies | quotes | 0.477948 | 0.717896 | 2804 |
| retweets | quotes | 0.474890 | 0.511146 | 2804 |
| replies | is_viral | 0.468467 | 0.312888 | 2804 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
