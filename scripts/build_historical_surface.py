"""Calibrate Bloomberg normal-SABR smiles on a configurable historical frequency."""
from __future__ import annotations
import argparse,json
from datetime import date,timedelta
from pathlib import Path
from src.bloomberg_history import BloombergHistoryClient
from src.ens_universe import build_ens_universe
from src.sabr import calibrate_sabr
from src.surface import STRIKE_OFFSETS_BP,absolute_volatilities,available_smile_points

def main():
 p=argparse.ArgumentParser();p.add_argument("config",type=Path);p.add_argument("--start",type=date.fromisoformat);p.add_argument("--end",type=date.fromisoformat);p.add_argument("--years",type=float);p.add_argument("--frequency",choices=("DAILY","WEEKLY","MONTHLY"));p.add_argument("--output",type=Path);a=p.parse_args();c=json.loads(a.config.read_text());end=a.end or date.today();start=a.start or end-timedelta(days=round(365.25*(a.years if a.years is not None else c.get("historical_years",1/12)));freq=a.frequency or c.get("historical_frequency","DAILY");expiries=c.get("expiry_years",c.get("maturity_years"));tenors=c.get("swap_tenor_years",[10]);index=c["index"];yellow=c.get("yellow_key","Curncy");field=c.get("field","PX_LAST")
 universe=build_ens_universe(expiries,tenors,index,yellow);secs=[];sm={}
 for e in expiries:
  for t in tenors:
   f=c.get("forward_security_template","EUSA01{years:02d} BGN Curncy").format(years=t);atm=f"ENPS0F{e:02d}{t:02d} {index} {yellow}";sm[(e,t,"forward")]=f;sm[(e,t,"atm")]=atm;secs += [f,atm]+[x.ticker for x in universe[(e,t)]]
 with BloombergHistoryClient(host=c.get("host","localhost"),port=int(c.get("port",8194)),timeout_ms=int(c.get("timeout_ms",10000))) as b:h=b.historical(secs,field,start,end,periodicity=freq)
 rec=[]
 for d in sorted({d for v in h.values() for d in v}):
  for e in expiries:
   for t in tenors:
    f=h.get(sm[(e,t,"forward")],{}).get(d);atm=h.get(sm[(e,t,"atm")],{}).get(d)
    if f is None or atm is None:continue
    raw={x.offset_bp:h.get(x.ticker,{}).get(d) for x in universe[(e,t)]};valid=absolute_volatilities(float(atm),raw)
    if len(valid)<3:continue
    strikes,vols=available_smile_points(float(f),raw,float(atm))
    if len(strikes)<3:continue
    try:s=calibrate_sabr(float(f),float(e),strikes,vols,beta=.5)
    except Exception:continue
    q= s.parameters;rec.append({"date":d,"expiry":f"{e}Y","expiry_years":float(e),"swap_tenor":f"{t}Y","swap_tenor_years":float(t),"forward":float(f),"atm_normal_vol":float(atm)/10000,"alpha":q.alpha,"beta":q.beta,"rho":q.rho,"nu":q.nu,"rms_error":s.rms_error,"quotes":[{"offset_bp":o,"strike":float(f)+o/10000,"market_normal_vol":valid[o],"sabr_normal_vol":s.volatility(float(f)+o/10000)} for o in STRIKE_OFFSETS_BP if o in valid]})
 out=a.output or Path("output/historical_sabr_5y_weekly.json");out.parent.mkdir(exist_ok=True);out.write_text(json.dumps({"index":index,"frequency":freq,"start":start.isoformat(),"end":end.isoformat(),"expiries":expiries,"swap_tenors":tenors,"nodes":rec},indent=2));print(f"Wrote {len(rec)} historical SABR nodes to {out}")
if __name__=="__main__":main()
