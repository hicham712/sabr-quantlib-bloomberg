"""CLI for collecting Bloomberg quotes and calibrating the SABR surface."""

from __future__ import annotations

import argparse

from .live_sabr import calibrate_surface
from .live_surface import collect_live_quotes


def main() -> None:
    parser = argparse.ArgumentParser(description="Bloomberg -> QuantLib SABR surface")
    parser.add_argument("--config", default="config/bloomberg.json")
    parser.add_argument("--beta", type=float, default=0.5)
    args = parser.parse_args()

    quotes = collect_live_quotes(args.config)
    surface = calibrate_surface(quotes, beta=args.beta)

    print("years,forward,alpha,beta,rho,nu,rms_error,max_error")
    for point in surface:
        p = point.sabr
        print(
            f"{point.years},{point.forward:.10g},{p.alpha:.10g},{p.beta:.10g},"
            f"{p.rho:.10g},{p.nu:.10g},{p.rms_error:.10g},{p.max_error:.10g}"
        )


if __name__ == "__main__":
    main()
