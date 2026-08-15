"""
NEXUS BRAIN v5 — FOCUSED PULLBACK DIAGNOSTIC
Key insight: DC_BREAK_BUY works only in 2023-2024 (PF=1.425), fails in 2022-2023 (PF=0.624) and 2024-2025 (PF=1.062 barely profitable).
DC_BREAK_SELL: only works in 2023-2024 (PF=1.276).

Root cause of 2022-2023 failure: 2022 was a STRONG BEAR year (May-Oct 2022 all negative months).
Root cause of 2024-2025 failure: DC breakout overfires in strong bull — price breaks out but quickly 
  gets tagged SL on normal pullback. Better to use PULLBACK in 2024-2025.

Strategy per year fingerprint:
  2022-2023: Mixed (first 6 months bear, last 6 months bull) -> need both Long pullback AND Short rebound
  2023-2024: Gradual bull with spiky months -> DC breakout works for the Oct+Mar+Apr spikes
  2024-2025: Strong continuous bull -> PULLBACK strategy optimal

Test: ONLY use DEEP_PULLBACK_BUY signal but calibrate it properly.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def compute_all(c,h,l):
    e8=ema(c,8);e21=ema(c,21);e50=ema(c,50);e200=ema(c,200)
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    d2=pd.Series(c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h).diff();dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.);ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # EMA slope for macro bias (50-bar change in EMA200 = ~12.5H timeframe)
    e200_slope = np.gradient(e200)   # rising or falling EMA200
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,atr14=atr14,rsi=rsi,adx=adx,di=di,e200_slope=e200_slope)

def gen_signals(df):
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    n=len(c);ind=compute_all(c,h,l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    e200s=ind['e200_slope']
    sig=np.zeros(n,dtype=int);slp=np.zeros(n);rrv=np.zeros(n);nm=['']*n

    for i in range(250,n):
        cv=c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        sloping_up   = e200s[i] > 0    # EMA200 currently rising
        sloping_down = e200s[i] < 0

        # Strict macro alignment
        macro_bull = cv > e200[i] and e50[i] > e200[i] and sloping_up
        macro_bear = cv < e200[i] and e50[i] < e200[i] and sloping_down

        # ── BUY SIGNALS ─────────────────────────────────────────
        # S1: EMA8 Deep Pullback — most robust signal from IS analysis
        if macro_bull and dv >= 16:
            # Strict: wick must tag EMA8 but close ABOVE (demand absorbed)
            if l[i] <= e8[i] and cv > e8[i] and rv <= 44 and cv > e21[i]:
                rr = 4.0 if dv >= 26 else 3.5
                sig[i]=1;slp[i]=(av/PIP)*1.35+SPR;rrv[i]=rr;nm[i]='PULL_BUY_E8';continue

        # S2: EMA21 Deep Pullback — catches bigger corrections
        if macro_bull and dv >= 18:
            if l[i] <= e21[i] and cv > e21[i] and rv <= 38 and cv > e50[i]:
                sig[i]=1;slp[i]=(av/PIP)*1.5+SPR*1.1;rrv[i]=3.5;nm[i]='PULL_BUY_E21';continue

        # ── SELL SIGNALS ────────────────────────────────────────
        # S3: EMA8 Rebound Sell — mirror of S1 for bear macro
        if macro_bear and dv >= 16:
            if h[i] >= e8[i] and cv < e8[i] and rv >= 56 and cv < e21[i]:
                rr = 4.0 if dv >= 26 else 3.5
                sig[i]=-1;slp[i]=(av/PIP)*1.35+SPR;rrv[i]=rr;nm[i]='PULL_SELL_E8';continue

        # S4: EMA21 Rebound Sell — deeper bear rebound
        if macro_bear and dv >= 18:
            if h[i] >= e21[i] and cv < e21[i] and rv >= 62 and cv < e50[i]:
                sig[i]=-1;slp[i]=(av/PIP)*1.5+SPR*1.1;rrv[i]=3.5;nm[i]='PULL_SELL_E21';continue

    return sig,slp,rrv,nm

def lot_size(eq,pk,slp,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=16:r=risk*0.2
    elif dd>=11:r=risk*0.42
    elif dd>=7:r=risk*0.68
    else:r=risk
    return max(0.01,min(round(eq*r/(slp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str='';entry:float=0.;sl:float=0.;tp:float=0.
    lot:float=0.01;pnl:float=0.;sname:str=''

def backtest(df,risk=0.055):
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    sig,slp,rrv,nm=gen_signals(df)
    bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None
    for i in range(250,len(c)):
        if ot:
            done=False;ex=c[i]
            if ot.dir=='BUY':
                if l[i]<=ot.sl:ex=ot.sl;done=True
                elif h[i]>=ot.tp:ex=ot.tp;done=True
            else:
                if h[i]>=ot.sl:ex=ot.sl;done=True
                elif l[i]<=ot.tp:ex=ot.tp;done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else (ot.entry-ex)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net;pk=max(pk,bal)
                dd=pk-bal;mx=max(mx,dd/pk*100)
                ot.pnl=net;sn=ot.sname
                if sn not in stats:stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1;stats[sn]['pnl']+=net
                if net>0:stats[sn]['w']+=1;stats[sn]['wu']+=net
                else:stats[sn]['lu']+=abs(net)
                trades.append(ot);ot=None
        if ot is None and sig[i]!=0:
            sp=slp[i]
            if sp>0:
                lot=lot_size(bal,pk,sp,risk)
                s2=SPR*PIP
                if sig[i]==1:e_=c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY'
                else:e_=c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL'
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=nm[i])
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    s=pd.Series(pnls)
    sh=float(s.mean()/s.std()*np.sqrt(252*24)) if len(s)>1 and s.std()>0 else 0.
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,sh=sh,stats=stats)

def main():
    print("="*66)
    print("🧠 NEXUS BRAIN v5 — EMA PULLBACK/REBOUND PURE ENGINE")
    print("="*66)
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    wins_map={'2022-2023':('2022-05-02','2023-05-01'),
              '2023-2024':('2023-05-01','2024-05-01'),
              '2024-2025':('2024-05-01','2025-05-01'),
              '2025-2026':('2025-05-01','2026-07-24')}
    RISK=0.055;rows=[]
    for yr,(s,e) in wins_map.items():
        d=df.loc[s:e].copy();r=backtest(d,RISK)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>=tgt*0.75)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3}")

    print("\n📊 Per-signal (combined):")
    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined:combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]:combined[sn][k]+=st[k]
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<26}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V5_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v5 — MULTI-YEAR GAUNTLET",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Target20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
