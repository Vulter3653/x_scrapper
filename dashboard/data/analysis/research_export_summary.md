# Research Export Summary

## Joined Dataset

- Wendy's: 980 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2778 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7566.60 | 870.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.58 | 467.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4096.58 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3801.00 | 1280.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12673.27 | 1359.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8140.23 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6495.07 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14947.42 | 2278.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3207.00 | 3207.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 435 | 0.157 | 4554.45 | 854.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.11 | 1059.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2236.89 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5566.12 | 494.00 | 870.00 | 16230.00 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4035.00 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.624 | 9278.12 | 968.00 | 4123.00 | 11610.60 | 997126.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13061.71 | 2278.00 | 5205.00 | 39496.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 989 | 0.356 | 3269.89 | 664.00 | 2613.00 | 8245.20 | 102798.00 | 0.483 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997271 | 0.987183 | 2778 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958225 | -0.958225 | 2778 |
| text_length | word_count | 0.939396 | 0.948406 | 2778 |
| sentiment_negative | sentiment_positive | -0.928751 | -0.928751 | 2778 |
| retweets | total_engagement | 0.916392 | 0.913490 | 2778 |
| likes | retweets | 0.888381 | 0.880069 | 2778 |
| replies | total_engagement | 0.547574 | 0.796090 | 2778 |
| likes | replies | 0.538483 | 0.773082 | 2778 |
| quotes | total_engagement | 0.536492 | 0.624579 | 2778 |
| likes | quotes | 0.510884 | 0.609442 | 2778 |
| total_engagement | is_viral | 0.503437 | 0.349255 | 2778 |
| likes | is_viral | 0.497187 | 0.334268 | 2778 |
| replies | quotes | 0.477689 | 0.719105 | 2778 |
| retweets | quotes | 0.474882 | 0.511826 | 2778 |
| replies | is_viral | 0.467101 | 0.310607 | 2778 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
