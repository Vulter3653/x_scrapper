# Research Export Summary

## Joined Dataset

- Wendy's: 959 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2757 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 17 | 0.006 | 5208.41 | 4041.00 | 0.334 | 0.543 |
| Affiliative humor | neutral | 7 | 0.003 | 5080.71 | 2747.00 | 0.341 | 0.496 |
| Affiliative humor | positive | 28 | 0.010 | 1478.64 | 334.50 | 0.461 | 0.841 |
| Aggressive humor | negative | 28 | 0.010 | 3480.14 | 1452.50 | 0.465 | 0.856 |
| Aggressive humor | positive | 7 | 0.003 | 3406.71 | 1282.00 | 0.502 | 0.737 |
| Non-humorous brand message | negative | 286 | 0.104 | 17272.62 | 1870.00 | 0.392 | 0.543 |
| Non-humorous brand message | neutral | 28 | 0.010 | 5994.21 | 1534.00 | 0.498 | 0.480 |
| Non-humorous brand message | positive | 286 | 0.104 | 7420.77 | 1238.00 | 0.493 | 0.670 |
| Self-defeating humor | negative | 22 | 0.008 | 12909.00 | 2206.50 | 0.412 | 0.841 |
| Self-defeating humor | neutral | 2 | 0.001 | 8033.50 | 8033.50 | 0.357 | 0.915 |
| Self-defeating humor | positive | 1 | 0.000 | 10141.00 | 10141.00 | 0.411 | 0.364 |
| Self-enhancing humor | negative | 909 | 0.330 | 6266.14 | 895.00 | 0.497 | 0.622 |
| Self-enhancing humor | neutral | 93 | 0.034 | 4926.30 | 1556.00 | 0.525 | 0.573 |
| Self-enhancing humor | positive | 1043 | 0.378 | 5420.30 | 525.00 | 0.645 | 0.763 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 52 | 0.019 | 3182.88 | 633.00 | 3969.75 | 8088.80 | 27910.00 | 0.403 |
| Aggressive humor | 35 | 0.013 | 3465.46 | 1420.00 | 4443.00 | 10347.60 | 15820.00 | 0.472 |
| Non-humorous brand message | 600 | 0.218 | 12050.24 | 1550.00 | 5646.50 | 17901.20 | 930463.00 | 0.445 |
| Self-defeating humor | 25 | 0.009 | 12408.24 | 2812.00 | 9887.00 | 36314.40 | 98909.00 | 0.407 |
| Self-enhancing humor | 2045 | 0.742 | 5773.81 | 668.00 | 2792.00 | 9224.80 | 1003033.00 | 0.573 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997405 | 0.987770 | 2757 |
| text_length | word_count | 0.939136 | 0.948324 | 2757 |
| retweets | total_engagement | 0.916918 | 0.913758 | 2757 |
| sentiment_negative | sentiment_positive | -0.909821 | -0.909821 | 2757 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.893835 | -0.893835 | 2757 |
| likes | retweets | 0.888617 | 0.880646 | 2757 |
| quotes | total_engagement | 0.620790 | 0.303245 | 2757 |
| likes | quotes | 0.600807 | 0.293181 | 2757 |
| retweets | quotes | 0.566556 | 0.287049 | 2757 |
| replies | total_engagement | 0.545628 | 0.793676 | 2757 |
| likes | replies | 0.538858 | 0.773370 | 2757 |
| total_engagement | is_viral | 0.502028 | 0.348517 | 2757 |
| likes | is_viral | 0.497460 | 0.334121 | 2757 |
| replies | is_viral | 0.465883 | 0.306035 | 2757 |
| replies | quotes | 0.463641 | 0.321862 | 2757 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
