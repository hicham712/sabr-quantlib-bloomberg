"""QuantLib-backed SABR smile calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import QuantLib as ql


@dataclass(frozen=True)
class SABRParameters:
    alpha: float
    beta: float
    rho: float
    nu: float


class SABRSmile:
    def __init__(self, interpolation: ql.SABRInterpolation):
        self._interpolation = interpolation

    @property
    def alpha(self) -> float:
        return float(self._interpolation.alpha())

    @property
    def beta(self) -> float:
        return float(self._interpolation.beta())

    @property
    def rho(self) -> float:
        return float(self._interpolation.rho())

    @property
    def nu(self) -> float:
        return float(self._interpolation.nu())

    @property
    def rms_error(self) -> float:
        return float(self._interpolation.rmsError())

    @property
    def max_error(self) -> float:
        return float(self._interpolation.maxError())

    @property
    def parameters(self) -> SABRParameters:
        return SABRParameters(self.alpha, self.beta, self.rho, self.nu)

    def volatility(self, strike: float, allow_extrapolation: bool = False) -> float:
        return float(self._interpolation(strike, allow_extrapolation))


def _shifted_lognormal_volatility_type():
    volatility_type = getattr(ql, "VolatilityType", None)
    if volatility_type is not None and hasattr(volatility_type, "ShiftedLognormal"):
        return volatility_type.ShiftedLognormal
    shifted = getattr(ql, "ShiftedLognormal", None)
    if shifted is not None:
        return shifted
    return None


def calibrate_sabr(
    forward: float,
    expiry: float,
    strikes: Sequence[float],
    volatilities: Sequence[float],
    beta: float = 0.5,
    alpha: float | None = None,
    rho: float = 0.0,
    nu: float = 0.5,
    vega_weighted: bool = True,
    error_accept: float = 1.0e-8,
) -> SABRSmile:
    if forward <= 0.0 or expiry <= 0.0:
        raise ValueError("forward and expiry must be positive")
    if len(strikes) != len(volatilities) or len(strikes) < 3:
        raise ValueError("matching strikes/volatilities with at least 3 points are required")
    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie in [0, 1]")
    if any(k <= 0.0 for k in strikes) or any(v <= 0.0 for v in volatilities):
        raise ValueError("strikes and volatilities must be positive")

    if alpha is None:
        atm_vol = float(volatilities[min(range(len(strikes)), key=lambda i: abs(strikes[i] - forward))])
        alpha = max(atm_vol * forward ** (1.0 - beta), 1.0e-8)

    end_criteria = ql.EndCriteria(1000, 100, 1.0e-10, 1.0e-10, 1.0e-10)
    args = [
        list(strikes), list(volatilities), float(expiry), float(forward),
        float(alpha), float(beta), float(nu), float(rho),
        False, True, False, False, bool(vega_weighted),
        end_criteria, None, float(error_accept), False, 100, 0.0,
    ]
    volatility_type = _shifted_lognormal_volatility_type()
    if volatility_type is not None:
        args.append(volatility_type)

    # QuantLib-SWIG performs calibration during construction. The Python
    # SABRInterpolation binding does not expose update() or enableExtrapolation().
    return SABRSmile(ql.SABRInterpolation(*args))
