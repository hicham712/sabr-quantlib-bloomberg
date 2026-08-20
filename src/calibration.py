"""SABR calibration against Bloomberg smile points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.optimize import least_squares

from .sabr import hagan_lognormal_vol
from .surface import QuotePoint, strikes_from_forward


@dataclass(frozen=True)
class SABRParameters:
    alpha: float
    beta: float
    rho: float
    nu: float


def calibrate_sabr(
    forward: float,
    expiry: float,
    quotes: Sequence[QuotePoint],
    beta: float = 0.5,
) -> SABRParameters:
    """Fit alpha, rho and nu to all available smile quotes with beta fixed."""
    if len(quotes) < 3:
        raise ValueError("At least three smile quotes are required for calibration")
    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie in [0, 1]")

    strikes = np.asarray(strikes_from_forward(forward, [q.offset_bp for q in quotes]))
    market_vols = np.asarray([q.volatility for q in quotes], dtype=float)
    if np.any(strikes <= 0):
        raise ValueError("strike offsets produce a non-positive strike")

    # alpha starts near ATM vol * F^(1-beta). rho and nu are initialized in
    # the interior of their admissible domains and then constrained by bounds.
    atm_guess = float(market_vols[np.argmin(np.abs(strikes - forward))])
    alpha0 = max(atm_guess * forward ** (1.0 - beta), 1e-8)
    x0 = np.array([alpha0, 0.0, 0.5])

    def residuals(x: np.ndarray) -> np.ndarray:
        alpha, rho, nu = x
        model = np.array(
            [hagan_lognormal_vol(forward, k, expiry, alpha, beta, rho, nu) for k in strikes]
        )
        return model - market_vols

    result = least_squares(
        residuals,
        x0,
        bounds=([1e-10, -0.9999, 1e-8], [np.inf, 0.9999, np.inf]),
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
        max_nfev=5000,
    )
    if not result.success:
        raise RuntimeError(f"SABR calibration failed: {result.message}")

    alpha, rho, nu = result.x
    return SABRParameters(float(alpha), beta, float(rho), float(nu))
