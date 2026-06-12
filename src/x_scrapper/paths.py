"""Central repository path constants.

These constants are intentionally pathlib.Path objects rooted at the repository
root. Scripts may still accept environment-variable overrides for backward
compatibility, but new code should import paths from this module.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = SRC_ROOT.parent

DATA_ROOT = REPO_ROOT / "data"
DASHBOARD_ROOT = REPO_ROOT / "dashboard"
DASHBOARD_DATA_ROOT = DASHBOARD_ROOT / "data"
CONFIG_ROOT = REPO_ROOT / "config"
AUDIT_ROOT = DATA_ROOT / "audit"
ANALYSIS_OUTPUT_ROOT = DATA_ROOT / "analysis"

CURRENT_BRAND_SLUGS = ("wendys", "cocacola", "moonpie")
CURRENT_BRAND_DATA_ROOTS = {slug: DATA_ROOT / slug for slug in CURRENT_BRAND_SLUGS}

FORTUNE2025_CONFIG_ROOT = CONFIG_ROOT / "fortune2025"
FORTUNE2025_AUDIT_ROOT = AUDIT_ROOT
FORTUNE2025_X_ACCOUNTS_ROOT = DATA_ROOT / "fortune2025" / "x_accounts"
FORTUNE2025_SEC_10K_ROOT = DATA_ROOT / "fortune2025" / "sec_10k"
FORTUNE2025_INDUSTRY_CODES_ROOT = DATA_ROOT / "fortune2025" / "industry_codes"
