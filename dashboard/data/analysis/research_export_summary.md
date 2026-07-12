# Research Export Summary

## Joined Dataset

- Wendy's: 986 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2786 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7564.00 | 868.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.33 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4109.63 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.60 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 761 | 0.273 | 12632.33 | 1355.00 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8136.95 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 893 | 0.321 | 6488.62 | 728.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14942.58 | 2276.00 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 437 | 0.157 | 4532.54 | 843.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2987.11 | 1059.00 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2228.53 | 553.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5565.18 | 493.00 | 868.00 | 16224.60 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.04 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1737 | 0.623 | 9259.01 | 964.00 | 4123.00 | 11581.20 | 995429.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13057.43 | 2276.00 | 5204.50 | 39461.10 | 99388.00 | 0.323 |
| Self-enhancing humor | 994 | 0.357 | 3255.20 | 658.50 | 2600.00 | 8156.20 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987198 | 2786 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958377 | -0.958377 | 2786 |
| text_length | word_count | 0.939677 | 0.948619 | 2786 |
| sentiment_negative | sentiment_positive | -0.928950 | -0.928950 | 2786 |
| retweets | total_engagement | 0.916411 | 0.913543 | 2786 |
| likes | retweets | 0.888385 | 0.880179 | 2786 |
| replies | total_engagement | 0.546600 | 0.796001 | 2786 |
| likes | replies | 0.537308 | 0.772997 | 2786 |
| quotes | total_engagement | 0.536279 | 0.624831 | 2786 |
| likes | quotes | 0.510603 | 0.609753 | 2786 |
| total_engagement | is_viral | 0.502881 | 0.350302 | 2786 |
| likes | is_viral | 0.496677 | 0.335392 | 2786 |
| replies | quotes | 0.478168 | 0.718354 | 2786 |
| retweets | quotes | 0.474836 | 0.512023 | 2786 |
| replies | is_viral | 0.468436 | 0.312021 | 2786 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
