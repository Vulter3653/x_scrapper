#!/usr/bin/env python3
"""Build humor classification input dataset from Fortune Top 100, Wendy's, and MoonPie posts."""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

def get_is_retweet(text: str) -> bool:
    return text.strip().startswith("RT @")

def get_is_reply(text: str) -> bool:
    # Very basic check, typically replies start with @ but not always in raw text
    return text.strip().startswith("@")

def get_language_hint(text: str, source_lang: Optional[str] = None) -> str:
    if source_lang:
        return source_lang
    # Very basic rule-based hint
    if any(ord(c) > 0x7F for c in text):
        return "mixed"
    return "en"

def load_fortune_posts(raw_root: Path, summary_path: Path) -> List[Dict[str, Any]]:
    posts = []
    if not summary_path.exists():
        print(f"Warning: Fortune summary not found at {summary_path}")
        return posts

    with summary_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rank = row["fortune_rank"]
            folder_str = row["folder"]
            folder = Path(folder_str)
            posts_path = folder / "posts.csv"
            
            if posts_path.exists():
                with posts_path.open(encoding="utf-8-sig", newline="") as pf:
                    p_reader = csv.DictReader(pf)
                    for p_row in p_reader:
                        p_row["sample_group"] = "fortune_top100_ranked"
                        p_row["source_dataset"] = "fortune_x_2025_ranked"
                        posts.append(p_row)
    return posts

