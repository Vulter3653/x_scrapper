#!/usr/bin/env python3
"""Evaluate local humor-presence results and diagnose ambiguous classifications."""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_ml_label(prob_str, humor_threshold=0.70, non_humor_threshold=0.30):
    if not prob_str:
        return "null"
    try:
        prob = float(prob_str)
        if prob >= humor_threshold:
            return "humor"
        if prob <= non_humor_threshold:
            return "non_humor"
        return "ambiguous"
    except ValueError:
        return "null"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Classification results CSV")
    parser.add_argument("--output-audit", type=Path, help="Audit summary CSV")
    parser.add_argument("--output-review-sample", type=Path, help="Review sample CSV")
    parser.add_argument("--mode", choices=["smoke", "pilot"], default="smoke")
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--humor-threshold", type=float, default=0.70)
    parser.add_argument("--non-humor-threshold", type=float, default=0.30)
    args = parser.parse_args()

    rows = read_csv(args.input)
    if not rows:
        print(f"Error: No data found in {args.input}", file=sys.stderr)
        sys.exit(1)

    total_rows = len(rows)
    # Filter by sample_size if needed, but usually we evaluate the whole input file
    # for smoke/pilot which are already limited.
    
    stats = {
        "input_rows": args.sample_size,
        "output_rows": total_rows,
        "classified_rows": sum(1 for r in rows if r.get("classification_status") == "classified"),
        "failed_rows": sum(1 for r in rows if r.get("classification_status") == "failed"),
    }

    labels = Counter(r.get("humor_presence", "missing_column") for r in rows)
    stats.update({
        "humor_count": labels.get("humor", 0),
        "non_humor_count": labels.get("non_humor", 0),
        "ambiguous_count": labels.get("ambiguous", 0),
    })

    if total_rows > 0:
        stats.update({
            "humor_rate": round(stats["humor_count"] / total_rows, 4),
            "non_humor_rate": round(stats["non_humor_count"] / total_rows, 4),
            "ambiguous_rate": round(stats["ambiguous_count"] / total_rows, 4),
        })

    reviews = sum(1 for r in rows if r.get("needs_manual_review") == "true")
    stats.update({
        "manual_review_count": reviews,
        "manual_review_rate": round(reviews / total_rows, 4) if total_rows > 0 else 0,
    })

    confidences = []
    for r in rows:
        val = r.get("confidence_score")
        if val:
            try:
                confidences.append(float(val))
            except ValueError:
                pass

    if confidences:
        stats.update({
            "mean_confidence": round(statistics.mean(confidences), 6),
            "median_confidence": round(statistics.median(confidences), 6),
            "min_confidence": round(min(confidences), 6),
            "max_confidence": round(max(confidences), 6),
        })
    else:
        stats.update({
            "mean_confidence": 0, "median_confidence": 0, "min_confidence": 0, "max_confidence": 0
        })

    # Distributions
    stats["decision_source_distribution"] = dict(Counter(r.get("decision_source", "missing_column") for r in rows))
    stats["rule_label_distribution"] = dict(Counter(r.get("rule_label", "missing_column") for r in rows))
    
    # ML label is often internal or missing from CSV, infer it from probability
    ml_labels = [get_ml_label(r.get("ml_humor_probability"), args.humor_threshold, args.non_humor_threshold) for r in rows]
    stats["ml_label_distribution"] = dict(Counter(ml_labels))
    
    stats["manual_review_reason_distribution"] = dict(Counter(r.get("manual_review_reason", "missing_column") for r in rows))
    stats["classifier_name_distribution"] = dict(Counter(r.get("model_name", "missing_column") for r in rows))
    stats["classifier_version_distribution"] = dict(Counter(r.get("prompt_version", "missing_column") for r in rows))

    # Optional group stats
    groups = set(r.get("sample_group", "unknown") for r in rows)
    group_stats = {}
    for g in groups:
        g_rows = [r for r in rows if r.get("sample_group") == g]
        g_labels = Counter(r.get("humor_presence") for r in g_rows)
        group_stats[g] = dict(g_labels)
    stats["sample_group_distribution"] = group_stats

    companies = set(r.get("company_name", "unknown") for r in rows)
    company_stats = {}
    for c in companies:
        c_rows = [r for r in rows if r.get("company_name") == c]
        c_labels = Counter(r.get("humor_presence") for r in c_rows)
        company_stats[c] = dict(c_labels)
    stats["company_distribution"] = company_stats

    # Diagnosis of ambiguous 80%
    ambiguous_rows = [r for r in rows if r.get("humor_presence") == "ambiguous"]
    diagnosis = Counter()
    for r in ambiguous_rows:
        reason = r.get("manual_review_reason", "")
        if reason:
            diagnosis[reason] += 1
        else:
            diagnosis["unknown_ambiguous"] += 1
    stats["ambiguous_diagnosis"] = dict(diagnosis)

    # Print results
    print(json.dumps(stats, indent=2))

    if args.output_audit:
        args.output_audit.parent.mkdir(parents=True, exist_ok=True)
        # Flatten for CSV audit if needed, but dict to CSV is easier as key-value pairs
        with args.output_audit.open("w", encoding="utf-8") as f:
            writer = csv.writer(f)
            for k, v in stats.items():
                writer.writerow([k, json.dumps(v) if isinstance(v, dict) else v])

    if args.output_review_sample:
        # Generate review sample
        # high-confidence humor 10, non_humor 10, ambiguous 30, rule/ML conflict 20, short-text ambiguous 10, low-confidence 20
        # Total up to 100
        sample = []
        
        def get_bucket(r, bucket_name, limit):
            count = 0
            for row in r:
                if count >= limit: break
                row["sample_bucket"] = bucket_name
                sample.append(row)
                count += 1
            return r[count:]

        # High confidence humor
        humor_rows = sorted([r for r in rows if r.get("humor_presence") == "humor"], key=lambda x: float(x.get("confidence_score", 0)), reverse=True)
        humor_rows = get_bucket(humor_rows, "high_confidence_humor", 10)

        # High confidence non_humor
        non_humor_rows = sorted([r for r in rows if r.get("humor_presence") == "non_humor"], key=lambda x: float(x.get("confidence_score", 0)), reverse=True)
        non_humor_rows = get_bucket(non_humor_rows, "high_confidence_non_humor", 10)

        # Ambiguous
        amb_rows = [r for r in rows if r.get("humor_presence") == "ambiguous"]
        # Rule/ML conflict
        conflict_rows = [r for r in amb_rows if r.get("manual_review_reason") == "rule_ml_conflict"]
        conflict_rows = get_bucket(conflict_rows, "rule_ml_conflict", 20)
        
        # Short text ambiguous
        short_rows = [r for r in amb_rows if r.get("manual_review_reason") == "rule_ambiguous"] # Assuming rule_ambiguous for short text
        short_rows = get_bucket(short_rows, "short_text_ambiguous", 10)

        # Other ambiguous
        other_amb = [r for r in amb_rows if r.get("manual_review_reason") == "ml_probability_between_thresholds"]
        other_amb = get_bucket(other_amb, "ml_ambiguous", 30)

        # Low confidence (rest of ambiguous or low score)
        low_conf = sorted([r for r in rows if r not in sample], key=lambda x: float(x.get("confidence_score", 0)))
        get_bucket(low_conf, "low_confidence", 20)

        if sample:
            args.output_review_sample.parent.mkdir(parents=True, exist_ok=True)
            with args.output_review_sample.open("w", encoding="utf-8-sig", newline="") as f:
                # Add inferred ml_label to sample output
                for r in sample:
                    r["ml_label"] = get_ml_label(r.get("ml_humor_probability"), args.humor_threshold, args.non_humor_threshold)
                    r["ml_probability_humor"] = r.get("ml_humor_probability", "")
                    r["ml_probability_non_humor"] = str(1.0 - float(r.get("ml_humor_probability"))) if r.get("ml_humor_probability") else ""
                    r["matched_humor_cues"] = r.get("rule_evidence") if r.get("rule_label") == "humor" else ""
                    r["matched_non_humor_cues"] = r.get("rule_evidence") if r.get("rule_label") == "non_humor" else ""
                
                # Filter fields for review sample
                fields = [
                    "sample_bucket", "global_post_id", "tweet_id", "sample_group", "company_name", 
                    "created_at", "text", "humor_presence", "confidence_score", "rule_label", 
                    "ml_label", "ml_probability_humor", "ml_probability_non_humor", "decision_source",
                    "needs_manual_review", "manual_review_reason", "matched_humor_cues", "matched_non_humor_cues"
                ]
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(sample)


if __name__ == "__main__":
    main()
