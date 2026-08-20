from src.forward_universe import build_forward_security, forward_maturity_code


def test_forward_maturity_code():
    assert forward_maturity_code(1) == "01"


def test_user_bloomberg_forward_example():
    assert build_forward_security(1) == "EUSA0101 BGN Curncy"


def test_five_year_forward():
    assert build_forward_security(5) == "EUSA0105 BGN Curncy"
