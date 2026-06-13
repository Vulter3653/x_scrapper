"""Runtime defaults for GitHub Actions collection jobs.

Scoped to the humor append collection path. This keeps failed render probes short
while allowing one additional attempt for transient X rendering failures.
"""
import os
import sys
from pathlib import Path

argv0 = Path(sys.argv[0]).name if sys.argv else ""

if argv0 == "run_humor_append_collection.py":
    os.environ["PAGE_TIMEOUT_MS"] = "15000"
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
