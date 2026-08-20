"""Historical Bloomberg Desktop API support."""
from __future__ import annotations
from datetime import date
from typing import Iterable
import blpapi

class BloombergHistoryClient:
    def __init__(self, host: str = "localhost", port: int = 8194, timeout_ms: int = 10000):
        self.host, self.port, self.timeout_ms = host, port, timeout_ms
        self._session = None

    def __enter__(self):
        options = blpapi.SessionOptions(); options.setServerHost(self.host); options.setServerPort(self.port)
        self._session = blpapi.Session(options)
        if not self._session.start(): raise RuntimeError("Could not start Bloomberg Desktop API session")
        if not self._session.openService("//blp/refdata"):
            self.close(); raise RuntimeError("Could not open Bloomberg refdata service")
        return self

    def __exit__(self, *args): self.close()
    def close(self):
        if self._session is not None: self._session.stop(); self._session = None

    def historical(self, securities: Iterable[str], field: str, start: date, end: date) -> dict[str, dict[str, float]]:
        service = self._session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")
        for security in dict.fromkeys(securities): request.getElement("securities").appendValue(security)
        request.getElement("fields").appendValue(field)
        request.set("startDate", start.strftime("%Y%m%d")); request.set("endDate", end.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")
        self._session.sendRequest(request)
        result: dict[str, dict[str, float]] = {}
        while True:
            event = self._session.nextEvent(self.timeout_ms)
            if event.eventType() == blpapi.Event.TIMEOUT: raise RuntimeError("Bloomberg historical request timed out")
            for message in event:
                if not message.hasElement("securityData"): continue
                sd = message.getElement("securityData"); security = sd.getElementAsString("security")
                rows = sd.getElement("fieldData")
                for i in range(rows.numValues()):
                    row = rows.getValueAsElement(i)
                    if row.hasElement("date") and row.hasElement(field):
                        value = row.getElement(field).getValue()
                        if value is not None:
                            result.setdefault(security, {})[row.getElementAsDatetime("date").date().isoformat()] = float(value)
            if event.eventType() == blpapi.Event.RESPONSE: return result
