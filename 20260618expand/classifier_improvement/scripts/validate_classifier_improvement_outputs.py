"""validate_classifier_improvement_outputs.py"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

REQUIRED_DIRS = [
    CI / "scripts",
    CI / "data" / "labeling_candidates",
    CI / "data" / "human_labeling_template",
    CI / "data" / "training",
    CI / "data" / "evaluation",
    CI / "data" / "classified",
    CI / "data" / "diagnostics",
    CI / "results",
    CI / "reports",
    CI / "workflows",
]

REQUIRED_FILES = [
    CI / "README.md",
    CI / "MANIFEST.md",
    CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv",
    CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv",
    CI / "reports" / "classifier_improvement_plan.md",
    CI / "reports" / "labeling_strategy.md",
    CI / "reports" / "limitations.md",
]

LABEL_REQUIRED_COLS = [
    "human_humor_presence", "human_humor_type", "human_confidence",
    "human_notes", "reviewer_id", "review_status",
]

CANDIDATE_REQUIRED_COLS = [
    "candidate_id", "sampling_stratum", "tweet_id", "text",
    "wendys_transfer_humor_presence", "wendys_transfer_humor_type",
    "classifier_disagreement_flag", "uncertainty_score",
]

FORBIDDEN_OUTPUT_PREFIXES = [
    ROOT / "dashboard" / "data",
    ROOT / "20260615wendy's",
    ROOT / "data" / "raw" / "fortune_x_2025_ranked",
    ROOT / "data" / "analysis",
    ROOT / "20260618expand" / "data" / "processed",
    ROOT / "20260618expand" / "data" / "regression_ready",
]

AGGRESSIVE_STRATA = {
    "wendys_transfer_aggressive",
    "full_chain_aggressive",
}


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh), [])


def main() -> int:
    failures: list[str] = []

    # 1. Required directories
    for d in REQUIRED_DIRS:
        if not d.exists():
            failures.append(f"missing required directory: {d.relative_to(ROOT)}")

    # 2. Required files
    for p in REQUIRED_FILES:
        if not p.exists():
            failures.append(f"missing required file: {p.relative_to(ROOT)}")

    # 3. Labeling template columns
    template = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template.csv"
    if template.exists():
        header = csv_header(template)
        for col in LABEL_REQUIRED_COLS:
            if col not in header:
                failures.append(f"template missing label column: {col}")

    # 4. Candidate file columns
    candidates = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"
    if candidates.exists():
        header = csv_header(candidates)
        for col in CANDIDATE_REQUIRED_COLS:
            if col not in header:
                failures.append(f"candidates missing column: {col}")

        # 5. sampling_stratum exists
        if "sampling_stratum" in header:
            with candidates.open("r", encoding="utf-8", newline="") as fh:
                strata = {r.get("sampling_stratum", "") for r in csv.DictReader(fh)}
            if not strata - {""}:
                failures.append("sampling_stratum column is empty in candidates")

            # 6. Aggressive oversample stratum present
            if not (AGGRESSIVE_STRATA & strata):
                failures.append(
                    f"candidates must include at least one aggressive oversample stratum "
                    f"({AGGRESSIVE_STRATA}); found: {strata}"
                )

    # 7. Classifier improvement plan exists and mentions H1/H2/H3
    plan = CI / "reports" / "classifier_improvement_plan.md"
    if plan.exists():
        text = plan.read_text(encoding="utf-8")
        for keyword in ["H1", "H2", "H3", "domain-adapted", "main analysis"]:
            if keyword not in text:
                failures.append(f"classifier_improvement_plan.md must mention '{keyword}'")

    # 8. Labeling strategy exists and mentions domain-transfer warning
    strategy = CI / "reports" / "labeling_strategy.md"
    if strategy.exists():
        text = strategy.read_text(encoding="utf-8")
        if "assertive" not in text.lower() and "corporate" not in text.lower():
            failures.append("labeling_strategy.md must contain corporate assertiveness warning")
        if "aggressive" not in text.lower():
            failures.append("labeling_strategy.md must contain aggressive humor coding criteria")

    # 9. Domain-transfer warning in limitations
    lim = CI / "reports" / "limitations.md"
    if lim.exists():
        text = lim.read_text(encoding="utf-8")
        if "domain" not in text.lower():
            failures.append("limitations.md must mention domain-transfer risk")

    # 10. No outputs outside classifier_improvement/
    for generated in CI.rglob("*"):
        if not generated.is_file():
            continue
        resolved = generated.resolve()
        for forbidden in FORBIDDEN_OUTPUT_PREFIXES:
            try:
                resolved.relative_to(forbidden)
                failures.append(f"forbidden output path: {resolved}")
            except ValueError:
                continue

    # 11. Workflow file exists and is manual-only
    workflow = ROOT / ".github" / "workflows" / "run-fortune100-classifier-improvement.yml"
    if not workflow.exists():
        failures.append("missing workflow: .github/workflows/run-fortune100-classifier-improvement.yml")
    else:
        wf_text = workflow.read_text(encoding="utf-8")
        if "workflow_dispatch" not in wf_text:
            failures.append("workflow must use workflow_dispatch (manual only)")
        if "commit_results" not in wf_text:
            failures.append("workflow must include commit_results input with default false")

    if failures:
        print("VALIDATION FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
