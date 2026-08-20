"""QuantLib-backed SABR calibration for Bloomberg swaption smiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import QuantLib as ql

BLOOMBERG_FIELDS: Mapping[float, str] = {
    -150.0: "ENSH", -100.0: "ENSI", -50.0: "ENSK", -25.0: "ENSL",
    25.0: "ENSM", 50.0: "ENSN", 100.0: "ENSP", 150.0: "ENSQ",
}

@dataclass(frozen=True)
class SABRConfig:
    beta: float = 0.5
    alpha: float = 0.03
    rho: float = 0.0
    nu: float = 0.3

@dataclass(frozen=True)
class SABRResult:
    alpha: float
    beta: float
    rho: float
    nu: float
    strikes: tuple[float, ...]
    market_vols: tuple[float, ...]


def strikes_from_forward(forward: float, offsets_bp: list[float]) -> list[float]:
    if forward <= 0.0:
        raise ValueError("forward must be positive for lognormal SABR")
    return [forward + x / 10_000.0 for x in offsets_bp]


def calibrate_sabr(
    forward: float,
    expiry: float,
    quotes_by_offset: Mapping[float, float | None],
    config: SABRConfig = SABRConfig(),
) -> SABRResult:
    """Calibrate alpha, rho and nu with QuantLib SABRInterpolation; beta is fixed."""
    if expiry <= 0.0:
        raise ValueError("expiry must be positive")
    points = sorted(
        (float(k), float(v)) for k, v in quotes_by_offset.items()
        if v is not None and float(v) > 0.0
    )
    if len(points) < 3:
        raise ValueError("at least three valid smile quotes are required")
    offsets = [x[0] for x in points]
    strikes = strikes_from_forward(forward, offsets)
    vols = [x[1] for x in points]
    if any(k <= 0.0 for k in strikes):
        raise ValueError("all strikes must be positive for lognormal SABR")

    interpolation = ql.SABRInterpolation(
        strikes, vols, expiry, forward,
        config.alpha, config.beta, config.nu, config.rho,
        False, True, False, False, False,
    )
    return SABRResult(
        float(interpolation.alpha()), float(interpolation.beta()),
        float(interpolation.rho()), float(interpolation.nu()),
        tuple(strikes), tuple(vols),
    )


def sabr_volatility(forward: float, strike: float, expiry: float, result: SABRResult) -> float:
    return float(ql.sabrVolatility(
        strike, forward, expiry, result.alpha, result.beta, result.nu, result.rho
    ))
