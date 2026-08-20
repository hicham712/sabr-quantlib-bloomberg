"""Historical Bloomberg normal-SABR dashboard."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from src.sabr import calibrate_sabr

DATA_FILE = Path("output/historical_sabr_5y_weekly.json")
app = Dash(__name__, title="SABR Surface")

PLOT = dict(paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Inter, Arial", color="#344054"), margin=dict(l=48,r=24,t=42,b=42), hovermode="x unified")
GRID = "#e9edf2"

def load():
    if not DATA_FILE.exists(): return {"nodes": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))

def records(): return load().get("nodes", [])
def ds_dates(): return sorted({r["date"] for r in records()})
def mats(d): return sorted({r["expiry"] for r in records() if r["date"] == d}, key=lambda x: float(x[:-1]))
def pct(v): return float(v)*100

def chart(fig, title):
    fig.update_layout(**PLOT, title=dict(text=title, x=0.02, xanchor="left", font=dict(size=14, color="#17212b")), xaxis=dict(showgrid=False), yaxis=dict(gridcolor=GRID, zeroline=False))
    return fig

def card(title, graph_id):
    return html.Div([html.Div(title, className="chart-title"), dcc.Graph(id=graph_id, config={"displayModeBar": False})], className="chart-card")

app.layout = html.Div(className="app-shell", children=[
    html.Div(className="header", children=[html.Div([html.Div("RATES VOLATILITY", className="eyebrow"), html.H1("SABR Surface Monitor"), html.Div("Bloomberg normal-volatility smile calibration · weekly history", className="subtitle")]), html.Div("LIVE DATASET", className="status-pill")]),
    html.Div(className="controls", children=[html.Div([html.Label("Calibration date"), dcc.Dropdown(id="date", clearable=False)], className="control"), html.Div([html.Label("Swaption maturity"), dcc.Dropdown(id="maturity", clearable=False)], className="control"), html.Div(id="dataset-info", className="dataset-info")]),
    html.Div(id="kpis", className="kpi-row"),
    html.Div(id="parameter-table", className="table-panel"),
    html.Div(className="charts", children=[card("SABR smile", "smile"), card("ATM normal volatility", "atm"), card("α — level", "alpha"), card("β — elasticity", "beta"), card("ρ — skew", "rho"), card("ν — curvature", "nu"), card("ATM weekly move", "atm-move")]),
])

@app.callback(Output("date","options"),Output("date","value"),Output("dataset-info","children"),Input("date","value"))
def set_dates(current):
    d=ds_dates(); v=current if current in d else (d[-1] if d else None)
    return ([{"label":x,"value":x} for x in d],v,f"{len(d)} calibration dates · {d[0]} → {d[-1]}" if d else "No dataset")

@app.callback(Output("maturity","options"),Output("maturity","value"),Input("date","value"))
def set_mats(d):
    m=mats(d) if d else []; return ([{"label":x,"value":x} for x in m],m[0] if m else None)

@app.callback(Output("kpis","children"),Output("parameter-table","children"),Input("date","value"),Input("maturity","value"))
def summary(d,m):
    rs=sorted([r for r in records() if r["expiry"]==m],key=lambda r:r["date"])
    cur=next((r for r in rs if r["date"]==d),None)
    if not cur:return [],html.Div()
    vals=[("α",pct(cur["alpha"]),"level"),("β",pct(cur["beta"]),"elasticity"),("ρ",pct(cur["rho"]),"skew"),("ν",pct(cur["nu"]),"curvature"),("ATM",float(cur["atm_normal_vol"])*10000,"normal vol")]
    k=html.Div([html.Div([html.Div(a,className="kpi-label"),html.Div(f"{b:.2f}%" if a!="ATM" else f"{b:.2f} bp",className="kpi-value"),html.Div(c,className="kpi-sub")],className="kpi") for a,b,c in vals])
    available=[r["date"] for r in rs]; target=date.fromisoformat(d)
    def prior(days):
        eligible=[x for x in available if date.fromisoformat(x)<=target.fromordinal(target.toordinal()-days)]; return eligible[-1] if eligible else None
    rows=[]
    for label,dd in [("Selected",d),("Last week",prior(7)),("Last month",prior(30))]:
        r=next((x for x in rs if x["date"]==dd),None)
        if r: rows.append(html.Tr([html.Td([html.Span(label,className="period"),html.Span(dd,className="date-muted")]),html.Td(f"{pct(r['alpha']):.3f}%"),html.Td(f"{pct(r['beta']):.3f}%"),html.Td(f"{pct(r['rho']):.3f}%"),html.Td(f"{pct(r['nu']):.3f}%"),html.Td(f"{float(r['atm_normal_vol'])*10000:.2f} bp")],className="selected" if label=="Selected" else ""))
    table=html.Div([html.Div([html.Span("Parameter snapshot",className="section-title"),html.Span(f"{m} · comparison",className="section-meta")],className="table-head"),html.Table([html.Thead(html.Tr([html.Th("Period"),html.Th("α"),html.Th("β"),html.Th("ρ"),html.Th("ν"),html.Th("ATM normal vol")],className="param-table-head")),html.Tbody(rows)],className="param-table")],className="table-inner")
    return k,table

@app.callback(Output("smile","figure"),Output("alpha","figure"),Output("beta","figure"),Output("rho","figure"),Output("nu","figure"),Output("atm","figure"),Output("atm-move","figure"),Input("date","value"),Input("maturity","value"))
def graphs(d,m):
    rs=sorted([r for r in records() if r["expiry"]==m],key=lambda r:r["date"]); cur=next((r for r in rs if r["date"]==d),None)
    if not cur:return (go.Figure(),)*7
    q=cur["quotes"]; f=float(cur["forward"]); T=float(cur["expiry_years"]); off=[float(x["offset_bp"]) for x in q]; vol=[float(x["market_normal_vol"]) for x in q]
    if 0 not in off:
        i=next((i for i,x in enumerate(off) if x>0),len(off));off.insert(i,0);vol.insert(i,float(cur["atm_normal_vol"]))
    fit=calibrate_sabr(f,T,[f+x/10000 for x in off],vol,beta=float(cur["beta"]))
    xx=list(range(-150,151)); yy=[fit.volatility(f+x/10000,False)*10000 for x in xx]
    s=go.Figure([go.Scatter(x=off,y=[x*10000 for x in vol],mode="markers",name="Bloomberg quotes",marker=dict(size=7)),go.Scatter(x=xx,y=yy,mode="lines",name="SABR fit",line=dict(width=3)),go.Scatter(x=[0],y=[fit.volatility(f,False)*10000],mode="markers",name="SABR ATM",marker=dict(size=9))]);s.update_layout(**PLOT,xaxis_title="Strike offset (bp)",yaxis_title="Normal vol (bp)",legend=dict(orientation="h",y=1.02,x=0))
    x=[r["date"] for r in rs]
    def p(n,t): return chart(go.Figure(go.Scatter(x=x,y=[pct(r[n]) for r in rs],mode="lines+markers",line=dict(width=2))),t)
    a=p("alpha",f"{m} · alpha");b=p("beta",f"{m} · beta");rho=p("rho",f"{m} · rho");nu=p("nu",f"{m} · nu")
    av=[r["atm_normal_vol"]*10000 for r in rs]; at=chart(go.Figure(go.Scatter(x=x,y=av,mode="lines+markers",line=dict(width=2))),f"{m} · ATM normal volatility"); at.update_layout(yaxis_title="bp")
    mv=[None]+[av[i]-av[i-1] for i in range(1,len(av))]; am=chart(go.Figure(go.Bar(x=x,y=mv)),f"{m} · ATM weekly move");am.update_layout(yaxis_title="bp")
    return s,a,b,rho,nu,at,am

if __name__=="__main__": app.run(debug=True)
