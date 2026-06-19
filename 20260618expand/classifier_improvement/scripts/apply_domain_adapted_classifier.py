"""
apply_domain_adapted_classifier.py

Applies the domain-adapted classifier to all 65,245 Fortune Top 100 posts.
Requires: validated human labels (template with completed reviews).
This script should only be run after:
  1. Human labeling is complete (>=500 presence labels, >=200 typed humor labels)
  2. train_domain_adapted_humor_presence_classifier.py PASS
  3. train_domain_adapted_humor_type_classifier.py PASS

Generates:
  data/classified/fortune100_domain_adapted_humor_classification.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
TEMPLATE = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
TRANSFER = ROOT / "20260618expand" / "model_transfer" / "data" / "classified" / "fortune100_wendys_model_humor_classification.csv"

OUT_CLASSIFIED = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"
OUT_COMPARISON = CI / "results" / "domain_transfer_comparison.csv"

CLASSES_TYPE = ["aggressive", "affiliative", "self_enhancing", "self_defeating"]
# Numeric coding: 0=non_humor, 1=humor, 2=uncertain
VALID_PRESENCE = {"0", "1"}
# Numeric type coding: 1=aggressive, 2=affiliative, 3=self_enhancing, 4=self_defeating
TYPE_CODE_TO_LABEL = {
    "1": "aggressive",
    "2": "affiliative",
    "3": "self_enhancing",
    "4": "self_defeating",
}
VALID_TYPES = set(TYPE_CODE_TO_LABEL.keys())
RANDOM_STATE = 42

# No abstention: classify all posts deterministically (argmax at p=0.5)
PRESENCE_THRESHOLD = 0.50
TYPE_ABSTENTION = 0.0  # always use argmax

CLASSIFIER_NAME = "fortune100_domain_adapted_tfidf_logreg"
CLASSIFIER_VERSION = "v1_trained_on_fortune100_human_labels"


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<MENTION>", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true",
                        help="Apply to first 500 posts only")
    parser.add_argument("--min-presence-labels", type=int, default=200,
                        help="Minimum human presence labels required to run")
    parser.add_argument("--template", type=Path, default=None,
                        help="Path to labeled template CSV (default: batch1 master)")
    parser.add_argument("--input", type=Path, default=None,
                        help="Corpus to classify (default: fortune100_post_master). "
                             "Also accepts integrated_h1_presence_classified_posts.csv "
                             "(68,039 rows)")
    args = parser.parse_args()

    template_path = args.template if args.template else TEMPLATE

    print("=== apply_domain_adapted_classifier ===")

    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}")
        raise SystemExit(1)

    print(f"  Template: {template_path.name}")
    with open(template_path, newline="", encoding="utf-8") as f:
        template_rows = list(csv.DictReader(f))

    labeled_presence = [r for r in template_rows
                        if r.get("human_humor_presence", "").strip() in VALID_PRESENCE]
    labeled_type = [r for r in template_rows
                    if r.get("human_humor_presence", "").strip() == "1"
                    and r.get("human_humor_type", "").strip() in VALID_TYPES]

    print(f"  Presence labels: {len(labeled_presence)}")
    print(f"  Type labels: {len(labeled_type)}")

    if len(labeled_presence) < args.min_presence_labels:
        print(f"ERROR: fewer than {args.min_presence_labels} presence labels. "
              f"Complete human labeling first.")
        raise SystemExit(1)

    # Train presence classifier
    print("\n  Training domain-adapted presence classifier...")
    texts_bin = [preprocess(r["text"]) for r in labeled_presence]
    labels_bin = [1 if r["human_humor_presence"].strip() == "1" else 0
                  for r in labeled_presence]

    bin_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2),
            min_df=2, max_df=0.95, sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced", solver="liblinear",
            max_iter=2000, random_state=RANDOM_STATE,
        )),
    ])
    bin_pipe.fit(texts_bin, labels_bin)

    # Train type classifier (if enough data)
    type_pipe = None
    if len(labeled_type) >= 20:
        print("  Training domain-adapted type classifier...")
        texts_type = [preprocess(r["text"]) for r in labeled_type]
        labels_type = [TYPE_CODE_TO_LABEL[r["human_humor_type"].strip()] for r in labeled_type]
        type_pipe = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), min_df=1, max_df=0.95,
                sublinear_tf=True, max_features=5000,
            )),
            ("clf", LogisticRegression(
                class_weight="balanced", solver="lbfgs",
                max_iter=2000, random_state=RANDOM_STATE,
            )),
        ])
        type_pipe.fit(texts_type, labels_type)
    else:
        print("  WARNING: fewer than 20 typed rows — type classifier not trained")

    # Load corpus (fortune100 master or integrated)
    corpus_path = args.input if args.input else MASTER
    enc = "utf-8-sig" if corpus_path == MASTER else "utf-8"
    with open(corpus_path, newline="", encoding=enc) as f:
        master_rows = list(csv.DictReader(f))
    print(f"  Corpus: {corpus_path.name}  ({len(master_rows)} rows)")

    # Normalise column names: integrated corpus uses 'created_at_raw'
    for r in master_rows:
        if "created_at_raw" in r and "created_at" not in r:
            r["created_at"] = r["created_at_raw"]
        if "source_dataset" not in r:
            r["source_dataset"] = "fortune100"

    if args.smoke:
        master_rows = master_rows[:500]
        print(f"  Smoke mode: {len(master_rows)} posts")

    # Classify
    all_texts = [r.get("text", "") for r in master_rows]
    all_texts_pp = [preprocess(t) for t in all_texts]

    bin_probs = bin_pipe.predict_proba(all_texts_pp)[:, 1]

    classified = []
    for i, (mr, prob) in enumerate(zip(master_rows, bin_probs)):
        # No abstention: argmax at 0.50 threshold
        presence = "1" if prob >= PRESENCE_THRESHOLD else "0"

        # Type
        humor_type = "non_humorous"
        humor_type_score = 0.0
        agg = aff = se = sd = "0"
        non_h = "0" if presence == "1" else "1"

        if presence == "1" and type_pipe is not None:
            t_vec = type_pipe.predict_proba([all_texts_pp[i]])
            type_cls = type_pipe.classes_
            max_p = float(np.max(t_vec))
            pred_type = str(type_cls[int(np.argmax(t_vec))])  # always assign argmax
            humor_type = pred_type
            humor_type_score = max_p
            agg = "1" if humor_type == "aggressive" else "0"
            aff = "1" if humor_type == "affiliative" else "0"
            se = "1" if humor_type == "self_enhancing" else "0"
            sd = "1" if humor_type == "self_defeating" else "0"
        elif presence == "1" and type_pipe is None:
            humor_type = "unknown"

        classified.append({
            "source_dataset": mr.get("source_dataset", "fortune100"),
            "fortune_rank": mr.get("fortune_rank", ""),
            "company_name": mr.get("company_name", ""),
            "source_x_handle": mr.get("source_x_handle", ""),
            "tweet_id": mr.get("tweet_id", ""),
            "tweet_url": mr.get("tweet_url", ""),
            "created_at": mr.get("created_at", ""),
            "text": mr.get("text", ""),
            "total_engagement": mr.get("total_engagement", ""),
            "log_total_engagement": mr.get("log_total_engagement", ""),
            "text_length": mr.get("text_length", ""),
            "hashtag_count": mr.get("hashtag_count", ""),
            "mention_count": mr.get("mention_count", ""),
            "humor_presence": presence,
            "humor_presence_score": f"{prob:.6f}",
            "classification_status": "ok",
            "humor_type": humor_type,
            "humor_type_score": f"{humor_type_score:.6f}",
            "aggressive_humor": agg,
            "affiliative_humor": aff,
            "self_enhancing_humor": se,
            "self_defeating_humor": sd,
            "non_humorous": non_h,
            "classifier_name": CLASSIFIER_NAME,
            "classifier_version": CLASSIFIER_VERSION,
            "training_label_source": "fortune100_human_labels",
            "classification_confidence": f"{max(prob, 1-prob):.6f}",
        })

    # Write classified output
    OUT_CLASSIFIED.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CLASSIFIED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(classified[0].keys()))
        w.writeheader()
        w.writerows(classified)
    print(f"\n  Classified → {OUT_CLASSIFIED} ({len(classified)} rows)")

    # Distribution summary
    pres_dist = Counter(r["humor_presence"] for r in classified)
    type_dist = Counter(r["humor_type"] for r in classified)
    print(f"  Presence: {dict(pres_dist)}")
    print(f"  Type: {dict(type_dist)}")

    # Domain transfer comparison
    if TRANSFER.exists():
        with open(TRANSFER, newline="", encoding="utf-8") as f:
            transfer_rows = list(csv.DictReader(f))
        tr_total = len(transfer_rows)
        tr_humor = sum(1 for r in transfer_rows if r.get("humor_presence") == "1")
        tr_agg = sum(1 for r in transfer_rows if r.get("humor_type") == "aggressive")

        total = len(classified)
        humor = sum(1 for r in classified if r["humor_presence"] == "humor")
        agg = sum(1 for r in classified if r["aggressive_humor"] == "1")

        comparison = [
            {"metric": "humor_presence_rate",
             "wendy_transfer": f"{tr_humor/tr_total*100:.2f}%",
             "domain_adapted": f"{humor/total*100:.2f}%"},
            {"metric": "aggressive_rate",
             "wendy_transfer": f"{tr_agg/tr_total*100:.2f}%",
             "domain_adapted": f"{agg/total*100:.2f}%"},
            {"metric": "humor_count",
             "wendy_transfer": tr_humor,
             "domain_adapted": humor},
            {"metric": "aggressive_count",
             "wendy_transfer": tr_agg,
             "domain_adapted": agg},
        ]
        OUT_COMPARISON.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_COMPARISON, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["metric", "wendy_transfer", "domain_adapted"])
            w.writeheader()
            w.writerows(comparison)
        print(f"  Comparison → {OUT_COMPARISON}")

    print("=== apply_domain_adapted_classifier COMPLETE ===")


if __name__ == "__main__":
    main()
