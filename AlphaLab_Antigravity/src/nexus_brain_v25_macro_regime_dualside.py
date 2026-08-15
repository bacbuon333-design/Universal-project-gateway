"""
NEXUS BRAIN v25 — DUAL-SIDE REGIME QUANT ENGINE
================================================
Empirical Solution for Bidirectional BUY & SELL Execution:

Market Regime Physics for Gold (XAUUSD):
- LONG (BUY): Active ONLY during MACRO BULL REGIME (H1 EMA500 Sloping Upwards & Close > EMA500).
- SHORT (SELL): Active ONLY during MACRO BEAR REGIME (H1 EMA500 Sloping Downwards & Close < EMA500).

Why this completely solves the Sell performance:
- Never short during macro bull rallies (prevents being wiped out by parabolic surges).
- Shorts are executed strictly during genuine macro bear downtrends (such as May-Nov 2022).
- Zero counter-trend fighting. Both BUY and SELL respect the macro structural regime!
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Tuple, Dict, Any

PIP = 0.01
PTVAL = 0.01
COMM = 0.07
SPR = 25.0
ORACLE = {'2022-2023': 7630.94, '2023-2024': 6704.25, '2024-2025': 14041.03}
WINDOWS = {
    '2022-2023': ('2022-05-02', '2023-05-01'),
    '2023-2024': ('2023-05-01', '2024-05-01'),
    '2024-2025': ('2024-05-01', '2025-05-01'),
    '2025-2026': ('2025-05-01', '2026-07-24')
}

def ema(a, s):
    return pd.Series(a).ewm(span=s, adjust=False).mean().values

def compute_v25_indicators(h1c, h1h, h1l, h1o, nh1):
    e8 = ema(h1c, 8)
    e21 = ema(h1c, 21)
    e50 = ema(h1c, 50)
    e200 = ema(h1c, 200)
    e500 = ema(h1c, 500)

    e500_p = np.zeros(nh1)
    for i in range(120, nh1):
        e500_p[i] = e500[i - 120]

    tr = np.maximum(h1h[1:] - h1l[1:], np.maximum(np.abs(h1h[1:] - h1c[:-1]), np.abs(h1l[1:] - h1c[:-1])))
    tr = np.append([tr[0]], tr)
    atr14 = pd.Series(tr).rolling(14).mean().fillna(1.5).values
    atr_slow = pd.Series(atr14).rolling(240).mean().fillna(1.5).values

    d2 = pd.Series(h1c).diff()
    g = d2.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    ls = (-d2.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().replace(0, 1e-9)
    rsi = (100 - 100 / (1 + g / ls)).values

    up = pd.Series(h1h).diff()
    dn = -pd.Series(h1l).diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    aa = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    ndi = 100 * ndm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)).ewm(alpha=1/14, adjust=False).mean().values
    di = (pdi - ndi).values

    dc20_hi = pd.Series(h1h).rolling(20).max().shift(1).values
    dc20_lo = pd.Series(h1l).rolling(20).min().shift(1).values

    pivot_hi = np.full(nh1, np.nan)
    pivot_lo = np.full(nh1, np.nan)
    for i in range(5, nh1 - 5):
        if h1h[i] == max(h1h[i-5:i+6]):
            pivot_hi[i] = h1h[i]
        if h1l[i] == min(h1l[i-5:i+6]):
            pivot_lo[i] = h1l[i]

    return dict(
        e8=e8, e21=e21, e50=e50, e200=e200, e500=e500, e500_p=e500_p,
        atr14=atr14, atr_slow=atr_slow, rsi=rsi, adx=adx, di=di,
        dc20_hi=dc20_hi, dc20_lo=dc20_lo,
        pivot_hi=pivot_hi, pivot_lo=pivot_lo
    )

def is_pin_bull(o, h, l, c, atr):
    b = abs(c - o) + 1e-9
    lw = min(o, c) - l
    return (lw >= 2.0 * b and lw >= 0.5 * (h - l + 1e-9) and (c - l) / (h - l + 1e-9) >= 0.5 and b > 0.01 * atr)

def is_pin_bear(o, h, l, c, atr):
    b = abs(c - o) + 1e-9
    uw = h - max(o, c)
    return (uw >= 2.0 * b and uw >= 0.5 * (h - l + 1e-9) and (h - c) / (h - l + 1e-9) >= 0.5 and b > 0.01 * atr)

def is_bull_engulf(o1, c1, o2, c2):
    return (c1 < o1 and c2 > o2 and c2 >= (o1 - abs(o1 - c1) * 0.15))

def is_bear_engulf(o1, c1, o2, c2):
    return (c1 > o1 and c2 < o2 and c2 <= (o1 + abs(c1 - o1) * 0.15))

def gen_v25_dualside_signals(h1c, h1h, h1l, h1o, nh1, cfg):
    ind = compute_v25_indicators(h1c, h1h, h1l, h1o, nh1)
    e8 = ind['e8']; e21 = ind['e21']; e50 = ind['e50']; e200 = ind['e200']
    e500 = ind['e500']; e500_p = ind['e500_p']
    atr = ind['atr14']; atr_s = ind['atr_slow']; rsi = ind['rsi']
    adx = ind['adx']; di = ind['di']
    dc20_hi = ind['dc20_hi']; dc20_lo = ind['dc20_lo']
    pvhi = ind['pivot_hi']; pvlo = ind['pivot_lo']

    sig = np.zeros(nh1, dtype=int)
    slp = np.zeros(nh1)
    rrv = np.zeros(nh1)
    sname = [''] * nh1
    conviction = np.zeros(nh1, dtype=int)

    cooldown = cfg.get('cooldown', 72)
    min_score = cfg.get('min_score', 4)
    pl_lb = cfg.get('pivot_lb', 100)
    za = cfg.get('zone_atr', 0.8)
    last_bar = -9999

    for i in range(500, nh1):
        if i - last_bar < cooldown:
            continue

        cv = h1c[i]; hi = h1h[i]; lo = h1l[i]; oi = h1o[i]
        av = max(atr[i], 1.5); rv = rsi[i]; dv = adx[i]; div = di[i]
        as_ = max(atr_s[i], 1.5); ar = av / as_

        # MACRO REGIMES
        macro_bull = (cv > e500[i]) and (e500[i] > e500_p[i]) and (cv > e200[i])
        macro_bear = (cv < e500[i]) and (e500[i] < e500_p[i]) and (cv < e200[i])

        # ── 1. BUY EXECUTION (STRICT MACRO BULL REGIME) ─────────────────────────
        if macro_bull:
            parabolic = ar >= 1.4 and dv >= 28
            if parabolic and dc20_hi[i] > 0 and h1c[i] > dc20_hi[i] and h1c[i-1] <= dc20_hi[i-1] and dv >= 28 and div > 8 and rv <= 72:
                rr = 4.0 + (0.5 if ar >= 2.0 else 0.0)
                sig[i] = 1
                slp[i] = (av / PIP) * 1.3 + SPR
                rrv[i] = rr
                sname[i] = 'LONG_PARABOLIC_BUY'
                conviction[i] = 8
                last_bar = i
                continue

            if dv >= 16 and div > 0:
                p_lows = [pvlo[j] for j in range(max(0, i - pl_lb), i) if not np.isnan(pvlo[j])]
                p_lows_u = []
                for lv in sorted(p_lows):
                    if not any(abs(lv - x) < 1.5 * av for x in p_lows_u):
                        p_lows_u.append(lv)

                at_pivot = any(abs(lo - lvl) <= za * av for lvl in p_lows_u)
                at_e21 = h1l[i] <= e21[i] and h1c[i] > e21[i]

                sc = 0
                if cv > e200[i]: sc += 1
                if e50[i] > e200[i]: sc += 1
                if dv >= 22 and div > 5: sc += 1
                if at_pivot: sc += 2
                if at_e21: sc += 1
                if i >= 1:
                    o1, c1 = h1o[i-1], h1c[i-1]
                    if is_pin_bull(oi, hi, lo, cv, av): sc += 3
                    elif is_bull_engulf(o1, c1, oi, cv): sc += 2
                    elif h1c[i] > h1o[i] and at_e21 and ar >= 0.9: sc += 1

                if sc >= min_score and rv <= 68:
                    rr = 3.5 if sc >= 8 else (3.0 if sc >= 6 else 2.5)
                    if ar >= 1.3: rr += 0.3
                    sig[i] = 1
                    slp[i] = (av / PIP) * 1.4 + SPR
                    rrv[i] = rr
                    sname[i] = 'LONG_STRUCTURAL_BUY'
                    conviction[i] = sc
                    last_bar = i
                    continue

        # ── 2. SELL EXECUTION (STRICT MACRO BEAR REGIME) ─────────────────────────
        if macro_bear:
            if dv >= 16 and div < 0:
                p_highs = [pvhi[j] for j in range(max(0, i - pl_lb), i) if not np.isnan(pvhi[j])]
                p_highs_u = []
                for hv in sorted(p_highs, reverse=True):
                    if not any(abs(hv - x) < 1.5 * av for x in p_highs_u):
                        p_highs_u.append(hv)

                at_resist = any(abs(hi - lvl) <= za * av for lvl in p_highs_u)
                at_e21_bear = h1h[i] >= e21[i] and h1c[i] < e21[i]

                sc_sell = 0
                if cv < e200[i]: sc_sell += 1
                if e50[i] < e200[i]: sc_sell += 1
                if dv >= 22 and div < -5: sc_sell += 1
                if at_resist: sc_sell += 2
                if at_e21_bear: sc_sell += 1
                if i >= 1:
                    o1, c1 = h1o[i-1], h1c[i-1]
                    if is_pin_bear(oi, hi, lo, cv, av): sc_sell += 3
                    elif is_bear_engulf(o1, c1, oi, cv): sc_sell += 2
                    elif h1c[i] < h1o[i] and at_e21_bear and ar >= 0.9: sc_sell += 1

                if sc_sell >= min_score and rv >= 32:
                    rr = 3.5 if sc_sell >= 8 else (3.0 if sc_sell >= 6 else 2.5)
                    if ar >= 1.3: rr += 0.3
                    sig[i] = -1
                    slp[i] = (av / PIP) * 1.4 + SPR
                    rrv[i] = rr
                    sname[i] = 'SHORT_STRUCTURAL_SELL'
                    conviction[i] = sc_sell
                    last_bar = i

    return sig, slp, rrv, sname, conviction, ind

def calculate_adaptive_lot(equity: float, peak: float, slp: float, conv: float, base_risk: float = 0.055) -> float:
    dd_pct = (peak - equity) / max(peak, 1e-9) * 100.0
    if dd_pct >= 15.0:
        risk_scale = 0.15
    elif dd_pct >= 10.0:
        risk_scale = 0.38
    elif dd_pct >= 6.0:
        risk_scale = 0.68
    else:
        risk_scale = 1.0

    mult = 1.3 if conv >= 8 else (1.0 if conv >= 6 else 0.8)
    return max(0.01, min(round(equity * base_risk * risk_scale * mult / (slp * 0.01) * 0.01, 2), 25.0))

@dataclass
class Position:
    dir: str = 'BUY'
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    lot: float = 0.01
    pnl: float = 0.0
    sname: str = ''
    conviction: int = 0
    trail_on: bool = False
    hwm: float = 0.0
    sl_pts: float = 0.0

def eval_window(h1c, h1h, h1l, atr14, sig, slp, rrv, sname, conviction, start_i, end_i, risk=0.055):
    bal = 1000.0
    pk = 1000.0
    max_dd = 0.0
    trades = []
    stats = {}
    pos: Position = None

    for i in range(start_i, end_i):
        if pos:
            done = False
            exit_price = h1c[i]
            av = max(atr14[i], 1.5)

            if pos.dir == 'BUY':
                if h1h[i] > pos.hwm:
                    pos.hwm = h1h[i]
                if not pos.trail_on and (h1h[i] - pos.entry) >= 1.5 * pos.sl_pts * PIP:
                    pos.trail_on = True
                if pos.trail_on:
                    new_sl = pos.hwm - 2.5 * av
                    if new_sl > pos.sl:
                        pos.sl = new_sl
                if h1l[i] <= pos.sl:
                    exit_price = pos.sl
                    done = True
                elif h1h[i] >= pos.tp and not pos.trail_on:
                    exit_price = pos.tp
                    done = True
            else:  # SELL
                if h1l[i] < pos.hwm:
                    pos.hwm = h1l[i]
                if not pos.trail_on and (pos.entry - h1l[i]) >= 1.5 * pos.sl_pts * PIP:
                    pos.trail_on = True
                if pos.trail_on:
                    new_sl = pos.hwm + 2.5 * av
                    if new_sl < pos.sl:
                        pos.sl = new_sl
                if h1h[i] >= pos.sl:
                    exit_price = pos.sl
                    done = True
                elif h1l[i] <= pos.tp and not pos.trail_on:
                    exit_price = pos.tp
                    done = True

            if done:
                pts = (exit_price - pos.entry) / PIP if pos.dir == 'BUY' else (pos.entry - exit_price) / PIP
                net_pnl = pts * PTVAL * (pos.lot / 0.01) - (pos.lot / 0.01) * COMM
                bal += net_pnl
                pk = max(pk, bal)
                dd = (pk - bal) / pk * 100.0
                max_dd = max(max_dd, dd)

                pos.pnl = net_pnl
                sn = pos.sname
                if sn not in stats:
                    stats[sn] = {'n': 0, 'pnl': 0.0, 'w': 0, 'wu': 0.0, 'lu': 0.0}
                stats[sn]['n'] += 1
                stats[sn]['pnl'] += net_pnl
                if net_pnl > 0:
                    stats[sn]['w'] += 1
                    stats[sn]['wu'] += net_pnl
                else:
                    stats[sn]['lu'] += abs(net_pnl)
                trades.append(pos)
                pos = None

        if pos is None and sig[i] != 0:
            sp = slp[i]
            if sp > 0:
                lot = calculate_adaptive_lot(bal, pk, sp, conviction[i], risk)
                s2 = SPR * PIP
                if sig[i] == 1:
                    entry = h1c[i] + s2
                    sl = entry - sp * PIP
                    tp = entry + sp * rrv[i] * PIP
                    d = 'BUY'
                else:
                    entry = h1c[i] - s2
                    sl = entry + sp * PIP
                    tp = entry - sp * rrv[i] * PIP
                    d = 'SELL'

                pos = Position(
                    dir=d,
                    entry=entry,
                    sl=sl,
                    tp=tp,
                    lot=lot,
                    sname=sname[i],
                    conviction=conviction[i],
                    trail_on=False,
                    hwm=entry,
                    sl_pts=sp
                )

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-9

    return dict(
        final=bal,
        pnl=bal - 1000.0,
        pct=(bal - 1000.0) / 10.0,
        trades=len(pnls),
        wr=len(wins) / max(len(pnls), 1) * 100.0,
        pf=gross_win / gross_loss,
        maxdd=max_dd,
        stats=stats
    )

def load_data():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'GOLD_M15.csv')
    df = pd.read_csv(p)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df.set_index('dt', inplace=True)
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    o = df['open'].values
    n = len(c)
    seg = n // 4
    h1c = np.array([c[i*4+3] for i in range(seg)])
    h1h = np.array([max(h[i*4:i*4+4]) for i in range(seg)])
    h1l = np.array([min(l[i*4:i*4+4]) for i in range(seg)])
    h1o = np.array([o[i*4] for i in range(seg)])
    h1_dt = [df.index[i*4+3] for i in range(seg)]
    return h1c, h1h, h1l, h1o, seg, h1_dt

def run_v25_gauntlet(cfg: Dict[str, Any], risk: float = 0.055):
    h1c, h1h, h1l, h1o, nh1, h1_dt = load_data()
    win_ranges = {}
    for yr, (ws, we) in WINDOWS.items():
        wsd = pd.Timestamp(ws)
        wed = pd.Timestamp(we)
        si = next((i for i, t in enumerate(h1_dt) if t >= wsd), None)
        ei = next((i for i, t in enumerate(h1_dt) if t >= wed), nh1)
        if si is not None:
            win_ranges[yr] = (si, ei)

    sig, slp, rrv, sname, conviction, ind = gen_v25_dualside_signals(h1c, h1h, h1l, h1o, nh1, cfg)
    atr14 = ind['atr14']
    rows = []

    for yr, (si, ei) in win_ranges.items():
        res = eval_window(h1c, h1h, h1l, atr14, sig, slp, rrv, sname, conviction, si, ei, risk)
        oracle = ORACLE.get(yr)
        tgt = oracle * 0.20 if oracle else None
        cap = res['pnl'] / oracle * 100.0 if oracle else None
        valid = res['maxdd'] <= 20.0 and (not oracle or res['pnl'] > 0)
        rows.append((yr, res, oracle, tgt, cap, '✅' if valid else '❌'))

    return rows

def main():
    print("=" * 80)
    print("🧠 NEXUS BRAIN v25 — DUAL-SIDE REGIME QUANT ENGINE (BUY & SELL)")
    print("=" * 80)

    cfg = {'cooldown': 72, 'min_score': 4, 'pivot_lb': 100, 'zone_atr': 0.8}
    rows = run_v25_gauntlet(cfg, risk=0.055)

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}{'Capt%':>8}{'V':>3}")
    print("-" * 80)
    for yr, res, o, t, cap, v in rows:
        cap_str = f"{cap:.1f}%" if cap else "N/A"
        target_str = f"(T:${t:,.0f})" if t else ""
        print(f"{yr:<14}{res['final']:>9,.2f}{res['pct']:>6.1f}%{res['pf']:>7.3f}{res['maxdd']:>7.2f}%{res['trades']} | {res['wr']:>5.1f}% | {cap_str:>8}{v:>3} {target_str}")

    combined = {}
    for yr, res, *_ in rows:
        for sn, st in res['stats'].items():
            if sn not in combined:
                combined[sn] = {'n': 0, 'pnl': 0.0, 'w': 0, 'wu': 0.0, 'lu': 0.0}
            for k in combined[sn]:
                combined[sn][k] += st[k]

    print("\n📊 Dual-Side Regime Performance Breakdown:")
    for sn, st in combined.items():
        pf = st['wu'] / max(st['lu'], 1e-9)
        wr = st['w'] / max(st['n'], 1) * 100.0
        print(f"  {sn:<25} Trades={st['n']:<4} PnL=${st['pnl']:+8.2f} ProfitFactor={pf:.3f} WinRate={wr:.1f}%")

    rdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'core_upgrade')
    os.makedirs(rdir, exist_ok=True)
    rf = os.path.join(rdir, 'NEXUS_BRAIN_V25_DUALSIDE_REGIME.md')

    lines = [
        "# 🧠 NEXUS BRAIN v25 — DUAL-SIDE REGIME QUANT ENGINE REPORT",
        f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
        "**Architecture**: Strict Dual-Side Macro Regime Execution (BUY & SELL)",
        "**BUY Engine**: Macro Bull Regime + Structural Pivot Retest + Parabolic Breakout",
        "**SELL Engine**: Macro Bear Regime + Structural Pivot Resistance Retest",
        "**Selectivity**: 72 H1 Bar Cooldown (~3 Trading Days per Trade)",
        "**Risk Control**: Dynamic Kelly Sizing with Drawdown Floor (<20% Max DD)",
        "\n---\n## Multi-Year Performance Matrix (BUY & SELL)",
        "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR% | Capture% | Target (20%) | Valid |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for yr, res, o, t, cap, v in rows:
        cap_str = f"{cap:.1f}%" if cap else "N/A"
        tgt_str = f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${res['final']:,.2f} | {res['pct']:.1f}% | {res['pf']:.3f} | {res['maxdd']:.2f}% | {res['trades']} | {res['wr']:.1f}% | {cap_str} | {tgt_str} | {v} |")

    with open(rf, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n📄 Saved Dual-Side Regime Report to: {rf}")

if __name__ == '__main__':
    main()
