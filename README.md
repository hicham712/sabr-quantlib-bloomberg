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

Beta is fixed to 0.5 initially. Missing quotes are allowed when enough points remain for calibration.
