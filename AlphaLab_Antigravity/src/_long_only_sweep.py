"""Long-only pivot sweep"""
import os,sys,pandas as pd,numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')
from nexus_brain_final import run_gauntlet,backtest

ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

print('=== LONG-ONLY PIVOT SWEEP ===')
best_score=-1e9;best_cfg=None;best_rows=None;pos3=[]
for ms in [4,5,6]:
    for cd in [24,48,72]:
        for pl in [50,100,150,200]:
            for za in [0.8,1.0,1.5]:
                cfg={'min_score':ms,'pivot_lb':pl,'zone_atr':za,'cooldown':cd,'use_short':False}
                rows=run_gauntlet(0.055,cfg)
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
    print(f'Found {len(pos3)} winning configs (3+yr positive + DD<=25%):')
    for tot,cfg,rows,nt in pos3[:5]:
        yr_str=' | '.join(f"{yr[:7]}:{r['pct']:+.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows)
        print(f"  ms={cfg['min_score']} cd={cfg['cooldown']} pl={cfg['pivot_lb']} za={cfg['zone_atr']} | {yr_str} | n={nt} PnL={tot:.0f}")
    tot,cfg,rows,nt=pos3[0]
    print(f'\nBEST: {cfg}')
else:
    print(f'No 3+yr config. Best({best_score:.0f}): {best_cfg}')
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
