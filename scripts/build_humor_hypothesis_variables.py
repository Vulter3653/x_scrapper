#!/usr/bin/env python3
"""Build hypothesis-ready humor variables for H1-H3 regression analysis.

Aggregates v1 full-chain classification results to firm-period (company × YYYY-MM)
level and constructs regression-ready variables for testing:

  H1: Brand SNS humor presence/usage → Brand Equity (positive)
  H2: Aggressive humor type has a larger effect on Brand Equity than other types
  H3: Aggressive humor usage intensity moderates the aggressive→Brand Equity
      relationship in an inverted-U shape (intensity is firm-level share/frequency)

CONSTRAINTS (enforced throughout):
  - Uses only v1 full-chain operational labels. No v2 production reclassification.
  - Does not create human_label, gold_label, coder_label, or adjudicated_label.
  - Does not treat v1-v2 consensus as ground truth.
  - Does not modify raw data or full-chain outputs.
  - v2 outputs are used only as company-level disagreement / candidate flags.
  - No classification is run here; only aggregation and variable construction.

Inputs:
  data/derived/humor/full_chain/humor_full_chain_master.csv
  data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv
  data/audit/humor/evaluation/humor_type_v1_v2_summary.json
  data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv

Outputs:
  data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv
  data/derived/humor/hypothesis_variables/humor_h1_variables.csv
  data/derived/humor/hypothesis_variables/humor_h2_type_variables.csv
  data/derived/humor/hypothesis_variables/humor_h3_intensity_variables.csv
  data/derived/humor/hypothesis_variables/humor_variable_dictionary.csv
  data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MASTER      = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
DEFAULT_COMPARISON  = Path("data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv")
DEFAULT_AB_SUMMARY  = Path("data/audit/humor/evaluation/humor_type_v1_v2_summary.json")
DEFAULT_PRIORITY    = Path("data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv")

DEFAULT_OUT_FULL    = Path("data/derived/humor/hypothesis_variables/humor_firm_period_hypothesis_variables.csv")
DEFAULT_OUT_H1      = Path("data/derived/humor/hypothesis_variables/humor_h1_variables.csv")
DEFAULT_OUT_H2      = Path("data/derived/humor/hypothesis_variables/humor_h2_type_variables.csv")
DEFAULT_OUT_H3      = Path("data/derived/humor/hypothesis_variables/humor_h3_intensity_variables.csv")
DEFAULT_OUT_DICT    = Path("data/derived/humor/hypothesis_variables/humor_variable_dictionary.csv")
DEFAULT_OUT_MANIFEST = Path("data/audit/humor/hypothesis_variables/humor_hypothesis_variables_manifest.json")

# Ambiguity rate above this → high_ambiguity_flag=1 and humor_share_ambiguity_as_missing=NA
HIGH_AMBIGUITY_THRESHOLD = 0.50

# ---------------------------------------------------------------------------
# Output column schemas
# ---------------------------------------------------------------------------
FULL_FIELDS = [
    "company_name", "period",
    # Handle collapse metadata (source_x_handle collapsed across all handles per company-period)
    "source_x_handle_count", "source_x_handle_list",
    # Presence counts
    "total_posts", "humor_count", "non_humor_count", "ambiguous_count", "ambiguity_rate",
    # H1 variables
    "humor_share", "humor_share_ambiguity_as_zero", "humor_share_ambiguity_excluded",
    "humor_share_ambiguity_as_missing", "log_humor_count", "humor_presence_any",
    # H2 type variables
    "affiliative_count", "self_enhancing_count", "aggressive_count", "self_defeating_count",
    "affiliative_share", "self_enhancing_share", "aggressive_share", "self_defeating_share",
    "rare_negative_humor_count", "rare_negative_humor_share", "aggressive_minus_other_humor_share",
    # H3 intensity variables
    "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
    "log_aggressive_count", "aggressive_presence_any", "aggressive_share_ambiguity_excluded",
    "rare_negative_humor_usage_intensity", "rare_negative_humor_usage_intensity_sq",
    # H3 interaction terms
    "humor_share_x_aggressive_intensity", "humor_share_x_aggressive_intensity_sq",
    "aggressive_presence_x_aggressive_intensity", "aggressive_presence_x_aggressive_intensity_sq",
    # v2 candidate flags (company-level, not period-level)
    "v2_aggressive_candidate_count", "v1_v2_disagreement_candidate_count", "rare_class_candidate_count",
    # Diagnostic flags
    "high_ambiguity_flag", "no_human_label_flag",
]

H1_FIELDS = [
    "company_name", "period", "source_x_handle_count", "source_x_handle_list", "total_posts",
    "humor_count", "humor_share", "log_humor_count", "humor_presence_any",
    "humor_share_ambiguity_as_zero", "humor_share_ambiguity_excluded",
    "humor_share_ambiguity_as_missing", "ambiguity_rate", "high_ambiguity_flag",
]

H2_FIELDS = [
    "company_name", "period", "source_x_handle_count", "source_x_handle_list", "total_posts",
    "affiliative_count", "self_enhancing_count", "aggressive_count", "self_defeating_count",
    "affiliative_share", "self_enhancing_share", "aggressive_share", "self_defeating_share",
    "aggressive_minus_other_humor_share",
    "rare_negative_humor_count", "rare_negative_humor_share",
    "v2_aggressive_candidate_count", "v1_v2_disagreement_candidate_count", "rare_class_candidate_count",
]

H3_FIELDS = [
    "company_name", "period", "source_x_handle_count", "source_x_handle_list", "total_posts",
    "aggressive_count", "aggressive_share",
    "aggressive_humor_usage_intensity", "aggressive_humor_usage_intensity_sq",
    "log_aggressive_count", "aggressive_presence_any", "aggressive_share_ambiguity_excluded",
    "rare_negative_humor_usage_intensity", "rare_negative_humor_usage_intensity_sq",
    "humor_share_x_aggressive_intensity", "humor_share_x_aggressive_intensity_sq",
    "aggressive_presence_x_aggressive_intensity", "aggressive_presence_x_aggressive_intensity_sq",
    "ambiguity_rate", "high_ambiguity_flag",
]

DICT_FIELDS = [
    "variable_name", "hypothesis", "construct", "role",
    "numerator", "denominator", "formula",
    "ambiguity_handling", "interpretation", "limitation", "no_human_label_warning",
]

# ---------------------------------------------------------------------------
# Variable dictionary
# ---------------------------------------------------------------------------
VARIABLE_DICTIONARY = [
    # --- Counts ---
    {
        "variable_name": "total_posts",
        "hypothesis": "Diagnostic",
        "construct": "Firm posting volume",
        "role": "Control / Denominator",
        "numerator": "All rows for firm-period",
        "denominator": "1",
        "formula": "COUNT(rows)",
        "ambiguity_handling": "All posts included",
        "interpretation": "Total number of posts by firm in the period. Used as denominator for share variables.",
        "limitation": "Does not distinguish collected vs. organic posts.",
        "no_human_label_warning": "Not dependent on humor labels.",
    },
    {
        "variable_name": "humor_count",
        "hypothesis": "H1",
        "construct": "Humor usage volume",
        "role": "IV (raw count)",
        "numerator": "Rows where humor_presence == 'humor'",
        "denominator": "1",
        "formula": "COUNT(humor_presence == 'humor')",
        "ambiguity_handling": "Ambiguous posts NOT counted as humor (conservative)",
        "interpretation": "Number of humor posts in firm-period. Raw count; use log_humor_count for regression.",
        "limitation": "v1 operational label only. No human validation. Ambiguous posts excluded from humor.",
        "no_human_label_warning": "Counts v1 labels only. ~48% of posts are ambiguous_or_review; true humor count may differ after human review.",
    },
    {
        "variable_name": "non_humor_count",
        "hypothesis": "Diagnostic",
        "construct": "Non-humor posting volume",
        "role": "Diagnostic",
        "numerator": "Rows where humor_presence == 'non_humor'",
        "denominator": "1",
        "formula": "COUNT(humor_presence == 'non_humor')",
        "ambiguity_handling": "Ambiguous posts NOT included",
        "interpretation": "Confirmed non-humor posts.",
        "limitation": "v1 operational label only.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "ambiguous_count",
        "hypothesis": "Diagnostic",
        "construct": "Classification uncertainty",
        "role": "Diagnostic / Robustness",
        "numerator": "Rows where humor_presence == 'ambiguous'",
        "denominator": "1",
        "formula": "COUNT(humor_presence == 'ambiguous')",
        "ambiguity_handling": "These ARE the ambiguous rows",
        "interpretation": "Posts where humor presence could not be determined by v1 pipeline.",
        "limitation": "High ambiguous_count signals measurement uncertainty for that firm-period.",
        "no_human_label_warning": "Human review of ambiguous rows would reduce this count.",
    },
    {
        "variable_name": "ambiguity_rate",
        "hypothesis": "Diagnostic",
        "construct": "Measurement uncertainty rate",
        "role": "Diagnostic / Robustness",
        "numerator": "ambiguous_count",
        "denominator": "total_posts",
        "formula": "ambiguous_count / total_posts",
        "ambiguity_handling": "Measures the ambiguity burden",
        "interpretation": "Share of posts that could not be classified. Used to flag unreliable firm-periods.",
        "limitation": "Firm-periods with ambiguity_rate >= 0.50 are flagged as high_ambiguity.",
        "no_human_label_warning": "Ambiguity is a v1 pipeline artifact. Human labels would resolve many of these.",
    },
    # --- H1 variables ---
    {
        "variable_name": "humor_share",
        "hypothesis": "H1",
        "construct": "Humor usage intensity (primary)",
        "role": "IV",
        "numerator": "humor_count",
        "denominator": "total_posts",
        "formula": "humor_count / total_posts",
        "ambiguity_handling": "conservative: ambiguous treated as non-humor (not counted in numerator)",
        "interpretation": "Primary H1 IV. Share of firm's posts that are humor. Ambiguous posts counted in denominator but not numerator.",
        "limitation": "Conservative estimate; true humor share likely higher if ambiguous posts were resolved.",
        "no_human_label_warning": "v1 label. ~48% of posts unresolved (ambiguous). Treat as lower bound on true humor share.",
    },
    {
        "variable_name": "humor_share_ambiguity_as_zero",
        "hypothesis": "H1",
        "construct": "Humor usage intensity (robustness: ambiguous=0)",
        "role": "IV (Robustness)",
        "numerator": "humor_count",
        "denominator": "total_posts",
        "formula": "humor_count / total_posts",
        "ambiguity_handling": "ambiguity_as_zero: ambiguous posts contribute 0 to numerator, 1 to denominator",
        "interpretation": "Identical to humor_share. Explicit robustness label for regressions treating ambiguous as non-humor.",
        "limitation": "Same as humor_share. Kept separately to allow explicit sensitivity labeling in regression tables.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "humor_share_ambiguity_excluded",
        "hypothesis": "H1",
        "construct": "Humor usage intensity (robustness: ambiguous excluded)",
        "role": "IV (Robustness)",
        "numerator": "humor_count",
        "denominator": "humor_count + non_humor_count",
        "formula": "humor_count / (humor_count + non_humor_count)",
        "ambiguity_handling": "ambiguity_excluded: ambiguous posts removed from both numerator and denominator",
        "interpretation": "Among posts that were unambiguously classified, share that are humor. NA if denominator == 0.",
        "limitation": "Denominator shrinks with high ambiguity. Not comparable across firms with very different ambiguity rates.",
        "no_human_label_warning": "v1 label only. Excludes unresolved rows.",
    },
    {
        "variable_name": "humor_share_ambiguity_as_missing",
        "hypothesis": "H1",
        "construct": "Humor usage intensity (robustness: high-ambiguity flagged)",
        "role": "IV (Robustness)",
        "numerator": "humor_count (if ambiguity_rate < 0.50)",
        "denominator": "total_posts (if ambiguity_rate < 0.50)",
        "formula": "IF ambiguity_rate < 0.50 THEN humor_count/total_posts ELSE NA",
        "ambiguity_handling": "ambiguity_as_missing: firm-period flagged as NA if ambiguity_rate >= 0.50",
        "interpretation": "humor_share restricted to firm-periods where ambiguity is below 50%. NA otherwise.",
        "limitation": "Results in listwise deletion of high-ambiguity firm-periods. May bias sample.",
        "no_human_label_warning": "NA values represent measurement uncertainty, not true absence of humor.",
    },
    {
        "variable_name": "log_humor_count",
        "hypothesis": "H1",
        "construct": "Humor posting frequency (logged)",
        "role": "IV (log-transformed)",
        "numerator": "1 + humor_count",
        "denominator": "1",
        "formula": "log(1 + humor_count)",
        "ambiguity_handling": "conservative: ambiguous not counted as humor",
        "interpretation": "Natural log of (1 + humor_count). Addresses right-skew in count data. Use in Poisson or log-transformed OLS.",
        "limitation": "log(1) = 0 for firms with zero humor. Consider zero-inflated models if zero-humor firm-periods are common.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "humor_presence_any",
        "hypothesis": "H1",
        "construct": "Humor adoption (binary)",
        "role": "IV (binary)",
        "numerator": "1 if humor_count > 0",
        "denominator": "1",
        "formula": "1 if humor_count > 0 else 0",
        "ambiguity_handling": "conservative",
        "interpretation": "Binary indicator: 1 if firm posted at least one humor post in period. Use for treatment-effect framing.",
        "limitation": "Loses information about volume. Useful for DiD or propensity-score designs.",
        "no_human_label_warning": "v1 label only.",
    },
    # --- H2 variables ---
    {
        "variable_name": "affiliative_count",
        "hypothesis": "H2",
        "construct": "Affiliative humor volume",
        "role": "IV",
        "numerator": "Rows where humor_type == 'affiliative'",
        "denominator": "1",
        "formula": "COUNT(humor_type == 'affiliative')",
        "ambiguity_handling": "Only confirmed humor rows are typed; ambiguous_or_review excluded",
        "interpretation": "Number of affiliative (inclusive, bonding) humor posts. Subset of humor_count.",
        "limitation": "v1 label. Ambiguous rows not typed. May undercount true affiliative posts.",
        "no_human_label_warning": "v1 operational label only. No human validation of type assignment.",
    },
    {
        "variable_name": "self_enhancing_count",
        "hypothesis": "H2",
        "construct": "Self-enhancing humor volume",
        "role": "IV",
        "numerator": "Rows where humor_type == 'self_enhancing'",
        "denominator": "1",
        "formula": "COUNT(humor_type == 'self_enhancing')",
        "ambiguity_handling": "Only confirmed humor rows typed",
        "interpretation": "Brand laughing at itself in a confident, positive way.",
        "limitation": "v1 label only.",
        "no_human_label_warning": "v1 operational label only.",
    },
    {
        "variable_name": "aggressive_count",
        "hypothesis": "H2, H3",
        "construct": "Aggressive humor volume",
        "role": "IV (H2) / Key variable (H3)",
        "numerator": "Rows where humor_type == 'aggressive'",
        "denominator": "1",
        "formula": "COUNT(humor_type == 'aggressive')",
        "ambiguity_handling": "Only confirmed humor rows typed",
        "interpretation": "Humor that ridicules or takes competitive shots at an external target. Rare class in v1 (105/68k).",
        "limitation": "Rare class: 105 rows in 68k. No human validation. v1 may undercount due to conservative cues.",
        "no_human_label_warning": "EXPLORATORY ONLY. aggressive_count is v1 operational label with no human validation. Treat as lower-bound estimate.",
    },
    {
        "variable_name": "self_defeating_count",
        "hypothesis": "H2",
        "construct": "Self-defeating humor volume",
        "role": "IV",
        "numerator": "Rows where humor_type == 'self_defeating'",
        "denominator": "1",
        "formula": "COUNT(humor_type == 'self_defeating')",
        "ambiguity_handling": "Only confirmed humor rows typed",
        "interpretation": "Brand laughing at its own flaws or mistakes. Very rare class (41/68k).",
        "limitation": "Extremely rare (41 rows). Insufficient for standalone regression. Combine with aggressive for rare_negative_humor.",
        "no_human_label_warning": "EXPLORATORY ONLY. Rare class with no human validation.",
    },
    {
        "variable_name": "affiliative_share",
        "hypothesis": "H2",
        "construct": "Affiliative humor usage rate",
        "role": "IV",
        "numerator": "affiliative_count",
        "denominator": "total_posts",
        "formula": "affiliative_count / total_posts",
        "ambiguity_handling": "conservative (ambiguous in denominator, 0 in numerator)",
        "interpretation": "Share of all posts that are affiliative humor.",
        "limitation": "v1 label only. Ambiguous posts may include undetected affiliative humor.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "self_enhancing_share",
        "hypothesis": "H2",
        "construct": "Self-enhancing humor usage rate",
        "role": "IV",
        "numerator": "self_enhancing_count",
        "denominator": "total_posts",
        "formula": "self_enhancing_count / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Share of all posts that are self-enhancing humor.",
        "limitation": "v1 label only.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "aggressive_share",
        "hypothesis": "H2, H3",
        "construct": "Aggressive humor usage rate",
        "role": "IV (H2) / Basis for H3 intensity",
        "numerator": "aggressive_count",
        "denominator": "total_posts",
        "formula": "aggressive_count / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Share of all posts that are aggressive humor. Identical to aggressive_humor_usage_intensity.",
        "limitation": "Rare class. Most firm-periods will have aggressive_share == 0.0.",
        "no_human_label_warning": "EXPLORATORY. v1 label only. True aggressive share unknown without human labels.",
    },
    {
        "variable_name": "self_defeating_share",
        "hypothesis": "H2",
        "construct": "Self-defeating humor usage rate",
        "role": "IV",
        "numerator": "self_defeating_count",
        "denominator": "total_posts",
        "formula": "self_defeating_count / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Share of all posts that are self-defeating humor.",
        "limitation": "Extremely rare (41/68k). Almost all firm-periods will be 0.",
        "no_human_label_warning": "EXPLORATORY. v1 label only.",
    },
    {
        "variable_name": "rare_negative_humor_count",
        "hypothesis": "H2, H3",
        "construct": "Rare negative humor volume",
        "role": "IV (combined rare class)",
        "numerator": "aggressive_count + self_defeating_count",
        "denominator": "1",
        "formula": "aggressive_count + self_defeating_count",
        "ambiguity_handling": "conservative",
        "interpretation": "Combined count of aggressive and self-defeating humor. Use when individual rare classes are too sparse for separate analysis.",
        "limitation": "Combines two theoretically distinct constructs for statistical power. Use when n is too small for separate terms.",
        "no_human_label_warning": "EXPLORATORY. Both components are v1 labels with no human validation.",
    },
    {
        "variable_name": "rare_negative_humor_share",
        "hypothesis": "H2, H3",
        "construct": "Rare negative humor usage rate",
        "role": "IV (combined rare class share)",
        "numerator": "rare_negative_humor_count",
        "denominator": "total_posts",
        "formula": "(aggressive_count + self_defeating_count) / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Share of all posts that are aggressive or self-defeating humor.",
        "limitation": "Same as rare_negative_humor_count.",
        "no_human_label_warning": "EXPLORATORY. v1 labels only.",
    },
    {
        "variable_name": "aggressive_minus_other_humor_share",
        "hypothesis": "H2",
        "construct": "Aggressive humor relative to other humor types",
        "role": "IV (relative contrast)",
        "numerator": "aggressive_count",
        "denominator": "total_posts (for each component)",
        "formula": "aggressive_share - (affiliative_share + self_enhancing_share + self_defeating_share)",
        "ambiguity_handling": "conservative",
        "interpretation": "Excess share of aggressive humor over sum of all other humor types. Negative if firm relies primarily on positive humor types.",
        "limitation": "Can be negative. Zero-centered interpretation depends on the humor mix.",
        "no_human_label_warning": "v1 labels only. Rare class sparsity may make this negative for almost all firm-periods.",
    },
    # --- H3 intensity variables ---
    {
        "variable_name": "aggressive_humor_usage_intensity",
        "hypothesis": "H3",
        "construct": "Aggressive humor usage intensity (firm-level)",
        "role": "Moderator (H3)",
        "numerator": "aggressive_count",
        "denominator": "total_posts",
        "formula": "aggressive_count / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Firm-level intensity of aggressive humor usage. NOT subjective message-level semantic intensity; this is the share of aggressive humor posts among all posts. For H3 inverted-U test, this is the moderator.",
        "limitation": "Identical value to aggressive_share. Kept as a separately-named variable to distinguish the moderator role in H3 from the independent variable role in H2.",
        "no_human_label_warning": "EXPLORATORY. v1 label. True intensity unknown without human validation.",
    },
    {
        "variable_name": "aggressive_humor_usage_intensity_sq",
        "hypothesis": "H3",
        "construct": "Aggressive humor usage intensity squared",
        "role": "Moderator squared (H3 inverted-U)",
        "numerator": "aggressive_count² / total_posts²",
        "denominator": "1",
        "formula": "(aggressive_count / total_posts)²",
        "ambiguity_handling": "conservative",
        "interpretation": "Squared term of aggressive_humor_usage_intensity. Required for testing inverted-U (curvilinear) moderation in H3. Negative coefficient expected.",
        "limitation": "Most firm-periods have intensity=0; squared term will also be 0. Very few non-zero observations.",
        "no_human_label_warning": "EXPLORATORY. v1 label.",
    },
    {
        "variable_name": "log_aggressive_count",
        "hypothesis": "H3",
        "construct": "Aggressive humor count (log-transformed)",
        "role": "IV / Moderator (log form)",
        "numerator": "1 + aggressive_count",
        "denominator": "1",
        "formula": "log(1 + aggressive_count)",
        "ambiguity_handling": "conservative",
        "interpretation": "Log-transformed count for skew correction. Most firm-periods will be log(1)=0.",
        "limitation": "Extremely sparse. Zero-inflated structure requires special attention.",
        "no_human_label_warning": "EXPLORATORY. v1 label.",
    },
    {
        "variable_name": "aggressive_presence_any",
        "hypothesis": "H3",
        "construct": "Aggressive humor adoption (binary)",
        "role": "Binary moderator / IV",
        "numerator": "1 if aggressive_count > 0",
        "denominator": "1",
        "formula": "1 if aggressive_count > 0 else 0",
        "ambiguity_handling": "conservative",
        "interpretation": "Binary indicator: firm posted at least one aggressive humor post in period. For DiD or selection analysis.",
        "limitation": "Loses intensity information. Most firm-periods will be 0.",
        "no_human_label_warning": "EXPLORATORY. v1 label.",
    },
    {
        "variable_name": "aggressive_share_ambiguity_excluded",
        "hypothesis": "H3",
        "construct": "Aggressive humor intensity (robustness: ambiguous excluded)",
        "role": "Moderator (Robustness)",
        "numerator": "aggressive_count",
        "denominator": "humor_count + non_humor_count",
        "formula": "aggressive_count / (humor_count + non_humor_count)",
        "ambiguity_handling": "ambiguity_excluded",
        "interpretation": "Aggressive humor share among unambiguous posts only. Robustness check for H3.",
        "limitation": "Denominator shrinks for high-ambiguity firm-periods.",
        "no_human_label_warning": "v1 label only.",
    },
    {
        "variable_name": "rare_negative_humor_usage_intensity",
        "hypothesis": "H3",
        "construct": "Combined rare negative humor intensity",
        "role": "Moderator (robustness, H3)",
        "numerator": "rare_negative_humor_count",
        "denominator": "total_posts",
        "formula": "(aggressive_count + self_defeating_count) / total_posts",
        "ambiguity_handling": "conservative",
        "interpretation": "Combined aggressive + self_defeating intensity. Use as robustness moderator when aggressive alone is too sparse.",
        "limitation": "Conflates two distinct humor constructs.",
        "no_human_label_warning": "EXPLORATORY. v1 labels.",
    },
    {
        "variable_name": "rare_negative_humor_usage_intensity_sq",
        "hypothesis": "H3",
        "construct": "Combined rare negative humor intensity squared",
        "role": "Moderator squared (robustness)",
        "numerator": "(rare_negative_humor_count)²",
        "denominator": "total_posts²",
        "formula": "((aggressive_count + self_defeating_count) / total_posts)²",
        "ambiguity_handling": "conservative",
        "interpretation": "Squared term for curvilinear moderation test using combined rare class.",
        "limitation": "Same caveats as rare_negative_humor_usage_intensity.",
        "no_human_label_warning": "EXPLORATORY.",
    },
    # --- H3 interaction terms ---
    {
        "variable_name": "humor_share_x_aggressive_intensity",
        "hypothesis": "H3",
        "construct": "H1 × H3 interaction: humor share × aggressive intensity",
        "role": "Interaction term",
        "numerator": "humor_share × aggressive_humor_usage_intensity",
        "denominator": "1",
        "formula": "humor_share * aggressive_humor_usage_intensity",
        "ambiguity_handling": "conservative (both components)",
        "interpretation": "Cross-product for testing whether aggressive humor moderates the humor→equity relationship. Center both variables before computing for interpretability.",
        "limitation": "Multicollinear with component variables. Centering recommended.",
        "no_human_label_warning": "v1 labels.",
    },
    {
        "variable_name": "humor_share_x_aggressive_intensity_sq",
        "hypothesis": "H3",
        "construct": "H1 × H3 interaction: humor share × aggressive intensity squared",
        "role": "Interaction term (inverted-U)",
        "numerator": "humor_share × aggressive_humor_usage_intensity²",
        "denominator": "1",
        "formula": "humor_share * aggressive_humor_usage_intensity_sq",
        "ambiguity_handling": "conservative",
        "interpretation": "Tests inverted-U moderation: whether the curvilinear effect of aggressive intensity depends on overall humor share.",
        "limitation": "High multicollinearity. Use with caution.",
        "no_human_label_warning": "v1 labels.",
    },
    {
        "variable_name": "aggressive_presence_x_aggressive_intensity",
        "hypothesis": "H3",
        "construct": "Binary adoption × continuous intensity interaction",
        "role": "Interaction term",
        "numerator": "aggressive_presence_any × aggressive_humor_usage_intensity",
        "denominator": "1",
        "formula": "aggressive_presence_any * aggressive_humor_usage_intensity",
        "ambiguity_handling": "conservative",
        "interpretation": "Cross-product: aggressive presence binary × intensity. Non-zero only when firm has any aggressive humor. Useful for split-sample designs.",
        "limitation": "Since aggressive_presence_any = 1 iff aggressive_count > 0, this equals aggressive_humor_usage_intensity for firms with any aggressive posts and 0 otherwise.",
        "no_human_label_warning": "v1 labels.",
    },
    {
        "variable_name": "aggressive_presence_x_aggressive_intensity_sq",
        "hypothesis": "H3",
        "construct": "Binary adoption × intensity squared interaction",
        "role": "Interaction term (inverted-U)",
        "numerator": "aggressive_presence_any × aggressive_humor_usage_intensity²",
        "denominator": "1",
        "formula": "aggressive_presence_any * aggressive_humor_usage_intensity_sq",
        "ambiguity_handling": "conservative",
        "interpretation": "Squared version of the binary × intensity interaction for inverted-U testing.",
        "limitation": "Same as above.",
        "no_human_label_warning": "v1 labels.",
    },
    # --- v2 candidate flags ---
    {
        "variable_name": "v2_aggressive_candidate_count",
        "hypothesis": "H2, H3",
        "construct": "v2 aggressive candidate count (company-level diagnostic)",
        "role": "Diagnostic flag (NOT production label)",
        "numerator": "Rows in v1-v2 comparison where v2_label == 'aggressive' for this company",
        "denominator": "1",
        "formula": "COUNT(v2_label == 'aggressive' AND company == firm) in 941-row comparison sample",
        "ambiguity_handling": "N/A — from stratified sample, not full 68k",
        "interpretation": "Number of posts that v2 classified as aggressive for this company in the 941-row A/B sample. COMPANY-LEVEL metric (not period-level). Same value repeated for all periods of the firm. Use as robustness check only.",
        "limitation": "From 941-row stratified sample only. Not period-specific. v2 is NOT a production label. Do not use as replacement for aggressive_count.",
        "no_human_label_warning": "v2 is a disagreement detector. v2 aggressive label has NO human validation.",
    },
    {
        "variable_name": "v1_v2_disagreement_candidate_count",
        "hypothesis": "Robustness",
        "construct": "v1-v2 classification disagreement count (company-level)",
        "role": "Diagnostic",
        "numerator": "Rows where v1 and v2 disagree for this company in the 941-row comparison sample",
        "denominator": "1",
        "formula": "COUNT(agreement != 'true' AND company == firm) in 941-row sample",
        "ambiguity_handling": "N/A",
        "interpretation": "Number of disagreement instances in the A/B sample for this company. High values indicate measurement uncertainty. COMPANY-LEVEL metric.",
        "limitation": "Stratified sample only. Not period-specific.",
        "no_human_label_warning": "Disagreement does not indicate which label is correct.",
    },
    {
        "variable_name": "rare_class_candidate_count",
        "hypothesis": "H2, H3",
        "construct": "P0 priority review candidates (company-level)",
        "role": "Diagnostic",
        "numerator": "P0 rows in priority sample for this company",
        "denominator": "1",
        "formula": "COUNT(priority == 'P0' AND company == firm) in priority sample",
        "ambiguity_handling": "N/A",
        "interpretation": "Number of v1-ambiguous posts that v2 reclassified as aggressive/self-defeating for this company. Awaiting human review. COMPANY-LEVEL metric.",
        "limitation": "Not period-specific. Human review pending.",
        "no_human_label_warning": "P0 candidates have no human label. v2 classification is unvalidated.",
    },
    {
        "variable_name": "high_ambiguity_flag",
        "hypothesis": "Diagnostic",
        "construct": "High measurement uncertainty flag",
        "role": "Flag / Exclusion criterion",
        "numerator": "1 if ambiguity_rate >= 0.50",
        "denominator": "1",
        "formula": "1 if ambiguity_rate >= 0.50 else 0",
        "ambiguity_handling": "Flag triggered when >= 50% of posts are ambiguous",
        "interpretation": "1 = this firm-period has >= 50% ambiguous posts; humor share is unreliable. Use to exclude or as control in robustness checks.",
        "limitation": "Threshold (0.50) is a judgment call. Consider sensitivity at 0.30 and 0.70.",
        "no_human_label_warning": "Flag signals v1 classification uncertainty, not true ambiguity of content.",
    },
    {
        "variable_name": "no_human_label_flag",
        "hypothesis": "Diagnostic",
        "construct": "Human label availability flag",
        "role": "Metadata",
        "numerator": "Always 1 at this stage",
        "denominator": "1",
        "formula": "1 (constant)",
        "ambiguity_handling": "N/A",
        "interpretation": "1 = no human labels available for this firm-period. All humor variables are v1 operational labels only. Will become 0 after human adjudication.",
        "limitation": "Always 1 until human review is completed.",
        "no_human_label_warning": "All variables in this dataset are v1 operational labels. No accuracy claims are possible.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_div(num: float, den: float) -> float:
    return round(num / den, 6) if den != 0 else 0.0


def safe_div_na(num: float, den: float):
    return round(num / den, 6) if den != 0 else ""


def load_csv(path: Path, label: str) -> list[dict]:
    if not path.exists():
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print(f"ERROR: {label} has no header: {path}", file=sys.stderr)
            sys.exit(1)
        return list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


TWITTER_DATE_FMT = "%a %b %d %H:%M:%S +0000 %Y"
FALLBACK_FMTS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def parse_period(date_str: str) -> str:
    """Return YYYY-MM from various date string formats. Returns 'unknown' on failure."""
    s = (date_str or "").strip()
    if not s:
        return "unknown"
    try:
        return datetime.strptime(s, TWITTER_DATE_FMT).strftime("%Y-%m")
    except ValueError:
        pass
    for fmt in FALLBACK_FMTS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return "unknown"


# ---------------------------------------------------------------------------
# Aggregate master to firm-period
# ---------------------------------------------------------------------------

def aggregate_master(rows: list[dict]) -> list[dict]:
    """Group master rows by (company_name, period), collapsing all source_x_handle values.

    Firms with multiple handles in the same period have their counts summed.
    source_x_handle values are collected into source_x_handle_list (sorted, '; '-joined,
    deduplicated) and counted in source_x_handle_count.
    The unique key of the output is (company_name, period).
    """

    # Find key columns robustly
    sample = rows[0] if rows else {}
    cols = set(sample.keys())

    company_col  = next((c for c in ["company_name", "firm", "brand"] if c in cols), None)
    handle_col   = next((c for c in ["source_x_handle", "handle", "twitter_handle"] if c in cols), None)
    date_col     = next((c for c in ["created_at", "post_created_at", "date", "posted_at", "timestamp"] if c in cols), None)
    presence_col = next((c for c in ["humor_presence"] if c in cols), None)
    htype_col    = next((c for c in ["humor_type"] if c in cols), None)

    if not company_col:
        print("ERROR: Cannot find company identifier column (tried: company_name, firm, brand)", file=sys.stderr)
        sys.exit(1)
    if not presence_col:
        print("ERROR: Cannot find humor_presence column", file=sys.stderr)
        sys.exit(1)
    if not htype_col:
        print("ERROR: Cannot find humor_type column", file=sys.stderr)
        sys.exit(1)

    period_fallback = date_col is None
    if period_fallback:
        print("WARNING: No date column found. Aggregating at firm level (period='all').", file=sys.stderr)

    print(f"  company_col={company_col!r}, handle_col={handle_col!r}, date_col={date_col!r}")
    print(f"  presence_col={presence_col!r}, htype_col={htype_col!r}")

    # Group by (company, period) — all handles collapsed into one row per company-period
    groups:  dict[tuple, list[dict]] = defaultdict(list)
    handles: dict[tuple, set]        = defaultdict(set)
    for r in rows:
        company = r.get(company_col, "").strip() or "_unknown"
        period  = parse_period(r.get(date_col, "")) if date_col else "all"
        handle  = r.get(handle_col, "").strip() if handle_col else ""
        key = (company, period)
        groups[key].append(r)
        if handle:
            handles[key].add(handle)

    unknown_period = sum(1 for (_, p) in groups if p == "unknown")
    if unknown_period > 0:
        print(f"  WARNING: {unknown_period} groups have period='unknown' (date parse failed)")

    output_rows = []
    for (company, period), grp in sorted(groups.items()):
        handle_list_sorted = sorted(handles.get((company, period), set()))
        handle_list_str    = "; ".join(handle_list_sorted)
        handle_count       = len(handle_list_sorted)
        n = len(grp)
        presence  = Counter(r.get(presence_col, "").strip() for r in grp)
        htype     = Counter(r.get(htype_col, "").strip() for r in grp)

        humor_count     = presence.get("humor", 0)
        non_humor_count = presence.get("non_humor", 0)
        ambiguous_count = presence.get("ambiguous", 0)
        affiliative     = htype.get("affiliative", 0)
        self_enhancing  = htype.get("self_enhancing", 0)
        aggressive      = htype.get("aggressive", 0)
        self_defeating  = htype.get("self_defeating", 0)

        ambiguity_rate   = safe_div(ambiguous_count, n)
        humor_share      = safe_div(humor_count, n)
        rare_neg         = aggressive + self_defeating
        affiliative_sh   = safe_div(affiliative, n)
        self_enhancing_sh = safe_div(self_enhancing, n)
        aggressive_sh    = safe_div(aggressive, n)
        self_defeating_sh = safe_div(self_defeating, n)

        # Robustness: ambiguity_excluded denominator
        unambig_n = humor_count + non_humor_count
        humor_sh_excl    = safe_div_na(humor_count, unambig_n)
        aggressive_sh_excl = safe_div_na(aggressive, unambig_n)

        # Robustness: ambiguity_as_missing
        humor_sh_missing = humor_share if ambiguity_rate < HIGH_AMBIGUITY_THRESHOLD else ""

        # H3 intensity and squared terms
        agg_intensity    = aggressive_sh
        agg_intensity_sq = round(agg_intensity ** 2, 9)
        rare_neg_intensity    = safe_div(rare_neg, n)
        rare_neg_intensity_sq = round(rare_neg_intensity ** 2, 9)

        agg_presence = 1 if aggressive > 0 else 0

        output_rows.append({
            "company_name":          company,
            "period":                period,
            "source_x_handle_count": handle_count,
            "source_x_handle_list":  handle_list_str,
            "total_posts":           n,
            "humor_count":     humor_count,
            "non_humor_count": non_humor_count,
            "ambiguous_count": ambiguous_count,
            "ambiguity_rate":  ambiguity_rate,
            # H1
            "humor_share":                      humor_share,
            "humor_share_ambiguity_as_zero":    humor_share,
            "humor_share_ambiguity_excluded":   humor_sh_excl,
            "humor_share_ambiguity_as_missing": humor_sh_missing,
            "log_humor_count":                  round(math.log1p(humor_count), 6),
            "humor_presence_any":               1 if humor_count > 0 else 0,
            # H2 counts
            "affiliative_count":     affiliative,
            "self_enhancing_count":  self_enhancing,
            "aggressive_count":      aggressive,
            "self_defeating_count":  self_defeating,
            # H2 shares
            "affiliative_share":     affiliative_sh,
            "self_enhancing_share":  self_enhancing_sh,
            "aggressive_share":      aggressive_sh,
            "self_defeating_share":  self_defeating_sh,
            "rare_negative_humor_count":  rare_neg,
            "rare_negative_humor_share":  safe_div(rare_neg, n),
            "aggressive_minus_other_humor_share": round(
                aggressive_sh - (affiliative_sh + self_enhancing_sh + self_defeating_sh), 6
            ),
            # H3 intensity
            "aggressive_humor_usage_intensity":    agg_intensity,
            "aggressive_humor_usage_intensity_sq": agg_intensity_sq,
            "log_aggressive_count":                round(math.log1p(aggressive), 6),
            "aggressive_presence_any":             agg_presence,
            "aggressive_share_ambiguity_excluded": aggressive_sh_excl,
            "rare_negative_humor_usage_intensity":    rare_neg_intensity,
            "rare_negative_humor_usage_intensity_sq": rare_neg_intensity_sq,
            # H3 interaction terms
            "humor_share_x_aggressive_intensity":      round(humor_share * agg_intensity, 9),
            "humor_share_x_aggressive_intensity_sq":   round(humor_share * agg_intensity_sq, 9),
            "aggressive_presence_x_aggressive_intensity":    round(agg_presence * agg_intensity, 9),
            "aggressive_presence_x_aggressive_intensity_sq": round(agg_presence * agg_intensity_sq, 9),
            # v2 flags — will be joined later
            "v2_aggressive_candidate_count":       0,
            "v1_v2_disagreement_candidate_count":  0,
            "rare_class_candidate_count":          0,
            # Diagnostic
            "high_ambiguity_flag":  1 if ambiguity_rate >= HIGH_AMBIGUITY_THRESHOLD else 0,
            "no_human_label_flag":  1,
        })

    return output_rows, period_fallback


# ---------------------------------------------------------------------------
# Build company-level v2 candidate flags
# ---------------------------------------------------------------------------

def build_v2_company_flags(
    comparison: list[dict],
    priority: list[dict],
) -> dict[str, dict]:
    """Compute company-level v2 candidate counts from comparison and priority sample."""
    v2_agg:    Counter = Counter()
    v1_v2_dis: Counter = Counter()
    for r in comparison:
        co = r.get("company_name", "").strip()
        if r.get("v2_label", "").strip() == "aggressive":
            v2_agg[co] += 1
        if r.get("agreement", "").strip().lower() != "true":
            v1_v2_dis[co] += 1

    rare_p0: Counter = Counter()
    for r in priority:
        if r.get("priority", "").strip() == "P0":
            co = r.get("company_name", "").strip()
            rare_p0[co] += 1

    all_companies = set(v2_agg) | set(v1_v2_dis) | set(rare_p0)
    return {
        co: {
            "v2_aggressive_candidate_count":      v2_agg.get(co, 0),
            "v1_v2_disagreement_candidate_count": v1_v2_dis.get(co, 0),
            "rare_class_candidate_count":         rare_p0.get(co, 0),
        }
        for co in all_companies
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build hypothesis-ready humor variables (H1/H2/H3) at firm-period level."
    )
    parser.add_argument("--master",      type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--comparison",  type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--ab-summary",  type=Path, default=DEFAULT_AB_SUMMARY)
    parser.add_argument("--priority",    type=Path, default=DEFAULT_PRIORITY)
    parser.add_argument("--out-full",    type=Path, default=DEFAULT_OUT_FULL)
    parser.add_argument("--out-h1",      type=Path, default=DEFAULT_OUT_H1)
    parser.add_argument("--out-h2",      type=Path, default=DEFAULT_OUT_H2)
    parser.add_argument("--out-h3",      type=Path, default=DEFAULT_OUT_H3)
    parser.add_argument("--out-dict",    type=Path, default=DEFAULT_OUT_DICT)
    parser.add_argument("--out-manifest", type=Path, default=DEFAULT_OUT_MANIFEST)
    parser.add_argument("--high-ambiguity-threshold", type=float, default=HIGH_AMBIGUITY_THRESHOLD,
                        help="Ambiguity rate threshold for high_ambiguity_flag (default: 0.50)")
    args = parser.parse_args()

    print(f"Loading master:     {args.master}")
    master = load_csv(args.master, "full-chain master")
    print(f"  Rows: {len(master)}")

    print(f"Loading comparison: {args.comparison}")
    comparison = load_csv(args.comparison, "v1-v2 comparison")
    print(f"  Rows: {len(comparison)}")

    print(f"Loading priority:   {args.priority}")
    priority = load_csv(args.priority, "human review priority sample")
    print(f"  Rows: {len(priority)}")

    if args.ab_summary.exists():
        ab_summary = json.loads(args.ab_summary.read_text(encoding="utf-8"))
    else:
        print(f"WARNING: A/B summary not found: {args.ab_summary}. Skipping summary metadata.", file=sys.stderr)
        ab_summary = {}

    # Aggregate
    print("\nAggregating master to firm-period (company_name × period)...")
    firm_period_rows, period_fallback = aggregate_master(master)
    print(f"  Firm-period cells: {len(firm_period_rows)}")

    # Validate unique key — must be 0 by construction; fail fast if there is a bug
    seen_keys: set = set()
    company_period_dup_count = 0
    for row in firm_period_rows:
        key = (row["company_name"], row["period"])
        if key in seen_keys:
            company_period_dup_count += 1
        seen_keys.add(key)
    if company_period_dup_count > 0:
        print(
            f"FATAL: {company_period_dup_count} duplicate company_name×period keys after aggregation. "
            "This is an aggregation bug.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"  Unique key check: company_period_duplicate_count={company_period_dup_count} (OK)")

    # Handle collapse diagnostics
    handle_counts            = [r["source_x_handle_count"] for r in firm_period_rows]
    source_x_handle_count_max = max(handle_counts, default=0)
    multi_handle_fp_count    = sum(1 for c in handle_counts if c > 1)
    print(f"  source_x_handle_count_max={source_x_handle_count_max}, multi_handle_firm_period_count={multi_handle_fp_count}")

    # H3 sparsity diagnostics
    agg_intensities          = [float(r["aggressive_humor_usage_intensity"]) for r in firm_period_rows]
    aggressive_count_total   = sum(int(r["aggressive_count"]) for r in firm_period_rows)
    nonzero_aggressive_fp    = sum(1 for x in agg_intensities if x > 0)
    n_fp = len(agg_intensities)
    agg_intensity_zero_share = round(safe_div(n_fp - nonzero_aggressive_fp, n_fp), 6) if n_fp else 0.0
    max_agg_intensity        = round(max(agg_intensities), 9) if agg_intensities else 0.0
    mean_agg_intensity       = round(safe_div(sum(agg_intensities), n_fp), 9) if n_fp else 0.0
    sorted_agg = sorted(agg_intensities)
    if n_fp % 2 == 1:
        median_agg = sorted_agg[n_fp // 2]
    elif n_fp > 0:
        median_agg = (sorted_agg[n_fp // 2 - 1] + sorted_agg[n_fp // 2]) / 2
    else:
        median_agg = 0.0
    median_agg = round(median_agg, 9)

    rare_neg_intensities     = [float(r["rare_negative_humor_usage_intensity"]) for r in firm_period_rows]
    rare_negative_count_total   = sum(int(r["rare_negative_humor_count"]) for r in firm_period_rows)
    nonzero_rare_neg_fp      = sum(1 for x in rare_neg_intensities if x > 0)

    # v2 company flags
    print("Computing v2 company-level flags...")
    v2_flags = build_v2_company_flags(comparison, priority)
    for row in firm_period_rows:
        flags = v2_flags.get(row["company_name"], {})
        row["v2_aggressive_candidate_count"]      = flags.get("v2_aggressive_candidate_count", 0)
        row["v1_v2_disagreement_candidate_count"] = flags.get("v1_v2_disagreement_candidate_count", 0)
        row["rare_class_candidate_count"]          = flags.get("rare_class_candidate_count", 0)

    # Write outputs
    n_full = write_csv(args.out_full, FULL_FIELDS, firm_period_rows)
    print(f"  Full → {args.out_full} ({n_full} rows)")

    n_h1 = write_csv(args.out_h1, H1_FIELDS, firm_period_rows)
    print(f"  H1   → {args.out_h1} ({n_h1} rows)")

    n_h2 = write_csv(args.out_h2, H2_FIELDS, firm_period_rows)
    print(f"  H2   → {args.out_h2} ({n_h2} rows)")

    n_h3 = write_csv(args.out_h3, H3_FIELDS, firm_period_rows)
    print(f"  H3   → {args.out_h3} ({n_h3} rows)")

    n_dict = write_csv(args.out_dict, DICT_FIELDS, VARIABLE_DICTIONARY)
    print(f"  Dict → {args.out_dict} ({n_dict} rows)")

    # Manifest
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    unique_companies = len({r["company_name"] for r in firm_period_rows})
    unique_periods   = len({r["period"] for r in firm_period_rows})
    high_ambig_cells = sum(1 for r in firm_period_rows if r.get("high_ambiguity_flag") == 1)

    manifest = {
        "created_at": created_at,
        "source_files": {
            "master":          str(args.master),
            "comparison":      str(args.comparison),
            "ab_summary":      str(args.ab_summary),
            "priority_sample": str(args.priority),
        },
        "output_files": {
            "full_hypothesis_variables": str(args.out_full),
            "h1_variables":  str(args.out_h1),
            "h2_variables":  str(args.out_h2),
            "h3_variables":  str(args.out_h3),
            "variable_dictionary": str(args.out_dict),
        },
        "input_rows":  len(master),
        "output_rows": n_full,
        "aggregation_level":    "firm-period (company_name × YYYY-MM)" if not period_fallback else "firm-level (no date column)",
        "unique_key_columns":   ["company_name", "period"],
        "company_period_duplicate_count": company_period_dup_count,
        "source_x_handle_collapsed":      True,
        "source_x_handle_count_max":      source_x_handle_count_max,
        "multi_handle_firm_period_count": multi_handle_fp_count,
        "period_column_used":   "created_at" if not period_fallback else None,
        "period_fallback_to_firm_level": period_fallback,
        "company_column_used":  "company_name",
        "handle_column_used":   "source_x_handle (collapsed)",
        "label_columns_used":   ["humor_presence", "humor_type"],
        "unique_companies":     unique_companies,
        "unique_periods":       unique_periods,
        "high_ambiguity_cells": high_ambig_cells,
        "high_ambiguity_threshold": args.high_ambiguity_threshold,
        "h3_sparsity_diagnostics": {
            "aggressive_count_total":             aggressive_count_total,
            "nonzero_aggressive_firm_period_count": nonzero_aggressive_fp,
            "aggressive_intensity_zero_share":    agg_intensity_zero_share,
            "max_aggressive_intensity":           max_agg_intensity,
            "mean_aggressive_intensity":          mean_agg_intensity,
            "median_aggressive_intensity":        median_agg,
            "rare_negative_count_total":          rare_negative_count_total,
            "nonzero_rare_negative_firm_period_count": nonzero_rare_neg_fp,
        },
        "v2_note": (
            "v2 candidate counts are company-level aggregates from the 941-row A/B stratified sample. "
            "They are NOT period-specific and are repeated for all firm-periods of each company. "
            "v2 is NOT a production label; these counts are diagnostic flags only."
        ),
        "constraints": {
            "no_human_label":              True,
            "gold_label_created":          False,
            "coder_label_created":         False,
            "adjudicated_label_created":   False,
            "v1_v2_consensus_as_gold":     False,
            "v2_production_converted":     False,
            "full_chain_overwritten":      False,
            "raw_data_modified":           False,
            "classification_run":          False,
            "hypothesis_testing_ready":    company_period_dup_count == 0,
            "h1_variables_created":        True,
            "h2_variables_created":        True,
            "h3_variables_created":        True,
        },
        "limitations": [
            "~48% of posts (32,749/68,020) are ambiguous_or_review; all humor type counts are lower-bound estimates.",
            "aggressive (105/68k) and self_defeating (41/68k) are rare classes with no human validation; treat as exploratory.",
            "v1-v2 agreement rate (39.53%) is a consistency indicator, not an accuracy estimate.",
            "All variables are v1 operational labels. No precision/recall claims are possible.",
            "Cue/threshold calibration requires human adjudication labels; deferred.",
            "v2 candidate counts are from the 941-row stratified sample and are not period-specific.",
            "Firms with multiple X handles have counts summed across handles per period; source_x_handle_list records all handles.",
        ],
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest → {args.out_manifest}")
    print(f"\nDone. {unique_companies} companies × {unique_periods} periods → {n_full} firm-period rows")
    print(f"  company_period_duplicate_count: {company_period_dup_count}")
    print(f"  multi_handle_firm_period_count: {multi_handle_fp_count} (source_x_handle_count_max={source_x_handle_count_max})")
    print(f"  High-ambiguity cells: {high_ambig_cells} / {n_full} ({100*high_ambig_cells/n_full:.1f}%)")
    print(f"  H3 sparsity: aggressive_count_total={aggressive_count_total}, nonzero_fp={nonzero_aggressive_fp}, zero_share={agg_intensity_zero_share:.3f}")


if __name__ == "__main__":
    main()
