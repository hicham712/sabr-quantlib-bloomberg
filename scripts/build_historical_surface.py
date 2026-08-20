"""Calibrate Bloomberg normal-SABR smiles on a configurable historical frequency."""
from __future__ import annotations
import argparse, json
from datetime import date, timedelta
from pathlib import Path
from src.bloomberg_history import BloombergHistoryClient
from src.ens_universe import build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import STRIKE_OFFSETS_BP, absolute_volatilities, available_smile_points


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--start", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--end", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--years", type=float, default=None, help="Historical lookback in years")
    parser.add_argument("--frequency", choices=("DAILY", "WEEKLY", "MONTHLY"), default=None)
    parser.add_argument("--output", type=Path, default=Path("output/historical_sabr.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    end = args.end or date.today()
    lookback_years = args.years if args.years is not None else config.get("historical_years", 1.0 / 12.0)
    start = args.start or (end - timedelta(days=round(365.25 * lookback_years)))
    frequency = args.frequency or config.get("historical_frequency", "DAILY")
    years = config.get("maturity_years", list(range(1, 31)))
    index, yellow = config["index"], config.get("yellow_key", "Curncy")
    field = config.get("field", "PX_LAST")
    universe = build_ens_universe(years, index, yellow)
    securities = []
    security_map = {}
    for y in years:
        forward = config.get("forward_security_template", "EUSA01{years:02d} BGN Curncy").format(years=y)
        atm = config.get("atm_security_template", "ENPS0F{years:02d} {index} {yellow}").format(years=y, index=index, yellow=yellow)
        security_map[(y, "forward")] = forward; security_map[(y, "atm")] = atm
        securities += [forward, atm] + [item.ticker for item in universe[y]]

    with BloombergHistoryClient(host=config.get("host", "localhost"), port=int(config.get("port", 8194)), timeout_ms=int(config.get("timeout_ms", 10000))) as bloomberg:
        history = bloomberg.historical(securities, field, start, end, periodicity=frequency)

    records = []
    for d in sorted({d for values in history.values() for d in values}):
        for y in years:
            forward = history.get(security_map[(y, "forward")], {}).get(d)
            atm = history.get(security_map[(y, "atm")], {}).get(d)
            if forward is None or atm is None:
                continue
            raw = {item.offset_bp: history.get(item.ticker, {}).get(d) for item in universe[y]}
            valid = absolute_volatilities(float(atm), raw)
            if len(valid) < 3:
                continue
            strikes, vols = available_smile_points(float(forward), raw, float(atm))
            if len(strikes) < 3:
                continue
            try:
                smile = calibrate_sabr(float(forward), float(y), strikes, vols, beta=0.5)
            except Exception:
                continue
            p = smile.parameters
            records.append({
                "date": d, "expiry": f"{y}Y", "expiry_years": float(y), "forward": float(forward),
                "atm_normal_vol": float(atm) / 10000.0, "alpha": p.alpha, "beta": p.beta,
                "rho": p.rho, "nu": p.nu, "rms_error": smile.rms_error,
                "quotes": [{"offset_bp": offset, "strike": float(forward) + offset / 10000.0,
                            "market_normal_vol": valid[offset],
                            "sabr_normal_vol": smile.volatility(float(forward) + offset / 10000.0)}
                           for offset in STRIKE_OFFSETS_BP if offset in valid],
            })
        print(f"{d}: {sum(r['date'] == d for r in records)} calibrated nodes")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"start": start.isoformat(), "end": end.isoformat(), "frequency": frequency, "nodes": records}, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} historical SABR nodes to {args.output}")


if __name__ == "__main__":
    main()
