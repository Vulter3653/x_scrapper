# Integrated Corpus — Descriptive Statistics Memo

**Scope:** Current integrated corpus **before through-2021 backfill**
**Date:** 2026-06-18
**Status:** Exploratory descriptive statistics only — NOT final result

---

## ⚠ Scope Notice

All figures and tables in this memo reflect the **current state of the integrated
collected corpus before through-2021 backfill is completed**. Pre-2022 data
coverage is insufficient. Results should NOT be interpreted as final.

---

## 1. Corpus Overview

| Item | Value |
|---|---|
| Total posts | **68,039** |
| Source datasets | 5 |
| Date range | 2009-11-26 – 2026-06-18 |
| Unique companies | 99 |
| Classifier | word_char_comb__lr_liblin_C01 (batch1-only, provisional) |
| Classifier OOF AUC | 0.7811 |
| Overall humor rate (t50) | **40.4%** |
| Overall humor rate (t40) | 85.6% |
| Overall humor rate (t60) | 5.5% |

---

## 2. Source Breakdown

| Source | N | % of corpus | Humor rate t50 |
|---|---|---|---|
| fortune100 | 65,245 | 95.9% | 38.6% |
| wendys_legacy | 977 | 1.4% | 86.4% |
| moonpie_legacy | 930 | 1.4% | 88.3% |
| cocacola_legacy | 708 | 1.0% | 82.9% |
| fortune100_raw_append | 179 | 0.3% | 40.8% |
| **Total** | **68,039** | 100% | **40.4%** |

**Interpretation note:**
The corpus is overwhelmingly composed of Fortune 100 posts (95.9%).
Legacy brand accounts (Wendy's, MoonPie, Coca-Cola) show substantially higher
classifier-assigned humor rates (83–88%) compared to Fortune 100 (38.6%).
This divergence likely reflects genuine differences in brand voice rather than
classifier noise, but cannot be confirmed without additional human validation.

---

## 3. Year Distribution

| Year | Posts | Humor rate t50 |
|---|---|---|
| 2009 | 1 | 100.0% |
| 2012 | 2 | 100.0% |
| 2015 | 22 | 50.0% |
| 2016 | 1,075 | 33.8% |
| 2017 | 932 | 65.1% |
| 2018 | 1,217 | 81.6% |
| 2019 | 2,047 | 56.2% |
| 2020 | 3,249 | 47.3% |
| 2021 | 7,314 | 40.0% |
| 2022 | 12,523 | 36.2% |
| 2023 | 10,774 | 39.2% |
| 2024 | 8,895 | 40.6% |
| 2025 | 11,729 | 37.5% |
| 2026 | 8,259 | 38.3% |

**Pre-2022 total: 15,859 rows (23.3% of corpus)**
**2022+ total: 52,180 rows (76.7% of corpus)**

The corpus is heavily concentrated in 2022–2026. Early years (2009–2015) have
near-zero coverage. Pre-2022 humor rate estimates are unreliable due to small samples
and source composition bias (legacy brand accounts skew pre-2022 humor rate upward).

---

## 4. Month Distribution

| Month | Posts | Humor rate t50 |
|---|---|---|
| Jan | 4,533 | 35.8% |
| Feb | 5,244 | 42.5% |
| Mar | 5,781 | 39.5% |
| Apr | 6,277 | 39.8% |
| May | 6,742 | 39.9% |
| Jun | 6,030 | 38.5% |
| Jul | 5,356 | 43.3% |
| Aug | 4,860 | 41.5% |
| Sep | 6,069 | 42.1% |
| Oct | 6,741 | 37.2% |
| Nov | 5,613 | 40.0% |
| Dec | 4,793 | 46.2% |

Post count peaks in May (6,742) and October (6,741).
Humor rate peaks in December (46.2%) and dips in January (35.8%).
Monthly variation is modest (range: 35.8%–46.2%), suggesting limited
seasonal humor signal at the classifier level.

---

## 5. Day of Week Distribution

| Day | Posts | Humor rate t50 |
|---|---|---|
| Monday | 11,068 | 41.1% |
| Tuesday | 12,755 | 35.5% |
| Wednesday | 13,600 | 38.1% |
| Thursday | 12,909 | 37.6% |
| Friday | 11,441 | 41.7% |
| Saturday | 3,335 | 54.8% |
| Sunday | 2,931 | 61.4% |

Post volume is concentrated Monday–Friday (weekday: 61,773 = 90.8%).
However, classifier-assigned humor rate is substantially higher on weekends
(Sat 54.8%, Sun 61.4%) compared to weekdays (35.5%–41.7%).

**Interpretation note:**
The weekend humor spike may reflect: (1) weekend posts being genuinely more casual/humorous,
or (2) classifier artifact — weekend posts from legacy brand accounts
(Wendy's, MoonPie with 86–88% humor rate) disproportionately fall on weekends.
The N is also much smaller on weekends, reducing estimate reliability.

---

## 6. Hour Distribution (UTC)

| Hour (UTC) | Posts | Humor rate t50 |
|---|---|---|
| 0–4h | 2,726 | 61.4% avg |
| 5–7h | 581 | 47.5% avg |
| 8–11h | 1,811 | 25.3% avg |
| 12–18h | 40,873 | 38.4% avg |
| 19–23h | 18,048 | 39.3% avg |

Peak posting: 14–18h UTC (approx. 9am–1pm US Eastern = business hours)
Peak humor rate: 3h UTC (66.8%) — but N=446 only
Low humor rate: 11h UTC (19.1%) — N=1,119

**Interpretation note:**
The hour-level humor rate pattern is confounded by:
(1) Small N at early morning UTC (0–7h) inflates variance
(2) Non-Fortune-100 legacy brand posts may skew certain hours
(3) UTC vs. local time mismatch — some firms may post in non-US timezones

---

## 7. Pre-2022 Data Gap — Limitation

### Current state

The current integrated corpus has 23.3% of posts (15,859 rows) from before 2022.
Within this pre-2022 group:
- 2015–2020: only 8,542 rows total (12.6% of corpus)
- 2009–2014: only 3 rows (near-zero)

### Why this matters

Any regression or time-trend analysis using this corpus will be dominated by
2022–2026 observations. Before-2022 firm-period cells will have sparse or zero
representation for most Fortune 100 firms, making:
- Year fixed effects for 2015–2021 unreliable
- Time-trend estimation across full 2015–2026 window unreliable
- Pre/post comparisons across 2021 boundary unreliable

### Through-2021 backfill (pending)

A through-2021 backfill is planned to supplement the pre-2022 gap.
Until that backfill is complete and validated, any analysis covering
the full 2015–2026 range should acknowledge this limitation explicitly.

### Permitted interpretation

Any result from the current corpus should be labeled:
> "current integrated corpus (before through-2021 backfill)"

Not:
> "full historical corpus" or "complete Fortune 100 X post history"

---

## 8. Figures

| File | Content |
|---|---|
| `figures/integrated_temporal_distribution.png` | 4-panel: Year / Month / DoW / Hour — post count + humor rate t50 |
| `figures/integrated_source_breakdown.png` | Source row count and humor rate t50 comparison |

---

## 9. What This Is NOT

- NOT a final characterization of the corpus
- NOT a regression result
- NOT H1 confirmation
- NOT a complete historical record (pre-2022 coverage is insufficient)
- backfill is pending; these numbers will change
