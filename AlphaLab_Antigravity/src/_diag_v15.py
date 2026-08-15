"""
Targeted diagnostic and fix for 2023-2024
Test: Higher ADX threshold blocks choppy May-Sep 2023
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'src')
from nexus_brain_v15 import run_gauntlet,print_table

RISK=0.055
best_cfg_v15={'min_score':4,'cooldown':72,'pivot_lb':100,'zone_atr':0.8,
              'para_th':1.4,'adx_para':28,'adx_norm':16}

print("=== ADX NORM THRESHOLD TEST ===")
print("Testing adx_norm = 14, 16, 18, 20, 22, 24, 26, 28")
print(f"{'adx':>5} {'2022':>8} {'2023':>8} {'2024':>8} {'2025':>8} {'Total':>8} {'MaxDD':>7} {'Pos':>5}")
print('-'*68)

best_score=-1e9;best_adx=16;best_rows=None
for adx_n in [14,16,18,20,22,24,26,28]:
    cfg=dict(best_cfg_v15,adx_norm=adx_n)
    rows=run_gauntlet(cfg,RISK)
    pnls=[r['pct'] for yr,r,o,t,c,v in rows]
    mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
    tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
    pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
    yr_pcts=" ".join(f"{r['pct']:+.1f}%" for yr,r,*_ in rows)
    flag="✅" if pos>=3 and mdd<=25 else ""
    pnl_cols=list(r['pct'] for yr,r,o,t,c,v in rows)
    print(f"{adx_n:>5} {pnl_cols[0]:>7.1f}%{pnl_cols[1]:>7.1f}%{pnl_cols[2]:>7.1f}%{pnl_cols[3]:>7.1f}%{tot:>7.0f} {mdd:>6.1f}% {pos}/3 {flag}")
    if tot>best_score:
        best_score=tot;best_adx=adx_n;best_rows=rows;best_rows_cfg=cfg

print(f"\nBest adx_norm={best_adx}")
print_table(best_rows)

# Also test: adding min_score=5 (filter lower quality)
print("\n=== MIN_SCORE TEST at best ADX ===")
for ms in [4,5,6,7]:
    cfg=dict(best_cfg_v15,adx_norm=best_adx,min_score=ms)
    rows=run_gauntlet(cfg,RISK)
    mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
    tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
    pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
    pnl_cols=[r['pct'] for yr,r,o,t,c,v in rows]
    flag="✅" if pos>=3 and mdd<=25 else ""
    print(f"  ms={ms}: {pnl_cols[0]:+.1f}%  {pnl_cols[1]:+.1f}%  {pnl_cols[2]:+.1f}%  {pnl_cols[3]:+.1f}%  total={tot:.0f}  DD={mdd:.1f}%  pos={pos}/3 {flag}")

# Test cooldown variations
print("\n=== COOLDOWN TEST at best ADX + ms ===")
for cd in [16,24,48,72,96,144]:
    cfg=dict(best_cfg_v15,adx_norm=best_adx,cooldown=cd)
    rows=run_gauntlet(cfg,RISK)
    mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
    tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
    pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
    pnl_cols=[r['pct'] for yr,r,o,t,c,v in rows]
    nt=sum(r['trades'] for yr,r,o,t,c,v in rows)
    flag="✅" if pos>=3 and mdd<=25 else ""
    print(f"  cd={cd:3d}: {pnl_cols[0]:+.1f}%  {pnl_cols[1]:+.1f}%  {pnl_cols[2]:+.1f}%  {pnl_cols[3]:+.1f}%  n={nt}  total={tot:.0f}  DD={mdd:.1f}%  pos={pos}/3 {flag}")
