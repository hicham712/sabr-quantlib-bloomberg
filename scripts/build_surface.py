"""Fetch Bloomberg smiles, calibrate SABR parameters and build a maturity surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.bloomberg_desktop import BloombergDesktopClient
from src.ens_universe import build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import available_smile_points


def _linear_interpolate(x: float, xs: list[float], ys: list[float]) -> float:
    if len(xs) == 1:
        return ys[0]
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            w = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + w * (ys[i + 1] - ys[i])
    return ys[-1]


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
            quotes = {item.offset_bp: values.get(item.ticker) for item in universe[years_value]}
            if forward is None:
                print(f"{expiry:>4}: forward unavailable ({forward_security})")
                rows.append({"maturity": expiry, "forward": None, "valid_quotes": 0, "status": "forward unavailable"})
                continue
            strikes, vols = available_smile_points(forward, quotes)
            if len(strikes) < 3:
                print(f"{expiry:>4}: skipped — {len(strikes)}/8 valid smile quotes")
                rows.append({"maturity": expiry, "forward": forward, "valid_quotes": len(strikes), "status": "skipped"})
                continue
            smile = calibrate_sabr(forward, float(years_value), strikes, vols, beta=0.5)
            p = smile.parameters
            print(f"{expiry:>4}  F={forward:.8f}  quotes={len(strikes)}/8  alpha={p.alpha:.8f}  beta={p.beta:.4f}  rho={p.rho:.6f}  nu={p.nu:.6f}  rms={smile.rms_error:.3e}")
            rows.append({"maturity": expiry, "forward": forward, "valid_quotes": len(strikes), "alpha": p.alpha, "beta": p.beta, "rho": p.rho, "nu": p.nu, "rms_error": smile.rms_error, "status": "calibrated"})

    calibrated = [r for r in rows if r["status"] == "calibrated"]
    if not calibrated:
        raise RuntimeError("no calibrated SABR maturity nodes")
    calibrated.sort(key=lambda r: float(r["maturity"].rstrip("Y")))
    xs = [float(r["maturity"].rstrip("Y")) for r in calibrated]
    curves = {key: [float(r[key]) for r in calibrated] for key in ("forward", "alpha", "rho", "nu")}

    print("\nInterpolated SABR parameter curve")
    print("Maturity  Forward       Alpha        Rho         Nu")
    for tenor in years:
        t = float(tenor)
        if xs[0] <= t <= xs[-1]:
            print(f"{tenor:>8}  {_linear_interpolate(t, xs, curves['forward']):10.6f}  {_linear_interpolate(t, xs, curves['alpha']):10.8f}  {_linear_interpolate(t, xs, curves['rho']):10.6f}  {_linear_interpolate(t, xs, curves['nu']):10.6f}")


if __name__ == "__main__":
    main()
