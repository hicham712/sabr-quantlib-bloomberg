from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from src.sabr import calibrate_sabr
DATA_FILE=Path("output/historical_sabr_5y_weekly.json")
app=Dash(__name__,title="SABR Market Dashboard")
BORDER="#1c2d43"; TEXT="#e7edf5"; ACCENT="#55c2ff"; GREEN="#39d98a"; RED="#ff5c66"
def load_payload(): return json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"nodes":[]}
def load_data(): return load_payload().get("nodes",[])
def dates(r): return sorted({x["date"] for x in r})
def mats(r): return sorted({x["expiry"] for x in r},key=lambda x:float(x[:-1]))
def pct(v): return float(v)*100
def card(label,value,sub=""): return html.Div([html.Div(label,className="kpi-label"),html.Div(value,className="kpi-value"),html.Div(sub,className="kpi-sub")],className="kpi")
def cc(title,id,wide=False): return html.Div([html.Div(title,className="chart-title"),dcc.Graph(id=id,config={"displayModeBar":False})],className="chart-card"+(" chart-wide" if wide else ""))
app.layout=html.Div([html.Div([html.Div([html.Div("RATES / VOLATILITY",className="eyebrow"),html.H1("SABR Market Dashboard"),html.Div("Bloomberg normal-volatility surface · weekly historical calibration",className="subtitle")]),html.Div("LIVE DATASET",className="status-pill")],className="header"),html.Div([html.Div([html.Label("Calibration date"),dcc.Dropdown(id="date",clearable=False,className="dark-dropdown")],className="control"),html.Div([html.Label("Expiry / maturities"),dcc.Dropdown(id="maturity",multi=True,placeholder="Select one, several, or all",className="dark-dropdown")],className="control maturity-control"),html.Div(id="dataset-info",className="dataset-info")],className="controls"),html.Div(id="kpis",className="kpi-row"),html.Div([html.Div("SABR snapshot",className="section-title"),html.Div(id="parameter-table")],className="panel table-panel"),html.Div([cc("SMILES · MARKET VS SABR","smile",True),cc("ALPHA","alpha"),cc("BETA","beta"),cc("RHO","rho"),cc("NU","nu"),cc("ATM NORMAL VOLATILITY","atm"),cc("ATM WEEKLY MOVE","atm-move")],className="charts")],className="app-shell")
@app.callback(Output("date","options"),Output("date","value"),Output("dataset-info","children"),Input("date","value"))
def init_date(cur):
 d=dates(load_data())
 if not d:return [],None,"NO DATA"
 s=cur if cur in d else d[-1];p=load_payload();return [{"label":x,"value":x} for x in d],s,f"{p.get('frequency','weekly').upper()} · {len(d)} calibration dates · {d[0]} → {d[-1]}"
@app.callback(Output("maturity","options"),Output("maturity","value"),Input("date","value"))
def update_maturity(d):
 o=mats(load_data());return [{"label":x,"value":x} for x in o],o
def prior(rs,t,n):
 c=t.toordinal()-n;z=[x for x in rs if date.fromisoformat(x["date"]).toordinal()<=c];return z[-1] if z else None
@app.callback(Output("kpis","children"),Output("parameter-table","children"),Input("date","value"),Input("maturity","value"))
def snapshot(d,selected):
 selected=selected or mats(load_data());data=load_data();t=date.fromisoformat(d) if d else None;rows=[]
 for m in selected:
  rs=sorted([r for r in data if r["expiry"]==m],key=lambda r:r["date"]);r=next((x for x in rs if x["date"]==d),None)
  if r:rows.append((m,r,prior(rs,t,7),prior(rs,t,30)))
 if not rows:return [],html.Div("No calibration available for the selected maturities",className="empty")
 r=rows[0][1];k=[card("SELECTED MATURITIES",str(len(rows)),", ".join(x[0] for x in rows)),card("ATM NORMAL VOL",f"{float(r['atm_normal_vol'])*10000:.2f} bp",rows[0][0]),card("Alpha",f"{pct(r['alpha']):.3f}%",rows[0][0]),card("Beta",f"{pct(r['beta']):.2f}%",rows[0][0]),card("Rho",f"{pct(r['rho']):.2f}%",rows[0][0])]
 header=html.Thead(html.Tr([html.Th(x) for x in ["EXPIRY","PERIOD","DATE","Alpha","Beta","Rho","Nu","ATM"]]));body=[]
 for m,r,lw,lm in rows:
  for label,item in [("Selected",r),("Last week",lw),("Last month",lm)]:
   if item:body.append(html.Tr([html.Td(m,className="period"),html.Td(label),html.Td(item["date"],className="date-muted"),html.Td(f"{pct(item['alpha']):.3f}%"),html.Td(f"{pct(item['beta']):.2f}%"),html.Td(f"{pct(item['rho']):.2f}%"),html.Td(f"{pct(item['nu']):.2f}%"),html.Td(f"{float(item['atm_normal_vol'])*10000:.2f} bp")]))
 return k,html.Table([header,html.Tbody(body)],className="param-table")
