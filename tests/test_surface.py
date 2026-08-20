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


def test_absolute_strikes_are_built_from_forward():
    strikes, vols = available_smile_points(
        0.03,
        {-50.0: 0.40, -25.0: 0.38, 25.0: 0.36, 50.0: None},
    )
    assert strikes == [0.025, 0.0275, 0.0325]
    assert vols == [0.40, 0.38, 0.36]
