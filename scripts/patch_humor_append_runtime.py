#!/usr/bin/env python3
from pathlib import Path

runner = Path("scripts/run_humor_append_collection.py")
s = runner.read_text(encoding="utf-8")
old = '''    brand_dir = get_fortune_dir(rank, name)
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
    }'''
new = '''    brand_dir = get_fortune_dir(rank, name)
    existing_paths = [brand_dir / "posts.csv"]
    accounts_dir = brand_dir / "accounts"
    if accounts_dir.exists():
        existing_paths.extend(sorted(accounts_dir.glob("*/posts.csv")))
    existing_paths = list(dict.fromkeys(existing_paths))
    posts_csv = max(existing_paths, key=get_posts_count_csv)

    return {
        "is_benchmark": False,
        "brand_dir": brand_dir,
        "posts_csv": posts_csv,
        "existing_paths": existing_paths,
        "temp_json": brand_dir / "temp_append.json",
        "state_file": brand_dir / "temp_append_state.json",
    }'''
s = s.replace(old, new)
old = '''            posts_csv = paths["posts_csv"]  # type: ignore[assignment]
            prev_count = get_posts_count_csv(posts_csv)
            existing_ids = load_existing_ids_csv(posts_csv)'''
new = '''            posts_csv = paths["posts_csv"]  # type: ignore[assignment]
            source_paths = paths.get("existing_paths", [posts_csv])
            existing_ids = set()
            prev_ids = set()
            for source_path in source_paths:
                ids = load_existing_ids_csv(source_path)
                existing_ids.update(ids)
                prev_ids.update(ids)
            prev_count = len(prev_ids)'''
s = s.replace(old, new)
s = s.replace('            "SCRAPE_METRICS_FILE": str(metrics_path),', '            "SCRAPE_METRICS_FILE": str(metrics_path),\n            "SKIP_EXISTING_RECORDS": "1",')
runner.write_text(s, encoding="utf-8")

scraper = Path("src/x_scrapper/collection/x_scraper.py")
s = scraper.read_text(encoding="utf-8")
s = s.replace("PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '60000'))", "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '15000'))")
s = s.replace("PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '25000'))", "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '15000'))")
s = s.replace("STOP_ON_EXISTING = os.getenv('STOP_ON_EXISTING', '0').lower() in {'1', 'true', 'yes'}", "STOP_ON_EXISTING = os.getenv('STOP_ON_EXISTING', '0').lower() in {'1', 'true', 'yes'}\nSKIP_EXISTING_RECORDS = os.getenv('SKIP_EXISTING_RECORDS', '0').lower() in {'1', 'true', 'yes'}")
s = s.replace("if STOP_ON_EXISTING and tweet_id in known_ids:", "if (STOP_ON_EXISTING or SKIP_EXISTING_RECORDS) and tweet_id in known_ids:")
scraper.write_text(s, encoding="utf-8")
print("runtime patch applied: broad existing id lookup, skip existing, 15s timeout, no render fast-skip")
