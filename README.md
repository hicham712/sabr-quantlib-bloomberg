# SABR QuantLib Bloomberg

Bloomberg swaption smile ingestion and SABR calibration using QuantLib.

## Bloomberg convention

The ATM reference is the forward swap rate. Bloomberg smile tickers are absolute strike offsets from that forward:

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

## SABR

The implementation uses QuantLib's `SABRInterpolation` for calibration and `sabrVolatility` for evaluation. Beta is fixed at 0.5 initially; alpha, rho and nu are calibrated. Missing Bloomberg quotes are ignored, with at least three valid smile points required.

QuantLib-Python can be installed on Windows from PyPI with `python -m pip install QuantLib`.
