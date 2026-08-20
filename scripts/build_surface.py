"""Fetch Bloomberg ENS smiles and calibrate one QuantLib SABR smile per maturity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.bloomberg import BloombergClient
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
    forward_field = config.get("forward_field", "PX_LAST")
    quote_field = config.get("quote_field", "PX_LAST")
    index = config["index"]
    yellow_key = config.get("yellow_key", "Curncy")
    years = config.get("maturity_years", list(range(1, 31)))
    universe = build_ens_universe(years, index, yellow_key)

    with BloombergClient(host=args.host, port=args.port) as bloomberg:
        for years_value in years:
            expiry = f"{years_value}Y"
            ens_securities = {
                item.offset_bp: item.ticker for item in universe[years_value]
            }
            forward_security = config["forward_security_template"].format(years=years_value)
            quote_set = bloomberg.fetch_smile(
                expiry=expiry,
                ens_securities=ens_securities,
                forward_security=forward_security,
                forward_field=forward_field,
                quote_field=quote_field,
            )
            if quote_set is None:
                print(f"{expiry:>4}: unavailable / fewer than 3 valid quotes")
                continue

            strikes, vols = available_smile_points(
                quote_set.forward, quote_set.quotes_by_offset_bp
            )
            smile = calibrate_sabr(
                quote_set.forward,
                float(years_value),
                strikes,
                vols,
                beta=0.5,
            )
            p = smile.parameters
            print(
                f"{expiry:>4}  F={quote_set.forward:.8f}  "
                f"alpha={p.alpha:.8f}  beta={p.beta:.4f}  "
                f"rho={p.rho:.6f}  nu={p.nu:.6f}  "
                f"rms={smile.rms_error:.3e}"
            )


if __name__ == "__main__":
    main()
