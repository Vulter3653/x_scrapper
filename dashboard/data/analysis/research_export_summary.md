# Research Export Summary

## Joined Dataset

- Wendy's: 986 posts
- MoonPie: 934 posts
- Coca-Cola: 866 posts
- Total: 2786 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 5 | 0.002 | 7562.40 | 868.00 | 0.290 | 0.767 |
| Affiliative humor | positive | 12 | 0.004 | 4732.08 | 467.00 | 0.369 | 0.730 |
| Aggressive humor | negative | 19 | 0.007 | 4110.47 | 1901.00 | 0.388 | 0.704 |
| Aggressive humor | positive | 5 | 0.002 | 3799.20 | 1277.00 | 0.347 | 0.766 |
| Non-humorous brand message | negative | 761 | 0.273 | 12631.37 | 1355.00 | 0.399 | 0.537 |
| Non-humorous brand message | neutral | 83 | 0.030 | 8136.40 | 2050.00 | 0.491 | 0.464 |
| Non-humorous brand message | positive | 893 | 0.321 | 6487.98 | 728.00 | 0.489 | 0.700 |
| Self-defeating humor | negative | 12 | 0.004 | 14941.58 | 2275.50 | 0.332 | 0.776 |
| Self-defeating humor | neutral | 1 | 0.000 | 3205.00 | 3205.00 | 0.260 | 0.489 |
| Self-defeating humor | positive | 1 | 0.000 | 288.00 | 288.00 | 0.274 | 0.638 |
| Self-enhancing humor | negative | 437 | 0.157 | 4532.11 | 843.00 | 0.405 | 0.640 |
| Self-enhancing humor | neutral | 18 | 0.006 | 2986.94 | 1058.50 | 0.351 | 0.443 |
| Self-enhancing humor | positive | 539 | 0.193 | 2228.34 | 553.00 | 0.549 | 0.769 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 17 | 0.006 | 5564.53 | 493.00 | 868.00 | 16220.40 | 50315.00 | 0.346 |
| Aggressive humor | 24 | 0.009 | 4045.62 | 1692.00 | 4470.75 | 13758.50 | 15940.00 | 0.379 |
| Non-humorous brand message | 1737 | 0.623 | 9258.24 | 964.00 | 4121.00 | 11581.20 | 995312.00 | 0.450 |
| Self-defeating humor | 14 | 0.005 | 13056.57 | 2275.50 | 5204.50 | 39453.40 | 99388.00 | 0.323 |
| Self-enhancing humor | 994 | 0.357 | 3254.90 | 658.50 | 2600.00 | 8154.60 | 102798.00 | 0.482 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997268 | 0.987199 | 2786 |
| humor_non_humorous_brand_message | humor_self_enhancing_humor | -0.958377 | -0.958377 | 2786 |
| text_length | word_count | 0.939677 | 0.948619 | 2786 |
| sentiment_negative | sentiment_positive | -0.928950 | -0.928950 | 2786 |
| retweets | total_engagement | 0.916415 | 0.913534 | 2786 |
| likes | retweets | 0.888390 | 0.880168 | 2786 |
| replies | total_engagement | 0.546582 | 0.795977 | 2786 |
| likes | replies | 0.537281 | 0.772966 | 2786 |
| quotes | total_engagement | 0.536271 | 0.624842 | 2786 |
| likes | quotes | 0.510592 | 0.609758 | 2786 |
| total_engagement | is_viral | 0.502879 | 0.350310 | 2786 |
| likes | is_viral | 0.496675 | 0.335389 | 2786 |
| replies | quotes | 0.478205 | 0.718358 | 2786 |
| retweets | quotes | 0.474837 | 0.512001 | 2786 |
| replies | is_viral | 0.468450 | 0.312027 | 2786 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
