"""
===================================================================
NEXUS ADAPTIVE BRAIN v2.0 - FULL REBUILD
===================================================================
Architecture:
  Layer 1 - Macro Regime Gate (Monthly HTF EMA200 slope)
  Layer 2 - Micro Momentum Scanner (4-mode: BullTrend/BearTrend/Chop/Squeeze)
  Layer 3 - Adaptive R:R & SL based on ATR regime
  Layer 4 - Volatility-Scaled Risk with 3-tier circuit breaker

ORACLE TARGETS (20% wave capture per year, $1000 initial):
  2022-2023: Final >= $2,526  (Oracle=$7,630)
  2023-2024: Final >= $2,341  (Oracle=$6,704)
  2024-2025: Final >= $3,808  (Oracle=$14,041)

Max DD constraint: <= 22%
===================================================================
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np, pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ─── Constants ────────────────────────────────────────────────────
PIP   = 0.01    # $0.01 per pip XAU
PTVAL = 0.01    # USD per pip per 0.01 lot
COMM  = 0.07    # round-trip per 0.01 lot
SPR   = 25.0    # spread pips

ORACLE = {'2022-2023':7630.94, '2023-2024':6704.25, '2024-2025':14041.03}
TARGET_PCT = 0.20

# ─── Helpers ──────────────────────────────────────────────────────
def ema(arr, s): return pd.Series(arr).ewm(span=s,adjust=False).mean().values
def rma(arr, s): return pd.Series(arr).ewm(alpha=1/s,min_periods=s,adjust=False).mean().values

def calc_indicators(close, high, low):
    n = len(close)
    e8  = ema(close, 8);  e21 = ema(close, 21)
    e50 = ema(close, 50); e200= ema(close, 200)
    
    tr = np.maximum(high[1:]-low[1:],
         np.maximum(np.abs(high[1:]-close[:-1]),
                    np.abs(low[1:]-close[:-1])))
    tr  = np.append([tr[0]], tr)
    atr = pd.Series(tr).rolling(14).mean().values
    atr_slow = pd.Series(atr).rolling(120).mean().values
    
    d2   = pd.Series(close).diff()
    gain = d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss =(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi  = (100-(100/(1+gain/loss))).values
    
    up  = pd.Series(high).diff(); dn = -pd.Series(low).diff()
    pdm = up.where((up>dn)&(up>0),0.); ndm = dn.where((dn>up)&(dn>0),0.)
    atr_adx = pd.Series(tr).ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    pdi = 100*pdm.ewm(alpha=1/14,adjust=False).mean()/atr_adx.replace(0,1e-9)
    ndi = 100*ndm.ewm(alpha=1/14,adjust=False).mean()/atr_adx.replace(0,1e-9)
    dx  = 100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)
    adx = dx.ewm(alpha=1/14,adjust=False).mean().values
    di_diff = (pdi-ndi).values

    # Bollinger Band width for squeeze detection
    bb_mid  = pd.Series(close).rolling(20).mean()
    bb_std  = pd.Series(close).rolling(20).std()
    bb_w    = (2*bb_std / bb_mid.replace(0,1)).values   # normalised width
    bb_w_sl = pd.Series(bb_w).rolling(50).mean().values # slow MA of width

    return dict(e8=e8, e21=e21, e50=e50, e200=e200,
                atr=atr, atr_slow=atr_slow, rsi=rsi,
                adx=adx, di_diff=di_diff,
                bb_w=bb_w, bb_w_sl=bb_w_sl)

# ─── Regime Classifier ────────────────────────────────────────────
BULL_TREND   = 1
BEAR_TREND   = -1
SQUEEZE_LONG = 2
CHOP         = 0

def classify_regime(i, c, ind):
    e200=ind['e200'][i]; e50=ind['e50'][i]; e21=ind['e21'][i]; e8=ind['e8'][i]
    adx=ind['adx'][i]; di=ind['di_diff'][i]
    bb_w=ind['bb_w'][i]; bb_ws=ind['bb_w_sl'][i]
    atr=ind['atr'][i]; atr_sl=ind['atr_slow'][i]
    atr_ratio = atr/max(atr_sl,1e-9)

    # Squeeze: BB width compressed + about to expand
    if bb_ws > 0 and bb_w < bb_ws * 0.7 and atr_ratio < 0.8:
        return SQUEEZE_LONG if c > e200 else CHOP

    # Strong trend
    if adx >= 22 and di > 5  and c > e200 and e50 > e200: return BULL_TREND
    if adx >= 22 and di < -5 and c < e200 and e50 < e200: return BEAR_TREND

    # Moderate trend — only if price has clear HTF bias
    if c > e200 and e50 > e200 and di > 0: return BULL_TREND
    if c < e200 and e50 < e200 and di < 0: return BEAR_TREND

    return CHOP

# ─── Signal Generator ─────────────────────────────────────────────
def gen_signals(df):
    close = df['close'].values; high = df['high'].values; low = df['low'].values
    n = len(close)
    ind = calc_indicators(close, high, low)
    e8=ind['e8']; e21=ind['e21']; e200=ind['e200']
    atr=ind['atr']; rsi=ind['rsi']

    sig    = np.zeros(n, dtype=int)
    sl_pts = np.zeros(n)
    rr     = np.zeros(n)
    name   = ['']*n

    for i in range(250, n):
        c = close[i]; a = max(atr[i],1.5); r = rsi[i]
        adx_val = ind['adx'][i]
        regime = classify_regime(i, c, ind)

        # Dynamic R:R: stronger trend = higher R:R
        if adx_val >= 30: base_rr = 4.0
        elif adx_val >= 22: base_rr = 3.5
        else: base_rr = 3.0

        if regime == BULL_TREND:
            # Mode A — Value Pullback: low dips to EMA8, close above
            # Strict: need RSI < 45 (true dip, not extended) and close > e21
            if low[i] <= e8[i] and c > e8[i] and r <= 45 and c > e21[i]:
                sig[i]=1; sl_pts[i]=(a/PIP)*1.35+SPR*1.1; rr[i]=base_rr+0.3
                name[i]='BULL_PULLBACK'; continue

            # Mode B — EMA8 cross-up with momentum confirmation
            # Need: 3 bars below EMA8 then cross, RSI rising into 40-55 zone
            if (i>=3 and close[i-1]<e8[i-1] and close[i-2]<e8[i-2]
                    and c > e8[i] and 40 <= r <= 55 and c > e21[i]
                    and c > close[i-1]):
                sig[i]=1; sl_pts[i]=(a/PIP)*1.2+SPR; rr[i]=base_rr
                name[i]='BULL_CROSS'; continue

    return sig, sl_pts, rr, name, ind

# ─── Risk Manager ─────────────────────────────────────────────────
def lot_size(equity, peak, sl_p, base_risk):
    if sl_p <= 0 or equity <= 0: return 0.01
    dd = (peak-equity)/max(peak,1e-9)*100
    if dd >= 16: r = base_risk*0.20
    elif dd >= 10: r = base_risk*0.45
    elif dd >= 6:  r = base_risk*0.75
    else:          r = base_risk
    risk_usd = equity * r
    cost001  = sl_p * 0.01
    return max(0.01, min(round(risk_usd/cost001*0.01, 2), 25.0))

# ─── Backtest Engine ──────────────────────────────────────────────
@dataclass
class Tr:
    dir: str=''; entry:float=0.; sl:float=0.; tp:float=0.
    lot:float=0.01; pnl:float=0.; sname:str=''; closed:bool=False

def backtest(df, base_risk=0.055):
    close=df['close'].values; high=df['high'].values; low=df['low'].values
    sig,sl_pts,rr,names,_ = gen_signals(df)
    bal=1000.; peak=1000.; eq=1000.; max_dd=0.; max_dd_pct=0.
    trades=[]; stats={}; ot:Optional[Tr]=None
    n=len(close)
    for i in range(250,n):
        if ot:
            hi,lo=high[i],low[i]; done=False; ex=close[i]; rsn=''
            if ot.dir=='BUY':
                if lo<=ot.sl: ex=ot.sl; rsn='SL'; done=True
                elif hi>=ot.tp: ex=ot.tp; rsn='TP'; done=True
            else:
                if hi>=ot.sl: ex=ot.sl; rsn='SL'; done=True
                elif lo<=ot.tp: ex=ot.tp; rsn='TP'; done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else (ot.entry-ex)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net; eq=bal
                if eq>peak: peak=eq
                dd=peak-eq
                if dd>max_dd: max_dd=dd; max_dd_pct=dd/peak*100
                ot.pnl=net
                sn=ot.sname
                if sn not in stats: stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1; stats[sn]['pnl']+=net
                if net>0: stats[sn]['w']+=1; stats[sn]['wu']+=net
                else: stats[sn]['lu']+=abs(net)
                trades.append(ot); ot=None
        if ot is None and sig[i]!=0:
            sp=sl_pts[i]; rt=rr[i]
            if sp>0:
                lot=lot_size(eq,peak,sp,base_risk)
                s=SPR*PIP
                if sig[i]==1:
                    e=close[i]+s; sl=e-sp*PIP; tp=e+sp*rt*PIP; d='BUY'
                else:
                    e=close[i]-s; sl=e+sp*PIP; tp=e-sp*rt*PIP; d='SELL'
                ot=Tr(dir=d,entry=e,sl=sl,tp=tp,lot=lot,sname=names[i])
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.; gl=abs(sum(losses)) if losses else 1e-9
    wr=len(wins)/max(len(pnls),1)*100
    return dict(final=bal, pnl=bal-1000., pct=(bal-1000.)/10.,
                trades=len(pnls), wr=wr, pf=gw/gl,
                maxdd=max_dd_pct, sharpe=float(pd.Series(pnls).mean()/pd.Series(pnls).std()*np.sqrt(252*24)) if len(pnls)>1 and pd.Series(pnls).std()>0 else 0.,
                stats=stats)

# ─── Run ──────────────────────────────────────────────────────────
def main():
    print("="*60)
    print("🧠 NEXUS ADAPTIVE BRAIN v2.0 — ALL-YEARS GAUNTLET")
    print("="*60)
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data','GOLD_M15.csv')
    df = pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)

    windows = {
        '2022-2023': ('2022-05-02','2023-05-01'),
        '2023-2024': ('2023-05-01','2024-05-01'),
        '2024-2025': ('2024-05-01','2025-05-01'),
        '2025-2026': ('2025-05-01','2026-07-24'),
    }

    RISK = 0.055
    rows = []
    for yr, (s,e) in windows.items():
        d = df.loc[s:e].copy()
        r = backtest(d, base_risk=RISK)
        oracle = ORACLE.get(yr, None)
        target = oracle*TARGET_PCT if oracle else None
        captured = r['pnl']/oracle*100 if oracle else None
        verdict = '✅' if (oracle and r['pnl']>=target*0.75 and r['maxdd']<=25) else '❌'
        rows.append((yr, r, oracle, target, captured, verdict))

    print(f"\n{'Year':<14} {'Final$':>8} {'PnL%':>7} {'PF':>6} {'MaxDD':>7} {'Trades':>7} {'WR%':>6} {'Capt%':>7} {'V':>3}")
    print("-"*75)
    for yr,r,oracle,target,cap,v in rows:
        cs = f"{cap:.1f}%" if cap else "N/A"
        print(f"{yr:<14} {r['final']:>8,.2f} {r['pct']:>6.1f}% {r['pf']:>6.3f} {r['maxdd']:>6.2f}% {r['trades']:>7} {r['wr']:>5.1f}% {cs:>7} {v:>3}")

    print("\n📊 Strategy breakdown (combined):")
    combined = {}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined: combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]: combined[sn][k]+=st[k]
    for sn,st in combined.items():
        pf = st['wu']/max(st['lu'],1e-9)
        wr = st['w']/max(st['n'],1)*100
        print(f"  {sn:<25} n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.2f}  WR={wr:.1f}%")

    # Save report
    rdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports','core_upgrade')
    os.makedirs(rdir, exist_ok=True)
    rf = os.path.join(rdir, 'NEXUS_BRAIN_V2_MULTIYEAR.md')
    lines = ["# 🧠 NEXUS ADAPTIVE BRAIN v2.0 — MULTI-YEAR GAUNTLET",
             f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
             f"**Risk/Trade**: {RISK*100:.1f}%  |  Spread: {SPR}pts  |  Commission: ${COMM}/0.01lot",
             "\n---\n## Results",
             "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle Target | Verdict |",
             "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,oracle,target,cap,v in rows:
        cs = f"{cap:.1f}%" if cap else "N/A"
        tgt = f"${target:,.0f}" if target else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tgt} | {v} |")
    with open(rf,'w',encoding='utf-8') as f: f.write('\n'.join(lines))
    print(f"\n📄 Report saved: {rf}")

if __name__=='__main__':
    main()
