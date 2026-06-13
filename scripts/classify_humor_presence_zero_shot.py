#!/usr/bin/env python3
"""Zero-shot humor presence classification using Gemini API."""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

def call_gemini(prompt: str, api_key: str, model: str = "gemini-3.5-flash") -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    # Exponential backoff for retries
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                # Extract text from response
                try:
                    text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_content)
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    return {"error": f"Failed to parse model response: {str(e)}", "raw": str(res_data)[:500]}
        except urllib.error.HTTPError as e:
            if e.code == 429: # Rate limit
                wait_time = (2 ** attempt) + 1
                time.sleep(wait_time)
                continue
            return {"error": f"HTTP Error {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
            
    return {"error": "Max retries exceeded"}

def build_prompt(prompt_template: str, row: dict) -> str:
    post_payload = {
        "global_post_id": row.get("global_post_id", ""),
        "tweet_id": row.get("tweet_id", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "source_x_handle": row.get("source_x_handle", ""),
        "created_at": row.get("created_at", ""),
        "text": row.get("text", ""),
    }

    return (
        prompt_template.rstrip()
        + "\n\n"
        + "Classify the following post. Return only one valid JSON object that conforms to the required output schema.\n"
        + "\nINPUT_POST_JSON:\n"
        + json.dumps(post_payload, ensure_ascii=False, indent=2)
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--api-key-env", default="GEMINI_API_KEY")
    parser.add_argument("--batch-size", type=int, default=1) # urillb based is simple, 1 by 1 for safety
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"Error: Environment variable {args.api_key_env} not found.")
        sys.exit(1)

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)

    prompt_template = args.prompt.read_text(encoding="utf-8")
    
    # Load existing results if resuming
    processed_ids = set()
    if args.resume and args.output.exists():
        with args.output.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_ids.add(row["global_post_id"])

    # Prepare output file
    file_exists = args.output.exists()
    
    # Fieldnames from schema requirements
    fieldnames = [
        "global_post_id", "tweet_id", "sample_group", "company_name", "text",
        "humor_presence", "confidence_score", "evidence_phrase", 
        "classification_rationale", "needs_manual_review", "manual_review_reason",
        "model_name", "prompt_version", "classification_status", "classified_at",
        "error_type", "error_message"
    ]

    count = 0
    with args.input.open(encoding="utf-8-sig", newline="") as f_in, \
         args.output.open("a" if args.resume else "w", encoding="utf-8-sig", newline="") as f_out:
        
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        
        if not file_exists or not args.resume:
            writer.writeheader()

        for row in reader:
            global_id = row["global_post_id"]
            if global_id in processed_ids:
                continue
            
            if args.limit and count >= args.limit:
                break

            text = row.get("text", "").strip()
            
            # Handle empty text
            if not text:
                result = {
                    "global_post_id": global_id,
                    "tweet_id": row.get("tweet_id", ""),
                    "sample_group": row.get("sample_group", ""),
                    "company_name": row.get("company_name", ""),
                    "text": text,
                    "humor_presence": "non_humor",
                    "confidence_score": 1.0,
                    "evidence_phrase": "",
                    "classification_rationale": "Empty text is classified as non_humor by default.",
                    "needs_manual_review": False,
                    "manual_review_reason": "",
                    "model_name": "rule-based",
                    "prompt_version": "1.0.0",
                    "classification_status": "classified",
                    "classified_at": datetime.utcnow().isoformat(),
                    "error_type": "",
                    "error_message": ""
                }
            else:
                prompt = build_prompt(prompt_template, row)
                
                print(f"Classifying {global_id}...")
                model_res = call_gemini(prompt, api_key, args.model)
                
                if "error" in model_res:
                    result = {
                        "global_post_id": global_id,
                        "tweet_id": row.get("tweet_id", ""),
                        "sample_group": row.get("sample_group", ""),
                        "company_name": row.get("company_name", ""),
                        "text": text,
                        "humor_presence": "ambiguous",
                        "confidence_score": 0.0,
                        "evidence_phrase": "",
                        "classification_rationale": "",
                        "needs_manual_review": True,
                        "manual_review_reason": "API error or parsing failure",
                        "model_name": args.model,
                        "prompt_version": "1.0.0",
                        "classification_status": "failed",
                        "classified_at": datetime.utcnow().isoformat(),
                        "error_type": "api_error",
                        "error_message": model_res["error"]
                    }
                else:
                    # Map model response to our fieldnames
                    result = {
                        "global_post_id": global_id,
                        "tweet_id": row.get("tweet_id", ""),
                        "sample_group": row.get("sample_group", ""),
                        "company_name": row.get("company_name", ""),
                        "text": text,
                        "humor_presence": model_res.get("humor_presence", "ambiguous"),
                        "confidence_score": model_res.get("confidence_score", 0.0),
                        "evidence_phrase": model_res.get("evidence_phrase", ""),
                        "classification_rationale": model_res.get("classification_rationale", ""),
                        "needs_manual_review": model_res.get("needs_manual_review", True),
                        "manual_review_reason": model_res.get("manual_review_reason", ""),
                        "model_name": args.model,
                        "prompt_version": "1.0.0",
                        "classification_status": "classified",
                        "classified_at": datetime.utcnow().isoformat(),
                        "error_type": "",
                        "error_message": ""
                    }
            
            writer.writerow(result)
            f_out.flush() # Ensure it's saved even if interrupted
            count += 1
            time.sleep(1) # Be nice to the API in 1-by-1 mode

    print(f"Classification completed for {count} rows.")

if __name__ == "__main__":
    main()
