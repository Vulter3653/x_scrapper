# Research Export Summary

## Joined Dataset

- Wendy's: 979 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2777 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7568.00 | 871.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.75 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4094.05 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3802.80 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12678.99 | 1359.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8143.66 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 891 | 0.321 | 6505.77 | 722.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14950.50 | 2280.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3211.00 | 3211.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 435 | 0.157 | 4556.59 | 855.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.44 | 1060.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2237.51 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5566.65 | 494.00 | 871.00 | 16234.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4033.38 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1733 | 0.624 | 9287.89 | 971.00 | 4135.00 | 11620.40 | 998433.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13064.64 | 2280.50 | 5206.00 | 39516.40 | 99388.00 | 0.323 |
| Self-enhancing humor | 989 | 0.356 | 3271.18 | 664.00 | 2613.00 | 8255.00 | 102874.00 | 0.483 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997270 | 0.987188 | 2777 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958216 | -0.958216 | 2777 |
| text_length | word_count | 0.939421 | 0.948454 | 2777 |
| sentiment_negative | sentiment_positive | -0.928729 | -0.928729 | 2777 |
| retweets | total_engagement | 0.916416 | 0.913432 | 2777 |
| likes | retweets | 0.888396 | 0.880003 | 2777 |
| replies | total_engagement | 0.547778 | 0.796470 | 2777 |
| likes | replies | 0.538698 | 0.773540 | 2777 |
| quotes | total_engagement | 0.536489 | 0.624646 | 2777 |
| likes | quotes | 0.510902 | 0.609593 | 2777 |
| total_engagement | is_viral | 0.503393 | 0.349309 | 2777 |
| likes | is_viral | 0.497163 | 0.334311 | 2777 |
| replies | quotes | 0.477863 | 0.718855 | 2777 |
| retweets | quotes | 0.474847 | 0.511864 | 2777 |
| replies | is_viral | 0.467151 | 0.310693 | 2777 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
