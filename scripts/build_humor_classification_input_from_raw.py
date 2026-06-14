#!/usr/bin/env python3
"""Build humor classification input from latest collected raw X posts.

Sources:
- data/raw/fortune_x_2025_ranked/*/posts.csv
- data/raw/fortune_x_2025_ranked/*/accounts/*/posts.csv
- data/wendys/posts.json, data/cocacola/posts.json, data/moonpie/posts.json when present

The output is the canonical CSV consumed by the humor full-chain workflow.
"""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
FORTUNE_ROOT = ROOT / "data" / "raw" / "fortune_x_2025_ranked"
BENCHMARK_SOURCES = [
    ("Wendy's", "@Wendys", ROOT / "data" / "wendys" / "posts.json"),
    ("Coca-Cola", "@cocacola", ROOT / "data" / "cocacola" / "posts.json"),
    ("MoonPie", "@MoonPie", ROOT / "data" / "moonpie" / "posts.json"),
]
FIELDS = [
    "global_post_id",
    "tweet_id",
    "sample_group",
    "fortune_rank",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
    "tweet_url",
    "reply_count",
    "repost_count",
    "like_count",
    "quote_count",
    "view_count_available",
    "media_present",
    "media_type",
    "source_path",
]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def tweet_id(row: Dict[str, Any]) -> str:
    for key in ("tweet_id", "id", "rest_id"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def int_or_blank(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def read_csv_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def infer_company_from_dir(directory: Path) -> tuple[str, str]:
    name = directory.name
    m = re.match(r"^(\d{3})_(.+)$", name)
    if not m:
        return "", name.replace("_", " ").title()
    rank = str(int(m.group(1)))
    company = m.group(2).replace("_", " ").title()
    return rank, company


def normalize_csv_row(row: Dict[str, Any], source_path: Path, fallback_rank: str, fallback_company: str) -> Dict[str, str] | None:
    tid = tweet_id(row)
    text = clean_text(row.get("text") or row.get("full_text") or row.get("content") or row.get("body"))
    if not tid or not text:
        return None
    company = clean_text(row.get("company_name")) or fallback_company
    rank = clean_text(row.get("fortune_rank")) or fallback_rank
    handle = clean_text(row.get("source_x_handle") or row.get("official_x_handle"))
    return {
        "global_post_id": f"fortune:{rank}:{tid}" if rank else f"fortune:{tid}",
        "tweet_id": tid,
        "sample_group": "fortune_top100_ranked",
        "fortune_rank": rank,
        "company_name": company,
        "source_x_handle": handle,
        "created_at": clean_text(row.get("created_at")),
        "text": text,
        "tweet_url": clean_text(row.get("tweet_url")),
        "reply_count": int_or_blank(row.get("reply_count")),
        "repost_count": int_or_blank(row.get("repost_count") or row.get("retweet_count")),
        "like_count": int_or_blank(row.get("like_count") or row.get("favorite_count")),
        "quote_count": int_or_blank(row.get("quote_count")),
        "view_count_available": clean_text(row.get("view_count_available")) or ("true" if row.get("view_count") else "false"),
        "media_present": clean_text(row.get("media_present")),
        "media_type": clean_text(row.get("media_type")),
        "source_path": str(source_path),
    }


def normalize_json_row(row: Dict[str, Any], source_path: Path, company: str, handle: str) -> Dict[str, str] | None:
    tid = tweet_id(row)
    text = clean_text(row.get("text") or row.get("full_text"))
    if not tid or not text:
        return None
    return {
        "global_post_id": f"benchmark:{handle.lstrip('@').lower()}:{tid}",
        "tweet_id": tid,
        "sample_group": "benchmark_humor_brand",
        "fortune_rank": "benchmark",
        "company_name": company,
        "source_x_handle": handle,
        "created_at": clean_text(row.get("created_at")),
        "text": text,
        "tweet_url": clean_text(row.get("tweet_url")),
        "reply_count": int_or_blank(row.get("reply_count")),
        "repost_count": int_or_blank(row.get("repost_count") or row.get("retweet_count")),
        "like_count": int_or_blank(row.get("like_count") or row.get("favorite_count")),
        "quote_count": int_or_blank(row.get("quote_count")),
        "view_count_available": "true" if row.get("view_count") else "false",
        "media_present": "",
        "media_type": "",
        "source_path": str(source_path),
    }


def build_rows() -> List[Dict[str, str]]:
    by_key: Dict[tuple[str, str], Dict[str, str]] = {}
    if FORTUNE_ROOT.exists():
        for company_dir in sorted(p for p in FORTUNE_ROOT.iterdir() if p.is_dir()):
            fallback_rank, fallback_company = infer_company_from_dir(company_dir)
            csv_paths = [company_dir / "posts.csv"]
            accounts_dir = company_dir / "accounts"
            if accounts_dir.exists():
                csv_paths.extend(sorted(accounts_dir.glob("*/posts.csv")))
            for csv_path in csv_paths:
                for source_row in read_csv_rows(csv_path):
                    row = normalize_csv_row(source_row, csv_path, fallback_rank, fallback_company)
                    if row:
                        by_key[(row["sample_group"], row["tweet_id"])] = row
    for company, handle, path in BENCHMARK_SOURCES:
        for source_row in read_json_rows(path):
            row = normalize_json_row(source_row, path, company, handle)
            if row:
                by_key[(row["sample_group"], row["tweet_id"])] = row
    rows = list(by_key.values())
    rows.sort(key=lambda r: (r["sample_group"], int(r["tweet_id"]) if r["tweet_id"].isdigit() else 0), reverse=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "derived" / "humor" / "humor_classification_input.csv")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "derived" / "humor" / "humor_classification_input_manifest.json")
    args = parser.parse_args()
    rows = build_rows()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    by_group: Dict[str, int] = {}
    by_company: Dict[str, int] = {}
    for row in rows:
        by_group[row["sample_group"]] = by_group.get(row["sample_group"], 0) + 1
        by_company[row["company_name"]] = by_company.get(row["company_name"], 0) + 1
    manifest = {
        "output": str(args.output),
        "row_count": len(rows),
        "sample_group_distribution": by_group,
        "company_count": len(by_company),
        "top_companies": dict(sorted(by_company.items(), key=lambda item: item[1], reverse=True)[:25]),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
