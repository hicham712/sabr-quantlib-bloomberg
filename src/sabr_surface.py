"""Maturity-interpolated QuantLib normal-SABR volatility surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .sabr import SABRParameters, SABRSmile, calibrate_sabr


@dataclass(frozen=True)
class SABRNode:
    expiry: float
    forward: float
    parameters: SABRParameters


class SABRSurface:
    """Interpolate calibrated normal-SABR nodes in maturity.

    No maturity extrapolation is allowed: queries must lie between the
    shortest and longest calibrated nodes. Strike extrapolation is delegated
    to the QuantLib SABR interpolation only when explicitly requested.
    """

    def __init__(self, nodes: Sequence[SABRNode], smiles: Sequence[SABRSmile] | None = None):
        if not nodes:
            raise ValueError("at least one SABR node is required")
        ordered = sorted(nodes, key=lambda n: n.expiry)
        if any(n.expiry <= 0.0 or n.forward <= 0.0 for n in ordered):
            raise ValueError("node expiry and forward must be positive")
        if any(a.expiry == b.expiry for a, b in zip(ordered, ordered[1:])):
            raise ValueError("node expiries must be unique")
        self._nodes = tuple(ordered)
        self._smiles = tuple(smiles) if smiles is not None else None

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
                if xs[i] == xs[i + 1]:
                    return ys[i]
                w = (x - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] + w * (ys[i + 1] - ys[i])
        return ys[-1]

    def parameters(self, expiry: float) -> SABRParameters:
        xs = [n.expiry for n in self._nodes]
        alpha = self._interp(expiry, xs, [n.parameters.alpha for n in self._nodes])
        beta = self._interp(expiry, xs, [n.parameters.beta for n in self._nodes])
        rho = self._interp(expiry, xs, [n.parameters.rho for n in self._nodes])
        nu = self._interp(expiry, xs, [n.parameters.nu for n in self._nodes])
        return SABRParameters(alpha, beta, rho, nu)

    def forward(self, expiry: float) -> float:
        return self._interp(expiry, [n.expiry for n in self._nodes], [n.forward for n in self._nodes])

    def volatility(self, expiry: float, strike: float, allow_strike_extrapolation: bool = False) -> float:
        """Return normal SABR volatility at arbitrary expiry/strike."""
        if strike <= 0.0:
            raise ValueError("strike must be positive")
        fwd = self.forward(expiry)
        p = self.parameters(expiry)
        # Reconstruct a QuantLib SABR interpolation for the requested
        # maturity. This uses the same normal-vol convention as calibration.
        atm = p.alpha / (fwd ** (1.0 - p.beta))
        smile = calibrate_sabr(
            fwd,
            expiry,
            [fwd],
            [atm],
            beta=p.beta,
            alpha=p.alpha,
            rho=p.rho,
            nu=p.nu,
            vega_weighted=False,
        )
        return smile.volatility(strike, allow_strike_extrapolation)
