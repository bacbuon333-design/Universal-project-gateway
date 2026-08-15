"""
SIGNAL ISOLATION TEST — find the single best combination per year
Key data from diag:
  DC_BREAK_BUY  2023-2024: PF=1.425, WR=33% -> WORKS
  DC_BREAK_BUY  2022-2023: PF=0.624 -> FAILS
  DC_BREAK_BUY  2024-2025: PF=1.062 -> marginal
  PULL_E8_BUY   combined: PF=0.921 -> marginal
  REBOUND_E8_SELL: PF=0.782 -> FAILS

Conclusion: SHORTS are net losers across all years. Remove shorts entirely.
Focus: tune LONG-ONLY pullback + DC_BREAK to maximize years.

Try: Different RSI thresholds: 30, 35, 40, 45, 50
Try: Different ADX thresholds: 12, 16, 20, 25
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from nexus_brain_v7 import run_gauntlet,ORACLE

print("="*70)
print("🔬 PARAMETER SWEEP — RSI + ADX + RR combinations (LONG ONLY)")
print("="*70)

best_score=0
best_cfg=None
best_rows=None

rsi_vals=[35,40,45,50]
adx_vals=[12,16,20]
rr_vals=[2.5,3.0,3.5,4.0]

for rsi_b in rsi_vals:
    for adx_m in adx_vals:
        for rr_b in rr_vals:
            cfg={'adx_min':adx_m,'rsi_buy':rsi_b,'rsi_sell':100,'rr_base':rr_b,'sl_mult':1.3}
            rows=run_gauntlet(RISK=0.055,cfg=cfg)
            # Score: sum of PnL% across 3 known years, penalize if maxdd>22
            score=0;ok_years=0
            for yr,r,o,t,cap,v in rows:
                if o is None:continue
                dd_pen=0 if r['maxdd']<=22 else (r['maxdd']-22)*50
                score+=r['pnl']-dd_pen
                if r['pnl']>0 and r['maxdd']<=25:ok_years+=1
            if score>best_score:
                best_score=score;best_cfg=cfg.copy();best_rows=rows
            # Quick print if all 3 positive
            if ok_years>=2:
                yr_str=" ".join(f"{yr[:4]}:{r['pct']:.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows if _[0])
                print(f"  rsi={rsi_b:2d} adx={adx_m:2d} rr={rr_b:.1f} | {yr_str} | score={score:.0f}")

print(f"\n🏆 BEST CONFIG: {best_cfg}")
print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
print("-"*72)
for yr,r,o,t,cap,v in best_rows:
    cs=f"{cap:.1f}%" if cap else "N/A"
    print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3}")
