from src.surface import BLOOMBERG_FIELDS, available_smile_points


def test_confirmed_bloomberg_ens_mapping():
    assert BLOOMBERG_FIELDS == {
        -150.0: "ENSH",
        -100.0: "ENSI",
        -50.0: "ENSK",
        -25.0: "ENSL",
        25.0: "ENSM",
        50.0: "ENSN",
        100.0: "ENSP",
        150.0: "ENSQ",
    }


def test_absolute_strikes_include_bloomberg_atm_point():
    strikes, vols = available_smile_points(
        0.03,
        {-50.0: -3.0, -25.0: -2.0, 25.0: 2.0, 50.0: None},
        atm_vol_bp=70.0,
    )
    assert strikes == [0.025, 0.0275, 0.03, 0.0325]
    assert vols == [0.0067, 0.0068, 0.0070, 0.0072]
