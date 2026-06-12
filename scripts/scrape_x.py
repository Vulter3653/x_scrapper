#!/usr/bin/env python3
"""Compatibility entrypoint for the X scraper implementation in src/."""

from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from x_scrapper.collection.x_scraper import scrape_profile


if __name__ == "__main__":
    try:
        asyncio.run(scrape_profile())
    except Exception as exc:
        print(f"Fatal scraper error: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)
