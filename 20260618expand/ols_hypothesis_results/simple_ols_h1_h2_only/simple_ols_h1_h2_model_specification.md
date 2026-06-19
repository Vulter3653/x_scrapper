# OLS Model Specification — H1 and H2 Diagnostic

## M1 Simple OLS

```
log(1+Engagement_i) = β₀ + β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating + ε_i
```

## M2 기업 더미 변수 OLS (Simple OLS + 99 firm dummies, no intercept)

```
log(1+Engagement_i) = β₁·Aggressive + β₂·Affiliative
                    + β₃·SelfEnhancing + β₄·SelfDefeating
                    + Σ(f=1~99) γ_f · D_firm_f + ε_i
```

인터셉트 없음 (기업 더미 99개가 흡수). reference 기업 없음 (all 99 included).

| Item | M1 | M2 |
|:---|:---|:---|
| DV | log_total_engagement | log_total_engagement |
| Reference category | non_humorous (omitted) | non_humorous (omitted) |
| Controls | NONE | NONE |
| Firm dummies | NONE | 99개 (no reference, no intercept) |
| Time FE | NONE | NONE |
| H3 variables | EXCLUDED | EXCLUDED |
| N | 68,039 | 68,039 |
| k | 5 | 103 |
| df_resid | 68,034 | 67,936 |
| SE type | Classical OLS | Classical OLS |

## Identification Rules

1. non_humorous = reference category (omitted)
2. non_humorous dummy not included in regression
3. HumorPresence dummy not included (avoids perfect multicollinearity)
4. No company_id numeric covariate
5. M2 firm dummies: 99개 더미 직접 포함, 인터셉트 제거 (dummy variable trap 방지)

## Data Source

- `h2_post_level_regression_ready.csv` — N=68,039 Fortune100 posts
- Classifier: domain-adapted TF-IDF LogReg trained on 1,980 Fortune100 human labels (batch1+batch2); predictions only — NOT_A_CANDIDATE level evidence; leakage risk: classifier trained on same corpus as regression sample
