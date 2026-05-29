# Research Export Summary

## Joined Dataset

- Wendy's: 966 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2764 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7541.40 | 876.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4730.75 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4037.89 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3803.00 | 1284.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 755 | 0.273 | 12762.21 | 1365.00 | 0.398 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8121.48 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 886 | 0.321 | 6548.43 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14926.75 | 2288.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3228.00 | 3228.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4569.64 | 859.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2959.22 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 534 | 0.193 | 2241.52 | 552.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5557.41 | 493.00 | 876.00 | 16185.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3988.96 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1724 | 0.624 | 9345.40 | 976.50 | 4196.00 | 11733.80 | 1002313.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13045.50 | 2288.50 | 5210.25 | 39623.50 | 98909.00 | 0.323 |
| Self-enhancing humor | 985 | 0.356 | 3278.06 | 672.00 | 2608.00 | 8299.60 | 103175.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997265 | 0.987163 | 2764 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958037 | -0.958037 | 2764 |
| text_length | word_count | 0.939181 | 0.948378 | 2764 |
| sentiment_negative | sentiment_positive | -0.928406 | -0.928406 | 2764 |
| retweets | total_engagement | 0.916705 | 0.914528 | 2764 |
| likes | retweets | 0.888619 | 0.880856 | 2764 |
| replies | total_engagement | 0.547487 | 0.796531 | 2764 |
| likes | replies | 0.538838 | 0.774343 | 2764 |
| quotes | total_engagement | 0.531044 | 0.388639 | 2764 |
| likes | quotes | 0.505242 | 0.369566 | 2764 |
| total_engagement | is_viral | 0.502838 | 0.350025 | 2764 |
| likes | is_viral | 0.496949 | 0.334885 | 2764 |
| retweets | quotes | 0.473020 | 0.373678 | 2764 |
| replies | is_viral | 0.466944 | 0.311152 | 2764 |
| replies | quotes | 0.460094 | 0.439424 | 2764 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
