"""Apply the provisional H1 presence-only classifier to the integrated corpus.

This fits the already selected batch1-only model specification and applies it
to already-collected posts. It does not perform model search, type/aggressive
classification, full H1 regression, or H2/H3 analysis.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


ROOT = Path(__file__).resolve().parents[5]
CI = ROOT / "20260618expand" / "classifier_improvement"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"
OUT_BASE = CI / "h1_presence_only" / "integrated_collected_corpus"
DATA_DIR = OUT_BASE / "data"

IN_CORPUS = DATA_DIR / "integrated_collected_post_corpus.csv"
OUT_POSTS = DATA_DIR / "integrated_h1_presence_classified_posts.csv"
OUT_SUMMARY = DATA_DIR / "integrated_h1_presence_classification_summary.csv"
OUT_SOURCE = DATA_DIR / "integrated_h1_presence_by_source_summary.csv"
OUT_FIRM = DATA_DIR / "integrated_h1_presence_by_firm_summary.csv"

CODERS = ["coder1", "coder2", "coder3"]
KOR_PRESENCE = "유머_존재여부"
KOR_TEXT = "본문"
MODEL_ID = "word_char_comb__lr_liblin_C01"
TRAIN_SCOPE = "batch1_only"
STATUS = "provisional_h1_presence_only"
RANDOM_STATE = 42

ADD_COLS = [
    "h1_humor_presence_probability",
    "h1_humor_presence_pred_t40",
    "h1_humor_presence_pred_t50",
    "h1_humor_presence_pred_t60",
    "h1_classifier_model",
    "h1_classifier_training_scope",
    "h1_classifier_status",
]


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text or "")
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("vec", FeatureUnion([
            ("word", TfidfVectorizer(
                analyzer="word", ngram_range=(1, 2), max_features=5000,
                min_df=2, max_df=0.95, sublinear_tf=True,
            )),
            ("char", TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), max_features=5000,
                min_df=2, max_df=0.95, sublinear_tf=True,
            )),
        ])),
        ("clf", LogisticRegression(
            solver="liblinear", C=0.1, class_weight="balanced",
            max_iter=2000, random_state=RANDOM_STATE,
        )),
    ])


def load_training_data() -> tuple[list[str], list[int]]:
    texts, labels = [], []
    for coder in CODERS:
        path = SPLITS_DIR / f"{coder}_labeling_template.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                label = row.get(KOR_PRESENCE, "").strip()
                if label not in {"0", "1"}:
                    continue
                texts.append(preprocess(row.get(KOR_TEXT, "")))
                labels.append(1 if label == "1" else 0)
    dist = Counter(labels)
    if len(labels) != 1482 or dist[1] != 648 or dist[0] != 834:
        raise RuntimeError(f"Unexpected batch1 labels: n={len(labels)} dist={dist}")
    return texts, labels


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def threshold(prob: float | None, value: float) -> str:
    if prob is None or np.isnan(prob):
        return ""
    return "1" if prob >= value else "0"


def fnum(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize(rows: list[dict[str, str]]) -> dict[str, str]:
    probs = [fnum(row["h1_humor_presence_probability"]) for row in rows if row["h1_humor_presence_probability"] != ""]
    classified = len(probs)
    total = len(rows)
    n40 = sum(1 for row in rows if row["h1_humor_presence_pred_t40"] == "1")
    n50 = sum(1 for row in rows if row["h1_humor_presence_pred_t50"] == "1")
    n60 = sum(1 for row in rows if row["h1_humor_presence_pred_t60"] == "1")
    return {
        "total_posts": str(total),
        "classified_posts": str(classified),
        "missing_text_posts": str(sum(1 for row in rows if row.get("missing_text") == "1")),
        "missing_date_posts": str(sum(1 for row in rows if row.get("missing_date") == "1")),
        "mean_humor_probability": str(round(float(np.mean(probs)), 6)) if probs else "",
        "humor_rate_t40": str(round(n40 / classified, 6)) if classified else "",
        "humor_rate_t50": str(round(n50 / classified, 6)) if classified else "",
        "humor_rate_t60": str(round(n60 / classified, 6)) if classified else "",
        "n_humor_t40": str(n40),
        "n_humor_t50": str(n50),
        "n_humor_t60": str(n60),
        "n_non_humor_t40": str(classified - n40),
        "n_non_humor_t50": str(classified - n50),
        "n_non_humor_t60": str(classified - n60),
    }


def main() -> None:
    train_texts, train_labels = load_training_data()
    pipe = build_pipeline()
    pipe.fit(train_texts, train_labels)

    fieldnames, rows = read_csv(IN_CORPUS)
    texts, valid_indices = [], []
    for idx, row in enumerate(rows):
        text = row.get("text", "").strip()
        if text:
            valid_indices.append(idx)
            texts.append(preprocess(text))

    probs = np.full(len(rows), np.nan)
    if texts:
        predicted = pipe.predict_proba(texts)[:, 1]
        for idx, prob in zip(valid_indices, predicted):
            probs[idx] = float(prob)

    for idx, row in enumerate(rows):
        prob = probs[idx]
        row["h1_humor_presence_probability"] = "" if np.isnan(prob) else str(round(float(prob), 6))
        row["h1_humor_presence_pred_t40"] = threshold(prob, 0.40)
        row["h1_humor_presence_pred_t50"] = threshold(prob, 0.50)
        row["h1_humor_presence_pred_t60"] = threshold(prob, 0.60)
        row["h1_classifier_model"] = MODEL_ID
        row["h1_classifier_training_scope"] = TRAIN_SCOPE
        row["h1_classifier_status"] = STATUS

    out_fields = fieldnames + [col for col in ADD_COLS if col not in fieldnames]
    with OUT_POSTS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    summary.update({
        "n_source_datasets": str(len({row["source_dataset"] for row in rows})),
        "n_companies": str(len({row["company_name"] for row in rows if row["company_name"]})),
        "min_date": min([row["date"] for row in rows if row["date"]], default=""),
        "max_date": max([row["date"] for row in rows if row["date"]], default=""),
        "classifier_model": MODEL_ID,
        "classifier_training_scope": TRAIN_SCOPE,
        "classifier_status": STATUS,
        "oof_auc_reference": "0.7811",
        "oof_f1_reference": "0.6792",
        "firm_held_out_f1_reference": "0.4770",
    })
    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)

    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_firm: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row["source_dataset"]].append(row)
        by_firm[(row["company_name"], row["source_dataset"], row["source_x_handle"])].append(row)

    source_fields = [
        "source_dataset", "total_posts", "classified_posts", "missing_text_posts",
        "missing_date_posts", "mean_humor_probability", "humor_rate_t40",
        "humor_rate_t50", "humor_rate_t60", "n_humor_t50", "n_non_humor_t50",
    ]
    with OUT_SOURCE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=source_fields)
        writer.writeheader()
        for source, group in sorted(by_source.items()):
            item = summarize(group)
            writer.writerow({field: source if field == "source_dataset" else item.get(field, "") for field in source_fields})

    firm_fields = [
        "company_name", "source_dataset", "source_x_handle", "total_posts",
        "mean_humor_probability", "humor_rate_t40", "humor_rate_t50",
        "humor_rate_t60", "n_humor_t50", "n_non_humor_t50", "missing_text_posts",
    ]
    with OUT_FIRM.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=firm_fields)
        writer.writeheader()
        for (company, source, handle), group in sorted(by_firm.items()):
            item = summarize(group)
            writer.writerow({
                "company_name": company,
                "source_dataset": source,
                "source_x_handle": handle,
                **{field: item.get(field, "") for field in firm_fields if field not in {"company_name", "source_dataset", "source_x_handle"}},
            })

    print("Integrated H1 presence classifier applied")
    print(f"rows={len(rows)}")
    print(f"classified={summary['classified_posts']}")
    print(f"missing_text={summary['missing_text_posts']}")
    print(f"humor_rate_t50={summary['humor_rate_t50']}")


if __name__ == "__main__":
    main()
