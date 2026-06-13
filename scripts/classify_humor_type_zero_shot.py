#!/usr/bin/env python3
"""HSQ codebook-based zero-shot-style humor type classifier.

This classifier operationalizes the uploaded HSQ zero-shot codebook at the text
level. It assigns each humor-present text to one of four HSQ-derived humor styles
and emits the codebook metadata needed for reliability checks:
secondary_label, target_of_humor, humor_function, harm_potential, reason, and key_cues.

Important: this is text-level humor style classification, not a respondent-level
Humor Styles Questionnaire trait measurement.
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
    "secondary_label",
    "target_of_humor",
    "humor_function",
    "harm_potential",
    "humor_type_rationale",
    "key_cues",
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
            "we're all": 2,
            "we are all": 2,
            "make everyone laugh": 3,
            "lighten the mood": 3,
        },
        "tokens": {
            "bestie": 2,
            "besties": 2,
            "friends": 1,
            "yall": 1,
            "folks": 1,
            "fans": 1,
            "together": 1,
        },
        "target_of_humor": "situation",
        "humor_function": "relationship_building",
        "harm_potential": "low",
    },
    "self_enhancing": {
        "phrases": {
            "me when": 3,
            "pov:": 3,
            "point of view": 2,
            "that feeling when": 3,
            "when you realize": 3,
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
            "at least i": 2,
            "coping with": 3,
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
            "cope": 2,
            "coping": 2,
        },
        "target_of_humor": "self",
        "humor_function": "coping",
        "harm_potential": "low",
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
            "your mistake": 2,
            "their mistake": 2,
            "competitor could never": 3,
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
            "mock": 2,
            "owned": 2,
        },
        "target_of_humor": "other_individual",
        "humor_function": "ridicule",
        "harm_potential": "high",
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
            "laugh at us": 3,
            "we deserve that": 3,
        },
        "tokens": {
            "oops": 3,
            "awkward": 2,
            "embarrassing": 2,
            "crying": 2,
            "mistake": 1,
            "failed": 1,
            "fail": 1,
            "useless": 2,
        },
        "target_of_humor": "self",
        "humor_function": "self_deprecation",
        "harm_potential": "high",
    },
}

SELF_MARKERS = {"i", "me", "my", "myself", "we", "us", "our", "ourselves"}
OTHER_MARKERS = {"you", "your", "they", "them", "their", "competitor", "customer", "customers"}
ADVERSITY_MARKERS = {"tired", "stress", "stressed", "hard", "fail", "failed", "mistake", "awkward", "surviving", "cope", "coping"}
SOCIAL_MARKERS = {"friend", "friends", "bestie", "team", "together", "everyone", "fans", "community"}

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


def infer_uncued_label(tokens):
    token_set = set(tokens)
    has_self = bool(token_set & SELF_MARKERS)
    has_other = bool(token_set & OTHER_MARKERS)
    has_adversity = bool(token_set & ADVERSITY_MARKERS)
    has_social = bool(token_set & SOCIAL_MARKERS)

    if has_self and has_adversity:
        return "self_enhancing", "self", "coping", "low"
    if has_other and has_adversity:
        return "aggressive", "other_individual", "criticism", "medium"
    if has_self:
        return "self_enhancing", "self", "emotion_regulation", "low"
    if has_social:
        return "affiliative", "situation", "relationship_building", "low"
    return "affiliative", "unclear", "tension_reduction", "low"


def secondary_label_from_ranked(ranked, best_label):
    for label, _score in ranked:
        if label != best_label:
            return label
    return "none"


def build_result(label, confidence, rationale, matches, review_flag, secondary_label="none", target=None, function=None, harm=None):
    profile = TYPE_CUES.get(label, {})
    return {
        "label": label,
        "confidence": confidence,
        "secondary_label": secondary_label or "none",
        "target_of_humor": target or profile.get("target_of_humor", "unclear"),
        "humor_function": function or profile.get("humor_function", "unclear"),
        "harm_potential": harm or profile.get("harm_potential", "low"),
        "rationale": rationale,
        "key_cues": sorted(set(matches)),
        "review_flag": bool(review_flag),
    }


def classify(text):
    clean = normalize_text(text)
    if not clean:
        return build_result(
            "affiliative",
            0.20,
            "Empty or missing text; assigning the nearest benign relationship-oriented label only as a low-confidence placeholder.",
            [],
            True,
            secondary_label="none",
            target="unclear",
            function="unclear",
            harm="low",
        )

    lower = clean.lower()
    tokens = [t.lower().strip("'") for t in TOKEN_RE.findall(clean)]
    scores = {}
    matches = {}
    for label, cue_config in TYPE_CUES.items():
        scores[label], matches[label] = score_type(lower, tokens, cue_config)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    best_label, best_score = ranked[0]
    second_label, second_score = ranked[1] if len(ranked) > 1 else ("none", 0)
    corporate_context = has_corporate_or_support_context(lower)

    if best_score == 0:
        inferred_label, target, function, harm = infer_uncued_label(tokens)
        return build_result(
            inferred_label,
            0.35,
            f"No explicit HSQ type cue matched; assigning nearest codebook label with low confidence based on inferred axis. scores={scores}.",
            [],
            True,
            secondary_label=secondary_label_from_ranked(ranked, inferred_label),
            target=target,
            function=function,
            harm=harm,
        )

    if best_score == second_score:
        return build_result(
            best_label,
            0.50,
            f"Top HSQ type scores are tied between {best_label} and {second_label}; assigning primary label but requiring review. scores={scores}.",
            matches[best_label],
            True,
            secondary_label=second_label,
        )

    margin = best_score - second_score
    review_flag = False
    rationale_notes = []

    if best_label == "affiliative" and best_score < 3:
        review_flag = True
        rationale_notes.append("Affiliative evidence is weak; review required under v3 HSQ codebook implementation.")

    if corporate_context and best_score < 3:
        review_flag = True
        rationale_notes.append("Corporate/support context detected with weak humor-type evidence.")

    if margin < 2 and best_score < 4:
        review_flag = True
        rationale_notes.append("Top-label margin is small.")

    confidence = min(0.94, 0.50 + 0.10 * margin + 0.05 * min(best_score, 6))
    if review_flag:
        confidence = min(confidence, 0.62)

    rationale = (
        f"Assigned {best_label} using HSQ codebook axes: target, function, and harm potential. scores={scores}."
    )
    if rationale_notes:
        rationale += " " + " ".join(rationale_notes)

    return build_result(
        best_label,
        confidence,
        rationale,
        matches[best_label],
        review_flag or confidence < 0.67,
        secondary_label=second_label,
    )


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
                result = classify(text)
                status = "classified"
                error_type = ""
                error_message = ""
            except Exception as exc:
                result = build_result(
                    "affiliative",
                    0.0,
                    "Local HSQ humor type classifier error; assigning low-confidence placeholder label for schema integrity.",
                    [],
                    True,
                    secondary_label="none",
                    target="unclear",
                    function="unclear",
                    harm="low",
                )
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
                "humor_type": result["label"],
                "humor_type_confidence": f"{result['confidence']:.6f}",
                "secondary_label": result["secondary_label"],
                "target_of_humor": result["target_of_humor"],
                "humor_function": result["humor_function"],
                "harm_potential": result["harm_potential"],
                "humor_type_rationale": result["rationale"],
                "key_cues": ";".join(result["key_cues"]),
                "matched_type_cues": ";".join(result["key_cues"]),
                "humor_type_review_flag": str(bool(result["review_flag"])).lower(),
                "humor_type_status": status,
                "humor_type_error_type": error_type,
                "humor_type_error_message": error_message,
                "model_name": "local_zero_shot_hsq_humor_type_v3_codebook",
                "classified_at": datetime.now(timezone.utc).isoformat(),
            })
            written += 1

    print(f"Local HSQ codebook humor type classification completed for {written} rows.")


if __name__ == "__main__":
    main()
