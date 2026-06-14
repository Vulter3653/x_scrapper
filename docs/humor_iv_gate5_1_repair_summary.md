# Gate 5.1 — Paper-Grounded Humor IV Reconstruction Repair: Summary

**Based on:** Gate 5 commit `d4c20be22c71185bd3bb7609d76a20acc5e060b8`
**Script:** `scripts/build_humor_iv_gate5_1_repair.py`
**Status:** COMPLETED — pre-regression measurement audit, no regression run

---

## 1. Why Gate 5.1 Was Necessary

Gate 5 (commit `d4c20be`) produced 31 candidate IVs but received CONDITIONAL PASS with five open concerns:

1. **Manual validation sample missing** — no human-auditable post sample for aggressive candidate review
2. **Probability score provenance not audited** — `aggressive_prob_sum` formula not validated against HSQ-grounded aggressive probability definition
3. **Share/intensity values potentially exceeding 1** — normalization consistency unchecked
4. **v2 candidate misinterpretation risk** — `v2_aggressive_candidate_count` treated as a per-period post count when it may be a firm-level value
5. **No HSQ-grounded codebook or variable dictionary** — lack of paper-anchored definitions for the classification taxonomy

Gate 5.1 addresses all five concerns without running any regressions or modifying existing data.

---

## 2. Literature Reflected in Gate 5.1

### 2.1 Martin et al. (2003) — Humor Styles Questionnaire (HSQ)

**What it provides:** Four humor type definitions (affiliative, self-enhancing, aggressive, self-defeating) grounded in empirical personality psychology research.

**How reflected:**
- `docs/humor_iv_hsq_based_codebook.md` operationalizes all four types for brand SNS text
- Aggressive humor cue inventory (sarcasm, ridicule, derision, put-down, disparagement, hostile comparison, offensive joke)
- Self-defeating humor cue inventory (brand self-deprecation, approval-seeking self-mockery, humor-as-deflection)
- Boundary rules between adjacent types (affiliative vs. aggressive; self-enhancing vs. self-defeating)
- Explicit limit: HSQ is an individual psychology measure; no brand personality profiling from classification output

### 2.2 CCPA Assurance AI Working Paper

**What it provides:** Multi-measurement operationalization framework; threshold sensitivity analysis; parallel binary/continuous/intensity IV construction.

**How reflected:**
- Binary, count, log-transformed, share, and intensity variants maintained in parallel (not collapsed into one canonical IV)
- Threshold sensitivity grid: humor probability [0.40–0.60], aggressive score [0.30–0.60], self-defeating score [0.30–0.60]
- `data/derived/regression/humor_iv_threshold_sensitivity_gate5_1.csv` documents how nonzero coverage varies across thresholds
- H3 feasibility thresholds: `< 30` = blocked; `30–50` = exploratory only; `≥ 50 and bounded` = limited robustness possible

### 2.3 Brand/Personality ML and Social Media Text-Score Literature

**What it provides:** Soft-label IV construction from probability scores; preservation of ambiguous posts; post-level score aggregation methods.

