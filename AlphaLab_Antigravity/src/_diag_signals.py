"""
NEXUS BRAIN v5 — DIAGNOSTIC PER-YEAR SIGNAL BREAKDOWN
Find exactly which signal works per year so we can isolate the winning combination.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from nexus_brain_v4 import make_ind,gen_signals,backtest,ORACLE

p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)

windows={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01')}

for yr,(s,e) in windows.items():
    d=df.loc[s:e].copy()
    sig,slp,rrv,nm=gen_signals(d)
    # Count signals per type
    from collections import Counter
    cnt=Counter([n for n in nm if n])
    oracle=ORACLE[yr]; tgt=oracle*0.20
    c=d['close'].values
    bull_pct=float(sum(c>pd.Series(c).ewm(span=200,adjust=False).mean().values)/len(c)*100)
    print(f"\n=== {yr} | Oracle20%=${tgt:,.0f} | BullPct={bull_pct:.1f}% ===")
    print(f"  Total signals: {sum(cnt.values())} -> {dict(cnt)}")
    # per signal backtest
    for sname in ['DC_BREAK_BUY','DC_BREAK_SELL','DEEP_PULL_BUY','EMA21_BOUNCE_BUY','BEAR_REBOUND_SELL']:
        # filter only this signal
        sig2=sig.copy(); slp2=slp.copy(); rrv2=rrv.copy(); nm2=nm.copy()
        for i in range(len(sig2)):
            if nm2[i]!=sname: sig2[i]=0
        if not any(sig2!=0): continue
        # mini backtest with filtered signals
        from nexus_brain_v4 import lot_size, Tr
        ci=d['close'].values;hi=d['high'].values;li=d['low'].values
        bal=1000.;pk=1000.;mx=0.;ot=None;trades=[];RISK=0.055
        for i in range(250,len(ci)):
            if ot:
                done=False;ex=ci[i]
                if ot.dir=='BUY':
                    if li[i]<=ot.sl:ex=ot.sl;done=True
                    elif hi[i]>=ot.tp:ex=ot.tp;done=True
                else:
                    if hi[i]>=ot.sl:ex=ot.sl;done=True
                    elif li[i]<=ot.tp:ex=ot.tp;done=True
                if done:
                    pts=(ex-ot.entry)/0.01 if ot.dir=='BUY' else (ot.entry-ex)/0.01
                    net=pts*0.01*(ot.lot/0.01)-(ot.lot/0.01)*0.07
                    bal+=net;pk=max(pk,bal)
                    mx=max(mx,(pk-bal)/pk*100);ot.pnl=net;trades.append(ot);ot=None
            if ot is None and sig2[i]!=0:
                sp=slp2[i]
                if sp>0:
                    lot=lot_size(bal,pk,sp,RISK)
                    if sig2[i]==1:e_=ci[i]+25*0.01;sl_=e_-sp*0.01;tp_=e_+sp*rrv2[i]*0.01;dir='BUY'
                    else:e_=ci[i]-25*0.01;sl_=e_+sp*0.01;tp_=e_-sp*rrv2[i]*0.01;dir='SELL'
                    ot=Tr(dir=dir,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=sname)
        pnls=[t.pnl for t in trades]
        wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
        gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
        print(f"  {sname:<26} n={len(pnls):3d}  bal=${bal:,.2f}  PF={gw/gl:.3f}  maxDD={mx:.1f}%  WR={len(wins)/max(len(pnls),1)*100:.1f}%")
