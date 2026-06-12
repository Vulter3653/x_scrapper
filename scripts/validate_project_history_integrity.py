#!/usr/bin/env python3
"""Compatibility wrapper for project history integrity validation."""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).resolve().with_name("validate_history_integrity.py")
runpy.run_path(str(TARGET), run_name="__main__")
