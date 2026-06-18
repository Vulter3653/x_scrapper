# Limitations and Claim Boundaries

## Analysis Status

**This is an exploratory model-transfer analysis.** Results must not be used as the main Fortune Top 100 hypothesis evidence. The correct evidence hierarchy is:

```
Main evidence:     full_chain_master classification (existing) → 20260618expand/
Supplemental:      Wendy's-classifier transfer (this subpackage) → model_transfer/
```

## Claim Boundary

- This applies the Wendy's-trained classifier to Fortune Top 100 posts.
- This is a model-transfer classification, not a newly human-validated Fortune-wide classifier.
- Full-sample model-based classification remains the main empirical evidence.
- Human-coded labels are supplemental validation evidence only.
- Engagement is an engagement-based brand equity proxy, not brand equity itself.
- X engagement metrics are point-in-time captures.
- The analysis is observational evidence and does not support unrestricted causal claims.

## Model Transfer Limitations

- The binary humor classifier was trained on 597 Wendy's-labeled posts (fast food, active social media presence).
- The four-type classifier was trained on 278 humorous Wendy's posts.
- Fortune Top 100 companies span diverse industries with different communication styles.
- Domain transfer (Wendy's → Fortune Top 100) may introduce systematic misclassification.
- CV performance on Wendy's data (AUC≈0.71 binary, macro-F1≈0.34 four-type) reflects within-domain performance only.
- No human validation of the transferred classifications on Fortune Top 100 posts has been performed.

## Aggressive Humor Classification Note

- The Wendy's-trained model classified 6,857 Fortune Top 100 posts (10.5%) as aggressive humor.
- This is substantially higher than the 95 posts in the original full_chain_master classification.
- The classifier may be overfitting Wendy's aggressive humor patterns (e.g., competitive fast-food roasting language) to Fortune 100 posts with directionally confident or assertive language.
- H2 and H3 results using this classification should be treated as exploratory evidence.

## H3 Note

- H3 used a confirmatory_candidate label because non-zero aggressive intensity rows = 2,066/3,532.
- However, given the domain-transfer quality concerns above, H3 should be treated as exploratory.
- The H3 shape is U-shaped (β1<0, β2>0), which does not match the predicted inverted-U (β1>0, β2<0).

## Engagement DV

- total_engagement = reply_count + repost_count + like_count + quote_count.
- bookmark_count is excluded from the DV.
- This may differ from the earlier 20260615 Wendy's-only DV.
