import pytest
import QuantLib as ql

from src.quantlib_sabr import BLOOMBERG_FIELDS, calibrate_sabr, sabr_volatility, strikes_from_forward


def test_bloomberg_mapping():
    assert list(BLOOMBERG_FIELDS.values()) == ["ENSH", "ENSI", "ENSK", "ENSL", "ENSM", "ENSN", "ENSP", "ENSQ"]


def test_strikes_are_absolute_offsets_from_forward():
    assert strikes_from_forward(0.03, [-50.0, 0.0, 50.0]) == pytest.approx([0.025, 0.03, 0.035])


def test_quantlib_calibration_reprices_quotes():
    forward, expiry = 0.03, 5.0
    alpha, beta, rho, nu = 0.02, 0.5, -0.25, 0.35
    offsets = [-150, -100, -50, -25, 25, 50, 100, 150]
    quotes = {
        offset: ql.sabrVolatility(forward + offset / 10000.0, forward, expiry, alpha, beta, nu, rho)
        for offset in offsets
    }
    result = calibrate_sabr(forward, expiry, quotes)
    assert result.beta == pytest.approx(beta)
    for offset, market_vol in quotes.items():
        strike = forward + offset / 10000.0
        assert sabr_volatility(forward, strike, expiry, result) == pytest.approx(market_vol, rel=1e-5)


def test_missing_quotes_are_ignored():
    result = calibrate_sabr(0.03, 2.0, {-100: 0.22, -50: None, 50: 0.21, 100: 0.22})
    assert len(result.strikes) == 3


def test_too_few_quotes():
    with pytest.raises(ValueError, match="at least three"):
        calibrate_sabr(0.03, 2.0, {-50: 0.21, 50: 0.21})
