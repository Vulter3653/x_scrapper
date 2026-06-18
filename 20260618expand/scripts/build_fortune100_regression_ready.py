#!/usr/bin/env python3
"""Build post-level and firm-period regression-ready datasets for H1/H2/H3."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "20260618expand"
POST_MASTER = PACKAGE / "data/processed/fortune100_post_master.csv"
HUMOR = PACKAGE / "data/processed/fortune100_humor_variables.csv"
PANEL = PACKAGE / "data/processed/fortune100_firm_period_panel.csv"
OUT_DIR = PACKAGE / "data/regression_ready"
POST_OUT = OUT_DIR / "fortune100_post_level_regression_ready.csv"
PANEL_OUT = OUT_DIR / "fortune100_firm_period_regression_ready.csv"
LEGACY_OUT = OUT_DIR / "fortune100_h1_h2_h3_regression_ready.csv"

POST_FIELDS = [
    "tweet_id",
    "fortune_rank",
    "company_name",
    "source_x_handle",
    "period",
    "log_total_engagement",
    "total_engagement",
    "humor_presence",
    "aggressive_humor",
    "affiliative_humor",
    "self_enhancing_humor",
    "self_defeating_humor",
    "non_humorous",
    "text_length",
    "hashtag_count",
    "mention_count",
    "h1_sample_inclusion_flag",
    "h2_sample_inclusion_flag",
    "missingness_flag",
    "classification_source",
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


def period(value: str) -> str:
    if not value:
        return "missing_period"
    parts = value.split()
    if len(parts) >= 4 and parts[-1].isdigit():
        months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        return f"{parts[-1]}-{months.get(parts[1], '00')}"
    return value[:7] if len(value) >= 7 else "missing_period"


def present(row: dict[str, str], columns: list[str]) -> bool:
    return all(row.get(column) not in ("", None) for column in columns)


def main() -> None:
    posts = read_csv(POST_MASTER)
    humor = {row.get("tweet_id", ""): row for row in read_csv(HUMOR)}
    post_rows: list[dict[str, object]] = []
    for post in posts:
        merged = dict(post)
        merged.update(humor.get(post.get("tweet_id", ""), {}))
        h1_ready = present(merged, ["log_total_engagement", "humor_presence", "text_length", "hashtag_count", "mention_count"])
        h2_ready = h1_ready and any(merged.get(col) == "1" for col in ["aggressive_humor", "affiliative_humor", "self_enhancing_humor", "self_defeating_humor", "non_humorous"])
        missing_bits = []
        for column in ["log_total_engagement", "humor_presence", "text_length", "hashtag_count", "mention_count"]:
            if merged.get(column) in ("", None):
                missing_bits.append(column)
        post_rows.append(
            {
                "tweet_id": merged.get("tweet_id", ""),
                "fortune_rank": merged.get("fortune_rank", ""),
                "company_name": merged.get("company_name", ""),
                "source_x_handle": merged.get("source_x_handle", ""),
                "period": period(merged.get("created_at", "")),
                "log_total_engagement": merged.get("log_total_engagement", ""),
                "total_engagement": merged.get("total_engagement", ""),
                "humor_presence": merged.get("humor_presence", ""),
                "aggressive_humor": merged.get("aggressive_humor", ""),
                "affiliative_humor": merged.get("affiliative_humor", ""),
                "self_enhancing_humor": merged.get("self_enhancing_humor", ""),
                "self_defeating_humor": merged.get("self_defeating_humor", ""),
                "non_humorous": merged.get("non_humorous", ""),
                "text_length": merged.get("text_length", ""),
                "hashtag_count": merged.get("hashtag_count", ""),
                "mention_count": merged.get("mention_count", ""),
                "h1_sample_inclusion_flag": "1" if h1_ready else "0",
                "h2_sample_inclusion_flag": "1" if h2_ready else "0",
                "missingness_flag": ";".join(missing_bits),
                "classification_source": merged.get("classification_source", ""),
            }
        )

    panel_rows = read_csv(PANEL)
    for row in panel_rows:
        ready = present(
            row,
            [
                "mean_log_total_engagement",
                "aggressive_humor_usage_intensity",
                "aggressive_humor_usage_intensity_sq",
                "mean_text_length",
                "mean_hashtag_count",
                "mean_mention_count",
            ],
        )
        row["h3_sample_inclusion_flag"] = "1" if ready else "0"
        row["missingness_flag"] = "" if ready else "missing_required_h3_variable"

    write_csv(POST_OUT, post_rows, POST_FIELDS)
    write_csv(LEGACY_OUT, post_rows, POST_FIELDS)
    write_csv(PANEL_OUT, panel_rows, list(panel_rows[0].keys()) if panel_rows else [])
    print(f"wrote {POST_OUT.relative_to(ROOT)} rows={len(post_rows)}")
    print(f"wrote {PANEL_OUT.relative_to(ROOT)} rows={len(panel_rows)}")


if __name__ == "__main__":
    main()
