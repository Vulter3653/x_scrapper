# Research Export Summary

## Joined Dataset

- Wendy's: 962 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2760 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7529.00 | 873.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4729.92 | 466.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4028.89 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.00 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 753 | 0.273 | 12723.96 | 1370.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8097.95 | 2031.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 885 | 0.321 | 6539.35 | 718.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14164.25 | 2274.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3222.00 | 3222.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 433 | 0.157 | 4550.58 | 855.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.007 | 2957.17 | 1049.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 533 | 0.193 | 2234.98 | 548.00 | 0.549 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5553.18 | 492.00 | 873.00 | 16150.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 3981.62 | 1693.00 | 4407.75 | 13347.20 | 15820.00 | 0.379 |
| Non-humorous brand message | 1721 | 0.624 | 9320.51 | 967.00 | 4202.00 | 11720.00 | 1002746.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 12391.50 | 2274.00 | 5208.75 | 33262.60 | 98909.00 | 0.323 |
| Self-enhancing humor | 984 | 0.357 | 3267.15 | 673.00 | 2615.00 | 8177.20 | 102458.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997485 | 0.987782 | 2760 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.957985 | -0.957985 | 2760 |
| text_length | word_count | 0.939145 | 0.948314 | 2760 |
| sentiment_negative | sentiment_positive | -0.928305 | -0.928305 | 2760 |
| retweets | total_engagement | 0.916572 | 0.913902 | 2760 |
| likes | retweets | 0.888622 | 0.880779 | 2760 |
| quotes | total_engagement | 0.610317 | 0.310767 | 2760 |
| likes | quotes | 0.593890 | 0.304287 | 2760 |
| replies | total_engagement | 0.545106 | 0.794172 | 2760 |
| retweets | quotes | 0.540562 | 0.294610 | 2760 |
| likes | replies | 0.538859 | 0.773915 | 2760 |
| total_engagement | is_viral | 0.501273 | 0.349972 | 2760 |
| likes | is_viral | 0.496973 | 0.335538 | 2760 |
| replies | is_viral | 0.464716 | 0.307276 | 2760 |
| retweets | is_viral | 0.437035 | 0.349229 | 2760 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
