#!/usr/bin/env python3
"""Build firm-period panel variables for H3 readiness."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "20260618expand"
POST_MASTER = PACKAGE / "data/processed/fortune100_post_master.csv"
HUMOR = PACKAGE / "data/processed/fortune100_humor_variables.csv"
OUT = PACKAGE / "data/processed/fortune100_firm_period_panel.csv"

FIELDS = [
    "fortune_rank",
    "company_name",
    "period",
    "period_level",
    "post_count",
    "humor_post_count",
    "humor_usage_rate",
    "aggressive_humor_post_count",
    "aggressive_humor_usage_rate",
    "mean_total_engagement",
    "median_total_engagement",
    "mean_log_total_engagement",
    "sum_total_engagement",
    "mean_text_length",
    "mean_hashtag_count",
    "mean_mention_count",
    "aggressive_humor_usage_intensity",
    "aggressive_humor_usage_intensity_sq",
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


def number(value: object) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def period_from_created_at(value: str) -> str:
    if not value:
        return "missing_period"
    parsers = [
        lambda v: parsedate_to_datetime(v),
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
    ]
    for parser in parsers:
        try:
            dt = parser(value)
            return f"{dt.year:04d}-{dt.month:02d}"
        except (TypeError, ValueError, IndexError):
            continue
    return "missing_period"


def mean(values: list[float]) -> float | str:
    return round(sum(values) / len(values), 12) if values else ""


def median(values: list[float]) -> float | str:
    if not values:
        return ""
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 12)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 12)


def main() -> None:
    posts = read_csv(POST_MASTER)
    humor = {row.get("tweet_id", ""): row for row in read_csv(HUMOR)}
    buckets: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for post in posts:
        key = (post.get("company_name", ""), period_from_created_at(post.get("created_at", "")))
        merged = dict(post)
        merged.update(humor.get(post.get("tweet_id", ""), {}))
        buckets[key].append(merged)

    rows: list[dict[str, object]] = []
    for (_company, period), bucket in sorted(buckets.items(), key=lambda item: (item[1][0].get("fortune_rank", ""), item[0][1])):
        post_count = len(bucket)
        humor_count = sum(1 for row in bucket if row.get("humor_presence") == "1")
        aggressive_count = sum(1 for row in bucket if row.get("aggressive_humor") == "1")
        engagement = [number(row.get("total_engagement")) for row in bucket]
        engagement = [v for v in engagement if v is not None]
        log_engagement = [number(row.get("log_total_engagement")) for row in bucket]
        log_engagement = [v for v in log_engagement if v is not None]
        text_length = [number(row.get("text_length")) for row in bucket]
        text_length = [v for v in text_length if v is not None]
        hashtag_count = [number(row.get("hashtag_count")) for row in bucket]
        hashtag_count = [v for v in hashtag_count if v is not None]
        mention_count = [number(row.get("mention_count")) for row in bucket]
        mention_count = [v for v in mention_count if v is not None]
        aggressive_rate = aggressive_count / post_count if post_count else 0
        rows.append(
            {
                "fortune_rank": bucket[0].get("fortune_rank", ""),
                "company_name": bucket[0].get("company_name", ""),
                "period": period,
                "period_level": "firm_month",
                "post_count": post_count,
                "humor_post_count": humor_count,
                "humor_usage_rate": round(humor_count / post_count, 12) if post_count else "",
                "aggressive_humor_post_count": aggressive_count,
                "aggressive_humor_usage_rate": round(aggressive_rate, 12),
                "mean_total_engagement": mean(engagement),
                "median_total_engagement": median(engagement),
                "mean_log_total_engagement": mean(log_engagement),
                "sum_total_engagement": round(sum(engagement), 12) if engagement else "",
                "mean_text_length": mean(text_length),
                "mean_hashtag_count": mean(hashtag_count),
                "mean_mention_count": mean(mention_count),
                "aggressive_humor_usage_intensity": round(aggressive_rate, 12),
                "aggressive_humor_usage_intensity_sq": round(aggressive_rate * aggressive_rate, 12),
            }
        )
    write_csv(OUT, rows, FIELDS)
    print(f"wrote {OUT.relative_to(ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
