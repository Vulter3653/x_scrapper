# Research Export Summary

## Joined Dataset

- Wendy's: 997 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2799 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7559.00 | 864.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.50 | 465.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4110.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.20 | 1275.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 768 | 0.274 | 12509.25 | 1309.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8131.11 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 897 | 0.320 | 6452.32 | 719.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14933.50 | 2271.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3202.00 | 3202.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 439 | 0.157 | 4506.59 | 829.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.44 | 1057.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.23 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.12 | 490.00 | 864.00 | 16214.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.42 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1748 | 0.625 | 9193.20 | 957.50 | 4046.25 | 11500.00 | 992462.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13049.43 | 2271.50 | 5203.75 | 39398.80 | 99388.00 | 0.323 |
| Self-enhancing humor | 996 | 0.356 | 3245.61 | 658.00 | 2584.00 | 8102.50 | 102364.00 | 0.481 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997266 | 0.987215 | 2799 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958520 | -0.958520 | 2799 |
| text_length | word_count | 0.939635 | 0.948542 | 2799 |
| sentiment_negative | sentiment_positive | -0.929291 | -0.929291 | 2799 |
| retweets | total_engagement | 0.916396 | 0.913203 | 2799 |
| likes | retweets | 0.888369 | 0.879883 | 2799 |
| replies | total_engagement | 0.546215 | 0.796153 | 2799 |
| likes | replies | 0.536838 | 0.773084 | 2799 |
| quotes | total_engagement | 0.536300 | 0.624355 | 2799 |
| likes | quotes | 0.510565 | 0.609270 | 2799 |
| total_engagement | is_viral | 0.503049 | 0.349698 | 2799 |
| likes | is_viral | 0.496811 | 0.334846 | 2799 |
| replies | quotes | 0.478216 | 0.717891 | 2799 |
| retweets | quotes | 0.474972 | 0.511467 | 2799 |
| replies | is_viral | 0.468636 | 0.311558 | 2799 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
