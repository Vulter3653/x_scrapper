#!/usr/bin/env python3
"""
Diagnose ambiguous humor classification cases to identify patterns and root causes.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# Standard promotional and customer service patterns
PROMO_KEYWORDS = [
    r"\bbuy\b", r"\bsale\b", r"\bavailable\b", r"\blimited\b", r"\boffer\b", 
    r"\bshop\b", r"\bget your\b", r"\bcheck out\b", r"\blink in bio\b", 
    r"\border now\b", r"\bnow on\b", r"\bexclusive\b", r"\bdiscount\b"
]

CS_PATTERNS = [
    r"\bdm us\b", r"\bhelp\b", r"\bsorry\b", r"\border\b", r"\bcontact\b", 
    r"\bassist\b", r"\breference number\b", r"\breach out\b", r"\bemail\b",
    r"\binbox\b", r"\bwe'd like to help\b", r"\blooking into this\b"
]

AGGRESSIVE_CANDIDATES = [
    r"\bratio\b", r"\bmid\b", r"\bdelete\b", r"\b L \b", r"\bfell off\b", 
    r"\bskill issue\b", r"\bstfu\b", r"\bdumb\b", r"\bstupid\b", r"\bclown\b"
]

SELF_DEFEATING_CANDIDATES = [
    r"\bclown\b", r"\bgarbage\b", r"\btrash\b", r"\bbad at\b", r"\bfail\b", 
    r"\bpain\b", r"\bsad\b", r"\bcrying\b", r"\bwhy am i\b", r"\bmy life\b"
]

def load_humor_cues():
    cue_path = Path("config/humor_presence_rule_cues.json")
    if cue_path.exists():
        with open(cue_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("strong_humor_cues", [])
    return []

def get_text_length_bucket(text):
    length = len(text)
    if length <= 50: return "0-50"
    if length <= 100: return "51-100"
    if length <= 150: return "101-150"
    if length <= 200: return "151-200"
    return "201+"

def analyze_row(row, humor_cues):
    text = row.get("text", "").lower()
    
    # Feature detection
    has_q = "?" in text
    has_excl = "!" in text
    has_emoji = bool(re.search(r"[\U00010000-\U0010ffff]", text))
    has_hashtag = "#" in text
    has_mention = "@" in text
    has_url = any(u in text for u in ["http://", "https://", "t.co/"])
    
    is_promo = any(re.search(p, text) for p in PROMO_KEYWORDS)
    is_cs = any(re.search(p, text) for p in CS_PATTERNS)
    has_humor_cue = any(cue.lower() in text for cue in humor_cues)
    
    is_aggressive_cand = any(re.search(p, text) for p in AGGRESSIVE_CANDIDATES)
    is_self_defeating_cand = any(re.search(p, text) for p in SELF_DEFEATING_CANDIDATES)
    
    return {
        "length_bucket": get_text_length_bucket(text),
        "has_question_mark": has_q,
        "has_exclamation": has_excl,
        "has_emoji": has_emoji,
        "has_hashtag": has_hashtag,
        "has_mention": has_mention,
        "has_url": has_url,
        "is_promotional": is_promo,
        "is_customer_service": is_cs,
        "has_humor_cue": has_humor_cue,
        "is_aggressive_candidate": is_aggressive_cand,
        "is_self_defeating_candidate": is_self_defeating_cand
    }

def main():
    parser = argparse.ArgumentParser(description="Diagnose ambiguous humor classification cases.")
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/full_chain/humor_full_chain_master.csv"),
                        help="Path to the master humor classification CSV.")
    parser.add_argument("--output-csv", type=Path, default=Path("data/audit/humor/evaluation/ambiguous_case_diagnostics.csv"),
                        help="Path to save the detailed diagnostic CSV.")
    parser.add_argument("--output-summary", type=Path, default=Path("data/audit/humor/evaluation/ambiguous_case_diagnostics_summary.json"),
                        help="Path to save the summary JSON.")
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    
    humor_cues = load_humor_cues()
    
    total_rows = 0
    ambiguous_rows = []
    
    with open(args.input, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Check both possible labels for ambiguity
            if row.get("humor_presence") == "ambiguous" or row.get("humor_type") == "ambiguous_or_review":
                ambiguous_rows.append(row)
                
    if not ambiguous_rows:
        print("No ambiguous cases found to diagnose.")
        return

    print(f"Analyzing {len(ambiguous_rows)} ambiguous cases out of {total_rows} total rows...")
    
    diagnostics = []
    summary_stats = {
        "total_rows": total_rows,
        "ambiguous_count": len(ambiguous_rows),
        "ambiguous_ratio": round(len(ambiguous_rows) / total_rows, 4) if total_rows > 0 else 0,
        "company_distribution": Counter(),
        "length_bucket_distribution": Counter(),
        "feature_counts": Counter(),
        "top_ambiguous_companies": [],
        "aggressive_candidates_count": 0,
        "self_defeating_candidates_count": 0
    }
    
    company_totals = Counter()
    with open(args.input, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_totals[row.get("company_name", "Unknown")] += 1

    for row in ambiguous_rows:
        analysis = analyze_row(row, humor_cues)
        company = row.get("company_name", "Unknown")
        
        summary_stats["company_distribution"][company] += 1
        summary_stats["length_bucket_distribution"][analysis["length_bucket"]] += 1
        
        for feature, val in analysis.items():
            if feature not in ["length_bucket", "is_aggressive_candidate", "is_self_defeating_candidate"] and val:
                summary_stats["feature_counts"][feature] += 1
        
        if analysis["is_aggressive_candidate"]:
            summary_stats["aggressive_candidates_count"] += 1
        if analysis["is_self_defeating_candidate"]:
            summary_stats["self_defeating_candidates_count"] += 1
            
        diag_row = {
            "global_post_id": row.get("global_post_id"),
            "company_name": company,
            "text": row.get("text"),
            "humor_presence": row.get("humor_presence"),
            "humor_type": row.get("humor_type")
        }
        diag_row.update(analysis)
        diagnostics.append(diag_row)

    # Calculate top ambiguous companies by ratio
    company_ratios = []
    for company, count in summary_stats["company_distribution"].items():
        total = company_totals.get(company, 0)
        ratio = round(count / total, 4) if total > 0 else 0
        company_ratios.append({"company": company, "ambiguous_count": count, "total_count": total, "ratio": ratio})
    
    summary_stats["top_ambiguous_companies"] = sorted(company_ratios, key=lambda x: x["ratio"], reverse=True)[:10]
    
    # Save CSV
    if diagnostics:
        keys = diagnostics[0].keys()
        with open(args.output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(diagnostics)
            
    # Save Summary JSON
    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2, ensure_ascii=False)
        
    print(f"Diagnostics complete. Summary saved to {args.output_summary}")

if __name__ == "__main__":
    main()
