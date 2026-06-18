"""Validate expanded H1 humor-presence training dataset outputs."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_training"
DATASET = BASE / "data" / "expanded_h1_presence_training_dataset.csv"
DIAG = BASE / "data" / "expanded_h1_presence_training_diagnostics.csv"
ALLOWED_SOURCES = {"batch1_fortune100", "wendys_human"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    failures: list[str] = []
    if not DATASET.exists():
        failures.append(f"missing dataset: {DATASET}")
    if not DIAG.exists():
        failures.append(f"missing diagnostics: {DIAG}")
    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    rows = read_csv(DATASET)
    diag_rows = read_csv(DIAG)
    counts = Counter(row["humor_presence_binary"] for row in rows)
    source_counts = Counter(row["source"] for row in rows)

    if len(rows) != 1550:
        failures.append(f"total rows expected 1550, got {len(rows)}")
    if counts["1"] != 685:
        failures.append(f"humor expected 685, got {counts['1']}")
    if counts["0"] != 865:
        failures.append(f"non_humor expected 865, got {counts['0']}")
    if set(source_counts) - ALLOWED_SOURCES:
        failures.append(f"unexpected source values: {sorted(set(source_counts) - ALLOWED_SOURCES)}")
    if any(row["humor_presence_binary"] not in {"0", "1"} for row in rows):
        failures.append("humor_presence_binary contains values outside 0/1")
    if source_counts["batch1_fortune100"] != 1482:
        failures.append(f"batch1 valid rows expected 1482, got {source_counts['batch1_fortune100']}")
    if source_counts["wendys_human"] != 68:
        failures.append(f"wendys valid rows expected 68, got {source_counts['wendys_human']}")
    tweet_ids = [row["tweet_id"] for row in rows if row.get("tweet_id")]
    if len(tweet_ids) != len(set(tweet_ids)):
        failures.append("duplicate tweet_id found")
    if any(not row.get("text", "").strip() for row in rows):
        failures.append("blank text found")

    diag = {row["source"]: row for row in diag_rows}
    expected_diag = {
        "batch1_fortune100": {"raw_rows": "1500", "valid_rows": "1482", "humor_count": "648", "non_humor_count": "834", "excluded_rows": "18", "final_rows": "1482"},
        "wendys_human": {"raw_rows": "69", "valid_rows": "68", "humor_count": "37", "non_humor_count": "31", "excluded_rows": "1", "final_rows": "68"},
    }
    for source, expected in expected_diag.items():
        if source not in diag:
            failures.append(f"missing diagnostics source: {source}")
            continue
        for key, value in expected.items():
            if diag[source].get(key) != value:
                failures.append(f"{source} {key} expected {value}, got {diag[source].get(key)}")

    forbidden_dirs = ["classifier", "regression", "h2", "h3", "type", "aggressive"]
    for path in BASE.rglob("*"):
        lower = path.name.lower()
        if path.is_file() and any(token in lower for token in forbidden_dirs) and path.name not in {Path(__file__).name}:
            failures.append(f"forbidden output file found: {path.relative_to(BASE)}")
            break

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("VALIDATION PASS")
    print(f"rows={len(rows)}")
    print(f"humor={counts['1']}")
    print(f"non_humor={counts['0']}")
    print(f"batch1_rows={source_counts['batch1_fortune100']}")
    print(f"wendys_rows={source_counts['wendys_human']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
