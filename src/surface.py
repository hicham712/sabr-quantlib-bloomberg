"""Bloomberg swaption strike-offset conventions and surface helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class QuotePoint:
    """One Bloomberg smile quote at an absolute strike offset."""

    offset_bp: float
    volatility: float


# User-confirmed Bloomberg convention for the smile columns.
BLOOMBERG_FIELDS: Mapping[float, str] = {
    -150.0: "ENSH",
    -100.0: "ENSI",
    -50.0: "K",
    -25.0: "L",
    25.0: "M",
    50.0: "N",
    100.0: "P",
    150.0: "Q",
}


@dataclass(frozen=True)
class SABRConfig:
    """Calibration configuration."""

    beta: float = 0.5


def strikes_from_forward(forward: float, offsets_bp: list[float]) -> list[float]:
    """Convert absolute bp offsets into strikes around the ATM forward."""
    if forward <= 0:
        raise ValueError("forward must be positive")
    return [forward + offset_bp / 10_000.0 for offset_bp in offsets_bp]


def available_quotes(
    quotes_by_offset: Mapping[float, float | None],
) -> list[QuotePoint]:
    """Return available smile points, preserving increasing strike-offset order."""
    points = [
        QuotePoint(offset, vol)
        for offset, vol in quotes_by_offset.items()
        if vol is not None and vol > 0
    ]
    return sorted(points, key=lambda point: point.offset_bp)
