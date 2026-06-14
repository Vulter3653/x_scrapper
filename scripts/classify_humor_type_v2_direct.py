#!/usr/bin/env python3
"""HSQ humor type v2 direct 5-class classifier for brand X posts.

Classifies all posts (including non-humor) directly into one of six labels without
requiring a prior humor-presence gate. Addresses three weaknesses of the v1 pipeline:
  1. Ambiguous_or_review over-assignment from deferred ambiguous presence labels
  2. Under-detection of aggressive and self_defeating humor in brand posts
  3. URL-dominant rule over-suppression of humor in mixed posts

Key architectural difference from v1 classify_humor_type_zero_shot.py:
  - Applies not_humor scoring as an explicit class alongside the four HSQ types
  - Uses expanded brand-appropriate cues for aggressive and self_defeating
  - Makes a forced best-guess choice; only assigns ambiguous_review when genuinely tied
  - Operates on the full post population, not just humor-flagged rows
"""

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

V2_OUTPUT_FIELDS = [
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "source_x_handle",
    "created_at",
    "text",
    "v2_humor_label",
    "v2_confidence",
    "v2_target_of_humor",
    "v2_humor_function",
    "v2_review_flag",
    "v2_reason_code",
]

ALLOWED_V2_LABELS = frozenset(
    ["affiliative", "self_enhancing", "aggressive", "self_defeating", "not_humor", "ambiguous_review"]
)

TOKEN_RE = re.compile(r"[A-Za-z']+")

NOT_HUMOR_PHRASES = {
    "announcing": 4,
    "proud to announce": 5,
    "we are pleased": 5,
    "we're pleased": 5,
    "pleased to announce": 5,
    "honored to announce": 5,
    "excited to announce": 4,
    "excited to share": 4,
    "introducing": 4,
    "now available": 4,
    "available now": 4,
    "shop now": 5,
    "buy now": 5,
    "order now": 5,
    "link in bio": 4,
    "use code": 4,
    "limited time": 4,
    "sign up": 3,
    "register now": 4,
    "apply now": 4,
    "we're hiring": 5,
    "we are hiring": 5,
    "join our team": 5,
    "open positions": 4,
    "please dm": 5,
    "please contact": 5,
    "reach out to": 3,
    "our team is here": 4,
    "customer support": 5,
    "we've reached out": 4,
    "earnings": 4,
    "fiscal quarter": 5,
    "quarterly results": 5,
    "investor relations": 5,
    "annual report": 5,
    "shareholder": 5,
    "dividend": 5,
    "press release": 5,
    "news release": 5,
    "conference call": 4,
    "sustainability report": 4,
    "committed to": 3,
    "we believe in": 3,
    "our mission": 3,
    "our values": 3,
    "webinar": 4,
    "register for": 4,
    "learn more": 3,
    "read more": 3,
    "find out": 2,
    "click here": 3,
    "full story": 3,
    "thank you for": 2,
    "we appreciate": 3,
    "we're grateful": 3,
    "proud to support": 4,
    "proud to partner": 4,
}

NOT_HUMOR_TOKENS = {
    "announcing": 4,
    "congratulations": 3,
    "congratulating": 3,
    "partnerships": 3,
    "shareholders": 5,
    "patients": 3,
    "clinical": 3,
    "pipeline": 2,
    "compliance": 3,
    "regulatory": 4,
    "certification": 3,
}

