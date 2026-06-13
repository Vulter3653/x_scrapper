#!/usr/bin/env python3
"""Fast local sentiment classifier for full-chain diagnostics.

This is a lightweight lexicon classifier intended for one full-chain pass before
later tuning. It is deterministic, has no external API dependency, and is shard-safe.
"""

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_FIELDS = [
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
    "sentiment_label",
    "sentiment_confidence",
    "sentiment_rationale",
    "matched_positive_cues",
    "matched_negative_cues",
    "sentiment_status",
    "sentiment_error_type",
    "sentiment_error_message",
    "model_name",
    "classified_at",
]

POSITIVE_CUES = {
    "thank", "thanks", "congratulations", "congrats", "proud", "excited", "happy",
    "great", "good", "best", "better", "love", "loved", "win", "winner", "winning",
    "celebrate", "celebrating", "welcome", "honor", "honored", "award", "amazing",
    "awesome", "excellent", "success", "successful", "support", "sustainability",
    "innovation", "innovative", "new", "launch", "help", "helping", "improve", "growth",
}

NEGATIVE_CUES = {
    "sorry", "apologize", "apology", "fail", "failed", "failure", "bad", "worse", "worst",
    "problem", "issue", "issues", "delay", "delayed", "crash", "outage", "recall",
    "lawsuit", "investigation", "risk", "risks", "concern", "concerns", "sad", "angry",
    "hate", "damage", "damaged", "loss", "lost", "decline", "down", "cut", "cuts",
    "fraud", "breach", "leak", "unsafe", "violation", "fine", "penalty", "shutdown",
}

TOKEN_RE = re.compile(r"[A-Za-z']+")


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def classify(text):
    clean = normalize_text(text)
    tokens = [t.lower().strip("'") for t in TOKEN_RE.findall(clean)]
    pos_hits = sorted(set(t for t in tokens if t in POSITIVE_CUES))
    neg_hits = sorted(set(t for t in tokens if t in NEGATIVE_CUES))
    pos = len(pos_hits)
    neg = len(neg_hits)

    if not clean:
        return "neutral", 1.0, "Empty text treated as neutral.", pos_hits, neg_hits

    if pos > neg:
        margin = pos - neg
        confidence = min(0.95, 0.60 + 0.10 * margin + 0.03 * min(pos, 5))
        return "positive", confidence, f"Positive cues exceed negative cues ({pos}>{neg}).", pos_hits, neg_hits
    if neg > pos:
        margin = neg - pos
        confidence = min(0.95, 0.60 + 0.10 * margin + 0.03 * min(neg, 5))
        return "negative", confidence, f"Negative cues exceed positive cues ({neg}>{pos}).", pos_hits, neg_hits

    if pos and neg:
        return "neutral", 0.55, f"Positive and negative cues are balanced ({pos}={neg}).", pos_hits, neg_hits
    return "neutral", 0.60, "No strong sentiment cues matched.", pos_hits, neg_hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input not found: {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.input.open(encoding="utf-8-sig", newline="") as f_in, args.output.open("w", encoding="utf-8-sig", newline="") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in reader:
            text = normalize_text(row.get("text") or row.get("full_text") or row.get("content") or row.get("body") or "")
            try:
                label, confidence, rationale, pos_hits, neg_hits = classify(text)
                status = "classified"
                error_type = ""
                error_message = ""
            except Exception as exc:
                label = "neutral"
                confidence = 0.0
                rationale = "Local sentiment classifier error."
                pos_hits = []
                neg_hits = []
                status = "failed"
                error_type = type(exc).__name__
                error_message = str(exc)

            writer.writerow({
                "global_post_id": row.get("global_post_id", ""),
                "tweet_id": row.get("tweet_id", ""),
                "sample_group": row.get("sample_group", ""),
                "company_name": row.get("company_name", ""),
                "source_x_handle": row.get("source_x_handle", ""),
                "created_at": row.get("created_at", ""),
                "text": text,
                "sentiment_label": label,
                "sentiment_confidence": f"{confidence:.6f}",
                "sentiment_rationale": rationale,
                "matched_positive_cues": ";".join(pos_hits),
                "matched_negative_cues": ";".join(neg_hits),
                "sentiment_status": status,
                "sentiment_error_type": error_type,
                "sentiment_error_message": error_message,
                "model_name": "local_lexicon_sentiment_v1",
                "classified_at": datetime.now(timezone.utc).isoformat(),
            })
            written += 1

    print(f"Local sentiment classification completed for {written} rows.")


if __name__ == "__main__":
    main()
