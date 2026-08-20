"""Bloomberg Desktop API adapter.

Requires Bloomberg Terminal/Desktop API to be running on the Windows host and
requires the ``blpapi`` Python package installed in that environment.
"""

from __future__ import annotations

from typing import Iterable

try:
    import blpapi
except ImportError as exc:  # pragma: no cover - exercised only without Bloomberg
    blpapi = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class BloombergError(RuntimeError):
    pass


class BloombergDesktopClient:
    """Synchronous reference-data client backed by Bloomberg Desktop API."""

    def __init__(self, host: str = "localhost", port: int = 8194, timeout_ms: int = 10000):
        if blpapi is None:
            raise BloombergError(
                "blpapi is not installed. Install Bloomberg Desktop API's Python package "
                "on the Windows machine running the Bloomberg Terminal."
            ) from _IMPORT_ERROR
        self.host = host
        self.port = port
        self.timeout_ms = timeout_ms
        self._session = None

    def __enter__(self) -> "BloombergDesktopClient":
        options = blpapi.SessionOptions()
        options.setServerHost(self.host)
        options.setServerPort(self.port)
        self._session = blpapi.Session(options)
        if not self._session.start():
            raise BloombergError("Could not start Bloomberg Desktop API session")
        if not self._session.openService("//blp/refdata"):
            self.close()
            raise BloombergError("Could not open Bloomberg //blp/refdata service")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._session is not None:
            self._session.stop()
            self._session = None

    def get(self, securities: Iterable[str], field: str = "PX_LAST") -> dict[str, float | None]:
        if self._session is None:
            raise BloombergError("Client must be used as a context manager")

        securities = list(dict.fromkeys(securities))
        if not securities:
            return {}

        service = self._session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")
        security_list = request.getElement("securities")
        for security in securities:
            security_list.appendValue(security)
        field_list = request.getElement("fields")
        field_list.appendValue(field)

        self._session.sendRequest(request)
        result: dict[str, float | None] = {security: None for security in securities}

        while True:
            event = self._session.nextEvent(self.timeout_ms)
            if event.eventType() == blpapi.Event.TIMEOUT:
                raise BloombergError("Timed out waiting for Bloomberg reference data")

            for message in event:
                if message.hasElement("responseError"):
                    raise BloombergError(str(message.getElement("responseError")))
                if not message.hasElement("securityData"):
                    continue

                security_data = message.getElement("securityData")
                for i in range(security_data.numValues()):
                    row = security_data.getValueAsElement(i)
                    security = row.getElementAsString("security")
                    field_data = row.getElement("fieldData")
                    if field_data.hasElement(field):
                        value = field_data.getElement(field).getValue()
                        result[security] = float(value) if value is not None else None

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return result
