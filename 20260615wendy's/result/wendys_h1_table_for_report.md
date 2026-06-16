# H1 Results Table: Humor Presence and Engagement (log1p_engagement_total)

**Hypothesis H1:** 유머 트윗은 비유머 트윗보다 더 높은 engagement를 보인다.

---

## Table. OLS Regression Results: Effect of Humor on Engagement (Primary DV: log1p_engagement_total)

|  | **Model 1** | **Model 2** | **Model 3** | **Model 4** | **Model 5** | **Model 6** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sample** | Full Sample | Full Sample | Full Sample | Human-Coded | Human-Coded | Human-Coded |
| **Specification** | Simple OLS | Time FE | Time FE + Controls | Simple OLS | Time FE | Time FE + Controls |
| **IV** | Model Probability | Model Probability | Model Probability | Human Label (Binary) | Human Label (Binary) | Human Label (Binary) |
| **Humor (β)** | 1.5214\*\* | 1.0666\*\* | 0.8404\*\* | 0.5043\*\*\* | 0.3306\*\* | 0.3171\*\* |
| | (p = 0.002) | (p = 0.003) | (p = 0.018) | (SE = 0.142) | (p = 0.028) | (p = 0.031) |
| **R²** | 0.009 | 0.157 | 0.248 | 0.021 | 0.197 | 0.260 |
| **Adj R²** | 0.008 | 0.121 | 0.213 | 0.019 | 0.142 | 0.205 |
| **n** | 978 | 978 | 978 | 597 | 597 | 597 |
| **Time FE** | None | Year+Month+Hour | Year+Month+Hour | None | Year+Month+Hour | Year+Month+Hour |
| **Post Format Controls** | None | None | text\_length, hashtag\_count, mention\_count | None | None | text\_length, hashtag\_count, mention\_count |

---

### Notes

- **DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)  
- **Full Sample IV (Models 1–3):** Humor probability from TF-IDF logistic regression model (`p_humor_final_tfidf_logreg`)  
- **Human-Coded Sample IV (Models 4–6):** Binary human label (`유머레이블최종`; 1 = humor, 0 = non-humor)  
- **Parentheses report p-values except Model 4, where standard error is available from the newly generated OLS result.**  
- Time FE: Year FE + Month FE + Hour FE (year+month+hour dummies; reference categories dropped automatically).  
- Post Format Controls: text\_length, hashtag\_count, mention\_count.  
- Significance: \*\*\* p < .01, \*\* p < .05, \* p < .10  

---

### Data Sources

| Model | Source File |
|---|---|
| Model 1 | `result/wendys_h1_simple_ols_results_final_humor.csv` (Simple OLS) |
| Model 2 | `result/wendys_h1_three_post_format_fullsample_probability_results.csv` (M0\_time\_fe\_only) |
| Model 3 | `result/wendys_h1_three_post_format_fullsample_probability_results.csv` (M7\_all\_three) |
| Model 4 | `result/wendys_h1_human_coded_simple_ols_results.csv` (Simple\_OLS) |
| Model 5 | `result/wendys_h1_three_post_format_human_validation_results.csv` (M0\_time\_fe\_only) |
| Model 6 | `result/wendys_h1_three_post_format_human_validation_results.csv` (M7\_all\_three) |

---

### Summary

모든 6개 모형에서 유머 계수(β)는 양수이며 p < .05 수준에서 유의하다. **H1은 지지된다.**

- **Full Sample:** β = 1.5214 (Simple OLS) → 1.0666 (Time FE) → 0.8404 (Time FE + Controls). 시간 고정효과 및 post format controls 추가 후에도 유머의 positive effect가 유지된다.  
- **Human-Coded Sample:** β = 0.5043\*\*\* (Simple OLS) → 0.3306\*\* (Time FE) → 0.3171\*\* (Time FE + Controls). human-coded label 기반에서도 일관된 양의 효과가 확인된다.  
- Model 4 (Human-Coded Simple OLS)는 H1 human validation 표본(n = 597)에서 새로 계산된 OLS 결과이며, coefficient = 0.5043, SE = 0.142, p = 0.0004 (R² = 0.021, Adj R² = 0.019)이다.