TYPE_CUES_V2 = {
    "affiliative": {
        "phrases": {
            "tag a friend": 4,
            "tag someone who": 4,
            "tag your friend": 4,
            "send this to": 4,
            "who else": 3,
            "raise your hand": 3,
            "you and your": 3,
            "we all know": 3,
            "y'all know": 3,
            "yall know": 3,
            "the group chat": 4,
            "for the group chat": 4,
            "tell your friends": 3,
            "same energy": 3,
            "same tbh": 3,
            "same lol": 3,
            "this is us": 3,
            "this energy": 3,
            "this is the way": 3,
            "this is giving": 3,
            "everyone say": 3,
            "make everyone laugh": 4,
            "lighten the mood": 4,
            "we love you all": 4,
            "for the culture": 3,
            "squad goals": 3,
            "that feeling when": 3,
            "everyone deserves": 3,
            "can we all agree": 4,
            "us when": 3,
            "we're all": 3,
            "we are all": 3,
            "obsessed with this": 3,
            "can't stop": 2,
            "happy monday": 2,
            "happy friday": 2,
            "case of the mondays": 3,
        },
        "tokens": {
            "bestie": 3,
            "besties": 3,
            "squad": 2,
            "crew": 2,
            "fam": 2,
            "together": 2,
            "everyone": 2,
            "yall": 2,
            "folks": 2,
            "fans": 2,
            "community": 2,
            "relatable": 3,
            "same": 2,
            "vibe": 2,
            "vibes": 2,
            "mood": 2,
        },
        "target_of_humor": "shared_situation",
        "humor_function": "relationship_building",
    },
    "self_enhancing": {
        "phrases": {
            "pov:": 4,
            "point of view": 3,
            "me when": 3,
            "not me": 3,
            "i can't": 3,
            "i cant": 3,
            "no big deal": 3,
            "just sayin": 3,
            "just saying": 2,
            "understood the assignment": 4,
            "ate and left no crumbs": 4,
            "main character energy": 4,
            "main character": 3,
            "we did that": 3,
            "this hits different": 3,
            "hits different": 3,
            "built different": 3,
            "built for this": 3,
            "slaps though": 3,
            "just dropped": 3,
            "we just": 2,
            "my toxic trait": 3,
            "mentally i'm": 3,
            "running on": 3,
            "surviving on": 3,
            "nobody: /": 4,
            "nobody:\n": 4,
            "us:": 3,
            "the brand:": 3,
            "it's giving": 3,
            "we're that": 3,
            "killing it": 3,
            "crushing it": 3,
            "on a roll": 2,
            "at this point": 2,
            "at least we": 2,
            "casual reminder": 3,
            "friendly reminder": 2,
            "your favorite": 2,
            "your fave": 3,
        },
        "tokens": {
            "slay": 3,
            "slaying": 3,
            "iconic": 3,
            "obsessed": 2,
            "legendary": 2,
            "unmatched": 3,
            "elite": 2,
            "premier": 2,
            "chaotic": 2,
            "energy": 2,
            "cope": 2,
            "coping": 2,
            "tired": 2,
            "coffee": 2,
            "surviving": 2,
        },
        "target_of_humor": "self_brand",
        "humor_function": "positive_self_presentation",
    },
    "aggressive": {
        "phrases": {
            "sorry not sorry": 4,
            "not sorry": 3,
            "try again": 3,
            "delete this": 4,
            "sir this is": 4,
            "ma'am this is": 4,
            "we said what we said": 4,
            "you wish": 3,
            "didn't ask": 3,
            "not today": 3,
            "nice try": 3,
            "say less": 3,
            "unlike some": 4,
            "unlike other": 4,
            "the competition": 3,
            "competitor could never": 5,
            "the rest vs": 4,
            "vs the rest": 4,
            "while others": 3,
            "interesting choice": 3,
            "must be nice": 3,
            "sure jan": 4,
            "how about no": 4,
            "hard pass": 3,
            "bold of you": 4,
            "the audacity": 4,
            "we heard you": 2,
            "our response:": 3,
            "you're welcome": 2,
            "we'll wait": 4,
            "call us maybe": 3,
            "we just do it": 3,
            "first. always": 4,
            "nobody does it like": 3,
            "the bar is low": 4,
            "l take": 4,
            "hot take:": 3,
            "ratio": 3,
        },
        "tokens": {
            "roast": 4,
            "roasted": 4,
            "owned": 3,
            "trash": 3,
            "clown": 3,
            "nope": 2,
            "nah": 2,
            "wrong": 2,
            "savage": 3,
            "ratio": 3,
            "cope": 2,
            "dunked": 3,
            "dunking": 3,
            "ridiculous": 2,
            "mock": 2,
        },
        "target_of_humor": "external_target",
        "humor_function": "ridicule_competition",
    },
    "self_defeating": {
        "phrases": {
            "our bad": 4,
            "my bad": 3,
            "we messed": 4,
            "we tried": 4,
            "we failed": 4,
            "we're not okay": 4,
            "we are not okay": 4,
            "why are we like this": 5,
            "send help": 4,
            "not us": 4,
            "help us": 3,
            "we forgot": 3,
            "we can't": 3,
            "we cant": 3,
            "this is awkward": 4,
            "laugh at us": 5,
            "we deserve that": 5,
            "plot twist": 3,
            "didn't go as planned": 4,
            "didn't go according": 4,
            "whoops": 4,
            "it's fine everything is fine": 5,
            "everything is fine": 4,
            "this is fine": 4,
            "we're fine": 3,
            "nobody asked": 3,
            "nobody asked but": 4,
            "don't mind us": 4,
            "we're still": 2,
            "we still don't": 3,
            "accidentally": 3,
            "unintentionally": 3,
            "we didn't mean to": 4,
            "technically this counts": 3,
            "we're learning": 3,
        },
        "tokens": {
            "oops": 4,
            "whoops": 4,
            "awkward": 3,
            "embarrassing": 3,
            "crying": 2,
            "mistake": 2,
            "failed": 2,
            "fail": 2,
            "useless": 3,
            "accidentally": 3,
        },
        "target_of_humor": "self_brand",
        "humor_function": "self_deprecation",
    },
}

