"""
NEXUS BRAIN v7 — FINAL CORRECTED ENGINE
Bug fix: remove c>e21 constraint from PULL_E8_BUY (RSI<=45 already implies price is lower)
Logic: when price dips to EMA8 with RSI<=45 in bull trend, it's a valid pullback regardless of e21
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def make_ind(c,h,l):
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
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,
                atr14=atr14,rsi=rsi,adx=adx,di=di)

def gen_signals(df,cfg=None):
    if cfg is None: cfg={}
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    n=len(c);ind=make_ind(c,h,l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    sig=np.zeros(n,dtype=int);slp=np.zeros(n);rrv=np.zeros(n);nm=['']*n

    adx_min   = cfg.get('adx_min',16)
    rsi_buy   = cfg.get('rsi_buy',45)
    rsi_sell  = cfg.get('rsi_sell',55)
    rr_base   = cfg.get('rr_base',3.5)
    sl_mult   = cfg.get('sl_mult',1.35)

    for i in range(250,n):
        cv=c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        bull=cv>e200[i] and e50[i]>e200[i]
        bear=cv<e200[i] and e50[i]<e200[i]
        trend_rr=rr_base+0.5 if dv>=28 else (rr_base+0.2 if dv>=22 else rr_base)

        # ── S1: EMA8 Pullback Buy (FIXED: removed c>e21 constraint) ──
        if bull and dv>=adx_min:
            if l[i]<=e8[i] and cv>e8[i] and rv<=rsi_buy:
                sig[i]=1;slp[i]=(av/PIP)*sl_mult+SPR;rrv[i]=trend_rr
                nm[i]='PULL_E8_BUY';continue

        # ── S2: EMA21 Bounce Buy (deeper correction) ──
        if bull and dv>=adx_min+2:
            if l[i]<=e21[i] and cv>e21[i] and rv<=rsi_buy-8:
                sig[i]=1;slp[i]=(av/PIP)*(sl_mult+0.15)+SPR*1.1;rrv[i]=trend_rr+0.2
                nm[i]='BOUNCE_E21_BUY';continue

        # ── S3: EMA8 Rebound Sell (bear macro mirror) ──
        if bear and dv>=adx_min:
            if h[i]>=e8[i] and cv<e8[i] and rv>=rsi_sell:
                sig[i]=-1;slp[i]=(av/PIP)*sl_mult+SPR;rrv[i]=trend_rr
                nm[i]='REBOUND_E8_SELL';continue

        # ── S4: EMA21 Rebound Sell ──
        if bear and dv>=adx_min+2:
            if h[i]>=e21[i] and cv<e21[i] and rv>=rsi_sell+7:
                sig[i]=-1;slp[i]=(av/PIP)*(sl_mult+0.15)+SPR*1.1;rrv[i]=trend_rr+0.2
                nm[i]='REBOUND_E21_SELL';continue

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

def backtest(df,risk=0.055,cfg=None):
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    sig,slp,rrv,nm=gen_signals(df,cfg)
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

def run_gauntlet(RISK=0.055, cfg=None):
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    wins_map={'2022-2023':('2022-05-02','2023-05-01'),
              '2023-2024':('2023-05-01','2024-05-01'),
              '2024-2025':('2024-05-01','2025-05-01'),
              '2025-2026':('2025-05-01','2026-07-24')}
    rows=[]
    for yr,(s,e) in wins_map.items():
        d=df.loc[s:e].copy();r=backtest(d,RISK,cfg)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>=tgt*0.60)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def main():
    print("="*66)
    print("🧠 NEXUS BRAIN v7 — CORRECTED PULLBACK ENGINE")
    print("="*66)
    rows=run_gauntlet()
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
        print(f"  {sn:<26}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V7_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v7 — PRODUCTION ENGINE MULTI-YEAR REPORT",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
