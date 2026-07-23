# Research Export Summary

## Joined Dataset

- Wendy's: 994 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2796 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7560.00 | 864.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.75 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4112.95 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.40 | 1276.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 767 | 0.274 | 12527.57 | 1324.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8132.59 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.320 | 6469.30 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14935.67 | 2272.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3203.00 | 3203.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4509.19 | 830.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.44 | 1057.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.65 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.59 | 491.00 | 864.00 | 16216.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.42 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1745 | 0.624 | 9211.27 | 960.00 | 4092.00 | 11518.00 | 993672.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13051.36 | 2272.00 | 5204.00 | 39413.50 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3246.98 | 658.00 | 2584.00 | 8110.50 | 102798.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987207 | 2796 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958495 | -0.958495 | 2796 |
| text_length | word_count | 0.939715 | 0.948710 | 2796 |
| sentiment_negative | sentiment_positive | -0.929221 | -0.929221 | 2796 |
| retweets | total_engagement | 0.916416 | 0.913345 | 2796 |
| likes | retweets | 0.888397 | 0.880000 | 2796 |
| replies | total_engagement | 0.546319 | 0.796402 | 2796 |
| likes | replies | 0.536968 | 0.773355 | 2796 |
| quotes | total_engagement | 0.536303 | 0.624699 | 2796 |
| likes | quotes | 0.510590 | 0.609634 | 2796 |
| total_engagement | is_viral | 0.502993 | 0.349838 | 2796 |
| likes | is_viral | 0.496766 | 0.334973 | 2796 |
| replies | quotes | 0.478247 | 0.717972 | 2796 |
| retweets | quotes | 0.474948 | 0.511759 | 2796 |
| replies | is_viral | 0.468589 | 0.311667 | 2796 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
