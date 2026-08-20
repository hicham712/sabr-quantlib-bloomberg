from __future__ import annotations

import pytest

from src.bbg_surface import BloombergSABRSurface, SABRSmileNode


class DummySmile:
    parameters = type("P", (), {"alpha": 1.0, "beta": 0.5, "rho": 0.1, "nu": 0.2})()

    def volatility(self, strike, allow_extrapolation=False):
        return strike


def test_surface_exposes_only_observed_nodes():
    surface = BloombergSABRSurface([
        SABRSmileNode(10.0, 0.03, DummySmile()),
        SABRSmileNode(2.0, 0.031, DummySmile()),
    ])
    assert surface.expiries == (2.0, 10.0)
    assert surface.forward(2.0) == 0.031
    with pytest.raises(ValueError, match="does not provide"):
        surface.forward(5.0)


def test_surface_rejects_duplicate_expiry():
    with pytest.raises(ValueError, match="unique"):
        BloombergSABRSurface([
            SABRSmileNode(2.0, 0.03, DummySmile()),
            SABRSmileNode(2.0, 0.031, DummySmile()),
        ])
