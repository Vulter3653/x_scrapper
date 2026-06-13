# Humor Classification Input Dataset

## Dataset Purpose
This dataset is a consolidated input for zero-shot humor classification. It combines Fortune 2025 Top 100 corporate X posts with known humor benchmarks.

## Source Data
- **Fortune 2025 Top 100 Ranked**: Corporate posts collected via browser-based scraping.
- **Wendy's**: Benchmark for aggressive humor (source: data/wendys/posts.json).
- **MoonPie**: Benchmark for self-defeating/affiliative humor (source: data/moonpie/posts.json).

## Sample Groups
- `fortune_top100_ranked`: Main target group for analysis.
- `benchmark_aggressive_wendys`: Reference for aggressive humor style.
- `benchmark_self_defeating_moonpie`: Reference for self-defeating/niche humor style.

## Metadata
- `classification_status`: All entries are currently marked as `pending`.
- `global_post_id`: Unique identifier across all sample groups.
- `is_duplicate_removed`: Set to `true` as deduplication was performed by `tweet_id` within each sample group.

## Note
Zero-shot classification has **not** yet been executed on this dataset.
