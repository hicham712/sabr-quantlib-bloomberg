"""Bloomberg ENS swaption security generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .surface import BLOOMBERG_FIELDS


@dataclass(frozen=True)
class ENSSecurity:
    """One Bloomberg ENS smile security."""

    offset_bp: float
    ticker: str


def maturity_code(years: int) -> str:
    """Convert an integer tenor in years to the Bloomberg ENS maturity code.

    Bloomberg examples such as ``ENSI0F05 IIRO Curncy`` use ``0F05`` for 5Y.
    """
    if not 1 <= years <= 99:
        raise ValueError("ENS maturity years must be between 1 and 99")
    return f"0F{years:02d}"


def build_ens_security(
    offset_bp: float,
    years: int,
    index: str,
    yellow_key: str = "Curncy",
) -> str:
    """Build one ENS Bloomberg security from offset, maturity and index."""
    if offset_bp not in BLOOMBERG_FIELDS:
        raise ValueError(f"unsupported ENS offset: {offset_bp}")
    return f"{BLOOMBERG_FIELDS[offset_bp]}{maturity_code(years)} {index} {yellow_key}"


def build_ens_universe(
    years: Sequence[int],
    index: str,
    yellow_key: str = "Curncy",
) -> dict[int, list[ENSSecurity]]:
    """Generate all eight ENS securities for every requested maturity."""
    return {
        year: [
            ENSSecurity(offset, build_ens_security(offset, year, index, yellow_key))
            for offset in BLOOMBERG_FIELDS
        ]
        for year in years
    }
