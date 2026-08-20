# SABR QuantLib Bloomberg

Bloomberg swaption smile ingestion and SABR calibration using QuantLib.

## Bloomberg Python API installation

Bloomberg's `blpapi` Python package is installed from Bloomberg's package repository. On the Windows machine running Bloomberg Terminal/Desktop API:

```powershell
python -m pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple blpapi
python -m pip install QuantLib
python -m pip install -e .
```

`requirements.txt` is configured to use Bloomberg's package index for `blpapi`.

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

For an ATM-forward rate `F`, a quote at offset `x` bp is converted to `K = F + x / 10000`.

For an `N`-year maturity, the corresponding EUSA forward uses the same maturity mapping, e.g. `EUSA0101 BGN Curncy`.

## SABR calibration

QuantLib's `SABRInterpolation` performs the calibration. Beta is fixed at **0.5**; alpha, rho and nu are calibrated. Missing Bloomberg quotes are ignored, with at least three valid smile points required.

## Bloomberg Desktop API

The data layer uses synchronous BLPAPI `Session` + `ReferenceDataRequest` against the local Bloomberg Desktop API (`localhost:8194`, service `//blp/refdata`).

Run on a Windows machine with Bloomberg Terminal/Desktop API running:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m scripts.build_surface config/bloomberg.json
```
