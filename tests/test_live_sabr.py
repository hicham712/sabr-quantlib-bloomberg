import pytest

from src.ens_universe import ENSSecurity
from src.live_sabr import calibrate_maturity
from src.market_surface_runner import MaturityQuotes


def make_quote(forward=0.03):
    offsets = (-150.0, -100.0, -50.0, -25.0, 25.0, 50.0, 100.0, 150.0)
    smile = tuple(ENSSecurity(o, f"S{o}") for o in offsets)
    quotes = {s.ticker: 0.20 + 0.0002 * s.offset_bp**2 / 100.0 for s in smile}
    return MaturityQuotes(5, "EUSA0105 BGN Curncy", forward, smile, quotes)


def test_live_calibration_keeps_beta_fixed():
    result = calibrate_maturity(make_quote(), beta=0.5)
    assert result is not None
    assert result.sabr.beta == pytest.approx(0.5)
    assert len(result.strikes) == 8


def test_missing_forward_is_skipped():
    quote = make_quote()
    quote = MaturityQuotes(5, quote.forward_security, None, quote.smile, quote.quotes)
    assert calibrate_maturity(quote) is None
