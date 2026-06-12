# Research Export Summary

## Joined Dataset

- Wendy's: 976 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2774 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7572.60 | 873.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.83 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4092.42 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3804.80 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.274 | 12686.38 | 1360.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8148.08 | 2051.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 889 | 0.320 | 6523.34 | 722.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14958.92 | 2283.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3216.00 | 3216.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 434 | 0.156 | 4568.71 | 855.50 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.78 | 1060.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2238.57 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5568.06 | 495.00 | 873.00 | 16245.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4032.50 | 1692.00 | 4470.75 | 13763.90 | 15942.00 | 0.379 |
| Non-humorous brand message | 1731 | 0.624 | 9303.58 | 972.00 | 4151.50 | 11640.00 | 999745.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13072.21 | 2283.50 | 5207.25 | 39559.80 | 99411.00 | 0.323 |
| Self-enhancing humor | 988 | 0.356 | 3275.79 | 667.50 | 2618.75 | 8267.60 | 102980.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997269 | 0.987187 | 2774 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958173 | -0.958173 | 2774 |
| text_length | word_count | 0.939330 | 0.948370 | 2774 |
| sentiment_negative | sentiment_positive | -0.928658 | -0.928658 | 2774 |
| retweets | total_engagement | 0.916456 | 0.913575 | 2774 |
| likes | retweets | 0.888433 | 0.880191 | 2774 |
| replies | total_engagement | 0.547832 | 0.796554 | 2774 |
| likes | replies | 0.538757 | 0.773655 | 2774 |
| quotes | total_engagement | 0.536450 | 0.624848 | 2774 |
| likes | quotes | 0.510885 | 0.609768 | 2774 |
| total_engagement | is_viral | 0.503323 | 0.349455 | 2774 |
| likes | is_viral | 0.497110 | 0.334447 | 2774 |
| replies | quotes | 0.477930 | 0.719226 | 2774 |
| retweets | quotes | 0.474793 | 0.512116 | 2774 |
| replies | is_viral | 0.467118 | 0.310786 | 2774 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