def load_json_posts(json_path: Path, sample_group: str, source_dataset: str, company_name: str, handle: str) -> List[Dict[str, Any]]:
    posts = []
    if not json_path.exists():
        return posts
    
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            # Map posts.json schema to common schema
            post = {
                "fortune_rank": "benchmark",
                "company_name": company_name,
                "official_x_handle": handle,
                "tweet_id": item.get("id", ""),
                "tweet_url": item.get("tweet_url", ""),
                "created_at": item.get("created_at", ""),
                "text": item.get("text", ""),
                "reply_count": item.get("reply_count", 0),
                "repost_count": item.get("retweet_count", 0),
                "like_count": item.get("favorite_count", 0),
                "quote_count": item.get("quote_count", 0),
                "view_count_available": "true" if item.get("view_count") else "false",
                "media_present": "unknown",
                "media_type": "",
                "account_role": "primary",
                "account_index": "1",
                "collection_method": "legacy_json_import",
                "max_posts_cap": "0",
                "source_folder": str(json_path.parent),
                "sample_group": sample_group,
                "source_dataset": source_dataset,
                "lang": item.get("lang", "en")
            }
            posts.append(post)
    return posts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fortune-raw-root", type=Path, default=Path("data/raw/fortune_x_2025_ranked"))
    parser.add_argument("--fortune-summary", type=Path, default=Path("data/audit/fortune_x_2025_ranked_collection_summary.csv"))
    parser.add_argument("--wendys-source", type=Path, default=Path("data/wendys/posts.json"))
    parser.add_argument("--moonpie-source", type=Path, default=Path("data/moonpie/posts.json"))
    parser.add_argument("--cocacola-source", type=Path, default=Path("data/cocacola/posts.json"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--audit-output", type=Path, default=Path("data/derived/humor/humor_classification_input_audit.csv"))
    args = parser.parse_args()

    all_posts: List[Dict[str, Any]] = []
    
    # Audit tracking
    audit = {}
    
    # 1. Load Fortune Top 100
    fortune_posts = load_fortune_posts(args.fortune_raw_root, args.fortune_summary)
    audit["fortune_posts_loaded_before_dedup"] = len(fortune_posts)
    all_posts.extend(fortune_posts)
    
    # 2. Load Wendy's
    wendys_posts = load_json_posts(
        args.wendys_source, 
        "benchmark_aggressive_wendys", 
        "wendys_existing_collection",
        "Wendy's",
        "@Wendys"
    )
    audit["wendys_source_found"] = str(args.wendys_source.exists()).lower()
    audit["wendys_posts_loaded_before_dedup"] = len(wendys_posts)
    all_posts.extend(wendys_posts)
    
    # 3. Load MoonPie
    moonpie_posts = load_json_posts(
        args.moonpie_source, 
        "benchmark_self_defeating_moonpie", 
        "moonpie_existing_collection",
        "MoonPie",
        "@MoonPie"
    )
    audit["moonpie_source_found"] = str(args.moonpie_source.exists()).lower()
    audit["moonpie_posts_loaded_before_dedup"] = len(moonpie_posts)
    all_posts.extend(moonpie_posts)

    # 4. Load Coca-Cola (Benchmark)
    cocacola_posts = load_json_posts(
        args.cocacola_source,
        "benchmark_cocacola",
        "cocacola_existing_collection",
        "Coca-Cola",
        "@cocacola"
    )
    audit["cocacola_source_found"] = str(args.cocacola_source.exists()).lower()
    audit["cocacola_posts_loaded_before_dedup"] = len(cocacola_posts)
    all_posts.extend(cocacola_posts)

    audit["total_rows_before_dedup"] = len(all_posts)

    # 4. Deduplication
    # Criteria: sample_group + tweet_id
    # Priority for Fortune: success status (though here we just have rows), lower rank
    
    deduped: Dict[tuple, Dict[str, Any]] = {}
    removed_count = 0
    
    # Sort to handle priorities (Fortune success/low rank first)
    # We'll treat benchmark ranks as high numbers for sorting
    def sort_key(p):
        try:
            r = int(p.get("fortune_rank", 999))
        except ValueError:
            r = 999
        return (p["sample_group"], r, p.get("source_folder", ""))

    all_posts.sort(key=sort_key)
    
    for p in all_posts:
        tid = p.get("tweet_id", "")
        group = p.get("sample_group", "")
        key = (group, tid)
        
        if not tid:
            # If no tid, we'll generate one later, but for now just keep it
            # Using a temporary unique key
            key = (group, f"notid_{len(deduped)}")
            
        if key in deduped:
            removed_count += 1
            continue
        deduped[key] = p

    # 5. Final processing & Global ID generation
    final_rows = []
    empty_text_count = 0
    sample_group_counts = {
        "fortune_top100_ranked": 0,
        "benchmark_aggressive_wendys": 0,
        "benchmark_self_defeating_moonpie": 0,
        "benchmark_cocacola": 0
    }
    
    for i, ((group, tid), p) in enumerate(deduped.items()):
        text = p.get("text", "")
        if not text.strip():
            empty_text_count += 1
            
        global_id = f"{group}::{tid}" if tid else f"{group}::row::unknown::{i}"
        
        row = {
            "global_post_id": global_id,
            "sample_group": group,
            "source_dataset": p.get("source_dataset", ""),
            "fortune_rank": p.get("fortune_rank", ""),
            "company_name": p.get("company_name", ""),
            "official_x_handle": p.get("official_x_handle", ""),
            "source_x_handle": p.get("source_x_handle", p.get("official_x_handle", "")),
            "source_x_url": p.get("source_x_url", p.get("tweet_url", "")),
            "tweet_id": tid,
            "tweet_url": p.get("tweet_url", ""),
            "created_at": p.get("created_at", ""),
            "text": text,
            "reply_count": p.get("reply_count", 0),
            "repost_count": p.get("repost_count", 0),
            "like_count": p.get("like_count", 0),
            "quote_count": p.get("quote_count", 0),
            "view_count_available": p.get("view_count_available", "false"),
            "media_present": p.get("media_present", "false"),
            "media_type": p.get("media_type", ""),
            "account_role": p.get("account_role", "primary"),
            "account_index": p.get("account_index", "1"),
            "collection_method": p.get("collection_method", ""),
            "max_posts_cap": p.get("max_posts_cap", "0"),
            "source_folder": p.get("source_folder", ""),
            "is_duplicate_removed": "true",
            "is_empty_text": "true" if not text.strip() else "false",
            "is_retweet": "true" if get_is_retweet(text) else "false",
            "is_reply": "true" if get_is_reply(text) else "false",
            "is_quote": "true" if p.get("is_quote_status") or "quote" in text.lower() else "false",
            "language_hint": get_language_hint(text, p.get("lang")),
            "classification_status": "pending"
        }
        final_rows.append(row)
        sample_group_counts[group] = sample_group_counts.get(group, 0) + 1

    # 6. Write Output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "global_post_id", "sample_group", "source_dataset", "fortune_rank",
        "company_name", "official_x_handle", "source_x_handle", "source_x_url",
        "tweet_id", "tweet_url", "created_at", "text", "reply_count",
        "repost_count", "like_count", "quote_count", "view_count_available",
        "media_present", "media_type", "account_role", "account_index",
        "collection_method", "max_posts_cap", "source_folder", "is_duplicate_removed",
        "is_empty_text", "is_retweet", "is_reply", "is_quote", "language_hint",
        "classification_status"
    ]
    
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    # 7. Audit Summary
    audit["total_rows_after_dedup"] = len(final_rows)
    audit["duplicate_rows_removed"] = removed_count
    audit["empty_text_rows"] = empty_text_count
    audit["classification_pending_rows"] = len(final_rows)
    for group, count in sample_group_counts.items():
        audit[f"sample_group_count_{group}"] = count

    # Add Fortune summary stats if available
    if args.fortune_summary.exists():
        with args.fortune_summary.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            status_counts = {}
            for row in reader:
                s = row["status"]
                status_counts[s] = status_counts.get(s, 0) + 1
            audit["fortune_summary_rows"] = sum(status_counts.values())
            audit["fortune_status_success"] = status_counts.get("success", 0)
            audit["fortune_status_partial_success"] = status_counts.get("partial_success", 0)
            audit["fortune_status_no_observable_posts"] = status_counts.get("no_observable_posts", 0)
            audit["fortune_status_failed"] = status_counts.get("failed", 0)

    with args.audit_output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["audit_key", "audit_value"])
        for k, v in audit.items():
            writer.writerow([k, v])

    # 8. Schema JSON
    schema = {
        "dataset": "humor_classification_input",
        "purpose": "Input dataset for zero-shot humor presence and humor type classification",
        "classification_not_run": True,
        "sample_groups": [
            "fortune_top100_ranked",
            "benchmark_aggressive_wendys",
            "benchmark_self_defeating_moonpie",
            "benchmark_cocacola"
        ],
        "humor_types_future_target": [
            "affiliative_humor",
            "self_enhancing_humor",
            "aggressive_humor",
            "self_defeating_humor"
        ],
        "columns": {col: "Standardized column" for col in fieldnames}
    }
    schema_path = args.output.parent / "humor_classification_input_schema.json"
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    # 9. README.md
    readme_path = args.output.parent / "README.md"
    readme_content = """# Humor Classification Input Dataset

## Dataset Purpose
This dataset is a consolidated input for zero-shot humor classification. It combines Fortune 2025 Top 100 corporate X posts with known humor benchmarks.

## Source Data
- **Fortune 2025 Top 100 Ranked**: Corporate posts collected via browser-based scraping.
- **Wendy's**: Benchmark for aggressive humor (source: data/wendys/posts.json).
- **MoonPie**: Benchmark for self-defeating/affiliative humor (source: data/moonpie/posts.json).
- **Coca-Cola**: Benchmark for standard corporate/neutral humor (source: data/cocacola/posts.json).

## Sample Groups
- `fortune_top100_ranked`: Main target group for analysis.
- `benchmark_aggressive_wendys`: Reference for aggressive humor style.
- `benchmark_self_defeating_moonpie`: Reference for self-defeating/niche humor style.
- `benchmark_cocacola`: Reference for standard/neutral brand messaging.

## Metadata
- `classification_status`: All entries are currently marked as `pending`.
- `global_post_id`: Unique identifier across all sample groups.
- `is_duplicate_removed`: Set to `true` as deduplication was performed by `tweet_id` within each sample group.

## Note
Zero-shot classification has **not** yet been executed on this dataset.
"""
    with readme_path.open("w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"Dataset built successfully: {len(final_rows)} rows")
    print(f"Audit: {args.audit_output}")

if __name__ == "__main__":
    main()
