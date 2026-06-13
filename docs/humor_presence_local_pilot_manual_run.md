# Manual Run Guide: 800-Row Local Humor Presence Pilot

This guide explains how to manually run the 800-row diagnostic pilot for the local humor presence classifier using GitHub Actions.

## 1. Workflow Name
In the GitHub Actions tab, select:
**"Run Local Humor Presence Pilot"**

## 2. workflow_dispatch Inputs
When clicking "Run workflow", use the following default or recommended values:

- **pilot_rows**: `800`
- **shard_size**: `200`
- **max_parallel**: `4`
- **humor_threshold**: `0.70`
- **non_humor_threshold**: `0.30`
- **classifier_version**: `local-pilot-v1-github-actions`

## 3. Before Running
- Ensure all recent changes to `config/humor_presence_rule_cues.json` and `scripts/classify_humor_presence_local.py` have been pushed to the `main` branch.
- Verify that the training seed data (Wendy's and MoonPie HSQ results) is present in the repository.

## 4. Steps to Monitor
Monitor the following jobs in the GitHub Actions UI:
1. **plan-local-pilot-shards**: Splits the 800 rows into 4 shards.
2. **classify-local-pilot-shards**: Runs the local classifier on each shard in parallel.
3. **aggregate-local-pilot-results**: Merges the shard outputs into a single CSV.
4. **evaluate-local-pilot-results**: Generates metrics, audit summaries, and review samples.

## 5. Success Criteria
The run is successful if:
- All jobs complete with a "Success" status.
- **input rows** = 800
- **output rows** = 800
- **failed rows** = 0
- Artifacts are generated and available for download.

## 6. Artifacts to Check
Download the following artifacts:
- **humor-presence-local-pilot-evaluation**: Contains:
  - `data/audit/humor_presence_local_pilot_audit_summary.csv`
  - `data/audit/humor_presence_local_pilot_ambiguous_diagnosis.csv`
  - `data/audit/humor_presence_local_pilot_review_sample.csv`
- **humor-presence-local-pilot-aggregated**: The full results file.

## 7. Important Restrictions
- **DO NOT** perform a full run (55,788 rows) yet.
- **DO NOT** attempt HSQ 4-type classification.
- **DO NOT** update the dashboard with these results.
- These results are for **diagnostic purposes only**.

## 8. Feedback to Gemini
After the run completes, please provide the following information to Gemini:

1. **Workflow Run URL**: (e.g., `https://github.com/Vulter3653/x_scrapper/actions/runs/...`)
2. **Run Status**: (Success/Failure)
3. **Total Run Time**: (e.g., 2m 45s)
4. **Input/Output Row Counts**: (e.g., 800/800)
5. **Failed Rows**: (e.g., 0)
6. **Humor/Non-humor/Ambiguous Counts**: (e.g., 50/150/600)
7. **Mean/Median Confidence**: (e.g., 0.58/0.55)
8. **Top Review Bucket Observations**: (Optional, after looking at the review sample)
9. **Any Error/Warning Logs**: (Paste snippet if applicable)
