"""
build_coder_labeling_splits.py

Splits the 1,500-row Fortune Top 100 labeling template into three 500-row
files for three coders (random seed 42, simple shuffle-and-split).

Outputs:
  data/human_labeling_template/coder_splits/coder1_labeling_template.csv
  data/human_labeling_template/coder_splits/coder2_labeling_template.csv
  data/human_labeling_template/coder_splits/coder3_labeling_template.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_coder.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_stratum.csv
  data/human_labeling_template/coder_splits/LABELING_GUIDE.md
"""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"

RANDOM_SEED = 42
CODERS = ["coder1", "coder2", "coder3"]

# Required column order: human-entry fields immediately after text
PRIORITY_COLS = [
    "candidate_id",
    "sampling_stratum",
    "fortune_rank",
    "company_name",
    "source_x_handle",
    "tweet_id",
    "tweet_url",
    "created_at",
    "text",
    "human_humor_presence",
    "human_humor_type",
    "assigned_coder",
    "review_status",
]
REFERENCE_COLS = [
    "total_engagement",
    "log_total_engagement",
    "wendys_transfer_humor_presence",
    "wendys_transfer_humor_score",
    "wendys_transfer_humor_type",
    "wendys_transfer_type_score",
    "full_chain_humor_presence",
    "full_chain_humor_type",
    "classifier_disagreement_flag",
    "uncertainty_score",
]

LABELING_GUIDE_TEXT = """\
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
"""


def load_template() -> tuple[list[dict], list[str]]:
    for path in [TEMPLATE, CANDIDATES]:
        if path.exists():
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
    raise FileNotFoundError(f"Neither template nor candidates file found.")


def build_fieldnames(source_fieldnames: list[str]) -> list[str]:
    seen = set(PRIORITY_COLS)
    extra_ref = [c for c in REFERENCE_COLS if c in source_fieldnames and c not in seen]
    leftover = [c for c in source_fieldnames
                if c not in seen and c not in set(REFERENCE_COLS)]
    return PRIORITY_COLS + extra_ref + leftover


def main() -> None:
    print("=== build_coder_labeling_splits ===")

    rows, source_fieldnames = load_template()
    print(f"  Input rows: {len(rows)}")
    assert len(rows) == 1500, f"Expected 1500 rows, got {len(rows)}"

    # Check no duplicate candidate_ids
    cids = [r["candidate_id"] for r in rows]
    assert len(set(cids)) == len(cids), "Duplicate candidate_ids in input"

    # Shuffle and split
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(rows)
    splits = {
        "coder1": rows[0:500],
        "coder2": rows[500:1000],
        "coder3": rows[1000:1500],
    }

    fieldnames = build_fieldnames(source_fieldnames)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    # Write coder files
    for coder, coder_rows in splits.items():
        out = SPLITS_DIR / f"{coder}_labeling_template.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for row in coder_rows:
                row_out = dict(row)
                row_out["human_humor_presence"] = ""
                row_out["human_humor_type"] = ""
                row_out["assigned_coder"] = coder
                row_out["review_status"] = "pending"
                w.writerow(row_out)
        print(f"  {coder}: {len(coder_rows)} rows → {out.name}")

    # Summary by coder
    by_coder_path = SPLITS_DIR / "coder_assignment_summary_by_coder.csv"
    with by_coder_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "assigned_coder", "n_rows", "n_unique_candidate_id",
            "n_unique_tweet_id", "note",
        ])
        w.writeheader()
        for coder, coder_rows in splits.items():
            w.writerow({
                "assigned_coder": coder,
                "n_rows": len(coder_rows),
                "n_unique_candidate_id": len({r["candidate_id"] for r in coder_rows}),
                "n_unique_tweet_id": len({r["tweet_id"] for r in coder_rows}),
                "note": "",
            })
        # Totals / overlap check
        all_cids = set()
        all_tids = set()
        overlap_cid = 0
        overlap_tid = 0
        for coder_rows in splits.values():
            cids_set = {r["candidate_id"] for r in coder_rows}
            tids_set = {r["tweet_id"] for r in coder_rows}
            overlap_cid += len(cids_set & all_cids)
            overlap_tid += len(tids_set & all_tids)
            all_cids |= cids_set
            all_tids |= tids_set
        w.writerow({
            "assigned_coder": "TOTAL",
            "n_rows": 1500,
            "n_unique_candidate_id": len(all_cids),
            "n_unique_tweet_id": len(all_tids),
            "note": f"overlap_candidate_id={overlap_cid} overlap_tweet_id={overlap_tid}",
        })
    print(f"  Summary by coder → {by_coder_path.name}")

    # Summary by stratum
    by_stratum_path = SPLITS_DIR / "coder_assignment_summary_by_stratum.csv"
    stratum_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"coder1": 0, "coder2": 0, "coder3": 0})
    for coder, coder_rows in splits.items():
        for r in coder_rows:
            stratum_counts[r.get("sampling_stratum", "unknown")][coder] += 1
    with by_stratum_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sampling_stratum", "coder1", "coder2", "coder3", "total"])
        w.writeheader()
        for stratum, counts in sorted(stratum_counts.items()):
            total = sum(counts.values())
            w.writerow({"sampling_stratum": stratum, **counts, "total": total})
    print(f"  Summary by stratum → {by_stratum_path.name}")

    # LABELING_GUIDE.md
    guide_path = SPLITS_DIR / "LABELING_GUIDE.md"
    guide_path.write_text(LABELING_GUIDE_TEXT, encoding="utf-8")
    print(f"  Labeling guide → {guide_path.name}")

    print("=== build_coder_labeling_splits COMPLETE ===")


if __name__ == "__main__":
    main()
