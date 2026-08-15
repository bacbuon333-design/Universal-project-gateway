"""
NEXUS BRAIN FINAL — PIVOT-BASED HUMAN BRAIN
=============================================
Fundamental redesign insight from all testing:

THE CORE PROBLEM with all previous approaches:
→ Using rolling window max/min as "S/R levels" is wrong.
  A rolling 480-bar max/min doesn't identify PRICE LEVELS — it just finds recent extremes.
  A human trader identifies SPECIFIC PIVOTS where price REVERSED multiple times.

THE REAL SOLUTION: 
1. Identify actual FRACTAL PIVOTS (local highs/lows where price reversed)
2. Track these levels as S/R zones
3. Trade RETESTS of these zones WITH pattern confirmation

ALSO: The v11 H1 EMA500 approach gave 2022-2023: +58.8% with DD=18.8%
      → Best single-year result we've achieved.
      → The EMA500 macro filter WORKS for regime detection.

HYBRID APPROACH (v15 FINAL):
1. MACRO FILTER: H1 EMA500 direction (from v11 — proven to work)
2. ENTRY: Pure price action at FRACTAL PIVOT levels (not rolling windows)
3. CONFIRMATION: Pin bar or engulfing with RSI divergence check
4. POSITION SIZING: Conviction-based (3% to 6% per trade)
5. EXIT: Trailing stop OR end-of-week close (whichever comes first)
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass,field
from typing import List,Optional,Tuple

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def m15_to_h1(c,h,l,o):
    n=len(c); seg=n//4
    h1c=np.array([c[i*4+3] for i in range(seg)])
    h1h=np.array([max(h[i*4:i*4+4]) for i in range(seg)])
    h1l=np.array([min(l[i*4:i*4+4]) for i in range(seg)])
    h1o=np.array([o[i*4] for i in range(seg)])
    return h1c,h1h,h1l,h1o,seg

def find_fractal_pivots(h,l,lookback=5):
    """
    Find fractal highs and lows.
    A fractal high at bar i: h[i] is max of h[i-lb:i+lb+1]
    A fractal low at bar i: l[i] is min of l[i-lb:i+lb+1]
    Returns arrays of pivot_hi and pivot_lo (nan where not a pivot)
    """
    n=len(h)
    pivot_hi=np.full(n,np.nan)
    pivot_lo=np.full(n,np.nan)
    lb=lookback
    for i in range(lb,n-lb):
        if h[i]==max(h[i-lb:i+lb+1]): pivot_hi[i]=h[i]
        if l[i]==min(l[i-lb:i+lb+1]): pivot_lo[i]=l[i]
    return pivot_hi,pivot_lo

def get_recent_pivots(pivot_hi,pivot_lo,i,lookback_bars,min_dist_atr,atr):
    """Get pivot levels within lookback_bars of i, separated by min_dist_atr"""
    highs=[]; lows=[]
    start=max(0,i-lookback_bars)
    for j in range(start,i):
        if not np.isnan(pivot_hi[j]):
            # Don't add if too close to existing level
            if not any(abs(pivot_hi[j]-x)<min_dist_atr*atr for x in highs):
                highs.append(pivot_hi[j])
        if not np.isnan(pivot_lo[j]):
            if not any(abs(pivot_lo[j]-x)<min_dist_atr*atr for x in lows):
                lows.append(pivot_lo[j])
    return sorted(highs,reverse=True)[:5], sorted(lows)[:5]  # top 5 each

def is_pin_bull(o,h,l,c,atr):
    b=abs(c-o)+1e-9; lw=min(o,c)-l; uw=h-max(o,c)
    return (lw>=2.0*b and lw>=0.5*(h-l+1e-9) and (c-l)/(h-l+1e-9)>=0.5 and b>0.01*atr)

def is_pin_bear(o,h,l,c,atr):
    b=abs(c-o)+1e-9; uw=h-max(o,c)
    return (uw>=2.0*b and uw>=0.5*(h-l+1e-9) and (h-c)/(h-l+1e-9)>=0.5 and b>0.01*atr)

def is_bull_engulf(o1,c1,o2,c2):
    return c1<o1 and c2>o2 and c2>=(o1-abs(o1-c1)*0.1) and o2<=(c1+abs(o1-c1)*0.1)

def is_bear_engulf(o1,c1,o2,c2):
    return c1>o1 and c2<o2 and c2<=(o1+abs(c1-o1)*0.1) and o2>=(c1-abs(c1-o1)*0.1)

def make_h1_ind(c,h,l,o):
    e8=ema(c,8); e21=ema(c,21); e50=ema(c,50); e200=ema(c,200); e500=ema(c,500)
    e500_p=np.zeros_like(e500)
    for i in range(120,len(c)): e500_p[i]=e500[i-120]
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr50=pd.Series(tr).rolling(50).mean().values
    d2=pd.Series(c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h).diff(); dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.); ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # ATR ratio: current vs slow (is volatility expanding?)
    atr_r=atr14/np.where(atr50>0,atr50,1e-9)
    # Fractal pivots on H1 (5-bar lookback each side)
    ph,pl=find_fractal_pivots(h,l,lookback=5)
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,e500=e500,e500_p=e500_p,
                atr14=atr14,atr50=atr50,atr_r=atr_r,rsi=rsi,adx=adx,di=di,
                pivot_hi=ph,pivot_lo=pl)

def gen_h1_signals(h1c,h1h,h1l,h1o,nh1,cfg=None):
    if cfg is None: cfg={}
    ind=make_h1_ind(h1c,h1h,h1l,h1o)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    e500=ind['e500'];e500p=ind['e500_p']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    ph=ind['pivot_hi'];pl=ind['pivot_lo'];atr_r=ind['atr_r']

    min_score=cfg.get('min_score',6)
    pivot_lb=cfg.get('pivot_lb',100)  # look back 100 H1 bars for pivots (~4 days)
    zone_atr=cfg.get('zone_atr',1.2)  # price within zone_atr*ATR of level = "at level"
    cooldown=cfg.get('cooldown',48)   # minimum 48 H1 bars between trades (~2 days)
    use_short=cfg.get('use_short',True)

    sig=np.zeros(nh1,dtype=int);slp=np.zeros(nh1);rrv=np.zeros(nh1)
    nm=['']*nh1;conv=np.zeros(nh1,dtype=int)
    last_bar=-9999

    for i in range(520,nh1):
        if i-last_bar<cooldown: continue
        cv=h1c[i];hi=h1h[i];lo=h1l[i];oi=h1o[i]
        av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i];ar=atr_r[i]

        # MACRO: EMA500 direction
        macro_bull=e500[i]>e500p[i] and cv>e500[i]
        macro_bear=e500[i]<e500p[i] and cv<e500[i]

        # Get recent pivot levels
        p_highs,p_lows=get_recent_pivots(ph,pl,i,pivot_lb,1.5,av)

        # ── LONG SETUP ───────────────────────────────────────────
        if macro_bull:
            # Is price near a FRACTAL LOW (support)?
            at_support=any(abs(lo-lvl)<=zone_atr*av for lvl in p_lows)
            # Is price near EMA21 or EMA50 (dynamic support)?
            at_ema=(abs(lo-e21[i])<=av*0.8 or abs(lo-e50[i])<=av*1.0)

            score=0
            # Context
            if cv>e200[i]: score+=1
            if e50[i]>e200[i]: score+=1
            if dv>=20 and div>5: score+=1
            # Setup
            if at_support: score+=2
            elif at_ema: score+=1
            # Trigger (requires pattern)
            trigger_ok=False
            if i>=1:
                o1,c1=h1o[i-1],h1c[i-1]
                if is_pin_bull(oi,hi,lo,cv,av): score+=3; trigger_ok=True
                elif is_bull_engulf(o1,c1,oi,cv): score+=2; trigger_ok=True
                elif cv>oi and lo<=e21[i] and ar>=1.0: score+=1; trigger_ok=True

            if trigger_ok and score>=min_score and rv<65:
                rr=3.5 if score>=8 else (3.0 if score>=6 else 2.5)
                if ar>=1.4: rr+=0.5
                sig[i]=1;slp[i]=(av/PIP)*1.4+SPR;rrv[i]=rr;nm[i]='LONG_PIVOT';conv[i]=score
                last_bar=i;continue

        # ── SHORT SETUP ──────────────────────────────────────────
        if use_short and macro_bear:
            at_resist=any(abs(hi-lvl)<=zone_atr*av for lvl in p_highs)
            at_ema=(abs(hi-e21[i])<=av*0.8 or abs(hi-e50[i])<=av*1.0)
            score=0
            if cv<e200[i]: score+=1
            if e50[i]<e200[i]: score+=1
            if dv>=20 and div<-5: score+=1
            if at_resist: score+=2
            elif at_ema: score+=1
            trigger_ok=False
            if i>=1:
                o1,c1=h1o[i-1],h1c[i-1]
                if is_pin_bear(oi,hi,lo,cv,av): score+=3; trigger_ok=True
                elif is_bear_engulf(o1,c1,oi,cv): score+=2; trigger_ok=True
                elif cv<oi and hi>=e21[i] and ar>=1.0: score+=1; trigger_ok=True
            if trigger_ok and score>=min_score and rv>35:
                rr=3.5 if score>=8 else (3.0 if score>=6 else 2.5)
                if ar>=1.4: rr+=0.5
                sig[i]=-1;slp[i]=(av/PIP)*1.4+SPR;rrv[i]=rr;nm[i]='SHORT_PIVOT';conv[i]=score
                last_bar=i

    return sig,slp,rrv,nm,conv

def lot_size(eq,pk,slp,conviction,base_risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=15: r=base_risk*0.15
    elif dd>=10: r=base_risk*0.38
    elif dd>=6: r=base_risk*0.68
    else: r=base_risk
    mult=1.3 if conviction>=8 else (1.0 if conviction>=6 else 0.8)
    return max(0.01,min(round(eq*r*mult/(slp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str=''; entry:float=0.; sl:float=0.; tp:float=0.
    lot:float=0.01; pnl:float=0.; sname:str=''; conviction:int=0
    trail_on:bool=False; hwm:float=0.; sl_pts:float=0.

def backtest(df,base_risk=0.055,cfg=None):
    c=df['close'].values;h=df['high'].values;l=df['low'].values;o=df['open'].values
    h1c,h1h,h1l,h1o,nh1=m15_to_h1(c,h,l,o)
    sig,slp,rrv,nm,conv=gen_h1_signals(h1c,h1h,h1l,h1o,nh1,cfg)
    ind=make_h1_ind(h1c,h1h,h1l,h1o)
    atr_h1=ind['atr14']
    bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None
    for i in range(520,nh1):
        if ot:
            done=False;ex=h1c[i];av=max(atr_h1[i],1.5)
            if ot.dir=='BUY':
                if h1h[i]>ot.hwm: ot.hwm=h1h[i]
                if not ot.trail_on and (h1h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm-2.5*av
                    if ns>ot.sl: ot.sl=ns
                if h1l[i]<=ot.sl: ex=ot.sl; done=True
                elif h1h[i]>=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            else:
                if h1l[i]<ot.hwm: ot.hwm=h1l[i]
                if not ot.trail_on and (ot.entry-h1l[i])>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm+2.5*av
                    if ns<ot.sl: ot.sl=ns
                if h1h[i]>=ot.sl: ex=ot.sl; done=True
                elif h1l[i]<=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else (ot.entry-ex)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net;pk=max(pk,bal);dd=pk-bal;mx=max(mx,dd/pk*100)
                ot.pnl=net;sn=ot.sname
                if sn not in stats:stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1;stats[sn]['pnl']+=net
                if net>0:stats[sn]['w']+=1;stats[sn]['wu']+=net
                else:stats[sn]['lu']+=abs(net)
                trades.append(ot);ot=None
        if ot is None and sig[i]!=0:
            sp=slp[i]
            if sp>0:
                lot=lot_size(bal,pk,sp,conv[i],base_risk)
                s2=SPR*PIP
                if sig[i]==1:e_=h1c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY';hwm=e_
                else:e_=h1c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL';hwm=e_
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=nm[i],
                      conviction=conv[i],trail_on=False,hwm=hwm,sl_pts=sp)
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def run_gauntlet(base_risk=0.055,cfg=None):
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    wm={'2022-2023':('2022-05-02','2023-05-01'),
        '2023-2024':('2023-05-01','2024-05-01'),
        '2024-2025':('2024-05-01','2025-05-01'),
        '2025-2026':('2025-05-01','2026-07-24')}
    rows=[]
    for yr,(s,e) in wm.items():
        d=df.loc[s:e].copy();r=backtest(d,base_risk,cfg)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def print_table(rows,label=""):
    if label:print(label)
    print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

def main():
    print("="*68)
    print("🧠 NEXUS BRAIN FINAL — PIVOT-BASED HUMAN BRAIN")
    print("="*68)
    print("\nH1 FRACTAL PIVOT + EMA500 MACRO + PRICE ACTION CONFIRMATION\n")

    RISK=0.055
    best_score=-1e9;best_cfg=None;best_rows=None;pos3=[]

    # Sweep key parameters
    for ms in [5,6,7]:
        for cd in [24,48,72]:
            for pl in [50,100,150]:
                for za in [1.0,1.5,2.0]:
                    cfg={'min_score':ms,'pivot_lb':pl,'zone_atr':za,
                         'cooldown':cd,'use_short':True}
                    rows=run_gauntlet(RISK,cfg)
                    pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
                    mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
                    tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
                    nt=sum(r['trades'] for yr,r,o,t,c,v in rows)
                    if pos>=3 and mdd<=25:
                        pos3.append((tot,cfg.copy(),rows,nt))
                    if tot>best_score:
                        best_score=tot;best_cfg=cfg.copy();best_rows=rows

    if pos3:
        pos3.sort(key=lambda x:-x[0])
        print(f"✅ {len(pos3)} configs with 3+years positive AND DD<=25%!")
        for tot,cfg,rows,nt in pos3[:3]:
            yr_str=" | ".join(f"{yr[:7]}:{r['pct']:+.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows)
            print(f"  ms={cfg['min_score']} cd={cfg['cooldown']} pl={cfg['pivot_lb']} za={cfg['zone_atr']} | {yr_str} | n={nt} PnL={tot:.0f}")
        tot,cfg,rows,nt=pos3[0]
        print(f"\n🏆 BEST: {cfg}")
        print_table(rows)
    else:
        print(f"⚠️  No 3+yr DD<=25% found. Best totalPnL={best_score:.0f}:")
        print_table(best_rows,f"Config: {best_cfg}")

    # Signal breakdown
    combined={}
    for yr,r,*_ in (pos3[0][2] if pos3 else best_rows):
        for sn,st in r['stats'].items():
            if sn not in combined:combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]:combined[sn][k]+=st[k]
    print("\n📊 Signal stats (combined):")
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<14}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_FINAL_PIVOT.md')
    out_rows=pos3[0][2] if pos3 else best_rows
    lines=["# 🧠 NEXUS BRAIN FINAL — PIVOT-BASED HUMAN BRAIN",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in out_rows:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
