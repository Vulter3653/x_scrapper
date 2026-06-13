#!/usr/bin/env python3
"""Build pilot sample for humor presence classification."""

import argparse
import csv
import random
from pathlib import Path
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/humor/humor_presence_pilot_sample.csv"))
    parser.add_argument("--fortune-n", type=int, default=500)
    parser.add_argument("--wendys-n", type=int, default=150)
    parser.add_argument("--moonpie-n", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        return

    groups = defaultdict(list)
    with args.input.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("text", "").strip():
                continue
            groups[row["sample_group"]].append(row)

    pilot_sample = []

    # 1. Wendy's
    wendys = groups.get("benchmark_aggressive_wendys", [])
    pilot_sample.extend(random.sample(wendys, min(len(wendys), args.wendys_n)))

    # 2. MoonPie
    moonpie = groups.get("benchmark_self_defeating_moonpie", [])
    pilot_sample.extend(random.sample(moonpie, min(len(moonpie), args.moonpie_n)))

    # 3. Fortune Top 100 (Balanced by company)
    fortune = groups.get("fortune_top100_ranked", [])
    if fortune:
        by_company = defaultdict(list)
        for row in fortune:
            by_company[row["company_name"]].append(row)
        
        # Sample evenly across companies as much as possible
        companies = list(by_company.keys())
        random.shuffle(companies)
        
        fortune_sampled = []
        while len(fortune_sampled) < args.fortune_n and companies:
            for company in list(companies):
                if not by_company[company]:
                    companies.remove(company)
                    continue
                
                post = random.choice(by_company[company])
                by_company[company].remove(post)
                fortune_sampled.append(post)
                
                if len(fortune_sampled) >= args.fortune_n:
                    break
        
        pilot_sample.extend(fortune_sampled)

    # Final shuffle
    random.shuffle(pilot_sample)

    # Write output
    if pilot_sample:
        fieldnames = list(pilot_sample[0].keys())
        with args.output.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(pilot_sample)
        print(f"Successfully wrote {len(pilot_sample)} rows to {args.output}")
    else:
        print("No rows sampled.")

if __name__ == "__main__":
    main()
