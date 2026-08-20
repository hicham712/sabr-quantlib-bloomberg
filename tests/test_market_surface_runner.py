from src.market_surface_runner import MaturityQuotes, available_maturities
from src.ens_universe import ENSSecurity


def test_filters_missing_forward_and_sparse_smiles():
    smile = tuple(ENSSecurity(float(x), f"S{x}") for x in (-150, -100, -50, -25, 25, 50, 100, 150))
    good = MaturityQuotes(5, "EUSA0105 BGN Curncy", 2.5, smile, {s.ticker: 1.0 for s in smile[:3]})
    bad_forward = MaturityQuotes(10, "EUSA0110 BGN Curncy", None, smile, {s.ticker: 1.0 for s in smile})
    bad_smile = MaturityQuotes(15, "EUSA0115 BGN Curncy", 2.5, smile, {s.ticker: 1.0})

    result = available_maturities([good, bad_forward, bad_smile], minimum_smile_points=3)
    assert [q.years for q in result] == [5]
