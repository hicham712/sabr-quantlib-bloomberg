# Surface workflow

The generated surface is a set of Bloomberg-observed maturity nodes. Each node contains the Bloomberg forward, ENPS ATM normal volatility, the available ENS normal-vol add-ons, calibrated QuantLib normal-SABR parameters, and the market/fitted smile values.

There is no maturity interpolation. A missing maturity is unavailable. Within an observed maturity, QuantLib SABR provides the model smile between the Bloomberg strike-offset observations; strike extrapolation is disabled by default.

Use `scripts/build_surface.py --output-json output/sabr_nodes.json` to persist the calibration. Use `scripts/export_surface.py` to create a flat CSV/JSON representation for downstream pricing and risk applications.
