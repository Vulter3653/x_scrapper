# Research Export Summary

## Joined Dataset

- Wendy's: 968 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2766 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7539.80 | 871.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.75 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4036.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.20 | 1280.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 757 | 0.274 | 12718.08 | 1354.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8116.89 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 886 | 0.320 | 6537.78 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14918.08 | 2285.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3218.00 | 3218.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4564.48 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2959.06 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 534 | 0.193 | 2240.50 | 551.50 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5556.94 | 494.00 | 871.00 | 16185.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3987.67 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1726 | 0.624 | 9324.31 | 975.00 | 4187.00 | 11657.00 | 999053.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13037.36 | 2285.00 | 5207.75 | 39562.60 | 98909.00 | 0.323 |
| Self-enhancing humor | 985 | 0.356 | 3275.24 | 672.00 | 2608.00 | 8285.80 | 103035.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997260 | 0.987150 | 2766 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958054 | -0.958054 | 2766 |
| text_length | word_count | 0.939206 | 0.948412 | 2766 |
| sentiment_negative | sentiment_positive | -0.928464 | -0.928464 | 2766 |
| retweets | total_engagement | 0.916644 | 0.914296 | 2766 |
| likes | retweets | 0.888530 | 0.880640 | 2766 |
| replies | total_engagement | 0.547440 | 0.796006 | 2766 |
| likes | replies | 0.538768 | 0.773658 | 2766 |
| quotes | total_engagement | 0.531034 | 0.388060 | 2766 |
| likes | quotes | 0.505159 | 0.368898 | 2766 |
| total_engagement | is_viral | 0.502964 | 0.349914 | 2766 |
| likes | is_viral | 0.497050 | 0.334778 | 2766 |
| retweets | quotes | 0.473135 | 0.372817 | 2766 |
| replies | is_viral | 0.466950 | 0.311064 | 2766 |
| replies | quotes | 0.460091 | 0.439559 | 2766 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
