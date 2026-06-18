# Labeling Guide — Fortune Top 100 Human Humor Coding

This file provides coding instructions for annotators using the coder split
labeling templates (coder1_labeling_template.csv, coder2_labeling_template.csv,
coder3_labeling_template.csv).

---

## How to Use the Template

1. Open your assigned CSV file.
2. Read the `text` column for each row.
3. Fill in ONLY the following two columns:
   - `human_humor_presence`
   - `human_humor_type`
4. Leave all other columns unchanged.
5. Do not add, remove, or rename columns.

---

## human_humor_presence

**Allowed values:**

| Value | Meaning |
|---|---|
| `humor` | Post contains intentional humorous expression |
| `non_humor` | Post is informational, promotional, announcement, CSR, etc. — no humor |
| `uncertain` | Humor presence is genuinely ambiguous; cannot be determined with confidence |

**Decision rule:**

Ask: "Is this post intentionally trying to be funny?"

- Yes → `humor`
- No → `non_humor`
- Cannot tell → `uncertain`

---

## human_humor_type

**Allowed values:**

| Value | When to use |
|---|---|
| `aggressive` | Humor that disparages, teases, mocks, or attacks a target |
| `affiliative` | Humor that builds warmth, connection, positive in-group feeling |
| `self_enhancing` | Humor about absurd situations; brand laughs at the situation |
| `self_defeating` | Brand laughs at its own expense; self-deprecating |
| `non_humorous` | Use when human_humor_presence = non_humor |
| `uncertain` | Use when human_humor_presence = uncertain, or type is ambiguous |

**Entry rule based on human_humor_presence:**

```
human_humor_presence = humor
  → enter one of: aggressive / affiliative / self_enhancing / self_defeating

human_humor_presence = non_humor
  → enter: non_humorous

human_humor_presence = uncertain
  → enter: uncertain
```

---

## Critical Distinction: Corporate Assertiveness vs. Aggressive Humor

This is the most important coding distinction for Fortune Top 100 posts.

**Corporate assertive language should not be coded as aggressive humor unless it
contains a clear humor cue AND target-directed teasing, sarcasm, roast-like
language, playful attack, or disparagement.**

| Feature | Corporate Assertiveness | Aggressive Humor |
|---|---|---|
| Tone | Confident, direct | Joking, roast-like, sarcastic |
| Target | None (about self or product) | Specific target (competitor, institution) |
| Humor cue | None | Explicit joke or comedic frame |
| Example | "We're the market leader." | "Sorry, [Rival], but we win again 😏" |

**Default rule:** If there is no clear joke and no target of ridicule, code as
`non_humor`, not `aggressive`.

---

## Uncertain Cases

Use `uncertain` when:
- The humor intent requires cultural context you do not have
- The post is mildly playful but could be either personality or humor
- You genuinely cannot decide after reading the full text

Do NOT force a label when uncertain.

---

## Reference Columns (Do Not Edit)

The following columns are pre-filled for reference. Do not modify them:

- `wendys_transfer_humor_presence` / `wendys_transfer_humor_type` — Wendy's classifier output
- `full_chain_humor_presence` / `full_chain_humor_type` — full-chain classifier output
- `classifier_disagreement_flag` — 1 if the two classifiers disagree
- `uncertainty_score` — classifier uncertainty (higher = more uncertain)
- `assigned_coder` — your coder assignment (do not change)
- `review_status` — leave as `pending` until your review is complete, then change to `complete`
