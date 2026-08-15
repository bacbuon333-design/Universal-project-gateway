"""
MULTI-ASSET SYMBOL STRESS TESTER — NEXUS BRAIN v22 CHAMPION ENGINE
===================================================================
Tests the Champion Adaptive Regime Engine on diverse asset classes:
1. CRYPTO: BTC-USD (Bitcoin)
2. FOREX: EURUSD=X (Euro / US Dollar)
3. INDICES: ^GSPC / SPY (S&P 500 Index)
4. COMMODITIES: CL=F (Crude Oil)
5. TECH EQUITIES: NVDA (Nvidia)

Proves whether the engine's mathematical regime logic generalizes
across different market microstructures without overfitting.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any

PIP_MAP = {
    'BTC-USD': 1.0,
    'EURUSD=X': 0.0001,
    '^GSPC': 0.1,
    'SPY': 0.01,
    'CL=F': 0.01,
    'NVDA': 0.01,
    'GOLD': 0.01
}

def ema(a, s):
    return pd.Series(a).ewm(span=s, adjust=False).mean().values

def compute_champion_indicators(c, h, l, o, n):
    e8 = ema(c, 8)
    e21 = ema(c, 21)
    e50 = ema(c, 50)
    e200 = ema(c, 200)

    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    tr = np.append([tr[0]], tr)
    atr14 = pd.Series(tr).rolling(14).mean().fillna(1.5).values
    atr_slow = pd.Series(atr14).rolling(240).mean().fillna(1.5).values

    d2 = pd.Series(c).diff()
    g = d2.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    ls = (-d2.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().replace(0, 1e-9)
    rsi = (100 - 100 / (1 + g / ls)).values

    up = pd.Series(h).diff()
    dn = -pd.Series(l).diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    aa = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    ndi = 100 * ndm.ewm(alpha=1/14, adjust=False).mean() / aa.replace(0, 1e-9)
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)).ewm(alpha=1/14, adjust=False).mean().values
    di = (pdi - ndi).values

    # 3-month momentum (90 daily bars or 480 H1 bars)
    mom3m_span = min(120, max(20, n // 5))
    mom3m = np.zeros(n, dtype=bool)
    for i in range(mom3m_span, n):
        mom3m[i] = c[i] > c[i - mom3m_span]

    mom1m_span = max(10, mom3m_span // 3)
    mom1m = np.zeros(n, dtype=bool)
    for i in range(mom1m_span, n):
        mom1m[i] = c[i] > c[i - mom1m_span]

    dc20_hi = pd.Series(h).rolling(20).max().shift(1).values

    pivot_lo = np.full(n, np.nan)
    for i in range(5, n - 5):
        if l[i] == min(l[i-5:i+6]):
            pivot_lo[i] = l[i]

    return dict(
        e8=e8, e21=e21, e50=e50, e200=e200,
        atr14=atr14, atr_slow=atr_slow, rsi=rsi, adx=adx, di=di,
        mom3m=mom3m, mom1m=mom1m, dc20_hi=dc20_hi, pivot_lo=pivot_lo
    )

def gen_champion_signals(c, h, l, o, n, symbol: str, pip_val: float):
    ind = compute_champion_indicators(c, h, l, o, n)
    e8 = ind['e8']; e21 = ind['e21']; e50 = ind['e50']; e200 = ind['e200']
    atr = ind['atr14']; atr_s = ind['atr_slow']; rsi = ind['rsi']
    adx = ind['adx']; di = ind['di']; mom3m = ind['mom3m']; mom1m = ind['mom1m']
    dc20 = ind['dc20_hi']; pvlo = ind['pivot_lo']

    sig = np.zeros(n, dtype=int)
    slp = np.zeros(n)
    rrv = np.zeros(n)
    sname = [''] * n
    conviction = np.zeros(n, dtype=int)

    cooldown = 24  # bars
    min_score = 4
    last_bar = -9999

    for i in range(100, n):
        if i - last_bar < cooldown:
            continue

        cv = c[i]; hi = h[i]; lo = l[i]; oi = o[i]
        av = max(atr[i], pip_val * 10)
        rv = rsi[i]; dv = adx[i]; div = di[i]
        as_ = max(atr_s[i], pip_val * 10); ar = av / as_

        macro_bull = mom3m[i] and mom1m[i] and cv > e200[i]
        if not macro_bull:
            continue

        parabolic = ar >= 1.3 and dv >= 25

        if parabolic:
            if (dc20[i] > 0 and c[i] > dc20[i] and c[i-1] <= dc20[i-1]
                    and dv >= 25 and div > 8 and rv <= 75):
                rr = 3.5 + (0.5 if ar >= 1.8 else 0.0)
                sc = 6 + int(dv >= 30)
                sig[i] = 1
                slp[i] = (av / pip_val) * 1.3 + 10.0
                rrv[i] = rr
                sname[i] = 'PARABOLIC_BREAKOUT_BUY'
                conviction[i] = sc
                last_bar = i
                continue

        if dv >= 15 and div > 0:
            p_lows = [pvlo[j] for j in range(max(0, i - 50), i) if not np.isnan(pvlo[j])]
            p_lows_u = []
            for lv in sorted(p_lows):
                if not any(abs(lv - x) < 1.5 * av for x in p_lows_u):
                    p_lows_u.append(lv)

            at_pivot = any(abs(lo - lvl) <= 1.0 * av for lvl in p_lows_u)
            at_e21 = l[i] <= e21[i] and c[i] > e21[i]

            sc = 0
            if cv > e200[i]: sc += 1
            if e50[i] > e200[i]: sc += 1
            if dv >= 20 and div > 5: sc += 1
            if at_pivot: sc += 2
            if at_e21: sc += 1
            if i >= 1:
                o1, c1 = o[i-1], c[i-1]
                b = abs(c[i] - o[i]) + 1e-9; lw = min(o[i], c[i]) - lo
                is_pin = (lw >= 1.8 * b and lw >= 0.45 * (hi - lo + 1e-9) and (c[i] - lo) / (hi - lo + 1e-9) >= 0.45)
                is_eng = (c1 < o1 and c[i] > o[i] and c[i] >= (o1 - abs(o1 - c1) * 0.15))
                if is_pin: sc += 3
                elif is_eng: sc += 2
                elif c[i] > o[i] and at_e21 and ar >= 0.9: sc += 1

            if sc >= min_score and rv <= 70:
                rr = 3.0 if sc >= 6 else 2.5
                if ar >= 1.2: rr += 0.3
                sig[i] = 1
                slp[i] = (av / pip_val) * 1.4 + 10.0
                rrv[i] = rr
                sname[i] = 'ADAPTIVE_PULLBACK_BUY'
                conviction[i] = sc
                last_bar = i

    return sig, slp, rrv, sname, conviction, ind

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

def test_multi_asset_symbol(symbol: str, period: str = '2y', interval: str = '1h'):
    print(f"\nFetching data for {symbol} ({interval}, {period})...")
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 200:
        # Fallback to daily data if hourly not available for requested period
        df = yf.download(symbol, period='5y', interval='1d', progress=False)
        interval = '1d'

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)
    c = df['Close'].values
    h = df['High'].values
    l = df['Low'].values
    o = df['Open'].values
    n = len(c)

    pip_val = PIP_MAP.get(symbol, 0.01)
    sig, slp, rrv, sname, conviction, ind = gen_champion_signals(c, h, l, o, n, symbol, pip_val)
    atr14 = ind['atr14']

    bal = 1000.0
    pk = 1000.0
    max_dd = 0.0
    trades = []
    stats = {}
    pos: Position = None
    comm_rate = 0.0002  # 0.02% trading cost

    for i in range(100, n):
        if pos:
            done = False
            exit_price = c[i]
            av = max(atr14[i], pip_val * 10)

            if h[i] > pos.hwm:
                pos.hwm = h[i]

            if not pos.trail_on and (h[i] - pos.entry) >= 1.4 * pos.sl_pts * pip_val:
                pos.trail_on = True

            if pos.trail_on:
                new_sl = pos.hwm - 2.4 * av
                if new_sl > pos.sl:
                    pos.sl = new_sl

            if l[i] <= pos.sl:
                exit_price = pos.sl
                done = True
            elif h[i] >= pos.tp and not pos.trail_on:
                exit_price = pos.tp
                done = True

            if done:
                pnl_pct = (exit_price - pos.entry) / pos.entry - comm_rate
                net_pnl = bal * 0.05 * pnl_pct * 10  # 5% risk sizing
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

        if pos is None and sig[i] == 1:
            sl_dist = slp[i]
            if sl_dist > 0:
                entry = c[i]
                sl = entry - sl_dist * pip_val
                tp = entry + sl_dist * rrv[i] * pip_val
                pos = Position(
                    entry=entry,
                    sl=sl,
                    tp=tp,
                    lot=0.01,
                    sname=sname[i],
                    conviction=conviction[i],
                    trail_on=False,
                    hwm=entry,
                    sl_pts=sl_dist
                )

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-9

    pf = gross_win / gross_loss
    wr = len(wins) / max(len(pnls), 1) * 100.0
    pnl_pct = (bal - 1000.0) / 10.0

    return dict(
        symbol=symbol,
        interval=interval,
        bars=n,
        final=bal,
        pnl=bal - 1000.0,
        pct=pnl_pct,
        trades=len(trades),
        wr=wr,
        pf=pf,
        maxdd=max_dd
    )

def main():
    print("=" * 80)
    print("🌍 MULTI-ASSET SYMBOL STRESS TEST — CHAMPION ENGINE v22")
    print("=" * 80)

    test_symbols = [
        ('BTC-USD', 'Crypto (Bitcoin)'),
        ('EURUSD=X', 'Forex (EUR/USD)'),
        ('SPY', 'Equity Index (S&P 500 ETF)'),
        ('CL=F', 'Commodity (Crude Oil)'),
        ('NVDA', 'Tech Stock (Nvidia)'),
        ('AAPL', 'Bluechip Stock (Apple)')
    ]

    results = []
    for sym, asset_type in test_symbols:
        try:
            res = test_multi_asset_symbol(sym, period='2y', interval='1h')
            res['type'] = asset_type
            results.append(res)
        except Exception as e:
            print(f"Error testing {sym}: {e}")

    print("\n" + "=" * 80)
    print(f"{'Asset Class':<22}{'Symbol':<10}{'Interval':>8}{'Bars':>7}{'Final$':>10}{'PnL%':>8}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}")
    print("-" * 80)

    for r in results:
        v_flag = '✅' if r['pnl'] > 0 and r['maxdd'] <= 22.0 else ('🟡' if r['pnl'] > 0 else '❌')
        print(f"{r['type']:<22}{r['symbol']:<10}{r['interval']:>8}{r['bars']:>7}{r['final']:>10,.2f}{r['pct']:>7.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}% {v_flag}")

    # Save summary report
    rdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'core_upgrade')
    os.makedirs(rdir, exist_ok=True)
    rf = os.path.join(rdir, 'MULTI_ASSET_SYMBOLS_STRESS_TEST.md')

    lines = [
        "# 🌍 MULTI-ASSET SYMBOL STRESS TEST REPORT — NEXUS BRAIN v22",
        f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
        "**Objective**: Prove zero overfitting across diverse asset classes (Crypto, Forex, Indices, Commodities, Tech Stocks).",
        "\n---\n## Multi-Asset Performance Matrix",
        "| Asset Class | Symbol | Timeframe | Bars | Final$ | PnL% | Profit Factor | Max DD | Trades | Win Rate | Status |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for r in results:
        v_flag = '✅' if r['pnl'] > 0 and r['maxdd'] <= 22.0 else ('🟡' if r['pnl'] > 0 else '❌')
        lines.append(f"| **{r['type']}** | `{r['symbol']}` | {r['interval']} | {r['bars']} | ${r['final']:,.2f} | {r['pct']:+.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {v_flag} |")

    with open(rf, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n📄 Saved Multi-Asset Stress Test Report to: {rf}")

if __name__ == '__main__':
    main()
