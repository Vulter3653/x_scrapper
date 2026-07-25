# Research Export Summary

## Joined Dataset

- Wendy's: 996 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2798 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7559.20 | 862.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 466.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4111.63 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.20 | 1275.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 768 | 0.274 | 12511.51 | 1309.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8131.78 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 896 | 0.320 | 6460.94 | 720.50 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14934.83 | 2271.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3202.00 | 3202.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4508.52 | 831.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.33 | 1056.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.47 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.18 | 491.00 | 862.00 | 16215.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4046.33 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1747 | 0.624 | 9200.22 | 960.00 | 4061.50 | 11506.00 | 993199.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13050.57 | 2271.50 | 5203.75 | 39409.30 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3246.59 | 658.00 | 2584.00 | 8107.50 | 102798.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987211 | 2798 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958512 | -0.958512 | 2798 |
| text_length | word_count | 0.939621 | 0.948520 | 2798 |
| sentiment_negative | sentiment_positive | -0.929270 | -0.929270 | 2798 |
| retweets | total_engagement | 0.916408 | 0.913311 | 2798 |
| likes | retweets | 0.888386 | 0.879978 | 2798 |
| replies | total_engagement | 0.546271 | 0.796355 | 2798 |
| likes | replies | 0.536910 | 0.773299 | 2798 |
| quotes | total_engagement | 0.536297 | 0.624419 | 2798 |
| likes | quotes | 0.510574 | 0.609349 | 2798 |
| total_engagement | is_viral | 0.503028 | 0.349746 | 2798 |
| likes | is_viral | 0.496794 | 0.334883 | 2798 |
| replies | quotes | 0.478230 | 0.717900 | 2798 |
| retweets | quotes | 0.474956 | 0.511481 | 2798 |
| replies | is_viral | 0.468628 | 0.311597 | 2798 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
