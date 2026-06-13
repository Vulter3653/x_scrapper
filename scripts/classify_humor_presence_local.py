#!/usr/bin/env python3
"""Local humor presence classifier using rules plus TF-IDF logistic regression."""

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
except ModuleNotFoundError:
    TfidfVectorizer = None
    LogisticRegression = None
    Pipeline = None


OUTPUT_FIELDS = [
    "global_post_id",
    "tweet_id",
    "sample_group",
    "company_name",
    "text",
    "humor_presence",
    "confidence_score",
    "evidence_phrase",
    "classification_rationale",
    "needs_manual_review",
    "manual_review_reason",
    "decision_source",
    "model_name",
    "prompt_version",
    "classification_status",
    "classified_at",
    "error_type",
    "error_message",
    "ml_humor_probability",
    "rule_label",
    "rule_evidence",
]

URL_RE = re.compile(r"https?://\S+|www\.\S+|\b\S+\.(?:com|org|net|io|co)\S*", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


class StdlibTfidfLogReg:
    """Small binary TF-IDF logistic regression fallback for restricted envs."""

    def __init__(self, max_iter=300, learning_rate=0.4, l2=0.001):
        self.max_iter = max_iter
        self.learning_rate = learning_rate
        self.l2 = l2
        self.vocabulary = {}
        self.idf = []
        self.weights = []
        self.bias = 0.0

    def _terms(self, text):
        tokens = [token.lower() for token in TOKEN_RE.findall(text)]
        terms = list(tokens)
        terms.extend(f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1))
        return terms

    def _fit_vocabulary(self, texts):
        df = Counter()
        for text in texts:
            df.update(set(self._terms(text)))
        self.vocabulary = {term: idx for idx, (term, _) in enumerate(sorted(df.items()))}
        n_docs = max(len(texts), 1)
        self.idf = [0.0] * len(self.vocabulary)
        for term, idx in self.vocabulary.items():
            self.idf[idx] = math.log((1.0 + n_docs) / (1.0 + df[term])) + 1.0

    def _vectorize_one(self, text):
        counts = Counter(term for term in self._terms(text) if term in self.vocabulary)
        if not counts:
            return {}
        total = sum(counts.values())
        vector = {}
        norm = 0.0
        for term, count in counts.items():
            idx = self.vocabulary[term]
            value = (count / total) * self.idf[idx]
            vector[idx] = value
            norm += value * value
        norm = math.sqrt(norm) or 1.0
        return {idx: value / norm for idx, value in vector.items()}

    @staticmethod
    def _sigmoid(score):
        if score >= 0:
            z = math.exp(-score)
            return 1.0 / (1.0 + z)
        z = math.exp(score)
        return z / (1.0 + z)

    def fit(self, texts, labels):
        self._fit_vocabulary(texts)
        vectors = [self._vectorize_one(text) for text in texts]
        y = [1.0 if label == "humor" else 0.0 for label in labels]
        self.weights = [0.0] * len(self.vocabulary)
        self.bias = 0.0
        positives = sum(y) or 1.0
        negatives = (len(y) - sum(y)) or 1.0
        class_weights = {1.0: len(y) / (2.0 * positives), 0.0: len(y) / (2.0 * negatives)}

        for _ in range(self.max_iter):
            grad = [0.0] * len(self.weights)
            bias_grad = 0.0
            for vector, target in zip(vectors, y):
                score = self.bias + sum(self.weights[idx] * value for idx, value in vector.items())
                error = (self._sigmoid(score) - target) * class_weights[target]
                bias_grad += error
                for idx, value in vector.items():
                    grad[idx] += error * value
            scale = 1.0 / max(len(y), 1)
            self.bias -= self.learning_rate * bias_grad * scale
            for idx in range(len(self.weights)):
                penalty = self.l2 * self.weights[idx]
                self.weights[idx] -= self.learning_rate * ((grad[idx] * scale) + penalty)

    def humor_probability(self, text):
        vector = self._vectorize_one(text)
        score = self.bias + sum(self.weights[idx] * value for idx, value in vector.items())
        return self._sigmoid(score)


