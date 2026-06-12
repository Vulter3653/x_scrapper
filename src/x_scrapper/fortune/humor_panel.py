"""Skeleton for Fortune firm-level humor panel construction.

This module documents the planned boundary only. It must not scrape X posts or
create a Fortune 500 panel until the official account verification stage is
complete.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumorFirmPanelRow:
    fortune_year: str
    fortune_rank: int
    firm_name: str
    post_count: int = 0
    dominant_humor_label: str = ""
    humor_confidence_mean: float = 0.0
    aggregation_status: str = "not_implemented"


def build_humor_firm_panel() -> list[HumorFirmPanelRow]:
    """Return an empty skeleton result until post collection is in scope."""
    return []
