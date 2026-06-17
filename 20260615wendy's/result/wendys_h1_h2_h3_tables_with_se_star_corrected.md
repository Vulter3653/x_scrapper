# Wendy's Twitter Humor Study — Regression Tables (SE, Star-Corrected)

*Coefficient (SE) format. Stars: \*p < .10, \*\*p < .05, \*\*\*p < .01.*  
*DV = log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수) = Consumer Engagement proxy.*

---

## TABLE 1. H1 Results — Effect of Humor on Consumer Engagement
**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)

| | Model 1<br>Full Sample OLS | Model 2<br>Full Sample Time FE | Model 3<br>Full Sample Time FE+Controls | Model 4<br>Human-Coded OLS | Model 5<br>Human-Coded Time FE | Model 6<br>Human-Coded Time FE+Controls |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Humor** | 0.5008***<br>(0.1130) | 0.4677***<br>(0.1128) | 0.2918***<br>(0.1111) | 0.5043***<br>(0.1418) | 0.3306**<br>(0.1503) | 0.3171**<br>(0.1463) |
| **N** | 978 | 978 | 978 | 597 | 597 | 597 |
| **R²** | 0.020 | 0.165 | 0.249 | 0.021 | 0.197 | 0.260 |
| **Adjusted R²** | 0.019 | 0.128 | 0.214 | 0.019 | 0.142 | 0.205 |
| **Year FE** | Not included | Included | Included | Not included | Included | Included |
| **Month FE** | Not included | Included | Included | Not included | Included | Included |
| **Hour FE** | Not included | Included | Included | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included | Not included | Not included | Included |

*Standard errors are reported in parentheses.*  
*\*p < .10, \*\*p < .05, \*\*\*p < .01.*  
*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  
*Time FE: 작성연도, 작성월, 작성시간 dummies (first category as reference).*  
*Models 1–3: Full sample (N = 978), IV = 유머예측이진.*  
*Models 4–6: Human-coded sample (N = 597), IV = 유머레이블최종 (validation).*  
*Primary model: Model 3.*

---

## TABLE 2. H2 Results — Effect of Aggressive Humor on Consumer Engagement
**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)

| | Model 1<br>Model-Based OLS | Model 2<br>Model-Based Time FE | Model 3<br>Model-Based Time FE+Controls | Model 4<br>Human-Coded OLS | Model 5<br>Human-Coded Time FE | Model 6<br>Human-Coded Time FE+Controls |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Aggressive humor** | 0.4684***<br>(0.1518) | 0.5199***<br>(0.1498) | 0.4056***<br>(0.1469) | 0.7074***<br>(0.2052) | 0.7261***<br>(0.1977) | 0.6405***<br>(0.1915) |
| **N** | 564 | 564 | 564 | 278 | 278 | 278 |
| **R²** | 0.017 | 0.228 | 0.319 | 0.041 | 0.381 | 0.450 |
| **Adjusted R²** | 0.015 | 0.167 | 0.262 | 0.038 | 0.283 | 0.354 |
| **Year FE** | Not included | Included | Included | Not included | Included | Included |
| **Month FE** | Not included | Included | Included | Not included | Included | Included |
| **Hour FE** | Not included | Included | Included | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included | Not included | Not included | Included |

*Standard errors are reported in parentheses.*  
*\*p < .10, \*\*p < .05, \*\*\*p < .01.*  
*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  
*Time FE: 작성연도, 작성월, 작성시간 dummies (first category as reference).*  
*Models 1–3: Model-based humor sample (N = 564), IV = H2공격적유머모델더미.*  
*Models 4–6: Human-coded humor sample (N = 278), IV = H2공격적유머인간더미 (validation).*  
*Primary model: Model 3.*

---

## TABLE 3. H3 Results — Moderation of Humor Effect by Humor Usage Intensity
**DV:** log1p(좋아요수 + 리트윗수 + 답글수 + 인용수 + 북마크수)  
**H3 조건:** β4 > 0 AND β5 < 0, both *p* < .05 (역 U자형 조절)

| | Model 1<br>Simple OLS | Model 2<br>Time FE | Model 3<br>Time FE + Controls |
| --- | :---: | :---: | :---: |
| **Humor (β1)** | 0.5447***<br>(0.1467) | 0.4237***<br>(0.1445) | 0.2459*<br>(0.1402) |
| **Intensity centered (β2)** | -0.7579<br>(0.6868) | -2.4916***<br>(0.8834) | -2.3131***<br>(0.8444) |
| **Intensity centered² (β3)** | 0.0351<br>(3.2608) | 2.1714<br>(3.2536) | 2.4663<br>(3.0990) |
| **Humor × Intensity centered (β4)** | 1.6488*<br>(0.8598) | 1.5893*<br>(0.8409) | 1.4176*<br>(0.7997) |
| **Humor × Intensity centered² (β5)** | -1.4275<br>(4.0909) | 2.3622<br>(4.0680) | 1.9648<br>(3.8657) |
| **N** | 960 | 960 | 960 |
| **Quarter count** | 25 | 25 | 25 |
| **R²** | 0.026 | 0.175 | 0.260 |
| **Adjusted R²** | 0.021 | 0.136 | 0.222 |
| **Year FE** | Not included | Included | Included |
| **Month FE** | Not included | Included | Included |
| **Hour FE** | Not included | Included | Included |
| **Post format controls** | Not included | Not included | Included |
| **H3 판정** | **not_support** | **not_support** | **not_support** |

*Standard errors are reported in parentheses.*  
*\*p < .10, \*\*p < .05, \*\*\*p < .01.*  
*Intensity centered: 유머비율LOO분기 − mean(유머비율LOO분기), H3 sample (n = 960) 내부 평균중심화.*  
*Post format controls: 텍스트길이, 해시태그수, 멘션수.*  
*Primary model: Model 3 (Time FE + Controls).*  
*H3 not supported: β4 = 1.4176* (p = 0.0766), β5 = 1.9648 (p = 0.6114, 양수 → 역 U자형 불충족).*
