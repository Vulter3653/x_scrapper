# Gate 6 — Regression Design Plan (No Execution)

**Status:** Design document only — regression NOT executed  
**Based on:** Gate 5.1.1 commit `06219560a84568a0aad2310f982fd7ff41d4ed36`  
**IV authority:** `data/audit/regression/humor_iv_gate6_input_manifest.json`  
**IV source file (when run):** `data/derived/regression/humor_iv_reconstructed_candidates_gate5_1.csv`

---

## 1. Gate Status Summary

| Gate | Status |
|------|--------|
| Gate 3: Extended CAR Regression | PASS |
| Gate 4: IV Measurement Diagnostic | PASS |
| Gate 5: IV Reconstruction | VERIFIED |
| Gate 5.1: Paper-grounded IV Repair | CONDITIONAL PASS |
| Gate 5.1.1: Denominator fix + Gate 6 manifest | COMPLETE |
| **Gate 6: Regression Design** | **DESIGN ONLY — execution pending** |

**Pending pre-conditions before execution:**
- Human coding of `data/derived/validation/humor_candidate_manual_audit_sample.csv` (required before H3)
- Resolution of v2_aggressive_candidate_count firm-level vs. per-period ambiguity (required before interpreting H2 v2-based results)

---

## 2. Gate 6 Purpose

Gate 6 estimates the association between firm-period humor characteristics and short-window cumulative abnormal returns (CAR), using the reconstructed IV set from Gate 5.1.

**Gate 6 is a measurement validity check, not a causal test.** Its purpose is to determine whether probability-weighted and candidate-based humor IVs produce different inferential conclusions than the original IVs used in Gate 3. CAR is used as a short-window market reaction proxy only.

---

## 3. DV Definition

| DV | Window | Role |
|----|--------|------|
| `CAR_m1_p1` | [−1, +1] trading days | **Primary DV** |
| `CAR_m3_p3` | [−3, +3] trading days | Robustness DV |
| `CAR_m5_p5` | [−5, +5] trading days | Robustness DV |

**Source file:** `data/derived/regression/humor_car_hypothesis_regression_master.csv`  
(or Gate 5.1 panel: `humor_iv_reconstructed_candidates_gate5_1.csv`, which contains all CAR columns)

**Forbidden DVs:**
- `CAR_0_p3` — asymmetric window, must not be used
- `CAR_0_p5` — asymmetric window, must not be used

**Interpretation constraint:**  
CAR represents short-window abnormal return around the 10-K filing date. CAR must NOT be described as Tobin's Q, brand equity, or any causal market effect. Significant associations are observational only.

---

## 4. Sample Definition

Identical to Gate 3 primary sample:

```
alignment_type ∈ {prefiling_lag_1m, prefiling_lag_3m}
AND join_ready_for_CAR_<window> == True
```

Expected n ≈ 430 observations (78–80 companies, 3 fiscal years).  
Each DV uses its own `join_ready_for_CAR_<window>` filter separately.

---

## 5. IV Lists

### 5.1 Allowed H1 IVs

| IV | Role | Notes |
|----|------|-------|
| `humor_prob_mean` | **Primary H1** | bounded [0,1]; mean P(humor) per firm-period; 100% nonzero |
| `ambiguity_adjusted_humor_share` | Primary H1 alias | identical to `humor_prob_mean`; **do not include simultaneously** |
| `hc_humor_share` | H1 robustness | existing humor_share from hypothesis_variables |
| `hc_humor_presence_any` | H1 robustness | binary; 66.7% nonzero |
| `hc_log_humor_count` | H1 robustness | log(1+count) |
| `humor_candidate_score_sum` | H1 robustness | unbounded sum; renamed from `humor_prob_sum` |

**Collinearity rule:** `humor_prob_mean` and `ambiguity_adjusted_humor_share` are algebraically identical. Never include both in the same model.

### 5.2 Allowed H2 IVs

