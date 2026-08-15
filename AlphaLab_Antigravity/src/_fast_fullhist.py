"""
FAST FULL-HISTORY GAUNTLET v2
==============================
Optimization: Pre-compute H1 signals on full dataset ONCE per config,
then evaluate window performance without re-computing indicators.

Key fix: Use full dataset from start → EMA500 properly warmed up
before reaching any test window.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}
WINDOWS={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01'),
         '2025-2026':('2025-05-01','2026-07-24')}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def make_atr(h,l,c):
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    return pd.Series(np.append([tr[0]],tr)).rolling(14).mean().values

def find_pivots(h,l,lb=5):
    n=len(h);ph=np.full(n,np.nan);pl=np.full(n,np.nan)
    for i in range(lb,n-lb):
        if h[i]==max(h[i-lb:i+lb+1]):ph[i]=h[i]
        if l[i]==min(l[i-lb:i+lb+1]):pl[i]=l[i]
    return ph,pl

def is_pin_bull(o,h,l,c,atr):
    b=abs(c-o)+1e-9;lw=min(o,c)-l
    return lw>=2.0*b and lw>=0.5*(h-l+1e-9) and (c-l)/(h-l+1e-9)>=0.5 and b>0.01*atr

def is_pin_bear(o,h,l,c,atr):
    b=abs(c-o)+1e-9;uw=h-max(o,c)
    return uw>=2.0*b and uw>=0.5*(h-l+1e-9) and (h-c)/(h-l+1e-9)>=0.5 and b>0.01*atr

def is_bull_engulf(o1,c1,o2,c2):
    return c1<o1 and c2>o2 and c2>=(o1-abs(o1-c1)*0.1) and o2<=(c1+abs(o1-c1)*0.1)

def is_bear_engulf(o1,c1,o2,c2):
    return c1>o1 and c2<o2 and c2<=(o1+abs(c1-o1)*0.1) and o2>=(c1-abs(c1-o1)*0.1)

def build_full_signals(h1c,h1h,h1l,h1o,nh1,cfg):
    """Build signals on FULL H1 dataset — called once per config"""
    ms=cfg.get('min_score',5); pl=cfg.get('pivot_lb',100)
    za=cfg.get('zone_atr',1.0); cd=cfg.get('cooldown',48)
    use_short=cfg.get('use_short',False)

    # Indicators on full H1
    e8=ema(h1c,8);e21=ema(h1c,21);e50=ema(h1c,50);e200=ema(h1c,200);e500=ema(h1c,500)
    e500p=np.zeros(nh1)
    for i in range(120,nh1):e500p[i]=e500[i-120]
    atr14=make_atr(h1h,h1l,h1c)
    tr=np.maximum(h1h[1:]-h1l[1:],np.maximum(np.abs(h1h[1:]-h1c[:-1]),np.abs(h1l[1:]-h1c[:-1])))
    tr=np.append([tr[0]],tr)
    atr50=pd.Series(tr).rolling(50).mean().values
    atr_r=atr14/np.where(atr50>0,atr50,1e-9)
    d2=pd.Series(h1c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h1h).diff();dn=-pd.Series(h1l).diff()
    pdm=up.where((up>dn)&(up>0),0.);ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # Fractal pivots
    ph,plo=find_pivots(h1h,h1l,lb=5)

    sig=np.zeros(nh1,dtype=int);slp=np.zeros(nh1);rrv=np.zeros(nh1)
    nm=['']*nh1;conv=np.zeros(nh1,dtype=int)
    last_bar=-9999

    for i in range(520,nh1):
        if i-last_bar<cd:continue
        cv=h1c[i];hi=h1h[i];lo=h1l[i];oi=h1o[i]
        av=max(atr14[i],1.5);rv=rsi[i];dv=adx[i];div=di[i];ar=atr_r[i]
        macro_bull=e500[i]>e500p[i] and cv>e500[i]
        macro_bear=e500[i]<e500p[i] and cv<e500[i]

        # Get recent pivot lows (support) and highs (resistance)
        start=max(0,i-pl)
        p_lows=[];p_highs=[]
        for j in range(start,i):
            if not np.isnan(plo[j]) and not any(abs(plo[j]-x)<1.5*av for x in p_lows):
                p_lows.append(plo[j])
            if not np.isnan(ph[j]) and not any(abs(ph[j]-x)<1.5*av for x in p_highs):
                p_highs.append(ph[j])

        # LONG
        if macro_bull:
            at_sup=any(abs(lo-lvl)<=za*av for lvl in p_lows)
            at_ema=abs(lo-e21[i])<=av*0.8 or abs(lo-e50[i])<=av*1.0
            sc=0
            if cv>e200[i]:sc+=1
            if e50[i]>e200[i]:sc+=1
            if dv>=20 and div>5:sc+=1
            if at_sup:sc+=2
            elif at_ema:sc+=1
            trig=False
            if i>=1:
                o1,c1=h1o[i-1],h1c[i-1]
                if is_pin_bull(oi,hi,lo,cv,av):sc+=3;trig=True
                elif is_bull_engulf(o1,c1,oi,cv):sc+=2;trig=True
                elif cv>oi and lo<=e21[i] and ar>=1.0:sc+=1;trig=True
            if trig and sc>=ms and rv<65:
                rr=3.5 if sc>=8 else(3.0 if sc>=6 else 2.5)
                if ar>=1.4:rr+=0.5
                sig[i]=1;slp[i]=(av/PIP)*1.4+SPR;rrv[i]=rr;nm[i]='LONG';conv[i]=sc
                last_bar=i;continue

        # SHORT
        if use_short and macro_bear:
            at_res=any(abs(hi-lvl)<=za*av for lvl in p_highs)
            at_ema=abs(hi-e21[i])<=av*0.8 or abs(hi-e50[i])<=av*1.0
            sc=0
            if cv<e200[i]:sc+=1
            if e50[i]<e200[i]:sc+=1
            if dv>=20 and div<-5:sc+=1
            if at_res:sc+=2
            elif at_ema:sc+=1
            trig=False
            if i>=1:
                o1,c1=h1o[i-1],h1c[i-1]
                if is_pin_bear(oi,hi,lo,cv,av):sc+=3;trig=True
                elif is_bear_engulf(o1,c1,oi,cv):sc+=2;trig=True
                elif cv<oi and hi>=e21[i] and ar>=1.0:sc+=1;trig=True
            if trig and sc>=ms and rv>35:
                rr=3.5 if sc>=8 else(3.0 if sc>=6 else 2.5)
                if ar>=1.4:rr+=0.5
                sig[i]=-1;slp[i]=(av/PIP)*1.4+SPR;rrv[i]=rr;nm[i]='SHORT';conv[i]=sc
                last_bar=i

    return sig,slp,rrv,nm,conv,atr14

def lot_size(eq,pk,sp,cv,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=15:r=risk*0.15
    elif dd>=10:r=risk*0.38
    elif dd>=6:r=risk*0.68
    else:r=risk
    mult=1.3 if cv>=8 else(1.0 if cv>=6 else 0.8)
    return max(0.01,min(round(eq*r*mult/(sp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str='';entry:float=0.;sl:float=0.;tp:float=0.
    lot:float=0.01;pnl:float=0.;sname:str='';conv:int=0
    trail_on:bool=False;hwm:float=0.;sl_pts:float=0.

def eval_window(h1c,h1h,h1l,atr14,sig,slp,rrv,nm,conv,start_i,end_i,risk=0.055):
    bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None
    for i in range(start_i,end_i):
        if ot:
            done=False;ex=h1c[i];av=max(atr14[i],1.5)
            if ot.dir=='BUY':
                if h1h[i]>ot.hwm:ot.hwm=h1h[i]
                if not ot.trail_on and(h1h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm-2.5*av
                    if ns>ot.sl:ot.sl=ns
                if h1l[i]<=ot.sl:ex=ot.sl;done=True
                elif h1h[i]>=ot.tp and not ot.trail_on:ex=ot.tp;done=True
            else:
                if h1l[i]<ot.hwm:ot.hwm=h1l[i]
                if not ot.trail_on and(ot.entry-h1l[i])>=1.5*ot.sl_pts*PIP:ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm+2.5*av
                    if ns<ot.sl:ot.sl=ns
                if h1h[i]>=ot.sl:ex=ot.sl;done=True
                elif h1l[i]<=ot.tp and not ot.trail_on:ex=ot.tp;done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else(ot.entry-ex)/PIP
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
                lt=lot_size(bal,pk,sp,conv[i],risk)
                s2=SPR*PIP
                if sig[i]==1:e_=h1c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY';hwm=e_
                else:e_=h1c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL';hwm=e_
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lt,sname=nm[i],
                      conv=conv[i],trail_on=False,hwm=hwm,sl_pts=sp)
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def load_h1():
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    c=df['close'].values;h=df['high'].values;l=df['low'].values;o=df['open'].values
    n=len(c);seg=n//4
    h1c=np.array([c[i*4+3] for i in range(seg)])
    h1h=np.array([max(h[i*4:i*4+4]) for i in range(seg)])
    h1l=np.array([min(l[i*4:i*4+4]) for i in range(seg)])
    h1o=np.array([o[i*4] for i in range(seg)])
    h1_dt=[df.index[i*4+3] for i in range(seg)]
    return h1c,h1h,h1l,h1o,seg,h1_dt

if __name__=='__main__':
    print('='*68)
    print('🧠 FAST FULL-HISTORY GAUNTLET (EMA500 properly warmed up)')
    print('='*68)
    h1c,h1h,h1l,h1o,nh1,h1_dt=load_h1()
    # Pre-compute window index ranges
    win_ranges={}
    for yr,(ws,we) in WINDOWS.items():
        wsd=pd.Timestamp(ws);wed=pd.Timestamp(we)
        si=next((i for i,t in enumerate(h1_dt) if t>=wsd),None)
        ei=next((i for i,t in enumerate(h1_dt) if t>=wed),nh1)
        if si:win_ranges[yr]=(si,ei)

    RISK=0.055
    best_score=-1e9;best_cfg=None;best_rows=None;pos3=[]

    configs=[]
    for ms in [4,5,6]:
        for cd in [24,48,72]:
            for pl_v in [50,100,150]:
                for za in [0.8,1.0,1.5]:
                    configs.append({'min_score':ms,'cooldown':cd,'pivot_lb':pl_v,
                                    'zone_atr':za,'use_short':False})
    print(f"Testing {len(configs)} configs on full history...")

    for cfg in configs:
        sig,slp,rrv,nm,conv,atr14=build_full_signals(h1c,h1h,h1l,h1o,nh1,cfg)
        rows=[]
        for yr,(si,ei) in win_ranges.items():
            r=eval_window(h1c,h1h,h1l,atr14,sig,slp,rrv,nm,conv,si,ei,RISK)
            oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
            cap=r['pnl']/oracle*100 if oracle else None
            ok=r['maxdd']<=25 and(not oracle or r['pnl']>0)
            rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
        pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
        mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
        tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
        nt=sum(r['trades'] for yr,r,o,t,c,v in rows)
        if pos>=3 and mdd<=25:pos3.append((tot,cfg.copy(),rows,nt))
        if tot>best_score:best_score=tot;best_cfg=cfg.copy();best_rows=rows

    pos3.sort(key=lambda x:-x[0])
    if pos3:
        print(f'\n✅ {len(pos3)} configs: 3+ positive years AND DD<=25%!')
        for tot,cfg,rows,nt in pos3[:5]:
            yr_str=' | '.join(f"{yr[:7]}:{r['pct']:+.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows)
            print(f"  ms={cfg['min_score']} cd={cfg['cooldown']} pl={cfg['pivot_lb']} za={cfg['zone_atr']} | {yr_str} | n={nt} PnL={tot:.0f}")
        tot,cfg,rows,nt=pos3[0]
        print(f'\n🏆 BEST ({tot:.0f}): {cfg}')
    else:
        print(f'\n⚠️  No 3+yr DD<=25%. Best({best_score:.0f}): {best_cfg}')
        rows=best_rows

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
    print('-'*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else 'N/A'
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined:combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]:combined[sn][k]+=st[k]
    print('\n📊 Combined signal stats:')
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<10}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    # Save report
    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_FULLHISTORY_FINAL.md')
    out=pos3[0][2] if pos3 else best_rows
    cfg_out=pos3[0][1] if pos3 else best_cfg
    lines=["# 🧠 NEXUS BRAIN — FULL-HISTORY PIVOT ENGINE FINAL REPORT",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           f"**Config**: {cfg_out}",
           f"**Method**: Full dataset EMA500 (properly warmed up)",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in out:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")
