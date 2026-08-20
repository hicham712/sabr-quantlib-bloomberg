"""Bloomberg forward-swap security generation."""

from __future__ import annotations


def forward_maturity_code(years: int) -> str:
    """Return the maturity code used by the EUSA-style forward swap ticker.

    Example supplied from Bloomberg: EUSA0101 BGN Curncy for the forward swap.
    The maturity code is generated with the same year input used by the ENS
    universe; the market-specific prefix is kept configurable.
    """
    if not 1 <= years <= 99:
        raise ValueError("forward maturity years must be between 1 and 99")
    return f"{years:02d}"


def build_forward_security(
    years: int,
    prefix: str = "EUSA01",
    yellow_key: str = "Curncy",
    source: str = "BGN",
) -> str:
    """Build an EUSA-style forward swap security.

    For example, years=1 produces ``EUSA0101 BGN Curncy``.
    """
    return f"{prefix}{forward_maturity_code(years)} {source} {yellow_key}"
