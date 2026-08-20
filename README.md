# SABR QuantLib Bloomberg

Bloomberg swaption smile ingestion and SABR calibration using QuantLib.

## Bloomberg convention

The ATM reference is the **forward swap rate**, sourced separately from the swap/swap-rate security. Bloomberg smile tickers represent absolute strike offsets from that forward:

| Offset | Bloomberg ticker |
|---:|:---|
| -150 bp | ENSH |
| -100 bp | ENSI |
| -50 bp | ENSK |
| -25 bp | ENSL |
| +25 bp | ENSM |
| +50 bp | ENSN |
| +100 bp | ENSP |
| +150 bp | ENSQ |

These are the actual `ENS*` Bloomberg tickers; `K`, `L`, `M`, `N`, `P`, `Q` are suffixes, not standalone fields.

For an ATM-forward rate `F`, a quote at offset `x` bp is converted to `K = F + x / 10000`.

## SABR calibration

QuantLib's `SABRInterpolation` performs the multidimensional calibration. Beta is fixed at **0.5**; alpha, rho and nu are calibrated. The interpolation is configured for shifted-lognormal volatility with zero shift, matching the lognormal SABR convention. Missing Bloomberg quotes are ignored, with at least three valid smile points required.

The implementation uses QuantLib's own calibration/interpolation machinery rather than a parallel scipy/Hagan implementation.

## Bloomberg Desktop API

The data layer uses the synchronous BLPAPI `Session` + `ReferenceDataRequest` pattern against the local Bloomberg Desktop API (`localhost:8194`, service `//blp/refdata`). Bloomberg documents `Session` as the consumer API for requests and `Service.createRequest()` as the way to create schema-valid requests.

The security universe is intentionally configuration-driven. Bloomberg security naming differs by currency/index and should not be guessed in code. Put every candidate maturity you want to test in `config/example.json` (copy it to a private config and replace the securities). Maturities for which Bloomberg returns no forward or fewer than three valid `ENS*` quotes are skipped.

The forward is deliberately requested from the **swap security**, not the swaption security, in accordance with the project convention.

Run on a Windows machine with Bloomberg Terminal/Desktop API running:

```powershell
python -m pip install -r requirements-quantlib.txt
python scripts/build_surface.py config/my_surface.json
```

The runner prints one calibrated SABR parameter set per available maturity.

## References

- QuantLib `SABRInterpolation`: https://rkapl123.github.io/QLAnnotatedSource/db/d61/class_quant_lib_1_1_s_a_b_r_interpolation.html
- Bloomberg BLPAPI `Session`: https://bloomberg.github.io/blpapi-docs/python/3.21/_autosummary/blpapi.Session.html
- Bloomberg BLPAPI `Request`: https://bloomberg.github.io/blpapi-docs/python/3.26.5/_autosummary/blpapi.Request.html
