# Wendy's Humor Presence Scoring Audit

Generated: 2026-06-15 10:47 UTC

## Run Configuration

- **source_raw_file:** `data/wendys/posts.json`
- **working_raw_file:** `20260615wendy's/data/wendys_posts_raw.json`
- **output_csv:** `20260615wendy's/result/wendys_humor_presence_scores.csv`
- **output_jsonl:** `20260615wendy's/result/wendys_humor_presence_scores.jsonl`

## Summary Statistics

- **total_posts:** 978
- **mean_humor_score:** 0.0720
- **median_humor_score:** 0.0000
- **min_humor_score:** 0.000
- **max_humor_score:** 1.000

## Band Distribution

- **very_low** (0.000–0.199): 847
- **low** (0.200–0.399): 49
- **medium** (0.400–0.599): 55
- **high** (0.600–0.799): 21
- **very_high** (0.800–1.000): 6

- **number_humor_present_050:** 78
- **share_humor_present_050:** 0.0798 (8.0%)

## Language and Retweet

- **number_english_posts:** 917
- **number_non_english_or_undefined_posts:** 61
- **number_retweet_text_posts:** 26

## Date Range

- **date_min:** Fri Apr 03 03:00:14 +0000 2026
- **date_max:** Wed Sep 22 15:10:45 +0000 2021

## Interpretation Constraints

- humor_score is a transparent deterministic rule-based score, NOT a calibrated probability.
- humor_present_050 is a convenience binary threshold, NOT the primary variable.
- No aggressive humor classification was performed.
- No four-type humor type classification was performed.
- No regression was run. No causal claims are made.

## Score Examples

### very_high examples (top 5 by score)

- **id:** 2057589742649192842
  - **created_at:** Thu May 21 22:29:57 +0000 2026
  - **text:** it's not roasting if it's true 😌 @Jeopardy https://t.co/Da3mvCbEFB
  - **humor_score:** 1.0
  - **humor_score_band:** very_high
  - **humor_present_050:** 1
  - **reason:** sarcasm or irony detected
  - **components:** sarcasm_irony; roast_teasing; pop_culture_reference; brand_persona; casual_conversational_tone

- **id:** 2064726596179706275
  - **created_at:** Wed Jun 10 15:09:15 +0000 2026
  - **text:** Her: Gimme 10 Me: minutes or nuggets?
  - **humor_score:** 0.928
  - **humor_score_band:** very_high
  - **humor_present_050:** 1
  - **reason:** joke-like question-answer structure detected
  - **components:** joke_qa_structure; pun_wordplay

- **id:** 1510643384419037186
  - **created_at:** Sun Apr 03 15:40:23 +0000 2022
  - **text:** STIUCSIB KCAB ERA STIUCSIB KCUB
  - **humor_score:** 0.908
  - **humor_score_band:** very_high
  - **humor_present_050:** 1
  - **reason:** absurd or surreal phrasing detected
  - **components:** absurdity_surrealism; pun_wordplay; non_english_or_undefined

- **id:** 1480986154765885443
  - **created_at:** Tue Jan 11 19:33:09 +0000 2022
  - **text:** There’s still one more holiday that’s just around the corner, and I know exactly what you’re getting 🔥🔥🔥  See ya tomorrow for National Roast Day 😉
  - **humor_score:** 0.896
  - **humor_score_band:** very_high
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; roast_teasing; casual_conversational_tone

- **id:** 1266395345996652552
  - **created_at:** Fri May 29 15:45:53 +0000 2020
  - **text:** We’re moving National Roast Day because there are going to be better times for it. Love you guys.
  - **humor_score:** 0.835
  - **humor_score_band:** very_high
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; roast_teasing


### high examples (top 5 by score)

- **id:** 2056803537636467033
  - **created_at:** Tue May 19 18:25:51 +0000 2026
  - **text:** might change my name to Wemby’s and only serve french fries after last night’s game
  - **humor_score:** 0.743
  - **humor_score_band:** high
  - **humor_present_050:** 1
  - **reason:** absurd or surreal phrasing detected
  - **components:** absurdity_surrealism; pop_culture_reference

- **id:** 1255937272907776001
  - **created_at:** Thu Apr 30 19:09:14 +0000 2020
  - **text:** Come and see the Wendy-est Mortys in the entire multiverse. We’re playing with Wendy Morty and Breakfast Morty in Pocket Mortys! Check out our stream right now: https://t.co/sQfjVH1iaa
  - **humor_score:** 0.71
  - **humor_score_band:** high
  - **humor_present_050:** 1
  - **reason:** absurd or surreal phrasing detected
  - **components:** absurdity_surrealism; brand_persona

- **id:** 1485407829506904069
  - **created_at:** Mon Jan 24 00:23:18 +0000 2022
  - **text:** Tune in for the cool and crispy moves on the Knuckle Huck while crushing some of those hot and crispy Official Fries of X Games Aspen. (That’s our fries)
  - **humor_score:** 0.703
  - **humor_score_band:** high
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; pop_culture_reference

