# Research Export Summary

## Joined Dataset

- Wendy's: 978 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2776 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7568.40 | 872.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.92 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4093.11 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3803.20 | 1282.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12681.13 | 1359.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8144.94 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 891 | 0.321 | 6507.35 | 722.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14952.67 | 2282.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3213.00 | 3213.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 434 | 0.156 | 4566.98 | 855.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.50 | 1060.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2237.83 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5566.88 | 495.00 | 872.00 | 16235.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4032.71 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1733 | 0.624 | 9289.70 | 972.00 | 4134.00 | 11620.40 | 998889.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13066.64 | 2282.00 | 5206.50 | 39531.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 988 | 0.356 | 3274.62 | 667.00 | 2618.75 | 8260.60 | 102911.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997269 | 0.987190 | 2776 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958190 | -0.958190 | 2776 |
| text_length | word_count | 0.939382 | 0.948417 | 2776 |
| sentiment_negative | sentiment_positive | -0.928701 | -0.928701 | 2776 |
| retweets | total_engagement | 0.916415 | 0.913437 | 2776 |
| likes | retweets | 0.888386 | 0.880014 | 2776 |
| replies | total_engagement | 0.547854 | 0.796466 | 2776 |
| likes | replies | 0.538776 | 0.773551 | 2776 |
| quotes | total_engagement | 0.536477 | 0.624755 | 2776 |
| likes | quotes | 0.510898 | 0.609709 | 2776 |
| total_engagement | is_viral | 0.503373 | 0.349355 | 2776 |
| likes | is_viral | 0.497150 | 0.334357 | 2776 |
| replies | quotes | 0.477932 | 0.718944 | 2776 |
| retweets | quotes | 0.474812 | 0.511936 | 2776 |
| replies | is_viral | 0.467153 | 0.310721 | 2776 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
