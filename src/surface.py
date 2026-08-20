"""Market convention and strike construction for Bloomberg swaption smiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

BLOOMBERG_FIELDS: Mapping[float, str] = {
    -150.0: "ENSH", -100.0: "ENSI", -50.0: "ENSK", -25.0: "ENSL",
    25.0: "ENSM", 50.0: "ENSN", 100.0: "ENSP", 150.0: "ENSQ",
}
STRIKE_OFFSETS_BP = tuple(BLOOMBERG_FIELDS)

@dataclass(frozen=True)
class BloombergQuoteSet:
    security: str
    expiry: str
    forward: float
    quotes_by_offset_bp: Mapping[float, float]

def strikes_from_forward(forward: float) -> list[float]:
    if forward <= 0.0:
        raise ValueError("forward must be positive")
    return [forward + offset / 10_000.0 for offset in STRIKE_OFFSETS_BP]

def absolute_volatilities(atm_vol_pct: float, quotes_by_offset_bp: Mapping[float, float | None]) -> dict[float, float]:
    """Convert Bloomberg percentage-point ATM/add-ons into decimal vols."""
    if atm_vol_pct is None or atm_vol_pct <= 0.0:
        raise ValueError("ATM volatility must be positive")
    result = {}
    for offset in STRIKE_OFFSETS_BP:
        addon = quotes_by_offset_bp.get(offset)
        if addon is None:
            continue
        vol_pct = float(atm_vol_pct) + float(addon)
        if vol_pct > 0.0:
            result[offset] = vol_pct / 100.0
    return result

def available_smile_points(forward: float, quotes_by_offset_bp: Mapping[float, float | None], atm_vol_pct: float | None = None) -> tuple[list[float], list[float]]:
    if forward <= 0.0:
        raise ValueError("forward must be positive")
    if atm_vol_pct is None:
        raise ValueError("atm_vol_pct is required for ENS volatility add-ons")
    absolute = absolute_volatilities(atm_vol_pct, quotes_by_offset_bp)
    points = [(forward + offset / 10_000.0, absolute[offset]) for offset in STRIKE_OFFSETS_BP if offset in absolute and forward + offset / 10_000.0 > 0.0]
    points.sort(key=lambda item: item[0])
    return [p[0] for p in points], [p[1] for p in points]

def build_smile(security: str, expiry: str, forward: float, quotes_by_offset_bp: Mapping[float, float | None], atm_vol_pct: float) -> BloombergQuoteSet:
    strikes, vols = available_smile_points(forward, quotes_by_offset_bp, atm_vol_pct)
    if len(strikes) < 3:
        raise ValueError(f"{security}: at least three valid Bloomberg smile quotes are required")
    normalized = {round((strike - forward) * 10_000.0, 8): vol for strike, vol in zip(strikes, vols)}
    return BloombergQuoteSet(security, expiry, forward, normalized)
