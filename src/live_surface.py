"""End-to-end Bloomberg -> SABR market-data collection entry point."""

from __future__ import annotations

import json
from pathlib import Path

from .bloomberg_desktop import BloombergDesktopClient
from .market_surface_runner import available_maturities, collect_market_data


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect_live_quotes(config_path: str | Path):
    config = load_config(config_path)
    with BloombergDesktopClient(
        host=config.get("host", "localhost"),
        port=int(config.get("port", 8194)),
        timeout_ms=int(config.get("timeout_ms", 10000)),
    ) as client:
        quotes = collect_market_data(
            client,
            config["maturity_years"],
            index=config.get("index", "IIRO"),
            field=config.get("field", "PX_LAST"),
        )
    return available_maturities(quotes)
