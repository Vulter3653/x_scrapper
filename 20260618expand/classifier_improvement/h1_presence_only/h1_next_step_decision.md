# H1 Next Step Decision

**Date:** 2026-06-18
**Current status:** Classifier performance review complete. H1 regression not yet run.

---

## Current Position

The batch1-only presence classifier (`word_char_comb__lr_liblin_C01`) provisionally passes
the OOF AUC threshold (0.7811 >= 0.75). The question is how to proceed toward H1.

---

## Option A: H1 Descriptive / Preliminary Interpretation Only

**What it means:**
Use batch1 human labels directly as a sample-level description of humor prevalence.
Do not apply the classifier to the full corpus. Report descriptive statistics only.

**What can be reported:**
- In the batch1 human-coded sample (1,482 posts, stratified sample):
  - Humor rate: 648/1,482 = 43.7%
  - This sample is NOT random — it was stratified by labeling strategy
  - Cannot generalize directly to the full 65,245-post corpus
- Presence classifier: provisionally passes AUC >= 0.75 (OOF)

**Appropriate framing:**
"Among the batch1 stratified human-coded posts (n=1,482), 43.7% were coded as humorous.
The classifier provisionally meets the AUC threshold for preliminary H1 analysis.
Full corpus H1 regression remains a future step."

**Limitations:**
- Sample is not a random draw from the full corpus
- 43.7% humor rate reflects stratification design, not true population rate
- Cannot test H1 formally without full corpus classification

**When to choose Option A:**
- batch2 receipt is delayed
- Only descriptive summary of batch1 is needed
- No regression analysis is required in the near term

---

## Option B: Apply Presence Classifier to Full Corpus for Exploratory H1 Regression

**What it means:**
Apply the best presence classifier to the full Fortune 100 post corpus (65,245 posts),
then run a provisional H1 regression on the predicted humor labels.

**Preconditions (all must be met before execution):**
1. `apply_domain_adapted_classifier.py` is updated for presence-only mode
2. Output boundary documentation is written before running
3. H1 regression is clearly labeled "exploratory" / "provisional"
4. Full corpus output is NOT used for H2/H3 (type classification is out of scope)

**Appropriate framing:**
"Using the batch1-only presence classifier (OOF AUC=0.7811), an exploratory H1 regression
was conducted on the full Fortune 100 corpus. Results are provisional and should not be
interpreted as confirmatory evidence."

**Limitations:**
- Classifier is batch1-only (batch2 not incorporated)
- Firm-held-out F1=0.48 suggests limited cross-firm generalizability
- Any H1 regression result must be labeled exploratory
- H2/H3 cannot be derived from this step

**When to choose Option B:**
- Exploratory H1 estimate is needed to inform next research steps
- A quantitative presence estimate for the full corpus is required
- Researcher accepts exploratory framing as sufficient for the current purpose

---

## H2/H3 Status (Unchanged)

| Item | Status | Reason |
|---|---|---|
| H2 (aggressive humor) | BLOCKED | Aggressive detector failed batch1 criteria |
| H3 (moderation) | BLOCKED | Depends on H2 |
| Type classifier (4-class) | BLOCKED | macro-F1 < 0.3448 threshold |

H2/H3 unblock path: receive batch2 → retrain → if aggressive detector passes criteria → apply to corpus → H2/H3 regression.

---

## Recommended Immediate Action

**Option A first.**

Reason: The full corpus application (Option B) requires executing `apply_domain_adapted_classifier.py`
which is currently blocked/BLOCKED in MANIFEST.md. Before executing Option B:
1. Update MANIFEST.md to separate presence-only and type modes
2. Write output boundary documentation
3. Confirm scope is presence-only (not aggressive/type)
4. Obtain explicit authorization to run

For now, batch1 descriptive summary (Option A) is sufficient to characterize the
classifier performance and establish the H1 preliminary framing.

## 2026-06-19 Integrated Corpus Scope Correction

Earlier `full corpus` wording in this H1 presence-only area refers to the Fortune 100 subset based on `20260618expand/data/processed/fortune100_post_master.csv` unless explicitly stated otherwise. Those 65,245-row outputs should be interpreted as Fortune 100 subset classification or Fortune 100 subset simple OLS checks, not as the final integrated collected corpus.

The integrated collected corpus output is maintained separately at `20260618expand/classifier_improvement/h1_presence_only/integrated_collected_corpus/`. It includes Fortune 100 sources plus usable existing legacy brand post datasets such as Wendy's, MoonPie, and Coca-Cola, and reflects the June 18 append workflow audit/raw outputs. Integrated-corpus H1 regression has not been run. H2/H3 remain blocked. Type and aggressive classifiers are not used.

