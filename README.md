# SABR QuantLib Bloomberg

Bloomberg swaption smile ingestion and SABR calibration using QuantLib.

## Bloomberg Python API installation

Bloomberg's `blpapi` Python package is installed from Bloomberg's package repository. On the Windows machine running Bloomberg Terminal/Desktop API:

```powershell
python -m pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple blpapi
python -m pip install QuantLib
python -m pip install -e .
```

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

The ENPS ATM volatility and ENS smile values are **normal volatilities quoted in bp**. An ENS value is an add-on to ENPS, so `abs_normal_vol_bp = ENPS + ENS`. The value passed to QuantLib is `abs_normal_vol_bp / 10000`.

## SABR calibration

QuantLib's `SABRInterpolation` performs the calibration with the **Normal** volatility type. Beta is fixed at **0.5**; alpha, rho and nu are calibrated. Missing Bloomberg quotes are ignored, with at least three valid smile points required.

The surface is **node-based in maturity**: only Bloomberg maturities with sufficient quotes are included. There is deliberately no maturity interpolation or extrapolation. SABR is used only to fit/evaluate the strike smile at each observed maturity.

## Build and export

Run on a Windows machine with Bloomberg Terminal/Desktop API running:

```powershell
python -m scripts.build_surface config/bloomberg.json
python -m scripts.build_surface config/bloomberg.json --output-json output/sabr_nodes.json
python -m scripts.export_surface output/sabr_nodes.json
```

The exported CSV contains each Bloomberg-observed strike point, its market normal volatility, the fitted SABR normal volatility, and the node's calibrated parameters. The JSON preserves the same node-level data for downstream pricing and risk tools.

## Bloomberg Desktop API

The data layer uses synchronous BLPAPI `Session` + `ReferenceDataRequest` against the local Bloomberg Desktop API (`localhost:8194`, service `//blp/refdata`).

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```
