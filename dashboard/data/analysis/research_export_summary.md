# Research Export Summary

## Joined Dataset

- Wendy's: 975 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2773 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7573.40 | 874.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.75 | 468.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4092.37 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3804.60 | 1281.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 759 | 0.274 | 12687.19 | 1361.00 | 0.398 | 0.538 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8148.92 | 2051.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 888 | 0.320 | 6530.84 | 726.00 | 0.490 | 0.701 |
| Self-defeating humor | negative | 12 | 0.004 | 14959.67 | 2283.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3215.00 | 3215.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 434 | 0.157 | 4569.13 | 856.00 | 0.404 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.94 | 1060.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 536 | 0.193 | 2238.75 | 551.00 | 0.550 | 0.770 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5568.24 | 495.00 | 874.00 | 16247.20 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4032.42 | 1692.00 | 4470.75 | 13763.90 | 15942.00 | 0.379 |
| Non-humorous brand message | 1730 | 0.624 | 9309.43 | 973.00 | 4159.00 | 11649.60 | 999915.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13072.79 | 2283.00 | 5207.00 | 39566.10 | 99411.00 | 0.323 |
| Self-enhancing humor | 988 | 0.356 | 3276.07 | 667.50 | 2618.75 | 8268.10 | 103005.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997269 | 0.987186 | 2773 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958165 | -0.958165 | 2773 |
| text_length | word_count | 0.939333 | 0.948382 | 2773 |
| sentiment_negative | sentiment_positive | -0.928637 | -0.928637 | 2773 |
| retweets | total_engagement | 0.916460 | 0.913672 | 2773 |
| likes | retweets | 0.888434 | 0.880289 | 2773 |
| replies | total_engagement | 0.547825 | 0.796535 | 2773 |
| likes | replies | 0.538753 | 0.773638 | 2773 |
| quotes | total_engagement | 0.536433 | 0.624859 | 2773 |
| likes | quotes | 0.510871 | 0.609782 | 2773 |
| total_engagement | is_viral | 0.503312 | 0.349501 | 2773 |
| likes | is_viral | 0.497103 | 0.334491 | 2773 |
| replies | quotes | 0.477935 | 0.719208 | 2773 |
| retweets | quotes | 0.474769 | 0.512124 | 2773 |
| replies | is_viral | 0.467113 | 0.310821 | 2773 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
