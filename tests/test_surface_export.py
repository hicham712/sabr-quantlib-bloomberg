from __future__ import annotations

import json

from scripts.export_surface import write_surface


def test_write_surface(tmp_path):
    rows = [{
        "expiry": "2Y", "forward": 0.03144, "strike": 0.01644,
        "offset_bp": -150.0, "market_normal_vol": 0.00939,
        "sabr_normal_vol": 0.0094, "alpha": 0.0038, "beta": 0.5,
        "rho": 0.36, "nu": 1.0, "rms_error": 2.8e-5,
    }]
    csv_path = tmp_path / "surface.csv"
    json_path = tmp_path / "surface.json"
    write_surface(rows, csv_path, json_path)
    assert csv_path.exists()
    assert json.loads(json_path.read_text())[0]["expiry"] == "2Y"
    assert "market_normal_vol" in csv_path.read_text()
