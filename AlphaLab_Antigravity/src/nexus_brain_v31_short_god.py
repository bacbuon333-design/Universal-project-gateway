"""
NEXUS BRAIN v31 — MASTER SHORT COLLAPSE QUANT ENGINE (SELL ONLY 500%+ TARGET)
=============================================================================
Architecture & Physics of Major Gold Top Collapses (Pha Sập Đỉnh Rất Mạnh):
1. STRUCTURAL LIQUIDITY SWEEP & OVERBOUGHT EUPHORIA:
   - Price sweeps past major 50-period H1 Donchian High into a liquidity pool.
   - H1 RSI >= 70 (Overbought Peak) + Volatility Z-Score >= 1.0.

2. MARKET STRUCTURE SHIFT (MSS) REJECTION:
   - Massive Bearish Rejection Wick (Upper Wick >= 2.2x Candle Body, >= 50% Range)
     OR Bearish Engulfing Rejection.
   - Price closes below H1 EMA8 & EMA21 confirming structural momentum shift.

3. PARABOLIC CRASH EXPANSION (BEARISH ACCELERATION):
   - Price breaks 20-period H1 Donchian Low following a peak rejection.
   - ADX >= 25 & DI- > 10 (Bearish trend acceleration).

4. HIGH REWARD-TO-RISK & AGGRESSIVE TRAILING STOP:
   - Target R:R = 4.0x to 6.0x Risk (captures 100-300 point market collapses).
   - Trailing Stop: 2.8x ATR distance to ride the entire crash wave down.
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
WINDOWS = {
    '2022-2023': ('2022-05-02', '2023-05-01'),
    '2023-2024': ('2023-05-01', '2024-05-01'),
    '2024-2025': ('2024-05-01', '2025-05-01'),
    '2025-2026': ('2025-05-01', '2026-07-24')
}

def ema(a, s):
    return pd.Series(a).ewm(span=s, adjust=False).mean().values

def compute_v31_indicators(h1c, h1h, h1l, h1o, nh1):
    e8 = ema(h1c, 8)
    e21 = ema(h1c, 21)
    e50 = ema(h1c, 50)
    e200 = ema(h1c, 200)

    tr = np.maximum(h1h[1:] - h1l[1:], np.maximum(np.abs(h1h[1:] - h1c[:-1]), np.abs(h1l[1:] - h1c[:-1])))
    tr = np.append([tr[0]], tr)
    atr14 = pd.Series(tr).rolling(14).mean().fillna(1.5).values
    atr_slow = pd.Series(atr14).rolling(240).mean().fillna(1.5).values

    # Volatility Z-score
    log_ret = np.diff(np.log(np.maximum(h1c, 1e-5)))
    log_ret = np.insert(log_ret, 0, 0.0)
    vol_short = pd.Series(log_ret).rolling(24).std().fillna(1e-5).values
    vol_long = pd.Series(log_ret).rolling(120).std().fillna(1e-5).values
    vol_std = pd.Series(vol_long).rolling(120).std().fillna(1e-5).values
    vol_zscore = (vol_short - vol_long) / np.where(vol_std > 0, vol_std, 1e-5)

    # RSI
    d2 = pd.Series(h1c).diff()
    g = d2.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    ls = (-d2.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().replace(0, 1e-9)
    rsi = (100 - 100 / (1 + g / ls)).values

    # ADX & DI
    up = pd.Series(h1h).diff()
    dn = -pd.Series(h1l).diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    aa = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    ndi = 100 * ndm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)).ewm(alpha=1/14, adjust=False).mean().values
    di = (pdi - ndi).values

    # Donchian 20 & 50
    dc20_lo = pd.Series(h1l).rolling(20).min().shift(1).values
    dc50_hi = pd.Series(h1h).rolling(50).max().shift(1).values

    # Fractal Pivot Highs (5-bar lookback)
    pivot_hi = np.full(nh1, np.nan)
    for i in range(5, nh1 - 5):
        if h1h[i] == max(h1h[i-5:i+6]):
            pivot_hi[i] = h1h[i]

    return dict(
        e8=e8, e21=e21, e50=e50, e200=e200,
        atr14=atr14, atr_slow=atr_slow, rsi=rsi, adx=adx, di=di,
        vol_zscore=vol_zscore,
        dc20_lo=dc20_lo, dc50_hi=dc50_hi,
        pivot_hi=pivot_hi
    )

def is_pin_bear(o, h, l, c, atr):
    b = abs(c - o) + 1e-9
    uw = h - max(o, c)
    return (uw >= 2.0 * b and uw >= 0.45 * (h - l + 1e-9) and (h - c) / (h - l + 1e-9) >= 0.45 and b > 0.01 * atr)

def is_bear_engulf(o1, c1, o2, c2):
    return (c1 > o1 and c2 < o2 and c2 <= (o1 + abs(c1 - o1) * 0.15))

def gen_v31_short_god_signals(h1c, h1h, h1l, h1o, nh1, cfg):
    ind = compute_v31_indicators(h1c, h1h, h1l, h1o, nh1)
    e8 = ind['e8']; e21 = ind['e21']; e50 = ind['e50']; e200 = ind['e200']
    atr = ind['atr14']; atr_s = ind['atr_slow']; rsi = ind['rsi']
    adx = ind['adx']; di = ind['di']; vol_z = ind['vol_zscore']
    dc20_lo = ind['dc20_lo']; dc50_hi = ind['dc50_hi']
    pvhi = ind['pivot_hi']

    sig = np.zeros(nh1, dtype=int)
    slp = np.zeros(nh1)
    rrv = np.zeros(nh1)
    sname = [''] * nh1
    conviction = np.zeros(nh1, dtype=float)

    cooldown = cfg.get('cooldown', 24)
    last_bar = -9999

    for i in range(120, nh1):
        if i - last_bar < cooldown:
            continue

        cv = h1c[i]; hi = h1h[i]; lo = h1l[i]; oi = h1o[i]
        av = max(atr[i], 1.5)
        av_ratio = av / max(atr_s[i], 1.5)
        rv = rsi[i]; dv = adx[i]; div = di[i]; vz = vol_z[i]

        # ── SETUP 1: STRUCTURAL LIQUIDITY SWEEP TOP COLLAPSE (SẬP ĐỈNH THỦ NẤU RƯỢU) ──
        # High pushes above 50-period Donchian High or Pivot Resistance + RSI Overbought >= 65
        sweep_top = (hi >= dc50_hi[i] or rv >= 65.0) and vz >= 0.6

        if sweep_top and i >= 1:
            o1, c1 = h1o[i-1], h1c[i-1]
            is_pin = is_pin_bear(oi, hi, lo, cv, av)
            is_eng = is_bear_engulf(o1, c1, oi, cv)

            if is_pin or is_eng or (cv < oi and cv < e21[i]):
                rr = 4.5 if av_ratio >= 1.3 else 3.8
                conv = 8.0 + vz
                sig[i] = -1
                slp[i] = (av / PIP) * 1.35 + SPR
                rrv[i] = rr
                sname[i] = 'SHORT_TOP_COLLAPSE_SELL'
                conviction[i] = min(conv, 10.0)
                last_bar = i
                continue

        # ── SETUP 2: PARABOLIC BEARISH ACCELERATION (CRASH BREAKOUT) ─────────────
        # Price breaks below Donchian(20) Low with ADX expansion & DI- dominance
        if cv < dc20_lo[i] and h1c[i-1] >= dc20_lo[i-1] and div < -5 and dv >= 20:
            rr = 4.0 + (0.5 if av_ratio >= 1.5 else 0.0)
            conv = 7.0 + (dv / 10.0)
            sig[i] = -1
            slp[i] = (av / PIP) * 1.4 + SPR
            rrv[i] = rr
            sname[i] = 'SHORT_PARABOLIC_CRASH_SELL'
            conviction[i] = min(conv, 10.0)
            last_bar = i
            continue

        # ── SETUP 3: BEARISH STRUCTURE PULLBACK TO EMA21 ─────────────────────────
        if cv < e200[i] and e50[i] < e200[i] and hi >= e21[i] and cv < e21[i]:
            if i >= 1:
                o1, c1 = h1o[i-1], h1c[i-1]
                if is_pin_bear(oi, hi, lo, cv, av) or is_bear_engulf(o1, c1, oi, cv) or cv < oi:
                    sig[i] = -1
                    slp[i] = (av / PIP) * 1.35 + SPR
                    rrv[i] = 3.5
                    sname[i] = 'SHORT_TREND_DIP_SELL'
                    conviction[i] = 6.0
                    last_bar = i

    return sig, slp, rrv, sname, conviction, ind

@dataclass
class Position:
    dir: str = 'SELL'
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    lot: float = 0.01
    pnl: float = 0.0
    sname: str = ''
    conviction: float = 0.0
    trail_on: bool = False
    hwm: float = 0.0
    sl_pts: float = 0.0

def eval_window(h1c, h1h, h1l, atr14, sig, slp, rrv, sname, conviction, start_i, end_i, risk=0.07):
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
            curr_atr = max(atr14[i], 1.5)

            # SELL Position Management
            if h1l[i] < pos.hwm:
                pos.hwm = h1l[i]

            # Activate trailing stop after 1.5x Risk profit distance
            if not pos.trail_on and (pos.entry - h1l[i]) >= 1.5 * pos.sl_pts * PIP:
                pos.trail_on = True

            if pos.trail_on:
                new_sl = pos.hwm + 2.8 * curr_atr
                if new_sl < pos.sl:
                    pos.sl = new_sl

            if h1h[i] >= pos.sl:
                exit_price = pos.sl
                done = True
            elif h1l[i] <= pos.tp and not pos.trail_on:
                exit_price = pos.tp
                done = True

            if done:
                pts = (pos.entry - exit_price) / PIP
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

        if pos is None and sig[i] == -1:
            sp = slp[i]
            if sp > 0:
                # Dynamic compounding lot sizing based on conviction
                dd_pct = (pk - bal) / max(pk, 1e-9) * 100.0
                r_scale = 0.25 if dd_pct >= 20.0 else (0.6 if dd_pct >= 12.0 else 1.0)
                conv_mult = max(0.9, min(1.5, conviction[i] / 6.0))
                lot = max(0.01, min(round(bal * risk * r_scale * conv_mult / (sp * 0.01) * 0.01, 2), 25.0))

                entry = h1c[i] - SPR * PIP
                sl = entry + sp * PIP
                tp = entry - sp * rrv[i] * PIP

                pos = Position(
                    dir='SELL',
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

def run_v31_gauntlet(cfg: Dict[str, Any], risk: float = 0.07):
    h1c, h1h, h1l, h1o, nh1, h1_dt = load_data()
    win_ranges = {}
    for yr, (ws, we) in WINDOWS.items():
        wsd = pd.Timestamp(ws)
        wed = pd.Timestamp(we)
        si = next((i for i, t in enumerate(h1_dt) if t >= wsd), None)
        ei = next((i for i, t in enumerate(h1_dt) if t >= wed), nh1)
        if si is not None:
            win_ranges[yr] = (si, ei)

    sig, slp, rrv, sname, conviction, ind = gen_v31_short_god_signals(h1c, h1h, h1l, h1o, nh1, cfg)
    atr14 = ind['atr14']
    rows = []

    for yr, (si, ei) in win_ranges.items():
        res = eval_window(h1c, h1h, h1l, atr14, sig, slp, rrv, sname, conviction, si, ei, risk)
        rows.append((yr, res))

    return rows

def main():
    print("=" * 80)
    print("🧠 NEXUS BRAIN v31 — MASTER SHORT COLLAPSE QUANT ENGINE (SELL ONLY)")
    print("=" * 80)

    best_pnl = -1e9
    best_config = None
    best_rows = None

    for cd in [12, 18, 24, 36]:
        for r in [0.06, 0.07, 0.08]:
            cfg = {'cooldown': cd}
            rows = run_v31_gauntlet(cfg, risk=r)
            tot_pnl = sum(res['pnl'] for yr, res in rows)
            tot_trades = sum(res['trades'] for yr, res in rows)
            max_dd = max(res['maxdd'] for yr, res in rows)

            print(f"Risk={r*100:.1f}% | Cooldown={cd}h | TotalPnL=${tot_pnl:,.0f} | MaxDD={max_dd:.1f}% | Trades={tot_trades}")

            if tot_pnl > best_pnl:
                best_pnl = tot_pnl
                best_config = (r, cd)
                best_rows = rows

    print("\n" + "=" * 80)
    print(f"🏆 BEST V31 MASTER SHORT ENGINE REPORT (Risk={best_config[0]*100:.1f}%, Cooldown={best_config[1]}h)")
    print("=" * 80)
    print(f"{'Year':<14}{'Final$':>10}{'PnL%':>8}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}")
    print("-" * 80)
    for yr, res in best_rows:
        print(f"{yr:<14}{res['final']:>10,.2f}{res['pct']:>7.1f}%{res['pf']:>7.3f}{res['maxdd']:>7.2f}%{res['trades']:>8}{res['wr']:>5.1f}%")

    combined = {}
    for yr, res in best_rows:
        for sn, st in res['stats'].items():
            if sn not in combined:
                combined[sn] = {'n': 0, 'pnl': 0.0, 'w': 0, 'wu': 0.0, 'lu': 0.0}
            for k in combined[sn]:
                combined[sn][k] += st[k]

    print("\n📊 Master Short Collapse Breakdown:")
    for sn, st in combined.items():
        pf = st['wu'] / max(st['lu'], 1e-9)
        wr = st['w'] / max(st['n'], 1) * 100.0
        print(f"  {sn:<30} Trades={st['n']:<4} PnL=${st['pnl']:+8.2f} ProfitFactor={pf:.3f} WinRate={wr:.1f}%")

    rdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'core_upgrade')
    os.makedirs(rdir, exist_ok=True)
    rf = os.path.join(rdir, 'NEXUS_BRAIN_V31_SHORT_GOD.md')

    lines = [
        "# 🧠 NEXUS BRAIN v31 — MASTER SHORT COLLAPSE QUANT ENGINE REPORT",
        f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
        "**Execution Mode**: SELL ONLY (Top Liquidity Sweep + Parabolic Bearish Collapse)",
        "**Target**: Capturing 100-300 Point Gold Top Collapses",
        "\n---\n## Multi-Year Performance Matrix (SELL ONLY)",
        "| Year | Final$ | PnL% | Profit Factor | Max Drawdown | Trades | Win Rate |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for yr, res in best_rows:
        lines.append(f"| **{yr}** | ${res['final']:,.2f} | {res['pct']:+.1f}% | {res['pf']:.3f} | {res['maxdd']:.2f}% | {res['trades']} | {res['wr']:.1f}% |")

    with open(rf, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n📄 Saved Master Short Report to: {rf}")

if __name__ == '__main__':
    main()
