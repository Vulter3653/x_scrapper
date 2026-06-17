# TABLE 1. H1 OLS Results — DV: log1p Engagement Total

**Hypothesis H1:** 유머 게시물은 비유머 게시물보다 더 높은 engagement를 보인다.  
*IV: 유머 여부 (0=non-humor, 1=humor); DV: log1p(좋아요+리트윗+답글+인용+북마크)*

---

| Independent Variables | Model 1:<br>Full Sample OLS | Model 2:<br>Full Sample Time FE | Model 3:<br>Full Sample Time FE+Controls | Model 4:<br>Human-Coded OLS | Model 5:<br>Human-Coded Time FE | Model 6:<br>Human-Coded Time FE+Controls |
|---|---:|---:|---:|---:|---:|---:|
| **Humor** | 0.5008***<br>(0.1130) | 0.4677***<br>(0.1128) | 0.2918***<br>(0.1111) | 0.5043***<br>(0.1418) | 0.3306**<br>(0.1503) | 0.3171**<br>(0.1463) |
| **N** | 978 | 978 | 978 | 597 | 597 | 597 |
| **R²** | 0.020 | 0.165 | 0.249 | 0.021 | 0.197 | 0.260 |
| **Adjusted R²** | 0.019 | 0.128 | 0.214 | 0.019 | 0.142 | 0.205 |
| **Year fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Month fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Hour fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included | Not included | Not included | Included |

---

### Notes

- **DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)
- **Standard errors are reported in parentheses** (non-robust OLS SE)
- \*p < .10, \*\*p < .05, \*\*\*p < .01
- **Models 1–3:** Full sample (N = 978), IV = 유머예측이진 (model-based binary)
- **Models 4–6:** Human-coded sample (N = 597), IV = 유머레이블최종
- **Post format controls:** 텍스트길이, 해시태그수, 멘션수
- **Time FE:** 작성연도, 작성월, 작성시간 fixed effects (first category dropped as reference)
- **Primary model:** Model 3 (Full Sample, Time FE + Controls)
  - H1 판정: coefficient = 0.2918***, SE = 0.1111, p = 0.0088 → supports_H1
