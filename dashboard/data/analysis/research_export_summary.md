# Research Export Summary

## Joined Dataset

- Wendy's: 990 posts
- MoonPie: 936 posts
- Coca-Cola: 866 posts
- Total: 2792 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7560.80 | 867.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4731.83 | 466.50 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4112.89 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.80 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 764 | 0.274 | 12577.89 | 1339.50 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8133.82 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.321 | 6471.23 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14937.92 | 2274.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3204.00 | 3204.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 438 | 0.157 | 4520.33 | 838.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.56 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.78 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.88 | 492.00 | 867.00 | 16217.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.46 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1742 | 0.624 | 9228.68 | 961.00 | 4101.75 | 11536.00 | 994268.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13053.36 | 2274.00 | 5204.25 | 39428.20 | 99388.00 | 0.323 |
| Self-enhancing humor | 995 | 0.356 | 3250.69 | 658.00 | 2592.00 | 8129.80 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987203 | 2792 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958444 | -0.958444 | 2792 |
| text_length | word_count | 0.939692 | 0.948614 | 2792 |
| sentiment_negative | sentiment_positive | -0.929107 | -0.929107 | 2792 |
| retweets | total_engagement | 0.916418 | 0.913378 | 2792 |
| likes | retweets | 0.888396 | 0.880051 | 2792 |
| replies | total_engagement | 0.546414 | 0.796016 | 2792 |
| likes | replies | 0.537076 | 0.772944 | 2792 |
| quotes | total_engagement | 0.536292 | 0.624637 | 2792 |
| likes | quotes | 0.510591 | 0.609518 | 2792 |
| total_engagement | is_viral | 0.502945 | 0.350024 | 2792 |
| likes | is_viral | 0.496727 | 0.335133 | 2792 |
| replies | quotes | 0.478259 | 0.718146 | 2792 |
| retweets | quotes | 0.474907 | 0.511644 | 2792 |
| replies | is_viral | 0.468543 | 0.311816 | 2792 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
