#!/usr/bin/env python3
"""Runtime patch for append collection.

Applied inside GitHub Actions before collection starts. It keeps the repository data untouched
while making the scraper safer for incremental/backfill runs.
"""
from pathlib import Path


def patch_runner() -> None:
    path = Path("scripts/run_humor_append_collection.py")
    text = path.read_text(encoding="utf-8")

    old = "\n".join([
        "    brand_dir = get_fortune_dir(rank, name)",
        "    account_folder = f\"01_primary_{slugify(handle.lstrip('@'))}\"",
        "    posts_csv = brand_dir / \"accounts\" / account_folder / \"posts.csv\"",
        "    if not posts_csv.exists():",
        "        posts_csv = brand_dir / \"posts.csv\"",
        "",
        "    return {",
        "        \"is_benchmark\": False,",
        "        \"brand_dir\": brand_dir,",
        "        \"posts_csv\": posts_csv,",
        "        \"temp_json\": brand_dir / \"temp_append.json\",",
        "        \"state_file\": brand_dir / \"temp_append_state.json\",",
        "    }",
    ])
    new = "\n".join([
        "    brand_dir = get_fortune_dir(rank, name)",
        "    existing_paths = [brand_dir / \"posts.csv\"]",
        "    accounts_dir = brand_dir / \"accounts\"",
        "    if accounts_dir.exists():",
        "        existing_paths.extend(sorted(accounts_dir.glob(\"*/posts.csv\")))",
        "    existing_paths = list(dict.fromkeys(existing_paths))",
        "    posts_csv = max(existing_paths, key=get_posts_count_csv)",
        "",
        "    return {",
        "        \"is_benchmark\": False,",
        "        \"brand_dir\": brand_dir,",
        "        \"posts_csv\": posts_csv,",
        "        \"existing_paths\": existing_paths,",
        "        \"temp_json\": brand_dir / \"temp_append.json\",",
        "        \"state_file\": brand_dir / \"temp_append_state.json\",",
        "    }",
    ])
    if old in text:
        text = text.replace(old, new)

    old = "\n".join([
        "            posts_csv = paths[\"posts_csv\"]  # type: ignore[assignment]",
        "            prev_count = get_posts_count_csv(posts_csv)",
        "            existing_ids = load_existing_ids_csv(posts_csv)",
    ])
    new = "\n".join([
        "            posts_csv = paths[\"posts_csv\"]  # type: ignore[assignment]",
        "            source_paths = paths.get(\"existing_paths\", [posts_csv])",
        "            existing_ids = set()",
        "            prev_ids = set()",
        "            for source_path in source_paths:",
        "                ids = load_existing_ids_csv(source_path)",
        "                existing_ids.update(ids)",
        "                prev_ids.update(ids)",
        "            prev_count = len(prev_ids)",
    ])
    if old in text:
        text = text.replace(old, new)

    text = text.replace(
        "            \"SCRAPE_METRICS_FILE\": str(metrics_path),",
        "            \"SCRAPE_METRICS_FILE\": str(metrics_path),\n            \"SKIP_EXISTING_RECORDS\": \"1\",",
    )

    old = "\n".join([
        "        except Exception as exc:",
        "            last_error = str(exc)",
        "            print(f\"Failed attempt {attempt}/{attempts} for {target_name}: {exc}\", flush=True)",
        "            if attempt < attempts and retry_delay_seconds > 0:",
        "                time.sleep(retry_delay_seconds)",
    ])
    new = "\n".join([
        "        except Exception as exc:",
        "            last_error = str(exc)",
        "            print(f\"Failed attempt {attempt}/{attempts} for {target_name}: {exc}\", flush=True)",
        "            failure_metrics = read_metrics(metrics_path)",
        "            if failure_metrics.get(\"stop_reason\") == \"render_failure\":",
        "                print(\"Render failure detected; skipping target without additional retry.\", flush=True)",
        "                return \"failed_skipped\", attempt, last_error",
        "            if attempt < attempts and retry_delay_seconds > 0:",
        "                time.sleep(retry_delay_seconds)",
    ])
    if old in text:
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")


def patch_scraper() -> None:
    path = Path("src/x_scrapper/collection/x_scraper.py")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '60000'))",
        "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '25000'))",
    )
    text = text.replace(
        "STOP_ON_EXISTING = os.getenv('STOP_ON_EXISTING', '0').lower() in {'1', 'true', 'yes'}",
        "STOP_ON_EXISTING = os.getenv('STOP_ON_EXISTING', '0').lower() in {'1', 'true', 'yes'}\nSKIP_EXISTING_RECORDS = os.getenv('SKIP_EXISTING_RECORDS', '0').lower() in {'1', 'true', 'yes'}",
    )
    text = text.replace(
        "if STOP_ON_EXISTING and tweet_id in known_ids:",
        "if (STOP_ON_EXISTING or SKIP_EXISTING_RECORDS) and tweet_id in known_ids:",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_runner()
    patch_scraper()
    print("runtime patch applied: broad id lookup, skip existing, render-failure fast skip, 25s timeout")
