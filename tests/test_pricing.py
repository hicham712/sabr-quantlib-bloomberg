import math

from src.pricing import SABRPricer, SwaptionResult


def test_bachelier_price_at_atm():
    class Surface:
        def forward(self, expiry):
            return 0.03

        def volatility(self, expiry, strike):
            return 0.007

    result = SABRPricer(Surface()).price(5.0, 0.03)
    expected = 0.007 * math.sqrt(5.0) / math.sqrt(2.0 * math.pi)
    assert isinstance(result, SwaptionResult)
    assert math.isclose(result.premium, expected)
    assert math.isclose(result.delta, 0.5)


def test_rejects_invalid_scale():
    class Surface:
        def forward(self, expiry):
            return 0.03

        def volatility(self, expiry, strike):
            return 0.007

    try:
        SABRPricer(Surface()).price(5.0, 0.03, annuity=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid annuity to raise")
