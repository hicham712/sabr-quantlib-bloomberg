"""Build a complete SABR surface from the Bloomberg ENS/EUSA universe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from .ens_universe import ENSSecurity, build_ens_universe
from .forward_universe import build_forward_security


class MarketData(Protocol):
    def get(self, securities: Iterable[str], field: str) -> Mapping[str, float | None]: ...


@dataclass(frozen=True)
class MaturityQuotes:
    years: int
    forward_security: str
    forward: float | None
    smile: tuple[ENSSecurity, ...]
    quotes: Mapping[str, float | None]


def collect_market_data(
    market_data: MarketData,
    maturity_years: Iterable[int],
    index: str = "IIRO",
    field: str = "PX_LAST",
) -> list[MaturityQuotes]:
    """Batch-request every ENS quote and matching EUSA forward.

    Missing Bloomberg values are retained as ``None`` so the calibration layer
    can decide whether enough points exist for a maturity.
    """
    years = list(maturity_years)
    universe = build_ens_universe(years, index)

    securities: list[str] = []
    forward_by_year: dict[int, str] = {}
    for year in years:
        securities.extend(s.ticker for s in universe[year])
        forward_by_year[year] = build_forward_security(year)
        securities.append(forward_by_year[year])

    values = market_data.get(securities, field)

    return [
        MaturityQuotes(
            years=year,
            forward_security=forward_by_year[year],
            forward=values.get(forward_by_year[year]),
            smile=tuple(universe[year]),
            quotes={s.ticker: values.get(s.ticker) for s in universe[year]},
        )
        for year in years
    ]


def available_maturities(
    quotes: Iterable[MaturityQuotes],
    minimum_smile_points: int = 3,
) -> list[MaturityQuotes]:
    """Keep maturities with a forward and enough valid smile observations."""
    return [
        q for q in quotes
        if q.forward is not None
        and sum(v is not None for v in q.quotes.values()) >= minimum_smile_points
    ]
