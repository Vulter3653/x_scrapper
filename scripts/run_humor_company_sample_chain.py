#!/usr/bin/env python3
"""Run a per-company humor classification chain for diagnostic testing.

This runner is intended for the 102-company x 100-post test pass. It avoids a
large Actions matrix while still reducing bottlenecks by running independent
humor-presence and sentiment stages concurrently. Humor type is run only after
presence results are available and only for rows classified as humor.
"""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def run_cmd(cmd):
    print("+ " + " ".join(str(x) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/derived/humor/humor_classification_input.csv"))
    parser.add_argument("--per-company-limit", type=int, default=100)
    parser.add_argument("--expected-companies", type=int, default=102)
    parser.add_argument("--workdir", type=Path, default=Path("data/derived/humor/company_sample_chain"))
    parser.add_argument("--audit-dir", type=Path, default=Path("data/audit/company_sample_chain"))
    args = parser.parse_args()

    inputs_dir = args.workdir / "inputs"
    presence_dir = args.workdir / "presence"
    sentiment_dir = args.workdir / "sentiment"
    type_input_dir = args.workdir / "type_inputs"
    type_dir = args.workdir / "humor_type"
    final_dir = args.workdir / "final"
    args.audit_dir.mkdir(parents=True, exist_ok=True)

    for path in [inputs_dir, presence_dir, sentiment_dir, type_input_dir, type_dir, final_dir]:
        path.mkdir(parents=True, exist_ok=True)

    training_seed = inputs_dir / "humor_presence_training_seed.csv"
    company_input = inputs_dir / "humor_company_sample_input.csv"
    company_manifest = inputs_dir / "humor_company_sample_input_manifest.json"
    presence_results = presence_dir / "humor_presence_company_sample_results.csv"
    sentiment_results = sentiment_dir / "sentiment_company_sample_results.csv"
    type_input = type_input_dir / "humor_type_company_sample_input.csv"
    type_manifest = type_input_dir / "humor_type_company_sample_input_manifest.json"
    type_results = type_dir / "humor_type_company_sample_results.csv"
    master_output = final_dir / "humor_company_sample_master.csv"
    summary_json = args.audit_dir / "humor_company_sample_summary.json"
    summary_csv = args.audit_dir / "humor_company_sample_summary.csv"
    company_summary = args.audit_dir / "humor_company_sample_company_summary.csv"
    cross_tab = args.audit_dir / "humor_company_sample_cross_tab.csv"

    run_cmd([
        sys.executable,
        "scripts/build_humor_presence_training_seed.py",
        "--output",
        training_seed,
    ])

    run_cmd([
        sys.executable,
        "scripts/build_humor_company_sample_input.py",
        "--input",
        args.input,
        "--output",
        company_input,
        "--manifest",
        company_manifest,
        "--per-company-limit",
        args.per_company_limit,
        "--expected-companies",
        args.expected_companies,
    ])

    # Presence and sentiment are independent, so run them concurrently.
    concurrent_jobs = {
        "presence": [
            sys.executable,
            "scripts/classify_humor_presence_local.py",
            "--input",
            company_input,
            "--output",
            presence_results,
            "--training-seed",
            training_seed,
            "--cues",
            "config/humor_presence_rule_cues.json",
        ],
        "sentiment": [
            sys.executable,
            "scripts/classify_sentiment_local.py",
            "--input",
            company_input,
            "--output",
            sentiment_results,
        ],
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run_cmd, cmd): name for name, cmd in concurrent_jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
                print(f"{name} stage completed.", flush=True)
            except Exception:
                print(f"{name} stage failed.", flush=True)
                raise

    run_cmd([
        sys.executable,
        "scripts/build_humor_type_input_from_presence.py",
        "--presence-results",
        presence_results,
        "--output",
        type_input,
        "--manifest",
        type_manifest,
    ])

    run_cmd([
        sys.executable,
        "scripts/classify_humor_type_zero_shot.py",
        "--input",
        type_input,
        "--output",
        type_results,
    ])

    # Count expected master rows from company input.
    import csv
    with company_input.open(encoding="utf-8-sig", newline="") as f:
        expected_rows = sum(1 for _ in csv.DictReader(f))

    run_cmd([
        sys.executable,
        "scripts/merge_humor_full_chain_outputs.py",
        "--full-input",
        company_input,
        "--presence",
        presence_results,
        "--sentiment",
        sentiment_results,
        "--humor-type",
        type_results,
        "--master-output",
        master_output,
        "--summary-json",
        summary_json,
        "--summary-csv",
        summary_csv,
        "--company-summary",
        company_summary,
        "--cross-tab",
        cross_tab,
        "--expected-rows",
        str(expected_rows),
        "--strict",
    ])

    print("Company-sample full chain completed.", flush=True)
    print(f"expected_rows={expected_rows}", flush=True)
    print(f"master_output={master_output}", flush=True)
    print(f"summary_json={summary_json}", flush=True)


if __name__ == "__main__":
    main()
