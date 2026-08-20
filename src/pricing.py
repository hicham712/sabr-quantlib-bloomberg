"""Small pricing/risk API on top of the Bloomberg SABR surface."""

from __future__ import annotations

from dataclasses import dataclass
import math

import QuantLib as ql

from .bbg_surface import BloombergSABRSurface


@dataclass(frozen=True)
class SwaptionResult:
    normal_vol: float
    premium: float
    delta: float
    vega: float


class SABRPricer:
    def __init__(self, surface: BloombergSABRSurface):
        self.surface = surface

    def normal_vol(self, expiry: float, strike: float) -> float:
        return self.surface.volatility(expiry, strike)

    def price(self, expiry: float, strike: float, annuity: float = 1.0, notional: float = 1.0) -> SwaptionResult:
        if annuity <= 0.0 or notional <= 0.0:
            raise ValueError("annuity and notional must be positive")
        forward = self.surface.forward(expiry)
        vol = self.normal_vol(expiry, strike)
        stddev = vol * math.sqrt(expiry)
        if stddev <= 0.0:
            raise ValueError("normal volatility must be positive")
        d = (forward - strike) / stddev
        phi = math.exp(-0.5 * d * d) / math.sqrt(2.0 * math.pi)
        Phi = 0.5 * (1.0 + math.erf(d / math.sqrt(2.0)))
        # Receiver/put-or-call convention is intentionally not embedded here;
        # this is the undiscounted payer/call Bachelier value on a unit annuity.
        premium_per_unit = (forward - strike) * Phi + stddev * phi
        delta = Phi
        vega = math.sqrt(expiry) * phi
        scale = annuity * notional
        return SwaptionResult(vol, scale * premium_per_unit, scale * delta, scale * vega)
