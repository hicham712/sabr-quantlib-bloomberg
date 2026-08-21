"""Calibrate Bloomberg normal-SABR smiles on a configurable historical frequency."""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from src.bloomberg_history import BloombergHistoryClient
from src.ens_universe import build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import (
    STRIKE_OFFSETS_BP,
    absolute_volatilities,
    available_smile_points,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--years", type=float)
    parser.add_argument("--frequency", choices=("DAILY", "WEEKLY", "MONTHLY"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))

    end = args.end or date.today()
    history_years = args.years
    if history_years is None:
        history_years = config.get("historical_years", 1 / 12)

    if args.start is not None:
        start = args.start
    else:
        start = end - timedelta(days=round(365.25 * history_years))

    frequency = args.frequency or config.get("historical_frequency", "DAILY")
    expiries = config.get("expiry_years", config.get("maturity_years"))
    swap_tenors = config.get("swap_tenor_years", [10])
    index = config["index"]
    yellow_key = config.get("yellow_key", "Curncy")
    field = config.get("field", "PX_LAST")
    forward_template = config.get(
        "forward_security_template", "EUSA01{years:02d} BGN Curncy"
    )

    if not expiries:
        raise ValueError("No option expiries configured")
    if not swap_tenors:
        raise ValueError("No swap tenors configured")

    # Bloomberg universe is two-dimensional:
    # option expiry x underlying swap tenor.
    universe = build_ens_universe(expiries, swap_tenors, index, yellow_key)
    securities: list[str] = []
    security_map: dict[tuple[int, int, str], str] = {}

    for expiry in expiries:
        for tenor in swap_tenors:
            forward = forward_template.format(years=tenor)
            atm = f"ENPS0F{expiry:02d}{tenor:02d} {index} {yellow_key}"
            security_map[(expiry, tenor, "forward")] = forward
            security_map[(expiry, tenor, "atm")] = atm
            securities.extend([forward, atm])
            securities.extend(q.ticker for q in universe[(expiry, tenor)])

    with BloombergHistoryClient(
        host=config.get("host", "localhost"),
        port=int(config.get("port", 8194)),
        timeout_ms=int(config.get("timeout_ms", 10000)),
    ) as bloomberg:
        history = bloomberg.historical(
            securities, field, start, end, periodicity=frequency
        )

    records = []
    dates = sorted({d for values in history.values() for d in values})

    for calibration_date in dates:
        for expiry in expiries:
            for tenor in swap_tenors:
                forward = history.get(
                    security_map[(expiry, tenor, "forward")], {}
                ).get(calibration_date)
                atm = history.get(
                    security_map[(expiry, tenor, "atm")], {}
                ).get(calibration_date)

                if forward is None or atm is None:
                    continue

                raw_quotes = {
                    quote.offset_bp: history.get(quote.ticker, {}).get(calibration_date)
                    for quote in universe[(expiry, tenor)]
                }
                valid = absolute_volatilities(float(atm), raw_quotes)
                if len(valid) < 3:
                    continue

                strikes, vols = available_smile_points(
                    float(forward), raw_quotes, float(atm)
                )
                if len(strikes) < 3:
                    continue

                try:
                    smile = calibrate_sabr(
                        float(forward),
                        float(expiry),
                        strikes,
                        vols,
                        beta=0.5,
                    )
                except Exception:
                    continue

                parameters = smile.parameters
                records.append(
                    {
                        "date": calibration_date,
                        "expiry": f"{expiry}Y",
                        "expiry_years": float(expiry),
                        "swap_tenor": f"{tenor}Y",
                        "swap_tenor_years": float(tenor),
                        "forward": float(forward),
                        "atm_normal_vol": float(atm) / 10000,
                        "alpha": parameters.alpha,
                        "beta": parameters.beta,
                        "rho": parameters.rho,
                        "nu": parameters.nu,
                        "rms_error": smile.rms_error,
                        "quotes": [
                            {
                                "offset_bp": offset,
                                "strike": float(forward) + offset / 10000,
                                "market_normal_vol": valid[offset],
                                "sabr_normal_vol": smile.volatility(
                                    float(forward) + offset / 10000
                                ),
                            }
                            for offset in STRIKE_OFFSETS_BP
                            if offset in valid
                        ],
                    }
                )

    output = args.output or Path("output/historical_sabr_5y_weekly.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "index": index,
                "frequency": frequency,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "expiries": expiries,
                "swap_tenors": swap_tenors,
                "nodes": records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} historical SABR nodes to {output}")


if __name__ == "__main__":
    main()
