"""Build temporal distribution diagnostics for H1 presence-only classifications.

This script is descriptive only. It does not retrain classifiers, apply a
classifier, run regressions, or produce H1 support claims.
"""

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only"
WORK_DIR = BASE / "temporal_distribution"
INPUT = (
    BASE
    / "full_corpus_classification"
    / "data"
    / "fortune100_h1_presence_classified_posts.csv"
)
RESULTS = WORK_DIR / "results"
FIGURES = WORK_DIR / "figures"
REPORTS = WORK_DIR / "reports"

PRED_T50 = "h1_humor_presence_pred_t50"
PRED_T40 = "h1_humor_presence_pred_t40"
PRED_T60 = "h1_humor_presence_pred_t60"
PROB = "h1_humor_presence_probability"


def parse_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for parser in (
        lambda x: datetime.fromisoformat(x),
        lambda x: datetime.strptime(x, "%a %b %d %H:%M:%S %z %Y"),
        lambda x: datetime.strptime(x[:19], "%Y-%m-%d %H:%M:%S"),
        lambda x: datetime.strptime(x[:10], "%Y-%m-%d"),
    ):
        try:
            return parser(text)
        except ValueError:
            continue
    return None


def as_int(value: str) -> int:
    text = (value or "").strip()
    if text in {"1", "1.0", "True", "true", "TRUE"}:
        return 1
    return 0


