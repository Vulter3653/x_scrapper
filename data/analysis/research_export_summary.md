# Research Export Summary

## Joined Dataset

- Wendy's: 970 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2768 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7538.20 | 874.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4733.00 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4077.89 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3801.60 | 1281.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 757 | 0.273 | 12722.99 | 1354.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8142.22 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 887 | 0.320 | 6535.36 | 722.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14918.67 | 2283.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3217.00 | 3217.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.156 | 4574.36 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2960.56 | 1057.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 535 | 0.193 | 2239.30 | 553.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5558.06 | 495.00 | 874.00 | 16178.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4020.33 | 1693.00 | 4407.75 | 13767.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1727 | 0.624 | 9324.82 | 974.00 | 4180.00 | 11681.20 | 1000243.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13037.79 | 2283.00 | 5207.50 | 39575.20 | 98909.00 | 0.323 |
| Self-enhancing humor | 986 | 0.356 | 3277.90 | 674.00 | 2630.75 | 8279.00 | 103033.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997265 | 0.987158 | 2768 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958088 | -0.958088 | 2768 |
| text_length | word_count | 0.939328 | 0.948358 | 2768 |
| sentiment_negative | sentiment_positive | -0.928507 | -0.928507 | 2768 |
| retweets | total_engagement | 0.916624 | 0.914191 | 2768 |
| likes | retweets | 0.888585 | 0.880668 | 2768 |
| replies | total_engagement | 0.547643 | 0.796330 | 2768 |
| likes | replies | 0.538662 | 0.773744 | 2768 |
| quotes | total_engagement | 0.533008 | 0.469244 | 2768 |
| likes | quotes | 0.507135 | 0.451183 | 2768 |
| total_engagement | is_viral | 0.503014 | 0.349776 | 2768 |
| likes | is_viral | 0.496973 | 0.334713 | 2768 |
| retweets | quotes | 0.473512 | 0.412426 | 2768 |
| replies | quotes | 0.472634 | 0.550759 | 2768 |
| replies | is_viral | 0.466973 | 0.310980 | 2768 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
