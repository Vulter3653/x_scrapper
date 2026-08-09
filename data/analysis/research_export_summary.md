# Research Export Summary

## Joined Dataset

- Wendy's: 1007 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2810 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.40 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4108.89 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.60 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12487.07 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8127.35 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 903 | 0.321 | 6408.43 | 715.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14929.83 | 2269.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3199.00 | 3199.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 441 | 0.157 | 4484.82 | 804.00 | 0.403 | 0.639 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2985.89 | 1055.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.193 | 2235.65 | 553.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.35 | 491.00 | 862.00 | 16206.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.04 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1755 | 0.625 | 9153.24 | 950.00 | 4010.00 | 11416.00 | 991078.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13046.07 | 2269.00 | 5203.00 | 39377.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 1000 | 0.356 | 3241.03 | 657.50 | 2584.00 | 8187.90 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987229 | 2810 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958679 | -0.958679 | 2810 |
| text_length | word_count | 0.939706 | 0.948572 | 2810 |
| sentiment_negative | sentiment_positive | -0.929543 | -0.929543 | 2810 |
| retweets | total_engagement | 0.916375 | 0.913202 | 2810 |
| likes | retweets | 0.888355 | 0.879953 | 2810 |
| replies | total_engagement | 0.545302 | 0.795593 | 2810 |
| quotes | total_engagement | 0.536104 | 0.624344 | 2810 |
| likes | replies | 0.535833 | 0.772401 | 2810 |
| likes | quotes | 0.510317 | 0.609240 | 2810 |
| total_engagement | is_viral | 0.502520 | 0.350595 | 2810 |
| likes | is_viral | 0.496387 | 0.335822 | 2810 |
| replies | quotes | 0.477646 | 0.718105 | 2810 |
| retweets | quotes | 0.474933 | 0.511403 | 2810 |
| replies | is_viral | 0.468860 | 0.312677 | 2810 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
