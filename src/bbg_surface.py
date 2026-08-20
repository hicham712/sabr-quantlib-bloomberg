"""Collection of Bloomberg-observed SABR smiles; no maturity interpolation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .sabr import SABRSmile, SABRParameters


@dataclass(frozen=True)
class SABRSmileNode:
    """A SABR smile calibrated only from one Bloomberg-supported expiry."""

    expiry: float
    forward: float
    smile: SABRSmile

    @property
    def parameters(self) -> SABRParameters:
        return self.smile.parameters


class BloombergSABRSurface:
    """Node-based surface containing only maturities observed in Bloomberg.

    There is deliberately no interpolation or extrapolation in expiry. The
    SABR model is used only in strike to evaluate between the observed smile
    points at a supported expiry.
    """

    def __init__(self, nodes: Iterable[SABRSmileNode]):
        ordered = sorted(nodes, key=lambda node: node.expiry)
        if not ordered:
            raise ValueError("at least one Bloomberg SABR node is required")
        if any(node.expiry <= 0.0 or node.forward <= 0.0 for node in ordered):
            raise ValueError("node expiry and forward must be positive")
        if any(a.expiry == b.expiry for a, b in zip(ordered, ordered[1:])):
            raise ValueError("node expiries must be unique")
        self._nodes = tuple(ordered)
        self._by_expiry = {node.expiry: node for node in ordered}

    @property
    def nodes(self) -> tuple[SABRSmileNode, ...]:
        return self._nodes

    @property
    def expiries(self) -> tuple[float, ...]:
        return tuple(node.expiry for node in self._nodes)

    def node(self, expiry: float) -> SABRSmileNode:
        try:
            return self._by_expiry[float(expiry)]
        except KeyError as exc:
            available = ", ".join(f"{x:g}Y" for x in self.expiries)
            raise ValueError(f"Bloomberg does not provide a calibrated {expiry:g}Y node; available: {available}") from exc

    def parameters(self, expiry: float) -> SABRParameters:
        return self.node(expiry).parameters

    def forward(self, expiry: float) -> float:
        return self.node(expiry).forward

    def volatility(self, expiry: float, strike: float, allow_strike_extrapolation: bool = False) -> float:
        return self.node(expiry).smile.volatility(strike, allow_strike_extrapolation)

    def smile(self, expiry: float) -> SABRSmile:
        return self.node(expiry).smile
