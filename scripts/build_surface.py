"""Fetch Bloomberg smiles, calibrate normal SABR and optionally export nodes."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.bloomberg_desktop import BloombergDesktopClient
from src.ens_universe import build_atm_security, build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import STRIKE_OFFSETS_BP, absolute_volatilities, available_smile_points


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8194)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    field = config.get("field", config.get("quote_field", "PX_LAST"))
    index, yellow_key = config["index"], config.get("yellow_key", "Curncy")
    years = config.get("maturity_years", list(range(1, 31)))
    forward_template = config.get("forward_security_template", "EUSA01{years:02d} BGN Curncy")
    atm_template = config.get("atm_security_template")
    universe = build_ens_universe(years, index, yellow_key)
    nodes: list[dict[str, object]] = []

    with BloombergDesktopClient(host=args.host, port=args.port, timeout_ms=int(config.get("timeout_ms", 10000))) as bloomberg:
        for y in years:
            expiry = f"{y}Y"
            ens = [item.ticker for item in universe[y]]
            forward_security = forward_template.format(years=y)
            atm_security = (atm_template.format(years=y) if atm_template else build_atm_security(y, index, yellow_key))
            values = bloomberg.get(ens + [forward_security, atm_security], field)
            forward, atm = values.get(forward_security), values.get(atm_security)
            raw_addons = {item.offset_bp: values.get(item.ticker) for item in universe[y]}
            if forward is None or atm is None:
                print(f"{expiry:>4}: skipped — forward={forward!r}, ATM={atm!r}")
                continue
            valid = absolute_volatilities(float(atm), raw_addons)
            print(f"{expiry:>4}  F={float(forward):.8f}  ATM={float(atm):.4f} bp  quotes={len(valid)}/8")
            print("       offset(bp)  add-on(bp)  abs-normal-vol(bp)")
            for offset in sorted(valid):
                print(f"       {offset:>10.0f}  {float(raw_addons[offset]):>10.4f}  {10_000.0*valid[offset]:>18.4f}")
            strikes, vols = available_smile_points(float(forward), raw_addons, float(atm))
            if len(strikes) < 3:
                print("       skipped: fewer than 3 valid quotes")
                continue
            smile = calibrate_sabr(float(forward), float(y), strikes, vols, beta=0.5)
            p = smile.parameters
            print(f"       SABR-Normal: alpha={p.alpha:.8f} beta={p.beta:.4f} rho={p.rho:.6f} nu={p.nu:.6f} rms={smile.rms_error:.3e}")
            quotes = []
            for offset in STRIKE_OFFSETS_BP:
                if offset not in valid:
                    continue
                strike = float(forward) + offset / 10_000.0
                quotes.append({"offset_bp": offset, "strike": strike, "market_normal_vol": valid[offset], "sabr_normal_vol": smile.volatility(strike)})
            nodes.append({"expiry": expiry, "expiry_years": float(y), "forward": float(forward), "atm_normal_vol": float(atm) / 10_000.0, "alpha": p.alpha, "beta": p.beta, "rho": p.rho, "nu": p.nu, "rms_error": smile.rms_error, "max_error": smile.max_error, "quotes": quotes})

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps({"nodes": nodes}, indent=2), encoding="utf-8")
        print(f"\nWrote {len(nodes)} Bloomberg SABR nodes to {args.output_json}")


if __name__ == "__main__":
    main()
