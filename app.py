"""Small Dash UI for historical Bloomberg SABR smiles."""
from __future__ import annotations
import json
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from src.sabr import calibrate_sabr

DATA_FILE = Path("output/historical_sabr_5y_weekly.json")
app = Dash(__name__)


def load_payload():
    if not DATA_FILE.exists():
        return {"nodes": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def load_data():
    return load_payload().get("nodes", [])


def dates(records):
    return sorted({r["date"] for r in records})


def maturity_options(records, selected_date):
    return sorted({r["expiry"] for r in records if r["date"] == selected_date}, key=lambda x: float(x[:-1]))


app.layout = html.Div([
    html.H2("Bloomberg Normal SABR Smile"),
    html.Div(id="dataset-info"),
    html.Div([
        html.Label("Date"),
        dcc.DatePickerSingle(id="date", display_format="YYYY-MM-DD"),
        html.Label("Maturity"),
        dcc.Dropdown(id="maturity", clearable=False),
    ], style={"display": "grid", "gridTemplateColumns": "180px 220px", "gap": "8px 16px", "maxWidth": "450px"}),
    dcc.Graph(id="smile"),
    html.Div([
        dcc.Graph(id="alpha"), dcc.Graph(id="beta"), dcc.Graph(id="rho"),
        dcc.Graph(id="nu"), dcc.Graph(id="atm"), dcc.Graph(id="atm-move"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))"}),
])


@app.callback(
    Output("date", "min_date_allowed"), Output("date", "max_date_allowed"),
    Output("date", "date"), Output("dataset-info", "children"), Input("date", "date")
)
def init_date(current):
    available = dates(load_data())
    if not available:
        return None, None, None, "No historical dataset found."
    selected = current if current in available else available[-1]
    payload = load_payload()
    frequency = payload.get("frequency", "weekly")
    info = f"Dataset: {available[0]} → {available[-1]} | {frequency} | {len(available)} observations"
    return available[0], available[-1], selected, info


@app.callback(Output("maturity", "options"), Output("maturity", "value"), Input("date", "date"))
def update_maturity(selected_date):
    records = load_data()
    opts = maturity_options(records, selected_date)
    return [{"label": x, "value": x} for x in opts], (opts[0] if opts else None)


@app.callback(
    Output("smile", "figure"), Output("alpha", "figure"), Output("beta", "figure"),
    Output("rho", "figure"), Output("nu", "figure"), Output("atm", "figure"), Output("atm-move", "figure"),
    Input("date", "date"), Input("maturity", "value")
)
def update_graphs(selected_date, maturity):
    records = load_data()
    empty = go.Figure()
    if not selected_date or not maturity:
        return (empty,) * 7

    selected = next((r for r in records if r["date"] == selected_date and r["expiry"] == maturity), None)
    smile = go.Figure()
    if selected:
        q = selected["quotes"]
        forward = float(selected["forward"])
        expiry = float(selected["expiry_years"])
        # Reconstruct the QuantLib SABR interpolation from the stored market
        # quotes and explicitly include Bloomberg's ATM normal-vol point at 0 bp.
        market_offsets = [float(x["offset_bp"]) for x in q]
        market_vols = [float(x["market_normal_vol"]) for x in q]
        if 0.0 not in market_offsets:
            insert_at = next((i for i, x in enumerate(market_offsets) if x > 0.0), len(market_offsets))
            market_offsets.insert(insert_at, 0.0)
            market_vols.insert(insert_at, float(selected["atm_normal_vol"]))
        strikes = [forward + offset / 10000.0 for offset in market_offsets]
        fitted = calibrate_sabr(forward, expiry, strikes, market_vols, beta=float(selected["beta"]))

        # Evaluate QuantLib directly at 0 bp and across the whole displayed range.
        plot_offsets = list(range(-150, 151))
        plot_vols = [fitted.volatility(forward + offset / 10000.0, False) * 10000.0 for offset in plot_offsets]
        fitted_atm = fitted.volatility(forward, False) * 10000.0

        smile.add_trace(go.Scatter(
            x=[x["offset_bp"] for x in q], y=[x["market_normal_vol"] * 10000 for x in q],
            mode="markers", name="Bloomberg smile"
        ))
        smile.add_trace(go.Scatter(
            x=[0], y=[selected["atm_normal_vol"] * 10000],
            mode="markers", marker={"size": 9}, name="Bloomberg ATM"
        ))
        smile.add_trace(go.Scatter(
            x=plot_offsets, y=plot_vols, mode="lines", name="QuantLib SABR"
        ))
        smile.add_trace(go.Scatter(
            x=[0], y=[fitted_atm], mode="markers", marker={"size": 8}, name="QuantLib SABR ATM"
        ))
        smile.update_layout(
            title=f"{selected_date} — {maturity} smile",
            xaxis_title="Strike offset (bp)", yaxis_title="Normal volatility (bp)",
        )

    history = sorted((r for r in records if r["expiry"] == maturity), key=lambda r: r["date"])
    x = [r["date"] for r in history]

    def parameter_figure(name: str, title: str):
        fig = go.Figure(go.Scatter(x=x, y=[r[name] for r in history], mode="lines+markers", name=name))
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title=name)
        return fig

    alpha = parameter_figure("alpha", f"{maturity} — α")
    beta = parameter_figure("beta", f"{maturity} — β")
    rho = parameter_figure("rho", f"{maturity} — ρ")
    nu = parameter_figure("nu", f"{maturity} — ν")
    atm_values = [r["atm_normal_vol"] * 10000 for r in history]
    atm = go.Figure(go.Scatter(x=x, y=atm_values, mode="lines+markers", name="ATM"))
    atm.update_layout(title=f"{maturity} — ATM normal volatility", xaxis_title="Date", yaxis_title="Normal volatility (bp)")
    moves = [None] + [atm_values[i] - atm_values[i - 1] for i in range(1, len(atm_values))]
    atm_move = go.Figure(go.Bar(x=x, y=moves, name="ATM move"))
    atm_move.update_layout(title=f"{maturity} — ATM normal-vol move", xaxis_title="Date", yaxis_title="Weekly move (bp)")
    return smile, alpha, beta, rho, nu, atm, atm_move


if __name__ == "__main__":
    app.run(debug=True)
