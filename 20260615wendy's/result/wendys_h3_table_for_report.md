# TABLE 3. H3 Moderation Results — DV: log1p Engagement Total

**Hypothesis H3:** 유머 게시물의 engagement 효과는 humor usage intensity에 따라 역 U자형으로 조절된다.  
*H3 지지 조건: β4 (Humor × Intensity) > 0 AND β5 (Humor × Intensity²) < 0, both p < .05*

---

| Independent Variables | Model 1:<br>Simple OLS | Model 2:<br>Time FE | Model 3:<br>Time FE + Controls |
| --------------------- | ---------------------: | ------------------: | -----------------------------: |
| **Humor** | .5447\*\*\*<br>(SE = .147) | .4237\*\*<br>(SE = .145) | .2459\*<br>(SE = .140) |
| **Intensity centered** | −.7579<br>(SE = .687) | −2.4916\*\*<br>(SE = .883) | −2.3131\*\*<br>(SE = .844) |
| **Intensity centered²** | .0351<br>(SE = 3.261) | 2.1714<br>(SE = 3.254) | 2.4663<br>(SE = 3.099) |
| **Humor × Intensity centered** | 1.6488<br>(SE = .860) | 1.5893<br>(SE = .841) | 1.4176<br>(SE = .800) |
| **Humor × Intensity centered²** | −1.4275<br>(SE = 4.091) | 2.3622<br>(SE = 4.068) | 1.9648<br>(SE = 3.866) |
| **N** | 960 | 960 | 960 |
| **Quarter count** | 25 | 25 | 25 |
| **R²** | .026 | .175 | .260 |
| **Adjusted R²** | .021 | .136 | .222 |
| **Year fixed effects** | Not included | Included | Included |
| **Month fixed effects** | Not included | Included | Included |
| **Hour fixed effects** | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included |
| **H3 interpretation** | weak\_support | **not\_support** | **not\_support** |

---

### Notes

- **DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)
- **Intensity centered:** 유머비율LOO분기 − mean(유머비율LOO분기), H3 sample(n = 960) 내부에서 평균중심화
- **Post format controls (Model 3):** 텍스트길이, 해시태그수, 멘션수
- **Parentheses report standard errors** for all models (computed from OLS residual variance)
- Significance: \*\*\* p < .01, \*\* p < .05, \* p < .10
- **Primary model:** Model 3 (Time FE + Controls)
- **H3 판정: 지지되지 않음 (not\_support)**
  - β4 (Humor × IC) = +1.4176, p = .077 (양수이나 미유의)
  - β5 (Humor × IC²) = +1.9648, p = .611 (양수, 역 U자형 예측과 반대 방향)
  - 역 U자형 조절 조건(β4 > 0 AND β5 < 0, both p < .05)을 충족하지 않음
