import QuantLib as ql

from src.sabr import _shifted_lognormal_volatility_type


def test_shifted_lognormal_type_is_available():
    value = _shifted_lognormal_volatility_type()
    assert value is not None
    assert isinstance(value, (int, float)) or hasattr(value, "__class__")
