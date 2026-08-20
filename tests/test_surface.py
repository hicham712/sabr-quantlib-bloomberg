from src.surface import BLOOMBERG_FIELDS, available_quotes, strikes_from_forward


def test_bloomberg_field_mapping():
    assert BLOOMBERG_FIELDS == {
        -150.0: "ENSH",
        -100.0: "ENSI",
        -50.0: "K",
        -25.0: "L",
        25.0: "M",
        50.0: "N",
        100.0: "P",
        150.0: "Q",
    }


def test_absolute_offsets_from_forward():
    assert strikes_from_forward(0.03, [-50.0, 0.0, 50.0]) == [0.025, 0.03, 0.035]


def test_missing_quotes_are_ignored():
    points = available_quotes({-50.0: 0.01, -25.0: None, 25.0: 0.02})
    assert [p.offset_bp for p in points] == [-50.0, 25.0]
