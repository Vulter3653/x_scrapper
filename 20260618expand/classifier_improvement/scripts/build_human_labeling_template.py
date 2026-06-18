"""
build_human_labeling_template.py

Generates the human labeling template CSV from the candidate set.
Adds empty label columns for reviewers to fill in.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"
OUT_TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
OUT_INSTRUCTIONS = CI / "data" / "human_labeling_template" / "labeling_instructions_quick_ref.md"

VALID_PRESENCE = {"humor", "non_humor", "uncertain"}
VALID_TYPE = {"aggressive", "affiliative", "self_enhancing", "self_defeating", "non_humorous", "uncertain"}

LABEL_COLS = [
    "human_humor_presence",
    "human_humor_type",
    "human_confidence",
    "human_notes",
    "reviewer_id",
    "review_status",
]

BASE_COLS = [
    "candidate_id", "sampling_stratum",
    "fortune_rank", "company_name", "source_x_handle",
    "tweet_id", "tweet_url", "created_at", "text",
    "total_engagement",
    "wendys_transfer_humor_presence", "wendys_transfer_humor_type",
    "full_chain_humor_presence", "full_chain_humor_type",
    "classifier_disagreement_flag",
]


def main() -> None:
    print("=== build_human_labeling_template ===")

    if not CANDIDATES.exists():
        print(f"ERROR: candidates file not found: {CANDIDATES}")
        raise SystemExit(1)

    with open(CANDIDATES, newline="", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    print(f"  candidates: {len(candidates)}")

    fieldnames = BASE_COLS + LABEL_COLS
    rows = []
    for r in candidates:
        row = {col: r.get(col, "") for col in BASE_COLS}
        row.update({
            "human_humor_presence": "",
            "human_humor_type": "",
            "human_confidence": "",
            "human_notes": "",
            "reviewer_id": "",
            "review_status": "pending",
        })
        rows.append(row)

    OUT_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_TEMPLATE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Template → {OUT_TEMPLATE}")

    # Quick reference instructions
    with open(OUT_INSTRUCTIONS, "w", encoding="utf-8") as f:
        f.write("""# Human Labeling Quick Reference

## Column: human_humor_presence

Allowed values: `humor` | `non_humor` | `uncertain`

- `humor`: The post uses humor as an intentional communication device.
- `non_humor`: The post is a standard announcement, news, or informational post with no humor intent.
- `uncertain`: You cannot determine whether the post is humorous, or the post is ambiguous.

## Column: human_humor_type

Allowed values: `aggressive` | `affiliative` | `self_enhancing` | `self_defeating` | `non_humorous` | `uncertain`

- Fill this column only if `human_humor_presence = humor`.
- If `human_humor_presence = non_humor`, set this to `non_humorous`.
- If `human_humor_presence = uncertain`, set this to `uncertain`.

## Column: human_confidence

Enter a number from 1 to 3:
- `1`: Low confidence — the post is genuinely ambiguous
- `2`: Medium confidence
- `3`: High confidence

## Column: human_notes

Free text. Use to explain edge cases, flag issues, or note reasons for uncertain judgments.

## Column: reviewer_id

Your reviewer identifier (e.g., coder1, coder2, etc.)

## Column: review_status

- `pending`: not yet reviewed
- `complete`: reviewed by at least one reviewer
- `needs_second_review`: flagged for a second opinion
""")
    print(f"  Instructions → {OUT_INSTRUCTIONS}")
    print("=== build_human_labeling_template COMPLETE ===")


if __name__ == "__main__":
    main()
