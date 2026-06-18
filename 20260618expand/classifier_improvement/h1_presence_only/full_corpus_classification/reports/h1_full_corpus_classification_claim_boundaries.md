# H1 Full Corpus Classification — Claim Boundaries

**Date:** 2026-06-18

---

## Permitted Claims

- "The batch1-only presence classifier was applied to the collected Fortune 100 post corpus."
- "The output is provisional and intended for exploratory H1 analysis."
- "Humor probability and threshold-based labels are available for future H1 robustness checks."
- "38.6% of classified posts received a t50 humor label under the provisional classifier."
- "Humor rate ranges from 4.8% (t60) to 85.0% (t40) across thresholds, reflecting calibration uncertainty."
- "The provisional classifier (OOF AUC=0.7811) was applied; firm-held-out F1=0.4770 limits cross-firm claims."

---

## Prohibited Claims

These must NOT appear in any report, paper, or presentation using this output.

| Prohibited claim | Why prohibited |
|---|---|
| "H1 is supported." | H1 regression has not been run |
| "The final H1 classifier is validated." | Batch1-only; provisional status only |
| "This is confirmatory evidence." | Exploratory/provisional classification only |
| "H2/H3 can be tested from this output." | Type/aggressive labels not generated here |
| "Aggressive humor classification is available." | Aggressive detector not applied |
| "Fortune 100 companies use humor X% of the time (final)." | Classifier is not final; threshold choice matters |
| "The humor rate is [X]% (final estimate)." | Must be labeled provisional / classifier-dependent |
| "Cross-firm humor differences are confirmed." | Firm-held-out F1=0.4770; generalization limited |

---

## H1 Status

**H1 regression: NOT yet run.** This classification output is a precursor input only.

When H1 regression is conducted (future step), it must be labeled:
- "exploratory" or "preliminary"
- With explicit citation of classifier limitations
- With threshold sensitivity analysis across t40/t50/t60

---

## H2/H3 Status

**H2/H3: BLOCKED.** Not addressable from this output.
Type classifier failed batch1 threshold. Aggressive detector failed batch1 criteria.
