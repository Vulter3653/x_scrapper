# Limitations And Claim Boundaries

- The result is limited to already collected observable X posts in this repository.
- It is not the full X historical archive.
- Engagement metrics are point-in-time captures from the collection moment.
- Humor classification is a model-based estimate.
- Human-coded labels are validation or supplemental evidence only, not the main H1/H2/H3 result.
- Account mapping should use the human final fields in `config/fortune2025_x_account_verification_master.csv`.
- The analysis is observational evidence. It does not support unrestricted causal claims.
- Dashboard descriptive evidence and the hypothesis-testing datasets must remain separate.
- Existing `20260615wendy's/`, `data/analysis/`, `dashboard/data/`, and raw Fortune collection files are not overwritten by this package.
- Current Fortune Top 100 collected data contain only 95 aggressive humor posts, approximately 0.15% of the deduplicated post-level sample. At the firm-month level, only 84 out of 3,532 firm-month rows have aggressive_humor_usage_intensity greater than zero. Therefore, H3 is not treated as confirmatory inverted-U evidence. It is reported only as exploratory/readiness evidence.
- Ambiguous humor_presence rows account for 31,456 posts, or 48.2% of the post-level sample. The aggressive_humor_usage_intensity denominator includes these ambiguous posts, making it a conservative lower-bound measure.
- The Fortune Top 100 expansion DV (total_engagement) excludes bookmark_count. The Wendy's-only analysis in `20260615wendy's/` may include bookmark_count. Direct coefficient comparison between the two analyses is not appropriate without accounting for this DV difference.
