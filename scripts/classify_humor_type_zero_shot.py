#!/usr/bin/env python3
"""Local zero-shot-style humor type classifier.

The classifier applies the four Humor Styles Questionnaire categories as fixed
concept definitions, then assigns the closest type using transparent cue scores.
The v2 tuning is intentionally conservative:
- it no longer defaults uncued humor to affiliative;
- generic brand/community words are not enough for affiliative classification;
- formal corporate/news/support language is deferred to review unless a specific
  humor-type cue is present.
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
        "phrases": {
            "tag a friend": 3,
            "tag your friend": 3,
            "you and your bestie": 3,
            "you and your friends": 3,
            "the group chat": 3,
            "send this to": 3,
            "tell your friends": 3,
            "friends don't let friends": 3,
            "friends don’t let friends": 3,
            "everyone say": 2,
            "everyone knows": 2,
            "y'all know": 2,
            "yall know": 2,
            "us when": 2,
            "we love you": 2,
            "we said what we said": 2,
            "we're all": 2,
            "we are all": 2,
        },
        "tokens": {
            "bestie": 2,
            "besties": 2,
            "friends": 1,
            "yall": 1,
            "folks": 1,
            "fans": 1,
        },
    },
    "self_enhancing": {
        "phrases": {
            "me when": 3,
            "pov:": 3,
            "point of view": 2,
            "that feeling when": 3,
            "when you realize": 3,
            "when you": 2,
            "not me": 3,
            "i can't": 3,
            "i cant": 3,
            "my toxic trait": 3,
            "main character energy": 3,
            "same energy": 2,
            "me trying": 2,
            "me after": 2,
            "mentally i'm": 2,
            "mentally i’m": 2,
            "surviving on": 2,
            "running on": 2,
        },
        "tokens": {
            "mood": 2,
            "relatable": 2,
            "same": 1,
            "vibes": 1,
            "vibe": 1,
            "chaotic": 1,
            "tired": 1,
            "surviving": 1,
            "coffee": 1,
        },
    },
    "aggressive": {
        "phrases": {
            "sorry not sorry": 3,
            "try again": 3,
            "delete this": 3,
            "sir this is": 3,
            "ma'am this is": 3,
            "ma’am this is": 3,
            "we said what we said": 3,
            "you wish": 2,
            "didn't ask": 2,
            "didn’t ask": 2,
            "not today": 2,
            "nice try": 2,
            "say less": 2,
        },
        "tokens": {
            "roast": 3,
            "roasted": 3,
            "burn": 3,
            "savage": 3,
            "ratio": 2,
            "wrong": 2,
            "nope": 2,
            "nah": 2,
            "trash": 2,
            "clown": 2,
            "ridiculous": 1,
            "worst": 1,
        },
    },
    "self_defeating": {
        "phrases": {
            "our bad": 3,
            "my bad": 3,
            "we messed": 3,
            "we tried": 3,
            "we failed": 3,
            "we're not okay": 3,
            "we are not okay": 3,
            "why are we like this": 3,
            "send help": 3,
            "not us": 3,
            "help us": 2,
            "we forgot": 2,
            "we can't": 2,
            "we cant": 2,
            "this is awkward": 2,
        },
        "tokens": {
            "oops": 3,
            "awkward": 2,
            "embarrassing": 2,
            "crying": 2,
            "mistake": 1,
            "failed": 1,
            "fail": 1,
        },
    },
}

CORPORATE_OR_SUPPORT_CUES = {
    "press release",
    "news release",
    "earnings",
    "quarterly results",
    "investor relations",
    "conference call",
    "annual report",
    "sustainability report",
    "customer support",
    "support team",
    "please contact",
    "learn more",
    "read more",
    "apply now",
    "we're hiring",
    "we are hiring",
    "join our team",
    "webinar",
    "conference",
    "report",
    "filing",
    "shareholders",
    "dividend",
    "clinical",
    "patients",
    "research",
}

TOKEN_RE = re.compile(r"[A-Za-z']+")


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def score_type(text_lower, tokens, cue_config):
    score = 0
    matches = []
    token_set = set(tokens)

    for cue, weight in cue_config["phrases"].items():
        if cue in text_lower:
            score += weight
            matches.append(cue)

    for cue, weight in cue_config["tokens"].items():
        if cue in token_set:
            score += weight
            matches.append(cue)

    return score, sorted(set(matches))


def has_corporate_or_support_context(text_lower):
    return any(cue in text_lower for cue in CORPORATE_OR_SUPPORT_CUES)


def classify(text):
    clean = normalize_text(text)
    if not clean:
        return "ambiguous_or_review", 0.0, "Empty text cannot be assigned a humor type.", [], True

    lower = clean.lower()
    tokens = [t.lower().strip("'") for t in TOKEN_RE.findall(clean)]
    scores = {}
    matches = {}
    for label, cue_config in TYPE_CUES.items():
        scores[label], matches[label] = score_type(lower, tokens, cue_config)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    best_label, best_score = ranked[0]
    second_label, second_score = ranked[1] if len(ranked) > 1 else ("", 0)
    corporate_context = has_corporate_or_support_context(lower)

    if best_score == 0:
        return (
            "ambiguous_or_review",
            0.35,
            f"No type-specific HSQ cue matched; scores={scores}.",
            [],
            True,
        )

    if best_score == second_score:
        return (
            "ambiguous_or_review",
            0.50,
            f"Top humor type scores are tied between {best_label} and {second_label}: scores={scores}.",
            matches[best_label],
            True,
        )

    margin = best_score - second_score

    # Affiliative was over-assigned in the baseline. Require stronger evidence.
    if best_label == "affiliative" and best_score < 3:
        return (
            "ambiguous_or_review",
            0.48,
            f"Affiliative evidence is too weak after v2 tuning; scores={scores}.",
            matches[best_label],
            True,
        )

    # Formal corporate/support context should not be typed unless cue evidence is strong.
    if corporate_context and best_score < 3:
        return (
            "ambiguous_or_review",
            0.47,
            f"Corporate/support context with weak humor-type evidence; scores={scores}.",
            matches[best_label],
            True,
        )

    if margin < 2 and best_score < 4:
        return (
            "ambiguous_or_review",
            0.52,
            f"Humor type margin is too small for a confident assignment; scores={scores}.",
            matches[best_label],
            True,
        )

    confidence = min(0.94, 0.52 + 0.10 * margin + 0.05 * min(best_score, 6))
    rationale = f"Assigned {best_label} from tuned HSQ-style cue definitions; scores={scores}."
    return best_label, confidence, rationale, matches[best_label], confidence < 0.67


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
                "model_name": "local_zero_shot_hsq_humor_type_v2",
                "classified_at": datetime.now(timezone.utc).isoformat(),
            })
            written += 1

    print(f"Local zero-shot humor type classification completed for {written} rows.")


if __name__ == "__main__":
    main()
