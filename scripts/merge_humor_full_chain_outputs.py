#!/usr/bin/env python3
"""Merge humor presence, humor type, and sentiment outputs into one master dataset."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def index_by_id(rows, name):
    out = {}
    duplicates = 0
    for row in rows:
        gid = row.get("global_post_id", "")
        if not gid:
            continue
        if gid in out:
            duplicates += 1
        out[gid] = row
    return out, duplicates


def rate(num, denom):
    return round(num / denom, 6) if denom else 0.0


def write_metric_csv(path, summary):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in summary.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])


def write_company_summary(path, master_rows):
    companies = sorted(set(r.get("company_name", "") for r in master_rows))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "company_name", "row_count", "humor_count", "non_humor_count", "ambiguous_count", "humor_rate",
            "positive_count", "negative_count", "neutral_count", "positive_rate", "negative_rate",
            "affiliative_count", "self_enhancing_count", "aggressive_count", "self_defeating_count",
            "humor_type_review_count", "humor_type_review_rate",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for company in companies:
            rows = [r for r in master_rows if r.get("company_name", "") == company]
            h = Counter(r.get("humor_presence", "") for r in rows)
            s = Counter(r.get("sentiment_label", "") for r in rows)
            t = Counter(r.get("humor_type", "") for r in rows)
            review_count = sum(1 for r in rows if r.get("humor_type_review_flag") == "true")
            n = len(rows)
            writer.writerow({
                "company_name": company,
                "row_count": n,
                "humor_count": h.get("humor", 0),
                "non_humor_count": h.get("non_humor", 0),
                "ambiguous_count": h.get("ambiguous", 0),
                "humor_rate": rate(h.get("humor", 0), n),
                "positive_count": s.get("positive", 0),
                "negative_count": s.get("negative", 0),
                "neutral_count": s.get("neutral", 0),
                "positive_rate": rate(s.get("positive", 0), n),
                "negative_rate": rate(s.get("negative", 0), n),
                "affiliative_count": t.get("affiliative", 0),
                "self_enhancing_count": t.get("self_enhancing", 0),
                "aggressive_count": t.get("aggressive", 0),
                "self_defeating_count": t.get("self_defeating", 0),
                "humor_type_review_count": review_count,
                "humor_type_review_rate": rate(review_count, n),
            })


def write_crosstab(path, master_rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    pairs = [
        ("humor_presence", "sentiment_label"),
        ("humor_type", "sentiment_label"),
        ("humor_type", "target_of_humor"),
        ("humor_type", "humor_function"),
        ("humor_type", "harm_potential"),
        ("company_name", "humor_presence"),
        ("company_name", "sentiment_label"),
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_variable", "column_variable", "row_value", "column_value", "count"])
        for row_var, col_var in pairs:
            counts = Counter((r.get(row_var, ""), r.get(col_var, "")) for r in master_rows)
            for (row_value, col_value), count in sorted(counts.items()):
                writer.writerow([row_var, col_var, row_value, col_value, count])


def type_metadata_or_defaults(humor_type_row, presence_label, missing=False):
    if presence_label == "humor" and humor_type_row and not missing:
        return {
            "humor_type_secondary_label": humor_type_row.get("secondary_label", ""),
            "target_of_humor": humor_type_row.get("target_of_humor", ""),
            "humor_function": humor_type_row.get("humor_function", ""),
            "harm_potential": humor_type_row.get("harm_potential", ""),
            "humor_type_key_cues": humor_type_row.get("key_cues", ""),
            "matched_type_cues": humor_type_row.get("matched_type_cues", ""),
        }
    if presence_label == "non_humor":
        return {
            "humor_type_secondary_label": "none",
            "target_of_humor": "not_applicable",
            "humor_function": "not_applicable",
            "harm_potential": "not_applicable",
            "humor_type_key_cues": "",
            "matched_type_cues": "",
        }
    return {
        "humor_type_secondary_label": "none",
        "target_of_humor": "unclear",
        "humor_function": "unclear",
        "harm_potential": "unclear",
        "humor_type_key_cues": "",
        "matched_type_cues": "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-input", type=Path, required=True)
    parser.add_argument("--presence", type=Path, required=True)
    parser.add_argument("--sentiment", type=Path, required=True)
    parser.add_argument("--humor-type", type=Path, required=True)
    parser.add_argument("--master-output", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--company-summary", type=Path, required=True)
    parser.add_argument("--cross-tab", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    input_rows = read_csv(args.full_input)
    presence_rows = read_csv(args.presence)
    sentiment_rows = read_csv(args.sentiment)
    type_rows = read_csv(args.humor_type)

    presence_by_id, presence_dup = index_by_id(presence_rows, "presence")
    sentiment_by_id, sentiment_dup = index_by_id(sentiment_rows, "sentiment")
    type_by_id, type_dup = index_by_id(type_rows, "humor_type")

    errors = []
    if len(input_rows) != args.expected_rows:
        errors.append(f"full_input rows mismatch: {len(input_rows)} != {args.expected_rows}")
    if len(presence_rows) != args.expected_rows:
        errors.append(f"presence rows mismatch: {len(presence_rows)} != {args.expected_rows}")
    if len(sentiment_rows) != args.expected_rows:
        errors.append(f"sentiment rows mismatch: {len(sentiment_rows)} != {args.expected_rows}")
    if presence_dup or sentiment_dup or type_dup:
        errors.append(f"duplicate ids: presence={presence_dup}, sentiment={sentiment_dup}, type={type_dup}")

    master_rows = []
    missing_presence = 0
    missing_sentiment = 0
    missing_type_for_humor = 0
    presence_failed = 0
    sentiment_failed = 0
    type_failed = 0

    for row in input_rows:
        gid = row.get("global_post_id", "")
        presence = presence_by_id.get(gid)
        sentiment = sentiment_by_id.get(gid)
        humor_type = type_by_id.get(gid)

        if not presence:
            missing_presence += 1
            presence = {}
        if not sentiment:
            missing_sentiment += 1
            sentiment = {}

        presence_label = presence.get("humor_presence", "missing_presence")
        if presence.get("classification_status") == "failed":
            presence_failed += 1
        if sentiment.get("sentiment_status") == "failed":
            sentiment_failed += 1

        if presence_label == "humor":
            if not humor_type:
                missing_type_for_humor += 1
                type_label = "ambiguous_or_review"
                type_conf = "0.000000"
                type_reason = "Missing humor type output for humor-present row."
                type_review = "true"
                type_status = "missing"
                type_meta = type_metadata_or_defaults({}, presence_label, missing=True)
            else:
                if humor_type.get("humor_type_status") == "failed":
                    type_failed += 1
                type_label = humor_type.get("humor_type", "ambiguous_or_review")
                type_conf = humor_type.get("humor_type_confidence", "")
                type_reason = humor_type.get("humor_type_rationale", "")
                type_review = humor_type.get("humor_type_review_flag", "")
                type_status = humor_type.get("humor_type_status", "")
                type_meta = type_metadata_or_defaults(humor_type, presence_label)
        elif presence_label == "non_humor":
            type_label = "not_applicable"
            type_conf = "1.000000"
            type_reason = "Humor type not applicable because humor_presence=non_humor."
            type_review = "false"
            type_status = "not_applicable"
            type_meta = type_metadata_or_defaults({}, presence_label)
        else:
            type_label = "ambiguous_or_review"
            type_conf = "0.000000"
            type_reason = "Humor type deferred because humor_presence is ambiguous or missing."
            type_review = "true"
            type_status = "deferred"
            type_meta = type_metadata_or_defaults({}, presence_label)

        out = {
            "global_post_id": gid,
            "tweet_id": row.get("tweet_id", ""),
            "sample_group": row.get("sample_group", ""),
            "company_name": row.get("company_name", ""),
            "source_x_handle": row.get("source_x_handle", ""),
            "created_at": row.get("created_at", ""),
            "text": row.get("text", ""),
            "humor_presence": presence_label,
            "humor_presence_confidence": presence.get("confidence_score", ""),
            "humor_presence_decision_source": presence.get("decision_source", ""),
            "humor_presence_review_flag": presence.get("needs_manual_review", ""),
            "humor_presence_review_reason": presence.get("manual_review_reason", ""),
            "ml_humor_probability": presence.get("ml_humor_probability", ""),
            "rule_label": presence.get("rule_label", ""),
            "rule_evidence": presence.get("rule_evidence", ""),
            "humor_type": type_label,
            "humor_type_confidence": type_conf,
            "humor_type_reason": type_reason,
            "humor_type_review_flag": type_review,
            "humor_type_status": type_status,
            "humor_type_secondary_label": type_meta["humor_type_secondary_label"],
            "target_of_humor": type_meta["target_of_humor"],
            "humor_function": type_meta["humor_function"],
            "harm_potential": type_meta["harm_potential"],
            "humor_type_key_cues": type_meta["humor_type_key_cues"],
            "matched_type_cues": type_meta["matched_type_cues"],
            "sentiment_label": sentiment.get("sentiment_label", "missing_sentiment"),
            "sentiment_confidence": sentiment.get("sentiment_confidence", ""),
            "sentiment_reason": sentiment.get("sentiment_rationale", ""),
            "sentiment_status": sentiment.get("sentiment_status", ""),
            "matched_positive_cues": sentiment.get("matched_positive_cues", ""),
            "matched_negative_cues": sentiment.get("matched_negative_cues", ""),
        }
        master_rows.append(out)

    if missing_presence or missing_sentiment or missing_type_for_humor:
        errors.append(f"missing outputs: presence={missing_presence}, sentiment={missing_sentiment}, type_for_humor={missing_type_for_humor}")
    if presence_failed or sentiment_failed or type_failed:
        errors.append(f"failed rows: presence={presence_failed}, sentiment={sentiment_failed}, type={type_failed}")

    fieldnames = list(master_rows[0].keys()) if master_rows else []
    args.master_output.parent.mkdir(parents=True, exist_ok=True)
    with args.master_output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)

    n = len(master_rows)
    presence_counts = Counter(r.get("humor_presence") for r in master_rows)
    type_counts = Counter(r.get("humor_type") for r in master_rows)
    sentiment_counts = Counter(r.get("sentiment_label") for r in master_rows)
    target_counts = Counter(r.get("target_of_humor") for r in master_rows)
    function_counts = Counter(r.get("humor_function") for r in master_rows)
    harm_counts = Counter(r.get("harm_potential") for r in master_rows)
    type_review_counts = Counter(r.get("humor_type_review_flag") for r in master_rows)

    summary = {
        "integrity_pass": not errors,
        "expected_rows": args.expected_rows,
        "full_input_rows": len(input_rows),
        "presence_rows": len(presence_rows),
        "sentiment_rows": len(sentiment_rows),
        "humor_type_rows": len(type_rows),
        "master_output_rows": len(master_rows),
        "presence_failed_rows": presence_failed,
        "sentiment_failed_rows": sentiment_failed,
        "type_failed_rows": type_failed,
        "missing_presence_rows": missing_presence,
        "missing_sentiment_rows": missing_sentiment,
        "missing_type_for_humor_rows": missing_type_for_humor,
        "humor_presence_distribution": dict(presence_counts),
        "humor_presence_rates": {k: rate(v, n) for k, v in presence_counts.items()},
        "humor_type_distribution": dict(type_counts),
        "humor_type_rates": {k: rate(v, n) for k, v in type_counts.items()},
        "humor_type_review_distribution": dict(type_review_counts),
        "target_of_humor_distribution": dict(target_counts),
        "humor_function_distribution": dict(function_counts),
        "harm_potential_distribution": dict(harm_counts),
        "sentiment_distribution": dict(sentiment_counts),
        "sentiment_rates": {k: rate(v, n) for k, v in sentiment_counts.items()},
        "errors": errors,
    }

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_metric_csv(args.summary_csv, summary)
    write_company_summary(args.company_summary, master_rows)
    write_crosstab(args.cross_tab, master_rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.strict and errors:
        for error in errors:
            print(f"FULL CHAIN ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
