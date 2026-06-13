# Manual Run Guide: 800-Row Local Humor Presence Pilot

This guide explains how to manually run the 800-row diagnostic pilot for the local humor presence classifier using GitHub Actions.

## 1. Workflow Name

In the GitHub Actions tab, select:

**Run Local Humor Presence Pilot**

## 2. workflow_dispatch Inputs

Use the default values unless you are deliberately testing a threshold variant.

- **pilot_rows**: `800`
- **shard_size**: `200`
- **max_parallel**: `4`
- **humor_threshold**: `0.70`
- **non_humor_threshold**: `0.30`
- **classifier_version**: `local-pilot-v2-integrity`

## 3. What Changed in the Integrity Repair

The prior pilot produced successful jobs but only `441/800` output rows. The likely cause was shell-based CSV sharding with `sed`, which can corrupt records when post text contains embedded newlines. The repaired workflow uses a single centrally generated pilot sample and CSV-aware record sharding.

The repaired workflow now enforces:

1. one shared pilot input artifact for all shards;
2. CSV-aware sharding via `scripts/shard_csv_records.py`;
3. sample/result row-count validation;
4. allowed `sample_group` whitelist validation;
5. workflow failure if `output_rows != input_rows`;
6. integrity audit artifact upload.

Allowed sample groups:

- `benchmark_aggressive_wendys`
- `benchmark_self_defeating_moonpie`
- `fortune_top100_ranked`

## 4. Jobs to Monitor

1. **build-local-pilot-inputs**
   - builds training seed;
   - builds one 800-row pilot sample;
   - writes a sample manifest;
   - uploads `humor-presence-local-pilot-inputs`.

2. **classify-local-pilot-shards**
   - downloads the shared pilot input artifact;
   - creates CSV-aware record shards;
   - classifies each shard.

3. **aggregate-local-pilot-results**
   - merges shard outputs;
   - validates sample/result integrity;
   - uploads aggregated results and integrity audit.

4. **evaluate-local-pilot-results**
   - evaluates the aggregated output;
   - fails under `--strict-integrity` if row count, failed rows, or sample groups are invalid.

## 5. Success Criteria

The run is successful only if:

- all jobs complete with success;
- `input_rows = 800`;
- `output_rows = 800`;
- `failed_rows = 0`;
- `integrity_pass = true`;
- no invalid `sample_group` values appear;
- artifacts are generated.

## 6. Artifacts to Check

- **humor-presence-local-pilot-inputs**
  - `humor_presence_training_seed.csv`
  - `humor_presence_local_pilot_sample.csv`
  - `humor_presence_local_pilot_manifest.json`

- **humor-presence-local-pilot-aggregated**
  - `humor_presence_local_pilot_results.csv`

- **humor-presence-local-pilot-integrity**
  - `humor_presence_local_pilot_integrity_audit.csv`

- **humor-presence-local-pilot-evaluation**
  - `humor_presence_local_pilot_audit_summary.csv`
  - `humor_presence_local_pilot_ambiguous_diagnosis.csv`
  - `humor_presence_local_pilot_review_sample.csv`

## 7. Restrictions

Do not run:

- 55,788-row full classification;
- HSQ 4-type classification;
- humor intensity generation;
- dashboard sync.

This pilot is still diagnostic only.

## 8. Information to Report After Running

Provide:

1. Workflow Run URL
2. Run Status
3. Total Run Time
4. `input_rows / output_rows`
5. `failed_rows`
6. `integrity_pass`
7. Humor / Non-humor / Ambiguous counts
8. Rule coverage rate
9. ML decisive rate
10. Mean / median confidence
11. Any invalid sample group or row-count warning
