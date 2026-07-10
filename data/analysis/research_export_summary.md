# Research Export Summary

## Joined Dataset

- Wendy's: 984 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2784 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7565.20 | 869.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.42 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.58 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.80 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 761 | 0.273 | 12633.55 | 1355.00 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8137.39 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.320 | 6490.67 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14943.58 | 2276.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 437 | 0.157 | 4532.96 | 843.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.06 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 538 | 0.193 | 2232.37 | 553.50 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5565.59 | 493.00 | 869.00 | 16227.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.04 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1736 | 0.624 | 9262.22 | 964.00 | 4112.75 | 11591.00 | 995750.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13058.29 | 2276.00 | 5204.50 | 39470.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 993 | 0.357 | 3258.50 | 659.00 | 2608.00 | 8177.80 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987191 | 2784 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958343 | -0.958343 | 2784 |
| text_length | word_count | 0.939613 | 0.948549 | 2784 |
| sentiment_negative | sentiment_positive | -0.928908 | -0.928908 | 2784 |
| retweets | total_engagement | 0.916409 | 0.913478 | 2784 |
| likes | retweets | 0.888383 | 0.880092 | 2784 |
| replies | total_engagement | 0.546734 | 0.796187 | 2784 |
| likes | replies | 0.537463 | 0.773193 | 2784 |
| quotes | total_engagement | 0.536284 | 0.624740 | 2784 |
| likes | quotes | 0.510617 | 0.609640 | 2784 |
| total_engagement | is_viral | 0.502864 | 0.350440 | 2784 |
| likes | is_viral | 0.496666 | 0.335526 | 2784 |
| replies | quotes | 0.478115 | 0.718569 | 2784 |
| retweets | quotes | 0.474826 | 0.511882 | 2784 |
| replies | is_viral | 0.468373 | 0.312090 | 2784 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
