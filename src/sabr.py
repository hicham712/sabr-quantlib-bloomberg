"""SABR implied volatility utilities.

The implementation follows the standard Hagan lognormal SABR approximation.
Beta is configurable and is set to 0.5 by the surface layer by default.
"""

from __future__ import annotations

import math


def hagan_lognormal_vol(
    forward: float,
    strike: float,
    expiry: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
) -> float:
    """Return the Hagan lognormal SABR implied volatility.

    Rates and strikes must use the same units. Expiry is in years.
    """
    if min(forward, strike, expiry, alpha, nu) <= 0:
        raise ValueError("forward, strike, expiry, alpha and nu must be positive")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must lie strictly between -1 and 1")
    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie in [0, 1]")

    one_minus_beta = 1.0 - beta
    fk = forward * strike
    log_fk = math.log(forward / strike)

    if abs(log_fk) < 1e-12:
        # ATM limit of the Hagan formula.
        f_beta = forward ** one_minus_beta
        correction = (
            (one_minus_beta**2 / 24.0) * alpha**2 / (f_beta**2)
            + rho * beta * nu * alpha / (4.0 * f_beta)
            + (2.0 - 3.0 * rho**2) * nu**2 / 24.0
        )
        return alpha / f_beta * (1.0 + correction * expiry)

    z = (nu / alpha) * fk ** (one_minus_beta / 2.0) * log_fk
    x_z = math.log((math.sqrt(1.0 - 2.0 * rho * z + z * z) + z - rho) / (1.0 - rho))

    denominator = (
        fk ** (one_minus_beta / 2.0)
        * (1.0 + one_minus_beta**2 * log_fk**2 / 24.0 + one_minus_beta**4 * log_fk**4 / 1920.0)
    )
    correction = (
        one_minus_beta**2 * alpha**2 / (24.0 * fk**one_minus_beta)
        + rho * beta * nu * alpha / (4.0 * fk ** (one_minus_beta / 2.0))
        + (2.0 - 3.0 * rho**2) * nu**2 / 24.0
    )

    return alpha / denominator * (z / x_z) * (1.0 + correction * expiry)
