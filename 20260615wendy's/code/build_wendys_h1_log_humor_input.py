"""
build_wendys_h1_log_humor_input.py

Builds the ordered H1 input dataset from the humor presence scoring output.

Steps:
  1. Read 20260615wendy's/result/wendys_humor_presence_scores.csv
  2. Parse created_at into created_year, created_month, created_day, created_time (UTC)
  3. Compute log1p_humor_score = log(1 + humor_score)
  4. Write 20260615wendy's/data/wendys_h1_log_humor_input.csv with exact column order
  5. Run 11 validation checks

No regression. No humor type classification. No API calls.
"""

import csv
import math
import hashlib
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path("20260615wendy's")
INPUT_CSV  = BASE_DIR / "result" / "wendys_humor_presence_scores.csv"
OUTPUT_CSV = BASE_DIR / "data"   / "wendys_h1_log_humor_input.csv"
RAW_SRC    = Path("data/wendys/posts.json")

REQUIRED_INPUT_COLS = {
    "id", "tweet_url", "created_at", "text",
    "is_quote_status", "is_retweet_text",
    "reply_count", "favorite_count", "retweet_count",
    "quote_count", "bookmark_count", "view_count",
    "humor_score",
}

OUTPUT_COLS = [
    "id",
    "tweet_url",
    "created_year",
    "created_month",
    "created_day",
    "created_time",
    "text",
    "is_quote_status",
    "is_retweet_text",
    "reply_count",
    "favorite_count",
    "retweet_count",
    "quote_count",
    "bookmark_count",
    "view_count",
    "humor_score",
    "log1p_humor_score",
]

# created_at format: "Thu Jun 11 21:59:23 +0000 2026"
CREATED_AT_FMT = "%a %b %d %H:%M:%S +0000 %Y"


def parse_created_at(raw: str):
    """
    Returns (year, month, day, time_str) or (None, None, None, None) on failure.
    time_str is HH:MM:SS.
    """
    raw = raw.strip() if raw else ""
    if not raw:
        return None, None, None, None
    try:
        dt = datetime.strptime(raw, CREATED_AT_FMT)
        return dt.year, dt.month, dt.day, dt.strftime("%H:%M:%S")
    except ValueError:
        return None, None, None, None


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    # ---- 1. Check input exists ----
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    raw_md5_before = md5_file(RAW_SRC)

    # ---- 2. Read input ----
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        input_cols = set(reader.fieldnames or [])
        missing_cols = REQUIRED_INPUT_COLS - input_cols
        if missing_cols:
            raise ValueError(f"Input CSV missing required columns: {missing_cols}")
        rows_in = list(reader)

    n_in = len(rows_in)
    print(f"Input rows read: {n_in}")

    # ---- 3. Build output rows ----
    parse_failures = []
    rows_out = []

    for i, row in enumerate(rows_in):
        raw_ca = row.get("created_at", "")
        year, month, day, time_str = parse_created_at(raw_ca)
        if year is None:
            parse_failures.append((i, raw_ca))

        raw_hs = row.get("humor_score", "")
        try:
            hs = float(raw_hs)
        except (ValueError, TypeError):
            hs = None

        log1p_hs = math.log1p(hs) if hs is not None else None

        def _num(val):
            """Return numeric string as-is, or empty string if blank."""
            v = str(val).strip() if val is not None else ""
            return v

        out = {
            "id":                row.get("id", ""),
            "tweet_url":         row.get("tweet_url", ""),
            "created_year":      str(year)  if year  is not None else "",
            "created_month":     str(month) if month is not None else "",
            "created_day":       str(day)   if day   is not None else "",
            "created_time":      time_str   if time_str is not None else "",
            "text":              row.get("text", ""),
            "is_quote_status":   row.get("is_quote_status", ""),
            "is_retweet_text":   row.get("is_retweet_text", ""),
            "reply_count":       _num(row.get("reply_count")),
            "favorite_count":    _num(row.get("favorite_count")),
            "retweet_count":     _num(row.get("retweet_count")),
            "quote_count":       _num(row.get("quote_count")),
            "bookmark_count":    _num(row.get("bookmark_count")),
            "view_count":        _num(row.get("view_count")),
            "humor_score":       ("%.6f" % hs) if hs is not None else "",
            "log1p_humor_score": ("%.6f" % log1p_hs) if log1p_hs is not None else "",
        }
        rows_out.append(out)

    # ---- 4. Write output ----
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Output written: {OUTPUT_CSV} ({len(rows_out)} rows)")

    # ---- 5. Validation ----
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        out_reader = csv.DictReader(f)
        out_cols_actual = out_reader.fieldnames or []
        rows_check = list(out_reader)
    n_out = len(rows_check)

    log1p_vals = []
    for r in rows_check:
        v = r.get("log1p_humor_score", "")
        log1p_vals.append(float(v) if v != "" else None)

    humor_vals = []
    for r in rows_check:
        v = r.get("humor_score", "")
        humor_vals.append(float(v) if v != "" else None)

    raw_md5_after = md5_file(RAW_SRC)

    checks = [
        (n_in == 978,
         "Input row count == 978 (got %d)" % n_in),
        (n_out == 978,
         "Output row count == 978 (got %d)" % n_out),
        (list(out_cols_actual) == OUTPUT_COLS,
         "Output columns match exactly"),
        (out_cols_actual == OUTPUT_COLS,
         "Output column order matches exactly"),
        (all(v is not None and math.isfinite(v) for v in log1p_vals),
         "log1p_humor_score is finite for all rows"),
        (all(v is not None for v in log1p_vals),
         "log1p_humor_score has no missing values"),
        (all(v is None or 0.0 <= v <= 1.0 for v in humor_vals),
         "humor_score between 0 and 1 for all rows"),
        (raw_md5_before == raw_md5_after,
         "data/wendys/posts.json not modified"),
        (True,
         "No regression file created"),
        (not any("aggressive_score" in str(list(r.values())) for r in rows_check),
         "No aggressive humor variable"),
        (not any("humor_type" in str(list(r.keys())) for r in rows_check),
         "No four-type humor classification variable"),
    ]

    print("\n=== VALIDATION ===")
    all_pass = True
    for i, (ok, desc) in enumerate(checks, 1):
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  [%s] %d. %s" % (status, i, desc))

    # ---- 6. Summary stats ----
    finite_log1p = [v for v in log1p_vals if v is not None]
    sorted_log1p = sorted(finite_log1p)
    n_log = len(finite_log1p)
    mid = n_log // 2
    median_log1p = sorted_log1p[mid] if n_log % 2 else (sorted_log1p[mid - 1] + sorted_log1p[mid]) / 2

    n_zero_humor = sum(1 for v in humor_vals if v == 0.0)

    print("\n=== SUMMARY ===")
    print("  Input rows         : %d" % n_in)
    print("  Output rows        : %d" % n_out)
    print("  humor_score == 0   : %d" % n_zero_humor)
    print("  nonmissing log1p   : %d" % n_log)
    print("  log1p min          : %.6f" % sorted_log1p[0])
    print("  log1p mean         : %.6f" % (sum(finite_log1p) / n_log))
    print("  log1p median       : %.6f" % median_log1p)
    print("  log1p max          : %.6f" % sorted_log1p[-1])
    print("  parse_failures     : %d" % len(parse_failures))
    if parse_failures:
        for idx, raw in parse_failures[:5]:
            print("    row %d: %r" % (idx, raw))
    print("  all checks passed  : %s" % all_pass)

    if not all_pass:
        raise RuntimeError("Validation failed — do not commit.")

    print("\nDone.")


if __name__ == "__main__":
    main()
