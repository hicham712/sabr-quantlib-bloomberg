"""Bloomberg Desktop API data access.

The client uses the synchronous BLPAPI Session/ReferenceDataRequest pattern.
Security identifiers are deliberately supplied by configuration rather than
hard-coded: Bloomberg security naming varies by currency/index and market.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import blpapi

from .surface import BLOOMBERG_FIELDS


@dataclass(frozen=True)
class BloombergQuoteSet:
    """Bloomberg data for one swaption maturity."""

    security: str
    expiry: str
    forward: float
    quotes_by_offset_bp: Mapping[float, float]


class BloombergClient:
    """Thin synchronous wrapper around Bloomberg Desktop API."""

    def __init__(self, host: str = "localhost", port: int = 8194, service: str = "//blp/refdata") -> None:
        options = blpapi.SessionOptions()
        options.setServerHost(host)
        options.setServerPort(port)
        self._session = blpapi.Session(options)
        self._service_name = service
        self._service = None

    def start(self) -> None:
        if not self._session.start():
            raise RuntimeError("Unable to start Bloomberg BLPAPI session")
        if not self._session.openService(self._service_name):
            self._session.stop()
            raise RuntimeError(f"Unable to open Bloomberg service {self._service_name}")
        self._service = self._session.getService(self._service_name)

    def stop(self) -> None:
        self._session.stop()
        self._service = None

    def __enter__(self) -> "BloombergClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def reference_data(self, securities: Iterable[str], fields: Iterable[str]) -> dict[str, dict[str, object]]:
        """Request reference data and return security -> field -> value."""
        if self._service is None:
            raise RuntimeError("Bloomberg session is not started")

        securities = list(dict.fromkeys(securities))
        fields = list(dict.fromkeys(fields))
        request = self._service.createRequest("ReferenceDataRequest")
        for security in securities:
            request.getElement("securities").appendValue(security)
        for field in fields:
            request.getElement("fields").appendValue(field)

        self._session.sendRequest(request)
        result: dict[str, dict[str, object]] = {}

        while True:
            event = self._session.nextEvent()
            for message in event:
                if not message.hasElement("securityData"):
                    continue
                security_data = message.getElement("securityData")
                for i in range(security_data.numValues()):
                    row = security_data.getValueAsElement(i)
                    security = row.getElementAsString("security")
                    field_data = row.getElement("fieldData")
                    values: dict[str, object] = {}
                    for field in fields:
                        values[field] = (
                            self._element_value(field_data.getElement(field))
                            if field_data.hasElement(field)
                            else None
                        )
                    result[security] = values
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        return result

    @staticmethod
    def _element_value(element: blpapi.Element) -> object:
        if element.isNull():
            return None
        datatype = element.datatype()
        if datatype in (blpapi.DataType.FLOAT64, blpapi.DataType.FLOAT32):
            return element.getValueAsFloat()
        if datatype in (blpapi.DataType.INT64, blpapi.DataType.INT32, blpapi.DataType.BOOL):
            return element.getValueAsInteger()
        return element.getValueAsString()

    def fetch_smile(
        self,
        expiry: str,
        swaption_security: str,
        forward_security: str,
        forward_field: str,
    ) -> BloombergQuoteSet | None:
        """Fetch forward plus ENSH..ENSQ quotes for one maturity.

        The forward is intentionally sourced from a separate security/field:
        the project convention is ATM-forward swap data, not a swaption quote.
        """
        fields = [forward_field, *BLOOMBERG_FIELDS.values()]
        data = self.reference_data([swaption_security, forward_security], fields)
        forward_value = data.get(forward_security, {}).get(forward_field)
        if not isinstance(forward_value, (int, float)) or forward_value <= 0.0:
            return None

        quotes: dict[float, float] = {}
        for offset_bp, field in BLOOMBERG_FIELDS.items():
            value = data.get(swaption_security, {}).get(field)
            if isinstance(value, (int, float)) and value > 0.0:
                quotes[offset_bp] = float(value)
        if len(quotes) < 3:
            return None

        return BloombergQuoteSet(
            security=swaption_security,
            expiry=expiry,
            forward=float(forward_value),
            quotes_by_offset_bp=quotes,
        )
