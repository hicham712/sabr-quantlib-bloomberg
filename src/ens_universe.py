"""Bloomberg ENS swaption security generation.

The Bloomberg ENS universe is two-dimensional:
option expiry x underlying swap tenor.
"""
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

def build_ens_security(offset_bp: float, expiry_years: int, swap_tenor_years: int, index: str, yellow_key: str = "Curncy") -> str:
    if offset_bp not in BLOOMBERG_FIELDS:
        raise ValueError(f"unsupported ENS offset: {offset_bp}")
    return f"{BLOOMBERG_FIELDS[offset_bp]}{maturity_code(expiry_years)}{swap_tenor_years:02d} {index} {yellow_key}"

def build_atm_security(expiry_years: int, swap_tenor_years: int, index: str, yellow_key: str = "Curncy") -> str:
    return f"ENPS{maturity_code(expiry_years)}{swap_tenor_years:02d} {index} {yellow_key}"

def build_ens_universe(expiries: Sequence[int], swap_tenors: Sequence[int], index: str, yellow_key: str = "Curncy") -> dict[tuple[int,int], list[ENSSecurity]]:
    return {
        (expiry, tenor): [
            ENSSecurity(offset, build_ens_security(offset, expiry, tenor, index, yellow_key))
            for offset in BLOOMBERG_FIELDS
        ]
        for expiry in expiries for tenor in swap_tenors
    }
