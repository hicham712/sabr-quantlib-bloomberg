import QuantLib as ql

from src.sabr import calibrate_sabr
from src.surface import BLOOMBERG_FIELDS


def test_quantlib_sabr_calibration_recovers_synthetic_smile():
    forward = 0.0325
    expiry = 5.0
    beta = 0.5
    alpha = 0.012
    rho = -0.35
    nu = 0.42
    offsets = list(BLOOMBERG_FIELDS)
    strikes = [forward + offset / 10_000.0 for offset in offsets]
    vols = [
        ql.sabrVolatility(k, forward, expiry, alpha, beta, nu, rho)
        for k in strikes
    ]

    smile = calibrate_sabr(forward, expiry, strikes, vols, beta=beta)

    assert smile.beta == beta
    assert abs(smile.alpha - alpha) < 1e-5
    assert abs(smile.rho - rho) < 1e-5
    assert abs(smile.nu - nu) < 1e-5
    assert smile.rms_error < 1e-7


def test_beta_is_fixed():
    smile = calibrate_sabr(
        0.03,
        2.0,
        [0.015, 0.025, 0.03, 0.035, 0.045],
        [0.65, 0.48, 0.42, 0.39, 0.37],
        beta=0.5,
    )
    assert smile.beta == 0.5
