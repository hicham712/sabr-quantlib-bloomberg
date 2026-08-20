from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from src.sabr import calibrate_sabr
DATA_FILE=Path("output/historical_sabr_5y_weekly.json")
app=Dash(__name__,title="SABR Market Dashboard")
BORDER="#1c2d43"; TEXT="#e7edf5"; ACCENT="#55c2ff"; GREEN="#39d98a"
def load_payload(): return json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"nodes":[]}
def load_data(): return load_payload().get("nodes",[])
def dates(r): return sorted({x["date"] for x in r})
def mats(r,d): return sorted({x["expiry"] for x in r if x["date"]==d},key=lambda x:float(x[:-1]))
def pct(v): return float(v)*100
def card(label,value,sub=""): return html.Div([html.Div(label,className="kpi-label"),html.Div(value,className="kpi-value"),html.Div(sub,className="kpi-sub")],className="kpi")
def cc(title,id,wide=False): return html.Div([html.Div(title,className="chart-title"),dcc.Graph(id=id,config={"displayModeBar":False})],className="chart-card"+(" chart-wide" if wide else ""))
app.layout=html.Div([html.Div([html.Div([html.Div("RATES / VOLATILITY",className="eyebrow"),html.H1("SABR Market Dashboard"),html.Div("Bloomberg normal-volatility surface · weekly historical calibration",className="subtitle")]),html.Div("LIVE DATASET",className="status-pill")],className="header"),html.Div([html.Div([html.Label("Calibration date"),dcc.Dropdown(id="date",clearable=False,className="dark-dropdown")],className="control"),html.Div([html.Label("Maturity"),dcc.Dropdown(id="maturity",clearable=False,className="dark-dropdown")],className="control"),html.Div(id="dataset-info",className="dataset-info")],className="controls"),html.Div(id="kpis",className="kpi-row"),html.Div([html.Div("SABR snapshot",className="section-title"),html.Div(id="parameter-table")],className="panel table-panel"),html.Div([cc("SMILE · MARKET VS SABR","smile",True),cc("ALPHA","alpha"),cc("BETA","beta"),cc("RHO","rho"),cc("NU","nu"),cc("ATM NORMAL VOLATILITY","atm"),cc("ATM WEEKLY MOVE","atm-move")],className="charts")],className="app-shell")
@app.callback(Output("date","options"),Output("date","value"),Output("dataset-info","children"),Input("date","value"))
def init_date(cur):
 d=dates(load_data())
 if not d:return [],None,"NO DATA"
 s=cur if cur in d else d[-1];p=load_payload();return [{"label":x,"value":x} for x in d],s,f"{p.get('frequency','weekly').upper()} · {len(d)} calibration dates · {d[0]} → {d[-1]}"
@app.callback(Output("maturity","options"),Output("maturity","value"),Input("date","value"))
def update_maturity(d):
 o=mats(load_data(),d);return [{"label":x,"value":x} for x in o],o[0] if o else None
@app.callback(Output("kpis","children"),Output("parameter-table","children"),Input("date","value"),Input("maturity","value"))
def snapshot(d,m):
 rs=sorted([r for r in load_data() if r["expiry"]==m],key=lambda r:r["date"]);r=next((x for x in rs if x["date"]==d),None)
 if not r:return [],html.Div("No calibration available",className="empty")
 t=date.fromisoformat(d)
 def prior(n):
  c=t.toordinal()-n;z=[x for x in rs if date.fromisoformat(x["date"]).toordinal()<=c];return z[-1] if z else None
 rows=[("Selected",r),("Last week",prior(7)),("Last month",prior(30))]
 k=[card("ATM NORMAL VOL",f"{float(r['atm_normal_vol'])*10000:.2f} bp",m),card("ALPHA",f"{pct(r['alpha']):.3f}%"),card("BETA",f"{pct(r['beta']):.2f}%"),card("RHO",f"{pct(r['rho']):.2f}%"),card("NU",f"{pct(r['nu']):.2f}%")]
 header=html.Thead(html.Tr([html.Th(x) for x in ["PERIOD","DATE","α","β","ρ","ν","ATM"]]))
 body=html.Tbody([html.Tr([html.Td(label,className="period"),html.Td(item["date"],className="date-muted"),html.Td(f"{pct(item['alpha']):.3f}%"),html.Td(f"{pct(item['beta']):.2f}%"),html.Td(f"{pct(item['rho']):.2f}%"),html.Td(f"{pct(item['nu']):.2f}%"),html.Td(f"{float(item['atm_normal_vol'])*10000:.2f} bp")]) for label,item in rows if item])
 return k,html.Table([header,body],className="param-table")
def pl(y,h=290): return dict(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=TEXT,size=11),margin=dict(l=48,r=18,t=8,b=42),xaxis=dict(gridcolor=BORDER,zerolinecolor=BORDER),yaxis=dict(gridcolor=BORDER,zerolinecolor=BORDER,title=y),legend=dict(orientation="h",y=1.08,x=0))
@app.callback(Output("smile","figure"),Output("alpha","figure"),Output("beta","figure"),Output("rho","figure"),Output("nu","figure"),Output("atm","figure"),Output("atm-move","figure"),Input("date","value"),Input("maturity","value"))
def graphs(d,m):
 rs=load_data();e=go.Figure()
 if not d or not m:return(e,)*7
 s=next((r for r in rs if r["date"]==d and r["expiry"]==m),None);sm=go.Figure()
 if s:
  q=s["quotes"];f=float(s["forward"]);t=float(s["expiry_years"]);o=[float(x["offset_bp"]) for x in q];v=[float(x["market_normal_vol"]) for x in q]
  if 0 not in o:
   i=next((i for i,x in enumerate(o) if x>0),len(o));o.insert(i,0);v.insert(i,float(s["atm_normal_vol"]))
  fit=calibrate_sabr(f,t,[f+x/10000 for x in o],v,beta=float(s["beta"]));xo=list(range(-150,151));yv=[fit.volatility(f+x/10000,False)*10000 for x in xo]
  sm.add_trace(go.Scatter(x=[x["offset_bp"] for x in q],y=[x["market_normal_vol"]*10000 for x in q],mode="markers",name="Bloomberg",marker=dict(size=8)));sm.add_trace(go.Scatter(x=[0],y=[s["atm_normal_vol"]*10000],mode="markers",name="ATM",marker=dict(size=11)));sm.add_trace(go.Scatter(x=xo,y=yv,mode="lines",name="SABR",line=dict(width=2.5,color=ACCENT)));sm.update_layout(**pl("Normal vol (bp)",430),xaxis_title="Strike offset (bp)")
 h=sorted([r for r in rs if r["expiry"]==m],key=lambda r:r["date"]);x=[r["date"] for r in h]
 def p(n):
  f=go.Figure(go.Scatter(x=x,y=[pct(r[n]) for r in h],mode="lines+markers",line=dict(color=ACCENT,width=2),marker=dict(size=5)));f.update_layout(**pl("%"));return f
 a,b,r,n=[p(z) for z in ["alpha","beta","rho","nu"]];av=[z["atm_normal_vol"]*10000 for z in h];at=go.Figure(go.Scatter(x=x,y=av,mode="lines+markers",line=dict(color=GREEN,width=2),marker=dict(size=5)));at.update_layout(**pl("bp"));mv=[None]+[av[i]-av[i-1] for i in range(1,len(av))];am=go.Figure(go.Bar(x=x,y=mv,marker_color=ACCENT));am.update_layout(**pl("bp"));return sm,a,b,r,n,at,am
if __name__=="__main__": app.run(debug=True)
