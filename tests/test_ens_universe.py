from src.ens_universe import build_ens_security, build_ens_universe, maturity_code


def test_five_year_maturity_code():
    assert maturity_code(5) == "0F05"


def test_user_bloomberg_example():
    assert build_ens_security(-100.0, 5, "IIRO") == "ENSI0F05 IIRO Curncy"


def test_full_five_year_universe():
    securities = build_ens_universe([5], "IIRO")[5]
    assert [s.ticker for s in securities] == [
        "ENSH0F05 IIRO Curncy",
        "ENSI0F05 IIRO Curncy",
        "ENSK0F05 IIRO Curncy",
        "ENSL0F05 IIRO Curncy",
        "ENSM0F05 IIRO Curncy",
        "ENSN0F05 IIRO Curncy",
        "ENSP0F05 IIRO Curncy",
        "ENSQ0F05 IIRO Curncy",
    ]
