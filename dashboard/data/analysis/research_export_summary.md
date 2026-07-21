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
| Aggressive humor | negative | 19 | 0.007 | 4112.63 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3798.60 | 1276.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 764 | 0.274 | 12576.91 | 1340.00 | 0.399 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8133.23 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 895 | 0.321 | 6470.50 | 722.00 | 0.489 | 0.699 |
| Self-defeating humor | negative | 12 | 0.004 | 14937.25 | 2272.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3204.00 | 3204.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 438 | 0.157 | 4519.89 | 838.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.50 | 1058.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2227.80 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5563.88 | 492.00 | 867.00 | 16217.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4047.21 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1742 | 0.624 | 9227.85 | 961.50 | 4102.50 | 11536.00 | 994058.00 | 0.449 |
| Self-defeating humor | 14 | 0.005 | 13052.79 | 2272.50 | 5204.25 | 39424.70 | 99388.00 | 0.323 |
| Self-enhancing humor | 995 | 0.356 | 3250.51 | 658.00 | 2592.00 | 8129.60 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997267 | 0.987200 | 2792 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958444 | -0.958444 | 2792 |
| text_length | word_count | 0.939692 | 0.948614 | 2792 |
| sentiment_negative | sentiment_positive | -0.929107 | -0.929107 | 2792 |
| retweets | total_engagement | 0.916414 | 0.913175 | 2792 |
| likes | retweets | 0.888392 | 0.879803 | 2792 |
| replies | total_engagement | 0.546381 | 0.796051 | 2792 |
| likes | replies | 0.537039 | 0.772951 | 2792 |
| quotes | total_engagement | 0.536279 | 0.624680 | 2792 |
| likes | quotes | 0.510571 | 0.609555 | 2792 |
| total_engagement | is_viral | 0.502950 | 0.350031 | 2792 |
| likes | is_viral | 0.496729 | 0.335135 | 2792 |
| replies | quotes | 0.478256 | 0.718094 | 2792 |
| retweets | quotes | 0.474908 | 0.511670 | 2792 |
| replies | is_viral | 0.468544 | 0.311811 | 2792 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
