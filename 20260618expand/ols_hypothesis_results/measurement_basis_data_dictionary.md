# Measurement Basis Data Dictionary — Two-Basis Plain OLS Analysis

**SE type**: Classical OLS (s²×(X'X)⁻¹) — NOT HC3/robust

---

## Measurement Basis A: Batch1 Human-coded

### H1 Input
**File**: `fortune100_human_labeling_template.csv`
**Rows used**: 1,482 (excluded 18 rows with human_humor_presence=2 [ambiguous])

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | join key | — |
| `company_name` | H3 groupby | 97 unique companies |
| `total_engagement` | DV source | log1p() applied |
| `human_humor_presence` | **H1 IV** | 0=non-humor, 1=humor; HUMAN-CODED |
| `text` | control source | text_length, hashtag_count, mention_count computed here |

**Distribution**: humor=648 / non-humor=834

### H2/H3 Input
**File**: `type_training_leakage_filtered_variants.csv` (batch1_fortune100 only)
**Rows**: 648 (all humor-positive)
**Engagement join**: `fortune100_h1_presence_classified_posts.csv` on `tweet_id` (100% match)

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | join key | — |
| `company_name` | H3 firm groupby | 88 unique firms |
| `humor_type` | **H2/H3 IV** | aggressive/affiliative/self-enhancing/self-defeating; HUMAN-CODED |
| `total_engagement` | DV (via join) | from fortune100_h1_presence_classified_posts.csv |

**Type distribution**: affiliative=321, self-enhancing=259, aggressive=44, self-defeating=24

### H3 Intensity Construction (Batch1)
- `aggressive_intensity = n_aggressive / n_humor` per firm (from 648 labeled posts)
- DV: firm-level mean log1p(total_engagement) from batch1 labeled posts
- Analysis unit: **firm-level** (88 firms)
- WARNING: intensity based on small labeled sample per firm → unstable estimates

---

## Measurement Basis B: Full-sample Classifier-predicted

### H1 Full Input
**File**: `integrated_h1_presence_classified_posts.csv`
**Rows**: 68,039

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | identifier | — |
| `company_name` | — | 99 unique companies |
| `source_dataset` | stratification | fortune100/wendys_legacy/moonpie_legacy/cocacola_legacy/fortune100_raw_append |
| `total_engagement` | DV source | log1p() applied |
| `log_total_engagement` | DV alt | pre-computed log1p |
| `h1_humor_presence_pred_t50` | **H1 IV** | PREDICTED at threshold 0.50; model=word_char_comb__lr_liblin_C01 |
| `text_length` | control | pre-computed |
| `hashtag_count` | control | pre-computed |
| `mention_count` | control | pre-computed |

**Source breakdown**: fortune100=65,245 / wendys_legacy=977 / moonpie_legacy=930 / cocacola_legacy=708 / fortune100_raw_append=179

### H2 Full Input
**File**: `h2_post_level_regression_ready.csv` (model_transfer pipeline)
**Rows total**: 65,245 / **Humor rows used**: 28,177 (humor_type != non_humorous)

| Column | Role | Notes |
|---|---|---|
| `tweet_id` | identifier | — |
| `company_name` | H3 groupby | 97 unique companies |
| `log_total_engagement` | DV | pre-computed |
| `humor_type` | type label | PREDICTED by Wendy's model transfer |
| `aggressive_humor` | H2 IV (0/1) | PREDICTED dummy |
| `affiliative_humor` | reference (0/1) | PREDICTED dummy |
| `self_enhancing_humor` | H2 IV (0/1) | PREDICTED dummy |
| `self_defeating_humor` | H2 IV (0/1) | PREDICTED dummy |
| `text_length` | control | pre-computed |
| `hashtag_count` | control | pre-computed |
| `mention_count` | control | pre-computed |

**CRITICAL**: classifier_status=NOT_A_CANDIDATE; source-shortcut leakage (#NationalRoastDay) confirmed

### H3 Full Intensity Construction
- `predicted_aggressive_intensity = n_pred_aggressive / n_pred_humor` per firm
- DV: firm-level mean log1p(total_engagement) from predicted humor posts
- Analysis unit: **firm-level** (97 firms)

**Predicted type distribution** (humor posts only):
- affiliative: 19,101
- aggressive: 6,857
- self-enhancing: 1,994
- self-defeating: 225

---

## Output Files

| File | Contents |
|---|---|
| `h1_batch1_human_coded_plain_ols_results.csv` | H1 OLS (batch1, classical SE) |
| `h1_full_sample_predicted_plain_ols_results.csv` | H1 OLS (full predicted, classical SE) |
| `h2_1_batch1_human_coded_aggressive_vs_other_plain_ols_results.csv` | H2-1 batch1 |
| `h2_2_batch1_human_coded_four_type_plain_ols_results.csv` | H2-2 batch1 |
| `h2_1_full_sample_predicted_aggressive_vs_other_plain_ols_results.csv` | H2-1 full predicted |
| `h2_2_full_sample_predicted_four_type_plain_ols_results.csv` | H2-2 full predicted |
| `h3_batch1_human_coded_intensity_plain_ols_results.csv` | H3 quadratic batch1 |
| `h3_batch1_human_coded_intensity_distribution.csv` | Firm-level intensity (batch1) |
| `h3_full_sample_predicted_intensity_plain_ols_results.csv` | H3 quadratic full predicted |
| `h3_full_sample_predicted_intensity_distribution.csv` | Firm-level intensity (full predicted) |
| `hypothesis_plain_ols_two_basis_summary.csv` | One row per model × basis summary |
| `hypothesis_plain_ols_two_basis_interpretation.md` | Korean interpretation |
| `measurement_basis_sample_attrition.csv` | Attrition steps per basis × hypothesis |
| `measurement_basis_data_dictionary.md` | This file |
| `run_two_basis_plain_ols_hypotheses.py` | Generating script |

---

## SE Type

Classical OLS SE: `s² = SSR/(n-k)`, `Var(β̂) = s²·(X'X)⁻¹`, `SE = √diag(Var(β̂))`
**HC3, HC1, clustered SE are NOT used in any main result.**

---

*Last updated*: 2026-06-19
*Script*: `run_two_basis_plain_ols_hypotheses.py`
