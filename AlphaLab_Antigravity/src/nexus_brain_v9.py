"""
NEXUS BRAIN v9 — H1 TIMEFRAME ENGINE (FINAL PRODUCTION)
==========================================================
Key finding from research:
- H1 DC20 breakout: 2022-2023 WR=37.5% DD=13.7%, 2023-2024 WR=29.4% DD=18.7%
- 2024-2025 weak because it's TREND-FOLLOWING in a strongly trending year
  → in 2024-2025, price rarely retests DC20 because it's in parabolic uptrend
  → need to add PULLBACK_TO_EMA signal for trending years

COMBINED STRATEGY:
1. H1 DC20 Breakout Buy (works in impulse + early trend months)
2. H1 EMA21 Pullback Buy (works in sustained trend months)
3. Short: H1 DC20 Breakdown Sell ONLY when e50 < e200

H1 = 4 M15 bars = 1 hour
DC20 H1 = 5-day high/low (20 hours)
EMA21 H1 ≈ 1-week EMA
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def m15_to_h1(df):
    """Resample M15 OHLCV to H1 by grouping 4 bars"""
    c=df['close'].values;h=df['high'].values;l=df['low'].values;o=df['open'].values if 'open' in df.columns else c
    n=len(c); segments=n//4
    h1_c=np.array([c[i*4+3] for i in range(segments)])
    h1_h=np.array([max(h[i*4:i*4+4]) for i in range(segments)])
    h1_l=np.array([min(l[i*4:i*4+4]) for i in range(segments)])
    return h1_c,h1_h,h1_l,segments

def make_h1_ind(c,h,l):
    e8=ema(c,8);e21=ema(c,21);e50=ema(c,50);e200=ema(c,200)
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr50=pd.Series(tr).rolling(50).mean().values
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
    atr_r=atr14/np.where(atr50>0,atr50,1e-9)
    # Donchian 20H1 (=5-day highs/lows)
    dc_hi=pd.Series(h).rolling(20).max().shift(1).values
    dc_lo=pd.Series(l).rolling(20).min().shift(1).values
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,
                atr14=atr14,atr_r=atr_r,rsi=rsi,adx=adx,di=di,
                dc_hi=dc_hi,dc_lo=dc_lo)

def gen_h1_signals(h1c,h1h,h1l,nh1,cfg=None):
    if cfg is None: cfg={}
    ind=make_h1_ind(h1c,h1h,h1l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];atr_r=ind['atr_r']
    rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    dc_hi=ind['dc_hi'];dc_lo=ind['dc_lo']
    sig=np.zeros(nh1,dtype=int);slp=np.zeros(nh1);rrv=np.zeros(nh1);nm=['']*nh1

    adx_min=cfg.get('adx_min',18)
    rsi_buy=cfg.get('rsi_buy',65)
    rsi_sell=cfg.get('rsi_sell',35)
    rr_dc=cfg.get('rr_dc',3.5)
    rr_pull=cfg.get('rr_pull',3.0)
    sl_dc=cfg.get('sl_dc',1.5)
    sl_pull=cfg.get('sl_pull',1.3)
    use_short=cfg.get('use_short',True)

    for i in range(250,nh1):
        cv=h1c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        bull=cv>e200[i] and e50[i]>e200[i]
        bear=cv<e200[i] and e50[i]<e200[i]
        ar=atr_r[i]
        trend_bonus=0.5 if dv>=28 else 0.2 if dv>=22 else 0.

        # ── S1: H1 DC20 Breakout Buy ──────────────────────────
        if bull and dv>=adx_min and div>5 and ar>=1.0:
            if dc_hi[i]>0 and h1c[i]>dc_hi[i] and h1c[i-1]<=dc_hi[i-1] and rv<=rsi_buy:
                sig[i]=1;slp[i]=(av/PIP)*sl_dc+SPR;rrv[i]=rr_dc+trend_bonus
                nm[i]='H1_DC_BREAK_BUY';continue

        # ── S2: H1 EMA21 Pullback Buy (trending year supplement) ──
        if bull and dv>=adx_min and div>0:
            if h1l[i]<=e21[i] and h1c[i]>e21[i] and rv<=50:
                sig[i]=1;slp[i]=(av/PIP)*sl_pull+SPR;rrv[i]=rr_pull+trend_bonus
                nm[i]='H1_EMA21_PULL_BUY';continue

        if use_short:
            # ── S3: H1 DC20 Breakdown Sell ──────────────────────
            if bear and dv>=adx_min and div<-5 and ar>=1.0:
                if dc_lo[i]>0 and h1c[i]<dc_lo[i] and h1c[i-1]>=dc_lo[i-1] and rv>=rsi_sell:
                    sig[i]=-1;slp[i]=(av/PIP)*sl_dc+SPR;rrv[i]=rr_dc+trend_bonus
                    nm[i]='H1_DC_BREAK_SELL';continue

            # ── S4: H1 EMA21 Rebound Sell ──────────────────────
            if bear and dv>=adx_min and div<0:
                if h1h[i]>=e21[i] and h1c[i]<e21[i] and rv>=50:
                    sig[i]=-1;slp[i]=(av/PIP)*sl_pull+SPR;rrv[i]=rr_pull+trend_bonus
                    nm[i]='H1_EMA21_REBOUND_SELL';continue

    return sig,slp,rrv,nm

def lot_size(eq,pk,slp,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=15:r=risk*0.15
    elif dd>=10:r=risk*0.38
    elif dd>=6:r=risk*0.68
    else:r=risk
    return max(0.01,min(round(eq*r/(slp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str='';entry:float=0.;sl:float=0.;tp:float=0.
    lot:float=0.01;pnl:float=0.;sname:str=''

def backtest_h1(df,risk=0.055,cfg=None):
    h1c,h1h,h1l,nh1=m15_to_h1(df)
    sig,slp,rrv,nm=gen_h1_signals(h1c,h1h,h1l,nh1,cfg)
    bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None
    for i in range(250,nh1):
        if ot:
            done=False;ex=h1c[i]
            if ot.dir=='BUY':
                if h1l[i]<=ot.sl:ex=ot.sl;done=True
                elif h1h[i]>=ot.tp:ex=ot.tp;done=True
            else:
                if h1h[i]>=ot.sl:ex=ot.sl;done=True
                elif h1l[i]<=ot.tp:ex=ot.tp;done=True
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
                if sig[i]==1:e_=h1c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY'
                else:e_=h1c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL'
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=nm[i])
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def run_gauntlet(RISK=0.055,cfg=None):
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    wm={'2022-2023':('2022-05-02','2023-05-01'),
        '2023-2024':('2023-05-01','2024-05-01'),
        '2024-2025':('2024-05-01','2025-05-01'),
        '2025-2026':('2025-05-01','2026-07-24')}
    rows=[]
    for yr,(s,e) in wm.items():
        d=df.loc[s:e].copy();r=backtest_h1(d,RISK,cfg)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>=tgt*0.60)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def main():
    print("="*66)
    print("🧠 NEXUS BRAIN v9 — H1 TIMEFRAME MULTI-SIGNAL ENGINE")
    print("="*66)
    # Default config
    cfg={'adx_min':18,'rsi_buy':65,'rsi_sell':35,'rr_dc':3.5,'rr_pull':3.0,
         'sl_dc':1.5,'sl_pull':1.3,'use_short':True}
    RISK=0.055
    rows=run_gauntlet(RISK,cfg)

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

    print("\n📊 Combined signal stats:")
    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined:combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]:combined[sn][k]+=st[k]
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<28}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    print("\n📋 Per-year detail:")
    for yr,r,o,t,cap,v in rows:
        line=f"  [{yr}]"
        for sn,st in r['stats'].items():
            pf2=st['wu']/max(st['lu'],1e-9)
            wr2=st['w']/max(st['n'],1)*100
            line+=f"  {sn}:n={st['n']},pnl={st['pnl']:+.0f},pf={pf2:.2f},wr={wr2:.0f}%"
        print(line)

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V9_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v9 — H1 ENGINE MULTI-YEAR REPORT",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           f"**Timeframe**: H1 (4×M15) | Risk: {RISK*100}% | Spread: {SPR}pts | Comm: ${COMM}",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
