# TABLE 2. H2 OLS Results — DV: log1p Engagement Total

**Hypothesis H2:** 공격적 유머 게시물은 기타 유머 게시물보다 더 높은 engagement를 보인다.  
*IV: 공격적 유머 여부 (0=other humor, 1=aggressive humor); DV: log1p(좋아요+리트윗+답글+인용+북마크)*

---

| Independent Variables | Model 1:<br>Model-Based OLS | Model 2:<br>Model-Based Time FE | Model 3:<br>Model-Based Time FE+Controls | Model 4:<br>Human-Coded OLS | Model 5:<br>Human-Coded Time FE | Model 6:<br>Human-Coded Time FE+Controls |
|---|---:|---:|---:|---:|---:|---:|
| **Aggressive humor** | 0.4684***<br>(0.1518) | 0.5199***<br>(0.1498) | 0.4056***<br>(0.1469) | 0.7074***<br>(0.2052) | 0.7261***<br>(0.1977) | 0.6405***<br>(0.1915) |
| **N** | 564 | 564 | 564 | 278 | 278 | 278 |
| **R²** | 0.017 | 0.228 | 0.319 | 0.041 | 0.381 | 0.450 |
| **Adjusted R²** | 0.015 | 0.167 | 0.262 | 0.038 | 0.283 | 0.354 |
| **Year fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Month fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Hour fixed effects** | Not included | Included | Included | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included | Not included | Not included | Included |

---

### Notes

- **DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)
- **Standard errors are reported in parentheses** (non-robust OLS SE)
- \*p < .10, \*\*p < .05, \*\*\*p < .01
- **Models 1–3:** Model-based humor sample (N = 564), IV = H2공격적유머모델더미
- **Models 4–6:** Human-coded humor sample (N = 278), IV = H2공격적유머인간더미
- **Post format controls:** 텍스트길이, 해시태그수, 멘션수
- **Time FE:** 작성연도, 작성월, 작성시간 fixed effects (first category dropped as reference)
- **Primary model:** Model 3 (Model-Based, Time FE + Controls)
  - H2 판정: coefficient = 0.4056***, SE = 0.1469, p = 0.0060 → supports_H2
