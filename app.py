"""Small Dash UI for historical Bloomberg SABR smiles."""
from __future__ import annotations
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, Input, Output, dcc, html

DATA_FILE = Path("output/historical_sabr.json")
app = Dash(__name__)

def load_data():
    if not DATA_FILE.exists(): return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))["nodes"]

def options(records):
    return sorted({r["date"] for r in records})

def maturity_options(records, selected_date):
    return sorted({r["expiry"] for r in records if r["date"] == selected_date}, key=lambda x: float(x[:-1]))

app.layout = html.Div([
    html.H2("Bloomberg Normal SABR Smile"),
    html.Div([html.Label("Date"), dcc.DatePickerSingle(id="date", display_format="YYYY-MM-DD"), html.Label("Maturity"), dcc.Dropdown(id="maturity", clearable=False)]),
    dcc.Graph(id="smile"),
    html.H3("SABR parameter time series"),
    dcc.Graph(id="parameters"),
])

@app.callback(Output("date", "min_date_allowed"), Output("date", "max_date_allowed"), Output("date", "date"), Input("date", "date"))
def init_date(current):
    dates = options(load_data())
    if not dates: return None, None, None
    selected = current if current in dates else dates[-1]
    return dates[0], dates[-1], selected

@app.callback(Output("maturity", "options"), Output("maturity", "value"), Input("date", "date"))
def update_maturity(selected_date):
    records = load_data(); opts = maturity_options(records, selected_date)
    return [{"label": x, "value": x} for x in opts], (opts[0] if opts else None)

@app.callback(Output("smile", "figure"), Output("parameters", "figure"), Input("date", "date"), Input("maturity", "value"))
def update_graphs(selected_date, maturity):
    records = load_data(); fig = go.Figure(); params = go.Figure()
    selected = next((r for r in records if r["date"] == selected_date and r["expiry"] == maturity), None)
    if selected:
        q = selected["quotes"]
        fig.add_trace(go.Scatter(x=[x["offset_bp"] for x in q], y=[x["market_normal_vol"]*10000 for x in q], mode="markers", name="Bloomberg"))
        fig.add_trace(go.Scatter(x=[x["offset_bp"] for x in q], y=[x["sabr_normal_vol"]*10000 for x in q], mode="lines", name="SABR"))
        fig.update_layout(title=f"{selected_date} — {maturity} smile", xaxis_title="Strike offset (bp)", yaxis_title="Normal volatility (bp)")
        history = [r for r in records if r["expiry"] == maturity]
        dates = [r["date"] for r in history]
        for name in ("alpha", "beta", "rho", "nu"):
            params.add_trace(go.Scatter(x=dates, y=[r[name] for r in history], mode="lines+markers", name=name))
        params.update_layout(title=f"{maturity} SABR parameters", xaxis_title="Date", yaxis_title="Parameter")
    return fig, params

if __name__ == "__main__": app.run(debug=True)