SELF_MARKERS = frozenset({"i", "me", "my", "myself", "we", "us", "our", "ourselves"})
SOCIAL_MARKERS = frozenset({"friend", "friends", "bestie", "team", "together", "everyone", "fans", "y'all", "yall", "community"})
ADVERSITY_MARKERS = frozenset({"tired", "stress", "stressed", "hard", "fail", "failed", "mistake", "awkward", "surviving", "cope", "coping", "oops", "whoops"})
OTHER_MARKERS = frozenset({"you", "your", "they", "them", "their", "competitor", "competition", "others", "rivals"})


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def tokenize(text: str) -> list[str]:
    return [t.lower().strip("'") for t in TOKEN_RE.findall(text)]


def score_cues(text_lower: str, tokens: list[str], cue_config: dict) -> tuple[int, list[str]]:
    score = 0
    matches: list[str] = []
    token_set = set(tokens)
    for cue, weight in cue_config.get("phrases", {}).items():
        if cue in text_lower:
            score += weight
            matches.append(cue)
    for cue, weight in cue_config.get("tokens", {}).items():
        if cue in token_set:
            score += weight
            matches.append(cue)
    return score, sorted(set(matches))


def score_not_humor(text_lower: str, tokens: list[str]) -> int:
    score = 0
    token_set = set(tokens)
    for phrase, weight in NOT_HUMOR_PHRASES.items():
        if phrase in text_lower:
            score += weight
    for tok, weight in NOT_HUMOR_TOKENS.items():
        if tok in token_set:
            score += weight
    return score


def infer_fallback(tokens: list[str]) -> tuple[str, str, str]:
    token_set = set(tokens)
    has_social = bool(token_set & SOCIAL_MARKERS)
    has_adversity = bool(token_set & ADVERSITY_MARKERS)
    has_self = bool(token_set & SELF_MARKERS)
    has_other = bool(token_set & OTHER_MARKERS)

    if has_self and has_adversity:
        return "self_defeating", "self_brand", "self_deprecation"
    if has_other and has_adversity:
        return "aggressive", "external_target", "ridicule"
    if has_social:
        return "affiliative", "shared_situation", "relationship_building"
    if has_self:
        return "self_enhancing", "self_brand", "positive_self_presentation"
    return "not_humor", "none", "none"


