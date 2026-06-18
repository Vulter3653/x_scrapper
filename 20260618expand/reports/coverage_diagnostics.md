# Coverage Diagnostics

Generated from existing repository files only. No X collection, X API call, SEC download, dashboard sync, or model inference is performed.

## Summary

- Fortune Top 100 raw folders inspected: 100
- posts.csv exists firms: 100
- non-empty posts.csv firms: 97
- total deduplicated posts: 65245
- duplicate tweet rows audited before deduplication: 77
- missing text rows: 0
- missing engagement proxy rows: 0
- collection status not success / not empty: 5
- empty posts.csv firms: 3

## Deduplication Rule

Rows are deduplicated by `tweet_id`. If the same tweet id appears more than once, the retained row is the copy with the highest `total_engagement`; ties are resolved by lexicographic `source_folder`. All duplicate source rows are written to `data/diagnostics/fortune100_duplicate_tweet_audit.csv`.

## Post Format Controls

The literature-based post format controls prepared for hypothesis datasets are exactly `text_length`, `hashtag_count`, and `mention_count`. `emoji_count` is intentionally excluded.

## Largest Account-Level Post Counts

- General Dynamics / @generaldynamics: 1493
- Walt Disney / @Disney: 1353
- Nationwide / @nationwide: 1149
- Ford Motor / @Ford: 1146
- Nvidia / @nvidia: 1117
- Comcast / @comcast: 1096
- Amazon / @amazon: 1086
- Tyson Foods / @tysonfoods: 1081
- Liberty Mutual Insurance Group / @LibertyMutual: 1018
- Goldman Sachs Group / @GoldmanSachs: 1012
- Cisco Systems / @Cisco: 1007
- Boeing / @boeing: 969
- Uber Technologies / @Uber: 952
- ConocoPhillips / @conocophillips: 942
- AT&T / @ATT: 933
- Ingram Micro Holding / @IngramMicroInc: 931
- Bristol-Myers Squibb / @bmsnews: 930
- TJX / @tjmaxx: 909
- Oracle / @oracle: 909
- Lowe's / @lowes: 908

## Empty Or Failed Coverage Rows

- rank 4: Apple status=no_observable_posts posts=0 error=manual_no_observable_posts
- rank 7: Berkshire Hathaway status=no_observable_posts posts=0 error=no_observable_posts
- rank 13: Costco Wholesale status=no_observable_posts posts=0 error=no_observable_posts
- rank 25: Home Depot status=partial_success posts=1392 error=collector_failed
- rank 29: Phillips 66 status=partial_success posts=684 error=collector_failed
- rank 4: Apple status=no_observable_posts posts=0 error=manual_no_observable_posts
- rank 7: Berkshire Hathaway status=no_observable_posts posts=0 error=no_observable_posts
- rank 13: Costco Wholesale status=no_observable_posts posts=0 error=no_observable_posts
