# Controlled OLS Model Specification

**Controls**: text_length, hashtag_count, mention_count
**H3 controls**: mean_text_length, mean_hashtag_count, mean_mention_count (firm-period aggregated)
**emoji_count**: NOT included
**SE**: Classical OLS (s²×(X'X)⁻¹)
**Firm FE**: explicit binary dummies (n_firms−1), NOT C(company_id)

---

## H1 Models

```
1. Plain OLS + controls:
   E[Y] = β0 + β1 HumorPresence + β2 text_length + β3 hashtag_count + β4 mention_count + ε

2. Year+Month FE + controls:
   within-cell: ỹ = β1 H̃umorPresence + β2 t̃ext_length + β3 h̃ashtag_count + β4 m̃ention_count + ε
   (FWL: demeaning by year-month cell)

3. Firm dummy + controls:
   E[Y] = β0 + β1 HumorPresence + β2 text_length + β3 hashtag_count + β4 mention_count
          + Σ γ_j FirmDummy_j + ε

4. Firm dummy + Year+Month FE + controls:
   (FWL: demeaning by joint (firm, year_month) cell)
   within-cell: ỹ = β1 H̃P + β2 t̃l + β3 h̃c + β4 m̃c + ε
```

## H2-1 Models (same structure as H1, focal = aggressive_vs_other)

## H2-2 Models (ref=affiliative; focal = aggressive, self_enhancing, self_defeating)

## H3 Models

```
1. Plain OLS + agg controls:
   E[Ȳ] = β0 + β1 Intensity + β2 Intensity² + β3 mean_tl + β4 mean_hc + β5 mean_mc + ε

2. Year+Month FE + agg controls:
   ⚠ H3 firm-month panel: (firm, period) is unique identifier → month FE absorbs all variation
     → not_estimable_df_resid_zero

3. Firm dummy + agg controls:
   E[Ȳ] = β0 + β1 Intensity + β2 Intensity² + β3 mean_tl + β4 mean_hc + β5 mean_mc
          + Σ γ_j FirmDummy_j + ε

4. Firm dummy + Year FE + agg controls (representative combined FE):
   (FWL: demeaning by joint (firm, year) cell)
   within-cell: ỹ = β1 Ĩ + β2 Ĩ² + β3 m̃tl + β4 m̃hc + β5 m̃mc + ε
```

## Batch1 H3: not_applicable
Batch1 H3 is a firm cross-section (n=88 firms, 1 obs/firm).
With controls (5 vars) + intercept, effective k ≥ 6 for n=88 → unfeasible with firm dummies.
