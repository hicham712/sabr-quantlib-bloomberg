"""Calibrate QuantLib SABR directly from live Bloomberg observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .market_surface_runner import MaturityQuotes
from .sabr import SABRSmile, calibrate_sabr
from .surface import STRIKE_OFFSETS_BP, available_smile_points


@dataclass(frozen=True)
class CalibratedMaturity:
    years: int
    forward: float
    strikes: tuple[float, ...]
    volatilities: tuple[float, ...]
    sabr: SABRSmile


def calibrate_maturity(quote: MaturityQuotes, beta: float = 0.5) -> CalibratedMaturity | None:
    """Calibrate one maturity; return None when Bloomberg data is insufficient."""
    if quote.forward is None or quote.forward <= 0.0:
        return None

    quotes_by_offset = {}
    for security, value in quote.quotes.items():
        offset = next((s.offset_bp for s in quote.smile if s.ticker == security), None)
        if offset is not None:
            quotes_by_offset[offset] = value

    strikes, vols = available_smile_points(quote.forward, quotes_by_offset)
    if len(strikes) < 3:
        return None

    sabr = calibrate_sabr(
        forward=quote.forward,
        expiry=float(quote.years),
        strikes=strikes,
        volatilities=vols,
        beta=beta,
    )
    return CalibratedMaturity(quote.years, quote.forward, tuple(strikes), tuple(vols), sabr)


def calibrate_surface(quotes: Iterable[MaturityQuotes], beta: float = 0.5) -> list[CalibratedMaturity]:
    """Calibrate all maturities for which Bloomberg supplies enough data."""
    results = []
    for quote in quotes:
        calibrated = calibrate_maturity(quote, beta=beta)
        if calibrated is not None:
            results.append(calibrated)
    return results
