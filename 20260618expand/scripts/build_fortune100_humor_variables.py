#!/usr/bin/env python3
"""Build Fortune Top 100 humor variables from existing classifications."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "20260618expand"
POST_MASTER = PACKAGE / "data/processed/fortune100_post_master.csv"
FULL_CHAIN = ROOT / "data/derived/humor/full_chain/humor_full_chain_master.csv"
OUT = PACKAGE / "data/processed/fortune100_humor_variables.csv"
DIAG = PACKAGE / "data/diagnostics/fortune100_humor_classification_coverage.csv"

HUMOR_COLUMNS = [
    "tweet_id",
    "fortune_rank",
    "company_name",
    "source_x_handle",
    "humor_presence",
    "humor_presence_score",
    "humor_type",
    "humor_type_score",
    "aggressive_humor",
    "affiliative_humor",
    "self_enhancing_humor",
    "self_defeating_humor",
    "non_humorous",
    "classification_source",
    "model_name",
    "classification_confidence",
    "classification_version",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_presence(value: str) -> str:
    lowered = (value or "").strip().lower()
    if lowered in {"humor", "1", "true", "yes"}:
        return "1"
    if lowered in {"non_humor", "non-humor", "not_humor", "0", "false", "no"}:
        return "0"
    return ""


def normalize_type(value: str, presence: str) -> str:
    lowered = (value or "").strip().lower().replace("-", "_")
    if presence == "0":
        return "non_humorous"
    if lowered in {"aggressive", "affiliative", "self_enhancing", "self_defeating"}:
        return lowered
    if lowered in {"not_applicable", "non_humor", "non_humorous"}:
        return "non_humorous"
    return "classification_missing" if presence == "" else "ambiguous_or_review"


def main() -> None:
    posts = read_csv(POST_MASTER)
    existing = {str(row.get("tweet_id", "")): row for row in read_csv(FULL_CHAIN) if row.get("tweet_id")}
    rows: list[dict[str, object]] = []
    coverage: dict[tuple[str, str], dict[str, object]] = {}

    for post in posts:
        tweet_id = str(post.get("tweet_id", ""))
        classification = existing.get(tweet_id)
        company = post.get("company_name", "")
        handle = post.get("source_x_handle", "")
        key = (company, handle)
        bucket = coverage.setdefault(
            key,
            {
                "company_name": company,
                "source_x_handle": handle,
                "post_count": 0,
                "classified_count": 0,
                "classification_missing_count": 0,
                "humor_count": 0,
                "non_humor_count": 0,
                "ambiguous_or_missing_presence_count": 0,
            },
        )
        bucket["post_count"] = int(bucket["post_count"]) + 1

        if classification:
            presence = normalize_presence(classification.get("humor_presence", ""))
            htype = normalize_type(classification.get("humor_type", ""), presence)
            score = classification.get("ml_humor_probability") or classification.get("humor_presence_confidence", "")
            confidence = classification.get("humor_presence_confidence", "")
            source = classification.get("humor_presence_decision_source") or "existing_full_chain_model_based"
            model_name = "existing_repository_full_chain_classifier"
            version = "existing_data_derived_humor_full_chain"
            bucket["classified_count"] = int(bucket["classified_count"]) + 1
            if presence == "1":
                bucket["humor_count"] = int(bucket["humor_count"]) + 1
            elif presence == "0":
                bucket["non_humor_count"] = int(bucket["non_humor_count"]) + 1
            else:
                bucket["ambiguous_or_missing_presence_count"] = int(bucket["ambiguous_or_missing_presence_count"]) + 1
        else:
            presence = ""
            htype = "classification_missing"
            score = ""
            confidence = ""
            source = "classification_missing_no_new_inference"
            model_name = ""
            version = ""
            bucket["classification_missing_count"] = int(bucket["classification_missing_count"]) + 1

        rows.append(
            {
                "tweet_id": tweet_id,
                "fortune_rank": post.get("fortune_rank", ""),
                "company_name": company,
                "source_x_handle": handle,
                "humor_presence": presence,
                "humor_presence_score": score,
                "humor_type": htype,
                "humor_type_score": classification.get("humor_type_confidence", "") if classification else "",
                "aggressive_humor": "1" if htype == "aggressive" else "0",
                "affiliative_humor": "1" if htype == "affiliative" else "0",
                "self_enhancing_humor": "1" if htype == "self_enhancing" else "0",
                "self_defeating_humor": "1" if htype == "self_defeating" else "0",
                "non_humorous": "1" if htype == "non_humorous" or presence == "0" else "0",
                "classification_source": source,
                "model_name": model_name,
                "classification_confidence": confidence,
                "classification_version": version,
            }
        )

    coverage_rows = list(coverage.values())
    for row in coverage_rows:
        post_count = int(row["post_count"])
        row["classification_available_rate"] = round(int(row["classified_count"]) / post_count, 6) if post_count else ""

    write_csv(OUT, rows, HUMOR_COLUMNS)
    write_csv(
        DIAG,
        coverage_rows,
        [
            "company_name",
            "source_x_handle",
            "post_count",
            "classified_count",
            "classification_missing_count",
            "classification_available_rate",
            "humor_count",
            "non_humor_count",
            "ambiguous_or_missing_presence_count",
        ],
    )
    print(f"wrote {OUT.relative_to(ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
