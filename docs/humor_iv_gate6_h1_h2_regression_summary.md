# Gate 6A — H1/H2 Regression Results

**Date:** 2026-06-14
**Status:** H1 and H2 executed; H3 blocked (pending human validation)
**Design commit:** f264e38895559fec6edc7f388e57b25be5c3c366
**Models run:** 46 total (19 H1, 27 H2)
**Failed models:** 0

---

## Interpretation Constraints

> **CAR is a short-window market reaction proxy only.** Results must not be described as evidence of causal effects on brand equity, firm value, or Tobin's Q. All associations are observational. Significant coefficients reflect correlation, not causation.

> **v2 aggressive candidates are unvalidated candidate signals.** H2 results using v2-based IVs are not evidence of true aggressive humor presence.

---

## H1 Results: Humor Presence and Market Reaction

**Hypothesis:** Greater probability-weighted humor presence is associated with higher CAR.

**Primary IV:** `humor_prob_mean` (bounded [0,1]; mean P(humor) per firm-period; 100% nonzero)

**Overall H1 verdict:** No significant associations at p < 0.10.

### H1 Primary Models (humor_prob_mean × 3 DVs)

| Model | IV | β | SE (HC3) | p-value | n | R² |
|-------|----|----|----------|---------|---|-----|
| H1a_gate6_CAR_m1_p1            | humor_prob_mean                | +0.0046 | 0.0449 | 0.918 NS     | 430 | 0.051 |
| H1a_gate6_CAR_m3_p3            | humor_prob_mean                | -0.0159 | 0.0543 | 0.769 NS     | 430 | 0.048 |
| H1a_gate6_CAR_m5_p5            | humor_prob_mean                | -0.0475 | 0.0709 | 0.503 NS     | 430 | 0.071 |

*† p<0.10  * p<0.05  ** p<0.01  NS = not significant*

### H1 Robustness Models

| Model | IV | DV | β | p-value |
|-------|----|----|---|---------|
| H1b_share_CAR_m1_p1                 | hc_humor_share                 | CAR_m1_p1    | +0.0072 | 0.610 NS     |
| H1b_binary_CAR_m1_p1                | hc_humor_presence_any          | CAR_m1_p1    | +0.0021 | 0.731 NS     |
| H1b_logcount_CAR_m1_p1              | hc_log_humor_count             | CAR_m1_p1    | -0.0010 | 0.832 NS     |
| H1b_scoresum_CAR_m1_p1              | humor_candidate_score_sum      | CAR_m1_p1    | -0.0001 | 0.813 NS     |
| H1b_share_CAR_m3_p3                 | hc_humor_share                 | CAR_m3_p3    | +0.0138 | 0.385 NS     |
| H1b_binary_CAR_m3_p3                | hc_humor_presence_any          | CAR_m3_p3    | +0.0020 | 0.792 NS     |
| H1b_logcount_CAR_m3_p3              | hc_log_humor_count             | CAR_m3_p3    | +0.0013 | 0.796 NS     |
| H1b_scoresum_CAR_m3_p3              | humor_candidate_score_sum      | CAR_m3_p3    | +0.0002 | 0.597 NS     |
| H1b_share_CAR_m5_p5                 | hc_humor_share                 | CAR_m5_p5    | -0.0117 | 0.549 NS     |
| H1b_binary_CAR_m5_p5                | hc_humor_presence_any          | CAR_m5_p5    | -0.0030 | 0.721 NS     |
| H1b_logcount_CAR_m5_p5              | hc_log_humor_count             | CAR_m5_p5    | -0.0026 | 0.626 NS     |
| H1b_scoresum_CAR_m5_p5              | humor_candidate_score_sum      | CAR_m5_p5    | +0.0002 | 0.651 NS     |
| H1a_compFE_CAR_m1_p1                | humor_prob_mean                | CAR_m1_p1    | +0.0348 | 0.616 NS     |
| H1a_compFE_CAR_m3_p3                | humor_prob_mean                | CAR_m3_p3    | +0.0322 | 0.704 NS     |
| H1a_compFE_CAR_m5_p5                | humor_prob_mean                | CAR_m5_p5    | +0.0051 | 0.960 NS     |


---

## H2 Results: Aggressive Humor Candidate Signal and Market Reaction

**Hypothesis:** Greater aggressive humor candidate signal is associated with differential CAR.

**Primary IV:** `hc_v2_aggressive_candidate_count` (firm-level count; NOT confirmed aggressive)

**Overall H2 verdict:** 15 model(s) significant at p < 0.10 — see table.

### H2 Primary Models (hc_v2_aggressive_candidate_count × 3 DVs)

| Model | IV | β | SE (HC3) | p-value | n | R² |
|-------|----|----|----------|---------|---|-----|
| H2a_gate6_CAR_m1_p1            | hc_v2_aggressive_candidate_count    | +0.0031 | 0.0014 | 0.027 *      | 430 | 0.058 |
| H2a_gate6_CAR_m3_p3            | hc_v2_aggressive_candidate_count    | +0.0036 | 0.0017 | 0.035 *      | 430 | 0.055 |
| H2a_gate6_CAR_m5_p5            | hc_v2_aggressive_candidate_count    | +0.0040 | 0.0020 | 0.044 *      | 430 | 0.078 |


