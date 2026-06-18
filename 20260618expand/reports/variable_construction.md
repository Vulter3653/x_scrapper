# Variable Construction

This expansion preserves the Wendy's-only structure in `20260615wendy's/` while moving all new outputs into `20260618expand/`.

## Input Paths

- `data/raw/fortune_x_2025_ranked/*/posts.csv`
- `data/raw/fortune_x_2025_ranked/*/account_audit.csv`
- `data/audit/fortune_x_2025_ranked_collection_summary.csv`
- `config/fortune2025_top100_verified_x_collection_queue.csv`
- `config/fortune2025_x_account_verification_master.csv`
- `data/derived/humor/full_chain/humor_full_chain_master.csv`, when existing classifications are available

## Post Master Variables

`fortune100_post_master.csv` coalesces count columns across raw files:

- repost metric: `repost_count`, falling back to `retweet_count` or equivalent raw names
- like metric: `like_count`, falling back to `favorite_count` or equivalent raw names
- total engagement: `reply_count + repost_count + like_count + quote_count`
- brand equity proxy: `log_total_engagement = log1p(total_engagement)`

Post format controls are:

- `text_length`
- `hashtag_count`
- `mention_count`

`emoji_count` is intentionally excluded from the hypothesis-ready controls.

## Deduplication

Rows are deduplicated by `tweet_id`. When duplicates exist, the retained row is the copy with the highest `total_engagement`; ties are resolved by lexicographic `source_folder`. All duplicate source rows are preserved in `data/diagnostics/fortune100_duplicate_tweet_audit.csv`.

## Humor Variables

The first source is existing model-based full-chain classification in `data/derived/humor/full_chain/humor_full_chain_master.csv`. The script does not run new model inference. Posts without an existing classification are marked `classification_missing_no_new_inference`.

Human-coded labels are not used as the main H1/H2/H3 evidence. They remain supplemental validation evidence only.

## Firm-Period Variables

The panel uses firm-month as the first candidate period because the raw Fortune collection spans observable post histories and many firms have enough posts for month aggregation. If the generated coverage diagnostics show insufficient monthly density, H3 should be downgraded to readiness or exploratory analysis before regression execution.

`aggressive_humor_usage_intensity` is operationalized as firm-period aggressive humor usage rate:

```text
aggressive_humor_usage_intensity = aggressive_humor_post_count / post_count
aggressive_humor_usage_intensity_sq = aggressive_humor_usage_intensity^2
```

This is a usage rate, not message-level semantic intensity.
