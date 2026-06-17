# TABLE 3. H3 Moderation Results — DV: log1p Engagement Total

**Hypothesis H3:** 유머 게시물의 engagement 효과는 humor usage intensity에 따라 역 U자형으로 조절된다.  
*H3 지지 조건: β4 (Humor × Intensity) > 0 AND β5 (Humor × Intensity²) < 0, both p < .05*

---

| Independent Variables | Model 1:<br>Simple OLS | Model 2:<br>Time FE | Model 3:<br>Time FE + Controls |
| --------------------- | ---------------------: | ------------------: | -----------------------------: |
| **Humor** | 0.5447***<br>(SE = 0.147) | 0.4237***<br>(SE = 0.145) | 0.2459*<br>(SE = 0.140) |
| **Intensity centered** | -0.7579<br>(SE = 0.687) | -2.4916***<br>(SE = 0.883) | -2.3131***<br>(SE = 0.844) |
| **Intensity centered²** | 0.0351<br>(SE = 3.261) | 2.1714<br>(SE = 3.254) | 2.4663<br>(SE = 3.099) |
| **Humor × Intensity centered** | 1.6488*<br>(SE = 0.860) | 1.5893*<br>(SE = 0.841) | 1.4176*<br>(SE = 0.800) |
| **Humor × Intensity centered²** | -1.4275<br>(SE = 4.091) | 2.3622<br>(SE = 4.068) | 1.9648<br>(SE = 3.866) |
| **N** | 960 | 960 | 960 |
| **Quarter count** | 25 | 25 | 25 |
| **R²** | 0.026 | 0.175 | 0.260 |
| **Adjusted R²** | 0.021 | 0.136 | 0.222 |
| **Year fixed effects** | Not included | Included | Included |
| **Month fixed effects** | Not included | Included | Included |
| **Hour fixed effects** | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included |
| **H3 interpretation** | not_support | not_support | **not_support** |

---

### Notes

- **DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)
- **Standard errors are reported in parentheses** (non-robust OLS SE)
- \*p < .10, \*\*p < .05, \*\*\*p < .01
- **Intensity centered:** 유머비율LOO분기 − mean(유머비율LOO분기), H3 analysis sample (n = 960) 내부에서 평균중심화
- **Post format controls (Model 3):** 텍스트길이, 해시태그수, 멘션수
- **Time FE:** 작성연도, 작성월, 작성시간 fixed effects (first category dropped as reference)
- **Primary model:** Model 3 (Time FE + Controls)
- **H3 판정: 지지되지 않음 (not_support)**
  - β4 (Humor × IC) = 1.4176, p = 0.0766 (미유의)
  - β5 (Humor × IC²) = 1.9648, p = 0.6114 (양수: 역 U자형 예측과 반대 방향)
  - H3 지지 조건(β4 > 0 AND β5 < 0, both p < .05) 미충족
