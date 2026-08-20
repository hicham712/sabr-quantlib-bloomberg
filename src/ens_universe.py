"""Bloomberg ENS swaption security generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .surface import BLOOMBERG_FIELDS


@dataclass(frozen=True)
class ENSSecurity:
    offset_bp: float
    ticker: str


def maturity_code(years: int) -> str:
    if not 1 <= years <= 99:
        raise ValueError("ENS maturity years must be between 1 and 99")
    return f"0F{years:02d}"


def build_ens_security(offset_bp: float, years: int, index: str, yellow_key: str = "Curncy") -> str:
    if offset_bp not in BLOOMBERG_FIELDS:
        raise ValueError(f"unsupported ENS offset: {offset_bp}")
    return f"{BLOOMBERG_FIELDS[offset_bp]}{maturity_code(years)} {index} {yellow_key}"


def build_atm_security(years: int, index: str, yellow_key: str = "Curncy") -> str:
    """Build the Bloomberg ATM ENS security (ENPS) for a maturity."""
    return f"ENPS{maturity_code(years)} {index} {yellow_key}"


def build_ens_universe(years: Sequence[int], index: str, yellow_key: str = "Curncy") -> dict[int, list[ENSSecurity]]:
    return {
        year: [
            ENSSecurity(offset, build_ens_security(offset, year, index, yellow_key))
            for offset in BLOOMBERG_FIELDS
        ]
        for year in years
    }