| IV | Role | Notes |
|----|------|-------|
| `hc_v2_aggressive_candidate_count` | **Primary H2** | count only; firm-level score; do NOT normalize |
| `hc_log_v2_aggressive_candidate` | H2 robustness | log-transformed count |
| `hc_v2_aggressive_candidate_presence` | H2 robustness | binary; 60.2% nonzero |
| `aggressive_candidate_score_sum` | H2 robustness | corrected formula; probability-weighted sum |
| `aggressive_candidate_score_mean` | H2 robustness | mean per-post score |
| `aggressive_candidate_score_max` | H2 robustness | max per-post score; most extreme post signal |
| `hc_rare_class_candidate_count` | H2 robustness | rare class candidate count |
| `hc_log_rare_class_candidate` | H2 robustness | log-transformed |
| `hc_rare_class_candidate_presence` | H2 robustness | binary; 19.8% nonzero |

**v2 candidate caveat:** `hc_v2_aggressive_candidate_count` appears to be a firm-level fixed score (see Gate 5.1 findings). It is NOT confirmed to be a per-period post count. Results must be interpreted as an association with a firm-level aggressive candidate signal, not a period-specific posting rate.

### 5.3 Allowed H3 IVs (Planned Exploratory Only)

**Primary:**

| IV | Notes |
|----|-------|
| `aggressive_candidate_score_intensity_bounded` | corrected formula / total_posts; bounded [0,1]; 92.8% nonzero |
| `aggressive_candidate_score_intensity_bounded_sq` | quadratic term |

**Robustness:**

| IV | Notes |
|----|-------|
| `aggressive_candidate_score_sum` | unbounded; 92.8% nonzero |
| `aggressive_candidate_score_sum_sq` | quadratic term |
| `hc_rare_class_candidate_intensity_bounded` | bounded; 19.8% nonzero |
| `hc_rare_class_candidate_intensity_bounded_sq` | quadratic term |
| `sd_candidate_score_intensity_bounded` | self-defeating; bounded; 92.8% nonzero |
| `sd_candidate_score_intensity_bounded_sq` | quadratic term |

**⚠ H3 EXECUTION BLOCKED:** H3 models must not be run until:
1. Human coding of `humor_candidate_manual_audit_sample.csv` is complete
2. Coder agreement rate ≥ threshold (to be specified by PI)
3. v2_aggressive_candidate_count provenance resolved

---

## 6. Forbidden IVs

The following variables must never appear in any Gate 6 model:

| IV | Reason |
|----|--------|
| `hc_v2_aggressive_candidate_share` | v2_count > total_posts; max = 8.0 |
| `hc_v2_aggressive_candidate_intensity` | v2_count > humor_count; max = 7.0 |
| `hc_v2_aggressive_candidate_intensity_bounded` | still exceeds 1 (firm-level) |
| `hc_v2_aggressive_candidate_ratio_to_hard_humor` | exceeds 1; explicitly a ratio |
| `hc_negative_humor_intensity` | H3 BLOCKED: nonzero = 9/430 |
| `top_k_aggressive_score` | H3 BLOCKED: nonzero = 5/430 |
| `top_k_aggressive_type_confidence` | H3 BLOCKED: nonzero = 5/430 |
| `aggressive_prob_sum` | legacy formula; max > 1 |
| `aggressive_prob_mean` | legacy formula |
| `aggressive_prob_max` | legacy formula |
| `aggressive_prob_intensity` | legacy formula + wrong denominator |
| `CAR_0_p3` | asymmetric DV window; forbidden |
| `CAR_0_p5` | asymmetric DV window; forbidden |

---

## 7. Regression Specifications by Hypothesis

### 7.1 H1 Models

**Hypothesis:** More humor content (measured as probability-weighted humor presence) is associated with higher CAR.

#### H1a — Primary (per DV: CAR_m1_p1, CAR_m3_p3, CAR_m5_p5)

