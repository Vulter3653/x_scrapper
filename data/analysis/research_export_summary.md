# Research Export Summary

## Joined Dataset

- Wendy's: 982 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2782 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7565.20 | 869.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.42 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.21 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.80 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12667.02 | 1357.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8137.61 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6491.03 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14943.58 | 2276.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 437 | 0.157 | 4533.00 | 843.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.06 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 538 | 0.193 | 2232.41 | 553.50 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5565.59 | 493.00 | 869.00 | 16227.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4044.75 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.623 | 9273.18 | 967.00 | 4120.25 | 11610.60 | 995913.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13058.29 | 2276.00 | 5204.50 | 39470.90 | 99388.00 | 0.323 |
| Self-enhancing humor | 993 | 0.357 | 3258.54 | 659.00 | 2608.00 | 8175.00 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987189 | 2782 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958326 | -0.958326 | 2782 |
| text_length | word_count | 0.939507 | 0.948457 | 2782 |
| sentiment_negative | sentiment_positive | -0.928851 | -0.928851 | 2782 |
| retweets | total_engagement | 0.916410 | 0.913359 | 2782 |
| likes | retweets | 0.888383 | 0.879989 | 2782 |
| replies | total_engagement | 0.546744 | 0.796041 | 2782 |
| likes | replies | 0.537477 | 0.772987 | 2782 |
| quotes | total_engagement | 0.536285 | 0.624419 | 2782 |
| likes | quotes | 0.510620 | 0.609291 | 2782 |
| total_engagement | is_viral | 0.502840 | 0.350536 | 2782 |
| likes | is_viral | 0.496645 | 0.335608 | 2782 |
| replies | quotes | 0.478106 | 0.718556 | 2782 |
| retweets | quotes | 0.474826 | 0.511380 | 2782 |
| replies | is_viral | 0.468351 | 0.312162 | 2782 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
