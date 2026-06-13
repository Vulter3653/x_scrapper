#!/usr/bin/env python3
"""Evaluate local humor-presence results and diagnose classifications for 800-row pilot."""

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
    except (ValueError, TypeError):
        return "null"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Aggregated classification results CSV")
    parser.add_argument("--output-audit", type=Path, help="Audit summary CSV")
    parser.add_argument("--output-review-sample", type=Path, help="Review sample CSV")
    parser.add_argument("--output-diagnosis", type=Path, help="Ambiguous diagnosis CSV")
    parser.add_argument("--mode", choices=["smoke", "pilot"], default="pilot")
    parser.add_argument("--sample-size", type=int, default=800)
    parser.add_argument("--humor-threshold", type=float, default=0.70)
    parser.add_argument("--non-humor-threshold", type=float, default=0.30)
    args = parser.parse_args()

    rows = read_csv(args.input)
    if not rows:
        print(f"Error: No data found in {args.input}", file=sys.stderr)
        sys.exit(1)

    total_rows = len(rows)

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

    reviews = sum(1 for r in rows if r.get("needs_manual_review", "").lower() == "true")
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
            except (ValueError, TypeError):
                pass

    if confidences:
        stats.update({
            "mean_confidence": round(statistics.mean(confidences), 6),
            "median_confidence": round(statistics.median(confidences), 6),
        })
    else:
        stats.update({"mean_confidence": 0.0, "median_confidence": 0.0})

    # Rule Coverage
    rule_decisions = sum(1 for r in rows if r.get("decision_source") == "rule")
    stats["rule_coverage_rate"] = round(rule_decisions / total_rows, 4) if total_rows > 0 else 0.0
    
    # ML Decisive Rate
    ml_decisive = sum(1 for r in rows if r.get("decision_source") == "ml" and r.get("humor_presence") != "ambiguous")
    stats["ml_decisive_rate"] = round(ml_decisive / total_rows, 4) if total_rows > 0 else 0.0

    # Distributions
    stats["decision_source_distribution"] = dict(Counter(r.get("decision_source", "missing_column") for r in rows))
    stats["rule_label_distribution"] = dict(Counter(r.get("rule_label", "missing_column") for r in rows))
    
    ml_labels = [get_ml_label(r.get("ml_humor_probability"), args.humor_threshold, args.non_humor_threshold) for r in rows]
    stats["ml_label_distribution"] = dict(Counter(ml_labels))
    
    stats["manual_review_reason_distribution"] = dict(Counter(r.get("manual_review_reason", "missing_column") for r in rows))
    
    # Sample group distribution
    groups = set(r.get("sample_group", "unknown") for r in rows)
    group_stats = {}
    for g in groups:
        g_rows = [r for r in rows if r.get("sample_group") == g]
        g_labels = Counter(r.get("humor_presence") for r in g_rows)
        group_stats[g] = dict(g_labels)
    stats["sample_group_distribution"] = group_stats

    # Company distribution (Top 20)
    companies = Counter(r.get("company_name", "unknown") for r in rows).most_common(20)
    comp_stats = {}
    for c, _ in companies:
        c_rows = [r for r in rows if r.get("company_name") == c]
        c_labels = Counter(r.get("humor_presence") for r in c_rows)
        comp_stats[c] = dict(c_labels)
    stats["company_distribution_top20"] = comp_stats

    # Diagnosis output
    if args.output_diagnosis:
        args.output_diagnosis.parent.mkdir(parents=True, exist_ok=True)
        diagnosis_rows = [
            ["category", "count", "percentage"],
            ["ML ambiguous (between thresholds)", stats["manual_review_reason_distribution"].get("ml_probability_between_thresholds", 0), 0],
            ["Rule ML conflict", stats["manual_review_reason_distribution"].get("rule_ml_conflict", 0), 0],
            ["Rule ambiguous (short text)", stats["manual_review_reason_distribution"].get("rule_ambiguous", 0), 0],
            ["Local classifier error", stats["manual_review_reason_distribution"].get("local_classifier_error", 0), 0],
        ]
        for row in diagnosis_rows[1:]:
            row[2] = round(row[1] / total_rows, 4) if total_rows > 0 else 0.0
        with args.output_diagnosis.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(diagnosis_rows)

    # Print summary JSON
    print(json.dumps(stats, indent=2))

    if args.output_audit:
        args.output_audit.parent.mkdir(parents=True, exist_ok=True)
        with args.output_audit.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for k, v in stats.items():
                if isinstance(v, (dict, list)):
                    writer.writerow([k, json.dumps(v)])
                else:
                    writer.writerow([k, v])

    if args.output_review_sample:
        # Define buckets
        # high_confidence_humor, high_confidence_non_humor, ambiguous, low_confidence, rule_ml_conflict, short_or_empty_text
        # sample_group_wendys, sample_group_moonpie, sample_group_fortune
        sample = []
        sampled_ids = set()

        def add_to_sample(rows_subset, bucket_name, limit):
            count = 0
            for r in rows_subset:
                if count >= limit: break
                if r.get("global_post_id") in sampled_ids: continue
                r_copy = dict(r)
                r_copy["sample_bucket"] = bucket_name
                # Add extra fields
                prob = r.get("ml_humor_probability")
                r_copy["ml_label"] = get_ml_label(prob, args.humor_threshold, args.non_humor_threshold)
                r_copy["ml_probability_humor"] = prob
                try:
                    r_copy["ml_probability_non_humor"] = f"{1.0 - float(prob):.6f}" if prob else ""
                except (ValueError, TypeError):
                    r_copy["ml_probability_non_humor"] = ""
                r_copy["matched_humor_cues"] = r.get("rule_evidence") if r.get("rule_label") == "humor" else ""
                r_copy["matched_non_humor_cues"] = r.get("rule_evidence") if r.get("rule_label") == "non_humor" else ""
                
                sample.append(r_copy)
                sampled_ids.add(r.get("global_post_id"))
                count += 1

        # 1. High confidence humor (Top 15)
        h_rows = sorted([r for r in rows if r.get("humor_presence") == "humor"], key=lambda x: float(x.get("confidence_score", 0)), reverse=True)
        add_to_sample(h_rows, "high_confidence_humor", 15)

        # 2. High confidence non_humor (Top 15)
        nh_rows = sorted([r for r in rows if r.get("humor_presence") == "non_humor"], key=lambda x: float(x.get("confidence_score", 0)), reverse=True)
        add_to_sample(nh_rows, "high_confidence_non_humor", 15)

        # 3. Rule/ML conflict (All up to 20)
        conflict_rows = [r for r in rows if r.get("manual_review_reason") == "rule_ml_conflict"]
        add_to_sample(conflict_rows, "rule_ml_conflict", 20)

        # 4. Short text ambiguous (Top 15)
        short_rows = [r for r in rows if r.get("manual_review_reason") == "rule_ambiguous"]
        add_to_sample(short_rows, "short_or_empty_text", 15)

        # 5. Low confidence (Lowest scores, up to 20)
        low_conf_rows = sorted(rows, key=lambda x: float(x.get("confidence_score", 0)))
        add_to_sample(low_conf_rows, "low_confidence", 20)

        # 6. Benchmark groups
        wendys_rows = [r for r in rows if r.get("sample_group") == "benchmark_aggressive_wendys"]
        add_to_sample(wendys_rows, "sample_group_wendys", 15)
        
        moonpie_rows = [r for r in rows if r.get("sample_group") == "benchmark_self_defeating_moonpie"]
        add_to_sample(moonpie_rows, "sample_group_moonpie", 15)

        fortune_rows = [r for r in rows if r.get("sample_group") == "fortune_top100_ranked"]
        add_to_sample(fortune_rows, "sample_group_fortune", 15)

        # 7. Remaining ambiguous
        amb_rows = [r for r in rows if r.get("humor_presence") == "ambiguous"]
        add_to_sample(amb_rows, "ambiguous", 30)

        if sample:
            args.output_review_sample.parent.mkdir(parents=True, exist_ok=True)
            fields = [
                "sample_bucket", "global_post_id", "tweet_id", "sample_group", "company_name", 
                "source_x_handle", "created_at", "text", "humor_presence", "confidence_score", "rule_label", 
                "ml_label", "ml_probability_humor", "ml_probability_non_humor", "decision_source",
                "needs_manual_review", "manual_review_reason", "matched_humor_cues", "matched_non_humor_cues",
                "model_name", "prompt_version"
            ]
            with args.output_review_sample.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(sample)


if __name__ == "__main__":
    main()
