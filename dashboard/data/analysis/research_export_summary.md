# Research Export Summary

## Joined Dataset

- Wendy's: 999 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2801 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7558.60 | 864.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.95 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.20 | 1275.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.275 | 12491.91 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8130.08 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 898 | 0.321 | 6445.22 | 720.50 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14932.92 | 2271.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3200.00 | 3200.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4506.05 | 830.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.33 | 1057.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.192 | 2227.06 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.00 | 490.00 | 864.00 | 16213.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.00 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1750 | 0.625 | 9182.22 | 954.00 | 4026.50 | 11488.00 | 992239.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13048.79 | 2271.00 | 5203.25 | 39396.00 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3245.28 | 658.00 | 2584.00 | 8099.50 | 102333.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987218 | 2801 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958537 | -0.958537 | 2801 |
| text_length | word_count | 0.939676 | 0.948597 | 2801 |
| sentiment_negative | sentiment_positive | -0.929340 | -0.929340 | 2801 |
| retweets | total_engagement | 0.916393 | 0.913213 | 2801 |
| likes | retweets | 0.888365 | 0.879919 | 2801 |
| replies | total_engagement | 0.546147 | 0.795969 | 2801 |
| likes | replies | 0.536766 | 0.772841 | 2801 |
| quotes | total_engagement | 0.536087 | 0.624302 | 2801 |
| likes | quotes | 0.510321 | 0.609171 | 2801 |
| total_engagement | is_viral | 0.503068 | 0.349601 | 2801 |
| likes | is_viral | 0.496824 | 0.334755 | 2801 |
| replies | quotes | 0.477964 | 0.718008 | 2801 |
| retweets | quotes | 0.474917 | 0.511410 | 2801 |
| replies | is_viral | 0.468652 | 0.311438 | 2801 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
