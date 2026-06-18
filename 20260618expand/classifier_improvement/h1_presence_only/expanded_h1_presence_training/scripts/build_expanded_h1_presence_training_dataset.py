"""Build expanded H1 humor-presence training data from batch1 + Wendy's labels.

This script only constructs a training dataset. It does not train classifiers,
run regressions, or create H2/H3/type/aggressive outputs.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_training"
DATA = BASE / "data"
SPLITS = ROOT / "20260618expand" / "classifier_improvement" / "data" / "human_labeling_template" / "coder_splits"
WENDYS = ROOT / "data" / "derived" / "humor" / "human_labels" / "wendys_human_label_raw_linked.csv"
FORTUNE_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
OUT = DATA / "expanded_h1_presence_training_dataset.csv"
DIAG = DATA / "expanded_h1_presence_training_diagnostics.csv"

OUT_FIELDS = [
    "row_id", "source", "original_file", "company_name", "tweet_id", "tweet_url",
    "created_at", "text", "humor_presence_binary", "original_presence_value",
    "label_source_detail",
]
DIAG_FIELDS = [
    "source", "raw_rows", "valid_rows", "humor_count", "non_humor_count",
    "excluded_rows", "duplicate_rows_removed", "final_rows",
]


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def text_hash(text: str) -> str:
    return hashlib.sha1(norm_text(text).lower().encode("utf-8")).hexdigest()[:16]


def dedupe_key(row: dict[str, str]) -> str:
    if row.get("tweet_id"):
        return "tweet_id:" + row["tweet_id"]
    if row.get("tweet_url"):
        return "tweet_url:" + row["tweet_url"]
    return "company_text:" + row.get("company_name", "") + ":" + text_hash(row.get("text", ""))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fortune_text_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    if not FORTUNE_MASTER.exists():
        return lookup
    for row in read_csv(FORTUNE_MASTER):
        text = norm_text(row.get("text", ""))
        if not text:
            continue
        tweet_id = (row.get("tweet_id") or "").strip()
        tweet_url = (row.get("tweet_url") or "").strip()
        if tweet_id:
            lookup["tweet_id:" + tweet_id] = text
        if tweet_url:
            lookup["tweet_url:" + tweet_url] = text
    return lookup


def fallback_text(row: dict[str, str], lookup: dict[str, str]) -> str:
    tweet_id = (row.get("트윗_ID") or "").strip()
    tweet_url = (row.get("트윗_URL") or "").strip()
    if tweet_id and lookup.get("tweet_id:" + tweet_id):
        return lookup["tweet_id:" + tweet_id]
    if tweet_url and lookup.get("tweet_url:" + tweet_url):
        return lookup["tweet_url:" + tweet_url]
    return ""


def batch1_rows() -> tuple[list[dict[str, str]], dict[str, dict[str, int]]]:
    output: list[dict[str, str]] = []
    diag: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    source = "batch1_fortune100"
    text_lookup = fortune_text_lookup()
    for coder in ["coder1", "coder2", "coder3"]:
        path = SPLITS / f"{coder}_labeling_template.csv"
        rows = read_csv(path)
        diag[source]["raw_rows"] += len(rows)
        for row in rows:
            value = (row.get("유머_존재여부") or "").strip()
            if value == "1":
                label = "1"
            elif value == "0":
                label = "0"
            else:
                diag[source]["excluded_rows"] += 1
                continue
            text = norm_text(row.get("본문", "")) or fallback_text(row, text_lookup)
            if not text:
                diag[source]["excluded_rows"] += 1
                continue
            diag[source]["valid_rows"] += 1
            diag[source]["humor_count" if label == "1" else "non_humor_count"] += 1
            output.append({
                "row_id": "",
                "source": source,
                "original_file": str(path.relative_to(ROOT)),
                "company_name": row.get("회사명", ""),
                "tweet_id": row.get("트윗_ID", ""),
                "tweet_url": row.get("트윗_URL", ""),
                "created_at": row.get("작성일시", ""),
                "text": text,
                "humor_presence_binary": label,
                "original_presence_value": value,
                "label_source_detail": coder,
            })
    return output, diag


def wendys_label(row: dict[str, str]) -> tuple[str | None, str]:
    binary = (row.get("human_humor_binary") or "").strip()
    if binary in {"0", "1"}:
        return binary, binary
    raw = (row.get("humor") or row.get("human_humor_label_raw") or "").strip().lower()
    if raw == "humor":
        return "1", raw
    if raw in {"non_humor", "none"}:
        return "0", raw
    return None, binary or raw


def wendys_rows() -> tuple[list[dict[str, str]], dict[str, dict[str, int]]]:
    source = "wendys_human"
    diag: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    output: list[dict[str, str]] = []
    rows = read_csv(WENDYS)
    diag[source]["raw_rows"] = len(rows)
    for row in rows:
        label, original = wendys_label(row)
        if label not in {"0", "1"}:
            diag[source]["excluded_rows"] += 1
            continue
        text = norm_text(row.get("raw_text") or row.get("human_text") or "")
        if not text:
            diag[source]["excluded_rows"] += 1
            continue
        diag[source]["valid_rows"] += 1
        diag[source]["humor_count" if label == "1" else "non_humor_count"] += 1
        output.append({
            "row_id": "",
            "source": source,
            "original_file": str(WENDYS.relative_to(ROOT)),
            "company_name": row.get("company_name", "Wendy's"),
            "tweet_id": row.get("tweet_id", ""),
            "tweet_url": row.get("tweet_url", ""),
            "created_at": row.get("created_at_raw") or row.get("created_at_human") or "",
            "text": text,
            "humor_presence_binary": label,
            "original_presence_value": original,
            "label_source_detail": row.get("human_label_source") or "wendys_human_label_raw_linked",
        })
    return output, diag


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rows1, diag1 = batch1_rows()
    rows2, diag2 = wendys_rows()
    all_rows = rows1 + rows2
    diagnostics: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for source_diag in [diag1, diag2]:
        for source, values in source_diag.items():
            for key, value in values.items():
                diagnostics[source][key] += value

    priority = {"batch1_fortune100": 1, "wendys_human": 2}
    kept: dict[str, dict[str, str]] = {}
    for row in sorted(all_rows, key=lambda r: priority[r["source"]]):
        key = dedupe_key(row)
        if key in kept:
            diagnostics[row["source"]]["duplicate_rows_removed"] += 1
            continue
        kept[key] = row

    final_rows = list(kept.values())
    final_by_source: dict[str, int] = defaultdict(int)
    for index, row in enumerate(final_rows, start=1):
        row["row_id"] = f"expanded_h1_{index:05d}"
        final_by_source[row["source"]] += 1

    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(final_rows)

    for source in ["batch1_fortune100", "wendys_human"]:
        diagnostics[source]["final_rows"] = final_by_source[source]
    with DIAG.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DIAG_FIELDS)
        writer.writeheader()
        for source in ["batch1_fortune100", "wendys_human"]:
            writer.writerow({field: source if field == "source" else diagnostics[source].get(field, 0) for field in DIAG_FIELDS})

    print("Expanded H1 presence training dataset built")
    print(f"rows={len(final_rows)}")
    print(f"humor={sum(1 for r in final_rows if r['humor_presence_binary'] == '1')}")
    print(f"non_humor={sum(1 for r in final_rows if r['humor_presence_binary'] == '0')}")


if __name__ == "__main__":
    main()
