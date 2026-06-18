# Human Labeling Strategy — Fortune Top 100 Humor Classification

## Purpose

This document defines the coding criteria for human reviewers labeling Fortune Top 100 posts as humor vs. non-humor, and classifying humor type. These criteria are designed specifically for the Fortune Top 100 corporate brand voice context, NOT Wendy's fast-food brand patterns.

---

## Humor Presence Coding

### `humor`: Humorous post

Code as `humor` when the post uses humor as an intentional communication device. Signals include:

- Puns, wordplay, or double meanings
- Jokes, riddles, or comedic setups
- Irony, sarcasm, or self-deprecation
- Memes, playful imagery references, or viral formats
- Exaggeration for comic effect
- Playful, non-serious tone that would produce laughter or amusement in the target audience

### `non_humor`: Non-humorous post

Code as `non_humor` for:

- Standard corporate announcements, product launches, event promotions
- Earnings or financial disclosures
- Customer service replies
- CSR/ESG statements
- Promotional language with no humor intent
- News or informational posts

### `uncertain`: Ambiguous post

Code as `uncertain` when:

- The humor intent is unclear (culturally specific, requires external context)
- The post uses mild playfulness that could be either light corporate personality or genuine humor
- You genuinely cannot determine intent with reasonable confidence

---

## Humor Type Coding

Code humor type ONLY when `human_humor_presence = humor`.

### `aggressive`

Aggressive humor involves disparagement, teasing, competitive taunting, sarcasm at the expense of others, or roast-like language directed at a target.

Criteria:
- Contains a clear humor cue (not merely directness or confidence)
- Contains target-directed disparagement, teasing, sarcasm, or playful attack
- Target may be: competitor, cultural institution, industry norm, or occasionally the brand's own audience in a playful roast

**Domain-Transfer Warning for Fortune 100 Coding:**

> **Corporate assertive language should not be automatically coded as aggressive humor unless it contains a clear humor cue AND target-directed disparagement, teasing, sarcasm, roast-like language, or playful attack.**

Examples of what is NOT aggressive humor (common Fortune 100 false positives):
- Bold marketing claims ("We dominate the market")
- Competitive product comparisons with no comedic framing
- Confident brand statements
- Industry leadership assertions

Examples of what IS aggressive humor:
- Playfully mocking a competitor by name with a joke
- Sarcastic response to a negative news event about a rival
- Roast-style commentary on industry trends

### `affiliative`

Affiliative humor creates warmth, connection, and positive in-group feeling. It invites the audience to laugh with the brand.

Criteria:
- Lighthearted, inclusive, feel-good humor
- Celebrates shared experiences, holidays, or community moments
- Self-referential jokes that build brand personality without targeting anyone negatively
- Playful engagement with fans or followers

### `self_enhancing`

Self-enhancing humor maintains a positive, amused perspective even in challenging or absurd situations. The brand laughs at the situation rather than a target.

Criteria:
- Jokes about product quirks, industry absurdities, or work situations
- Ironic or wry observations about the brand's own context
- "We know this is weird and we're owning it" type humor
- Brand coping humorously with external challenges

### `self_defeating`

Self-defeating humor involves the brand laughing at its own expense, acknowledging flaws, mistakes, or weaknesses in a humorous way.

Criteria:
- Self-deprecating jokes about the brand's own shortcomings
- Humor that acknowledges failure or vulnerability
- Rare in Fortune 100 context — apply conservatively
- Do NOT code negative self-commentary without a clear humor intent as self-defeating

---

## Uncertain Handling

If `human_humor_presence = uncertain`:
- Set `human_humor_type = uncertain`
- Add a brief note in `human_notes` explaining the ambiguity

---

## Common Distinction: Corporate Assertiveness vs. Aggressive Humor

This is the most critical distinction for Fortune Top 100 coding.

| Feature | Corporate Assertiveness | Aggressive Humor |
|---|---|---|
| Tone | Confident, direct | Playful, joking, roast-like |
| Target | None (about self/product) | Specific target (competitor, institution) |
| Humor cue | None | Explicit joke structure or comedic frame |
| Example | "We're the market leader in X" | "Sorry [CompetitorName], but we win again 🏆😉" |

**Key rule**: Confident or assertive brand language without a clear joke structure or comedic frame is `non_humor`, not `aggressive`.

---

## Coding Confidence

- `1` = Low: Genuinely ambiguous; you could defend either label
- `2` = Medium: Reasonably confident, but some uncertainty remains
- `3` = High: Clear-cut case with no ambiguity

---

## Labeling Checklist

Before submitting each row:

1. Read the full text in context (not just a keyword)
2. Ask: "Is this intentionally trying to be funny?"
3. If yes: ask "Who or what is the target, if any?"
4. If corporate assertive language without a joke — code `non_humor`
5. If genuinely unclear — code `uncertain` rather than forcing a label
6. Fill `human_confidence` (1–3) and `human_notes` for edge cases
