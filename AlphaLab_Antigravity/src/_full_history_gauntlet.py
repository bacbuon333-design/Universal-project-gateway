"""
FULL-HISTORY GAUNTLET — Run on complete dataset (not per-year slices)
so EMA500 is properly warmed up for ALL test windows.

This is crucial: when we slice 2022-2023 as a separate DataFrame,
EMA500 starts from scratch. In full dataset, EMA500 in May 2022
already has 2+ years of history → proper macro filter.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass
from nexus_brain_final import (make_h1_ind,gen_h1_signals,lot_size,
                                m15_to_h1,is_pin_bull,is_pin_bear,
                                is_bull_engulf,is_bear_engulf)

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

WINDOWS={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01'),
         '2025-2026':('2025-05-01','2026-07-24')}

def run_full_history_gauntlet(cfg=None,base_risk=0.055):
    """
    Load FULL dataset, compute signals once (so EMA500 uses full history),
    then evaluate performance per window by tracking equity within each window.
    """
    if cfg is None:cfg={}
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)

    c=df['close'].values;h=df['high'].values;l=df['low'].values;o=df['open'].values
    n=len(c)
    # Build H1 from full dataset
    h1c,h1h,h1l,h1o,nh1=m15_to_h1(c,h,l,o)
    # Build timestamps for H1 (align with M15 index)
    dt_idx=df.index
    h1_dt=[dt_idx[i*4+3] for i in range(nh1)]

    # Compute signals on FULL history (EMA500 properly warmed)
    sig,slp,rrv,nm,conv=gen_h1_signals(h1c,h1h,h1l,h1o,nh1,cfg)
    ind=make_h1_ind(h1c,h1h,h1l,h1o)
    atr_h1=ind['atr14']

    # Now run separate equity curves per window
    rows=[]
    for yr,(ws,we) in WINDOWS.items():
        ws_dt=pd.Timestamp(ws);we_dt=pd.Timestamp(we)
        # Find H1 bar indices for this window
        start_i=next((i for i,t in enumerate(h1_dt) if t>=ws_dt),None)
        end_i=next((i for i,t in enumerate(h1_dt) if t>=we_dt),len(h1_dt))
        if start_i is None:continue

        bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None

        @dataclass
        class Tr:
            dir:str='';entry:float=0.;sl:float=0.;tp:float=0.
            lot:float=0.01;pnl:float=0.;sname:str='';conviction:int=0
            trail_on:bool=False;hwm:float=0.;sl_pts:float=0.

        for i in range(start_i,end_i):
            if ot:
                done=False;ex=h1c[i];av=max(atr_h1[i],1.5)
                if ot.dir=='BUY':
                    if h1h[i]>ot.hwm:ot.hwm=h1h[i]
                    if not ot.trail_on and (h1h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:
                        ot.trail_on=True
                    if ot.trail_on:
                        ns=ot.hwm-2.5*av
                        if ns>ot.sl:ot.sl=ns
                    if h1l[i]<=ot.sl:ex=ot.sl;done=True
                    elif h1h[i]>=ot.tp and not ot.trail_on:ex=ot.tp;done=True
                else:
                    if h1l[i]<ot.hwm:ot.hwm=h1l[i]
                    if not ot.trail_on and (ot.entry-h1l[i])>=1.5*ot.sl_pts*PIP:
                        ot.trail_on=True
                    if ot.trail_on:
                        ns=ot.hwm+2.5*av
                        if ns<ot.sl:ot.sl=ns
                    if h1h[i]>=ot.sl:ex=ot.sl;done=True
                    elif h1l[i]<=ot.tp and not ot.trail_on:ex=ot.tp;done=True
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
            if ot is None and sig[i]!=0 and start_i<=i<end_i:
                sp=slp[i]
                if sp>0:
                    lot_v=lot_size(bal,pk,sp,conv[i],base_risk)
                    s2=SPR*PIP
                    if sig[i]==1:e_=h1c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY';hwm=e_
                    else:e_=h1c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL';hwm=e_
                    ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot_v,sname=nm[i],
                          conviction=conv[i],trail_on=False,hwm=hwm,sl_pts=sp)
        pnls=[t.pnl for t in trades]
        wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
        gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
        r=dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
               trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
               pf=gw/gl,maxdd=mx,stats=stats)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

if __name__=='__main__':
    print('='*68)
    print('🧠 FULL-HISTORY GAUNTLET (EMA500 properly warmed)')
    print('='*68)
    RISK=0.055
    best_score=-1e9;best_cfg=None;best_rows=None;pos3=[]
    for ms in [4,5,6]:
        for cd in [24,48,72]:
            for pl in [50,100,150,200]:
                for za in [0.8,1.0,1.5]:
                    cfg={'min_score':ms,'pivot_lb':pl,'zone_atr':za,'cooldown':cd,'use_short':False}
                    rows=run_full_history_gauntlet(cfg,RISK)
                    pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
                    mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
                    tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
                    nt=sum(r['trades'] for yr,r,o,t,c,v in rows)
                    if pos>=3 and mdd<=25:
                        pos3.append((tot,cfg.copy(),rows,nt))
                    if tot>best_score:
                        best_score=tot;best_cfg=cfg.copy();best_rows=rows

    pos3.sort(key=lambda x:-x[0])
    if pos3:
        print(f'\n✅ {len(pos3)} configs: 3+positive years AND DD<=25%!')
        for tot,cfg,rows,nt in pos3[:5]:
            yr_str=' | '.join(f"{yr[:7]}:{r['pct']:+.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows)
            print(f"  ms={cfg['min_score']} cd={cfg['cooldown']} pl={cfg['pivot_lb']} za={cfg['zone_atr']} | {yr_str} | n={nt}")
        tot,cfg,rows,nt=pos3[0]
        print(f'\n🏆 BEST config (score={tot:.0f}): {cfg}')
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
    print('\nSignal stats:')
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<16}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")
