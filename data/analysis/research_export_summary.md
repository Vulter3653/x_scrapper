# Research Export Summary

## Joined Dataset

- Wendy's: 1008 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2811 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.80 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.42 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4108.00 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.20 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12485.36 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8126.76 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 903 | 0.321 | 6407.55 | 715.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14929.33 | 2270.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3199.00 | 3199.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 442 | 0.157 | 4475.00 | 803.50 | 0.403 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2985.94 | 1055.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.192 | 2235.70 | 553.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.41 | 491.00 | 862.00 | 16207.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4043.25 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1755 | 0.624 | 9152.01 | 950.00 | 4009.50 | 11416.00 | 990820.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13045.64 | 2270.00 | 5203.00 | 39371.50 | 99388.00 | 0.323 |
| Self-enhancing humor | 1001 | 0.356 | 3237.97 | 657.00 | 2608.00 | 8178.00 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987226 | 2811 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958704 | -0.958704 | 2811 |
| text_length | word_count | 0.939705 | 0.948571 | 2811 |
| sentiment_negative | sentiment_positive | -0.929571 | -0.929571 | 2811 |
| retweets | total_engagement | 0.916396 | 0.913158 | 2811 |
| likes | retweets | 0.888381 | 0.879898 | 2811 |
| replies | total_engagement | 0.545111 | 0.795320 | 2811 |
| quotes | total_engagement | 0.536475 | 0.624222 | 2811 |
| likes | replies | 0.535633 | 0.772088 | 2811 |
| likes | quotes | 0.510700 | 0.609080 | 2811 |
| total_engagement | is_viral | 0.502524 | 0.350550 | 2811 |
| likes | is_viral | 0.496389 | 0.335779 | 2811 |
| replies | quotes | 0.477596 | 0.718044 | 2811 |
| retweets | quotes | 0.475399 | 0.511379 | 2811 |
| replies | is_viral | 0.468925 | 0.312634 | 2811 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
