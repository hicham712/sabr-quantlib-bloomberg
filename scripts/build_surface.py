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
    field = config.get("field", config.get("quote_field", "PX_LAST"))
    index = config["index"]
    yellow_key = config.get("yellow_key", "Curncy")
    years = config.get("maturity_years", list(range(1, 31)))
    universe = build_ens_universe(years, index, yellow_key)
    with BloombergDesktopClient(host=args.host, port=args.port, timeout_ms=int(config.get("timeout_ms", 10000))) as bloomberg:
        for years_value in years:
            expiry = f"{years_value}Y"
            ens_securities = [item.ticker for item in universe[years_value]]
            forward_security = config["forward_security_template"].format(years=years_value)
            values = bloomberg.get(ens_securities + [forward_security], field)
            forward = values.get(forward_security)
            quotes_by_offset = {item.offset_bp: values.get(item.ticker) for item in universe[years_value]}
            if forward is None:
                print(f"{expiry:>4}: forward unavailable ({forward_security})")
                continue
            strikes, vols = available_smile_points(forward, quotes_by_offset)
            if len(strikes) < 3:
                print(f"{expiry:>4}: unavailable / fewer than 3 valid quotes")
                continue
            smile = calibrate_sabr(forward, float(years_value), strikes, vols, beta=0.5)
            p = smile.parameters
            print(f"{expiry:>4}  F={forward:.8f}  alpha={p.alpha:.8f}  beta={p.beta:.4f}  rho={p.rho:.6f}  nu={p.nu:.6f}  rms={smile.rms_error:.3e}")


if __name__ == "__main__":
    main()
