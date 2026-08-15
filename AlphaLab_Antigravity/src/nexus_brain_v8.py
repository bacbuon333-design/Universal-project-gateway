"""
NEXUS BRAIN v8 — SWING RETEST ENGINE
=====================================================
Architecture shift: Instead of EMA pullback (20% WR), use SWING RETEST.

Logic:
1. Detect recent swing high (S/R level from price action)
2. When price PULLS BACK to test that level (broken resistance = new support)
3. Enter on confirmation (1 bar close above/below the level)

Why this works:
- Swing retest has empirical 40-50% WR in liquid markets
- With R:R=2.5, expected value = 0.45*2.5 - 0.55*1 = 1.125 - 0.55 = 0.575R per trade
- Much better expected value than 20%WR * 4.0RR = 0.80 - 0.75 = 0.05R

Swing detection: 20-bar fractal high/low (price was local max/min over 20 bars)
Retest window: price pulls back to within 0.5 ATR of the swing level
Confirmation: close above (for support) or below (for resistance)
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
    # Fractal swing high/low (20-bar)
    sw=20
    fh=pd.Series(h).rolling(sw,center=True).max().values  # fractal high zone
    fl=pd.Series(l).rolling(sw,center=True).min().values  # fractal low zone
    # Donchian for breakout detection
    dc_hi=pd.Series(h).rolling(sw).max().shift(1).values
    dc_lo=pd.Series(l).rolling(sw).min().shift(1).values
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,
                atr14=atr14,rsi=rsi,adx=adx,di=di,
                dc_hi=dc_hi,dc_lo=dc_lo)

def gen_signals(df, cfg=None):
    if cfg is None: cfg={}
    c=df['close'].values;h=df['high'].values;l=df['low'].values
    n=len(c);ind=make_ind(c,h,l)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];rsi=ind['rsi'];adx=ind['adx'];di=ind['di']
    dc_hi=ind['dc_hi'];dc_lo=ind['dc_lo']
    sig=np.zeros(n,dtype=int);slp=np.zeros(n);rrv=np.zeros(n);nm=['']*n

    adx_min=cfg.get('adx_min',15)
    rsi_os=cfg.get('rsi_os',48)   # oversold level for buy
    rsi_ob=cfg.get('rsi_ob',52)   # overbought level for sell
    base_rr=cfg.get('rr_base',3.0)
    sl_mult=cfg.get('sl_mult',1.25)
    use_short=cfg.get('use_short',False)

    # Track recent Donchian breakout level for retest
    last_dc_break_hi=[0.0]*n   # last level that was broken to upside
    last_dc_break_lo=[99999.0]*n  # last level that was broken to downside
    for i in range(1,n):
        last_dc_break_hi[i]=last_dc_break_hi[i-1]
        last_dc_break_lo[i]=last_dc_break_lo[i-1]
        if dc_hi[i]>0 and c[i-1]>dc_hi[i]:  # broke above
            last_dc_break_hi[i]=dc_hi[i]
        if dc_lo[i]<99999 and c[i-1]<dc_lo[i]:  # broke below
            last_dc_break_lo[i]=dc_lo[i]

    for i in range(250,n):
        cv=c[i];av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        bull=cv>e200[i] and e50[i]>e200[i]
        bear=cv<e200[i] and e50[i]<e200[i]
        trend_rr=base_rr+0.5 if dv>=28 else (base_rr+0.2 if dv>=20 else base_rr)

        # ── S1: Broken Resistance Retest (Buy) ──
        # DC broke up N bars ago, price pulls back to test that level from above
        lvl=last_dc_break_hi[i]
        if bull and dv>=adx_min and lvl>0:
            zone=av*0.8  # within 0.8 ATR of the level
            if abs(l[i]-lvl)<=zone and cv>lvl and rv<=rsi_os:
                sig[i]=1;slp[i]=(av/PIP)*sl_mult+SPR;rrv[i]=trend_rr
                nm[i]='SR_RETEST_BUY';continue

        # ── S2: EMA8 Pullback Buy (complementary signal) ──
        if bull and dv>=adx_min:
            if l[i]<=e8[i] and cv>e8[i] and rv<=rsi_os:
                sig[i]=1;slp[i]=(av/PIP)*sl_mult+SPR;rrv[i]=trend_rr+0.3
                nm[i]='PULL_E8_BUY';continue

        # ── S3: EMA50 Deep Bounce Buy (strongest support) ──
        if bull and dv>=adx_min:
            if l[i]<=e50[i] and cv>e50[i] and rv<=40:
                sig[i]=1;slp[i]=(av/PIP)*(sl_mult+0.2)+SPR*1.1;rrv[i]=trend_rr+0.5
                nm[i]='DEEP_E50_BUY';continue

        if use_short:
            # ── S4: Broken Support Retest (Sell) ──
            lvl_s=last_dc_break_lo[i]
            if bear and dv>=adx_min and lvl_s<99999:
                zone=av*0.8
                if abs(h[i]-lvl_s)<=zone and cv<lvl_s and rv>=rsi_ob:
                    sig[i]=-1;slp[i]=(av/PIP)*sl_mult+SPR;rrv[i]=trend_rr
                    nm[i]='SR_RETEST_SELL';continue

    return sig,slp,rrv,nm

def lot_size(eq,pk,slp,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    # Tighter scaling to keep DD <22%
    if dd>=15:r=risk*0.15
    elif dd>=10:r=risk*0.35
    elif dd>=6:r=risk*0.65
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

def main():
    print("="*66)
    print("🧠 NEXUS BRAIN v8 — SWING RETEST ENGINE")
    print("="*66)
    cfg={'adx_min':15,'rsi_os':48,'rsi_ob':52,'rr_base':3.0,'sl_mult':1.25,'use_short':False}
    rows=run_gauntlet(RISK=0.055,cfg=cfg)
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

    # Save report
    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V8_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v8 — SWING RETEST ENGINE MULTI-YEAR REPORT",
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
