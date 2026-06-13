#!/usr/bin/env python3
"""Append-only collection runner for 102 humor analysis targets."""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS_FILE = REPO_ROOT / "config" / "humor_collection_append_targets.csv"
SCRAPER_ENTRYPOINT = REPO_ROOT / "scrape_x.py"
FORTUNE_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
SUMMARY_FILE = REPO_ROOT / "data" / "audit" / "humor_collection_append_summary.csv"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug

def get_fortune_dir(rank: str, company_name: str) -> Path:
    rank_str = f"{int(rank):03d}"
    # Try to find existing directory matching rank
    for d in FORTUNE_ROOT.iterdir():
        if d.is_dir() and d.name.startswith(rank_str):
            return d
    # If not found, create one (should not happen if already collected)
    slug = slugify(company_name)
    return FORTUNE_ROOT / f"{rank_str}_{slug}"

def get_posts_count_csv(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8-sig") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return 0

def get_posts_count_json(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
            return len(data)
    except Exception:
        return 0

def load_posts_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def save_posts_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def merge_json_to_csv(json_path: Path, csv_path: Path, target: Dict[str, str]):
    if not json_path.exists():
        return
    
    with json_path.open(encoding="utf-8") as f:
        new_posts = json.load(f)
    
    existing_rows = load_posts_csv(csv_path)
    existing_ids = {row["tweet_id"] for row in existing_rows}
    
    fieldnames = [
        "fortune_rank", "company_name", "official_x_handle", "tweet_id", "created_at", "text",
        "tweet_url", "reply_count", "repost_count", "like_count", "quote_count",
        "view_count_available", "media_present", "media_type", "collected_at", "collection_method",
        "max_posts_cap", "source_folder", "source_x_handle", "source_x_url", "account_role",
        "account_index",
    ]
    
    new_rows = []
    collected_at = utc_now()
    for p in new_posts:
        tid = str(p.get("id", ""))
        if tid and tid not in existing_ids:
            new_rows.append({
                "fortune_rank": target["fortune_rank"],
                "company_name": target["company_name"],
                "official_x_handle": target["handle"],
                "tweet_id": tid,
                "created_at": p.get("created_at", ""),
                "text": p.get("text", ""),
                "tweet_url": p.get("tweet_url", ""),
                "reply_count": p.get("reply_count", 0),
                "repost_count": p.get("retweet_count", 0),
                "like_count": p.get("favorite_count", 0),
                "quote_count": p.get("quote_count", 0),
                "view_count_available": "true" if p.get("view_count") else "false",
                "media_present": "false",
                "media_type": "",
                "collected_at": collected_at,
                "collection_method": "capped browser-based collection of observable public posts",
                "max_posts_cap": "0",
                "source_folder": str(csv_path.parent),
                "source_x_handle": target["handle"],
                "source_x_url": f"https://x.com/{target['handle'].lstrip('@')}",
                "account_role": "primary",
                "account_index": "1"
            })
    
    all_rows = new_rows + existing_rows
    # Sort by tweet_id descending
    all_rows.sort(key=lambda x: int(x["tweet_id"]) if x["tweet_id"].isdigit() else 0, reverse=True)
    save_posts_csv(csv_path, all_rows, fieldnames)

def run_append_collection():
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", default=str(TARGETS_FILE))
    parser.add_argument("--max-posts", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=2500)
    args = parser.parse_args()

    if not Path(args.targets).exists():
        print(f"Error: Targets file {args.targets} not found.")
        sys.exit(1)

    with open(args.targets, encoding="utf-8-sig") as f:
        targets = list(csv.DictReader(f))

    results = []
    total_previous = 0
    total_final = 0

    for target in targets:
        rank = target["fortune_rank"]
        name = target["company_name"]
        handle = target["handle"]
        group = target["sample_group"]
        
        print(f"Processing {name} ({handle})...")
        
        is_benchmark = rank == "benchmark"
        if is_benchmark:
            brand_slug = slugify(name.replace("'", ""))
            brand_dir = REPO_ROOT / "data" / brand_slug
            posts_json = brand_dir / "posts.json"
            prev_count = get_posts_count_json(posts_json)
        else:
            brand_dir = get_fortune_dir(rank, name)
            # Fortune data is in accounts/01_primary_<handle>/
            account_folder = f"01_primary_{slugify(handle.lstrip('@'))}"
            posts_csv = brand_dir / "accounts" / account_folder / "posts.csv"
            # Some fortune companies might have posts.csv directly in brand_dir too if merged
            # But the primary source is in the account folder.
            # We'll check both, but usually it's in the account folder.
            if not posts_csv.exists():
                posts_csv = brand_dir / "posts.csv"
            
            prev_count = get_posts_count_csv(posts_csv)
            posts_json = brand_dir / "temp_append.json"

        total_previous += prev_count
        
        env = os.environ.copy()
        env.update({
            "TARGET_USER": handle,
            "BRAND_DIR": str(brand_dir if is_benchmark else brand_dir), # Scraper writes to BRAND_DIR/posts.json
            "OUTPUT_FILE": str(posts_json),
            "MAX_POSTS": str(args.max_posts),
            "MAX_SCROLLS": str(args.max_scrolls),
            "HEADLESS": "true"
        })
        
        # If it's a benchmark, scrape_x.py will merge into posts.json automatically.
        # If it's Fortune, we want it to write to temp_append.json (fresh) then we merge manually.
        # But scrape_x.py merges if OUTPUT_FILE exists.
        # So for Fortune, we ensure temp_append.json is deleted before running.
        if not is_benchmark:
            if posts_json.exists():
                posts_json.unlink()

        try:
            subprocess.run([sys.executable, str(SCRAPER_ENTRYPOINT)], env=env, check=True)
            status = "success"
        except Exception as e:
            print(f"Failed to scrape {name}: {e}")
            status = "failed"

        if status == "success" and not is_benchmark:
            # Merge temp_append.json into posts.csv
            merge_json_to_csv(posts_json, posts_csv, target)
            
            # Special case for Coca-Cola benchmark
            if "Coca-Cola" in name:
                coca_benchmark_dir = REPO_ROOT / "data" / "cocacola"
                coca_benchmark_json = coca_benchmark_dir / "posts.json"
                if coca_benchmark_dir.exists():
                    print(f"Updating Coca-Cola benchmark data in {coca_benchmark_dir}...")
                    # For benchmark JSON, we want to merge. scrape_x.py merges if OUTPUT_FILE exists.
                    # But we already ran the scraper once for the Fortune folder.
                    # We can either run it again (slow) or just merge the temp_append.json into the benchmark JSON.
                    if posts_json.exists():
                        # Manual merge of JSON into JSON
                        with posts_json.open(encoding="utf-8") as f:
                            new_p = json.load(f)
                        with coca_benchmark_json.open(encoding="utf-8") as f:
                            existing_p = json.load(f)
                        
                        existing_ids = {str(p.get("id")) for p in existing_p}
                        merged_p = [p for p in new_p if str(p.get("id")) not in existing_ids] + existing_p
                        merged_p.sort(key=lambda x: int(x["id"]) if str(x.get("id", "")).isdigit() else 0, reverse=True)
                        
                        with coca_benchmark_json.open("w", encoding="utf-8") as f:
                            json.dump(merged_p, f, ensure_ascii=False, indent=2)
                            f.write("\n")
            
            if posts_json.exists():
                posts_json.unlink()
            # Also update the company-level posts.csv if it exists
            company_posts_csv = brand_dir / "posts.csv"
            if company_posts_csv != posts_csv:
                # For simplicity, we can just copy the account-level posts.csv to company-level
                import shutil
                shutil.copy(posts_csv, company_posts_csv)

        if is_benchmark:
            final_count = get_posts_count_json(posts_json)
        else:
            final_count = get_posts_count_csv(posts_csv)
            
        total_final += final_count
        new_posts = final_count - prev_count
        
        results.append({
            "fortune_rank": rank,
            "company_name": name,
            "handle": handle,
            "sample_group": group,
            "status": status,
            "previous_posts": prev_count,
            "final_posts": final_count,
            "new_unique_posts": new_posts
        })

    # Generate summary report
    print("\nCollection Complete. Generating Summary...")
    
    with open(SUMMARY_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Print Final Statistics
    fortune_results = [r for r in results if r["fortune_rank"] != "benchmark"]
    benchmark_results = [r for r in results if r["fortune_rank"] == "benchmark"]
    
    cocacola = next((r for r in results if "Coca-Cola" in r["company_name"]), None)
    wendys = next((r for r in results if "Wendy's" in r["company_name"]), None)
    moonpie = next((r for r in results if "MoonPie" in r["company_name"]), None)
    
    print("-" * 40)
    print(f"Total target companies: {len(results)}")
    print(f"Fortune targets: {len(fortune_results)}")
    print(f"Benchmark targets: {len(benchmark_results)}")
    print(f"Attempted companies: {len(results)}")
    print(f"Success companies: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Failed companies: {len([r for r in results if r['status'] == 'failed'])}")
    print(f"Previous total posts: {total_previous}")
    print(f"Final total posts: {total_final}")
    print(f"New unique posts: {total_final - total_previous}")
    
    if cocacola:
        print(f"Coca-Cola: prev={cocacola['previous_posts']}, final={cocacola['final_posts']}, new={cocacola['new_unique_posts']}")
    if wendys:
        print(f"Wendy's: prev={wendys['previous_posts']}, final={wendys['final_posts']}, new={wendys['new_unique_posts']}")
    if moonpie:
        print(f"MoonPie: prev={moonpie['previous_posts']}, final={moonpie['final_posts']}, new={moonpie['new_unique_posts']}")
    print("-" * 40)

if __name__ == "__main__":
    run_append_collection()
