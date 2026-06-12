import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from x_scrapper.paths import ANALYSIS_OUTPUT_ROOT, DATA_ROOT
from statistics import mean, median
from typing import Any


BRAND_SLUGS = ("wendys", "cocacola", "moonpie")
BRAND_NAMES = {
    "wendys": "Wendy's",
    "cocacola": "Coca-Cola",
    "moonpie": "MoonPie",
}
BRAND_ACCOUNTS = {
    "wendys": "@Wendys",
    "cocacola": "@CocaCola",
    "moonpie": "@MoonPie",
}
OUTPUT_DIR = ANALYSIS_OUTPUT_ROOT
ENGAGEMENT_FIELDS = ("likes", "replies", "retweets", "quotes", "total_engagement")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def as_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def coalesce_number(post: dict[str, Any], keys: tuple[str, ...]) -> float:
    for key in keys:
        if key in post:
            return as_number(post.get(key))
    return 0.0


def normalize_text(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", " ", text)
    text = re.sub(r"[^A-Za-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * pct
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def pearson(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return None
    x_values = [x for x, _ in pairs]
    y_values = [y for _, y in pairs]
    x_mean = mean(x_values)
    y_mean = mean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_denominator = math.sqrt(sum((x - x_mean) ** 2 for x in x_values))
    y_denominator = math.sqrt(sum((y - y_mean) ** 2 for y in y_values))
    if x_denominator == 0 or y_denominator == 0:
        return None
    return numerator / (x_denominator * y_denominator)


def rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[index][1]:
            end += 1
        average_rank = (index + end + 2) / 2
        for original_index, _ in indexed[index : end + 1]:
            ranks[original_index] = average_rank
        index = end + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return None
    return pearson(rank([x for x, _ in pairs]), rank([y for _, y in pairs]))


def compact_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def read_brand_rows(slug: str) -> list[dict[str, Any]]:
    brand_dir = DATA_ROOT / slug
    brand_name = BRAND_NAMES.get(slug, slug)
    source_account = BRAND_ACCOUNTS.get(slug, f"@{slug}")
    posts = load_json(brand_dir / "posts.json", [])
    sentiment_posts = {
        str(item.get("id")): item
        for item in load_json(brand_dir / "zero_shot_sentiment.json", {}).get("posts", [])
        if item.get("id")
    }
    humor_posts = {
        str(item.get("id")): item
        for item in load_json(brand_dir / "hsq_humor_classification.json", {}).get("posts", [])
        if item.get("id")
    }
    lda = load_json(brand_dir / "lda_topics.json", {})
    topic_terms = {
        int(topic.get("topic_id", -1)): [str(term).lower() for term in topic.get("top_terms", [])]
        for topic in lda.get("topics", [])
    }

    raw_rows: list[dict[str, Any]] = []
    engagements: list[float] = []
    for post in posts:
        post_id = str(post.get("id") or "")
        text = str(post.get("text") or "")
        likes = coalesce_number(post, ("likes", "like_count", "favorite_count"))
        replies = coalesce_number(post, ("replies", "reply_count"))
        retweets = coalesce_number(post, ("retweets", "retweet_count", "reposts"))
        quotes = coalesce_number(post, ("quotes", "quote_count"))
        total_engagement = likes + replies + retweets + quotes
        engagements.append(total_engagement)

        sentiment = sentiment_posts.get(post_id, {})
        humor = humor_posts.get(post_id, {})
        cleaned = normalize_text(text)
        topic_id, topic_score = infer_topic(cleaned, topic_terms)

        raw_rows.append(
            {
                "brand": brand_name,
                "brand_slug": slug,
                "source_account": str(post.get("source_account") or post.get("screen_name") or source_account),
                "post_id": post_id,
                "tweet_url": post.get("tweet_url") or post.get("url") or "",
                "created_at": post.get("created_at") or post.get("date") or post.get("timestamp") or "",
                "text": text,
                "likes": int(likes),
                "replies": int(replies),
                "retweets": int(retweets),
                "quotes": int(quotes),
                "total_engagement": int(total_engagement),
                "log_total_engagement": math.log1p(total_engagement),
                "text_length": len(text),
                "word_count": word_count(text),
                "has_url": int(bool(re.search(r"https?://|www\.", text))),
                "hashtag_count": len(re.findall(r"(?<!\w)#\w+", text)),
                "mention_count": len(re.findall(r"(?<!\w)@\w+", text)),
                "sentiment_label": sentiment.get("top_label") or "",
                "sentiment_score": as_number(sentiment.get("top_score")),
                "humor_type": humor.get("top_label") or "",
                "humor_score": as_number(humor.get("top_score")),
                "topic_id": topic_id,
                "topic_score": topic_score,
            }
        )

    threshold = percentile(engagements, 0.95)
    for row in raw_rows:
        row["is_viral"] = int(row["total_engagement"] >= threshold) if engagements else 0
        row["viral_threshold_brand_p95"] = threshold
    return raw_rows


def infer_topic(cleaned_text: str, topic_terms: dict[int, list[str]]) -> tuple[str, float]:
    if not cleaned_text or not topic_terms:
        return "", 0.0
    best_topic = ""
    best_score = 0.0
    words = set(cleaned_text.split())
    for topic_id, terms in topic_terms.items():
        score = 0.0
        for term in terms:
            term_words = term.split()
            if len(term_words) == 1 and term_words[0] in words:
                score += 1.0
            elif len(term_words) > 1 and term in cleaned_text:
                score += 1.5
        if score > best_score:
            best_topic = str(topic_id)
            best_score = score
    return best_topic, best_score


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def group_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    return groups


def summarize_engagement(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row["total_engagement"]) for row in rows]
    return {
        "post_count": len(rows),
        "share": len(rows),
        "average_engagement": mean(values) if values else 0.0,
        "median_engagement": median(values) if values else 0.0,
        "p75_engagement": percentile(values, 0.75),
        "p90_engagement": percentile(values, 0.90),
        "max_engagement": max(values) if values else 0.0,
    }


def build_table4(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = max(1, len(rows))
    table = []
    for (humor_type, sentiment_label), group in sorted(group_rows(rows, ("humor_type", "sentiment_label")).items()):
        if not humor_type or not sentiment_label:
            continue
        summary = summarize_engagement(group)
        table.append(
            {
                "humor_type": humor_type,
                "sentiment_label": sentiment_label,
                "post_count": summary["post_count"],
                "share": summary["post_count"] / total,
                "average_engagement": summary["average_engagement"],
                "median_engagement": summary["median_engagement"],
                "average_humor_score": mean([row["humor_score"] for row in group]) if group else 0.0,
                "average_sentiment_score": mean([row["sentiment_score"] for row in group]) if group else 0.0,
            }
        )
    return table


def build_table5(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = max(1, len(rows))
    table = []
    for (humor_type,), group in sorted(group_rows(rows, ("humor_type",)).items()):
        if not humor_type:
            continue
        summary = summarize_engagement(group)
        table.append(
            {
                "humor_type": humor_type,
                "post_count": summary["post_count"],
                "share": summary["post_count"] / total,
                "average_engagement": summary["average_engagement"],
                "median_engagement": summary["median_engagement"],
                "p75_engagement": summary["p75_engagement"],
                "p90_engagement": summary["p90_engagement"],
                "max_engagement": summary["max_engagement"],
                "average_humor_score": mean([row["humor_score"] for row in group]) if group else 0.0,
            }
        )
    return table


def build_correlations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = sorted({row["sentiment_label"] for row in rows if row.get("sentiment_label")})
    humor_types = sorted({row["humor_type"] for row in rows if row.get("humor_type")})
    variables: dict[str, list[float]] = {
        "likes": [row["likes"] for row in rows],
        "replies": [row["replies"] for row in rows],
        "retweets": [row["retweets"] for row in rows],
        "quotes": [row["quotes"] for row in rows],
        "total_engagement": [row["total_engagement"] for row in rows],
        "log_total_engagement": [row["log_total_engagement"] for row in rows],
        "text_length": [row["text_length"] for row in rows],
        "word_count": [row["word_count"] for row in rows],
        "has_url": [row["has_url"] for row in rows],
        "hashtag_count": [row["hashtag_count"] for row in rows],
        "mention_count": [row["mention_count"] for row in rows],
        "sentiment_score": [row["sentiment_score"] for row in rows],
        "humor_score": [row["humor_score"] for row in rows],
        "topic_score": [row["topic_score"] for row in rows],
        "is_viral": [row["is_viral"] for row in rows],
    }
    for label in labels:
        variables[f"sentiment_{slugify(label)}"] = [1.0 if row["sentiment_label"] == label else 0.0 for row in rows]
    for humor_type in humor_types:
        variables[f"humor_{slugify(humor_type)}"] = [1.0 if row["humor_type"] == humor_type else 0.0 for row in rows]

    correlations = []
    names = list(variables)
    for i, var_a in enumerate(names):
        for var_b in names[i + 1 :]:
            correlations.append(
                {
                    "variable_a": var_a,
                    "variable_b": var_b,
                    "pearson_r": pearson(variables[var_a], variables[var_b]),
                    "spearman_rho": spearman(variables[var_a], variables[var_b]),
                    "n": len(rows),
                }
            )
    return correlations


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def build_sampling_audit(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates = sorted(
        rows,
        key=lambda row: (
            min(nonzero(row["sentiment_score"]), nonzero(row["humor_score"])),
            -row["is_viral"],
            -row["total_engagement"],
        ),
    )

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    strata = [
        ("low_confidence", lambda row: row["sentiment_score"] < 0.45 or row["humor_score"] < 0.45),
        ("viral", lambda row: bool(row["is_viral"])),
        ("non_dominant_humor", lambda row: row["humor_type"] != "Self-enhancing humor"),
    ]
    per_stratum = max(5, limit // max(1, len(strata)))
    for reason, predicate in strata:
        count = 0
        for row in candidates:
            if count >= per_stratum:
                break
            if row["post_id"] in seen or not predicate(row):
                continue
            selected.append({**audit_row(row), "audit_reason": reason})
            seen.add(row["post_id"])
            count += 1

    for row in candidates:
        if len(selected) >= limit:
            break
        if row["post_id"] in seen:
            continue
        selected.append({**audit_row(row), "audit_reason": "fill"})
        seen.add(row["post_id"])
    return selected[:limit]


def nonzero(value: float) -> float:
    return value if value > 0 else 1.0


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand": row["brand"],
        "post_id": row["post_id"],
        "created_at": row["created_at"],
        "tweet_url": row["tweet_url"],
        "text": row["text"],
        "sentiment_label": row["sentiment_label"],
        "sentiment_score": row["sentiment_score"],
        "humor_type": row["humor_type"],
        "humor_score": row["humor_score"],
        "total_engagement": row["total_engagement"],
        "is_viral": row["is_viral"],
        "human_sentiment_label": "",
        "human_humor_type": "",
        "human_notes": "",
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(rows: list[dict[str, Any]], table4: list[dict[str, Any]], table5: list[dict[str, Any]], correlations: list[dict[str, Any]]) -> None:
    top_correlations = sorted(
        [row for row in correlations if row["pearson_r"] is not None],
        key=lambda row: abs(row["pearson_r"]),
        reverse=True,
    )[:15]
    brand_counts = Counter(row["brand"] for row in rows)
    lines = [
        "# Research Export Summary",
        "",
        "## Joined Dataset",
        "",
    ]
    for brand, count in brand_counts.most_common():
        lines.append(f"- {brand}: {count} posts")
    lines.extend(
        [
            f"- Total: {len(rows)} posts",
            "",
            "## Table 4: Humor x Sentiment x Engagement",
            "",
            "| Humor Type | Sentiment | Posts | Share | Avg Engagement | Median Engagement | Avg Humor Score | Avg Sentiment Score |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in table4:
        lines.append(
            f"| {row['humor_type']} | {row['sentiment_label']} | {row['post_count']} | "
            f"{row['share']:.3f} | {row['average_engagement']:.2f} | {row['median_engagement']:.2f} | "
            f"{row['average_humor_score']:.3f} | {row['average_sentiment_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Table 5: Engagement Robustness by Humor Type",
            "",
            "| Humor Type | Posts | Share | Avg Engagement | Median | P75 | P90 | Max | Avg Humor Score |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in table5:
        lines.append(
            f"| {row['humor_type']} | {row['post_count']} | {row['share']:.3f} | "
            f"{row['average_engagement']:.2f} | {row['median_engagement']:.2f} | "
            f"{row['p75_engagement']:.2f} | {row['p90_engagement']:.2f} | "
            f"{row['max_engagement']:.2f} | {row['average_humor_score']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Strongest Pearson Correlations",
            "",
            "| Variable A | Variable B | Pearson r | Spearman rho | N |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in top_correlations:
        lines.append(
            f"| {row['variable_a']} | {row['variable_b']} | {compact_float(row['pearson_r'])} | "
            f"{compact_float(row['spearman_rho'])} | {row['n']} |"
        )
    lines.extend(
        [
            "",
            "## Topic Assignment Note",
            "",
            "Post-level `topic_id` is inferred from saved LDA top terms because the existing LDA output stores representative posts but not a full document-topic matrix. Use this as a descriptive topic proxy unless the LDA export is extended to persist full post-level topic probabilities.",
        ]
    )
    (OUTPUT_DIR / "research_export_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export paper-facing joined tables from brand analysis outputs.")
    parser.add_argument("--brands", default=",".join(BRAND_SLUGS), help="Comma-separated brand slugs to export.")
    parser.add_argument("--audit-limit", type=int, default=150, help="Maximum sampling audit candidate rows.")
    args = parser.parse_args()

    brand_slugs = [slugify(item) for item in args.brands.split(",") if item.strip()]
    rows: list[dict[str, Any]] = []
    for slug in brand_slugs:
        rows.extend(read_brand_rows(slug))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joined_fields = [
        "brand",
        "brand_slug",
        "source_account",
        "post_id",
        "tweet_url",
        "created_at",
        "text",
        "likes",
        "replies",
        "retweets",
        "quotes",
        "total_engagement",
        "log_total_engagement",
        "text_length",
        "word_count",
        "has_url",
        "hashtag_count",
        "mention_count",
        "sentiment_label",
        "sentiment_score",
        "humor_type",
        "humor_score",
        "topic_id",
        "topic_score",
        "is_viral",
        "viral_threshold_brand_p95",
    ]
    write_csv(OUTPUT_DIR / "joined_posts.csv", rows, joined_fields)
    write_json(OUTPUT_DIR / "joined_posts.json", rows)

    table4 = build_table4(rows)
    table5 = build_table5(rows)
    correlations = build_correlations(rows)
    audit_candidates = build_sampling_audit(rows, args.audit_limit)

    write_csv(
        OUTPUT_DIR / "table4_humor_sentiment_engagement.csv",
        table4,
        [
            "humor_type",
            "sentiment_label",
            "post_count",
            "share",
            "average_engagement",
            "median_engagement",
            "average_humor_score",
            "average_sentiment_score",
        ],
    )
    write_json(OUTPUT_DIR / "table4_humor_sentiment_engagement.json", table4)
    write_csv(
        OUTPUT_DIR / "table5_engagement_robustness_by_humor.csv",
        table5,
        [
            "humor_type",
            "post_count",
            "share",
            "average_engagement",
            "median_engagement",
            "p75_engagement",
            "p90_engagement",
            "max_engagement",
            "average_humor_score",
        ],
    )
    write_json(OUTPUT_DIR / "table5_engagement_robustness_by_humor.json", table5)
    write_csv(
        OUTPUT_DIR / "correlation_coefficients.csv",
        [
            {**row, "pearson_r": compact_float(row["pearson_r"]), "spearman_rho": compact_float(row["spearman_rho"])}
            for row in correlations
        ],
        ["variable_a", "variable_b", "pearson_r", "spearman_rho", "n"],
    )
    write_json(OUTPUT_DIR / "correlation_coefficients.json", correlations)
    write_csv(
        OUTPUT_DIR / "sampling_audit_candidates.csv",
        audit_candidates,
        [
            "audit_reason",
            "brand",
            "post_id",
            "created_at",
            "tweet_url",
            "text",
            "sentiment_label",
            "sentiment_score",
            "humor_type",
            "humor_score",
            "total_engagement",
            "is_viral",
            "human_sentiment_label",
            "human_humor_type",
            "human_notes",
        ],
    )
    write_json(OUTPUT_DIR / "sampling_audit_candidates.json", audit_candidates)
    write_report(rows, table4, table5, correlations)
    print(f"Exported {len(rows)} joined rows to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
