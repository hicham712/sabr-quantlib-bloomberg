"""Maturity-interpolated QuantLib normal-SABR volatility surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import QuantLib as ql

from .sabr import SABRParameters


@dataclass(frozen=True)
class SABRNode:
    expiry: float
    forward: float
    parameters: SABRParameters


class SABRSurface:
    """Interpolate calibrated normal-SABR nodes in maturity.

    Maturity extrapolation is rejected. Strike evaluation uses QuantLib's
    closed-form SABR normal-volatility implementation.
    """

    def __init__(self, nodes: Sequence[SABRNode]):
        if not nodes:
            raise ValueError("at least one SABR node is required")
        ordered = sorted(nodes, key=lambda n: n.expiry)
        if any(n.expiry <= 0.0 or n.forward <= 0.0 for n in ordered):
            raise ValueError("node expiry and forward must be positive")
        if any(a.expiry == b.expiry for a, b in zip(ordered, ordered[1:])):
            raise ValueError("node expiries must be unique")
        self._nodes = tuple(ordered)

    @property
    def nodes(self) -> tuple[SABRNode, ...]:
        return self._nodes

    @property
    def min_expiry(self) -> float:
        return self._nodes[0].expiry

    @property
    def max_expiry(self) -> float:
        return self._nodes[-1].expiry

    @staticmethod
    def _interp(x: float, xs: list[float], ys: list[float]) -> float:
        if x < xs[0] or x > xs[-1]:
            raise ValueError(f"expiry {x} outside surface range [{xs[0]}, {xs[-1]}]")
        if len(xs) == 1:
            return ys[0]
        for i in range(len(xs) - 1):
            if xs[i] <= x <= xs[i + 1]:
                w = (x - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] + w * (ys[i + 1] - ys[i])
        return ys[-1]

    def parameters(self, expiry: float) -> SABRParameters:
        xs = [n.expiry for n in self._nodes]
        return SABRParameters(
            self._interp(expiry, xs, [n.parameters.alpha for n in self._nodes]),
            self._interp(expiry, xs, [n.parameters.beta for n in self._nodes]),
            self._interp(expiry, xs, [n.parameters.rho for n in self._nodes]),
            self._interp(expiry, xs, [n.parameters.nu for n in self._nodes]),
        )

    def forward(self, expiry: float) -> float:
        return self._interp(expiry, [n.expiry for n in self._nodes], [n.forward for n in self._nodes])

    @staticmethod
    def _normal_type():
        vt = getattr(ql, "VolatilityType", None)
        if vt is not None and hasattr(vt, "Normal"):
            return vt.Normal
        normal = getattr(ql, "Normal", None)
        if normal is not None:
            return normal
        return 0

    def volatility(self, expiry: float, strike: float, allow_strike_extrapolation: bool = False) -> float:
        """Return normal SABR volatility at arbitrary expiry and strike."""
        if strike <= 0.0:
            raise ValueError("strike must be positive")
        forward = self.forward(expiry)
        p = self.parameters(expiry)
        # QuantLib-SWIG exposes the SABR formula directly. Its volatility-type
        # argument selects the same Normal convention used for calibration.
        try:
            return float(ql.sabrVolatility(
                strike, forward, expiry,
                p.alpha, p.beta, p.nu, p.rho,
                self._normal_type(),
            ))
        except TypeError:
            raise RuntimeError("installed QuantLib binding does not expose normal sabrVolatility") from None

    def parameters_at_grid(self, expiries: Sequence[float]) -> list[tuple[float, float, SABRParameters]]:
        return [(float(t), self.forward(float(t)), self.parameters(float(t))) for t in expiries]