def pl(y,h=290):return dict(height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=TEXT,size=13),margin=dict(l=58,r=18,t=10,b=48),xaxis=dict(gridcolor=BORDER,zerolinecolor=BORDER,tickfont=dict(size=11)),yaxis=dict(gridcolor=BORDER,zerolinecolor=BORDER,title=y,tickfont=dict(size=11)),legend=dict(orientation="h",y=1.08,x=0,font=dict(size=11)))
def add_calibration_line(fig,d):
 if d:fig.add_vline(x=d,line_width=2,line_dash="dash",line_color=RED)
@app.callback(Output("smile","figure"),Output("alpha","figure"),Output("beta","figure"),Output("rho","figure"),Output("nu","figure"),Output("atm","figure"),Output("atm-move","figure"),Input("date","value"),Input("maturity","value"))
def graphs(d,selected):
 rs=load_data();selected=selected or mats(rs);sm=go.Figure()
 if not d or not selected:return (go.Figure(),)*7
 palette=["#55c2ff","#39d98a","#b18cff","#ffb454","#ff6b9d","#78dce8","#c7e66a"]
 for j,m in enumerate(selected):
  s=next((r for r in rs if r["date"]==d and r["expiry"]==m),None)
  if not s:continue
  q=s["quotes"];f=float(s["forward"]);t=float(s["expiry_years"]);o=[float(x["offset_bp"]) for x in q];v=[float(x["market_normal_vol"]) for x in q]
  if 0 not in o:
   i=next((i for i,x in enumerate(o) if x>0),len(o));o.insert(i,0);v.insert(i,float(s["atm_normal_vol"]))
  fit=calibrate_sabr(f,t,[f+x/10000 for x in o],v,beta=float(s["beta"]));xo=list(range(-150,151));yv=[fit.volatility(f+x/10000,False)*10000 for x in xo];c=palette[j%len(palette)]
  sm.add_trace(go.Scatter(x=xo,y=yv,mode="lines",name=f"{m} SABR",line=dict(width=2.5,color=c)));sm.add_trace(go.Scatter(x=[x["offset_bp"] for x in q],y=[x["market_normal_vol"]*10000 for x in q],mode="markers",name=f"{m} Bloomberg",marker=dict(size=7,color=c,opacity=.7),legendgroup=m));sm.add_trace(go.Scatter(x=[0],y=[s["atm_normal_vol"]*10000],mode="markers",name=f"{m} ATM",marker=dict(size=10,color=c),legendgroup=m,showlegend=False))
 sm.update_layout(**pl("Normal vol (bp)",430),xaxis_title="Strike offset (bp)")
 def hist(param):
  f=go.Figure()
  for j,m in enumerate(selected):
   h=sorted([r for r in rs if r["expiry"]==m],key=lambda r:r["date"]);x=[r["date"] for r in h];f.add_trace(go.Scatter(x=x,y=[pct(r[param]) for r in h],mode="lines+markers",name=m,line=dict(color=palette[j%len(palette)],width=2),marker=dict(size=4),hovertemplate="%{x}<br>%{y:.2f}%<extra></extra>"))
  f.update_layout(**pl("%"));add_calibration_line(f,d);return f
 a,b,r,n=[hist(z) for z in ["alpha","beta","rho","nu"]]
 def atm_graph():
  f=go.Figure()
  for j,m in enumerate(selected):
   h=sorted([r for r in rs if r["expiry"]==m],key=lambda r:r["date"]);f.add_trace(go.Scatter(x=[r["date"] for r in h],y=[r["atm_normal_vol"]*10000 for r in h],mode="lines+markers",name=m,line=dict(color=palette[j%len(palette)],width=2),marker=dict(size=4),hovertemplate="%{x}<br>%{y:.2f} bp<extra></extra>"))
  f.update_layout(**pl("bp"));add_calibration_line(f,d);return f
 at=atm_graph()
 def move_graph():
  f=go.Figure()
  for j,m in enumerate(selected):
   h=sorted([r for r in rs if r["expiry"]==m],key=lambda r:r["date"]);av=[r["atm_normal_vol"]*10000 for r in h];mv=[None]+[av[i]-av[i-1] for i in range(1,len(av))];f.add_trace(go.Bar(x=[r["date"] for r in h],y=mv,name=m,marker_color=palette[j%len(palette)],opacity=.65,hovertemplate="%{x}<br>%{y:.2f} bp<extra></extra>"))
  f.update_layout(**pl("bp"),barmode="group");add_calibration_line(f,d);return f
 return sm,a,b,r,n,at,move_graph()
if __name__=="__main__":app.run(debug=True)