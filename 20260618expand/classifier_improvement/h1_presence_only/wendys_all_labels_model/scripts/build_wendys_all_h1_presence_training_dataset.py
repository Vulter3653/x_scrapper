"""Build H1 presence training data with all usable Wendy's human labels.

Creates Wendy's label-source inventory, merged raw/valid Wendy's labels, and an
expanded batch1 + all-Wendy's H1 binary training dataset. It does not modify raw
sources and does not train any classifier.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
H1 = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only"
INTEGRATION = H1 / "wendys_all_labels_integration"
MODEL = H1 / "wendys_all_labels_model"
INT_DATA = INTEGRATION / "data"
INT_DIAG = INTEGRATION / "diagnostics"
MODEL_DATA = MODEL / "data"
MODEL_DIAG = MODEL / "diagnostics"
EXPANDED_PREV = H1 / "expanded_h1_presence_training" / "data" / "expanded_h1_presence_training_dataset.csv"

OUT_INVENTORY = INT_DIAG / "wendys_label_source_inventory.csv"
OUT_RAW = INT_DATA / "wendys_all_h1_presence_labels_raw_merged.csv"
OUT_VALID = INT_DATA / "wendys_all_h1_presence_labels_valid.csv"
OUT_EXPANDED = INT_DATA / "expanded_h1_presence_training_with_all_wendys.csv"
OUT_DIAG = INT_DIAG / "wendys_all_label_diagnostics.csv"
OUT_DUP = INT_DIAG / "wendys_duplicate_diagnostics.csv"
OUT_CONFLICT = INT_DIAG / "wendys_conflicting_label_diagnostics.csv"
OUT_MISSING_TEXT = INT_DIAG / "wendys_missing_text_diagnostics.csv"
OUT_SOURCE_BREAKDOWN = INT_DIAG / "wendys_source_breakdown.csv"

# Mirror files required in model diagnostics.
MODEL_INVENTORY = MODEL_DIAG / "wendys_all_source_inventory.csv"
MODEL_SUMMARY = MODEL_DIAG / "wendys_label_integration_summary.csv"
MODEL_DUP = MODEL_DIAG / "wendys_duplicate_diagnostics.csv"
MODEL_CONFLICT = MODEL_DIAG / "wendys_conflicting_label_diagnostics.csv"

LABEL_COLS = [
    "human_humor_binary", "final_humor_binary", "humor_presence_binary",
    "human_humor_label", "human_humor_label_raw", "human_humor", "humor",
    "유머_존재여부",
]
TEXT_COLS = ["text", "raw_text", "human_text", "본문", "clean_text", "text_preprocessed"]
ID_COLS = ["tweet_id", "id", "global_post_id", "트윗_ID"]
URL_COLS = ["tweet_url", "트윗_URL", "url"]
DATE_COLS = ["created_at", "created_at_raw", "created_at_human", "date", "작성일시"]

INVENTORY_FIELDS = [
    "source_file", "file_type", "raw_rows", "detected_label_columns",
    "detected_text_columns", "detected_id_columns", "detected_date_columns",
    "usable_for_h1_presence", "reason_if_not_usable",
]
RAW_FIELDS = [
    "source_file", "source_row_number", "company_name", "tweet_id", "tweet_url",
    "created_at", "text", "humor_presence_binary", "original_presence_value",
    "label_source_detail", "dedupe_key", "usable_row", "exclude_reason",
]
VALID_FIELDS = [
    "row_id", "source", "original_file", "company_name", "tweet_id", "tweet_url",
    "created_at", "text", "humor_presence_binary", "original_presence_value",
    "label_source_detail", "dedupe_key",
]
EXPANDED_FIELDS = [
    "row_id", "source", "original_file", "company_name", "tweet_id", "tweet_url",
    "created_at", "text", "humor_presence_binary", "original_presence_value",
    "label_source_detail",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def norm_key(text: str) -> str:
    return hashlib.sha1(norm(text).lower().encode("utf-8")).hexdigest()[:16]


def status_id_from_url(url: str) -> str:
    match = re.search(r"/status/(\d+)", url or "")
    return match.group(1) if match else ""


def first_value(row: dict[str, str], cols: list[str]) -> str:
    for col in cols:
        val = row.get(col)
        if val not in (None, ""):
            return str(val).strip()
    return ""


def map_label(row: dict[str, str], fields: list[str]) -> tuple[str | None, str, str]:
    for col in LABEL_COLS:
        if col not in fields:
            continue
        raw = str(row.get(col, "")).strip()
        if raw == "":
            continue
        low = raw.lower().replace("‐", "-").replace("–", "-").replace("—", "-")
        if low in {"1", "true", "yes", "y", "humor", "humorous", "funny", "유머"}:
            return "1", raw, col
        if low in {"0", "false", "no", "n", "none", "non_humor", "non-humor", "nonhumor", "not_humor", "비유머"}:
            return "0", raw, col
        if low in {"2", "uncertain", "ambiguous", "unknown", "애매함", "모름"}:
            return None, raw, col
    return None, "", ""


def is_wendys_candidate(path: Path) -> bool:
    s = path.as_posix().lower()
    if "/venv/" in s or "/dashboard/" in s or "/.git/" in s:
        return False
    if not path.suffix.lower() in {".csv", ".json", ".jsonl", ".xlsx"}:
        return False
    return "wendy" in s or "human_label" in s or "human_humor" in s or "humor_presence" in s


def discover_files() -> list[Path]:
    roots = [ROOT / "data", ROOT / "20260615wendy's", ROOT / "20260618expand"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and is_wendys_candidate(path):
                files.append(path)
    return sorted(set(files))


def inventory_and_extract() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    inventory: list[dict[str, object]] = []
    raw_rows: list[dict[str, object]] = []
    text_lookup = build_wendys_text_lookup()
    for path in discover_files():
        rel = path.relative_to(ROOT).as_posix()
        suffix = path.suffix.lower().lstrip(".")
        fields: list[str] = []
        rows: list[dict[str, str]] = []
        reason = ""
        usable = False
        try:
            if suffix == "csv":
                fields, rows = read_csv(path)
            elif suffix in {"json", "jsonl"}:
                fields, rows = read_json_like(path)
            else:
                reason = "unsupported xlsx for local parser"
        except Exception as exc:
            reason = f"read_error: {exc}"
        label_cols = [c for c in fields if c in LABEL_COLS]
        text_cols = [c for c in fields if c in TEXT_COLS]
        id_cols = [c for c in fields if c in ID_COLS or c in URL_COLS]
        date_cols = [c for c in fields if c in DATE_COLS]
        if not reason:
            if not label_cols:
                reason = "no explicit H1 presence label column"
            elif not text_cols and not id_cols:
                reason = "no text or stable id column"
            elif is_model_prediction_only(rel, fields):
                reason = "model prediction or aggregate output, not direct human/final label source"
            else:
                usable = True
                reason = ""
        inventory.append({
            "source_file": rel,
            "file_type": suffix,
            "raw_rows": len(rows),
            "detected_label_columns": ";".join(label_cols),
            "detected_text_columns": ";".join(text_cols),
            "detected_id_columns": ";".join(id_cols),
            "detected_date_columns": ";".join(date_cols),
            "usable_for_h1_presence": "yes" if usable else "no",
            "reason_if_not_usable": reason,
        })
        if not usable:
            continue
        for idx, row in enumerate(rows, start=2):
            label, original, label_col = map_label(row, fields)
            company = first_value(row, ["company_name", "회사명"]) or "Wendy's"
            tweet_url = first_value(row, URL_COLS)
            tweet_id = first_value(row, ["tweet_id", "id", "트윗_ID"])
            if tweet_id.startswith("benchmark:wendys:"):
                tweet_id = tweet_id.rsplit(":", 1)[-1]
            if not tweet_id:
                tweet_id = status_id_from_url(tweet_url)
            if not tweet_url and tweet_id and tweet_id.isdigit():
                tweet_url = f"https://x.com/Wendys/status/{tweet_id}"
            created_at = first_value(row, DATE_COLS)
            text = norm(first_value(row, TEXT_COLS))
            if not text:
                text = text_lookup.get(tweet_id, {}).get("text", "") or text_lookup.get(status_id_from_url(tweet_url), {}).get("text", "")
            if not created_at:
                created_at = text_lookup.get(tweet_id, {}).get("created_at", "") or text_lookup.get(status_id_from_url(tweet_url), {}).get("created_at", "")
            key = dedupe_key(tweet_id, tweet_url, company, text, created_at)
            exclude = ""
            if label is None:
                exclude = "missing_or_uncertain_label"
            elif not text:
                exclude = "missing_text"
            raw_rows.append({
                "source_file": rel,
                "source_row_number": idx,
                "company_name": company,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "text": text,
                "humor_presence_binary": label or "",
                "original_presence_value": original,
                "label_source_detail": label_col or source_detail(row, rel),
                "dedupe_key": key,
                "usable_row": "yes" if not exclude else "no",
                "exclude_reason": exclude,
            })
    return inventory, raw_rows


def read_json_like(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append({k: str(v) if v is not None else "" for k, v in obj.items()})
    else:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            rows = [{k: str(v) if v is not None else "" for k, v in item.items()} for item in obj if isinstance(item, dict)]
        elif isinstance(obj, dict):
            for key in ["posts", "data", "rows", "results"]:
                if isinstance(obj.get(key), list):
                    rows = [{k: str(v) if v is not None else "" for k, v in item.items()} for item in obj[key] if isinstance(item, dict)]
                    break
    fields = sorted({k for row in rows for k in row})
    return fields, rows


def is_model_prediction_only(rel: str, fields: list[str]) -> bool:
    lower = rel.lower()
    label_set = set(fields)
    if "final_humor_binary" in label_set:
        return False
    if "human_humor_binary" in label_set or "human_humor_label" in label_set or "human_humor_label_raw" in label_set:
        return False
    if rel in {
        "data/manual_labels/wendys_human_humor_labels.csv",
        "20260615wendy's/data/wendys_partial_human_coded_humor_labels.csv",
    }:
        return False
    if "prediction" in lower or "classifier" in lower or "oof" in lower or "diagnostic" in lower or "distribution" in lower:
        return True
    return False


def source_detail(row: dict[str, str], rel: str) -> str:
    return first_value(row, ["final_humor_source", "human_label_source", "label_source", "source"]) or rel


def dedupe_key(tweet_id: str, tweet_url: str, company: str, text: str, created_at: str) -> str:
    if tweet_id:
        return "tweet_id:" + tweet_id
    sid = status_id_from_url(tweet_url)
    if sid:
        return "tweet_id:" + sid
    return "text_date:" + norm(company).lower() + ":" + norm(created_at).lower() + ":" + norm_key(text)


def build_wendys_text_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    candidates = [ROOT / "data" / "wendys" / "posts.json", ROOT / "20260615wendy's" / "data" / "wendys_posts_raw.json"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            _, rows = read_json_like(path)
        except Exception:
            continue
        for row in rows:
            tid = first_value(row, ["tweet_id", "id", "rest_id"])
            url = first_value(row, ["tweet_url", "url"])
            if not tid:
                tid = status_id_from_url(url)
            text = norm(first_value(row, ["text", "full_text", "raw_text"]))
            created = first_value(row, ["created_at", "date"])
            if tid and text:
                lookup[tid] = {"text": text, "created_at": created}
    return lookup


def dedupe_valid(raw_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    usable = [r for r in raw_rows if r["usable_row"] == "yes"]
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in usable:
        grouped[str(row["dedupe_key"])].append(row)
    valid: list[dict[str, object]] = []
    duplicates: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for key, group in grouped.items():
        labels = sorted({str(r["humor_presence_binary"]) for r in group})
        if len(labels) > 1:
            for r in group:
                conflicts.append({**r, "conflict_key": key, "conflicting_labels": ";".join(labels)})
            continue
        priority = sorted(group, key=lambda r: source_priority(str(r["source_file"])))
        keep = priority[0]
        valid.append(keep)
        for dup in priority[1:]:
            duplicates.append({**dup, "duplicate_of_source_file": keep["source_file"], "duplicate_key": key})
    valid.sort(key=lambda r: (source_priority(str(r["source_file"])), str(r["dedupe_key"])))
    return valid, duplicates, conflicts, [r for r in raw_rows if r["exclude_reason"] == "missing_text"]


def source_priority(source_file: str) -> tuple[int, str]:
    preferred = [
        "20260615wendy's/data/wendys_final_humor_presence_dataset.csv",
        "20260615wendy's/result/wendys_final_humor_presence_full_predictions.csv",
        "data/derived/humor/human_labels/wendys_human_label_raw_linked.csv",
        "data/manual_labels/wendys_human_humor_labels.csv",
        "20260615wendy's/data/wendys_partial_human_coded_humor_labels.csv",
    ]
    return (preferred.index(source_file) if source_file in preferred else 99, source_file)


def build_expanded(valid_wendys: list[dict[str, object]]) -> list[dict[str, object]]:
    _, rows = read_csv(EXPANDED_PREV)
    batch1 = [r for r in rows if r.get("source") == "batch1_fortune100"]
    output: list[dict[str, object]] = []
    for row in batch1:
        output.append({field: row.get(field, "") for field in EXPANDED_FIELDS})
    for row in valid_wendys:
        output.append({
            "row_id": "",
            "source": "wendys_all_human",
            "original_file": row["source_file"],
            "company_name": row["company_name"],
            "tweet_id": row["tweet_id"],
            "tweet_url": row["tweet_url"],
            "created_at": row["created_at"],
            "text": row["text"],
            "humor_presence_binary": row["humor_presence_binary"],
            "original_presence_value": row["original_presence_value"],
            "label_source_detail": row["label_source_detail"],
        })
    for idx, row in enumerate(output, start=1):
        row["row_id"] = f"wendys_all_h1_{idx:05d}"
    return output


def summary_rows(raw_rows, valid, duplicates, conflicts) -> list[dict[str, object]]:
    c_raw = Counter(str(r["exclude_reason"]) or "raw_binary_candidate" for r in raw_rows)
    c_valid = Counter(str(r["humor_presence_binary"]) for r in valid)
    return [
        {"metric": "raw_wendys_label_rows", "value": len(raw_rows)},
        {"metric": "raw_usable_binary_or_excludable_rows", "value": len(raw_rows)},
        {"metric": "valid_wendys_h1_rows", "value": len(valid)},
        {"metric": "valid_humor_rows", "value": c_valid.get("1", 0)},
        {"metric": "valid_non_humor_rows", "value": c_valid.get("0", 0)},
        {"metric": "excluded_uncertain_or_missing_label_rows", "value": c_raw.get("missing_or_uncertain_label", 0)},
        {"metric": "excluded_missing_text_rows", "value": c_raw.get("missing_text", 0)},
        {"metric": "excluded_conflict_rows", "value": len(conflicts)},
        {"metric": "duplicate_rows_removed", "value": len(duplicates)},
        {"metric": "final_wendys_rows_used", "value": len(valid)},
    ]


def source_breakdown(raw_rows, valid, duplicates, conflicts) -> list[dict[str, object]]:
    sources = sorted({str(r["source_file"]) for r in raw_rows})
    valid_c = Counter(str(r["source_file"]) for r in valid)
    dup_c = Counter(str(r["source_file"]) for r in duplicates)
    conf_c = Counter(str(r["source_file"]) for r in conflicts)
    raw_c = Counter(str(r["source_file"]) for r in raw_rows)
    excl_c = Counter(str(r["source_file"]) for r in raw_rows if r["usable_row"] != "yes")
    return [{
        "source_file": s,
        "raw_rows": raw_c[s],
        "final_rows": valid_c[s],
        "duplicate_rows_removed": dup_c[s],
        "conflict_rows_excluded": conf_c[s],
        "missing_or_uncertain_rows_excluded": excl_c[s],
    } for s in sources]


def main() -> int:
    for d in [INT_DATA, INT_DIAG, MODEL_DATA, MODEL_DIAG]:
        d.mkdir(parents=True, exist_ok=True)
    inventory, raw_rows = inventory_and_extract()
    valid, duplicates, conflicts, missing_text = dedupe_valid(raw_rows)
    valid_rows = []
    for idx, row in enumerate(valid, start=1):
        valid_rows.append({
            "row_id": f"wendys_all_{idx:05d}",
            "source": "wendys_all_human",
            "original_file": row["source_file"],
            "company_name": row["company_name"],
            "tweet_id": row["tweet_id"],
            "tweet_url": row["tweet_url"],
            "created_at": row["created_at"],
            "text": row["text"],
            "humor_presence_binary": row["humor_presence_binary"],
            "original_presence_value": row["original_presence_value"],
            "label_source_detail": row["label_source_detail"],
            "dedupe_key": row["dedupe_key"],
        })
    expanded = build_expanded(valid)

    write_csv(OUT_INVENTORY, inventory, INVENTORY_FIELDS)
    write_csv(OUT_RAW, raw_rows, RAW_FIELDS)
    write_csv(OUT_VALID, valid_rows, VALID_FIELDS)
    write_csv(OUT_EXPANDED, expanded, EXPANDED_FIELDS)
    write_csv(OUT_DIAG, summary_rows(raw_rows, valid, duplicates, conflicts), ["metric", "value"])
    write_csv(OUT_DUP, duplicates, list(duplicates[0].keys()) if duplicates else RAW_FIELDS + ["duplicate_of_source_file", "duplicate_key"])
    write_csv(OUT_CONFLICT, conflicts, list(conflicts[0].keys()) if conflicts else RAW_FIELDS + ["conflict_key", "conflicting_labels"])
    write_csv(OUT_MISSING_TEXT, missing_text, RAW_FIELDS)
    write_csv(OUT_SOURCE_BREAKDOWN, source_breakdown(raw_rows, valid, duplicates, conflicts), ["source_file", "raw_rows", "final_rows", "duplicate_rows_removed", "conflict_rows_excluded", "missing_or_uncertain_rows_excluded"])
    write_csv(MODEL_INVENTORY, inventory, INVENTORY_FIELDS)
    write_csv(MODEL_SUMMARY, summary_rows(raw_rows, valid, duplicates, conflicts), ["metric", "value"])
    write_csv(MODEL_DUP, duplicates, list(duplicates[0].keys()) if duplicates else RAW_FIELDS + ["duplicate_of_source_file", "duplicate_key"])
    write_csv(MODEL_CONFLICT, conflicts, list(conflicts[0].keys()) if conflicts else RAW_FIELDS + ["conflict_key", "conflicting_labels"])
    print("Built Wendy's all-label H1 training data")
    print(f"raw_wendys_label_rows={len(raw_rows)}")
    print(f"valid_wendys_h1_rows={len(valid)}")
    print(f"expanded_rows={len(expanded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
