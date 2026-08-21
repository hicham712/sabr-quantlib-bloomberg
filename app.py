from __future__ import annotations
import json
from pathlib import Path
from datetime import date
import plotly.graph_objects as go
from dash import Dash,Input,Output,dcc,html
from src.sabr import calibrate_sabr
DATA=Path('output/historical_sabr_5y_weekly.json');app=Dash(__name__,title='SABR Market Dashboard')
C=['#55c2ff','#39d98a','#b18cff','#ffb454','#ff6b9d','#78dce8','#c7e66a'];RED='#ff5c66';B='#1c2d43';T='#e7edf5'
def D():
 try:return json.loads(DATA.read_text()).get('nodes',[])
 except:return []
def pct(x):return float(x)*100
def opts(v):return [{'label':x,'value':x} for x in v]
def unique(n,k):return sorted({x[k] for x in n},key=lambda x:float(str(x).rstrip('Y')))
def layout(y,h=300):return dict(height=h,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color=T,size=13),margin=dict(l=55,r=15,t=10,b=45),xaxis=dict(gridcolor=B,zerolinecolor=B),yaxis=dict(gridcolor=B,zerolinecolor=B,title=y),legend=dict(orientation='h',y=1.08,x=0))
def line(fig,d):
 if d:fig.add_vline(x=d,line_width=2,line_dash='dash',line_color=RED)
app.layout=html.Div([html.H1('SABR Market Dashboard'),html.Div([html.Div([html.Label('Calibration date'),dcc.Dropdown(id='date',clearable=False,className='dark-dropdown')],className='control'),html.Div([html.Label('Option expiry'),dcc.Dropdown(id='expiry',multi=True,placeholder='All expiries',className='dark-dropdown')],className='control'),html.Div([html.Label('Swap tenor / underlying'),dcc.Dropdown(id='tenor',multi=True,placeholder='All swap tenors',className='dark-dropdown')],className='control')],className='controls'),html.Div(id='info'),html.Div(id='table',className='panel'),html.Div([dcc.Graph(id='smile'),dcc.Graph(id='alpha'),dcc.Graph(id='beta'),dcc.Graph(id='rho'),dcc.Graph(id='nu'),dcc.Graph(id='atm'),dcc.Graph(id='move')],className='charts')],className='app-shell')
@app.callback(Output('date','options'),Output('date','value'),Output('expiry','options'),Output('expiry','value'),Output('tenor','options'),Output('tenor','value'),Input('date','value'))
def init(d):
 n=D();ds=sorted({x['date'] for x in n});es=unique(n,'expiry');ts=unique(n,'swap_tenor');return opts(ds),d if d in ds else (ds[-1] if ds else None),opts(es),es,opts(ts),ts
@app.callback(Output('table','children'),Input('date','value'),Input('expiry','value'),Input('tenor','value'))
def table(d,es,ts):
 n=[x for x in D() if x['date']==d and (not es or x['expiry'] in es) and (not ts or x['swap_tenor'] in ts)]
 if not n:return 'No calibration available.'
 rows=[]
 for x in n:rows.append(html.Tr([html.Td(x['expiry']),html.Td(x['swap_tenor']),html.Td(f"{pct(x['alpha']):.3f}%"),html.Td(f"{pct(x['beta']):.2f}%"),html.Td(f"{pct(x['rho']):.2f}%"),html.Td(f"{pct(x['nu']):.2f}%"),html.Td(f"{x['atm_normal_vol']*10000:.2f} bp")]))
 return html.Table([html.Thead(html.Tr([html.Th(x) for x in ['Expiry','Swap tenor','Alpha','Beta','Rho','Nu','ATM']])),html.Tbody(rows)],className='param-table')
@app.callback(Output('smile','figure'),Output('alpha','figure'),Output('beta','figure'),Output('rho','figure'),Output('nu','figure'),Output('atm','figure'),Output('move','figure'),Input('date','value'),Input('expiry','value'),Input('tenor','value'))
def graphs(d,es,ts):
 n=D();es=es or unique(n,'expiry');ts=ts or unique(n,'swap_tenor');sm=go.Figure();hist={k:go.Figure() for k in ['alpha','beta','rho','nu','atm','move']}
 for j,(e,t) in enumerate((e,t) for e in es for t in ts):
  s=next((x for x in n if x['date']==d and x['expiry']==e and x['swap_tenor']==t),None);col=C[j%len(C)]
  if s:
   q=s['quotes'];o=[float(x['offset_bp']) for x in q];v=[float(x['market_normal_vol']) for x in q];f=float(s['forward']);fit=calibrate_sabr(f,float(s['expiry_years']),[f+x/10000 for x in o]+[f],v+[float(s['atm_normal_vol'])],beta=.5);xo=list(range(-150,151));sm.add_trace(go.Scatter(x=xo,y=[fit.volatility(f+x/10000,False)*10000 for x in xo],name=f'{e} x {t}',line=dict(color=col,width=2.5)));sm.add_trace(go.Scatter(x=o,y=[x['market_normal_vol']*10000 for x in q],mode='markers',name=f'{e} x {t} BBG',marker=dict(color=col,size=7),showlegend=False))
  h=sorted([x for x in n if x['expiry']==e and x['swap_tenor']==t],key=lambda x:x['date']);xs=[x['date'] for x in h];
  for k in ['alpha','beta','rho','nu'] : hist[k].add_trace(go.Scatter(x=xs,y=[pct(x[k]) for x in h],name=f'{e} x {t}',line=dict(color=col)))
  av=[x['atm_normal_vol']*10000 for x in h];hist['atm'].add_trace(go.Scatter(x=xs,y=av,name=f'{e} x {t}',line=dict(color=col)));hist['move'].add_trace(go.Bar(x=xs,y=[None]+[av[i]-av[i-1] for i in range(1,len(av))],name=f'{e} x {t}',marker_color=col,opacity=.65))
 sm.update_layout(**layout('Normal vol (bp)',430),xaxis_title='Strike offset (bp)');out=[sm]
 for k in ['alpha','beta','rho','nu','atm','move']:hist[k].update_layout(**layout('%' if k in ['alpha','beta','rho','nu'] else 'bp'));line(hist[k],d);out.append(hist[k])
 return out
if __name__=='__main__':app.run(debug=True)