```
Model H1a_gate6_{dv}:
  DV      : {CAR_m1_p1 | CAR_m3_p3 | CAR_m5_p5}
  IV      : humor_prob_mean
  Controls: ambiguity_rate, high_ambiguity_flag, source_x_handle_count
  FE      : target_report_year + naics_sector_code (absorbed via C())
  SE      : HC3 heteroscedasticity-robust
  Sample  : primary (n ≈ 430)
  Note    : CTRL_BASE only; log_humor_count excluded to avoid collinearity
             with probability-based H1 IV
```

#### H1a_alias (confirmation model)

```
Model H1a_alias_{dv}:
  Same as H1a but IV = ambiguity_adjusted_humor_share
  Note: identical to humor_prob_mean; run once for confirmation only;
        do NOT report as separate independent finding
```

#### H1 Robustness Models (per DV)

```
H1b_share_{dv}:    IV = hc_humor_share,        Controls = CTRL_BASE
H1b_binary_{dv}:   IV = hc_humor_presence_any, Controls = CTRL_BASE
H1b_logcount_{dv}: IV = hc_log_humor_count,    Controls = CTRL_BASE (no log_count)
H1b_scoresum_{dv}: IV = humor_candidate_score_sum, Controls = CTRL_BASE
H1a_compFE_{dv}:   IV = humor_prob_mean,        Controls = CTRL_BASE,
                   FE = target_report_year + company_name
```

**H1 total models:** 7 per DV × 3 DVs = **21 models**

---

### 7.2 H2 Models

**Hypothesis:** Greater aggressive humor candidate signal is associated with different CAR (direction: negative, positive, or null — observational, not directional claim at design stage).

#### H2a — Primary

```
Model H2a_gate6_{dv}:
  DV      : {CAR_m1_p1 | CAR_m3_p3 | CAR_m5_p5}
  IV      : hc_v2_aggressive_candidate_count
  Controls: log_humor_count (or hc_log_humor_count), ambiguity_rate,
            high_ambiguity_flag, source_x_handle_count
  FE      : target_report_year + naics_sector_code
  SE      : HC3
  Sample  : primary (n ≈ 430)
  Warning : v2_count is a firm-level fixed score; not confirmed per-period
```

#### H2 Robustness Models (per DV)

```
H2a_logv2_{dv}:     IV = hc_log_v2_aggressive_candidate,   Controls = CTRL_WITH_COUNT
H2a_binary_{dv}:    IV = hc_v2_aggressive_candidate_presence, Controls = CTRL_WITH_COUNT
H2b_scoresum_{dv}:  IV = aggressive_candidate_score_sum,    Controls = CTRL_WITH_COUNT
H2b_scoremean_{dv}: IV = aggressive_candidate_score_mean,   Controls = CTRL_WITH_COUNT
H2b_scoremax_{dv}:  IV = aggressive_candidate_score_max,    Controls = CTRL_WITH_COUNT
H2c_rare_{dv}:      IV = hc_rare_class_candidate_count,     Controls = CTRL_WITH_COUNT
H2c_rarelogg_{dv}:  IV = hc_log_rare_class_candidate,       Controls = CTRL_WITH_COUNT
H2c_rarebinary_{dv}:IV = hc_rare_class_candidate_presence,  Controls = CTRL_WITH_COUNT
```

**H2 total models:** 9 per DV × 3 DVs = **27 models**

---

### 7.3 H3 Models — PLANNED EXPLORATORY ONLY (NOT TO BE EXECUTED)

**Hypothesis (exploratory):** Aggressive humor intensity shows a nonlinear (inverted-U) association with CAR.

**Execution precondition:** Human validation of manual audit sample must be complete.

#### H3 Primary (planned)

