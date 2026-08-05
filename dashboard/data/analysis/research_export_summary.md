# Research Export Summary

## Joined Dataset

- Wendy's: 1004 posts
- MoonPie: 937 posts
- Coca-Cola: 866 posts
- Total: 2807 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7556.40 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3797.60 | 1273.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 769 | 0.274 | 12489.16 | 1294.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8128.77 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 900 | 0.321 | 6429.11 | 717.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14931.50 | 2270.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3200.00 | 3200.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 441 | 0.157 | 4485.56 | 805.00 | 0.403 | 0.639 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.00 | 1056.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 541 | 0.193 | 2232.26 | 554.00 | 0.548 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5562.35 | 490.00 | 862.00 | 16207.80 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.50 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1752 | 0.624 | 9169.55 | 951.00 | 4016.75 | 11465.50 | 991496.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13047.57 | 2270.50 | 5203.25 | 39386.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 1000 | 0.356 | 3239.53 | 657.50 | 2584.00 | 8031.10 | 102272.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987230 | 2807 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958654 | -0.958654 | 2807 |
| text_length | word_count | 0.939665 | 0.948526 | 2807 |
| sentiment_negative | sentiment_positive | -0.929480 | -0.929480 | 2807 |
| retweets | total_engagement | 0.916365 | 0.913341 | 2807 |
| likes | retweets | 0.888340 | 0.880070 | 2807 |
| replies | total_engagement | 0.545997 | 0.795982 | 2807 |
| likes | replies | 0.536596 | 0.772848 | 2807 |
| quotes | total_engagement | 0.536093 | 0.624648 | 2807 |
| likes | quotes | 0.510322 | 0.609551 | 2807 |
| total_engagement | is_viral | 0.502471 | 0.350714 | 2807 |
| likes | is_viral | 0.496362 | 0.335961 | 2807 |
| replies | quotes | 0.477945 | 0.718118 | 2807 |
| retweets | quotes | 0.474898 | 0.511966 | 2807 |
| replies | is_viral | 0.468492 | 0.312761 | 2807 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
