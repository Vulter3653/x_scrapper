#!/usr/bin/env python3
"""Backward-compatible root entrypoint for dashboard data sync."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from x_scrapper.dashboard.sync_data import main


if __name__ == "__main__":
    main()