def as_float(value: str) -> float | None:
    try:
        number = float((value or "").strip())
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def mean(values: Iterable[float | None]) -> float:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 6) if clean else 0.0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict], key: str, include_probability: bool, include_t40_t60: bool) -> list[dict]:
    buckets: dict[str | int, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[row[key]].append(row)

    output = []
    for bucket_key in sorted(buckets):
        group = buckets[bucket_key]
        total = len(group)
        humor_t50 = sum(row["pred_t50"] for row in group)
        item = {
            key: bucket_key,
            "total_posts": total,
            "humor_posts_t50": humor_t50,
            "non_humor_posts_t50": total - humor_t50,
            "humor_rate_t50": safe_rate(humor_t50, total),
        }
        if include_t40_t60:
            item["humor_rate_t40"] = safe_rate(sum(row["pred_t40"] for row in group), total)
            item["humor_rate_t60"] = safe_rate(sum(row["pred_t60"] for row in group), total)
        if include_probability:
            item["mean_humor_probability"] = mean(row["probability"] for row in group)
        output.append(item)
    return output


def bar_plot(rows: list[dict], x: str, y: str, title: str, xlabel: str, ylabel: str, path: Path, rotate: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([str(row[x]) for row in rows], [row[y] for row in rows])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if rotate:
        ax.tick_params(axis="x", rotation=rotate)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def line_plot(rows: list[dict], x: str, y: str, title: str, xlabel: str, ylabel: str, path: Path, rotate: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = [str(row[x]) for row in rows]
    values = [row[y] for row in rows]
    ax.plot(labels, values, marker="o")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1)
    if rotate:
        ax.tick_params(axis="x", rotation=rotate)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def max_key(rows: list[dict], key: str, value: str) -> str:
    if not rows:
        return ""
    return str(max(rows, key=lambda row: row[value])[key])


def min_rate_key(rows: list[dict], key: str) -> str:
    eligible = [row for row in rows if row["total_posts"] > 0]
    if not eligible:
        return ""
    return str(min(eligible, key=lambda row: row["humor_rate_t50"])[key])


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    parsed_rows: list[dict] = []
    total_input_rows = 0
    missing_date_rows = 0

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        date_col = "created_at" if "created_at" in fieldnames else "date"
        for source in reader:
            total_input_rows += 1
            dt = parse_datetime(source.get(date_col, ""))
            if dt is None:
                missing_date_rows += 1
                continue
            parsed_rows.append(
                {
                    "year": dt.year,
                    "year_month": dt.strftime("%Y-%m"),
                    "month_of_year": dt.month,
                    "day_of_month": dt.day,
                    "day_of_week": dt.weekday(),
                    "day_of_week_name": dt.strftime("%A"),
                    "hour_of_day": dt.hour,
                    "date": dt.strftime("%Y-%m-%d"),
                    "pred_t50": as_int(source.get(PRED_T50, "")),
                    "pred_t40": as_int(source.get(PRED_T40, "")),
                    "pred_t60": as_int(source.get(PRED_T60, "")),
                    "probability": as_float(source.get(PROB, "")),
                }
            )

    year_rows = aggregate(parsed_rows, "year", include_probability=False, include_t40_t60=True)
    year_month_rows = aggregate(parsed_rows, "year_month", include_probability=True, include_t40_t60=False)
    month_rows = aggregate(parsed_rows, "month_of_year", include_probability=True, include_t40_t60=False)
    day_month_rows = aggregate(parsed_rows, "day_of_month", include_probability=False, include_t40_t60=False)
    day_week_rows = aggregate(parsed_rows, "day_of_week", include_probability=False, include_t40_t60=False)
    for row in day_week_rows:
        row["day_of_week_name"] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][int(row["day_of_week"])]
    hour_rows = aggregate(parsed_rows, "hour_of_day", include_probability=True, include_t40_t60=False)

    write_csv(
        RESULTS / "year_distribution.csv",
        ["year", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "humor_rate_t40", "humor_rate_t60"],
        year_rows,
    )
    write_csv(
        RESULTS / "year_month_distribution.csv",
        ["year_month", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"],
        year_month_rows,
    )
    write_csv(
        RESULTS / "month_of_year_distribution.csv",
        ["month_of_year", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"],
        month_rows,
    )
    write_csv(
        RESULTS / "day_of_month_distribution.csv",
        ["day_of_month", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50"],
        day_month_rows,
    )
    write_csv(
        RESULTS / "day_of_week_distribution.csv",
        ["day_of_week", "day_of_week_name", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50"],
        day_week_rows,
    )
    write_csv(
        RESULTS / "hour_of_day_distribution.csv",
        ["hour_of_day", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"],
        hour_rows,
    )

    dates = [row["date"] for row in parsed_rows]
    summary = {
        "total_posts": total_input_rows,
        "parsed_date_rows": len(parsed_rows),
        "missing_date_rows": missing_date_rows,
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
        "n_years": len(year_rows),
        "n_year_months": len(year_month_rows),
        "most_active_year": max_key(year_rows, "year", "total_posts"),
        "most_active_month": max_key(year_month_rows, "year_month", "total_posts"),
        "most_active_hour": max_key(hour_rows, "hour_of_day", "total_posts"),
        "highest_humor_rate_hour_t50": max_key(hour_rows, "hour_of_day", "humor_rate_t50"),
        "lowest_humor_rate_hour_t50": min_rate_key(hour_rows, "hour_of_day"),
    }
    write_csv(RESULTS / "temporal_distribution_summary.csv", list(summary.keys()), [summary])

    bar_plot(year_rows, "year", "total_posts", "Post Count by Year", "Year", "Total posts", FIGURES / "year_post_count.png")
    line_plot(year_rows, "year", "humor_rate_t50", "Humor Rate by Year (t50)", "Year", "Humor rate t50", FIGURES / "year_humor_rate_t50.png")
    bar_plot(year_month_rows, "year_month", "total_posts", "Post Count by Year-Month", "Year-month", "Total posts", FIGURES / "year_month_post_count.png", rotate=60)
    line_plot(year_month_rows, "year_month", "humor_rate_t50", "Humor Rate by Year-Month (t50)", "Year-month", "Humor rate t50", FIGURES / "year_month_humor_rate_t50.png", rotate=60)
    bar_plot(month_rows, "month_of_year", "total_posts", "Post Count by Month of Year", "Month", "Total posts", FIGURES / "month_of_year_post_count.png")
    line_plot(month_rows, "month_of_year", "humor_rate_t50", "Humor Rate by Month of Year (t50)", "Month", "Humor rate t50", FIGURES / "month_of_year_humor_rate_t50.png")
    bar_plot(day_month_rows, "day_of_month", "total_posts", "Post Count by Day of Month", "Day of month", "Total posts", FIGURES / "day_of_month_post_count.png")
    bar_plot(day_week_rows, "day_of_week_name", "total_posts", "Post Count by Day of Week", "Day of week", "Total posts", FIGURES / "day_of_week_post_count.png", rotate=30)
    line_plot(day_week_rows, "day_of_week_name", "humor_rate_t50", "Humor Rate by Day of Week (t50)", "Day of week", "Humor rate t50", FIGURES / "day_of_week_humor_rate_t50.png", rotate=30)
    bar_plot(hour_rows, "hour_of_day", "total_posts", "Post Count by Hour of Day", "Hour of day", "Total posts", FIGURES / "hour_of_day_post_count.png")
    line_plot(hour_rows, "hour_of_day", "humor_rate_t50", "Humor Rate by Hour of Day (t50)", "Hour of day", "Humor rate t50", FIGURES / "hour_of_day_humor_rate_t50.png")

    memo = f"""# H1 Temporal Distribution Memo

## Scope

This analysis is descriptive distribution checking for H1 presence-only full corpus classification output.
It is not a regression analysis, not causal evidence, and not an H1 support judgment.

## Input

- Input file: `{INPUT.relative_to(ROOT)}`
- Input rows: {total_input_rows}
- Parsed date rows: {len(parsed_rows)}
- Missing date rows: {missing_date_rows}
- Date range: {summary['min_date']} to {summary['max_date']}

## Descriptive Summary

- Years observed: {summary['n_years']}
- Year-month periods observed: {summary['n_year_months']}
- Most active year: {summary['most_active_year']}
- Most active year-month: {summary['most_active_month']}
- Most active hour: {summary['most_active_hour']}
- Highest humor_rate_t50 hour: {summary['highest_humor_rate_hour_t50']}
- Lowest humor_rate_t50 hour: {summary['lowest_humor_rate_hour_t50']}

## Interpretation Boundary

The main descriptive threshold is `h1_humor_presence_pred_t50`.
The t40 and t60 rates are included only as threshold-sensitivity reference points.
They should not be interpreted as separate hypothesis tests.

No fixed effects, regressions, causal interpretations, H2/H3 tests, type classifier outputs,
or aggressive detector outputs are produced here.
"""
    (REPORTS / "temporal_distribution_memo.md").write_text(memo, encoding="utf-8")

    print("H1 temporal distribution build complete")
    print(f"input_rows={total_input_rows}")
    print(f"parsed_date_rows={len(parsed_rows)}")
    print(f"missing_date_rows={missing_date_rows}")
    print(f"output_dir={WORK_DIR}")


if __name__ == "__main__":
    main()
