"""Small Dash UI for historical Bloomberg SABR smiles."""
from __future__ import annotations
import json
from datetime import date
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


def pct_param(name, value):
    return float(value) * 100.0


app.layout = html.Div([
    html.H2("Bloomberg Normal SABR Smile"),
    html.Div(id="dataset-info"),
    html.Div([
        html.Label("Date"), dcc.Dropdown(id="date", clearable=False),
        html.Label("Maturity"), dcc.Dropdown(id="maturity", clearable=False),
    ], style={"display": "grid", "gridTemplateColumns": "180px 220px", "gap": "8px 16px", "maxWidth": "450px"}),
    html.Div(id="parameter-table"),
    dcc.Graph(id="smile"),
    html.Div([
        dcc.Graph(id="alpha"), dcc.Graph(id="beta"), dcc.Graph(id="rho"),
        dcc.Graph(id="nu"), dcc.Graph(id="atm"), dcc.Graph(id="atm-move"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))"}),
])


@app.callback(Output("date", "options"), Output("date", "value"), Output("dataset-info", "children"), Input("date", "value"))
def init_date(current):
    available = dates(load_data())
    if not available:
        return [], None, "No historical dataset found."
    selected = current if current in available else available[-1]
    payload = load_payload()
    frequency = payload.get("frequency", "weekly")
    info = f"Dataset: {available[0]} → {available[-1]} | {frequency} | {len(available)} calibration dates"
    return [{"label": d, "value": d} for d in available], selected, info


@app.callback(Output("maturity", "options"), Output("maturity", "value"), Input("date", "value"))
def update_maturity(selected_date):
    opts = maturity_options(load_data(), selected_date)
    return [{"label": x, "value": x} for x in opts], (opts[0] if opts else None)


@app.callback(Output("parameter-table", "children"), Input("date", "value"), Input("maturity", "value"))
def update_parameter_table(selected_date, maturity):
    records = sorted((r for r in load_data() if r["expiry"] == maturity), key=lambda r: r["date"])
    if not selected_date or not maturity or not records:
        return html.Div()
    available = [r["date"] for r in records]
    target = date.fromisoformat(selected_date)
    def nearest_at_or_before(days):
        cutoff = target.fromordinal(target.toordinal() - days)
        eligible = [d for d in available if date.fromisoformat(d) <= cutoff]
        return eligible[-1] if eligible else None
    periods = [("Selected", selected_date), ("Last week", nearest_at_or_before(7)), ("Last month", nearest_at_or_before(30))]
    rows = []
    for label, d in periods:
        r = next((x for x in records if x["date"] == d), None)
        if r:
            rows.append(html.Tr([
                html.Td(label), html.Td(d),
                html.Td(f"{pct_param('alpha', r['alpha']):.3f}%"),
                html.Td(f"{pct_param('beta', r['beta']):.3f}%"),
                html.Td(f"{pct_param('rho', r['rho']):.3f}%"),
                html.Td(f"{pct_param('nu', r['nu']):.3f}%"),
                html.Td(f"{float(r['atm_normal_vol']) * 10000:.2f} bp"),
            ]))
    return html.Table([
        html.Thead(html.Tr([html.Th(x) for x in ["Period", "Calibration date", "α", "β", "ρ", "ν", "ATM"]])),
        html.Tbody(rows)
    ], style={"width": "100%", "borderCollapse": "collapse", "margin": "18px 0", "textAlign": "right"})


@app.callback(Output("smile", "figure"), Output("alpha", "figure"), Output("beta", "figure"), Output("rho", "figure"), Output("nu", "figure"), Output("atm", "figure"), Output("atm-move", "figure"), Input("date", "value"), Input("maturity", "value"))
def update_graphs(selected_date, maturity):
    records = load_data()
    empty = go.Figure()
    if not selected_date or not maturity:
        return (empty,) * 7
    selected = next((r for r in records if r["date"] == selected_date and r["expiry"] == maturity), None)
    smile = go.Figure()
    if selected:
        q = selected["quotes"]
        forward, expiry = float(selected["forward"]), float(selected["expiry_years"])
        offsets = [float(x["offset_bp"]) for x in q]
        vols = [float(x["market_normal_vol"]) for x in q]
        if 0.0 not in offsets:
            i = next((i for i, x in enumerate(offsets) if x > 0.0), len(offsets))
            offsets.insert(i, 0.0)
            vols.insert(i, float(selected["atm_normal_vol"]))
        strikes = [forward + x / 10000.0 for x in offsets]
        fitted = calibrate_sabr(forward, expiry, strikes, vols, beta=float(selected["beta"]))
        plot_offsets = list(range(-150, 151))
        plot_vols = [fitted.volatility(forward + x / 10000.0, False) * 10000.0 for x in plot_offsets]
        fitted_atm = fitted.volatility(forward, False) * 10000.0
        smile.add_trace(go.Scatter(x=[x["offset_bp"] for x in q], y=[x["market_normal_vol"] * 10000 for x in q], mode="markers", name="Bloomberg smile"))
        smile.add_trace(go.Scatter(x=[0], y=[selected["atm_normal_vol"] * 10000], mode="markers", marker={"size": 9}, name="Bloomberg ATM"))
        smile.add_trace(go.Scatter(x=plot_offsets, y=plot_vols, mode="lines", name="QuantLib SABR"))
        smile.add_trace(go.Scatter(x=[0], y=[fitted_atm], mode="markers", marker={"size": 8}, name="QuantLib SABR ATM"))
        smile.update_layout(title=f"{selected_date} — {maturity} smile", xaxis_title="Strike offset (bp)", yaxis_title="Normal volatility (bp)")

    history = sorted((r for r in records if r["expiry"] == maturity), key=lambda r: r["date"])
    x = [r["date"] for r in history]
    def parameter_figure(name, title):
        fig = go.Figure(go.Scatter(x=x, y=[pct_param(name, r[name]) for r in history], mode="lines+markers", name=name))
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Parameter (%)")
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
