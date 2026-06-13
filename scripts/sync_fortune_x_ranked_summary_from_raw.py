#!/usr/bin/env python3
"""Sync Fortune X ranked collection summary CSV from raw audit.json and posts.csv files."""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, List

def get_row_count(posts_path: Path) -> int:
    """Return row count of CSV excluding header."""
    if not posts_path.exists():
        return 0
    try:
        with posts_path.open(encoding="utf-8-sig", newline="") as f:
            # Use csv.reader for faster counting
            reader = csv.reader(f)
            # Skip header
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception as e:
        print(f"Error reading {posts_path}: {e}")
        return 0

def sync_summary(raw_root: Path, output_path: Path):
    rows: List[Dict[str, Any]] = []
    
    # Sort folders by rank
    folders = sorted(
        [d for d in raw_root.iterdir() if d.is_dir() and re.match(r"^\d{3}_", d.name)],
        key=lambda x: int(x.name.split("_")[0])
    )
    
    for folder in folders:
        rank = int(folder.name.split("_")[0])
        audit_path = folder / "audit.json"
        posts_path = folder / "posts.csv"
        
        audit_data = {}
        if audit_path.exists():
            with audit_path.open(encoding="utf-8") as f:
                audit_data = json.load(f)
        
        posts_collected = get_row_count(posts_path)
        
        # Determine status
        status = audit_data.get("status", "failed")
        if posts_collected > 0:
            # If we have posts, status should be success or partial_success
            # If audit.json says failed but we have posts, default to success (or keep partial if present)
            if status not in {"success", "partial_success"}:
                status = "success"
        
        error_type = audit_data.get("error_type", "")
        error_message = audit_data.get("error_message", "")
        
        # Clean errors for success
        if status == "success":
            error_type = ""
            error_message = ""
            
        # Apple manual correction (Rank 4)
        if rank == 4 and audit_data.get("company_name") == "Apple":
            status = "no_observable_posts"
            posts_collected = 0
            error_type = "manual_no_observable_posts"
            error_message = "manual review confirmed zero observable public posts"

        row = {
            "fortune_rank": rank,
            "company_name": audit_data.get("company_name", ""),
            "official_x_handle": audit_data.get("official_x_handle", ""),
            "folder": str(folder.relative_to(Path.cwd())) if folder.is_absolute() else str(folder),
            "attempted": str(audit_data.get("attempted", True)).lower(),
            "status": status,
            "posts_collected": posts_collected,
            "error_type": error_type,
            "error_message": error_message,
            "started_at": audit_data.get("started_at", ""),
            "completed_at": audit_data.get("completed_at", "")
        }
        rows.append(row)
        print(f"Processed rank {rank:03}: {status} ({posts_collected} posts)")

    fieldnames = [
        "fortune_rank", "company_name", "official_x_handle", "folder", 
        "attempted", "status", "posts_collected", "error_type", 
        "error_message", "started_at", "completed_at"
    ]
    
    with output_path.open("w", encoding="utf-8-sig", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nSuccessfully wrote {len(rows)} rows to {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/fortune_x_2025_ranked"))
    parser.add_argument("--output", type=Path, default=Path("data/audit/fortune_x_2025_ranked_collection_summary.csv"))
    args = parser.parse_args()
    
    if not args.raw_root.exists():
        print(f"Error: Raw root {args.raw_root} does not exist.")
        return
        
    sync_summary(args.raw_root, args.output)

if __name__ == "__main__":
    main()
