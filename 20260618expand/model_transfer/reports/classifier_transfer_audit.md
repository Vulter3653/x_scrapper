# Classifier Transfer Audit

## Wendy's Classifier Summary

| Item | Value |
|---|---|
| Model | TF-IDF + Logistic Regression (two-stage) |
| Stage 1 | Binary humor presence (humor vs. non-humor) |
| Stage 2 | Four-type multinomial (aggressive/affiliative/self-enhancing/self-defeating) |
| Training source | `20260615wendy's/result/wendys_humor_review_sheet.csv` |
| Training labels (binary) | 597 labeled rows |
| Training labels (4-type) | 278 humorous rows with valid type |
| 4-type class distribution | {'affiliative': 106, 'aggressive': 95, 'self-enhancing': 62, 'self-defeating': 15} |
| Saved model artifact | None — model retrained from Wendy's labels at runtime |
| Threshold (binary) | 0.5 |

## Stage 1 (Binary) Hyperparameters

```
TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True)
LogisticRegression(class_weight='balanced', solver='liblinear', max_iter=1000, random_state=42)
```

CV result (Stratified 5-fold on Wendy's labeled data):

| Metric | Value |
|---|---|
| Accuracy | 0.6600 |
| F1 | 0.6937 |
| ROC-AUC | 0.7095 |

## Stage 2 (Four-Type) Hyperparameters

```
TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True, max_features=5000)
LogisticRegression(multi_class='multinomial', solver='lbfgs', class_weight='balanced',
                   max_iter=1000, random_state=42)
```

CV result (Stratified 5-fold on Wendy's 4-type labeled data):

| Metric | Value |
|---|---|
| Accuracy | 0.4282 |
| Macro-F1 | 0.3448 |

## Fortune Top 100 Classification Result

| Metric | Value |
|---|---|
| Total input posts | 65245 |
| Classified OK | 65245 |
| Failed (empty text) | 0 |
| humor_presence = 1 | 28177 (43.19%) |
| humor_presence = 0 | 37068 (56.81%) |

Humor type distribution:

| Type | Count |
|---|---|
| non_humorous | 37068 |
| affiliative | 19101 |
| aggressive | 6857 |
| self-enhancing | 1994 |
| self-defeating | 225 |


## Claim Boundary

- This applies the Wendy's-trained classifier to Fortune Top 100 posts.
- This is a model-transfer classification, not a newly human-validated Fortune-wide classifier.
- Full-sample model-based classification remains the main empirical evidence.
- Human-coded labels are supplemental validation evidence only.
- Engagement is an engagement-based brand equity proxy, not brand equity itself.
- X engagement metrics are point-in-time captures.
- The analysis is observational evidence and does not support unrestricted causal claims.