```
Model H3a_gate6_{dv} [PLANNED]:
  DV      : {CAR_m1_p1 | CAR_m3_p3 | CAR_m5_p5}
  IVs     : aggressive_candidate_score_intensity_bounded
            aggressive_candidate_score_intensity_bounded_sq
  Controls: log_humor_count, ambiguity_rate, high_ambiguity_flag,
            source_x_handle_count
  FE      : target_report_year + naics_sector_code
  SE      : HC3
  Sample  : primary (n ≈ 430)
  Label   : EXPLORATORY — not confirmatory
```

#### H3 Robustness (planned)

```
H3a_rob1_{dv}: IV linear+sq = aggressive_candidate_score_sum
H3a_rob2_{dv}: IV linear+sq = hc_rare_class_candidate_intensity_bounded
H3a_rob3_{dv}: IV linear+sq = sd_candidate_score_intensity_bounded
```

**H3 total planned models:** 4 per DV × 3 DVs = **12 planned models (not executed)**

---

## 8. Controls and Fixed Effects Structure

### 8.1 Control Variable Sets

```
CTRL_BASE = [
    "ambiguity_rate",          # share of ambiguous posts in firm-period
    "high_ambiguity_flag",     # binary: firm-period above high-ambiguity threshold
    "source_x_handle_count",   # number of distinct X handles per firm-period
]

CTRL_WITH_COUNT = CTRL_BASE + [
    "log_humor_count",         # log(1 + humor_count); controls for total humor volume
                               # when IV is aggressive/candidate-based (not count-based humor)
]
```

**Usage rules:**
- H1 primary models (IV = humor_prob_mean): use `CTRL_BASE` (avoid correlated humor count control)
- H2 and H3 models: use `CTRL_WITH_COUNT` (log_humor_count controls for baseline humor level)
- H1 robustness models with log/count IVs: use `CTRL_BASE` (drop log_humor_count to avoid exact collinearity)

### 8.2 Fixed Effects

| FE Specification | Label | Used In |
|-----------------|-------|---------|
| `target_report_year` + `naics_sector_code` | Period+NAICS FE | All primary models |
| `target_report_year` + `company_name` | Period+Company FE | H1a_compFE robustness only |

**Note:** When company FE is used, naics_sector_code FE drops out (company absorbs sector). Period FE absorbs year-level macro shocks common to all firms.

### 8.3 Standard Errors

- **Default:** HC3 heteroscedasticity-robust (consistent with Gate 3)
- **Clustered robustness (optional):** cluster by `company_name` for panel-robust inference
- Implementation: `statsmodels.OLS(...).fit(cov_type='HC3')` or `cov_type='cluster', cov_kwds={'groups': company_name}`

---

## 9. Model Family

- **Estimator:** OLS (ordinary least squares)
- **Package:** `statsmodels.formula.api.OLS`
- **FE absorption:** Categorical dummies via `C(target_report_year)` and `C(naics_sector_code)` in formula
- **No interaction terms** in H1/H2 primary specs
- **Quadratic terms** (linear + squared) in H3 only

**Why OLS for CAR:**  
CAR is a continuous outcome with no meaningful censoring. Logit/probit would require binary transformation, losing information. OLS with period+NAICS FE and robust SE is standard in event study regression literature.

---

## 10. H3 Exploratory Limitation

H3 is designated **exploratory** for the following reasons:

1. **Sparse nonzero in primary sample:** `aggressive_candidate_score_intensity_bounded` has 399/430 nonzero (92.8%), but the actual range of variation may be concentrated in a few firm-periods with very low values, with most nonzero values near zero.

2. **v2 candidate not human-validated:** The aggressive signal in the score is derived from ML classifier outputs that have not been confirmed by human coders for the aggressive content specifically.

3. **Prior Gate 3 results:** H3 was consistently non-significant across all three windows in Gate 3. Gate 6 H3 is a sensitivity check, not a new confirmatory test.

4. **No pre-registered direction:** Given Gate 3 null results, there is no pre-registered expected direction for H3 in Gate 6.

**Required label in all H3 output:** "Exploratory — pre-registered as non-confirmatory. Results do not confirm or reject H3."

