"""validate_coder_labeling_splits.py"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"
CODERS = ["coder1", "coder2", "coder3"]
ROWS_PER_CODER = 500
TOTAL_ROWS = 1500


def main() -> int:
    failures: list[str] = []

    # 1. coder files exist
    for coder in CODERS:
        p = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if not p.exists():
            failures.append(f"missing: {p.name}")

    # 2. LABELING_GUIDE.md exists
    guide = SPLITS_DIR / "LABELING_GUIDE.md"
    if not guide.exists():
        failures.append("missing: LABELING_GUIDE.md")
    else:
        guide_text = guide.read_text(encoding="utf-8")
        if "Corporate assertive" not in guide_text and "corporate assertive" not in guide_text.lower():
            failures.append("LABELING_GUIDE.md must contain corporate assertiveness warning")
        for val in ["humor", "non_humor", "uncertain", "aggressive", "affiliative",
                    "self_enhancing", "self_defeating", "non_humorous"]:
            if val not in guide_text:
                failures.append(f"LABELING_GUIDE.md missing allowed value: {val}")

    # 3. Load all coder files and check structure
    all_cids: set[str] = set()
    all_tids: set[str] = set()
    cid_sets: dict[str, set[str]] = {}
    tid_sets: dict[str, set[str]] = {}

    for coder in CODERS:
        p = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if not p.exists():
            continue

        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        # row count
        if len(rows) != ROWS_PER_CODER:
            failures.append(f"{coder}: expected {ROWS_PER_CODER} rows, got {len(rows)}")

        # column order: text -> human_humor_presence -> human_humor_type
        if "text" not in fieldnames:
            failures.append(f"{coder}: missing 'text' column")
        if "human_humor_presence" not in fieldnames:
            failures.append(f"{coder}: missing 'human_humor_presence' column")
        if "human_humor_type" not in fieldnames:
            failures.append(f"{coder}: missing 'human_humor_type' column")

        if "text" in fieldnames and "human_humor_presence" in fieldnames:
            idx_text = fieldnames.index("text")
            idx_hhp = fieldnames.index("human_humor_presence")
            if idx_hhp != idx_text + 1:
                failures.append(
                    f"{coder}: human_humor_presence must immediately follow text "
                    f"(text@{idx_text}, human_humor_presence@{idx_hhp})"
                )

        if "human_humor_presence" in fieldnames and "human_humor_type" in fieldnames:
            idx_hhp = fieldnames.index("human_humor_presence")
            idx_hht = fieldnames.index("human_humor_type")
            if idx_hht != idx_hhp + 1:
                failures.append(
                    f"{coder}: human_humor_type must immediately follow human_humor_presence "
                    f"(human_humor_presence@{idx_hhp}, human_humor_type@{idx_hht})"
                )

        # assigned_coder matches filename
        wrong_coder = [r for r in rows if r.get("assigned_coder", "") != coder]
        if wrong_coder:
            failures.append(
                f"{coder}: {len(wrong_coder)} rows have wrong assigned_coder value"
            )

        # review_status default = pending
        non_pending = [r for r in rows if r.get("review_status", "") != "pending"]
        if non_pending:
            failures.append(
                f"{coder}: {len(non_pending)} rows have review_status != 'pending'"
            )

        # human_humor_presence and human_humor_type are blank
        non_blank_presence = [r for r in rows if r.get("human_humor_presence", "").strip()]
        non_blank_type = [r for r in rows if r.get("human_humor_type", "").strip()]
        if non_blank_presence:
            failures.append(f"{coder}: {len(non_blank_presence)} rows have non-blank human_humor_presence")
        if non_blank_type:
            failures.append(f"{coder}: {len(non_blank_type)} rows have non-blank human_humor_type")

        cid_set = {r["candidate_id"] for r in rows}
        tid_set = {r["tweet_id"] for r in rows}
        cid_sets[coder] = cid_set
        tid_sets[coder] = tid_set

        # unique candidate_id within file
        all_file_cids = [r["candidate_id"] for r in rows]
        if len(set(all_file_cids)) != len(all_file_cids):
            failures.append(f"{coder}: duplicate candidate_ids within file")

    # 4. Cross-coder overlap
    coders_with_data = [c for c in CODERS if c in cid_sets]
    for i, c1 in enumerate(coders_with_data):
        for c2 in coders_with_data[i+1:]:
            cid_overlap = cid_sets[c1] & cid_sets[c2]
            if cid_overlap:
                failures.append(
                    f"candidate_id overlap between {c1} and {c2}: {len(cid_overlap)} ids"
                )
            tid_overlap = tid_sets[c1] & tid_sets[c2]
            if tid_overlap:
                failures.append(
                    f"tweet_id overlap between {c1} and {c2}: {len(tid_overlap)} ids"
                )

    # 5. Total rows = 1,500
    total = sum(len(v) for v in cid_sets.values())
    if total != TOTAL_ROWS and len(coders_with_data) == len(CODERS):
        failures.append(f"total assigned rows = {total}, expected {TOTAL_ROWS}")

    # 6. At least one summary file exists
    summary_files = list(SPLITS_DIR.glob("coder_assignment_summary*.csv"))
    if not summary_files:
        failures.append("missing: coder_assignment_summary*.csv (at least one required)")

    if failures:
        print("VALIDATION FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