def load_cues(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def find_cue(text_lower, cues):
    for cue in cues:
        if cue.lower() in text_lower:
            return cue
    return ""


def token_count(text):
    return len(TOKEN_RE.findall(text))


def is_url_dominant(text, cues):
    if not text:
        return False
    url_chars = sum(len(match.group(0)) for match in URL_RE.finditer(text))
    if url_chars / max(len(text), 1) >= float(cues.get("url_dominant_min_url_share", 0.35)):
        return True
    lowered = text.lower()
    return bool(URL_RE.search(text) and find_cue(lowered, cues.get("strong_non_humor_cues", [])))


def rule_decision(text, cues):
    clean = normalize_text(text)
    lowered = clean.lower()
    if not clean:
        return "non_humor", "empty_text", "Empty text is classified as non_humor."

    if is_url_dominant(clean, cues):
        return "non_humor", "url_or_notice_dominant", "URL/notice-dominant text is classified as non_humor."

    humor_cue = find_cue(lowered, cues.get("strong_humor_cues", []))
    non_humor_cue = find_cue(lowered, cues.get("strong_non_humor_cues", []))
    if humor_cue and not non_humor_cue:
        return "humor", humor_cue, "Strong humor cue without a strong non-humor cue."
    if non_humor_cue and not humor_cue:
        return "non_humor", non_humor_cue, "Strong non-humor cue without a strong humor cue."
    if humor_cue and non_humor_cue:
        return "ambiguous", f"{humor_cue} | {non_humor_cue}", "Humor and non-humor cues conflict."

    if token_count(clean) <= int(cues.get("short_text_max_tokens", 3)):
        context_cue = find_cue(lowered, cues.get("context_dependent_cues", []))
        evidence = context_cue or clean
        return "ambiguous", evidence, "Text is too short or context-dependent for a confident local decision."

    return "", "", ""


def load_training_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Training seed file not found: {path}")
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            label = row.get("humor_presence_seed_label", "")
            text = normalize_text(row.get("text", ""))
            if label in {"humor", "non_humor"} and text:
                rows.append((text, label))
    return rows


def train_model(seed_path):
    rows = load_training_rows(seed_path)
    label_counts = {label: sum(1 for _, row_label in rows if row_label == label) for label in {"humor", "non_humor"}}
    if min(label_counts.values() or [0]) < 2:
        raise ValueError(f"Need at least two seed rows for each binary class; got {label_counts}")
    if Pipeline is None:
        model = StdlibTfidfLogReg()
        model.fit([text for text, _ in rows], [label for _, label in rows])
        return model, label_counts

    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.95,
                    strip_accents="unicode",
                ),
            ),
            (
                "logreg",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit([text for text, _ in rows], [label for _, label in rows])
    return model, label_counts


def humor_probability(model, text):
    if hasattr(model, "humor_probability"):
        return float(model.humor_probability(text))
    classes = list(model.named_steps["logreg"].classes_)
    probabilities = model.predict_proba([text])[0]
    return float(probabilities[classes.index("humor")])


def final_decision(text, cues, model):
    clean = normalize_text(text)
    rule_label, rule_evidence, rule_reason = rule_decision(clean, cues)
    if not clean:
        return rule_label, 1.0, rule_evidence, rule_reason, False, "", 0.0, rule_label, rule_evidence, "rule"

    probability = humor_probability(model, clean)
    humor_threshold = float(cues.get("ml_humor_threshold", 0.70))
    non_humor_threshold = float(cues.get("ml_non_humor_threshold", 0.30))
    if probability >= humor_threshold:
        ml_label = "humor"
        ml_confidence = probability
    elif probability <= non_humor_threshold:
        ml_label = "non_humor"
        ml_confidence = 1.0 - probability
    else:
        ml_label = "ambiguous"
        ml_confidence = max(probability, 1.0 - probability)

    if rule_label in {"humor", "non_humor"} and ml_label in {"humor", "non_humor"} and rule_label != ml_label:
        return (
            "ambiguous",
            ml_confidence,
            rule_evidence,
            f"Rule label {rule_label} conflicts with ML label {ml_label}.",
            True,
            "rule_ml_conflict",
            probability,
            rule_label,
            rule_evidence,
            "rule_ml_conflict",
        )

    if rule_label:
        needs_review = rule_label == "ambiguous"
        review_reason = "rule_ambiguous" if needs_review else ""
        return rule_label, ml_confidence, rule_evidence, rule_reason, needs_review, review_reason, probability, rule_label, rule_evidence, "rule"

    needs_review = ml_label == "ambiguous"
    review_reason = "ml_probability_between_thresholds" if needs_review else ""
    rationale = f"Local TF-IDF logistic regression humor probability={probability:.3f}."
    return ml_label, ml_confidence, "", rationale, needs_review, review_reason, probability, "", "", "ml"


def read_processed_ids(path):
    if not path.exists():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row.get("global_post_id", "") for row in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-seed", type=Path, default=Path("data/derived/humor/humor_presence_training_seed.csv"))
    parser.add_argument("--cues", type=Path, default=Path("config/humor_presence_rule_cues.json"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cues = load_cues(args.cues)
    model, label_counts = train_model(args.training_seed)
    print(f"Trained local classifier from {args.training_seed}: {label_counts}")

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    processed_ids = read_processed_ids(args.output) if args.resume else set()
    write_header = not args.resume or not args.output.exists()
    written = 0

    with args.input.open(encoding="utf-8-sig", newline="") as f_in, args.output.open(
        "a" if args.resume else "w", encoding="utf-8-sig", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=OUTPUT_FIELDS)
        if write_header:
            writer.writeheader()
        for row in reader:
            global_post_id = row.get("global_post_id", "")
            if global_post_id in processed_ids:
                continue
            if args.limit is not None and written >= args.limit:
                break
            
            # Text fallback mapping
            text = row.get("text") or row.get("full_text") or row.get("content") or row.get("body") or ""
            
            try:
                label, confidence, evidence, rationale, needs_review, review_reason, probability, rule_label, rule_evidence, source = final_decision(
                    text, cues, model
                )
                status = "classified"
                error_type = ""
                error_message = ""
            except Exception as exc:
                label = "ambiguous"
                confidence = 0.0
                evidence = ""
                rationale = ""
                needs_review = True
                review_reason = "local_classifier_error"
                probability = 0.5
                rule_label = ""
                rule_evidence = ""
                source = "error"
                status = "failed"
                error_type = type(exc).__name__
                error_message = str(exc)

            writer.writerow(
                {
                    "global_post_id": global_post_id,
                    "tweet_id": row.get("tweet_id", ""),
                    "sample_group": row.get("sample_group", ""),
                    "company_name": row.get("company_name", ""),
                    "text": normalize_text(text),
                    "humor_presence": label,
                    "confidence_score": f"{confidence:.6f}",
                    "evidence_phrase": evidence,
                    "classification_rationale": rationale,
                    "needs_manual_review": str(bool(needs_review)).lower(),
                    "manual_review_reason": review_reason,
                    "decision_source": source,
                    "model_name": "local_tfidf_logreg_humor_presence_v1",
                    "prompt_version": "local-rules-v1.0.1",
                    "classification_status": status,
                    "classified_at": datetime.now(timezone.utc).isoformat(),
                    "error_type": error_type,
                    "error_message": error_message,
                    "ml_humor_probability": f"{probability:.6f}",
                    "rule_label": rule_label,
                    "rule_evidence": rule_evidence,
                }
            )
            written += 1

    print(f"Local humor presence classification completed for {written} rows.")


if __name__ == "__main__":
    main()
