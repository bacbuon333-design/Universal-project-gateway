"""
FINAL APPROACH — Use the ORACLE's own structure to understand what actually works.

Key math:
- Oracle 2022-2023: $7,630 profit theoretical max from $0 (perfect trading)
- That equals 76x the starting capital — meaning price moved $76.30 per dollar of starting capital
- 20% capture = $1,526 = catching $15.26 worth of CUMULATIVE price movement per dollar

What catches waves efficiently:
1. Trade ONLY in the direction of the MONTHLY TREND
2. Use WEEKLY SWING POINTS as entry/exit
3. Each major swing should be ~$50-200 range (1-2 months)

Actually from monthly data:
2023-10: +7.35%, range=196pts -> 1 trade in Oct, profit ~$80-130 if caught
2024-03: +9.27%, range=193pts -> same
2024-04: +2.04%, range=195pts -> same

So the strategy should be: ENTER at START of powerful month, EXIT at END.
These months share: ADX >25 AND +DI dominates AND price above weekly high of prior month.

Test: "Monthly Wave Capture" — enter when monthly conditions are right, hold for 2-3 weeks.
Use H1 timeframe approximation: 4 M15 bars = 1 H1. 
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

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0;ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

for yr,(s,e) in windows.items():
    d=df.loc[s:e].copy()
    c=d['close'].values;h=d['high'].values;l=d['low'].values;n=len(c)
    
    # Build H1 bars from M15 (aggregate 4 M15 = 1 H1)
    h1_c=[];h1_h=[];h1_l=[];h1_o=[]
    i=0
    while i+3<n:
        h1_o.append(c[i]);h1_h.append(max(h[i:i+4]));h1_l.append(min(l[i:i+4]));h1_c.append(c[i+3])
        i+=4
    h1c=np.array(h1_c);h1h=np.array(h1_h);h1l=np.array(h1_l);nh1=len(h1c)
    
    # H1 indicators
    e200h1=ema(h1c,200);e50h1=ema(h1c,50);e21h1=ema(h1c,21)
    tr1=np.maximum(h1h[1:]-h1l[1:],np.maximum(np.abs(h1h[1:]-h1c[:-1]),np.abs(h1l[1:]-h1c[:-1])))
    tr1=np.append([tr1[0]],tr1)
    atr14h1=pd.Series(tr1).rolling(14).mean().values
    d2=pd.Series(h1c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsih1=(100-100/(1+g/ls)).values
    up=pd.Series(h1h).diff();dn=-pd.Series(h1l).diff()
    pdm=up.where((up>dn)&(up>0),0.);ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr1).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adxh1=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    dih1=(pdi-ndi).values
    dc_hi_h1=pd.Series(h1h).rolling(20).max().shift(1).values

    # Strategy: BUY when H1 closes above 20-H1 high (=5-day high), H1 bull confirmed
    from dataclasses import dataclass
    @dataclass
    class Tr:
        entry:float=0.;sl:float=0.;tp:float=0.;lot:float=0.01;pnl:float=0.

    bal=1000.;pk=1000.;mx=0.;wins=0;losses=0;n_tr=0;ot=None

    for i in range(250,nh1):
        cv=h1c[i];av=max(atr14h1[i],1.5);rv=rsih1[i];dv=adxh1[i];div=dih1[i]
        bull=cv>e200h1[i] and e50h1[i]>e200h1[i]
        
        if ot:
            done=False;ex=h1c[i]
            if h1l[i]<=ot.sl:ex=ot.sl;done=True
            elif h1h[i]>=ot.tp:ex=ot.tp;done=True
            if done:
                pts=(ex-ot.entry)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net;pk=max(pk,bal)
                dd=pk-bal;mx=max(mx,dd/pk*100)
                n_tr+=1
                if net>0:wins+=1
                else:losses+=1
                ot=None
        
        if ot is None and bull and dv>=20 and div>5:
            # H1 DC20 breakout + RSI 45-65
            if dc_hi_h1[i]>0 and h1c[i]>dc_hi_h1[i] and h1c[i-1]<=dc_hi_h1[i-1] and 42<=rv<=68:
                dd_now=(pk-bal)/pk*100
                r=0.055*(0.15 if dd_now>=15 else 0.35 if dd_now>=10 else 0.65 if dd_now>=6 else 1.0)
                lot=max(0.01,min(round(bal*r/(av/PIP*1.5*0.01)*0.01,2),25.))
                e_=h1c[i]+SPR*PIP;sl_=e_-(av/PIP*1.5)*PIP;tp_=e_+(av/PIP*1.5)*3.5*PIP
                ot=Tr(entry=e_,sl=sl_,tp=tp_,lot=lot)
        
    wr=wins/max(n_tr,1)*100
    cap=(bal-1000)/ORACLE[yr]*100
    print(f"{yr}: bal=${bal:,.2f}({(bal-1000)/10:.1f}%)  n={n_tr}  WR={wr:.1f}%  maxDD={mx:.1f}%  capture={cap:.1f}%")
