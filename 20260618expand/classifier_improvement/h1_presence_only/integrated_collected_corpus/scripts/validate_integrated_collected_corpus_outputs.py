"""Validate integrated collected corpus H1 outputs."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "integrated_collected_corpus"
DATA = BASE / "data"
RESULTS = BASE / "results"
FIGURES = BASE / "figures"

REQUIRED_DATA = [
    "integrated_collected_post_corpus.csv",
    "integrated_h1_presence_classified_posts.csv",
    "integrated_corpus_source_diagnostics.csv",
    "append_workflow_reflection.csv",
    "integrated_h1_presence_classification_summary.csv",
    "integrated_h1_presence_by_source_summary.csv",
    "integrated_h1_presence_by_firm_summary.csv",
]
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
FORBIDDEN_COLUMNS = ["humor_type", "aggressive_humor", "aggressive_detector", "h2", "h3"]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fail_if_range(failures: list[str], items: list[dict[str, str]], column: str, low: int, high: int) -> None:
    for row in items:
        if row.get(column, "") == "":
            continue
        value = int(row[column])
        if value < low or value > high:
            failures.append(f"{column} outside {low}-{high}: {value}")
            return


def main() -> int:
    failures: list[str] = []
    for name in REQUIRED_DATA:
        if not (DATA / name).exists():
            failures.append(f"missing data file: {name}")
    for name in REQUIRED_RESULTS:
        if not (RESULTS / name).exists():
            failures.append(f"missing result file: {name}")
    for name in REQUIRED_FIGURES:
        path = FIGURES / name
        if not path.exists():
            failures.append(f"missing figure: {name}")
        elif path.stat().st_size == 0:
            failures.append(f"empty figure: {name}")

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    corpus = rows(DATA / "integrated_collected_post_corpus.csv")
    classified = rows(DATA / "integrated_h1_presence_classified_posts.csv")
    diagnostics = rows(DATA / "integrated_corpus_source_diagnostics.csv")
    reflection = rows(DATA / "append_workflow_reflection.csv")[0]

    if len(corpus) != len(classified):
        failures.append("classified row count != integrated corpus row count")
    sources = {row["source_dataset"] for row in corpus}
    if len(sources) < 2:
        failures.append("fewer than 2 source datasets")
    for required in ["fortune100", "fortune100_raw_append", "wendys_legacy", "cocacola_legacy", "moonpie_legacy"]:
        if required not in {row["source_dataset"] for row in diagnostics}:
            failures.append(f"source missing from diagnostics: {required}")
    for key in ["workflow_file_found", "audit_summary_found", "fortune_x_2025_ranked_included", "wendys_posts_included", "cocacola_posts_included", "moonpie_posts_included", "reflected_in_integrated_corpus"]:
        if reflection.get(key) != "yes":
            failures.append(f"append reflection not yes: {key}={reflection.get(key)}")

    if "missing_text" not in (classified[0].keys() if classified else []):
        failures.append("missing_text column missing")
    for row in classified:
        prob = row.get("h1_humor_presence_probability", "")
        if prob:
            value = float(prob)
            if value < 0 or value > 1:
                failures.append("probability outside 0-1")
                break
        for col in ["h1_humor_presence_pred_t40", "h1_humor_presence_pred_t50", "h1_humor_presence_pred_t60"]:
            if row.get(col) not in {"0", "1", ""}:
                failures.append(f"{col} outside 0/1/blank")
                break

    cols = {c.lower() for c in classified[0].keys()} if classified else set()
    for forbidden in FORBIDDEN_COLUMNS:
        if any(forbidden in col for col in cols):
            failures.append(f"forbidden type/aggressive/H2/H3 column found: {forbidden}")

    fail_if_range(failures, classified, "hour_of_day", 0, 23)
    fail_if_range(failures, classified, "month_of_year", 1, 12)
    fail_if_range(failures, classified, "day_of_month", 1, 31)

    for forbidden_dir in [
        BASE / "h1_regression",
        BASE / "h2",
        BASE / "h3",
        BASE / "type_classifier",
        BASE / "aggressive_detector",
    ]:
        if forbidden_dir.exists():
            failures.append(f"forbidden output directory exists: {forbidden_dir.relative_to(BASE)}")

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("VALIDATION PASS")
    print(f"integrated_rows={len(corpus)}")
    print(f"source_datasets={len(sources)}")
    print(f"append_summary_rows={reflection.get('audit_summary_rows')}")
    print(f"append_new_unique_posts_total={reflection.get('new_unique_posts_total')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
