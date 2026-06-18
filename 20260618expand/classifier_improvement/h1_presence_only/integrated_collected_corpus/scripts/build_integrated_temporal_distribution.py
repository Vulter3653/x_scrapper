"""Build temporal diagnostics for the integrated collected corpus."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "integrated_collected_corpus"
DATA = BASE / "data" / "integrated_h1_presence_classified_posts.csv"
RESULTS = BASE / "results"
FIGURES = BASE / "figures"


def read_rows() -> list[dict[str, str]]:
    with DATA.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rate(num: int, den: int) -> float:
    return round(num / den, 6) if den else 0.0


def mean_prob(group: list[dict[str, str]]) -> float:
    probs = [fnum(row["h1_humor_presence_probability"]) for row in group if row.get("h1_humor_presence_probability")]
    probs = [p for p in probs if p is not None]
    return round(sum(probs) / len(probs), 6) if probs else 0.0


def aggregate(rows: list[dict[str, str]], key: str, include_name: bool = False) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get(key) != "":
            buckets[row[key]].append(row)
    out = []
    for value in sorted(buckets, key=lambda x: int(x) if str(x).isdigit() else str(x)):
        group = buckets[value]
        total = len(group)
        humor = sum(1 for row in group if row.get("h1_humor_presence_pred_t50") == "1")
        item = {
            key: value,
            "total_posts": str(total),
            "humor_posts_t50": str(humor),
            "non_humor_posts_t50": str(total - humor),
            "humor_rate_t50": str(rate(humor, total)),
            "mean_humor_probability": str(mean_prob(group)),
        }
        if include_name:
            names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            item["day_of_week_name"] = names[int(value)]
        out.append(item)
    return out


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def bar(rows: list[dict[str, str]], x: str, y: str, title: str, xlabel: str, ylabel: str, path: Path, rotate: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([row.get(x, "") for row in rows], [float(row[y]) for row in rows])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if rotate:
        ax.tick_params(axis="x", rotation=rotate)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def line(rows: list[dict[str, str]], x: str, y: str, title: str, xlabel: str, ylabel: str, path: Path, rotate: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot([row.get(x, "") for row in rows], [float(row[y]) for row in rows], marker="o")
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


def max_key(rows: list[dict[str, str]], key: str, metric: str) -> str:
    return max(rows, key=lambda row: float(row[metric]))[key] if rows else ""


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    parsed_rows = [row for row in rows if row.get("missing_date") == "0"]

    year = aggregate(parsed_rows, "year")
    year_month = aggregate(parsed_rows, "year_month")
    month = aggregate(parsed_rows, "month_of_year")
    day_month = aggregate(parsed_rows, "day_of_month")
    day_week = aggregate(parsed_rows, "day_of_week", include_name=True)
    hour = aggregate(parsed_rows, "hour_of_day")

    write_csv(RESULTS / "year_distribution.csv", ["year", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], year)
    write_csv(RESULTS / "year_month_distribution.csv", ["year_month", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], year_month)
    write_csv(RESULTS / "month_of_year_distribution.csv", ["month_of_year", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], month)
    write_csv(RESULTS / "day_of_month_distribution.csv", ["day_of_month", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], day_month)
    write_csv(RESULTS / "day_of_week_distribution.csv", ["day_of_week", "day_of_week_name", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], day_week)
    write_csv(RESULTS / "hour_of_day_distribution.csv", ["hour_of_day", "total_posts", "humor_posts_t50", "non_humor_posts_t50", "humor_rate_t50", "mean_humor_probability"], hour)

    dates = [row["date"] for row in parsed_rows if row.get("date")]
    summary = {
        "total_posts": str(len(rows)),
        "parsed_date_rows": str(len(parsed_rows)),
        "missing_date_rows": str(len(rows) - len(parsed_rows)),
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
        "n_years": str(len(year)),
        "n_year_months": str(len(year_month)),
        "most_active_year": max_key(year, "year", "total_posts"),
        "most_active_month": max_key(year_month, "year_month", "total_posts"),
        "most_active_hour": max_key(hour, "hour_of_day", "total_posts"),
        "highest_humor_rate_hour_t50": max_key(hour, "hour_of_day", "humor_rate_t50"),
        "lowest_humor_rate_hour_t50": min(hour, key=lambda row: float(row["humor_rate_t50"]))["hour_of_day"] if hour else "",
    }
    write_csv(RESULTS / "temporal_distribution_summary.csv", list(summary.keys()), [summary])

    bar(year, "year", "total_posts", "Integrated Corpus Post Count by Year", "Year", "Total posts", FIGURES / "year_post_count.png")
    line(year, "year", "humor_rate_t50", "Integrated Corpus Humor Rate by Year (t50)", "Year", "Humor rate t50", FIGURES / "year_humor_rate_t50.png")
    bar(year_month, "year_month", "total_posts", "Integrated Corpus Post Count by Year-Month", "Year-month", "Total posts", FIGURES / "year_month_post_count.png", rotate=60)
    line(year_month, "year_month", "humor_rate_t50", "Integrated Corpus Humor Rate by Year-Month (t50)", "Year-month", "Humor rate t50", FIGURES / "year_month_humor_rate_t50.png", rotate=60)
    bar(month, "month_of_year", "total_posts", "Integrated Corpus Post Count by Month", "Month", "Total posts", FIGURES / "month_of_year_post_count.png")
    line(month, "month_of_year", "humor_rate_t50", "Integrated Corpus Humor Rate by Month (t50)", "Month", "Humor rate t50", FIGURES / "month_of_year_humor_rate_t50.png")
    bar(day_month, "day_of_month", "total_posts", "Integrated Corpus Post Count by Day of Month", "Day", "Total posts", FIGURES / "day_of_month_post_count.png")
    bar(day_week, "day_of_week_name", "total_posts", "Integrated Corpus Post Count by Day of Week", "Day of week", "Total posts", FIGURES / "day_of_week_post_count.png", rotate=30)
    line(day_week, "day_of_week_name", "humor_rate_t50", "Integrated Corpus Humor Rate by Day of Week (t50)", "Day of week", "Humor rate t50", FIGURES / "day_of_week_humor_rate_t50.png", rotate=30)
    bar(hour, "hour_of_day", "total_posts", "Integrated Corpus Post Count by Hour", "Hour UTC", "Total posts", FIGURES / "hour_of_day_post_count.png")
    line(hour, "hour_of_day", "humor_rate_t50", "Integrated Corpus Humor Rate by Hour (t50)", "Hour UTC", "Humor rate t50", FIGURES / "hour_of_day_humor_rate_t50.png")

    print("Integrated temporal distribution built")
    print(f"rows={len(rows)}")
    print(f"year_rows={len(year)}")
    print(f"year_month_rows={len(year_month)}")
    print(f"hour_rows={len(hour)}")


if __name__ == "__main__":
    main()
