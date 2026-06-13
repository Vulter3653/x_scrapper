#!/usr/bin/env python3
"""Build a local humor-presence training seed from existing HSQ results.

This script does not call external APIs. It folds Wendy's and MoonPie HSQ
classification outputs into humor/non_humor/ambiguous presence labels.
"""

import argparse
import csv
import json
from pathlib import Path


HUMOR_LABELS = {
    "Affiliative humor",
    "Self-enhancing humor",
    "Aggressive humor",
    "Self-defeating humor",
}
NON_HUMOR_LABEL = "Non-humorous brand message"


def presence_from_hsq(post, humor_threshold, non_humor_threshold, margin_threshold):
    scores = post.get("scores") or {}
    top_label = post.get("top_label", "")
    top_score = float(post.get("top_score") or 0.0)
    humor_score = max(float(scores.get(label, 0.0)) for label in HUMOR_LABELS)
    non_score = float(scores.get(NON_HUMOR_LABEL, 0.0))
    margin = abs(humor_score - non_score)

    if top_label in HUMOR_LABELS and top_score >= humor_threshold and margin >= margin_threshold:
        return "humor", humor_score, non_score, margin
    if top_label == NON_HUMOR_LABEL and non_score >= non_humor_threshold and margin >= margin_threshold:
        return "non_humor", humor_score, non_score, margin
    return "ambiguous", humor_score, non_score, margin


def iter_hsq_posts(path, sample_group, company_name, handle, args):
    payload = json.loads(path.read_text(encoding="utf-8"))
    for post in payload.get("posts", []):
        text = (post.get("text") or "").strip()
        if not text:
            continue
        label, humor_score, non_score, margin = presence_from_hsq(
            post,
            args.humor_threshold,
            args.non_humor_threshold,
            args.margin_threshold,
        )
        if label == "ambiguous" and not args.include_ambiguous:
            continue
        yield {
            "global_post_id": f"{sample_group}::{post.get('id', '')}",
            "tweet_id": post.get("id", ""),
            "tweet_url": post.get("tweet_url", ""),
            "created_at": post.get("created_at", ""),
            "sample_group": sample_group,
            "company_name": company_name,
            "source_x_handle": handle,
            "text": text,
            "humor_presence_seed_label": label,
            "hsq_top_label": post.get("top_label", ""),
            "hsq_top_score": f"{float(post.get('top_score') or 0.0):.6f}",
            "hsq_humor_score": f"{humor_score:.6f}",
            "hsq_non_humor_score": f"{non_score:.6f}",
            "hsq_presence_margin": f"{margin:.6f}",
            "seed_source": "existing_hsq_classification",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wendys", type=Path, default=Path("data/wendys/hsq_humor_classification.json"))
    parser.add_argument("--moonpie", type=Path, default=Path("data/moonpie/hsq_humor_classification.json"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/humor/humor_presence_training_seed.csv"))
    parser.add_argument("--humor-threshold", type=float, default=0.35)
    parser.add_argument("--non-humor-threshold", type=float, default=0.50)
    parser.add_argument("--margin-threshold", type=float, default=0.10)
    parser.add_argument("--include-ambiguous", action="store_true")
    args = parser.parse_args()

    rows = []
    if args.wendys.exists():
        rows.extend(iter_hsq_posts(args.wendys, "benchmark_aggressive_wendys", "Wendy's", "@Wendys", args))
    if args.moonpie.exists():
        rows.extend(iter_hsq_posts(args.moonpie, "benchmark_self_defeating_moonpie", "MoonPie", "@MoonPie", args))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "global_post_id",
        "tweet_id",
        "tweet_url",
        "created_at",
        "sample_group",
        "company_name",
        "source_x_handle",
        "text",
        "humor_presence_seed_label",
        "hsq_top_label",
        "hsq_top_score",
        "hsq_humor_score",
        "hsq_non_humor_score",
        "hsq_presence_margin",
        "seed_source",
    ]
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row["humor_presence_seed_label"]] = counts.get(row["humor_presence_seed_label"], 0) + 1
    print(f"Wrote {len(rows)} seed rows to {args.output}")
    print(f"Seed label counts: {counts}")


if __name__ == "__main__":
    main()
