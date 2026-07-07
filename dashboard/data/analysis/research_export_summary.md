# Research Export Summary

## Joined Dataset

- Wendy's: 981 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2781 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7565.40 | 869.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.50 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4108.00 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3800.40 | 1279.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.273 | 12668.38 | 1358.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8138.08 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 892 | 0.321 | 6491.83 | 725.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14944.17 | 2276.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 436 | 0.157 | 4542.96 | 848.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.11 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 538 | 0.193 | 2232.49 | 554.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5565.71 | 493.00 | 869.00 | 16227.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4043.92 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1734 | 0.624 | 9274.21 | 967.00 | 4120.50 | 11610.60 | 996150.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13058.79 | 2276.00 | 5204.50 | 39474.40 | 99388.00 | 0.323 |
| Self-enhancing humor | 992 | 0.357 | 3261.67 | 661.50 | 2609.25 | 8204.10 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997269 | 0.987189 | 2781 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958301 | -0.958301 | 2781 |
| text_length | word_count | 0.939504 | 0.948466 | 2781 |
| sentiment_negative | sentiment_positive | -0.928822 | -0.928822 | 2781 |
| retweets | total_engagement | 0.916404 | 0.913409 | 2781 |
| likes | retweets | 0.888385 | 0.880039 | 2781 |
| replies | total_engagement | 0.547078 | 0.796004 | 2781 |
| likes | replies | 0.537887 | 0.772961 | 2781 |
| quotes | total_engagement | 0.536415 | 0.624465 | 2781 |
| likes | quotes | 0.510772 | 0.609350 | 2781 |
| total_engagement | is_viral | 0.502824 | 0.350584 | 2781 |
| likes | is_viral | 0.496635 | 0.335649 | 2781 |
| replies | quotes | 0.477925 | 0.718623 | 2781 |
| retweets | quotes | 0.474911 | 0.511445 | 2781 |
| replies | is_viral | 0.468180 | 0.312196 | 2781 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
