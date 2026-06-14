"""Runtime defaults and lightweight preflight hooks for GitHub Actions jobs."""
import os
import subprocess
import sys
from pathlib import Path

argv0 = Path(sys.argv[0]).name if sys.argv else ""

if argv0 == "run_humor_append_collection.py":
    os.environ.setdefault("PAGE_TIMEOUT_MS", "45000")
    if "--retry-attempts" in sys.argv:
        i = sys.argv.index("--retry-attempts")
        if i + 1 < len(sys.argv):
            try:
                if int(sys.argv[i + 1]) < 2:
                    sys.argv[i + 1] = "2"
            except ValueError:
                sys.argv[i + 1] = "2"
    else:
        sys.argv.extend(["--retry-attempts", "2"])

if argv0 == "build_humor_full_chain_input.py":
    input_path = None
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        if idx + 1 < len(sys.argv):
            input_path = Path(sys.argv[idx + 1])
    if input_path is None:
        input_path = Path("data/derived/humor/humor_classification_input.csv")
    if str(input_path).replace("\\", "/") == "data/derived/humor/humor_classification_input.csv":
        manifest_path = Path("data/derived/humor/humor_classification_input_manifest.json")
        builder = Path("scripts/build_humor_classification_input_from_raw.py")
        if builder.exists():
            subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    "--output",
                    str(input_path),
                    "--manifest",
                    str(manifest_path),
                ],
                check=True,
            )
