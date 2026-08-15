"""
NEXUS BRAIN v10 — H1 EMA PULL OPTIMIZED + PARAM SWEEP
=======================================================
Keep ONLY:
  H1_EMA21_PULL_BUY  (PF=2.078, WR=41.7% combined)
  H1_EMA21_REBOUND_SELL  (conditional)

Remove all DC breakout signals (all net losers).

Sweep RSI/ADX/RR to maximize consistency.
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
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    n=len(c);seg=n//4
    h1c=np.array([c[i*4+3] for i in range(seg)])
    h1h=np.array([max(h[i*4:i*4+4]) for i in range(seg)])
    h1l=np.array([min(l[i*4:i*4+4]) for i in range(seg)])
    return h1c,h1h,h1l,seg

def make_ind(c,h,l):
    e21=ema(c,21);e50=ema(c,50);e200=ema(c,200);e8=ema(c,8)
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
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,atr14=atr14,rsi=rsi,adx=adx,di=di)

def gen_signals(h1c,h1h,h1l,nh1,cfg=None):
    if cfg is None:cfg={}
    ind=make_ind(h1c,h1h,h1l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    adx_min=cfg.get('adx_min',14)
    rsi_buy=cfg.get('rsi_buy',48)
    rsi_sell=cfg.get('rsi_sell',52)
    rr_base=cfg.get('rr_base',3.0)
    sl_m=cfg.get('sl_mult',1.3)
    sig=np.zeros(nh1,dtype=int);slp=np.zeros(nh1);rrv=np.zeros(nh1);nm=['']*nh1
    for i in range(250,nh1):
        cv=h1c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        bull=cv>e200[i] and e50[i]>e200[i]
        bear=cv<e200[i] and e50[i]<e200[i]
        rr=rr_base+0.5 if dv>=28 else rr_base+0.2 if dv>=20 else rr_base

        # ── BUY: EMA21 Pullback in Bull ──
        if bull and dv>=adx_min and div>0:
            if h1l[i]<=e21[i] and h1c[i]>e21[i] and rv<=rsi_buy:
                sig[i]=1;slp[i]=(av/PIP)*sl_m+SPR;rrv[i]=rr;nm[i]='E21_PULL_BUY';continue
            # EMA8 pullback variant (shallower)
            if h1l[i]<=e8[i] and h1c[i]>e8[i] and rv<=rsi_buy-5 and h1c[i]>e21[i]:
                sig[i]=1;slp[i]=(av/PIP)*sl_m+SPR;rrv[i]=rr+0.5;nm[i]='E8_PULL_BUY';continue

        # ── SELL: EMA21 Rebound in Bear ──
        if bear and dv>=adx_min and div<0:
            if h1h[i]>=e21[i] and h1c[i]<e21[i] and rv>=rsi_sell:
                sig[i]=-1;slp[i]=(av/PIP)*sl_m+SPR;rrv[i]=rr;nm[i]='E21_REBOUND_SELL';continue

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

def backtest(df,risk=0.055,cfg=None):
    h1c,h1h,h1l,nh1=m15_to_h1(df)
    sig,slp,rrv,nm=gen_signals(h1c,h1h,h1l,nh1,cfg)
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
        d=df.loc[s:e].copy();r=backtest(d,RISK,cfg)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def sweep():
    print("="*70)
    print("🔬 SWEEP: H1 EMA PULLBACK — RSI / ADX / RR")
    print("="*70)
    best_score=-1e9;best_cfg=None;best_rows=None
    for rsi_b in [40,45,48,52,55,60]:
        for adx_m in [12,16,20,24]:
            for rr_b in [2.5,3.0,3.5,4.0]:
                cfg={'adx_min':adx_m,'rsi_buy':rsi_b,'rsi_sell':100-rsi_b,
                     'rr_base':rr_b,'sl_mult':1.3}
                rows=run_gauntlet(RISK=0.055,cfg=cfg)
                pos_years=0;score=0;ok_dd=True
                for yr,r,o,t,cap,v in rows:
                    if o is None:continue
                    if r['maxdd']>25:ok_dd=False
                    if r['pnl']>0:pos_years+=1
                    score+=r['pnl']
                if pos_years>=3 and ok_dd:
                    yr_str=" | ".join(f"{yr[:7]}:{r['pct']:.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,o,*_ in rows if o)
                    print(f"  rsi={rsi_b:2d} adx={adx_m:2d} rr={rr_b:.1f} | {yr_str} | score={score:.0f} ***")
                if score>best_score:
                    best_score=score;best_cfg=cfg.copy();best_rows=rows
    if best_rows:
        print(f"\n🏆 BEST: {best_cfg}")
        print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
        print("-"*72)
        for yr,r,o,t,cap,v in best_rows:
            cs=f"{cap:.1f}%" if cap else "N/A"
            tg=f"(T:{t:,.0f}$)" if t else ""
            print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

if __name__=='__main__':
    sweep()
