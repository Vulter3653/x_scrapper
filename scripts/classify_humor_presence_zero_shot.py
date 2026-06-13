#!/usr/bin/env python3
"""Zero-shot humor presence classification using Gemini API with batched calls."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

FIELDNAMES = [
    "global_post_id", "tweet_id", "sample_group", "company_name", "text",
    "humor_presence", "confidence_score", "evidence_phrase",
    "classification_rationale", "needs_manual_review", "manual_review_reason",
    "model_name", "prompt_version", "classification_status", "classified_at",
    "error_type", "error_message",
]
ALLOWED_PRESENCE = {"humor", "non_humor", "ambiguous"}


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def parse_model_json(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if isinstance(value.get("results"), list):
            return [item for item in value["results"] if isinstance(item, dict)]
        if isinstance(value.get("posts"), list):
            return [item for item in value["posts"] if isinstance(item, dict)]
        if value.get("global_post_id"):
            return [value]
    return []


def call_gemini(prompt: str, credential: str, model: str) -> dict[str, Any]:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": credential},
        method="POST",
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            text_content = response_data["candidates"][0]["content"]["parts"][0]["text"]
            return {"parsed": json.loads(text_content)}
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait_time = min(60, (2 ** attempt) + 1)
                print(f"Rate limited; retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            return {"error": f"HTTP Error {exc.code}: {exc.reason}"}
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            return {"error": f"Failed to parse model response: {exc}"}
        except Exception as exc:
            return {"error": f"Unexpected error: {exc}"}
    return {"error": "Max retries exceeded"}


def post_payload(row: dict[str, str]) -> dict[str, str]:
    return {
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "source_x_handle": row.get("source_x_handle", ""),
        "created_at": row.get("created_at", ""),
        "text": row.get("text", ""),
    }


def build_batch_prompt(prompt_template: str, rows: list[dict[str, str]]) -> str:
    return (
        prompt_template.rstrip()
        + "\n\nClassify each post in INPUT_POSTS_JSON. Return only one valid JSON object with a top-level key named results. "
        + "The value of results must be an array with exactly one result object per input post, preserving global_post_id.\n"
        + "Required result fields: global_post_id, tweet_id, sample_group, company_name, text, humor_presence, confidence_score, "
        + "evidence_phrase, classification_rationale, needs_manual_review, manual_review_reason.\n"
        + "\nINPUT_POSTS_JSON:\n"
        + json.dumps([post_payload(row) for row in rows], ensure_ascii=False, indent=2)
    )


def empty_result(row: dict[str, str]) -> dict[str, Any]:
    return {
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "text": row.get("text", ""),
        "humor_presence": "non_humor",
        "confidence_score": 1.0,
        "evidence_phrase": "",
        "classification_rationale": "Empty text is classified as non_humor by default.",
        "needs_manual_review": False,
        "manual_review_reason": "",
        "model_name": "rule-based",
        "prompt_version": "1.0.0",
        "classification_status": "classified",
        "classified_at": utc_now(),
        "error_type": "",
        "error_message": "",
    }


def failed_result(row: dict[str, str], model: str, message: str) -> dict[str, Any]:
    return {
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "text": row.get("text", ""),
        "humor_presence": "ambiguous",
        "confidence_score": 0.0,
        "evidence_phrase": "",
        "classification_rationale": "",
        "needs_manual_review": True,
        "manual_review_reason": "API error or parsing failure",
        "model_name": model,
        "prompt_version": "1.0.0",
        "classification_status": "failed",
        "classified_at": utc_now(),
        "error_type": "api_error",
        "error_message": message,
    }


def normalized_result(row: dict[str, str], model_result: dict[str, Any], model: str) -> dict[str, Any]:
    presence = str(model_result.get("humor_presence", "ambiguous")).strip()
    if presence not in ALLOWED_PRESENCE:
        presence = "ambiguous"
    try:
        confidence = float(model_result.get("confidence_score", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    manual = model_result.get("needs_manual_review", True)
    if isinstance(manual, str):
        manual = manual.lower() == "true"
    return {
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "text": row.get("text", ""),
        "humor_presence": presence,
        "confidence_score": confidence,
        "evidence_phrase": model_result.get("evidence_phrase", ""),
        "classification_rationale": model_result.get("classification_rationale", ""),
        "needs_manual_review": bool(manual),
        "manual_review_reason": model_result.get("manual_review_reason", ""),
        "model_name": model,
        "prompt_version": "1.0.0",
        "classification_status": "classified",
        "classified_at": utc_now(),
        "error_type": "",
        "error_message": "",
    }


def batched(rows: list[dict[str, str]], size: int):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if args.provider != "gemini":
        raise SystemExit(f"Unsupported provider: {args.provider}")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")

    credential = os.environ.get(args.api_key_env)
    if not credential:
        raise SystemExit(f"Error: Environment variable {args.api_key_env} not found.")
    if not args.input.exists():
        raise SystemExit(f"Error: Input file {args.input} not found.")
    if not args.prompt.exists():
        raise SystemExit(f"Error: Prompt file {args.prompt} not found.")
    if not args.schema.exists():
        raise SystemExit(f"Error: Schema file {args.schema} not found.")

    prompt_template = args.prompt.read_text(encoding="utf-8")
    processed_ids: set[str] = set()
    if args.resume and args.output.exists():
        with args.output.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("global_post_id"):
                    processed_ids.add(row["global_post_id"])

    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("global_post_id") not in processed_ids]
    if args.limit is not None:
        rows = rows[: args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    file_exists = args.output.exists()
    written = 0
    with args.output.open("a" if args.resume else "w", encoding="utf-8-sig", newline="") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=FIELDNAMES)
        if not file_exists or not args.resume:
            writer.writeheader()

        for batch_number, batch_rows in enumerate(batched(rows, args.batch_size), start=1):
            empty_rows = [row for row in batch_rows if not row.get("text", "").strip()]
            model_rows = [row for row in batch_rows if row.get("text", "").strip()]
            for row in empty_rows:
                writer.writerow(empty_result(row))
                written += 1

            if model_rows:
                preview = ", ".join(row.get("global_post_id", "") for row in model_rows[:3])
                print(f"Classifying batch {batch_number}: rows={len(model_rows)} first_ids={preview}")
                response = call_gemini(build_batch_prompt(prompt_template, model_rows), credential, args.model)
                if "error" in response:
                    for row in model_rows:
                        writer.writerow(failed_result(row, args.model, response["error"]))
                        written += 1
                else:
                    parsed_rows = parse_model_json(response.get("parsed"))
                    parsed_by_id = {str(item.get("global_post_id", "")): item for item in parsed_rows if item.get("global_post_id")}
                    for row in model_rows:
                        global_post_id = row.get("global_post_id", "")
                        if global_post_id not in parsed_by_id:
                            writer.writerow(failed_result(row, args.model, "Model omitted global_post_id from batch result"))
                        else:
                            writer.writerow(normalized_result(row, parsed_by_id[global_post_id], args.model))
                        written += 1
            output_handle.flush()
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

    print(f"Classification completed for {written} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
