# Data Dictionary — H1/H2/H3 Simple OLS Analysis

## Input Files

### H1 Analysis Corpus

**File**: `20260618expand/classifier_improvement/h1_presence_only/full_corpus_classification/data/fortune100_h1_presence_classified_posts.csv`  
**Rows**: 65,245  
**Population**: Fortune 100 company Twitter/X posts (excludes Wendy's legacy, MoonPie, Coca-Cola)

| Column | Type | Used In | Description |
|---|---|---|---|
| `tweet_id` | str | join key | Unique post identifier |
| `company_name` | str | H3 groupby | Company name (97 companies in corpus) |
| `fortune_rank` | int | — | Fortune 100 rank (1–100) |
| `created_at` | str | — | Post timestamp (format: `Thu Jun 05 10:55:42 +0000 2025`) |
| `total_engagement` | float | H1 DV, H3 DV | like + repost + reply + quote count (0 if missing) |
| `log_total_engagement` | float | — | log1p(total_engagement) pre-computed |
| `text_length` | int | H1 control | Character length of post text |
| `hashtag_count` | int | H1 control | Number of hashtags in text |
| `mention_count` | int | H1 control | Number of @mentions in text |
| `h1_humor_presence_pred_t50` | int (0/1) | **H1 IV** | **PREDICTED** humor presence at threshold 0.50 |
| `h1_humor_presence_probability` | float | — | Raw classifier probability (not used in OLS) |
| `h1_humor_presence_pred_t40` | int (0/1) | — | Alternative threshold (not used in main analysis) |
| `h1_humor_presence_pred_t60` | int (0/1) | — | Alternative threshold (not used in main analysis) |
| `missing_text` | bool/str | filter | Posts with missing text excluded |
| `h1_classifier_model` | str | provenance | Model name (`word_char_comb__lr_liblin_C01`) |
| `h1_classifier_training_scope` | str | provenance | Training data scope |
| `h1_classifier_status` | str | provenance | Classifier deployment status |

**Important notes**:
- `h1_humor_presence_pred_t50` is a MODEL-PREDICTED label, NOT human ground truth
- Using predicted IV introduces measurement error bias into H1 OLS estimates
- H1 OLS results should be treated as preliminary pending H1 classifier validation

### H2/H3 Type Training Data

**File**: `20260618expand/classifier_improvement/humor_type_leakage_filtered/data/type_training_leakage_filtered_variants.csv`  
**Subset used**: `source == "batch1_fortune100"` only (excludes `wendys_human_type`)  
**Rows (subset)**: 648

| Column | Type | Used In | Description |
|---|---|---|---|
| `row_id` | str | — | Internal row identifier |
| `source` | str | filter | `batch1_fortune100` (used) or `wendys_human_type` (excluded) |
| `company_name` | str | H3 groupby | Company name (88 unique firms) |
| `tweet_id` | str | join key | Joins with H1 corpus for engagement data |
| `humor_type` | str | **H2 IV, H3 IV** | **HUMAN-CODED** type label: aggressive / affiliative / self-enhancing / self-defeating |
| `humor_presence_binary` | int | filter | 1 = humor (all 648 rows) |
| `text_original` | str | — | Original tweet text (not used in OLS) |
| `created_at` | str | — | Post timestamp |

**Type label distribution (batch1_fortune100 only)**:
- affiliative: 321 (49.5%)
- self-enhancing: 259 (40.0%)
- aggressive: 44 (6.8%)
- self-defeating: 24 (3.7%)

**Important notes**:
- These are HUMAN-CODED labels — coder1-priority scheme applied
- batch1 type labels cover ONLY humor-positive posts from the labeled sample
- 648 is NOT a random sample of Fortune 100 humor posts

---

## Output Files

### `h1_simple_ols_results.csv`

| Column | Description |
|---|---|
| `hypothesis` | "H1" |
| `model_name` | H1_simple / H1_simple_controls |
| `dependent_variable` | log1p_total_engagement |
| `feature` | Coefficient name (intercept, humor_presence_pred_t50, etc.) |
| `coefficient` | OLS coefficient (β) |
| `robust_se` | HC3 heteroskedasticity-robust standard error |
| `se_type` | "HC3" |
| `t_stat` | t-statistic (coefficient / robust_se) |
| `p_value` | Two-sided p-value |
| `p_stars` | *** p<.01 / ** p<.05 / * p<.10 |
| `n_obs` | Sample size |
| `k_params` | Number of parameters |
| `r_squared` | OLS R² |
| `r_squared_adj` | Adjusted R² |
| `sample_definition` | Sample description |
| `controls` | Control variables included |
| `label_source` | How the IV was generated |
| `label_source_warning` | Measurement limitation note |
| `interpretation_level` | preliminary_diagnostic |

### `h2_aggressive_vs_other_simple_ols_results.csv`

Same structure as H1. Key columns:
- `feature`: intercept / aggressive_vs_other / controls
- `n_aggressive`: count of aggressive posts in sample
- `n_other`: count of non-aggressive humor posts

### `h2_four_type_simple_ols_results.csv`

Same structure. Additional columns:
- `reference_category`: "affiliative" (omitted category)
- `n_aggressive`, `n_affiliative`, `n_self_enhancing`, `n_self_defeating`
- `mean_log_eng_*`: per-type mean log1p engagement
- Includes pairwise mean comparison rows (model_name contains "pairwise")

### `h3_intensity_simple_ols_results.csv`

Same structure. Additional columns:
- `turning_point`: -b1/(2*b2) from quadratic model
- `turning_point_in_range`: whether turning point falls within observed intensity range
- `inverted_u_check`: pattern description (b1>0 AND b2<0, etc.)
- `intensity_range`: min-max of aggressive_intensity across firms
- `n_firms_with_aggressive`: count of firms with intensity > 0
- `not_interpretable_reason`: explanation if interpretation_level = NOT_INTERPRETABLE

### `hypothesis_ols_summary.csv`

One row per hypothesis (H1, H2_1, H2_2, H3). Key columns:
- `focal_independent_variable`: main coefficient of interest
- `preliminary_verdict`: preliminary_supported / mixed / NOT_INTERPRETABLE

### `hypothesis_ols_interpretation.md`

Full interpretation in Korean. Covers data, results, limitations, and next steps.

### `data_dictionary.md`

This file.

---

## Derived Variables

### H1 DV: `log1p_total_engagement`
- Computed as: `math.log1p(float(total_engagement))`
- Rationale: total_engagement is right-skewed (mean=750, median=23); log1p compresses extreme outliers

### H2 IV: `aggressive_vs_other`
- Computed as: 1 if `humor_type == "aggressive"` else 0
- Reference group: affiliative + self-enhancing + self-defeating

### H2 IV: dummy variables for four-type model
- `aggressive`: 1 if humor_type == "aggressive" else 0
- `self_enhancing`: 1 if humor_type == "self-enhancing" else 0
- `self_defeating`: 1 if humor_type == "self-defeating" else 0
- Reference (omitted): affiliative

### H3 IV: `aggressive_intensity`
- Computed as: `n_aggressive_humor_posts / n_total_humor_posts` per firm
- Denominator: total humor-positive posts in batch1 type-labeled sample (NOT all firm posts)
- **Limitation**: This intensity reflects the batch1 labeled sample composition, not true firm-wide strategy

### H3 DV: `firm_mean_log1p_engagement`
- Computed as: mean of log1p(total_engagement) across all Fortune100 corpus posts per firm
- Based on full corpus (all firm posts, not just labeled subset)

---

## Join Logic (H2/H3 Engagement)

`type_training_leakage_filtered_variants.csv` batch1_fortune100 rows are joined with `fortune100_h1_presence_classified_posts.csv` on `tweet_id`.  
All 648 batch1 type-labeled posts are present in the Fortune100 corpus (100% match rate).

---

## Excluded Data

| Dataset | n | Reason |
|---|---|---|
| `wendys_human_type` rows in type training | 278 | Wendy's-only; excluded per analysis scope |
| `wendys_legacy` posts in integrated corpus | 977 | Legacy data; not in fortune100 classified posts |
| `moonpie_legacy` posts | 930 | Not Fortune 100 |
| `cocacola_legacy` posts | 708 | Not Fortune 100 |
| 564 model-predicted type rows | 564 | NOT used as training labels; never included in H2/H3 analysis |

---

*Last updated*: 2026-06-18  
*Script*: `run_simple_ols_hypotheses.py`
