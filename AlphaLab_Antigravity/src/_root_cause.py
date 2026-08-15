"""
ROOT CAUSE ANALYSIS
====================
Problem: PULL_E8_BUY PF=0.897, n=533. Losing strategy even with R:R>3.

The REAL issue is EMA8 pullback in M15 is TOO NOISY. 
Gold on M15 constantly touches EMA8 — it's not a meaningful signal.

Let me verify: In 2022-2023 with DC_BREAK_BUY alone from diag:
  n=62, bal=$765.90, PF=0.624 — also losing
  
But DC_BREAK_BUY in 2023-2024 alone:
  n=57, bal=$1,686.20, PF=1.425, WR=33.3% — STRONG WINNER

THE KEY: 2023-2024 has the RIGHT environment for DC breakouts because:
- Oct 2023: +7.35% (broke 1 year resistance)
- Mar 2024: +9.27% (strong bull impulse)
- Apr 2024: +2.04% but +195pts range (huge volatility)

What these months have in common: LARGE MONTHLY RANGE + clear directional bias.

Real solution: Only trade when MOMENTUM is CONFIRMED across multiple timeframes.

Let me test: DC_BREAKOUT with MONTHLY MOMENTUM filter
Monthly momentum = current close vs 4-week high-low midpoint (direction)
Only trade when monthly momentum aligns with trade direction.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)

windows={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01')}

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0

for yr,(s,e) in windows.items():
    d=df.loc[s:e].copy()
    c=d['close'].values;h=d['high'].values;l=d['low'].values;n=len(c)
    e200=ema(c,200);e50=ema(c,50)
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    up=pd.Series(h).diff();dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.);ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # Monthly momentum: compare current price to price 480 bars ago (1 month ~480 M15 bars)
    monthly_up=np.zeros(n,dtype=bool)
    for i in range(480,n):
        monthly_up[i]=c[i]>c[i-480]
    # Weekly momentum: 96 bars
    weekly_up=np.zeros(n,dtype=bool)
    for i in range(96,n):
        weekly_up[i]=c[i]>c[i-96]
    # DC20 breakout
    dc_hi=pd.Series(h).rolling(20).max().shift(1).values
    dc_lo=pd.Series(l).rolling(20).min().shift(1).values

    # Test: DC_BREAK_BUY with monthly + weekly alignment
    bal=1000.;pk=1000.;mx=0.;wins=0;losses=0;n_tr=0;ot=None
    from dataclasses import dataclass
    @dataclass
    class Tr:
        entry:float=0.;sl:float=0.;tp:float=0.;lot:float=0.01;pnl:float=0.

    for i in range(500,n):
        if ot:
            done=False;ex=c[i]
            if l[i]<=ot.sl:ex=ot.sl;done=True
            elif h[i]>=ot.tp:ex=ot.tp;done=True
            if done:
                pts=(ex-ot.entry)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net;pk=max(pk,bal)
                dd=pk-bal;mx=max(mx,dd/pk*100)
                n_tr+=1
                if net>0:wins+=1
                else:losses+=1
                ot=None
        if ot is None:
            bull=c[i]>e200[i] and e50[i]>e200[i]
            # DC breakout with monthly+weekly+ADX filter
            if (bull and adx[i]>=20 and di[i]>8 
                    and monthly_up[i] and weekly_up[i]
                    and dc_hi[i]>0 and c[i]>dc_hi[i] and c[i-1]<=dc_hi[i-1]):
                av=max(atr14[i],1.5)
                dd_now=(pk-bal)/pk*100
                r=0.055*(0.2 if dd_now>=16 else 0.42 if dd_now>=11 else 0.68 if dd_now>=7 else 1.0)
                lot=max(0.01,min(round(bal*r/(av/PIP*1.5*0.01)*0.01,2),25.))
                e_=c[i]+SPR*PIP;sl_=e_-(av/PIP*1.5)*PIP;tp_=e_+(av/PIP*1.5)*3.5*PIP
                ot=Tr(entry=e_,sl=sl_,tp=tp_,lot=lot)

    wr=wins/max(n_tr,1)*100
    print(f"{yr}: bal=${bal:,.2f}  n={n_tr}  WR={wr:.1f}%  maxDD={mx:.1f}%  wins={wins}  losses={losses}")
