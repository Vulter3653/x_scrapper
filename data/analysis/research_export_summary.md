# Research Export Summary

## Joined Dataset

- Wendy's: 959 posts
- MoonPie: 932 posts
- Coca-Cola: 866 posts
- Total: 2757 posts

## Table 4: Humor x Sentiment x Engagement

| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Affiliative humor | negative | 27 | 0.010 | 6735.41 | 2758.00 | 0.362 | 0.576 |
| Affiliative humor | neutral | 11 | 0.004 | 3634.27 | 1253.00 | 0.337 | 0.468 |
| Affiliative humor | positive | 31 | 0.011 | 2659.45 | 467.00 | 0.452 | 0.816 |
| Aggressive humor | negative | 38 | 0.014 | 4475.66 | 1543.50 | 0.458 | 0.825 |
| Aggressive humor | positive | 8 | 0.003 | 1913.62 | 1670.50 | 0.488 | 0.700 |
| Self-defeating humor | negative | 30 | 0.011 | 13347.80 | 3033.50 | 0.411 | 0.797 |
| Self-defeating humor | neutral | 5 | 0.002 | 4447.40 | 4650.00 | 0.373 | 0.669 |
| Self-defeating humor | positive | 2 | 0.001 | 6172.00 | 6172.00 | 0.503 | 0.599 |
| Self-enhancing humor | negative | 1200 | 0.435 | 8651.34 | 1042.00 | 0.523 | 0.622 |
| Self-enhancing humor | neutral | 121 | 0.044 | 5027.77 | 1752.00 | 0.535 | 0.571 |
| Self-enhancing humor | positive | 1284 | 0.466 | 6013.45 | 633.00 | 0.645 | 0.749 |

## Table 5: Engagement Robustness by Humor Type

| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Affiliative humor | 69 | 0.025 | 4409.80 | 778.00 | 4041.00 | 11084.60 | 41442.00 | 0.398 |
| Aggressive humor | 46 | 0.017 | 4030.09 | 1543.50 | 4540.00 | 9552.50 | 44182.00 | 0.463 |
| Self-defeating humor | 37 | 0.013 | 11757.16 | 3255.00 | 10073.00 | 23154.00 | 114199.00 | 0.411 |
| Self-enhancing humor | 2605 | 0.945 | 7182.82 | 820.00 | 3305.00 | 10037.20 | 1003033.00 | 0.584 |

## Strongest Pearson Correlations

| Variable A | Variable B | Pearson r | Spearman rho | N |
|---|---|---:|---:|---:|
| likes | total_engagement | 0.997406 | 0.987762 | 2757 |
| text_length | word_count | 0.939136 | 0.948324 | 2757 |
| retweets | total_engagement | 0.916905 | 0.913791 | 2757 |
| sentiment_negative | sentiment_positive | -0.905311 | -0.905311 | 2757 |
| likes | retweets | 0.888616 | 0.880659 | 2757 |
| humor_affiliative_humor | humor_self_enhancing_humor | -0.663272 | -0.663272 | 2757 |
| quotes | total_engagement | 0.619745 | 0.313778 | 2757 |
| likes | quotes | 0.599804 | 0.303372 | 2757 |
| retweets | quotes | 0.565054 | 0.301844 | 2757 |
| replies | total_engagement | 0.545643 | 0.793708 | 2757 |
| humor_aggressive_humor | humor_self_enhancing_humor | -0.539258 | -0.539258 | 2757 |
| likes | replies | 0.538858 | 0.773380 | 2757 |
| total_engagement | is_viral | 0.501943 | 0.348498 | 2757 |
| likes | is_viral | 0.497446 | 0.334122 | 2757 |
| humor_self_defeating_humor | humor_self_enhancing_humor | -0.482835 | -0.482835 | 2757 |

## Topic Assignment Note

Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.
