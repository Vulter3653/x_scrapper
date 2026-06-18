"""Build an integrated collected post corpus from existing repo data only.

This script does not collect new data and does not modify raw or legacy files.
It normalizes already-collected Fortune 100 and legacy brand post-level files
into one deduplicated corpus for H1 presence-only classification.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
OUT_BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "integrated_collected_corpus"
DATA_DIR = OUT_BASE / "data"

FORTUNE_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
LEGACY_SOURCES = [
    ("wendys_legacy", ROOT / "data" / "wendys" / "posts.json", "Wendy's", "Wendys"),
    ("moonpie_legacy", ROOT / "data" / "moonpie" / "posts.json", "MoonPie", "MoonPie"),
    ("cocacola_legacy", ROOT / "data" / "cocacola" / "posts.json", "Coca-Cola", "CocaCola"),
]

OUT_CORPUS = DATA_DIR / "integrated_collected_post_corpus.csv"
OUT_DIAG = DATA_DIR / "integrated_corpus_source_diagnostics.csv"

FIELDNAMES = [
    "integrated_post_id",
    "source_dataset",
    "source_file",
    "company_name",
    "source_x_handle",
    "x_handle",
    "created_at_raw",
    "parsed_datetime",
    "date",
    "year",
    "year_month",
    "month_of_year",
    "day_of_month",
    "day_of_week",
    "hour_of_day",
    "text",
    "tweet_id",
    "stable_source_id",
    "tweet_url",
    "reply_count",
    "repost_count",
    "retweet_count",
    "like_count",
    "favorite_count",
    "quote_count",
    "total_engagement",
    "log_total_engagement",
    "text_length",
    "hashtag_count",
    "mention_count",
    "missing_text",
    "missing_date",
    "dedupe_key",
    "dedupe_key_type",
]

DIAG_FIELDS = [
    "source_dataset",
    "input_path",
    "raw_rows",
    "parsed_rows",
    "duplicate_rows_removed",
    "final_rows",
    "min_date",
    "max_date",
    "missing_text_rows",
    "missing_date_rows",
    "has_engagement_fields",
    "usable_as_post_corpus",
    "notes",
]


def parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for parser in (
        lambda x: datetime.fromisoformat(x),
        lambda x: datetime.strptime(x, "%a %b %d %H:%M:%S %z %Y"),
        lambda x: datetime.strptime(x[:19], "%Y-%m-%d %H:%M:%S"),
        lambda x: datetime.strptime(x[:10], "%Y-%m-%d"),
    ):
        try:
            return parser(text)
        except ValueError:
            continue
    return None


def clean_int(value: Any) -> int | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def status_id_from_url(url: str) -> str:
    match = re.search(r"/status/(\d+)", url or "")
    return match.group(1) if match else ""


def date_parts(dt: datetime | None) -> dict[str, str]:
    if dt is None:
        return {
            "parsed_datetime": "",
            "date": "",
            "year": "",
            "year_month": "",
            "month_of_year": "",
            "day_of_month": "",
            "day_of_week": "",
            "hour_of_day": "",
        }
    return {
        "parsed_datetime": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "year": str(dt.year),
        "year_month": dt.strftime("%Y-%m"),
        "month_of_year": str(dt.month),
        "day_of_month": str(dt.day),
        "day_of_week": str(dt.weekday()),
        "hour_of_day": str(dt.hour),
    }


def coalesce(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return ""


def engagement(row: dict[str, Any]) -> tuple[str, str]:
    total = clean_int(row.get("total_engagement"))
    if total is None:
        reply = clean_int(row.get("reply_count")) or 0
        repost = clean_int(coalesce(row, ["repost_count", "retweet_count"])) or 0
        like = clean_int(coalesce(row, ["like_count", "favorite_count"])) or 0
        quote = clean_int(row.get("quote_count")) or 0
        if any(row.get(c) not in (None, "") for c in ["reply_count", "repost_count", "retweet_count", "like_count", "favorite_count", "quote_count"]):
            total = reply + repost + like + quote
    if total is None:
        return "", ""
    return str(total), str(round(math.log1p(total), 6))


def normalize_post(
    row: dict[str, Any],
    source_dataset: str,
    source_file: Path,
    company_name: str,
    handle: str,
) -> dict[str, str]:
    text = clean_text(row.get("text"))
    created_raw = str(coalesce(row, ["created_at", "date", "timestamp"])).strip()
    dt = parse_datetime(created_raw)
    tweet_url = str(row.get("tweet_url") or row.get("url") or "").strip()
    tweet_id = str(coalesce(row, ["tweet_id", "id", "conversation_id"])).strip()
    url_status_id = status_id_from_url(tweet_url)
    stable_source_id = tweet_id or url_status_id or str(coalesce(row, ["stable_source_id", "id"])).strip()
    total, log_total = engagement(row)
    out = {
        "integrated_post_id": "",
        "source_dataset": source_dataset,
        "source_file": str(source_file.relative_to(ROOT)),
        "company_name": str(row.get("company_name") or company_name),
        "source_x_handle": str(row.get("source_x_handle") or row.get("x_handle") or handle),
        "x_handle": str(row.get("x_handle") or row.get("source_x_handle") or handle),
        "created_at_raw": created_raw,
        "text": text,
        "tweet_id": tweet_id,
        "stable_source_id": stable_source_id,
        "tweet_url": tweet_url,
        "reply_count": str(coalesce(row, ["reply_count"])),
        "repost_count": str(coalesce(row, ["repost_count"])),
        "retweet_count": str(coalesce(row, ["retweet_count"])),
        "like_count": str(coalesce(row, ["like_count"])),
        "favorite_count": str(coalesce(row, ["favorite_count"])),
        "quote_count": str(coalesce(row, ["quote_count"])),
        "total_engagement": total,
        "log_total_engagement": log_total,
        "text_length": str(clean_int(row.get("text_length")) if row.get("text_length") not in (None, "") else len(text)),
        "hashtag_count": str(clean_int(row.get("hashtag_count")) if row.get("hashtag_count") not in (None, "") else len(re.findall(r"#\w+", text))),
        "mention_count": str(clean_int(row.get("mention_count")) if row.get("mention_count") not in (None, "") else len(re.findall(r"@\w+", text))),
        "missing_text": "1" if not text else "0",
        "missing_date": "1" if dt is None else "0",
    }
    out.update(date_parts(dt))
    if tweet_id:
        key_type, key = "tweet_id", tweet_id
    elif url_status_id:
        key_type, key = "tweet_url_status_id", url_status_id
    elif stable_source_id:
        key_type, key = "source_dataset_stable_source_id", f"{source_dataset}:{stable_source_id}"
    else:
        key_type = "source_company_datetime_text_hash"
        key = f"{source_dataset}:{out['company_name']}:{out['parsed_datetime']}:{normalized_hash(text)}"
    out["dedupe_key"] = key
    out["dedupe_key_type"] = key_type
    return out


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("posts", "data", "rows"):
            if isinstance(data.get(key), list):
                return [row for row in data[key] if isinstance(row, dict)]
    return []


def source_diag(source_dataset: str, input_path: Path, rows: list[dict[str, str]], raw_rows: int, note: str) -> dict[str, str]:
    dates = [row["date"] for row in rows if row["date"]]
    has_engagement = any(row.get("total_engagement") for row in rows)
    return {
        "source_dataset": source_dataset,
        "input_path": str(input_path.relative_to(ROOT)) if input_path.exists() else str(input_path),
        "raw_rows": str(raw_rows),
        "parsed_rows": str(len(rows)),
        "duplicate_rows_removed": "0",
        "final_rows": "0",
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
        "missing_text_rows": str(sum(1 for row in rows if row["missing_text"] == "1")),
        "missing_date_rows": str(sum(1 for row in rows if row["missing_date"] == "1")),
        "has_engagement_fields": "yes" if has_engagement else "no",
        "usable_as_post_corpus": "yes" if rows else "no",
        "notes": note,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []

    fortune_raw = read_csv_rows(FORTUNE_MASTER)
    fortune_rows = [
        normalize_post(row, "fortune100", FORTUNE_MASTER, row.get("company_name", ""), row.get("source_x_handle", ""))
        for row in fortune_raw
    ]
    all_rows.extend(fortune_rows)
    diagnostics.append(source_diag("fortune100", FORTUNE_MASTER, fortune_rows, len(fortune_raw), "Fortune 100 post master; treated as highest dedupe priority."))

    for source_dataset, path, company, handle in LEGACY_SOURCES:
        if not path.exists():
            diagnostics.append(source_diag(source_dataset, path, [], 0, "not found"))
            continue
        raw = read_json_rows(path) if path.suffix.lower() == ".json" else read_csv_rows(path)
        rows = [normalize_post(row, source_dataset, path, company, handle) for row in raw]
        all_rows.extend(rows)
        diagnostics.append(source_diag(source_dataset, path, rows, len(raw), "Existing legacy brand post-level file included."))

    priority = {"fortune100": 1, "wendys_legacy": 2, "moonpie_legacy": 2, "cocacola_legacy": 2}
    by_key: dict[str, dict[str, str]] = {}
    removed_by_source: dict[str, int] = defaultdict(int)
    for row in sorted(all_rows, key=lambda r: priority.get(r["source_dataset"], 9)):
        key = row["dedupe_key"]
        if key in by_key:
            removed_by_source[row["source_dataset"]] += 1
            continue
        by_key[key] = row

    final_rows = list(by_key.values())
    final_by_source: dict[str, int] = defaultdict(int)
    for index, row in enumerate(final_rows, start=1):
        row["integrated_post_id"] = f"icp_{index:07d}"
        final_by_source[row["source_dataset"]] += 1

    for diag in diagnostics:
        source = diag["source_dataset"]
        diag["duplicate_rows_removed"] = str(removed_by_source[source])
        diag["final_rows"] = str(final_by_source[source])

    with OUT_CORPUS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(final_rows)

    with OUT_DIAG.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DIAG_FIELDS)
        writer.writeheader()
        writer.writerows(diagnostics)

    print("Integrated collected corpus built")
    print(f"raw_rows={len(all_rows)}")
    print(f"duplicates_removed={len(all_rows) - len(final_rows)}")
    print(f"final_rows={len(final_rows)}")
    print(f"source_count={len([d for d in diagnostics if int(d['final_rows']) > 0])}")




def reflect_append_workflow_outputs() -> None:
    raw_dir = ROOT / "data" / "raw" / "fortune_x_2025_ranked"
    workflow = ROOT / ".github" / "workflows" / "append-humor-collection-102-companies.yml"
    append_summary = ROOT / "data" / "audit" / "humor_collection_append_summary.csv"
    failed_targets = ROOT / "data" / "audit" / "humor_collection_append_failed_targets.csv"
    out_append = DATA_DIR / "append_workflow_reflection.csv"

    with OUT_CORPUS.open("r", encoding="utf-8-sig", newline="") as f:
        corpus_rows = list(csv.DictReader(f))
    existing_keys = {row["dedupe_key"] for row in corpus_rows}

    raw_rows: list[dict[str, str]] = []
    raw_input_count = 0
    for path in sorted(raw_dir.glob("*/posts.csv")):
        for source in read_csv_rows(path):
            raw_input_count += 1
            row = dict(source)
            folder = path.parent.name
            if not row.get("company_name"):
                row["company_name"] = re.sub(r"^\d+_", "", folder).replace("_", " ").title()
            raw_rows.append(normalize_post(row, "fortune100_raw_append", path, row.get("company_name", ""), row.get("source_x_handle", "")))

    duplicate_removed = 0
    for row in raw_rows:
        if row["dedupe_key"] in existing_keys:
            duplicate_removed += 1
            continue
        row["integrated_post_id"] = f"icp_{len(corpus_rows) + 1:07d}"
        corpus_rows.append(row)
        existing_keys.add(row["dedupe_key"])

    with OUT_CORPUS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(corpus_rows)

    with OUT_DIAG.open("r", encoding="utf-8-sig", newline="") as f:
        diagnostics = list(csv.DictReader(f))
    diagnostics = [row for row in diagnostics if row.get("source_dataset") != "fortune100_raw_append"]
    dates = [row["date"] for row in raw_rows if row.get("date")]
    diagnostics.append({
        "source_dataset": "fortune100_raw_append",
        "input_path": str(raw_dir.relative_to(ROOT)),
        "raw_rows": str(raw_input_count),
        "parsed_rows": str(len(raw_rows)),
        "duplicate_rows_removed": str(duplicate_removed),
        "final_rows": str(len(raw_rows) - duplicate_removed),
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
        "missing_text_rows": str(sum(1 for row in raw_rows if row["missing_text"] == "1")),
        "missing_date_rows": str(sum(1 for row in raw_rows if row["missing_date"] == "1")),
        "has_engagement_fields": "yes" if any(row.get("total_engagement") for row in raw_rows) else "no",
        "usable_as_post_corpus": "yes" if raw_rows else "no",
        "notes": "Raw Fortune ranked posts from append workflow target directory; deduped after processed Fortune master.",
    })
    with OUT_DIAG.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DIAG_FIELDS)
        writer.writeheader()
        writer.writerows(diagnostics)

    append_rows = read_csv_rows(append_summary) if append_summary.exists() else []
    reflection = {
        "workflow_file_found": "yes" if workflow.exists() else "no",
        "audit_summary_found": "yes" if append_summary.exists() else "no",
        "failed_targets_found": "yes" if failed_targets.exists() else "no",
        "audit_summary_rows": str(len(append_rows)),
        "new_unique_posts_total": str(sum(clean_int(row.get("new_unique_posts")) or 0 for row in append_rows)),
        "fortune_x_2025_ranked_included": "yes" if raw_rows else "no",
        "wendys_posts_included": "yes" if any(row.get("source_dataset") == "wendys_legacy" for row in corpus_rows) else "no",
        "cocacola_posts_included": "yes" if any(row.get("source_dataset") == "cocacola_legacy" for row in corpus_rows) else "no",
        "moonpie_posts_included": "yes" if any(row.get("source_dataset") == "moonpie_legacy" for row in corpus_rows) else "no",
        "reflected_in_integrated_corpus": "yes",
    }
    with out_append.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(reflection.keys()))
        writer.writeheader()
        writer.writerow(reflection)

    print(f"append_summary_rows={reflection['audit_summary_rows']}")
    print(f"append_new_unique_posts_total={reflection['new_unique_posts_total']}")
    print(f"raw_fortune_rows={raw_input_count}")
    print(f"raw_fortune_duplicates_removed={duplicate_removed}")


if __name__ == "__main__":
    main()
    reflect_append_workflow_outputs()
