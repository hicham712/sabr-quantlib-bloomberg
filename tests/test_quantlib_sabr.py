import pytest

from src.quantlib_sabr import BLOOMBERG_FIELDS, calibrate_sabr, sabr_volatility, strikes_from_forward


def test_bloomberg_mapping():
    assert BLOOMBERG_FIELDS[-150.0] == "ENSH"
    assert BLOOMBERG_FIELDS[-100.0] == "ENSI"
    assert BLOOMBERG_FIELDS[-50.0] == "ENSK"
    assert BLOOMBERG_FIELDS[-25.0] == "ENSL"
    assert BLOOMBERG_FIELDS[25.0] == "ENSM"
    assert BLOOMBERG_FIELDS[50.0] == "ENSN"
    assert BLOOMBERG_FIELDS[100.0] == "ENSP"
    assert BLOOMBERG_FIELDS[150.0] == "ENSQ"


def test_strikes_are_absolute_offsets_from_forward():
    assert strikes_from_forward(0.03, [-50.0, 0.0, 50.0]) == pytest.approx([0.025, 0.03, 0.035])


def test_calibration_and_repricing():
    forward = 0.03
    quotes = {-150: 0.24, -100: 0.225, -50: 0.212, -25: 0.207, 25: 0.204, 50: 0.207, 100: 0.216, 150: 0.232}
    result = calibrate_sabr(forward, 5.0, quotes)
    assert result.beta == pytest.approx(0.5)
    assert -1.0 < result.rho < 1.0
    assert result.nu > 0.0
    assert sabr_volatility(forward, forward, 5.0, result) > 0.0


def test_missing_quotes_are_ignored():
    result = calibrate_sabr(0.03, 2.0, {-100: 0.22, -50: None, 50: 0.21, 100: 0.22})
    assert len(result.strikes) == 3


def test_too_few_quotes():
    with pytest.raises(ValueError, match="at least three"):
        calibrate_sabr(0.03, 2.0, {-50: 0.21, 50: 0.21})
