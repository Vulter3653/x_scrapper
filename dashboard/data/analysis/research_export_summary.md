# Research Export Summary

## Joined Dataset

- Wendy's: 1009 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2812 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.40 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.25 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4107.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.20 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.273 | 12485.22 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8126.31 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 903 | 0.321 | 6407.36 | 715.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14928.83 | 2269.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3198.00 | 3198.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 443 | 0.158 | 4466.38 | 802.00 | 0.403 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2985.83 | 1055.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.192 | 2235.70 | 553.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.18 | 491.00 | 862.00 | 16206.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4042.83 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1755 | 0.624 | 9151.83 | 950.00 | 4009.00 | 11416.00 | 990761.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13045.14 | 2269.50 | 5202.75 | 39368.00 | 99388.00 | 0.323 |
| Self-enhancing humor | 1002 | 0.356 | 3235.39 | 657.50 | 2600.00 | 8158.60 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987230 | 2812 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958729 | -0.958729 | 2812 |
| text_length | word_count | 0.939696 | 0.948554 | 2812 |
| sentiment_negative | sentiment_positive | -0.929599 | -0.929599 | 2812 |
| retweets | total_engagement | 0.916391 | 0.913117 | 2812 |
| likes | retweets | 0.888376 | 0.879873 | 2812 |
| replies | total_engagement | 0.545069 | 0.795147 | 2812 |
| quotes | total_engagement | 0.536106 | 0.624235 | 2812 |
| likes | replies | 0.535571 | 0.771896 | 2812 |
| likes | quotes | 0.510311 | 0.609076 | 2812 |
| total_engagement | is_viral | 0.502541 | 0.350505 | 2812 |
| likes | is_viral | 0.496396 | 0.335736 | 2812 |
| replies | quotes | 0.477607 | 0.718020 | 2812 |
| retweets | quotes | 0.474954 | 0.511364 | 2812 |
| replies | is_viral | 0.468947 | 0.312566 | 2812 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
