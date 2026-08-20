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
    forward_template = config.get("forward_security_template", "EUSA01{years:02d} BGN Curncy")
    universe = build_ens_universe(years, index, yellow_key)

    rows: list[dict[str, object]] = []
    with BloombergDesktopClient(host=args.host, port=args.port, timeout_ms=int(config.get("timeout_ms", 10000))) as bloomberg:
        for years_value in years:
            expiry = f"{years_value}Y"
            ens_securities = [item.ticker for item in universe[years_value]]
            forward_security = forward_template.format(years=years_value)
            values = bloomberg.get(ens_securities + [forward_security], field)
            forward = values.get(forward_security)
            quotes_by_offset = {item.offset_bp: values.get(item.ticker) for item in universe[years_value]}
            valid_quotes = sum(1 for value in quotes_by_offset.values() if value is not None and value > 0.0)

            if forward is None:
                print(f"{expiry:>4}: forward unavailable ({forward_security})")
                rows.append({"maturity": expiry, "forward": None, "valid_quotes": valid_quotes, "status": "forward unavailable"})
                continue

            strikes, vols = available_smile_points(forward, quotes_by_offset)
            if len(strikes) < 3:
                print(f"{expiry:>4}: skipped — {len(strikes)}/8 valid smile quotes")
                rows.append({"maturity": expiry, "forward": forward, "valid_quotes": len(strikes), "status": "skipped"})
                continue

            smile = calibrate_sabr(forward, float(years_value), strikes, vols, beta=0.5)
            p = smile.parameters
            print(
                f"{expiry:>4}  F={forward:.8f}  quotes={len(strikes)}/8  "
                f"alpha={p.alpha:.8f}  beta={p.beta:.4f}  rho={p.rho:.6f}  "
                f"nu={p.nu:.6f}  rms={smile.rms_error:.3e}"
            )
            rows.append({
                "maturity": expiry,
                "forward": forward,
                "valid_quotes": len(strikes),
                "alpha": p.alpha,
                "beta": p.beta,
                "rho": p.rho,
                "nu": p.nu,
                "rms_error": smile.rms_error,
                "status": "calibrated",
            })

    if rows:
        print("\nSummary")
        print("Maturity  Forward          Quotes  Status")
        print("--------  ---------------  ------  ---------")
        for row in rows:
            forward = "-" if row["forward"] is None else f"{row['forward']:.8f}"
            print(f"{row['maturity']:>8}  {forward:>15}  {row['valid_quotes']:>6}/8  {row['status']}")


if __name__ == "__main__":
    main()