### H2 Robustness Models

| Model | IV | DV | β | p-value |
|-------|----|----|---|---------|
| H2a_logv2_CAR_m1_p1                 | hc_log_v2_aggressive_candidate      | CAR_m1_p1    | +0.0078 | 0.052 †      |
| H2a_logv2_CAR_m3_p3                 | hc_log_v2_aggressive_candidate      | CAR_m3_p3    | +0.0093 | 0.032 *      |
| H2a_logv2_CAR_m5_p5                 | hc_log_v2_aggressive_candidate      | CAR_m5_p5    | +0.0105 | 0.041 *      |
| H2a_binary_CAR_m1_p1                | hc_v2_aggressive_candidate_presence | CAR_m1_p1    | +0.0067 | 0.206 NS     |
| H2a_binary_CAR_m3_p3                | hc_v2_aggressive_candidate_presence | CAR_m3_p3    | +0.0109 | 0.053 †      |
| H2a_binary_CAR_m5_p5                | hc_v2_aggressive_candidate_presence | CAR_m5_p5    | +0.0121 | 0.070 †      |
| H2b_scoresum_CAR_m1_p1              | aggressive_candidate_score_sum      | CAR_m1_p1    | +0.0221 | 0.488 NS     |
| H2b_scoresum_CAR_m3_p3              | aggressive_candidate_score_sum      | CAR_m3_p3    | +0.0574 | 0.074 †      |
| H2b_scoresum_CAR_m5_p5              | aggressive_candidate_score_sum      | CAR_m5_p5    | +0.0701 | 0.087 †      |
| H2b_scoremean_CAR_m1_p1             | aggressive_candidate_score_mean     | CAR_m1_p1    | +0.2846 | 0.667 NS     |
| H2b_scoremean_CAR_m3_p3             | aggressive_candidate_score_mean     | CAR_m3_p3    | +1.3033 | 0.240 NS     |
| H2b_scoremean_CAR_m5_p5             | aggressive_candidate_score_mean     | CAR_m5_p5    | +1.0341 | 0.564 NS     |
| H2b_scoremax_CAR_m1_p1              | aggressive_candidate_score_max      | CAR_m1_p1    | +0.0308 | 0.340 NS     |
| H2b_scoremax_CAR_m3_p3              | aggressive_candidate_score_max      | CAR_m3_p3    | +0.0570 | 0.121 NS     |
| H2b_scoremax_CAR_m5_p5              | aggressive_candidate_score_max      | CAR_m5_p5    | +0.0518 | 0.347 NS     |
| H2c_rare_CAR_m1_p1                  | hc_rare_class_candidate_count       | CAR_m1_p1    | -0.0014 | 0.711 NS     |
| H2c_rare_CAR_m3_p3                  | hc_rare_class_candidate_count       | CAR_m3_p3    | +0.0103 | 0.019 *      |
| H2c_rare_CAR_m5_p5                  | hc_rare_class_candidate_count       | CAR_m5_p5    | +0.0161 | 0.000 **     |
| H2c_rarelogg_CAR_m1_p1              | hc_log_rare_class_candidate         | CAR_m1_p1    | -0.0035 | 0.617 NS     |
| H2c_rarelogg_CAR_m3_p3              | hc_log_rare_class_candidate         | CAR_m3_p3    | +0.0164 | 0.040 *      |
| H2c_rarelogg_CAR_m5_p5              | hc_log_rare_class_candidate         | CAR_m5_p5    | +0.0273 | 0.001 **     |
| H2c_rarebinary_CAR_m1_p1            | hc_rare_class_candidate_presence    | CAR_m1_p1    | -0.0049 | 0.486 NS     |
| H2c_rarebinary_CAR_m3_p3            | hc_rare_class_candidate_presence    | CAR_m3_p3    | +0.0119 | 0.131 NS     |
| H2c_rarebinary_CAR_m5_p5            | hc_rare_class_candidate_presence    | CAR_m5_p5    | +0.0230 | 0.003 **     |


---

## Consistency with Gate 3

Gate 3 (Extended CAR Regression, commit `f5caa90`) found no significant H1–H3 associations across all three CAR windows using the original IVs (`humor_share`, `self_enhancing_share`, `aggressive_share`). Gate 6A uses reconstructed probability-weighted IVs.

---

## H3 Status

**H3 NOT executed.** Blocked pending:
1. Human coding of `humor_candidate_manual_audit_sample.csv`
2. Inter-rater reliability ≥ κ 0.60
3. PI sign-off

---

## Constraint Verification

| Constraint | Status |
|-----------|--------|
| H3 not run | ✅ True |
| Forbidden IVs not used | ✅ True |
| CAR_0_p3 not used | ✅ True |
| CAR_0_p5 not used | ✅ True |
| causal_claim_made | ✅ False |
| brand_equity_claimed | ✅ False |
| tobins_q_initiated | ✅ False |
| v2 candidate as ground truth | ✅ False |
| raw_data_modified | ✅ False |

*Gate 6A manifest: `data/audit/regression/humor_iv_gate6_h1_h2_regression_manifest.json`*
