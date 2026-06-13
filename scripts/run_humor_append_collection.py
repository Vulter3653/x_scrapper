#!/usr/bin/env python3
"""Incremental append-only collection runner for humor analysis targets.

The runner keeps the repository's append-only data policy while avoiding full
timeline re-scrapes when a target already has collected tweet IDs. Existing IDs
are passed to the browser scraper so it can stop after it reaches known posts.
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS_FILE = REPO_ROOT / "config" / "humor_collection_append_targets.csv"
SCRAPER_ENTRYPOINT = REPO_ROOT / "scrape_x.py"
FORTUNE_ROOT = REPO_ROOT / "data" / "raw" / "fortune_x_2025_ranked"
SUMMARY_FILE = REPO_ROOT / "data" / "audit" / "humor_collection_append_summary.csv"
SHARD_WORK = REPO_ROOT / "shard_work"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def safe_handle(handle: str) -> str:
    return slugify(handle.lstrip("@")) or "handle"


def get_fortune_dir(rank: str, company_name: str) -> Path:
    rank_str = f"{int(rank):03d}"
    if FORTUNE_ROOT.exists():
        for directory in FORTUNE_ROOT.iterdir():
            if directory.is_dir() and directory.name.startswith(rank_str):
                return directory
    return FORTUNE_ROOT / f"{rank_str}_{slugify(company_name)}"


def get_posts_count_csv(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return sum(1 for _ in csv.DictReader(handle))
    except Exception:
        return 0


def get_posts_count_json(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def load_posts_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_posts_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def save_posts_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_posts_json(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def tweet_id_from_row(row: Dict[str, Any]) -> str:
    for key in ("tweet_id", "id", "rest_id"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def load_existing_ids_csv(path: Path) -> Set[str]:
    return {tweet_id_from_row(row) for row in load_posts_csv(path) if tweet_id_from_row(row)}


def load_existing_ids_json(path: Path) -> Set[str]:
    return {tweet_id_from_row(row) for row in load_posts_json(path) if tweet_id_from_row(row)}


def write_existing_ids(path: Path, ids: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for tweet_id in sorted(ids, reverse=True):
            handle.write(f"{tweet_id}\n")


def merge_json_to_csv(json_path: Path, csv_path: Path, target: Dict[str, str]) -> int:
    if not json_path.exists():
        return 0

    new_posts = load_posts_json(json_path)
    existing_rows = load_posts_csv(csv_path)
    existing_ids = {tweet_id_from_row(row) for row in existing_rows if tweet_id_from_row(row)}

    fieldnames = [
        "fortune_rank", "company_name", "official_x_handle", "tweet_id", "created_at", "text",
        "tweet_url", "reply_count", "repost_count", "like_count", "quote_count",
        "view_count_available", "media_present", "media_type", "collected_at", "collection_method",
        "max_posts_cap", "source_folder", "source_x_handle", "source_x_url", "account_role",
        "account_index",
    ]

    collected_at = utc_now()
    new_rows = []
    for post in new_posts:
        tweet_id = str(post.get("id", "")).strip()
        if not tweet_id or tweet_id in existing_ids:
            continue
        new_rows.append({
            "fortune_rank": target["fortune_rank"],
            "company_name": target["company_name"],
            "official_x_handle": target["handle"],
            "tweet_id": tweet_id,
            "created_at": post.get("created_at", ""),
            "text": post.get("text", ""),
            "tweet_url": post.get("tweet_url", ""),
            "reply_count": post.get("reply_count", 0),
            "repost_count": post.get("retweet_count", 0),
            "like_count": post.get("favorite_count", 0),
            "quote_count": post.get("quote_count", 0),
            "view_count_available": "true" if post.get("view_count") else "false",
            "media_present": "false",
            "media_type": "",
            "collected_at": collected_at,
            "collection_method": "incremental browser-based collection of observable public posts",
            "max_posts_cap": "0",
            "source_folder": str(csv_path.parent),
            "source_x_handle": target["handle"],
            "source_x_url": f"https://x.com/{target['handle'].lstrip('@')}",
            "account_role": "primary",
            "account_index": "1",
        })

    all_rows = new_rows + existing_rows
    all_rows.sort(
        key=lambda row: int(row["tweet_id"]) if str(row.get("tweet_id", "")).isdigit() else 0,
        reverse=True,
    )
    save_posts_csv(csv_path, all_rows, fieldnames)
    return len(new_rows)


def merge_json_to_json(new_json_path: Path, store_json_path: Path) -> int:
    if not new_json_path.exists():
        return 0

    new_posts = load_posts_json(new_json_path)
    existing_posts = load_posts_json(store_json_path)
    existing_ids = {tweet_id_from_row(post) for post in existing_posts if tweet_id_from_row(post)}

    additions = []
    for post in new_posts:
        tweet_id = tweet_id_from_row(post)
        if tweet_id and tweet_id not in existing_ids:
            additions.append(post)

    merged = additions + existing_posts
    merged.sort(
        key=lambda post: int(tweet_id_from_row(post)) if tweet_id_from_row(post).isdigit() else 0,
        reverse=True,
    )
    save_posts_json(store_json_path, merged)
    return len(additions)


def read_metrics(metrics_path: Path) -> Dict[str, Any]:
    if not metrics_path.exists():
        return {}
    try:
        with metrics_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_target_paths(target: Dict[str, str]) -> Dict[str, Path | bool]:
    rank = target["fortune_rank"]
    name = target["company_name"]
    handle = target["handle"]
    is_benchmark = rank == "benchmark"

    if is_benchmark:
        brand_slug = slugify(name.replace("'", ""))
        brand_dir = REPO_ROOT / "data" / brand_slug
        store_json = brand_dir / "posts.json"
        return {
            "is_benchmark": True,
            "brand_dir": brand_dir,
            "store_json": store_json,
            "temp_json": brand_dir / "temp_append.json",
            "state_file": brand_dir / "temp_append_state.json",
        }

    brand_dir = get_fortune_dir(rank, name)
    account_folder = f"01_primary_{slugify(handle.lstrip('@'))}"
    posts_csv = brand_dir / "accounts" / account_folder / "posts.csv"
    if not posts_csv.exists():
        posts_csv = brand_dir / "posts.csv"

    return {
        "is_benchmark": False,
        "brand_dir": brand_dir,
        "posts_csv": posts_csv,
        "temp_json": brand_dir / "temp_append.json",
        "state_file": brand_dir / "temp_append_state.json",
    }


def run_scraper_with_retries(
    env: Dict[str, str],
    target_name: str,
    retry_attempts: int,
    retry_delay_seconds: int,
    temp_json: Path,
    state_file: Path,
    metrics_path: Path,
) -> tuple[str, int, str]:
    last_error = ""
    attempts = max(1, retry_attempts)

    for attempt in range(1, attempts + 1):
        for transient_file in (temp_json, state_file, metrics_path):
            if transient_file.exists():
                transient_file.unlink()

        print(f"Scrape attempt {attempt}/{attempts}: {target_name}", flush=True)
        try:
            subprocess.run([sys.executable, str(SCRAPER_ENTRYPOINT)], env=env, check=True)
            return "success", attempt, ""
        except Exception as exc:
            last_error = str(exc)
            print(f"Failed attempt {attempt}/{attempts} for {target_name}: {exc}", flush=True)
            if attempt < attempts and retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)

    return "failed_skipped", attempts, last_error


def run_append_collection() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", "--targets-file", dest="targets", default=str(DEFAULT_TARGETS_FILE))
    parser.add_argument("--max-posts", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=2500)
    parser.add_argument("--incremental-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--existing-stop-threshold", type=int, default=30)
    parser.add_argument("--min-scrolls-before-stop", type=int, default=3)
    parser.add_argument("--retry-attempts", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=int, default=10)
    args = parser.parse_args()

    targets_path = Path(args.targets)
    if not targets_path.exists():
        print(f"Error: Targets file {targets_path} not found.")
        sys.exit(1)

    with targets_path.open(encoding="utf-8-sig", newline="") as handle:
        targets = list(csv.DictReader(handle))

    SHARD_WORK.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)

    results = []
    total_previous = 0
    total_final = 0

    for target in targets:
        rank = target["fortune_rank"]
        name = target["company_name"]
        handle = target["handle"]
        group = target["sample_group"]

        print(f"Processing {name} ({handle})...", flush=True)

        paths = resolve_target_paths(target)
        is_benchmark = bool(paths["is_benchmark"])
        brand_dir = paths["brand_dir"]  # type: ignore[assignment]
        temp_json = paths["temp_json"]  # type: ignore[assignment]
        state_file = paths["state_file"]  # type: ignore[assignment]

        if is_benchmark:
            store_json = paths["store_json"]  # type: ignore[assignment]
            prev_count = get_posts_count_json(store_json)
            existing_ids = load_existing_ids_json(store_json)
        else:
            posts_csv = paths["posts_csv"]  # type: ignore[assignment]
            prev_count = get_posts_count_csv(posts_csv)
            existing_ids = load_existing_ids_csv(posts_csv)

        total_previous += prev_count

        existing_ids_path = SHARD_WORK / f"existing_ids_{safe_handle(handle)}.txt"
        metrics_path = SHARD_WORK / f"scrape_metrics_{safe_handle(handle)}.json"
        write_existing_ids(existing_ids_path, existing_ids)

        env = os.environ.copy()
        env.update({
            "TARGET_USER": handle,
            "BRAND_DIR": str(brand_dir),
            "OUTPUT_FILE": str(temp_json),
            "STATE_FILE": str(state_file),
            "MAX_POSTS": str(args.max_posts),
            "MAX_SCROLLS": str(args.max_scrolls),
            "HEADLESS": "true",
            "EXISTING_TWEET_IDS_PATH": str(existing_ids_path),
            "STOP_ON_EXISTING": "1" if args.incremental_only else "0",
            "EXISTING_STOP_THRESHOLD": str(args.existing_stop_threshold),
            "MIN_SCROLLS_BEFORE_STOP": str(args.min_scrolls_before_stop),
            "SCRAPE_METRICS_FILE": str(metrics_path),
        })

        status, attempts, last_error = run_scraper_with_retries(
            env=env,
            target_name=name,
            retry_attempts=args.retry_attempts,
            retry_delay_seconds=args.retry_delay_seconds,
            temp_json=temp_json,
            state_file=state_file,
            metrics_path=metrics_path,
        )
        metrics = read_metrics(metrics_path)

        merge_added = 0
        if status == "success":
            if is_benchmark:
                merge_added = merge_json_to_json(temp_json, store_json)  # type: ignore[arg-type]
            else:
                merge_added = merge_json_to_csv(temp_json, posts_csv, target)  # type: ignore[arg-type]

                if "Coca-Cola" in name:
                    coca_benchmark_dir = REPO_ROOT / "data" / "cocacola"
                    coca_benchmark_json = coca_benchmark_dir / "posts.json"
                    if coca_benchmark_json.exists():
                        print(f"Updating Coca-Cola benchmark data in {coca_benchmark_json}...", flush=True)
                        merge_json_to_json(temp_json, coca_benchmark_json)

                company_posts_csv = brand_dir / "posts.csv"  # type: ignore[operator]
                if company_posts_csv != posts_csv and posts_csv.exists():  # type: ignore[union-attr]
                    shutil.copy(posts_csv, company_posts_csv)  # type: ignore[arg-type]

        if is_benchmark:
            final_count = get_posts_count_json(store_json)  # type: ignore[arg-type]
        else:
            final_count = get_posts_count_csv(posts_csv)  # type: ignore[arg-type]

        total_final += final_count
        new_posts = final_count - prev_count

        for transient_file in (temp_json, state_file):
            if transient_file.exists():
                transient_file.unlink()

        results.append({
            "fortune_rank": rank,
            "company_name": name,
            "handle": handle,
            "sample_group": group,
            "status": status,
            "attempts": attempts,
            "previous_posts": prev_count,
            "final_posts": final_count,
            "new_unique_posts": new_posts,
            "merge_added_posts": merge_added,
            "existing_id_count": len(existing_ids),
            "new_posts_collected": metrics.get("new_posts_collected", ""),
            "known_posts_seen": metrics.get("known_posts_seen", ""),
            "stopped_on_existing": metrics.get("stopped_on_existing", ""),
            "stop_reason": metrics.get("stop_reason", "subprocess_failure" if status.startswith("failed") else ""),
            "scrolls_completed": metrics.get("scrolls_completed", ""),
            "last_error": last_error,
        })

    print("\nCollection Complete. Generating Summary...", flush=True)

    fieldnames = list(results[0].keys()) if results else [
        "fortune_rank", "company_name", "handle", "sample_group", "status", "attempts",
        "previous_posts", "final_posts", "new_unique_posts", "merge_added_posts",
        "existing_id_count", "new_posts_collected", "known_posts_seen",
        "stopped_on_existing", "stop_reason", "scrolls_completed", "last_error",
    ]

    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    fortune_results = [row for row in results if row["fortune_rank"] != "benchmark"]
    benchmark_results = [row for row in results if row["fortune_rank"] == "benchmark"]

    cocacola = next((row for row in results if "Coca-Cola" in row["company_name"]), None)
    wendys = next((row for row in results if "Wendy's" in row["company_name"]), None)
    moonpie = next((row for row in results if "MoonPie" in row["company_name"]), None)

    print("-" * 40)
    print(f"Total target companies: {len(results)}")
    print(f"Fortune targets: {len(fortune_results)}")
    print(f"Benchmark targets: {len(benchmark_results)}")
    print(f"Attempted companies: {len(results)}")
    print(f"Success companies: {len([row for row in results if row['status'] == 'success'])}")
    print(f"Failed/skipped companies: {len([row for row in results if str(row['status']).startswith('failed')])}")
    print(f"Previous total posts: {total_previous}")
    print(f"Final total posts: {total_final}")
    print(f"New unique posts: {total_final - total_previous}")

    if cocacola:
        print(f"Coca-Cola: prev={cocacola['previous_posts']}, final={cocacola['final_posts']}, new={cocacola['new_unique_posts']}, status={cocacola['status']}")
    if wendys:
        print(f"Wendy's: prev={wendys['previous_posts']}, final={wendys['final_posts']}, new={wendys['new_unique_posts']}, status={wendys['status']}")
    if moonpie:
        print(f"MoonPie: prev={moonpie['previous_posts']}, final={moonpie['final_posts']}, new={moonpie['new_unique_posts']}, status={moonpie['status']}")
    print("-" * 40)


if __name__ == "__main__":
    run_append_collection()
