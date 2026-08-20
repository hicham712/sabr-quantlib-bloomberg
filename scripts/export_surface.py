"""Build and export the Bloomberg-node SABR surface as CSV and JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def write_surface(rows: list[dict[str, object]], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["expiry", "forward", "strike", "offset_bp", "market_normal_vol", "sabr_normal_vol", "alpha", "beta", "rho", "nu", "rms_error"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a Bloomberg-node SABR surface from a calibration JSON file")
    parser.add_argument("input", type=Path, help="JSON produced by build_surface.py --output-json")
    parser.add_argument("--csv", type=Path, default=Path("output/sabr_surface.csv"))
    parser.add_argument("--json", type=Path, default=Path("output/sabr_surface.json"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    rows = []
    for node in data["nodes"]:
        for quote in node["quotes"]:
            rows.append({"expiry": node["expiry"], "forward": node["forward"], "strike": quote["strike"], "offset_bp": quote["offset_bp"], "market_normal_vol": quote["market_normal_vol"], "sabr_normal_vol": quote["sabr_normal_vol"], "alpha": node["alpha"], "beta": node["beta"], "rho": node["rho"], "nu": node["nu"], "rms_error": node["rms_error"]})
    write_surface(rows, args.csv, args.json)
    print(f"Wrote {len(rows)} surface points to {args.csv}")
    print(f"Wrote {len(data['nodes'])} Bloomberg maturity nodes to {args.json}")


if __name__ == "__main__":
    main()
