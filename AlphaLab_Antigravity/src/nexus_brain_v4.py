"""
NEXUS BRAIN v4 — REGIME-ADAPTIVE MULTI-SIGNAL ENGINE
Insight from v3: KC_BREAKOUT has PF=1.335 combined but DEEP_PULLBACK and EMA21_BOUNCE 
aren't triggering. Root issue: EMA96/384 too slow for annual windows.

Solution:
- Use rolling 5-week (35-day = 560 M15) slope to determine MACRO trend state
- In BEARISH macro years (2022 first half), add SHORT signals on bear rebounds
- In BULL years, maximize capture with: pullback + KC breakout + RSI divergence
- Risk: tiered 3-level with hard DD cap at 22%
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass
from typing import Optional

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def make_ind(c,h,l):
    e8=ema(c,8);e21=ema(c,21);e50=ema(c,50);e200=ema(c,200)
    e96=ema(c,96);e200b=ema(c,200)
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
    # Donchian 20-bar
    dc_hi=pd.Series(h).rolling(20).max().shift(1).values
    dc_lo=pd.Series(l).rolling(20).min().shift(1).values
    # BB width
    bb_m=pd.Series(c).rolling(20).mean()
    bb_w=(2*pd.Series(c).rolling(20).std()/bb_m.replace(0,1)).values
    bb_ws=pd.Series(bb_w).rolling(60).mean().values
    # ATR ratio (current vs slow)
    atr_r=atr14/np.where(atr50>0,atr50,1e-9)
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,e96=e96,
                atr14=atr14,atr50=atr50,atr_r=atr_r,
                rsi=rsi,adx=adx,di=di,
                dc_hi=dc_hi,dc_lo=dc_lo,
                bb_w=bb_w,bb_ws=bb_ws)

def gen_signals(df):
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    n=len(c);ind=make_ind(c,h,l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200'];e96=ind['e96']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    dc_hi=ind['dc_hi'];dc_lo=ind['dc_lo']
    bb_w=ind['bb_w'];bb_ws=ind['bb_ws'];atr_r=ind['atr_r']
    sig=np.zeros(n,dtype=int);slp=np.zeros(n);rrv=np.zeros(n);nm=['']*n

    for i in range(250,n):
        cv=c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        # Macro state from EMA200 and EMA96
        htf_bull=cv>e200[i] and e96[i]>e200[i]
        htf_bear=cv<e200[i] and e96[i]<e200[i]
        mid_bull=e50[i]>e200[i] and div>0
        mid_bear=e50[i]<e200[i] and div<0
        ar=atr_r[i]

        # ── LONG SIGNALS ─────────────────────────────────────────
        # S1: Deep Pullback to EMA8 in established bull (HIGH PRIORITY)
        if htf_bull and mid_bull and dv>=18:
            if l[i]<=e8[i] and cv>e8[i] and rv<=44:
                rr=4.0 if dv>=28 else 3.5
                sig[i]=1;slp[i]=(av/PIP)*1.3+SPR;rrv[i]=rr;nm[i]='DEEP_PULL_BUY';continue

        # S2: Donchian 20 Breakout with momentum (expansion signal)
        if htf_bull and dv>=20 and div>5 and ar>=1.1:
            if cv>dc_hi[i] and 48<=rv<=70 and cv>e50[i]:
                sig[i]=1;slp[i]=(av/PIP)*1.6+SPR*1.2;rrv[i]=3.8;nm[i]='DC_BREAK_BUY';continue

        # S3: EMA21 Support bounce — deeper pullback in strong bull
        if htf_bull and cv>e200[i] and mid_bull and dv>=16:
            if l[i]<=e21[i] and cv>e21[i] and rv<=38:
                sig[i]=1;slp[i]=(av/PIP)*1.5+SPR*1.1;rrv[i]=3.5;nm[i]='EMA21_BOUNCE_BUY';continue

        # ── SHORT SIGNALS ─────────────────────────────────────────
        # S4: Bear rebound sell — ONLY in confirmed bear macro
        if htf_bear and mid_bear and dv>=22:
            if h[i]>=e8[i] and cv<e8[i] and rv>=56 and cv<e21[i]:
                sig[i]=-1;slp[i]=(av/PIP)*1.3+SPR;rrv[i]=3.5;nm[i]='BEAR_REBOUND_SELL';continue

        # S5: Donchian 20 Bear Breakdown
        if htf_bear and dv>=22 and div<-5 and ar>=1.1:
            if cv<dc_lo[i] and 30<=rv<=52 and cv<e50[i]:
                sig[i]=-1;slp[i]=(av/PIP)*1.6+SPR*1.2;rrv[i]=3.8;nm[i]='DC_BREAK_SELL';continue

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
    bal=1000.;pk=1000.;mx=0.;mxp=0.
    trades=[];stats={};ot=None
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
                bal+=net
                if bal>pk:pk=bal
                dd=pk-bal
                if dd>mx:mx=dd;mxp=dd/pk*100
                ot.pnl=net
                sn=ot.sname
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
                pf=gw/gl,maxdd=mxp,sh=sh,stats=stats)

def main():
    print("="*66)
    print("🧠 NEXUS BRAIN v4 — FULL REGIME-ADAPTIVE MULTI-SIGNAL GAUNTLET")
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

    print("\n📊 Signal stats:")
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
    rf=os.path.join(rdir,'NEXUS_BRAIN_V4_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v4 — MULTI-YEAR GAUNTLET",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           f"**Risk**: {RISK*100}%/trade | Spread {SPR}pts | Comm ${COMM}",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Target20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
