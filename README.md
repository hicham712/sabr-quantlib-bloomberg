# SABR QuantLib Bloomberg

Bloomberg swaption smile ingestion and SABR calibration using QuantLib.

## Bloomberg convention

The ATM reference is the forward swap rate. Bloomberg smile tickers represent absolute strike offsets from that forward:

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

## SABR calibration

The implementation delegates SABR interpolation/calibration and implied-volatility evaluation to QuantLib's `SABRInterpolation` and `sabrVolatility`. Beta is fixed at 0.5 initially; alpha, rho and nu are calibrated. Missing Bloomberg quotes are ignored, with at least three valid smile points required.

## Windows

QuantLib-Python provides precompiled Windows wheels on PyPI. Install with:

```powershell
python -m pip install QuantLib
```

The Bloomberg Desktop API layer is intentionally separate: it will retrieve the forward and the available `ENS*` smile tickers for every available maturity and pass them into this calibration layer.
