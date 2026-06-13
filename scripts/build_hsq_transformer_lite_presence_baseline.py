#!/usr/bin/env python3
"""Run a small RoBERTa/BERTweet-style transformer-lite presence experiment.

This script is intentionally experimental. It trains on HSQ teacher pseudo-labels
built from high-intensity humor seeds and hard-negative non-humor seeds, then
reports test-set metrics. The output must be treated as a comparison baseline,
not as a final classifier, until human validation is available.
"""

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

LABEL_TO_ID = {"non_humor": 0, "humor": 1}
ID_TO_LABEL = {0: "non_humor", 1: "humor"}

COMBINED_FIELDS = ["global_post_id", "text", "presence_label", "seed_bucket", "hard_negative_category", "sample_group", "company_name", "created_at", "source_file"]
PREDICTION_FIELDS = COMBINED_FIELDS + ["predicted_presence_label", "predicted_humor_probability", "prediction_correct"]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text):
    return " ".join((text or "").split())


def dedupe_by_id(rows):
    seen = set()
    out = []
    for idx, row in enumerate(rows):
        gid = row.get("global_post_id") or f"missing_id_{idx}"
        if gid in seen:
            continue
        seen.add(gid)
        out.append(row)
    return out


def seed_row(row, label, source):
    return {
        "global_post_id": row.get("global_post_id", ""),
        "text": normalize_text(row.get("text", "")),
        "presence_label": label,
        "seed_bucket": row.get("seed_bucket", ""),
        "hard_negative_category": row.get("hard_negative_category", ""),
        "sample_group": row.get("sample_group", ""),
        "company_name": row.get("company_name", ""),
        "created_at": row.get("created_at", ""),
        "source_file": source,
    }


def sample_rows(rows, limit, rng):
    rows = list(rows)
    if limit <= 0 or len(rows) <= limit:
        return rows
    rng.shuffle(rows)
    return rows[:limit]


def build_rows(humor_seed, hard_negative_seed, max_negative_ratio, max_total_rows, rng):
    humor = [seed_row(r, "humor", humor_seed.name) for r in read_csv(humor_seed) if normalize_text(r.get("text", ""))]
    negative = [seed_row(r, "non_humor", hard_negative_seed.name) for r in read_csv(hard_negative_seed) if normalize_text(r.get("text", ""))]
    humor = dedupe_by_id(humor)
    negative = dedupe_by_id(negative)
    negative = sample_rows(negative, int(len(humor) * max_negative_ratio), rng)
    rows = humor + negative
    if max_total_rows > 0 and len(rows) > max_total_rows:
        # Preserve all positives when possible, sample negatives down first.
        max_neg = max(0, max_total_rows - len(humor))
        rows = humor + sample_rows(negative, max_neg, rng)
    rng.shuffle(rows)
    return rows


class TextDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length):
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        enc = self.tokenizer(row["text"], truncation=True, padding="max_length", max_length=self.max_length, return_tensors="pt")
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL_TO_ID[row["presence_label"]], dtype=torch.long),
        }


