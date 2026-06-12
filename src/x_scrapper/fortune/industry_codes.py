"""Skeleton for Fortune 2025 industry-code enrichment.

No external data collection is performed here. Future implementation should
join reviewed Fortune firms to NAICS/SIC metadata from a documented source and
write audit-friendly enrichment outputs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndustryCodeMatch:
    fortune_rank: int
    firm_name: str
    naics_code: str = ""
    sic_code: str = ""
    match_status: str = "not_implemented"
    notes: str = ""


def enrich_industry_codes() -> list[IndustryCodeMatch]:
    """Return an empty skeleton result until enrichment rules are finalized."""
    return []
