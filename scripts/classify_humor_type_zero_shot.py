#!/usr/bin/env python3
"""Local zero-shot-style humor type classifier.

The classifier applies the four Humor Styles Questionnaire categories as fixed
concept definitions, then assigns the closest type using transparent cue scores.
It is intended for a first full-chain diagnostic pass before later tuning.
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
    "humor_type",
    "humor_type_confidence",
    "humor_type_rationale",
    "matched_type_cues",
    "humor_type_review_flag",
    "humor_type_status",
    "humor_type_error_type",
    "humor_type_error_message",
    "model_name",
    "classified_at",
]

TYPE_CUES = {
    "affiliative": {
        "we", "us", "our", "team", "together", "friend", "friends", "family", "community",
        "everyone", "yall", "folks", "party", "celebrate", "join", "welcome", "fans",
    },
    "self_enhancing": {
        "monday", "tuesday", "survive", "surviving", "still", "again", "coffee", "cope",
        "coping", "mood", "me", "my", "myself", "today", "week", "deadline", "tired",
    },
    "aggressive": {
        "roast", "burn", "savage", "ratio", "wrong", "nope", "nah", "trash", "clown",
        "ridiculous", "competitor", "hate", "worst", "bad", "sorry not sorry", "delete",
    },
    "self_defeating": {
        "oops", "awkward", "sorry", "our bad", "my bad", "we messed", "we tried", "help us",
        "send help", "embarrassing", "mistake", "failed", "fail", "crying", "why are we like this",
    },
}

TOKEN_RE = re.compile(r"[A-Za-z']+")


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def score_type(text_lower, tokens, cues):
    score = 0
    matches = []
    token_set = set(tokens)
    for cue in cues:
        if " " in cue:
            if cue in text_lower:
                score += 2
                matches.append(cue)
        elif cue in token_set:
            score += 1
            matches.append(cue)
    return score, sorted(matches)


def classify(text):
    clean = normalize_text(text)
    if not clean:
        return "ambiguous_or_review", 0.0, "Empty text cannot be assigned a humor type.", [], True

    lower = clean.lower()
    tokens = [t.lower().strip("'") for t in TOKEN_RE.findall(clean)]
    scores = {}
    matches = {}
    for label, cues in TYPE_CUES.items():
        scores[label], matches[label] = score_type(lower, tokens, cues)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    best_label, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        return "affiliative", 0.40, "No type-specific cues matched; defaulting to broad social/affiliative humor for first-pass diagnostics.", [], True

    if best_score == second_score:
        return "ambiguous_or_review", 0.50, f"Top humor type scores are tied: {scores}.", matches[best_label], True

    margin = best_score - second_score
    confidence = min(0.92, 0.55 + 0.12 * margin + 0.04 * min(best_score, 5))
    rationale = f"Assigned {best_label} from fixed HSQ-style type definitions; scores={scores}."
    return best_label, confidence, rationale, matches[best_label], confidence < 0.65


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
            text = normalize_text(row.get("text", ""))
            try:
                label, confidence, rationale, matched, review_flag = classify(text)
                status = "classified"
                error_type = ""
                error_message = ""
            except Exception as exc:
                label = "ambiguous_or_review"
                confidence = 0.0
                rationale = "Local humor type classifier error."
                matched = []
                review_flag = True
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
                "humor_type": label,
                "humor_type_confidence": f"{confidence:.6f}",
                "humor_type_rationale": rationale,
                "matched_type_cues": ";".join(matched),
                "humor_type_review_flag": str(bool(review_flag)).lower(),
                "humor_type_status": status,
                "humor_type_error_type": error_type,
                "humor_type_error_message": error_message,
                "model_name": "local_zero_shot_hsq_humor_type_v1",
                "classified_at": datetime.now(timezone.utc).isoformat(),
            })
            written += 1

    print(f"Local zero-shot humor type classification completed for {written} rows.")


if __name__ == "__main__":
    main()
