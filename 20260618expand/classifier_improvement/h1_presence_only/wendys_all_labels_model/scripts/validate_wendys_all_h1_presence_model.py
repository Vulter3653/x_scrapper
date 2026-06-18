"""Validate all-Wendy's H1 presence integration and Model A/C outputs."""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
H1 = ROOT / "20260618expand" / "classifier_improvement" / "h1_presence_only"
INTEGRATION = H1 / "wendys_all_labels_integration"
BASE = H1 / "wendys_all_labels_model"
INT_DATA = INTEGRATION / "data"
INT_DIAG = INTEGRATION / "diagnostics"
DATA = BASE / "data"
DIAG = BASE / "diagnostics"

REQUIRED = [
    INT_DIAG / "wendys_label_source_inventory.csv",
    INT_DATA / "expanded_h1_presence_training_with_all_wendys.csv",
    INT_DATA / "wendys_all_h1_presence_labels_raw_merged.csv",
    INT_DATA / "wendys_all_h1_presence_labels_valid.csv",
    INT_DIAG / "wendys_duplicate_diagnostics.csv",
    INT_DIAG / "wendys_conflicting_label_diagnostics.csv",
    INT_DIAG / "wendys_missing_text_diagnostics.csv",
    DATA / "model_a_vs_model_c_metrics.csv",
    DATA / "source_aware_metrics.csv",
    DATA / "wendys_heldout_metrics_all_wendys.csv",
    DATA / "model_a_vs_model_c_confusion_matrices.csv",
    DATA / "model_c_oof_predictions.csv",
    DATA / "model_a_wendys_all_heldout_predictions.csv",
    DIAG / "training_data_diagnostics.csv",
    DIAG / "wendys_all_source_inventory.csv",
    DIAG / "wendys_label_integration_summary.csv",
    DIAG / "wendys_duplicate_diagnostics.csv",
    DIAG / "wendys_conflicting_label_diagnostics.csv",
    DIAG / "wendys_leakage_feature_diagnostic.csv",
    DIAG / "top_feature_weights_model_c.csv",
    DIAG / "validation_summary.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def metric_map(path: Path) -> dict[str, str]:
    return {r.get("metric", ""): r.get("value", "") for r in read_csv(path)}


def fail_if_forbidden_outputs(failures: list[str]) -> None:
    forbidden = ["integrated_h1_presence_classified", "h1_regression", "regression", "h2", "h3", "aggressive", "type_classifier"]
    for path in BASE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(BASE).as_posix().lower()
        if rel.startswith("scripts/"):
            continue
        if any(token in rel for token in forbidden):
            failures.append(f"forbidden output under model directory: {path.relative_to(BASE)}")


def fail_if_forbidden_git_changes(failures: list[str]) -> None:
    try:
        out = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    except Exception as exc:
        failures.append(f"git status check failed: {exc}")
        return
    for line in out.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path.startswith("data/raw/"):
            failures.append(f"data/raw modified: {line}")
        if path.startswith("dashboard/data/"):
            failures.append(f"dashboard/data modified: {line}")
        if path.startswith(".github/workflows/"):
            failures.append(f"workflow modified: {line}")


def main() -> int:
    failures: list[str] = []
    for path in REQUIRED:
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")
    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    expanded = read_csv(INT_DATA / "expanded_h1_presence_training_with_all_wendys.csv")
    batch1 = [r for r in expanded if r.get("source") == "batch1_fortune100"]
    wendys = [r for r in expanded if r.get("source") == "wendys_all_human"]
    if len(batch1) != 1482:
        failures.append(f"batch1 valid rows expected 1482, got {len(batch1)}")
    if len(wendys) <= 68:
        failures.append(f"Wendy's all valid H1 rows must be >68, got {len(wendys)}")
    if any(r.get("humor_presence_binary") not in {"0", "1"} for r in expanded):
        failures.append("expanded dataset contains non-binary H1 labels")
    if any(not r.get("text", "").strip() for r in expanded):
        failures.append("expanded dataset contains blank text")

    metrics = read_csv(DATA / "model_a_vs_model_c_metrics.csv")
    model_ids = {r.get("model_id") for r in metrics}
    if "model_a_batch1_only" not in model_ids:
        failures.append("Model A metrics missing")
    if "model_c_batch1_plus_all_wendys" not in model_ids:
        failures.append("Model C metrics missing")
    held = read_csv(DATA / "wendys_heldout_metrics_all_wendys.csv")
    if not held:
        failures.append("Wendy's-held-out metrics missing")
    else:
        if int(held[0].get("n_rows", "0")) != len(wendys):
            failures.append("Wendy's-held-out n_rows does not equal final Wendy's rows")

    train_diag = metric_map(DIAG / "training_data_diagnostics.csv")
    if train_diag.get("model_a_rows") != "1482":
        failures.append("training diagnostics missing model_a_rows=1482")
    if int(train_diag.get("wendys_all_human_rows", "0")) <= 68:
        failures.append("training diagnostics Wendy's rows <=68")
    if not read_csv(DIAG / "wendys_leakage_feature_diagnostic.csv"):
        failures.append("leakage diagnostic is empty")
    if not read_csv(DIAG / "top_feature_weights_model_c.csv"):
        failures.append("Model C feature weights missing")

    fail_if_forbidden_outputs(failures)
    fail_if_forbidden_git_changes(failures)

    if failures:
        print("VALIDATION FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALIDATION PASS")
    print(f"batch1_rows={len(batch1)}")
    print(f"wendys_all_human_rows={len(wendys)}")
    print(f"expanded_rows={len(expanded)}")
    print(f"candidate_status={train_diag.get('candidate_status')}")
    print(f"leakage_flag={train_diag.get('leakage_flag')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
