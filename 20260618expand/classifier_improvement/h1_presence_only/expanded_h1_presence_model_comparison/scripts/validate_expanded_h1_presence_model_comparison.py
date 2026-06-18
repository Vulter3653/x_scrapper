"""Validate expanded H1 presence model-comparison scaffold or outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_model_comparison"
EXPANDED = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only" / "expanded_h1_presence_training" / "data" / "expanded_h1_presence_training_dataset.csv"

SCRIPT = BASE / "scripts" / "compare_expanded_h1_presence_models.py"
README = BASE / "README.md"
DATA_DIR = BASE / "data"
DIAG_DIR = BASE / "diagnostics"
RES_DIR = BASE / "results"

REQUIRED_OUTPUTS = {
    "training_diagnostics": DIAG_DIR / "training_data_diagnostics.csv",
    "metrics": RES_DIR / "model_comparison_metrics.csv",
    "confusion_matrices": RES_DIR / "model_comparison_confusion_matrices.csv",
    "source_aware": RES_DIR / "source_aware_subset_metrics.csv",
    "wendys_held_out": RES_DIR / "wendys_held_out_metrics.csv",
    "wendys_held_out_cm": RES_DIR / "wendys_held_out_confusion_matrix.csv",
    "feature_weights": RES_DIR / "top_feature_weights.csv",
    "wendys_leakage": DIAG_DIR / "wendys_leakage_feature_diagnostic.csv",
}
METRIC_COLUMNS = {"model_name", "model_id", "eval_scope", "eval_mode", "n_rows", "humor_count", "non_humor_count", "auc", "f1", "precision", "recall"}
FEATURE_COLUMNS = {"model_name", "direction", "rank", "feature", "weight"}
SOURCE_AWARE_COLUMNS = METRIC_COLUMNS


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def columns(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return set(reader.fieldnames or [])


def validate_input_counts(failures: list[str]) -> None:
    if not EXPANDED.exists():
        failures.append(f"missing expanded input: {EXPANDED}")
        return
    rows = read_csv(EXPANDED)
    batch1 = [r for r in rows if r.get("source") == "batch1_fortune100"]
    wendys = [r for r in rows if r.get("source") == "wendys_human"]
    if len(batch1) != 1482:
        failures.append(f"Model A valid rows expected 1482, got {len(batch1)}")
    if len(rows) != 1550:
        failures.append(f"Model B valid rows expected 1550, got {len(rows)}")
    if len(wendys) != 68:
        failures.append(f"Wendy's-held-out test rows expected 68, got {len(wendys)}")
    bad_labels = sorted({r.get("humor_presence_binary", "") for r in rows} - {"0", "1"})
    if bad_labels:
        failures.append(f"invalid humor_presence_binary values: {bad_labels}")


def validate_no_forbidden_outputs(failures: list[str]) -> None:
    forbidden_tokens = ["integrated_h1_presence_classified", "regression", "h2", "h3", "type_classifier", "aggressive_detector"]
    for path in BASE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(BASE).as_posix().lower()
        if any(token in rel for token in forbidden_tokens):
            failures.append(f"forbidden output in comparison directory: {path.relative_to(BASE)}")


def validate_structure(failures: list[str]) -> None:
    for path in [SCRIPT, README, DATA_DIR, DIAG_DIR, RES_DIR]:
        if not path.exists():
            failures.append(f"missing scaffold path: {path.relative_to(ROOT)}")
    validate_input_counts(failures)
    validate_no_forbidden_outputs(failures)


def validate_outputs(failures: list[str]) -> None:
    validate_structure(failures)
    missing = [name for name, path in REQUIRED_OUTPUTS.items() if not path.exists()]
    if missing:
        failures.append(f"missing required output files: {missing}")
        return

    diag = {r.get("model_name", ""): r for r in read_csv(REQUIRED_OUTPUTS["training_diagnostics"])}
    if diag.get("batch1_only", {}).get("valid_rows") != "1482":
        failures.append("training diagnostics missing Model A valid_rows=1482")
    if diag.get("batch1_plus_wendys_human", {}).get("valid_rows") != "1550":
        failures.append("training diagnostics missing Model B valid_rows=1550")
    if diag.get("batch1_plus_wendys_human", {}).get("wendys_rows") != "68":
        failures.append("training diagnostics missing Wendy's rows=68")

    if not METRIC_COLUMNS <= columns(REQUIRED_OUTPUTS["metrics"]):
        failures.append("model_comparison_metrics.csv missing required metric columns")
    if not SOURCE_AWARE_COLUMNS <= columns(REQUIRED_OUTPUTS["source_aware"]):
        failures.append("source_aware_subset_metrics.csv missing required metric columns")
    if not FEATURE_COLUMNS <= columns(REQUIRED_OUTPUTS["feature_weights"]):
        failures.append("top_feature_weights.csv missing required feature columns")

    w_rows = read_csv(REQUIRED_OUTPUTS["wendys_held_out"])
    if not any(r.get("eval_scope") == "wendys_held_out" and r.get("n_rows") == "68" for r in w_rows):
        failures.append("Wendy's-held-out metrics missing n_rows=68")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate expanded H1 presence model comparison scaffold or full outputs.")
    parser.add_argument("--check-structure", action="store_true", help="Validate scaffold and inputs only; do not require model outputs.")
    args = parser.parse_args()

    failures: list[str] = []
    if args.check_structure:
        validate_structure(failures)
    else:
        validate_outputs(failures)

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALIDATION PASS")
    print("mode=" + ("structure" if args.check_structure else "outputs"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
