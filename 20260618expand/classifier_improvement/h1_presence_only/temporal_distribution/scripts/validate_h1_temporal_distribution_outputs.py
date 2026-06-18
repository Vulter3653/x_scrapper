"""Validate H1 temporal distribution diagnostics."""

from __future__ import annotations

import csv
from pathlib import Path


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

REQUIRED_RESULTS = [
    "year_distribution.csv",
    "year_month_distribution.csv",
    "month_of_year_distribution.csv",
    "day_of_month_distribution.csv",
    "day_of_week_distribution.csv",
    "hour_of_day_distribution.csv",
    "temporal_distribution_summary.csv",
]

REQUIRED_FIGURES = [
    "year_post_count.png",
    "year_humor_rate_t50.png",
    "year_month_post_count.png",
    "year_month_humor_rate_t50.png",
    "month_of_year_post_count.png",
    "month_of_year_humor_rate_t50.png",
    "day_of_month_post_count.png",
    "day_of_week_post_count.png",
    "day_of_week_humor_rate_t50.png",
    "hour_of_day_post_count.png",
    "hour_of_day_humor_rate_t50.png",
]

FORBIDDEN_PATTERNS = [
    "*regression*",
    "*type*",
    "*aggressive*",
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rate_ok(rows: list[dict], column: str) -> bool:
    for row in rows:
        value = float(row[column])
        if value < 0 or value > 1:
            return False
    return True


def main() -> int:
    failures: list[str] = []

    if not INPUT.exists():
        failures.append(f"input missing: {INPUT}")
    else:
        with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
            input_rows = sum(1 for _ in csv.DictReader(f))

    for name in REQUIRED_RESULTS:
        if not (RESULTS / name).exists():
            failures.append(f"missing result csv: {name}")

    for name in REQUIRED_FIGURES:
        path = FIGURES / name
        if not path.exists():
            failures.append(f"missing figure png: {name}")
        elif path.stat().st_size == 0:
            failures.append(f"empty figure png: {name}")

    if not failures:
        summary = read_csv(RESULTS / "temporal_distribution_summary.csv")
        if len(summary) != 1:
            failures.append("temporal_distribution_summary.csv must have one row")
        else:
            row = summary[0]
            total_posts = int(row["total_posts"])
            parsed_rows = int(row["parsed_date_rows"])
            missing_rows = int(row["missing_date_rows"])
            if total_posts != input_rows:
                failures.append(f"summary total_posts {total_posts} != input rows {input_rows}")
            if parsed_rows + missing_rows != input_rows:
                failures.append("parsed_date_rows + missing_date_rows != input rows")

        year_rows = read_csv(RESULTS / "year_distribution.csv")
        if sum(int(row["total_posts"]) for row in year_rows) != input_rows:
            failures.append("year_distribution total_posts does not equal input row count")
        for column in ["humor_rate_t50", "humor_rate_t40", "humor_rate_t60"]:
            if not rate_ok(year_rows, column):
                failures.append(f"year_distribution {column} outside 0-1")

        month_rows = read_csv(RESULTS / "month_of_year_distribution.csv")
        if any(int(row["month_of_year"]) < 1 or int(row["month_of_year"]) > 12 for row in month_rows):
            failures.append("month_of_year outside 1-12")
        if not rate_ok(month_rows, "humor_rate_t50"):
            failures.append("month_of_year humor_rate_t50 outside 0-1")

        day_rows = read_csv(RESULTS / "day_of_month_distribution.csv")
        if any(int(row["day_of_month"]) < 1 or int(row["day_of_month"]) > 31 for row in day_rows):
            failures.append("day_of_month outside 1-31")
        if not rate_ok(day_rows, "humor_rate_t50"):
            failures.append("day_of_month humor_rate_t50 outside 0-1")

        hour_rows = read_csv(RESULTS / "hour_of_day_distribution.csv")
        if any(int(row["hour_of_day"]) < 0 or int(row["hour_of_day"]) > 23 for row in hour_rows):
            failures.append("hour_of_day outside 0-23")
        if not rate_ok(hour_rows, "humor_rate_t50"):
            failures.append("hour_of_day humor_rate_t50 outside 0-1")

        day_week_rows = read_csv(RESULTS / "day_of_week_distribution.csv")
        if any(int(row["day_of_week"]) < 0 or int(row["day_of_week"]) > 6 for row in day_week_rows):
            failures.append("day_of_week outside 0-6")
        if not rate_ok(day_week_rows, "humor_rate_t50"):
            failures.append("day_of_week humor_rate_t50 outside 0-1")

        year_month_rows = read_csv(RESULTS / "year_month_distribution.csv")
        if not rate_ok(year_month_rows, "humor_rate_t50"):
            failures.append("year_month humor_rate_t50 outside 0-1")

    for pattern in FORBIDDEN_PATTERNS:
        matches = [
            path
            for path in WORK_DIR.rglob(pattern)
            if path.is_file()
            and "temporal_distribution" not in path.name
            and "validate_h1_temporal_distribution_outputs.py" not in path.name
        ]
        if matches:
            failures.append(
                "forbidden output pattern found: "
                + pattern
                + " -> "
                + ", ".join(str(path.relative_to(WORK_DIR)) for path in matches[:5])
            )

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("VALIDATION PASS")
    print(f"input_rows={input_rows}")
    print(f"results={len(REQUIRED_RESULTS)}")
    print(f"figures={len(REQUIRED_FIGURES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
