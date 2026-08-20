"""Fetch configured Bloomberg maturities and calibrate a SABR smile for each."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.bloomberg import BloombergClient
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

    with BloombergClient(host=args.host, port=args.port) as bloomberg:
        for item in config["maturities"]:
            quote_set = bloomberg.fetch_smile(
                expiry=item["expiry"],
                swaption_security=item["swaption_security"],
                forward_security=item["forward_security"],
                forward_field=forward_field,
            )
            if quote_set is None:
                print(f"{item['expiry']}: unavailable / fewer than 3 valid quotes")
                continue

            strikes, vols = available_smile_points(
                quote_set.forward, quote_set.quotes_by_offset_bp
            )
            smile = calibrate_sabr(
                quote_set.forward,
                _expiry_in_years(item["expiry"]),
                strikes,
                vols,
                beta=0.5,
            )
            p = smile.parameters
            print(
                f"{item['expiry']:>4}  F={quote_set.forward:.8f}  "
                f"alpha={p.alpha:.8f}  beta={p.beta:.4f}  "
                f"rho={p.rho:.6f}  nu={p.nu:.6f}  "
                f"rms={smile.rms_error:.3e}"
            )


def _expiry_in_years(expiry: str) -> float:
    """Convert simple Bloomberg-style tenor labels into year fractions."""
    unit = expiry[-1].upper()
    value = float(expiry[:-1])
    if unit == "M":
        return value / 12.0
    if unit == "Y":
        return value
    raise ValueError(f"Unsupported expiry label: {expiry!r}")


if __name__ == "__main__":
    main()
