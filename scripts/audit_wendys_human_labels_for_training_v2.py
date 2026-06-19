#!/usr/bin/env python3
"""Audit Wendy's human labels for a training-label v2 candidate.

This script is intentionally read-only with respect to existing inputs. It
normalizes the current Fortune human-label template and Wendy's human-coded
label candidates into the fixed 0..4 schema:

  0 = non-humorous
  1 = aggressive
  2 = affiliative
  3 = self-enhancing
  4 = self-defeating

It writes only under:
  20260618expand/classifier_improvement/wendys_label_integration_audit/
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "20260618expand" / "classifier_improvement" / "wendys_label_integration_audit"

CURRENT_TRAINING = (
    ROOT
    / "20260618expand"
    / "classifier_improvement"
    / "data"
    / "human_labeling_template"
    / "fortune100_human_labeling_template_combined.csv"
)

WENDYS_SOURCES = [
    ROOT / "data" / "derived" / "humor" / "human_labels" / "wendys_human_label_raw_linked.csv",
    ROOT / "data" / "manual_labels" / "wendys_human_humor_labels.csv",
    ROOT / "20260615wendy's" / "data" / "wendys_partial_human_coded_humor_labels.csv",
    ROOT / "20260615wendy's" / "data" / "wendys_h2_coder1_priority_dataset.csv",
    ROOT / "20260615wendy's" / "data" / "wendys_h2_four_type_humor_dataset.csv",
    ROOT / "20260615wendy's" / "data" / "wendys_full_sample_four_type_humor_classifier_dataset.csv",
]

MODEL_PREDICTION_EXCLUSIONS = [
    ROOT / "20260615wendy's" / "data" / "wendys_h1_time_fe_only_dataset.csv",
    ROOT / "20260615wendy's" / "data" / "wendys_h2_full_sample_four_type_prediction_dataset.csv",
    ROOT / "20260615wendy's" / "result" / "wendys_full_sample_four_type_humor_predictions.csv",
    ROOT / "20260615wendy's" / "result" / "wendys_full_sample_four_type_humor_distribution.csv",
]

LABEL_NAMES = {
    "0": "non-humorous",
    "1": "aggressive",
    "2": "affiliative",
    "3": "self-enhancing",
    "4": "self-defeating",
}

TYPE_MAP = {
    "1": "1",
    "aggressive": "1",
    "2": "2",
    "affiliative": "2",
    "affiliated": "2",
    "affliative": "2",
    "self-affliative": "2",
    "3": "3",
    "self-enhancing": "3",
    "self_enhancing": "3",
    "self enhancing": "3",
    "self-enchancing": "3",
    "4": "4",
    "self-defeating": "4",
    "self_defeating": "4",
    "self defeating": "4",
}

NON_HUMOR_VALUES = {
    "0",
    "none",
    "non_humor",
    "non-humor",
    "nonhumor",
    "non humorous",
    "non-humorous",
    "no",
    "false",
    "비유머",
}

HUMOR_VALUES = {"1", "humor", "humorous", "yes", "true", "유머"}
EXCLUDE_VALUES = {"", "2", "uncertain", "ambiguous", "unknown", "pending", "needs_review", "nan", "애매함"}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def norm_text(text: str | None) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def text_hash(text: str | None) -> str:
    normalized = norm_text(text).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:20] if normalized else ""


def status_id_from_url(url: str | None) -> str:
    match = re.search(r"/status/(\d+)", url or "")
    return match.group(1) if match else ""


def digits_or_blank(value: str | None) -> str:
    value = (value or "").strip()
    if re.fullmatch(r"\d{6,}", value):
        return value
    return ""


def status_id_from_global(value: str | None) -> str:
    value = (value or "").strip()
    match = re.search(r":(\d{6,})$", value)
    return match.group(1) if match else digits_or_blank(value)


def key_values(row: dict[str, str]) -> dict[str, str]:
    status = (
        digits_or_blank(row.get("tweet_id"))
        or status_id_from_url(row.get("tweet_url"))
        or status_id_from_global(row.get("candidate_id"))
    )
    thash = text_hash(row.get("text"))
    keys = {
        "candidate_id": row.get("candidate_id", ""),
        "status_id": status,
        "tweet_url": (row.get("tweet_url") or "").strip().lower(),
        "text_hash": thash,
    }
    return keys


def primary_dedupe_key(row: dict[str, str]) -> str:
    keys = key_values(row)
    if keys["status_id"]:
        return f"status_id:{keys['status_id']}"
    if keys["tweet_url"]:
        return f"tweet_url:{keys['tweet_url']}"
    created = (row.get("created_at") or "").strip().lower()
    company = (row.get("company_name") or "").strip().lower()
    return f"text_hash:{keys['text_hash']}|created:{created}|company:{company}"


def add_to_key_index(index: dict[str, set[str]], row: dict[str, str]) -> None:
    keys = key_values(row)
    for name, value in keys.items():
        if value:
            index[name].add(value)


def duplicate_against_index(index: dict[str, set[str]], row: dict[str, str]) -> tuple[bool, str]:
    keys = key_values(row)
    for name in ("candidate_id", "status_id", "tweet_url", "text_hash"):
        value = keys.get(name, "")
        if value and value in index[name]:
            return True, f"{name}:{value}"
    return False, ""


def value(row: dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return str(row.get(name, ""))
    return ""


def map_presence_type(presence_raw: str, type_raw: str) -> tuple[str, str]:
    p = (presence_raw or "").strip().lower()
    t = (type_raw or "").strip().lower()
    if p in NON_HUMOR_VALUES:
        return "0", ""
    if p in EXCLUDE_VALUES:
        return "", "excluded_presence"
    if p in HUMOR_VALUES:
        label = TYPE_MAP.get(t)
        if label:
            return label, ""
        return "", "humor_missing_valid_type"
    if not p and TYPE_MAP.get(t):
        return TYPE_MAP[t], ""
    if p in TYPE_MAP:
        return TYPE_MAP[p], ""
    return "", "invalid_presence"


def normalize_current_training() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, set[str]]]:
    raw_rows = read_csv(CURRENT_TRAINING)
    valid: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    index: dict[str, set[str]] = defaultdict(set)

    for i, r in enumerate(raw_rows, start=2):
        candidate_id = value(r, ["candidate_id", "후보_ID"])
        text = norm_text(value(r, ["text", "본문"]))
        tweet_url = value(r, ["tweet_url", "트윗_URL"])
        tweet_id = value(r, ["tweet_id", "트윗_ID"])
        presence = value(r, ["human_humor_presence", "유머_존재여부"])
        htype = value(r, ["human_humor_type", "유머_유형"])
        label, reason = map_presence_type(presence, htype)
        base = {
            "row_id": "",
            "source": "current_training_labels",
            "original_file": rel(CURRENT_TRAINING),
            "company_name": value(r, ["company_name", "회사명"]),
            "candidate_id": candidate_id,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "created_at": value(r, ["created_at", "작성일시"]),
            "text": text,
            "normalized_label": label,
            "label_name": LABEL_NAMES.get(label, ""),
            "original_presence_value": presence,
            "original_type_value": htype,
            "label_source_detail": value(r, ["reviewer_id", "review_status"]) or f"template_row_{i}",
        }
        keys = key_values(base)
        base.update(keys)
        base["dedupe_key"] = primary_dedupe_key(base)
        if label:
            valid.append(base)
            add_to_key_index(index, base)
        else:
            base["exclusion_reason"] = reason or "not_valid_training_label"
            excluded.append(base)

    for i, r in enumerate(valid, start=1):
        r["row_id"] = f"current_training_{i:05d}"
    return valid, excluded, index


def normalize_wendys_source(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not path.exists():
        return [], [{
            "source_file": rel(path),
            "candidate_id": "",
            "brand": "Wendy's",
            "tweet_url": "",
            "status_id": "",
            "text_hash": "",
            "humor_presence": "",
            "humor_type": "",
            "normalized_label": "",
            "include_candidate": "false",
            "exclusion_reason": "source_file_not_found",
            "duplicate_with_existing": "false",
            "duplicate_key": "",
        }]

    rows = read_csv(path)
    candidates: list[dict[str, str]] = []
    audits: list[dict[str, str]] = []

    for i, r in enumerate(rows, start=2):
        source_file = rel(path)
        candidate_id = value(r, ["candidate_id", "global_post_id", "row_id", "no", "id"])
        tweet_id = value(r, ["tweet_id", "id"])
        tweet_url = value(r, ["tweet_url"])
        status_id = (
            digits_or_blank(tweet_id)
            or status_id_from_url(tweet_url)
            or status_id_from_global(candidate_id)
        )
        if not tweet_url and status_id:
            tweet_url = f"https://x.com/Wendys/status/{status_id}"
        text = norm_text(value(r, ["text", "human_text", "raw_text"]))
        created_at = value(r, ["created_at", "created_at_raw", "created_at_human", "date"])
        company = value(r, ["company_name"]) or "Wendy's"

        if path.name == "wendys_human_label_raw_linked.csv":
            presence = value(r, ["human_humor_binary", "human_humor_label_raw"])
            htype = value(r, ["human_humor_type_normalized", "human_humor_type_raw"])
            detail = value(r, ["human_label_source", "human_label_scope"]) or path.name
        elif path.name in {"wendys_human_humor_labels.csv", "wendys_partial_human_coded_humor_labels.csv"}:
            presence = value(r, ["humor"])
            htype = value(r, ["type"])
            detail = path.name
        elif path.name == "wendys_h2_coder1_priority_dataset.csv":
            presence = value(r, ["final_humor_binary"])
            htype = value(r, ["final_humor_type"])
            detail = value(r, ["final_humor_source", "final_humor_type_source"]) or path.name
            if value(r, ["final_humor_label_available"]).strip().lower() in {"0", "false"}:
                presence = ""
            if presence.strip() == "1" and value(r, ["final_humor_type_available"]).strip().lower() in {"0", "false"}:
                htype = ""
        elif path.name == "wendys_h2_four_type_humor_dataset.csv":
            presence = value(r, ["final_humor_binary"]) or "1"
            htype = value(r, ["final_humor_type"])
            detail = value(r, ["final_humor_type_source"]) or path.name
            if value(r, ["final_humor_label_available"]).strip().lower() in {"0", "false"}:
                presence = ""
        elif path.name == "wendys_full_sample_four_type_humor_classifier_dataset.csv":
            # Despite the filename, this 278-row dataset is documented in the
            # local audit as human-coded type labels. Model prediction-only
            # files are excluded separately below.
            presence = "1"
            htype = value(r, ["label"])
            detail = "human-coded four-type label file"
        else:
            presence = value(r, ["human_humor_presence", "humor", "final_humor_binary", "label"])
            htype = value(r, ["human_humor_type", "type", "final_humor_type", "humor_type"])
            detail = path.name

        label, reason = map_presence_type(presence, htype)
        base = {
            "source_file": source_file,
            "candidate_id": candidate_id,
            "brand": company,
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "status_id": status_id,
            "text_hash": text_hash(text),
            "humor_presence": presence,
            "humor_type": htype,
            "normalized_label": label,
            "include_candidate": "pending",
            "exclusion_reason": reason,
            "duplicate_with_existing": "pending",
            "duplicate_key": "",
            "_created_at": created_at,
            "_text": text,
            "_label_source_detail": detail,
            "_row_number": str(i),
        }
        if not text:
            base["exclusion_reason"] = "missing_text"
            label = ""
        audits.append(base.copy())
        if label:
            candidates.append({
                "row_id": "",
                "source": "wendys_human",
                "original_file": source_file,
                "company_name": company,
                "candidate_id": candidate_id,
                "tweet_id": status_id or tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "text": text,
                "normalized_label": label,
                "label_name": LABEL_NAMES[label],
                "original_presence_value": presence,
                "original_type_value": htype,
                "label_source_detail": detail,
                "status_id": status_id,
                "text_hash": text_hash(text),
                "dedupe_key": "",
                "_source_row_number": str(i),
            })
    return candidates, audits


def source_inventory() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in WENDYS_SOURCES:
        if not path.exists():
            rows.append({
                "source_file": rel(path),
                "file_type": path.suffix.lstrip("."),
                "raw_rows": 0,
                "detected_label_columns": "",
                "detected_text_columns": "",
                "detected_id_columns": "",
                "detected_date_columns": "",
                "usable_for_h1_h2_type_schema": "false",
                "reason_if_not_usable": "file_not_found",
            })
            continue
        raw = read_csv(path)
        cols = list(raw[0].keys()) if raw else []
        label_cols = [c for c in cols if any(s in c.lower() for s in ["humor", "type", "label", "final"])]
        text_cols = [c for c in cols if "text" in c.lower()]
        id_cols = [c for c in cols if c.lower() in {"id", "tweet_id", "tweet_url", "global_post_id", "candidate_id"}]
        date_cols = [c for c in cols if "date" in c.lower() or "created" in c.lower()]
        rows.append({
            "source_file": rel(path),
            "file_type": path.suffix.lstrip("."),
            "raw_rows": len(raw),
            "detected_label_columns": ";".join(label_cols),
            "detected_text_columns": ";".join(text_cols),
            "detected_id_columns": ";".join(id_cols),
            "detected_date_columns": ";".join(date_cols),
            "usable_for_h1_h2_type_schema": "true",
            "reason_if_not_usable": "",
        })
    for path in MODEL_PREDICTION_EXCLUSIONS:
        exists = path.exists()
        raw_rows = len(read_csv(path)) if exists and path.suffix.lower() == ".csv" else 0
        rows.append({
            "source_file": rel(path),
            "file_type": path.suffix.lstrip("."),
            "raw_rows": raw_rows,
            "detected_label_columns": "model_prediction_output",
            "detected_text_columns": "",
            "detected_id_columns": "",
            "detected_date_columns": "",
            "usable_for_h1_h2_type_schema": "false",
            "reason_if_not_usable": "model_prediction_only_not_human_label",
        })
    return rows


def dedupe_wendys(
    candidates: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    existing_index: dict[str, set[str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], Counter]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in candidates:
        r["dedupe_key"] = primary_dedupe_key(r)
        grouped[r["dedupe_key"]].append(r)

    preference = {
        "20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv": 0,
        "data/derived/humor/human_labels/wendys_human_label_raw_linked.csv": 1,
        "data/manual_labels/wendys_human_humor_labels.csv": 2,
        "20260615wendy's/data/wendys_partial_human_coded_humor_labels.csv": 3,
        "20260615wendy's/data/wendys_h2_four_type_humor_dataset.csv": 4,
        "20260615wendy's/data/wendys_full_sample_four_type_humor_classifier_dataset.csv": 5,
    }

    retained: list[dict[str, str]] = []
    duplicate_keys = set()
    conflict_keys = set()
    counters: Counter = Counter()

    for dkey, group in grouped.items():
        labels = {r["normalized_label"] for r in group}
        if len(labels) > 1:
            conflict_keys.add(dkey)
            counters["excluded_conflict_rows"] += len(group)
            continue
        group = sorted(group, key=lambda r: preference.get(r["original_file"], 99))
        winner = group[0]
        duplicate_keys.update((r["dedupe_key"] for r in group[1:]))
        counters["duplicate_rows_removed"] += max(len(group) - 1, 0)
        is_dup_existing, dup_key = duplicate_against_index(existing_index, winner)
        if is_dup_existing:
            counters["duplicate_with_existing_rows"] += 1
            winner["_duplicate_with_existing"] = "true"
            winner["_duplicate_key"] = dup_key
            continue
        winner["_duplicate_with_existing"] = "false"
        winner["_duplicate_key"] = ""
        retained.append(winner)

    retained_keys = {r["dedupe_key"] for r in retained}
    retained_row_ids = {(r["original_file"], r["_source_row_number"]) for r in retained}

    final_audit: list[dict[str, str]] = []
    for r in audit_rows:
        out = {k: r.get(k, "") for k in [
            "source_file", "candidate_id", "brand", "tweet_url", "status_id",
            "text_hash", "humor_presence", "humor_type", "normalized_label",
            "include_candidate", "exclusion_reason", "duplicate_with_existing",
            "duplicate_key",
        ]}
        if not out["normalized_label"]:
            out["include_candidate"] = "false"
            out["duplicate_with_existing"] = "false"
            if not out["exclusion_reason"]:
                out["exclusion_reason"] = "invalid_or_excluded_label"
        else:
            tmp = {
                "candidate_id": out["candidate_id"],
                "tweet_url": out["tweet_url"],
                "tweet_id": out["status_id"],
                "text": r.get("_text", ""),
                "created_at": r.get("_created_at", ""),
                "company_name": r.get("brand", "Wendy's"),
            }
            dkey = primary_dedupe_key(tmp)
            row_identity = (out["source_file"], r.get("_row_number", ""))
            dup_existing, dup_key = duplicate_against_index(existing_index, tmp)
            if dkey in conflict_keys:
                out["include_candidate"] = "false"
                out["exclusion_reason"] = "conflicting_duplicate_label"
                out["duplicate_with_existing"] = "false"
                out["duplicate_key"] = dkey
            elif dup_existing:
                out["include_candidate"] = "false"
                out["exclusion_reason"] = "duplicate_with_existing_training"
                out["duplicate_with_existing"] = "true"
                out["duplicate_key"] = dup_key
            elif row_identity in retained_row_ids and dkey in retained_keys:
                out["include_candidate"] = "true"
                out["exclusion_reason"] = ""
                out["duplicate_with_existing"] = "false"
                out["duplicate_key"] = ""
            else:
                out["include_candidate"] = "false"
                out["exclusion_reason"] = "duplicate_with_wendys_candidate"
                out["duplicate_with_existing"] = "false"
                out["duplicate_key"] = dkey
        final_audit.append(out)

    for r in retained:
        counters[f"new_label_{r['normalized_label']}"] += 1
    return retained, final_audit, counters


def distribution(rows: list[dict[str, str]], source_label: str) -> list[dict[str, object]]:
    c = Counter(r["normalized_label"] for r in rows)
    total = sum(c.values())
    out = []
    for label in ["0", "1", "2", "3", "4"]:
        n = c.get(label, 0)
        out.append({
            "dataset": source_label,
            "normalized_label": label,
            "label_name": LABEL_NAMES[label],
            "n": n,
            "class_share": round(n / total, 6) if total else 0,
            "total_n": total,
        })
    return out


def write_markdown(
    path: Path,
    *,
    current_raw_n: int,
    current_valid: list[dict[str, str]],
    current_excluded: list[dict[str, str]],
    inventory_rows: list[dict[str, object]],
    wendys_raw_count: int,
    wendys_valid_count: int,
    wendys_duplicates_existing: int,
    wendys_new: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    v2_rows: list[dict[str, str]],
) -> None:
    exclusion_counts = Counter(r["exclusion_reason"] or "included" for r in audit_rows)
    current_dist = Counter(r["normalized_label"] for r in current_valid)
    v2_dist = Counter(r["normalized_label"] for r in v2_rows)
    new_dist = Counter(r["normalized_label"] for r in wendys_new)

    lines = [
        "# Wendy's Label Integration Audit",
        "",
        "## Scope",
        "",
        "- Purpose: audit whether Wendy's human-coded labels are already reflected in the current 2,498-label training source and prepare a separate v2 training-label candidate.",
        "- This does not replace `simple_ols_baseline_main/` and does not rerun classifier training, full-corpus classification, or OLS.",
        "- Fixed label schema: 0=non-humorous, 1=aggressive, 2=affiliative, 3=self-enhancing, 4=self-defeating.",
        "",
        "## Current training labels",
        "",
        f"- Current training labels path: `{rel(CURRENT_TRAINING)}`",
        f"- Current raw rows: {current_raw_n:,}",
        f"- Current valid rows under 0..4 schema: {len(current_valid):,}",
        f"- Current excluded rows: {len(current_excluded):,}",
        "- Source interpretation: combined Fortune Top 100 batch1+batch2 coder template used by `simple_ols_baseline_main/run_simple_ols_baseline_main.py`.",
        "",
        "## Wendy's candidate sources",
        "",
        "| Source file | Raw rows | Usable | Reason if not usable |",
        "|:--|--:|:--|:--|",
    ]
    for row in inventory_rows:
        lines.append(
            f"| `{row['source_file']}` | {row['raw_rows']} | "
            f"{row['usable_for_h1_h2_type_schema']} | {row['reason_if_not_usable']} |"
        )
    lines += [
        "",
        "## Integration audit",
        "",
        f"- Wendy's candidate raw rows scanned: {wendys_raw_count:,}",
        f"- Wendy's valid human labels after schema normalization: {wendys_valid_count:,}",
        f"- Duplicate with existing current training labels: {wendys_duplicates_existing:,}",
        f"- New Wendy's labels addable to v2: {len(wendys_new):,}",
        f"- Final training-label v2 N: {len(v2_rows):,}",
        f"- Aggressive class increase: {new_dist.get('1', 0):,}",
        "",
        "### Wendy's exclusion counts",
        "",
        "| Reason | N |",
        "|:--|--:|",
    ]
    for reason, n in sorted(exclusion_counts.items()):
        lines.append(f"| {reason or 'included'} | {n:,} |")

    lines += [
        "",
        "## Class distribution change",
        "",
        "| Label | Name | Current valid N | Wendy's added N | v2 N |",
        "|:--|:--|--:|--:|--:|",
    ]
    for label in ["0", "1", "2", "3", "4"]:
        lines.append(
            f"| {label} | {LABEL_NAMES[label]} | {current_dist.get(label, 0):,} | "
            f"{new_dist.get(label, 0):,} | {v2_dist.get(label, 0):,} |"
        )
    lines += [
        "",
        "## Judgment",
        "",
        "- Wendy's human-coded labels are not already represented in the current Fortune combined training template by candidate/status/text keys.",
        "- A separate `training_labels_v2_with_wendys.csv` was generated as an integration candidate because valid human-coded Wendy's labels remain after deduplication.",
        "- Model-prediction-only Wendy's files are explicitly excluded and are not treated as human labels.",
        "",
        "## Next step boundary",
        "",
        "- v2 is a classifier retraining candidate only.",
        "- Retraining, full-corpus reclassification, and fixed simple OLS reruns require separate user approval.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    current_valid, current_excluded, current_index = normalize_current_training()
    current_raw_n = len(read_csv(CURRENT_TRAINING))

    inventory_rows = source_inventory()
    all_candidates: list[dict[str, str]] = []
    all_audit_rows: list[dict[str, str]] = []
    for source in WENDYS_SOURCES:
        candidates, audits = normalize_wendys_source(source)
        all_candidates.extend(candidates)
        all_audit_rows.extend(audits)

    wendys_new, final_audit_rows, counters = dedupe_wendys(all_candidates, all_audit_rows, current_index)
    wendys_valid_count = sum(1 for r in all_audit_rows if r.get("normalized_label"))
    wendys_duplicates_existing = sum(1 for r in final_audit_rows if r.get("duplicate_with_existing") == "true")

    v2_rows = []
    for i, r in enumerate(current_valid + wendys_new, start=1):
        out = dict(r)
        out["row_id"] = f"training_v2_{i:05d}"
        v2_rows.append(out)

    audit_fields = [
        "source_file", "candidate_id", "brand", "tweet_url", "status_id",
        "text_hash", "humor_presence", "humor_type", "normalized_label",
        "include_candidate", "exclusion_reason", "duplicate_with_existing",
        "duplicate_key",
    ]
    training_fields = [
        "row_id", "source", "original_file", "company_name", "candidate_id",
        "tweet_id", "tweet_url", "status_id", "created_at", "text",
        "text_hash", "normalized_label", "label_name",
        "original_presence_value", "original_type_value", "label_source_detail",
        "dedupe_key",
    ]
    dist_fields = ["dataset", "normalized_label", "label_name", "n", "class_share", "total_n"]
    inventory_fields = [
        "source_file", "file_type", "raw_rows", "detected_label_columns",
        "detected_text_columns", "detected_id_columns", "detected_date_columns",
        "usable_for_h1_h2_type_schema", "reason_if_not_usable",
    ]

    write_csv(OUT / "wendys_label_source_inventory.csv", inventory_rows, inventory_fields)
    write_csv(OUT / "wendys_label_integration_audit.csv", final_audit_rows, audit_fields)
    write_csv(OUT / "training_labels_v2_with_wendys.csv", v2_rows, training_fields)
    dist_rows = (
        distribution(current_valid, "current_training_valid")
        + distribution(wendys_new, "wendys_new_additions")
        + distribution(v2_rows, "training_labels_v2_with_wendys")
    )
    write_csv(OUT / "training_labels_v2_distribution.csv", dist_rows, dist_fields)
    write_markdown(
        OUT / "wendys_label_integration_audit.md",
        current_raw_n=current_raw_n,
        current_valid=current_valid,
        current_excluded=current_excluded,
        inventory_rows=inventory_rows,
        wendys_raw_count=len(all_audit_rows),
        wendys_valid_count=wendys_valid_count,
        wendys_duplicates_existing=wendys_duplicates_existing,
        wendys_new=wendys_new,
        audit_rows=final_audit_rows,
        v2_rows=v2_rows,
    )
    (OUT / "README.md").write_text(
        "\n".join([
            "# Wendy's Label Integration Audit",
            "",
            "This folder audits whether legacy Wendy's human-coded labels can be added to the current Fortune combined training labels.",
            "",
            "Generated files:",
            "",
            "- `wendys_label_source_inventory.csv`: source-level inventory.",
            "- `wendys_label_integration_audit.csv`: row-level Wendy's inclusion audit.",
            "- `training_labels_v2_with_wendys.csv`: candidate v2 training labels, separate from existing baseline outputs.",
            "- `training_labels_v2_distribution.csv`: current vs v2 distribution comparison.",
            "- `wendys_label_integration_audit.md`: concise audit memo.",
            "",
            "Boundary: this is not classifier retraining, full-corpus reclassification, or a replacement for `simple_ols_baseline_main/`.",
        ]) + "\n",
        encoding="utf-8",
    )

    print("Wendy's label integration audit complete")
    print(f"current_training_raw_rows={current_raw_n}")
    print(f"current_training_valid_rows={len(current_valid)}")
    print(f"wendys_candidate_rows={len(all_audit_rows)}")
    print(f"wendys_valid_human_label_rows={wendys_valid_count}")
    print(f"duplicate_with_existing_training_rows={wendys_duplicates_existing}")
    print(f"new_wendys_rows_addable={len(wendys_new)}")
    print(f"training_labels_v2_rows={len(v2_rows)}")
    print(f"aggressive_class_increase={Counter(r['normalized_label'] for r in wendys_new).get('1', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
