# Research Export Summary

## Joined Dataset

- Wendy's: 968 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2766 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7536.00 | 869.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.08 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4036.00 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3801.60 | 1280.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 757 | 0.274 | 12712.51 | 1354.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8114.00 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 886 | 0.320 | 6533.13 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14916.42 | 2282.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3218.00 | 3218.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4561.97 | 858.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2958.89 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 534 | 0.193 | 2239.53 | 551.50 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5555.35 | 491.00 | 869.00 | 16175.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3987.17 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1726 | 0.624 | 9319.34 | 974.00 | 4187.00 | 11646.50 | 998008.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13035.93 | 2282.50 | 5207.75 | 39553.50 | 98909.00 | 0.323 |
| Self-enhancing humor | 985 | 0.356 | 3273.61 | 672.00 | 2608.00 | 8281.00 | 102982.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997259 | 0.987145 | 2766 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958054 | -0.958054 | 2766 |
| text_length | word_count | 0.939206 | 0.948412 | 2766 |
| sentiment_negative | sentiment_positive | -0.928464 | -0.928464 | 2766 |
| retweets | total_engagement | 0.916624 | 0.914288 | 2766 |
| likes | retweets | 0.888503 | 0.880612 | 2766 |
| replies | total_engagement | 0.547410 | 0.795990 | 2766 |
| likes | replies | 0.538734 | 0.773621 | 2766 |
| quotes | total_engagement | 0.531026 | 0.387970 | 2766 |
| likes | quotes | 0.505132 | 0.368762 | 2766 |
| total_engagement | is_viral | 0.502971 | 0.349933 | 2766 |
| likes | is_viral | 0.497049 | 0.334801 | 2766 |
| retweets | quotes | 0.473144 | 0.372822 | 2766 |
| replies | is_viral | 0.466942 | 0.311062 | 2766 |
| replies | quotes | 0.460061 | 0.439539 | 2766 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
