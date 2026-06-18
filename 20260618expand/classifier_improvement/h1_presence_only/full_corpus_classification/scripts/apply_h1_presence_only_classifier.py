"""
apply_h1_presence_only_classifier.py

Applies the H1 presence-only classifier to the full Fortune 100 post corpus.

Classifier: word_char_comb__lr_liblin_C01
  - Vectorizer: word(1,2) + char_wb(3,5) FeatureUnion, max_features=5000+5000
  - Classifier: LogisticRegression(liblinear, C=0.1, class_weight=balanced)
  - Training: batch1 human labels only, 1,482 valid rows (humor=648, non_humor=834)
  - OOF AUC: 0.7811   OOF F1: 0.6792   Firm-HO F1: 0.4770
  - Status: provisional / exploratory

Output columns added:
  h1_humor_presence_probability   — [0,1] predicted probability of humor
  h1_humor_presence_pred_t40      — 1 if probability >= 0.40, else 0
  h1_humor_presence_pred_t50      — 1 if probability >= 0.50, else 0
  h1_humor_presence_pred_t60      — 1 if probability >= 0.60, else 0
  missing_text                    — 1 if text was empty/missing
  h1_classifier_model             — word_char_comb__lr_liblin_C01
  h1_classifier_training_scope    — batch1_only
  h1_classifier_status            — provisional

IMPORTANT:
  - H1 regression is NOT run here.
  - type/aggressive classification is NOT performed.
  - H2/H3 are out of scope.
  - Output is provisional/exploratory only.
"""

from __future__ import annotations

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
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[5]
CI = ROOT / "20260618expand" / "classifier_improvement"
H1 = CI / "h1_presence_only"
SPLITS_DIR = CI / "data" / "human_labeling_template" / "coder_splits"
POST_MASTER = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
OUT_DIR = H1 / "full_corpus_classification" / "data"

OUT_POSTS   = OUT_DIR / "fortune100_h1_presence_classified_posts.csv"
OUT_SUMMARY = OUT_DIR / "fortune100_h1_presence_classification_summary.csv"
OUT_FIRM    = OUT_DIR / "fortune100_h1_presence_by_firm_summary.csv"

CODERS = ["coder1", "coder2", "coder3"]
KOR_PRESENCE = "유머_존재여부"
KOR_TEXT     = "본문"
RANDOM_STATE = 42

MODEL_ID     = "word_char_comb__lr_liblin_C01"
TRAIN_SCOPE  = "batch1_only"
CLF_STATUS   = "provisional"

PRESERVE_COLS = [
    "fortune_rank", "company_name", "normalized_company_name",
    "source_x_handle", "source_x_url", "account_role", "account_index",
    "tweet_id", "tweet_url", "created_at", "text",
    "reply_count", "repost_count", "retweet_count", "like_count",
    "favorite_count", "quote_count", "view_count_available",
    "total_engagement", "log_total_engagement",
    "text_length", "hashtag_count", "mention_count",
    "collection_method", "max_posts_cap", "source_folder",
]

ADD_COLS = [
    "h1_humor_presence_probability",
    "h1_humor_presence_pred_t40",
    "h1_humor_presence_pred_t50",
    "h1_humor_presence_pred_t60",
    "missing_text",
    "h1_classifier_model",
    "h1_classifier_training_scope",
    "h1_classifier_status",
]


def preprocess(text: str) -> str:
    text = re.sub(r"https?://\S+", "<URL>", text)
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
        if not path.exists():
            raise FileNotFoundError(f"Coder file missing: {path}")
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pc = row.get(KOR_PRESENCE, "").strip()
                if pc not in ("0", "1"):
                    continue
                text = row.get(KOR_TEXT, "").strip()
                texts.append(preprocess(text))
                labels.append(1 if pc == "1" else 0)
    return texts, labels