def evaluate(model, dataloader, device):
    model.eval()
    y_true, y_pred, probs = [], [], []
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            out = model(input_ids=input_ids, attention_mask=attention_mask)
            p = torch.softmax(out.logits, dim=-1)
            pred = torch.argmax(p, dim=-1)
            y_true.extend(labels.cpu().tolist())
            y_pred.extend(pred.cpu().tolist())
            probs.extend(p[:, LABEL_TO_ID["humor"]].cpu().tolist())
    return y_true, y_pred, probs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--humor-seed", type=Path, required=True)
    parser.add_argument("--hard-negative-seed", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="distilroberta-base")
    parser.add_argument("--max-total-rows", type=int, default=600)
    parser.add_argument("--max-negative-ratio", type=float, default=4.0)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--random-state", type=int, default=20260613)
    parser.add_argument("--freeze-base", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.random_state)
    torch.manual_seed(args.random_state)
    rows = build_rows(args.humor_seed, args.hard_negative_seed, args.max_negative_ratio, args.max_total_rows, rng)
    labels = [r["presence_label"] for r in rows]
    if len(set(labels)) < 2:
        raise SystemExit("Transformer-lite experiment requires both humor and non_humor labels.")

    train_rows, test_rows = train_test_split(rows, test_size=args.test_size, random_state=args.random_state, stratify=labels)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, num_labels=2, id2label=ID_TO_LABEL, label2id=LABEL_TO_ID)

    if args.freeze_base:
        for name, param in model.named_parameters():
            if "classifier" not in name and "score" not in name:
                param.requires_grad = False

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loader = DataLoader(TextDataset(train_rows, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(TextDataset(test_rows, tokenizer, args.max_length), batch_size=args.batch_size)

    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.learning_rate)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)

    model.train()
    losses = []
    for _epoch in range(args.epochs):
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_t = batch["labels"].to(device)
            out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels_t)
            out.loss.backward()
            optimizer.step()
            scheduler.step()
            losses.append(float(out.loss.detach().cpu()))

    y_true_ids, y_pred_ids, probs = evaluate(model, test_loader, device)
    y_true = [ID_TO_LABEL[i] for i in y_true_ids]
    y_pred = [ID_TO_LABEL[i] for i in y_pred_ids]
    labels_order = ["humor", "non_humor"]
    report = classification_report(y_true, y_pred, labels=labels_order, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels_order)
    p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)

    prediction_rows = []
    for row, pred, prob in zip(test_rows, y_pred, probs):
        out = dict(row)
        out["predicted_presence_label"] = pred
        out["predicted_humor_probability"] = f"{prob:.8f}"
        out["prediction_correct"] = str(pred == row["presence_label"]).lower()
        prediction_rows.append(out)

    report_rows = []
    for label, metrics in report.items():
        if isinstance(metrics, dict):
            report_rows.append({"label": label, "precision": metrics.get("precision", 0.0), "recall": metrics.get("recall", 0.0), "f1_score": metrics.get("f1-score", 0.0), "support": metrics.get("support", 0.0)})

    cm_rows = []
    for i, actual in enumerate(labels_order):
        for j, predicted in enumerate(labels_order):
            cm_rows.append({"actual_label": actual, "predicted_label": predicted, "count": int(cm[i][j])})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    combined_path = args.output_dir / "hsq_transformer_lite_presence_combined.csv"
    train_path = args.output_dir / "hsq_transformer_lite_presence_train.csv"
    test_path = args.output_dir / "hsq_transformer_lite_presence_test.csv"
    pred_path = args.output_dir / "hsq_transformer_lite_presence_predictions.csv"
    report_path = args.output_dir / "hsq_transformer_lite_presence_report.csv"
    cm_path = args.output_dir / "hsq_transformer_lite_presence_confusion_matrix.csv"
    summary_path = args.output_dir / "hsq_transformer_lite_presence_summary.json"

    write_csv(combined_path, rows, COMBINED_FIELDS)
    write_csv(train_path, train_rows, COMBINED_FIELDS)
    write_csv(test_path, test_rows, COMBINED_FIELDS)
    write_csv(pred_path, prediction_rows, PREDICTION_FIELDS)
    write_csv(report_path, report_rows, ["label", "precision", "recall", "f1_score", "support"])
    write_csv(cm_path, cm_rows, ["actual_label", "predicted_label", "count"])

    summary = {
        "task": "HSQ transformer-lite presence baseline",
        "important_note": "This uses HSQ teacher pseudo-labels, not human-gold labels. Treat as an exploratory comparison only.",
        "model_name": args.model_name,
        "device": str(device),
        "freeze_base": args.freeze_base,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "max_length": args.max_length,
        "learning_rate": args.learning_rate,
        "combined_rows": len(rows),
        "combined_distribution": dict(Counter(labels)),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "train_distribution": dict(Counter(r["presence_label"] for r in train_rows)),
        "test_distribution": dict(Counter(r["presence_label"] for r in test_rows)),
        "mean_train_loss": sum(losses) / len(losses) if losses else None,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_precision": p_macro,
        "macro_recall": r_macro,
        "macro_f1": f_macro,
        "classification_report": report,
        "confusion_matrix_labels": labels_order,
        "confusion_matrix": cm.tolist(),
        "output_files": {
            "combined": str(combined_path),
            "train": str(train_path),
            "test": str(test_path),
            "predictions": str(pred_path),
            "report": str(report_path),
            "confusion_matrix": str(cm_path),
            "summary": str(summary_path),
        },
        "recommended_next_step": "Compare with TF-IDF threshold results. Do not replace HSQ classifier unless transformer improves precision/recall and survives human validation.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
