#!/usr/bin/env python3
"""Build a priority human-review sample from v1 vs v2 humor type comparison output.

This script treats v2 as a human-review candidate generator, not as a
production replacement classifier. It prioritizes rows where v1 and v2 disagree
in ways that matter for research validity: ambiguous resolution, rare-class
expansion, humor/non-humor boundary reversals, and low-confidence v2 decisions.

Input:
  data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv

Outputs:
  data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv
  data/audit/humor/evaluation/humor_type_human_review_priority_manifest.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

DEFAULT_INPUT = Path("data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv")
DEFAULT_OUTPUT = Path("data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv")
DEFAULT_MANIFEST = Path("data/audit/humor/evaluation/humor_type_human_review_priority_manifest.json")

HUMOR_LABELS = {"affiliative", "self_enhancing", "aggressive", "self_defeating"}
AMBIGUOUS_LABELS = {"ambiguous_or_review", "ambiguous_review", "ambiguous"}
NOT_HUMOR_LABELS = {"not_humor", "not_applicable", "non_humor"}

OUTPUT_FIELDS = [
    "priority",
    "segment",
    "global_post_id",
    "company_name",
    "source_x_handle",
    "text",
    "v1_label",
    "v2_humor_label",
    "transition_type",
    "v1_confidence",
    "v2_confidence",
    "v2_review_flag",
    "v2_reason_code",
    "v2_target_of_humor",
    "v2_humor_function",
    "review_question",
    "human_label",
    "human_confidence",
    "adjudication_notes",
]


def norm(value: object) -> str:
    return str(value or "").strip()


def lower(value: object) -> str:
    return norm(value).lower()


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(norm(value))
    except (TypeError, ValueError):
        return default


def parse_bool(value: object) -> bool:
    return lower(value) in {"1", "true", "yes", "y"}


def is_ambiguous(label: str) -> bool:
    return lower(label) in AMBIGUOUS_LABELS


def is_humor(label: str) -> bool:
    return lower(label) in HUMOR_LABELS


def is_not_humor(label: str) -> bool:
    return lower(label) in NOT_HUMOR_LABELS


def load_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "global_post_id",
            "company_name",
            "source_x_handle",
            "text",
            "v1_label",
            "v2_label",
            "transition_type",
            "v2_confidence",
            "v2_review_flag",
            "v2_reason_code",
            "v2_target_of_humor",
            "v2_humor_function",
        }
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise SystemExit(f"Input missing required columns: {missing}")
        return list(reader)


def select_rows(
    rows: Sequence[Dict[str, str]],
    predicate: Callable[[Dict[str, str]], bool],
    limit: int | None,
    claimed: set[str],
    seed: int,
    sort_low_confidence: bool = False,
) -> Tuple[List[Dict[str, str]], int]:
    candidates = [r for r in rows if norm(r.get("global_post_id")) not in claimed and predicate(r)]
    available = len(candidates)
    if sort_low_confidence:
        candidates.sort(key=lambda r: (parse_float(r.get("v2_confidence"), 1.0), norm(r.get("global_post_id"))))
    else:
        rng = random.Random(seed)
        rng.shuffle(candidates)
    if limit is not None:
        candidates = candidates[:limit]
    for row in candidates:
        claimed.add(norm(row.get("global_post_id")))
    return candidates, available


def review_question_for(segment: str) -> str:
    questions = {
        "v1_ambiguous_to_v2_rare_humor": "Does this post truly contain aggressive or self-defeating humor, or did v2 force a rare label from weak lexical cues?",
        "v1_humor_to_v2_not_humor": "Was v1 over-inclusive, or is v2 incorrectly filtering a valid humor instance as not_humor?",
        "v1_not_humor_to_v2_humor": "Did v2 recover a missed humor instance, or is it misclassifying promotional/positive copy as humor?",
        "v1_positive_humor_to_v2_aggressive": "Is the target actually ridiculed or criticized, or is v2 over-reading friendly brand banter as aggressive humor?",
        "v1_ambiguous_to_v2_not_humor": "Is this genuine non-humor/noise, or did v2 discard context-dependent humor that v1 could not classify?",
        "low_confidence_or_review_flag": "Why did v2 mark this as low-confidence or review-worthy, and what final human label is justified?",
    }
    return questions.get(segment, "Assign a human-adjudicated humor label and explain the decision.")


def build_output_row(row: Dict[str, str], priority: str, segment: str) -> Dict[str, str]:
    return {
        "priority": priority,
        "segment": segment,
        "global_post_id": norm(row.get("global_post_id")),
        "company_name": norm(row.get("company_name")),
        "source_x_handle": norm(row.get("source_x_handle")),
        "text": norm(row.get("text")),
        "v1_label": norm(row.get("v1_label")),
        "v2_humor_label": norm(row.get("v2_label")),
        "transition_type": norm(row.get("transition_type")),
        "v1_confidence": norm(row.get("v1_confidence")),
        "v2_confidence": norm(row.get("v2_confidence")),
        "v2_review_flag": norm(row.get("v2_review_flag")),
        "v2_reason_code": norm(row.get("v2_reason_code")),
        "v2_target_of_humor": norm(row.get("v2_target_of_humor")),
        "v2_humor_function": norm(row.get("v2_humor_function")),
        "review_question": review_question_for(segment),
        "human_label": "",
        "human_confidence": "",
        "adjudication_notes": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build priority human review sample for humor type v1/v2 disagreement.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--p1-max", type=int, default=80, help="Max rows for v1 humor -> v2 not_humor")
    parser.add_argument("--p2-max", type=int, default=80, help="Max rows for v1 not_humor -> v2 humor")
    parser.add_argument("--p3-max", type=int, default=80, help="Max rows for v1 affiliative/self_enhancing -> v2 aggressive")
    parser.add_argument("--p4-max", type=int, default=80, help="Max rows for v1 ambiguous -> v2 not_humor")
    parser.add_argument("--p5-max", type=int, default=80, help="Max low-confidence or review-flag rows")
    parser.add_argument("--low-confidence-threshold", type=float, default=0.40)
    args = parser.parse_args()

    rows = load_rows(args.input)
    claimed: set[str] = set()
    selected: List[Dict[str, str]] = []
    manifest_segments: OrderedDict[str, Dict[str, object]] = OrderedDict()

    segment_specs = [
        (
            "P0",
            "v1_ambiguous_to_v2_rare_humor",
            lambda r: is_ambiguous(r.get("v1_label", "")) and lower(r.get("v2_label")) in {"aggressive", "self_defeating"},
            None,
            False,
        ),
        (
            "P1",
            "v1_humor_to_v2_not_humor",
            lambda r: is_humor(r.get("v1_label", "")) and is_not_humor(r.get("v2_label", "")),
            args.p1_max,
            False,
        ),
        (
            "P2",
            "v1_not_humor_to_v2_humor",
            lambda r: is_not_humor(r.get("v1_label", "")) and is_humor(r.get("v2_label", "")),
            args.p2_max,
            False,
        ),
        (
            "P3",
            "v1_positive_humor_to_v2_aggressive",
            lambda r: lower(r.get("v1_label")) in {"affiliative", "self_enhancing"} and lower(r.get("v2_label")) == "aggressive",
            args.p3_max,
            False,
        ),
        (
            "P4",
            "v1_ambiguous_to_v2_not_humor",
            lambda r: is_ambiguous(r.get("v1_label", "")) and is_not_humor(r.get("v2_label", "")),
            args.p4_max,
            False,
        ),
        (
            "P5",
            "low_confidence_or_review_flag",
            lambda r: parse_bool(r.get("v2_review_flag")) or parse_float(r.get("v2_confidence"), 1.0) < args.low_confidence_threshold,
            args.p5_max,
            True,
        ),
    ]

    for idx, (priority, segment, predicate, limit, sort_low_confidence) in enumerate(segment_specs):
        segment_rows, available = select_rows(
            rows=rows,
            predicate=predicate,
            limit=limit,
            claimed=claimed,
            seed=args.seed + idx,
            sort_low_confidence=sort_low_confidence,
        )
        selected.extend(build_output_row(r, priority, segment) for r in segment_rows)
        requested = "all" if limit is None else limit
        manifest_segments[segment] = {
            "priority": priority,
            "requested": requested,
            "available_after_higher_priority_exclusion": available,
            "sampled": len(segment_rows),
            "shortfall": 0 if limit is None else max(limit - len(segment_rows), 0),
            "selection_rule": "lowest_v2_confidence_first" if sort_low_confidence else "seeded_random_without_replacement",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(selected)

    manifest = {
        "input_path": str(args.input),
        "output_path": str(args.output),
        "manifest_path": str(args.manifest),
        "random_seed": args.seed,
        "low_confidence_threshold": args.low_confidence_threshold,
        "total_input_rows": len(rows),
        "total_selected_rows": len(selected),
        "deduplication_rule": "A row can appear in at most one segment; higher-priority segments claim rows first.",
        "segments": manifest_segments,
        "notes": [
            "v2 is treated as a human-review candidate generator, not a production replacement classifier.",
            "Gold labels should be produced through human adjudication, not by v1-v2 consensus alone.",
            "P0 rare-class transitions are included exhaustively after higher-priority exclusion logic, because they are central to aggressive/self-defeating validity checks.",
            "Cue/rule calibration should only be performed after human review confirms the error pattern.",
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Input rows: {len(rows)}")
    print(f"Selected rows: {len(selected)}")
    print(f"Wrote: {args.output}")
    print(f"Wrote: {args.manifest}")


if __name__ == "__main__":
    main()
