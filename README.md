# SABR QuantLib Bloomberg

Tools for building an interest-rate volatility surface from Bloomberg swaption quotes and fitting/interpolating the smile with SABR.

## Bloomberg strike-offset convention

The surface uses the forward swap rate as the ATM reference and Bloomberg absolute strike offsets:

| Offset | Bloomberg field |
|---:|:---|
| -150 bp | ENSH |
| -100 bp | ENSI |
| -50 bp | ENSJ |
| -25 bp | K |
| +25 bp | L |
| +50 bp | M |
| +100 bp | N |
| +150 bp | P/Q convention to be verified against the terminal mapping |

The implementation keeps the offset convention explicit so the Bloomberg field mapping can be changed without changing the calibration engine.

## Initial calibration assumptions

- SABR beta = 0.5
- Forward = ATM forward swap rate
- Strike = forward + absolute strike offset
- Missing Bloomberg quotes are allowed; calibration uses the available points
- All available maturities are supported

## Layout

- `src/`: SABR and surface construction code
- `tests/`: calibration and interpolation tests
- `examples/`: Bloomberg data ingestion examples