def main() -> None:
    print("=== apply_h1_presence_only_classifier ===")
    print(f"  Classifier: {MODEL_ID}  scope={TRAIN_SCOPE}  status={CLF_STATUS}")

    # --- Train on batch1 labels ---
    print("  Loading batch1 training labels...")
    train_texts, train_labels = load_training_data()
    label_dist = Counter(train_labels)
    print(f"  Training rows: {len(train_labels)}  humor={label_dist[1]}  non_humor={label_dist[0]}")
    assert len(train_labels) == 1482, f"Expected 1482, got {len(train_labels)}"
    assert label_dist[1] == 648, f"Expected 648 humor, got {label_dist[1]}"
    assert label_dist[0] == 834, f"Expected 834 non_humor, got {label_dist[0]}"

    pipe = build_pipeline()
    print("  Fitting final model on all 1,482 batch1 valid rows...")
    pipe.fit(train_texts, train_labels)
    print("  Fit complete.")

    # --- Load full corpus ---
    if not POST_MASTER.exists():
        raise FileNotFoundError(f"Post master not found: {POST_MASTER}")
    print(f"  Loading full corpus: {POST_MASTER}")
    with open(POST_MASTER, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_cols = reader.fieldnames or []
        corpus_rows = list(reader)
    print(f"  Corpus rows: {len(corpus_rows)}")

    # --- Classify ---
    print("  Preprocessing and classifying...")
    texts_corpus: list[str] = []
    missing_flags: list[int] = []
    for r in corpus_rows:
        t = r.get("text", "").strip()
        if not t:
            texts_corpus.append("")
            missing_flags.append(1)
        else:
            texts_corpus.append(preprocess(t))
            missing_flags.append(0)

    # Predict probabilities (only for non-missing rows)
    valid_idx = [i for i, m in enumerate(missing_flags) if m == 0]
    valid_texts = [texts_corpus[i] for i in valid_idx]

    probs_full = np.full(len(corpus_rows), np.nan)
    if valid_texts:
        probs = pipe.predict_proba(valid_texts)[:, 1]
        for idx, prob in zip(valid_idx, probs):
            probs_full[idx] = prob

    # Threshold predictions
    def threshold_pred(p: float | None, thr: float) -> str:
        if p is None or np.isnan(p):
            return ""
        return "1" if p >= thr else "0"

    # --- Build output rows ---
    print("  Writing output files...")
    out_cols = [c for c in PRESERVE_COLS if c in raw_cols or c == "text"]
    # Make sure we use actual available cols
    avail_preserve = [c for c in PRESERVE_COLS if c in raw_cols]
    out_fieldnames = avail_preserve + ADD_COLS

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_POSTS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fieldnames, extrasaction="ignore")
        w.writeheader()
        for i, row in enumerate(corpus_rows):
            p = probs_full[i]
            out_row = {c: row.get(c, "") for c in avail_preserve}
            out_row["h1_humor_presence_probability"] = "" if np.isnan(p) else round(float(p), 6)
            out_row["h1_humor_presence_pred_t40"]    = threshold_pred(p, 0.40)
            out_row["h1_humor_presence_pred_t50"]    = threshold_pred(p, 0.50)
            out_row["h1_humor_presence_pred_t60"]    = threshold_pred(p, 0.60)
            out_row["missing_text"]                  = missing_flags[i]
            out_row["h1_classifier_model"]           = MODEL_ID
            out_row["h1_classifier_training_scope"]  = TRAIN_SCOPE
            out_row["h1_classifier_status"]          = CLF_STATUS
            w.writerow(out_row)
    print(f"  Written: {OUT_POSTS}")

    # --- Summary ---
    classified_n = int(np.sum(~np.isnan(probs_full)))
    missing_n    = int(np.sum(np.array(missing_flags) == 1))
    valid_probs  = probs_full[~np.isnan(probs_full)]

    n_t40 = int((valid_probs >= 0.40).sum())
    n_t50 = int((valid_probs >= 0.50).sum())
    n_t60 = int((valid_probs >= 0.60).sum())
    total = len(corpus_rows)

    summary = [{
        "metric":  "total_posts",             "value": total},
        {"metric": "classified_posts",         "value": classified_n},
        {"metric": "missing_text_posts",       "value": missing_n},
        {"metric": "mean_humor_probability",   "value": round(float(valid_probs.mean()), 4) if len(valid_probs) else ""},
        {"metric": "humor_rate_t40",           "value": round(n_t40 / classified_n, 4) if classified_n else ""},
        {"metric": "humor_rate_t50",           "value": round(n_t50 / classified_n, 4) if classified_n else ""},
        {"metric": "humor_rate_t60",           "value": round(n_t60 / classified_n, 4) if classified_n else ""},
        {"metric": "n_humor_t40",              "value": n_t40},
        {"metric": "n_humor_t50",              "value": n_t50},
        {"metric": "n_humor_t60",              "value": n_t60},
        {"metric": "n_non_humor_t40",          "value": classified_n - n_t40},
        {"metric": "n_non_humor_t50",          "value": classified_n - n_t50},
        {"metric": "n_non_humor_t60",          "value": classified_n - n_t60},
        {"metric": "classifier_model",         "value": MODEL_ID},
        {"metric": "classifier_training_scope","value": TRAIN_SCOPE},
        {"metric": "classifier_status",        "value": CLF_STATUS},
        {"metric": "oof_auc_ref",              "value": 0.7811},
        {"metric": "oof_f1_ref",               "value": 0.6792},
        {"metric": "firm_held_out_f1_ref",     "value": 0.4770},
        {"metric": "h1_regression_run",        "value": "NO"},
        {"metric": "h2_h3_run",                "value": "NO"},
        {"metric": "type_classifier_used",     "value": "NO"},
        {"metric": "aggressive_detector_used", "value": "NO"},
    ]
    with open(OUT_SUMMARY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)
    print(f"  Written: {OUT_SUMMARY}")
    print(f"    total={total}  classified={classified_n}  missing_text={missing_n}")
    print(f"    humor_rate t40={n_t40/classified_n:.4f}  t50={n_t50/classified_n:.4f}  t60={n_t60/classified_n:.4f}")

    # --- Firm summary ---
    from collections import defaultdict
    firm_probs: dict[str, list[float]] = defaultdict(list)
    firm_handles: dict[str, str] = {}
    firm_missing: dict[str, int] = defaultdict(int)

    for i, row in enumerate(corpus_rows):
        company = row.get("company_name", "")
        handle  = row.get("source_x_handle", "")
        firm_handles[company] = handle
        p = probs_full[i]
        if missing_flags[i] == 1:
            firm_missing[company] += 1
        elif not np.isnan(p):
            firm_probs[company].append(float(p))

    firm_rows = []
    for company in sorted(firm_probs.keys()):
        ps = np.array(firm_probs[company])
        n  = len(ps)
        nh40 = int((ps >= 0.40).sum())
        nh50 = int((ps >= 0.50).sum())
        nh60 = int((ps >= 0.60).sum())
        firm_rows.append({
            "company_name":          company,
            "source_x_handle":       firm_handles.get(company, ""),
            "total_posts":           n + firm_missing.get(company, 0),
            "classified_posts":      n,
            "missing_text_posts":    firm_missing.get(company, 0),
            "mean_humor_probability": round(float(ps.mean()), 4),
            "humor_rate_t40":        round(nh40 / n, 4),
            "humor_rate_t50":        round(nh50 / n, 4),
            "humor_rate_t60":        round(nh60 / n, 4),
            "n_humor_t50":           nh50,
            "n_non_humor_t50":       n - nh50,
        })

    firm_keys = [
        "company_name", "source_x_handle", "total_posts", "classified_posts",
        "missing_text_posts", "mean_humor_probability",
        "humor_rate_t40", "humor_rate_t50", "humor_rate_t60",
        "n_humor_t50", "n_non_humor_t50",
    ]
    with open(OUT_FIRM, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=firm_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(firm_rows)
    print(f"  Written: {OUT_FIRM} ({len(firm_rows)} firms)")

    print("=== apply_h1_presence_only_classifier COMPLETE ===")


if __name__ == "__main__":
    main()
