# Research Export Summary

## Joined Dataset

- Wendy's: 978 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2776 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7569.20 | 873.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.92 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4091.79 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3803.40 | 1281.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12682.97 | 1357.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8146.51 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 891 | 0.321 | 6508.82 | 722.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14955.17 | 2282.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3213.00 | 3213.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 434 | 0.156 | 4567.62 | 855.50 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.44 | 1059.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2238.03 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5567.12 | 495.00 | 873.00 | 16237.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4031.71 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1733 | 0.624 | 9291.34 | 972.00 | 4137.00 | 11620.40 | 999351.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13068.79 | 2282.00 | 5206.50 | 39553.50 | 99388.00 | 0.323 |
| Self-enhancing humor | 988 | 0.356 | 3275.01 | 667.00 | 2618.75 | 8266.20 | 102950.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997269 | 0.987190 | 2776 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958190 | -0.958190 | 2776 |
| text_length | word_count | 0.939382 | 0.948417 | 2776 |
| sentiment_negative | sentiment_positive | -0.928701 | -0.928701 | 2776 |
| retweets | total_engagement | 0.916429 | 0.913468 | 2776 |
| likes | retweets | 0.888399 | 0.880056 | 2776 |
| replies | total_engagement | 0.547880 | 0.796449 | 2776 |
| likes | replies | 0.538805 | 0.773532 | 2776 |
| quotes | total_engagement | 0.536473 | 0.624738 | 2776 |
| likes | quotes | 0.510902 | 0.609696 | 2776 |
| total_engagement | is_viral | 0.503360 | 0.349356 | 2776 |
| likes | is_viral | 0.497144 | 0.334352 | 2776 |
| replies | quotes | 0.477946 | 0.718938 | 2776 |
| retweets | quotes | 0.474797 | 0.511945 | 2776 |
| replies | is_viral | 0.467154 | 0.310728 | 2776 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