def classify_v2(text: str) -> dict:
    clean = normalize_text(text)

    if not clean:
        return {
            "label": "not_humor",
            "confidence": 0.90,
            "target_of_humor": "none",
            "humor_function": "none",
            "review_flag": False,
            "reason_code": "empty_text",
        }

    lower = clean.lower()
    tokens = tokenize(clean)

    not_humor_score = score_not_humor(lower, tokens)

    type_scores: dict[str, int] = {}
    type_matches: dict[str, list[str]] = {}
    for label, cue_config in TYPE_CUES_V2.items():
        type_scores[label], type_matches[label] = score_cues(lower, tokens, cue_config)

    best_type = max(type_scores, key=lambda k: type_scores[k])
    best_type_score = type_scores[best_type]

    # Definitive not_humor: strong not_humor signal and no humor cues
    if not_humor_score >= 5 and best_type_score == 0:
        return {
            "label": "not_humor",
            "confidence": min(0.97, 0.70 + 0.03 * not_humor_score),
            "target_of_humor": "none",
            "humor_function": "none",
            "review_flag": False,
            "reason_code": "strong_not_humor_no_humor_cue",
        }

    # No humor cues at all — lean on not_humor or fallback
    if best_type_score == 0:
        if not_humor_score >= 3:
            return {
                "label": "not_humor",
                "confidence": min(0.85, 0.55 + 0.05 * not_humor_score),
                "target_of_humor": "none",
                "humor_function": "none",
                "review_flag": False,
                "reason_code": "moderate_not_humor_no_humor_cue",
            }
        # Fallback to linguistic inference
        label, target, function = infer_fallback(tokens)
        return {
            "label": label,
            "confidence": 0.30,
            "target_of_humor": target,
            "humor_function": function,
            "review_flag": True,
            "reason_code": "no_cue_inferred_from_pronouns",
        }

    # Humor cues present but not_humor signal is strong — contested
    if not_humor_score >= 5 and best_type_score < 4:
        return {
            "label": "ambiguous_review",
            "confidence": 0.40,
            "target_of_humor": TYPE_CUES_V2.get(best_type, {}).get("target_of_humor", "unclear"),
            "humor_function": TYPE_CUES_V2.get(best_type, {}).get("humor_function", "unclear"),
            "review_flag": True,
            "reason_code": "humor_and_not_humor_signals_contested",
        }

    # Rank type candidates
    ranked = sorted(type_scores.items(), key=lambda x: (-x[1], x[0]))
    best_label, best_score = ranked[0]
    second_label, second_score = ranked[1] if len(ranked) > 1 else ("none", 0)

    margin = best_score - second_score

    # Tied or very close — ambiguous
    if margin <= 1 and best_score < 4:
        return {
            "label": "ambiguous_review",
            "confidence": 0.45,
            "target_of_humor": TYPE_CUES_V2.get(best_label, {}).get("target_of_humor", "unclear"),
            "humor_function": TYPE_CUES_V2.get(best_label, {}).get("humor_function", "unclear"),
            "review_flag": True,
            "reason_code": f"tied_between_{best_label}_and_{second_label}",
        }

    # Clear winner — compute confidence
    review_flag = False
    reason_parts = []

    if best_score < 3:
        review_flag = True
        reason_parts.append("low_absolute_score")

    if margin < 2 and best_score < 5:
        review_flag = True
        reason_parts.append("narrow_margin")

    confidence = min(0.95, 0.50 + 0.08 * margin + 0.04 * min(best_score, 8))
    if not_humor_score >= 3:
        confidence *= 0.85
        review_flag = True
        reason_parts.append("mixed_not_humor_signal")
    if review_flag:
        confidence = min(confidence, 0.68)

    reason_code = "clear_winner"
    if reason_parts:
        reason_code = ";".join(reason_parts)

    profile = TYPE_CUES_V2.get(best_label, {})

    return {
        "label": best_label,
        "confidence": round(confidence, 6),
        "target_of_humor": profile.get("target_of_humor", "unclear"),
        "humor_function": profile.get("humor_function", "unclear"),
        "review_flag": review_flag,
        "reason_code": reason_code,
    }


def main():
    parser = argparse.ArgumentParser(
        description="HSQ humor type v2 direct 5-class classifier for brand X posts."
    )
    parser.add_argument("--input", type=Path, required=True, help="Input CSV with global_post_id and text columns")
    parser.add_argument("--output", type=Path, required=True, help="Output CSV path")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input not found: {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    label_counts: dict[str, int] = {}

    with (
        args.input.open(encoding="utf-8-sig", newline="") as f_in,
        args.output.open("w", encoding="utf-8-sig", newline="") as f_out,
    ):
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=V2_OUTPUT_FIELDS)
        writer.writeheader()

        for row in reader:
            text = normalize_text(row.get("text", ""))
            try:
                result = classify_v2(text)
            except Exception as exc:
                result = {
                    "label": "ambiguous_review",
                    "confidence": 0.0,
                    "target_of_humor": "error",
                    "humor_function": "error",
                    "review_flag": True,
                    "reason_code": f"classifier_error:{type(exc).__name__}",
                }

            label = result["label"]
            label_counts[label] = label_counts.get(label, 0) + 1

            writer.writerow({
                "global_post_id": row.get("global_post_id", ""),
                "tweet_id": row.get("tweet_id", ""),
                "sample_group": row.get("sample_group", ""),
                "company_name": row.get("company_name", ""),
                "source_x_handle": row.get("source_x_handle", ""),
                "created_at": row.get("created_at", ""),
                "text": text,
                "v2_humor_label": label,
                "v2_confidence": f"{result['confidence']:.6f}",
                "v2_target_of_humor": result["target_of_humor"],
                "v2_humor_function": result["humor_function"],
                "v2_review_flag": str(result["review_flag"]).lower(),
                "v2_reason_code": result["reason_code"],
            })
            written += 1

    print(f"v2 direct humor type classification completed: {written} rows")
    for label in ["affiliative", "self_enhancing", "aggressive", "self_defeating", "not_humor", "ambiguous_review"]:
        count = label_counts.get(label, 0)
        pct = round(100 * count / written, 2) if written else 0
        print(f"  {label}: {count} ({pct}%)")


if __name__ == "__main__":
    main()