- **id:** 1555191949707169794
  - **created_at:** Thu Aug 04 14:00:29 +0000 2022
  - **text:** Y’all sure know how to make a personified brand feel special 😊 Vote on the Top 8 fry proposals below! You have 24hrs, most likes wins free Hot &amp; Crispy for a year #ChooseHotAndCrispy
  - **humor_score:** 0.67
  - **humor_score_band:** high
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; brand_persona

- **id:** 1488512462223667201
  - **created_at:** Tue Feb 01 14:00:00 +0000 2022
  - **text:** Hot or cold? Doesn’t matter because any drank in a Wendy’s cup is free when you grab one of our breakfast sammies.
  - **humor_score:** 0.67
  - **humor_score_band:** high
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; brand_persona


### medium examples (top 5 by score)

- **id:** 1996659770724696551
  - **created_at:** Thu Dec 04 19:16:00 +0000 2025
  - **text:** im hot and im cold https://t.co/BVtiB1CiRA
  - **humor_score:** 0.56
  - **humor_score_band:** medium
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay

- **id:** 1510659635933548556
  - **created_at:** Sun Apr 03 16:44:58 +0000 2022
  - **text:** RT @Wendys: Who do you have to WIN. IT. ALL?!  8. North Carolina or 1. Kansas?  Tweet your CHAMP and we’ll @ you with how you did plus send…
  - **humor_score:** 0.56
  - **humor_score_band:** medium
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay; retweet_text

- **id:** 1481295012646334468
  - **created_at:** Wed Jan 12 16:00:26 +0000 2022
  - **text:** It’s #NationalRoastDay™  Drop the “roast me” below 👇  Oh, and don’t forget to get free medium fries with purchase, in the app. Gotta do something with all this salt.
  - **humor_score:** 0.56
  - **humor_score_band:** medium
  - **humor_present_050:** 1
  - **reason:** roast or teasing language detected
  - **components:** roast_teasing; casual_conversational_tone

- **id:** 1463554140190265344
  - **created_at:** Wed Nov 24 17:04:33 +0000 2021
  - **text:** How do you eat our hot and crispy fries?
  - **humor_score:** 0.56
  - **humor_score_band:** medium
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay

- **id:** 1455253881135538184
  - **created_at:** Mon Nov 01 19:22:17 +0000 2021
  - **text:** Ghosts, ghouls, monsters. None of these are nearly as terrifying as cold and soggy fries. Try Wendy’s new hot and crispy fries and save yourself the scares.  https://t.co/l2VERKj3PO
  - **humor_score:** 0.56
  - **humor_score_band:** medium
  - **humor_present_050:** 1
  - **reason:** pun or wordplay detected
  - **components:** pun_wordplay


### very_low examples (bottom 5 by score)

- **id:** 2064504139749417369
  - **created_at:** Wed Jun 10 00:25:18 +0000 2026
  - **text:** What does one wear to meet a minion
  - **humor_score:** 0.0
  - **humor_score_band:** very_low
  - **humor_present_050:** 0
  - **reason:** insufficient textual humor signal
  - **components:** insufficient_text_signal

- **id:** 2060406022825554333
  - **created_at:** Fri May 29 17:00:50 +0000 2026
  - **text:** 50% off on Sat &amp; Sun too 💅
  - **humor_score:** 0.0
  - **humor_score_band:** very_low
  - **humor_present_050:** 0
  - **reason:** insufficient textual humor signal
  - **components:** insufficient_text_signal

- **id:** 2060405944735957384
  - **created_at:** Fri May 29 17:00:32 +0000 2026
  - **text:** rich asf craving the new Ice Spicy Meal on DoorDash https://t.co/kVe28gJjYt
  - **humor_score:** 0.0
  - **humor_score_band:** very_low
  - **humor_present_050:** 0
  - **reason:** insufficient textual humor signal
  - **components:** insufficient_text_signal

- **id:** 2060393163458498982
  - **created_at:** Fri May 29 16:09:45 +0000 2026
  - **text:** 28 and 10? Fine. Free FRENCH fries in the app with $5 purchase for everybody (including aliens 👽)
  - **humor_score:** 0.0
  - **humor_score_band:** very_low
  - **humor_present_050:** 0
  - **reason:** plain promotion without clear humor
  - **components:** plain_promotion

- **id:** 2059700189909111001
  - **created_at:** Wed May 27 18:16:07 +0000 2026
  - **text:** Big star energy. Pocket-sized legends. https://t.co/oNQdB0s9Mn
  - **humor_score:** 0.0
  - **humor_score_band:** very_low
  - **humor_present_050:** 0
  - **reason:** insufficient textual humor signal
  - **components:** insufficient_text_signal
