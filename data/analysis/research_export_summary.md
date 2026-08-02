# Research Export Summary

## Joined Dataset

- Wendy's: 1000 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2802 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7558.00 | 864.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.84 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.20 | 1275.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12491.14 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8129.98 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 898 | 0.320 | 6444.70 | 720.50 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14932.50 | 2271.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3200.00 | 3200.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4505.72 | 830.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.17 | 1056.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 540 | 0.193 | 2223.19 | 551.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.82 | 490.00 | 864.00 | 16211.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.92 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1750 | 0.625 | 9181.61 | 954.00 | 4026.50 | 11488.00 | 992049.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13048.43 | 2271.00 | 5203.25 | 39393.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 997 | 0.356 | 3242.01 | 658.00 | 2576.00 | 8082.60 | 102331.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987221 | 2802 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958562 | -0.958562 | 2802 |
| text_length | word_count | 0.939701 | 0.948623 | 2802 |
| sentiment_negative | sentiment_positive | -0.929361 | -0.929361 | 2802 |
| retweets | total_engagement | 0.916388 | 0.913232 | 2802 |
| likes | retweets | 0.888361 | 0.879942 | 2802 |
| replies | total_engagement | 0.546113 | 0.796003 | 2802 |
| likes | replies | 0.536729 | 0.772894 | 2802 |
| quotes | total_engagement | 0.536079 | 0.624246 | 2802 |
| likes | quotes | 0.510313 | 0.609149 | 2802 |
| total_engagement | is_viral | 0.503080 | 0.349550 | 2802 |
| likes | is_viral | 0.496835 | 0.334709 | 2802 |
| replies | quotes | 0.477957 | 0.717923 | 2802 |
| retweets | quotes | 0.474903 | 0.511296 | 2802 |
| replies | is_viral | 0.468664 | 0.311399 | 2802 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
