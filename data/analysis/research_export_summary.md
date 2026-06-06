# Research Export Summary

## Joined Dataset

- Wendy's: 970 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2768 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7537.80 | 873.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4733.00 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4075.32 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3801.80 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 757 | 0.273 | 12724.47 | 1354.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8142.82 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 887 | 0.320 | 6536.41 | 722.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14919.83 | 2283.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3219.00 | 3219.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.156 | 4574.84 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2960.72 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 535 | 0.193 | 2239.42 | 553.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5557.94 | 495.00 | 873.00 | 16177.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4018.33 | 1693.00 | 4407.75 | 13767.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1727 | 0.624 | 9326.04 | 974.00 | 4180.00 | 11681.60 | 1000612.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13038.93 | 2283.00 | 5208.00 | 39580.10 | 98909.00 | 0.323 |
| Self-enhancing humor | 986 | 0.356 | 3278.18 | 674.00 | 2630.75 | 8280.00 | 103047.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997264 | 0.987155 | 2768 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958088 | -0.958088 | 2768 |
| text_length | word_count | 0.939328 | 0.948358 | 2768 |
| sentiment_negative | sentiment_positive | -0.928507 | -0.928507 | 2768 |
| retweets | total_engagement | 0.916627 | 0.914234 | 2768 |
| likes | retweets | 0.888583 | 0.880688 | 2768 |
| replies | total_engagement | 0.547672 | 0.796420 | 2768 |
| likes | replies | 0.538694 | 0.773836 | 2768 |
| quotes | total_engagement | 0.533016 | 0.469266 | 2768 |
| likes | quotes | 0.507151 | 0.451195 | 2768 |
| total_engagement | is_viral | 0.503000 | 0.349785 | 2768 |
| likes | is_viral | 0.496965 | 0.334718 | 2768 |
| retweets | quotes | 0.473504 | 0.412604 | 2768 |
| replies | quotes | 0.472680 | 0.550780 | 2768 |
| replies | is_viral | 0.466977 | 0.311002 | 2768 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
