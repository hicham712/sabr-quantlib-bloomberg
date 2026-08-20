"""Market convention and strike construction for Bloomberg swaption smiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# User-confirmed Bloomberg ticker suffixes for absolute strike offsets from
# the ATM-forward swap rate. The ENS* names are the actual Bloomberg fields.
BLOOMBERG_FIELDS: Mapping[float, str] = {
    -150.0: "ENSH",
    -100.0: "ENSI",
    -50.0: "ENSK",
    -25.0: "ENSL",
    25.0: "ENSM",
    50.0: "ENSN",
    100.0: "ENSP",
    150.0: "ENSQ",
}

STRIKE_OFFSETS_BP = tuple(BLOOMBERG_FIELDS)


@dataclass(frozen=True)
class BloombergQuoteSet:
    """One swaption smile observation returned by Bloomberg."""

    security: str
    expiry: str
    forward: float
    quotes_by_offset_bp: Mapping[float, float]


def strikes_from_forward(forward: float) -> list[float]:
    """Build absolute strikes from the ATM-forward rate and bp offsets."""
    if forward <= 0.0:
        raise ValueError("forward must be positive")
    return [forward + offset_bp / 10_000.0 for offset_bp in STRIKE_OFFSETS_BP]


def available_smile_points(
    forward: float, quotes_by_offset_bp: Mapping[float, float | None]
) -> tuple[list[float], list[float]]:
    """Return sorted strikes/vols while dropping unavailable Bloomberg quotes."""
    if forward <= 0.0:
        raise ValueError("forward must be positive")

    points = []
    for offset in STRIKE_OFFSETS_BP:
        vol = quotes_by_offset_bp.get(offset)
        if vol is None or vol <= 0.0:
            continue
        strike = forward + offset / 10_000.0
        if strike <= 0.0:
            continue
        points.append((strike, float(vol)))

    points.sort(key=lambda item: item[0])
    return [p[0] for p in points], [p[1] for p in points]


def build_smile(
    security: str,
    expiry: str,
    forward: float,
    quotes_by_offset_bp: Mapping[float, float | None],
) -> BloombergQuoteSet:
    """Validate and normalize one Bloomberg smile observation."""
    strikes, vols = available_smile_points(forward, quotes_by_offset_bp)
    if len(strikes) < 3:
        raise ValueError(
            f"{security}: at least three valid Bloomberg smile quotes are required"
        )
    normalized = {
        round((strike - forward) * 10_000.0, 8): vol
        for strike, vol in zip(strikes, vols)
    }
    return BloombergQuoteSet(security, expiry, forward, normalized)
