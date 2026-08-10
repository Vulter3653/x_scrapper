# Research Export Summary

## Joined Dataset

- Wendy's: 1008 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2811 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.40 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4108.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.20 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12486.21 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8127.05 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 903 | 0.321 | 6408.10 | 715.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14929.25 | 2270.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3199.00 | 3199.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 442 | 0.157 | 4474.76 | 803.50 | 0.403 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2985.94 | 1055.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.192 | 2235.82 | 553.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.35 | 491.00 | 862.00 | 16206.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4043.62 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1755 | 0.624 | 9152.68 | 950.00 | 4009.50 | 11416.00 | 990922.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13045.57 | 2270.50 | 5203.00 | 39370.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 1001 | 0.356 | 3237.93 | 657.00 | 2592.00 | 8176.00 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987232 | 2811 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958704 | -0.958704 | 2811 |
| text_length | word_count | 0.939705 | 0.948571 | 2811 |
| sentiment_negative | sentiment_positive | -0.929571 | -0.929571 | 2811 |
| retweets | total_engagement | 0.916387 | 0.913242 | 2811 |
| likes | retweets | 0.888369 | 0.880014 | 2811 |
| replies | total_engagement | 0.545185 | 0.795553 | 2811 |
| quotes | total_engagement | 0.536459 | 0.624286 | 2811 |
| likes | replies | 0.535715 | 0.772373 | 2811 |
| likes | quotes | 0.510684 | 0.609185 | 2811 |
| total_engagement | is_viral | 0.502527 | 0.350552 | 2811 |
| likes | is_viral | 0.496394 | 0.335783 | 2811 |
| replies | quotes | 0.477611 | 0.718051 | 2811 |
| retweets | quotes | 0.475386 | 0.511313 | 2811 |
| replies | is_viral | 0.468908 | 0.312639 | 2811 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
