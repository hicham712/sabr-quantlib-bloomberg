"""Fetch Bloomberg ENS smiles and calibrate one QuantLib SABR smile per maturity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.bloomberg_desktop import BloombergDesktopClient
from src.ens_universe import build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import available_smile_points


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8194)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    field = config.get("field", "PX_LAST")
    index = config.get("index", "IIRO")
    yellow_key = config.get("yellow_key", "Curncy")
    years = config.get("maturity_years", list(range(1, 31)))
    universe = build_ens_universe(years, index, yellow_key)

    securities = []
    forward_by_year = {}
    for year in years:
        securities.extend(item.ticker for item in universe[year])
        forward = config.get("forward_security_template", "EUSA01{years:02d} BGN Curncy").format(years=year)
        forward_by_year[year] = forward
        securities.append(forward)

    with BloombergDesktopClient(host=args.host, port=args.port) as bloomberg:
        values = bloomberg.get(securities, field)

    for year in years:
        expiry = f"{year}Y"
        forward = values.get(forward_by_year[year])
        if forward is None:
            print(f"{expiry:>4}: forward unavailable ({forward_by_year[year]})")
            continue

        quotes = {item.offset_bp: values.get(item.ticker) for item in universe[year]}
        strikes, vols = available_smile_points(float(forward), quotes)
        if len(strikes) < 3:
            print(f"{expiry:>4}: fewer than 3 valid smile quotes")
            continue

        smile = calibrate_sabr(float(forward), float(year), strikes, vols, beta=0.5)
        p = smile.parameters
        print(
            f"{expiry:>4}  F={float(forward):.8f}  "
            f"alpha={p.alpha:.8f}  beta={p.beta:.4f}  "
            f"rho={p.rho:.6f}  nu={p.nu:.6f}  "
            f"rms={smile.rms_error:.3e}"
        )


if __name__ == "__main__":
    main()
