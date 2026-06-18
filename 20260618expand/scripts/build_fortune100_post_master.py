#!/usr/bin/env python3
"""Build the Fortune Top 100 post-level master dataset.

This script reads only existing repository data. It does not collect X data,
call external APIs, sync dashboards, or mutate raw inputs.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "20260618expand"
RAW_ROOT = ROOT / "data/raw/fortune_x_2025_ranked"
AUDIT_SUMMARY = ROOT / "data/audit/fortune_x_2025_ranked_collection_summary.csv"
QUEUE = ROOT / "config/fortune2025_top100_verified_x_collection_queue.csv"
MASTER = ROOT / "config/fortune2025_x_account_verification_master.csv"

PROCESSED = PACKAGE / "data/processed"
DIAGNOSTICS = PACKAGE / "data/diagnostics"

POST_MASTER_CSV = PROCESSED / "fortune100_post_master.csv"
POST_MASTER_JSON = PROCESSED / "fortune100_post_master.json"
COVERAGE_CSV = DIAGNOSTICS / "fortune100_collection_coverage.csv"
MISSINGNESS_CSV = DIAGNOSTICS / "fortune100_missingness_summary.csv"
DUPLICATE_CSV = DIAGNOSTICS / "fortune100_duplicate_tweet_audit.csv"
COVERAGE_REPORT = PACKAGE / "reports/coverage_diagnostics.md"

POST_COLUMNS = [
    "fortune_rank",
    "company_name",
    "normalized_company_name",
    "source_x_handle",
    "source_x_url",
    "account_role",
    "account_index",
    "tweet_id",
    "tweet_url",
    "created_at",
    "text",
    "reply_count",
    "repost_count",
    "retweet_count",
    "like_count",
    "favorite_count",
    "quote_count",
    "view_count_available",
    "total_engagement",
    "log_total_engagement",
    "text_length",
    "hashtag_count",
    "mention_count",
    "collection_method",
    "max_posts_cap",
    "source_folder",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def first_present(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return ""


def as_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def safe_count(value: object) -> int:
    parsed = as_int(value)
    return parsed if parsed is not None else 0


def log1p(value: int | None) -> float | str:
    if value is None:
        return ""
    return round(math.log1p(value), 12)


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def make_rank_index() -> dict[int, dict[str, str]]:
    index: dict[int, dict[str, str]] = {}
    for row in read_csv(QUEUE) + read_csv(MASTER):
        rank = as_int(row.get("fortune_rank"))
        if rank is None:
            continue
        current = index.setdefault(rank, {})
        for key in [
            "company_name",
            "normalized_company_name",
            "collection_x_handle",
            "collection_x_url",
            "final_manual_x_url_primary",
            "final_manual_account_status",
            "final_manual_scrape_eligible",
        ]:
            if row.get(key) and not current.get(key):
                current[key] = row[key]
    return index


def get_rank_from_folder(path: Path) -> int | None:
    match = re.match(r"(\d{3})_", path.name)
    return int(match.group(1)) if match else None


def build_post_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rank_index = make_rank_index()
    audit_rows = {as_int(r.get("fortune_rank")): r for r in read_csv(AUDIT_SUMMARY)}
    output_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []
    seen_tweet_ids: Counter[str] = Counter()

    for folder in sorted(RAW_ROOT.glob("*")):
        if not folder.is_dir():
            continue
        rank = get_rank_from_folder(folder)
        posts_path = folder / "posts.csv"
        posts = read_csv(posts_path)
        metadata = rank_index.get(rank or -1, {})
        audit = audit_rows.get(rank, {})
        company = first_present(metadata, ["company_name"]) or first_present(audit, ["company_name"])
        if not company and posts:
            company = first_present(posts[0], ["company_name"])
        norm_company = first_present(metadata, ["normalized_company_name"]) or normalized_name(company)

        status = first_present(audit, ["status"])
        coverage_rows.append(
            {
                "fortune_rank": rank or "",
                "company_name": company,
                "normalized_company_name": norm_company,
                "raw_folder": str(folder.relative_to(ROOT)),
                "posts_csv_exists": str(posts_path.exists()).lower(),
                "posts_csv_non_empty": str(bool(posts)).lower(),
                "post_count": len(posts),
                "collection_status": status,
                "collection_error_type": first_present(audit, ["error_type"]),
                "collection_error_message": first_present(audit, ["error_message"]),
                "attempted": first_present(audit, ["attempted"]),
                "official_x_handle": first_present(audit, ["official_x_handle"]),
                "final_manual_account_status": first_present(metadata, ["final_manual_account_status"]),
                "final_manual_scrape_eligible": first_present(metadata, ["final_manual_scrape_eligible"]),
            }
        )

        for row in posts:
            reply_count = as_int(first_present(row, ["reply_count", "replies", "reply"]))
            repost_value = first_present(row, ["repost_count", "retweet_count", "retweets"])
            like_value = first_present(row, ["like_count", "favorite_count", "favorites"])
            quote_count = as_int(first_present(row, ["quote_count", "quotes"]))
            repost_count = as_int(repost_value)
            like_count = as_int(like_value)
            total = sum(safe_count(v) for v in [reply_count, repost_count, like_count, quote_count])
            tweet_id = str(first_present(row, ["tweet_id", "id", "status_id"]))
            seen_tweet_ids[tweet_id] += 1
            text = first_present(row, ["text", "full_text", "content"])
            source_handle = first_present(row, ["source_x_handle", "official_x_handle"]) or first_present(
                metadata, ["collection_x_handle"]
            )
            output_rows.append(
                {
                    "fortune_rank": as_int(first_present(row, ["fortune_rank"])) or rank or "",
                    "company_name": first_present(row, ["company_name"]) or company,
                    "normalized_company_name": norm_company,
                    "source_x_handle": source_handle,
                    "source_x_url": first_present(row, ["source_x_url"]) or first_present(metadata, ["collection_x_url", "final_manual_x_url_primary"]),
                    "account_role": first_present(row, ["account_role"]),
                    "account_index": as_int(first_present(row, ["account_index"])) or "",
                    "tweet_id": tweet_id,
                    "tweet_url": first_present(row, ["tweet_url", "url"]),
                    "created_at": first_present(row, ["created_at", "created_time"]),
                    "text": text,
                    "reply_count": reply_count if reply_count is not None else "",
                    "repost_count": repost_count if repost_count is not None else "",
                    "retweet_count": repost_count if repost_count is not None else "",
                    "like_count": like_count if like_count is not None else "",
                    "favorite_count": like_count if like_count is not None else "",
                    "quote_count": quote_count if quote_count is not None else "",
                    "view_count_available": first_present(row, ["view_count_available"]),
                    "total_engagement": total,
                    "log_total_engagement": log1p(total),
                    "text_length": len(text),
                    "hashtag_count": len(re.findall(r"(?<!\w)#\w+", text)),
                    "mention_count": len(re.findall(r"(?<!\w)@\w+", text)),
                    "collection_method": first_present(row, ["collection_method"]),
                    "max_posts_cap": first_present(row, ["max_posts_cap"]),
                    "source_folder": first_present(row, ["source_folder"]) or str(folder.relative_to(ROOT)),
                }
            )

    duplicate_ids = {tweet_id for tweet_id, count in seen_tweet_ids.items() if tweet_id and count > 1}
    duplicate_rows = [row for row in output_rows if row["tweet_id"] in duplicate_ids]
    write_csv(DUPLICATE_CSV, duplicate_rows, POST_COLUMNS)

    # Deterministic deduplication: keep the highest engagement copy, then first sorted source_folder.
    best: dict[str, dict[str, object]] = {}
    for row in output_rows:
        tweet_id = str(row["tweet_id"])
        if not tweet_id:
            key = f"missing:{len(best)}"
        else:
            key = tweet_id
        current = best.get(key)
        if current is None:
            best[key] = row
            continue
        current_score = safe_count(current.get("total_engagement"))
        row_score = safe_count(row.get("total_engagement"))
        if (row_score, str(row.get("source_folder"))) > (current_score, str(current.get("source_folder"))):
            best[key] = row

    deduped = sorted(
        best.values(),
        key=lambda r: (
            as_int(r.get("fortune_rank")) or 999,
            str(r.get("source_x_handle")),
            str(r.get("created_at")),
            str(r.get("tweet_id")),
        ),
    )
    return deduped, coverage_rows


def write_missingness(rows: list[dict[str, object]]) -> None:
    summary = []
    total = len(rows)
    for column in POST_COLUMNS:
        missing = sum(1 for row in rows if row.get(column) in ("", None))
        summary.append(
            {
                "dataset": "fortune100_post_master",
                "column": column,
                "row_count": total,
                "missing_count": missing,
                "missing_rate": round(missing / total, 6) if total else "",
            }
        )
    write_csv(MISSINGNESS_CSV, summary, ["dataset", "column", "row_count", "missing_count", "missing_rate"])


def write_coverage_report(rows: list[dict[str, object]], coverage_rows: list[dict[str, object]]) -> None:
    total_posts = len(rows)
    firms_with_posts = sum(1 for row in coverage_rows if row["posts_csv_exists"] == "true")
    non_empty = sum(1 for row in coverage_rows if row["posts_csv_non_empty"] == "true")
    empty = [row for row in coverage_rows if row["posts_csv_exists"] == "true" and row["posts_csv_non_empty"] == "false"]
    failed = [row for row in coverage_rows if row.get("collection_status") not in ("", "success")]
    dup_count = sum(1 for row in read_csv(DUPLICATE_CSV))
    missing_text = sum(1 for row in rows if row.get("text") in ("", None))
    missing_eng = sum(1 for row in rows if row.get("total_engagement") in ("", None))
    account_counts = Counter((row.get("company_name"), row.get("source_x_handle")) for row in rows)

    lines = [
        "# Coverage Diagnostics",
        "",
        "Generated from existing repository files only. No X collection, X API call, SEC download, dashboard sync, or model inference is performed.",
        "",
        "## Summary",
        "",
        f"- Fortune Top 100 raw folders inspected: {len(coverage_rows)}",
        f"- posts.csv exists firms: {firms_with_posts}",
        f"- non-empty posts.csv firms: {non_empty}",
        f"- total deduplicated posts: {total_posts}",
        f"- duplicate tweet rows audited before deduplication: {dup_count}",
        f"- missing text rows: {missing_text}",
        f"- missing engagement proxy rows: {missing_eng}",
        f"- collection status not success / not empty: {len(failed)}",
        f"- empty posts.csv firms: {len(empty)}",
        "",
        "## Deduplication Rule",
        "",
        "Rows are deduplicated by `tweet_id`. If the same tweet id appears more than once, the retained row is the copy with the highest `total_engagement`; ties are resolved by lexicographic `source_folder`. All duplicate source rows are written to `data/diagnostics/fortune100_duplicate_tweet_audit.csv`.",
        "",
        "## Post Format Controls",
        "",
        "The literature-based post format controls prepared for hypothesis datasets are exactly `text_length`, `hashtag_count`, and `mention_count`. `emoji_count` is intentionally excluded.",
        "",
        "## Largest Account-Level Post Counts",
        "",
    ]
    for (company, handle), count in account_counts.most_common(20):
        lines.append(f"- {company} / {handle}: {count}")
    lines.extend(
        [
            "",
            "## Empty Or Failed Coverage Rows",
            "",
        ]
    )
    for row in failed + empty:
        lines.append(
            f"- rank {row.get('fortune_rank')}: {row.get('company_name')} status={row.get('collection_status')} posts={row.get('post_count')} error={row.get('collection_error_type')}"
        )
    COVERAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, coverage_rows = build_post_rows()
    write_csv(POST_MASTER_CSV, rows, POST_COLUMNS)
    write_json(POST_MASTER_JSON, rows)
    write_csv(
        COVERAGE_CSV,
        coverage_rows,
        [
            "fortune_rank",
            "company_name",
            "normalized_company_name",
            "raw_folder",
            "posts_csv_exists",
            "posts_csv_non_empty",
            "post_count",
            "collection_status",
            "collection_error_type",
            "collection_error_message",
            "attempted",
            "official_x_handle",
            "final_manual_account_status",
            "final_manual_scrape_eligible",
        ],
    )
    write_missingness(rows)
    write_coverage_report(rows, coverage_rows)
    print(f"wrote {POST_MASTER_CSV.relative_to(ROOT)} rows={len(rows)}")
    print(f"wrote {COVERAGE_CSV.relative_to(ROOT)} firms={len(coverage_rows)}")


if __name__ == "__main__":
    main()