**How reflected:**
- Corrected `aggressive_candidate_score` formula: `ml_humor_probability × humor_type_confidence` for classified posts (unified with ambiguous posts' `ml_humor_probability × base_rate`)
- Probability-weighted aggregations: `aggressive_candidate_score_sum`, `aggressive_candidate_score_intensity_bounded` (÷ total_posts)
- Ambiguous posts preserved at full weight; NOT dropped or excluded
- Manual audit sample (`data/derived/validation/humor_candidate_manual_audit_sample.csv`) enables human validation per literature best practice

---

## 3. Gate 5 Findings Confirmed by Gate 5.1

| Finding | Details |
|---------|---------|
| `aggressive_candidate_score_sum` is the most viable H3 continuous IV | nonzero=399/430 (92.8%) in primary sample |
| `hc_v2_aggressive_candidate_count` is the most viable H2 count IV | 60.2% nonzero (259/430) |
| `hc_rare_class_candidate_intensity_bounded` viable H3 alternative | nonzero=85/430 (19.8%) |
| H1 probability-weighted IVs (`humor_prob_sum`, `humor_prob_mean`) are 100% nonzero | Resolves H1 zero-inflation |

---

## 4. Problems Corrected in Gate 5.1

### 4.1 `aggressive_prob_*` Formula Inconsistency (CRITICAL)

**Problem:** Gate 5's `aggressive_prob` used `humor_type_confidence` directly for classified aggressive posts, while using `ml_humor_probability × base_rate` for ambiguous posts. This is inconsistent: the former is P(type=aggressive | classified as humor), while the latter is P(humor) × P(aggressive|humor). The classified posts' formula was missing the `ml_humor_probability` factor.

**Fix:** Corrected formula: `aggressive_candidate_score = ml_humor_probability × humor_type_confidence` for classified aggressive posts. Both pathways now compute the same joint probability: P(post is humor) × P(type=aggressive | humor).

**Rename required:** `aggressive_prob_*` → `aggressive_candidate_score_*`

### 4.2 `v2_aggressive_candidate_count` is a Firm-Level Fixed Value (CRITICAL)

**Problem:** `v2_aggressive_candidate_count` exceeds `total_posts` in 189/3767 firm-periods (max ratio = 9.0). For example, Albertsons shows v2_count = 7 across multiple periods regardless of how many posts were in that period. This means the variable is a **firm-level score**, not a per-period post count.

**Implication:** `hc_v2_aggressive_candidate_share` (= v2_count/total_posts) and `hc_v2_aggressive_candidate_intensity` (= v2_count/humor_count) are **INVALID** — they produce values up to 8.0 and 7.0 respectively, violating the share/intensity [0,1] expectation.

**Fix:** `hc_v2_aggressive_candidate_count` (raw count) is retained as a valid H2 count IV. All normalized variants (share, intensity) are flagged as invalid and excluded from H2/H3 candidates.

### 4.3 `hc_rare_class_candidate_intensity` Exceeds 1

**Problem:** `rare_class_candidate_count / humor_count` exceeds 1.0 (max = 2.0).

**Fix:** Bounded version `hc_rare_class_candidate_intensity_bounded = rare_class_count / total_posts` — confirmed bounded [0,1].

### 4.4 `aggressive_prob_sum` Maximum = 1.0141

**Problem:** `aggressive_prob_sum` slightly exceeds 1.0 in some firm-periods due to the inconsistent formula.

**Fix:** Corrected formula bounds the per-post score at `ml_humor_probability × humor_type_confidence ≤ 1.0`; the sum is unbounded (renamed to `aggressive_candidate_score_sum`). The intensity-bounded variant `aggressive_candidate_score_intensity_bounded` (÷ total_posts) is confirmed bounded [0,1].

---

## 5. IV Validity Status

### Usable IVs (Gates 5.1 Approved)

| IV | Hypothesis | Nonzero% | Bounded | Recommended Use |
|----|-----------|---------|---------|----------------|
| `humor_prob_sum` | H1 | 100% | No (sum) | Probability-weighted count; rename to `humor_candidate_score_sum` |
| `humor_prob_mean` | H1 | 100% | Yes | Ambiguity-adjusted humor share; valid [0,1] |
| `ambiguity_adjusted_humor_share` | H1 | 100% | Yes | Same as humor_prob_mean; valid |
| `hc_humor_count` | H1 | 66.7% | No (count) | Count IV; same as existing |
| `hc_v2_aggressive_candidate_count` | H2 | 60.2% | No (count) | BEST H2 candidate; use as count only |
| `hc_log_v2_aggressive_candidate` | H2 | 60.2% | No (log) | Log-transformed count |
| `hc_v2_aggressive_candidate_presence` | H2 | 60.2% | Yes (binary) | Binary presence; valid |
| `aggressive_candidate_score_sum` | H2/H3 | 92.8% | No (sum) | Best H3 continuous; corrected formula |
| `aggressive_candidate_score_intensity_bounded` | H3 | 92.8% | Yes | BEST H3 bounded intensity; primary H3 candidate |
| `hc_rare_class_candidate_intensity_bounded` | H3 | 19.8% | Yes | H3 alternative; limited robustness |
| `sd_candidate_score_intensity_bounded` | H3 | 92.8% | Yes | Self-defeating alt; exploratory |

### Invalid / Do-Not-Use IVs

| IV | Reason |
|----|--------|
| `hc_v2_aggressive_candidate_share` | v2_count > total_posts; max = 8.0 |
| `hc_v2_aggressive_candidate_intensity` | v2_count > humor_count; max = 7.0 |
| `hc_v2_aggressive_candidate_intensity_bounded` | Still exceeds 1 (firm-level value) |
| `hc_rare_class_candidate_intensity` | Exceeds 1.0 (max = 2.0) |
| `aggressive_prob_sum` (legacy) | Inconsistent formula; max > 1.0 |
| `aggressive_prob_intensity` (legacy) | Legacy formula + wrong denominator |
| `top_k_aggressive_score` / `top_k_aggressive_type_confidence` | H3 BLOCKED: nonzero = 5/430 |
| `hc_negative_humor_intensity` | H3 BLOCKED: nonzero = 9/430 |

---

## 6. H3 Limited Robustness Candidates

| IV | Nonzero (primary, n=430) | Bounded | Verdict |
|----|------------------------|---------|---------|
| `aggressive_candidate_score_intensity_bounded` | 399 (92.8%) | Yes | **limited_robustness_possible** |
| `aggressive_candidate_score_sum` | 399 (92.8%) | No (sum) | limited_robustness_possible |
| `hc_rare_class_candidate_intensity_bounded` | 85 (19.8%) | Yes | limited_robustness_possible |
| `sd_candidate_score_intensity_bounded` | 399 (92.8%) | Yes | limited_robustness_possible (H3 alt) |

**Important constraints on H3 regression (when run):**
- H3 remains **exploratory** regardless of nonzero count
- `v2_aggressive_candidate_count` as a firm-level value must NOT be used as intensity denominator
- All H3 results must be reported with pre-registered exploratory label
- No causal interpretation

---

## 7. Conditions Remaining Before Regression

| Condition | Status |
|-----------|--------|
| HSQ codebook documented | ✅ `docs/humor_iv_hsq_based_codebook.md` |
| Probability score provenance audited | ✅ `humor_iv_probability_score_provenance.csv` |
| Share/intensity sanity checked | ✅ `humor_iv_candidate_sanity_checks.csv` |
| Corrected bounded H3 candidates created | ✅ Gate 5.1 panel |
| Manual validation sample created | ✅ 546 posts, 6 groups |
| Human coding of manual validation sample | ❌ **PENDING — required before H3 regression** |
| v2_aggressive_candidate_count provenance resolved | ❌ **PENDING — confirm whether firm-level or per-period** |
| Threshold sensitivity reviewed | ✅ |
| IV final selection for regression | ❌ **PENDING — gate for regression entry** |

---

## 8. Prohibited Interpretations

> The following interpretations are expressly forbidden regardless of empirical results.

- **No causal claims:** Association between humor type and abnormal returns does not imply that humor *caused* the market reaction.
- **No Brand Equity claims:** CAR is not a direct or proxy measure of brand equity. Results must not be described as evidence of humor affecting brand value.
- **No Tobin's Q:** Tobin's Q analysis has been deferred and must not begin without explicit authorization.
- **No v2 ground truth labeling:** `v2_aggressive_candidate_count` is a candidate signal, not a confirmed aggressive classification.
- **No regression run:** No regression may be executed without completing human validation of the manual audit sample and resolving the v2 firm-level provenance question.
- **No raw data modification:** The full_chain master, hypothesis_variables, and regression_master files must not be modified.

---

*Gate 5.1 completed — commit pending*