---

## 11. Manual Validation Precondition

**Gate 6 H1 and H2 models** may be executed once all file/data preconditions are met (no human validation required for these hypotheses).

**Gate 6 H3 models** require:

1. **Human coding completed:** All rows in `data/derived/validation/humor_candidate_manual_audit_sample.csv` must have `final_human_label` filled in.

2. **Inter-rater reliability check:** If multiple coders, κ (Cohen's kappa) ≥ 0.60 for aggressive label agreement.

3. **Score correlation verified:** Correlation between `aggressive_candidate_score` and human aggressive label must be computed and reported before H3 regression.

4. **PI sign-off:** Principal investigator must explicitly authorize H3 execution after reviewing manual coding results.

---

## 12. Expected Output Files (When Executed)

**These files do NOT yet exist and should not be created until regression is authorized.**

| File | Contents |
|------|---------|
| `data/derived/regression/humor_iv_gate6_regression_results.csv` | Coefficient table: model_id, dv, iv, beta, se, t, p, n, r2, fe, controls |
| `data/derived/regression/humor_iv_gate6_model_diagnostics.csv` | Per-model diagnostics: n, n_companies, n_periods, r2, adj_r2, vif_focal_iv |
| `data/audit/regression/humor_iv_gate6_regression_manifest.json` | Execution manifest with constraint flags |
| `docs/humor_iv_gate6_regression_summary.md` | Narrative summary of results |

**Column schema for regression_results.csv:**

```
model_id, hypothesis, dv, window, focal_iv, beta, se_hc3, t_stat, p_value,
ci_lower_95, ci_upper_95, significant_p05, n_obs, n_companies, n_periods,
r_squared, adj_r_squared, fixed_effects, controls, se_type, sample_filter,
iv_nonzero_n, iv_bounded_0_1, iv_provenance_note
```

---

## 13. Gemini Post-Audit Checklist

To be completed after Gate 6 execution:

**DV integrity:**
- [ ] `CAR_0_p3` and `CAR_0_p5` absent from all model specs
- [ ] All DVs are `CAR_m1_p1`, `CAR_m3_p3`, or `CAR_m5_p5`
- [ ] DV source confirmed from `join_ready_for_CAR_<window>` filtered panel

**IV integrity:**
- [ ] No forbidden IV appears in any results row
- [ ] `hc_v2_aggressive_candidate_share` / `_intensity` absent
- [ ] `aggressive_prob_*` (legacy) absent
- [ ] `humor_prob_mean` and `ambiguity_adjusted_humor_share` never in same model
- [ ] H3 IVs only appear in models labeled EXPLORATORY

**Statistical reporting:**
- [ ] HC3 robust SE used (or clustered; document which)
- [ ] No results reported without FE specification
- [ ] R² reported alongside coefficients (not as standalone goodness-of-fit claim)

**Interpretation constraints:**
- [ ] No causal language ("causes", "leads to", "drives", "impacts")
- [ ] No Brand Equity language ("brand value", "brand equity effect")
- [ ] No Tobin's Q reference
- [ ] CAR described as "short-window market reaction proxy" only
- [ ] v2 aggressive candidates labeled "candidate signal" not "confirmed aggressive"
- [ ] H3 results labeled "Exploratory"

**Constraint flags (all must be False in manifest):**
- [ ] `regression_auto_run` = False
- [ ] `causal_claim_made` = False
- [ ] `brand_equity_claimed` = False
- [ ] `tobins_q_initiated` = False
- [ ] `car_used_as_tobins_q` = False
- [ ] `raw_data_modified` = False
- [ ] `forbidden_iv_used` = False
- [ ] `car_0_p3_used` = False
- [ ] `car_0_p5_used` = False

---

*Document status: DESIGN ONLY — regression not executed*  
*Gate 6 manifest: `data/audit/regression/humor_iv_gate6_model_spec_manifest.json`*
