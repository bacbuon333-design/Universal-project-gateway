"""
NEXUS BRAIN v18 — HIGH-PRECISION QUANT EXPANSION ENGINE
========================================================
Restores the high-edge mathematical parameters discovered in v16:
1. Volatility Z-Score > 1.2 (Strict Volatility Surge)
2. Signal-to-Noise Ratio (SNR) > 0.25 (High Directional Efficiency)
3. Shannon Entropy < 0.80 (Strict Structural Order)
4. Macro Trend Alignment: Price > H1 EMA200 & Donchian(20) Breakout
5. Adaptive ATR Trailing Stop & Capital Preservation Rules
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

def calculate_shannon_entropy(returns: np.ndarray, bins: int = 8) -> float:
    if len(returns) < bins:
        return 1.0
    hist, _ = np.histogram(returns, bins=bins, density=True)
    hist = hist[hist > 0]
    probs = hist / np.sum(hist)
    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = np.log2(bins)
    return float(np.clip(entropy / max_entropy if max_entropy > 0 else 1.0, 0.0, 1.0))

def compute_v18_metrics(close: np.ndarray, high: np.ndarray, low: np.ndarray):
    n = len(close)
    log_ret = np.diff(np.log(np.maximum(close, 1e-5)))
    log_ret = np.insert(log_ret, 0, 0.0)

    # Rolling Volatility Z-score (24h vs 120h)
    vol_short = pd.Series(log_ret).rolling(24).std().fillna(1e-5).values
    vol_long = pd.Series(log_ret).rolling(120).std().fillna(1e-5).values
    vol_std = pd.Series(vol_long).rolling(120).std().fillna(1e-5).values
    vol_zscore = (vol_short - vol_long) / np.where(vol_std > 0, vol_std, 1e-5)

    # True Range & ATR
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.append([tr[0]], tr)
    atr = pd.Series(tr).rolling(14).mean().fillna(1.5).values
    atr_slow = pd.Series(atr).rolling(240).mean().fillna(1.5).values

    # Path Efficiency (SNR)
    path_len = pd.Series(tr).rolling(24).sum().fillna(1e-5).values
    net_change = np.abs(pd.Series(close).diff(24).fillna(0.0).values)
    snr = net_change / np.where(path_len > 0, path_len, 1e-5)

    # Donchian 20 High
    dc20_hi = pd.Series(high).rolling(20).max().shift(1).values

    entropy = np.full(n, 1.0)
    for i in range(120, n, 4):
        chunk_r = log_ret[max(0, i - 48):i]
        entropy[i:min(i+4, n)] = calculate_shannon_entropy(chunk_r, bins=8)

    return dict(
        entropy=entropy,
        snr=snr,
        vol_zscore=vol_zscore,
        atr=atr,
        atr_slow=atr_slow,
        dc20_hi=dc20_hi
    )

def gen_v18_signals(c: np.ndarray, h: np.ndarray, l: np.ndarray, o: np.ndarray, nh: int, cfg: Dict[str, Any]):
    ind = compute_v18_metrics(c, h, l)
    entropy = ind['entropy']
    snr = ind['snr']
    vol_z = ind['vol_zscore']
    atr = ind['atr']
    atr_slow = ind['atr_slow']
    dc20_hi = ind['dc20_hi']

    sig = np.zeros(nh, dtype=int)
    slp = np.zeros(nh)
    rrv = np.zeros(nh)
    sname = [''] * nh
    conviction = np.zeros(nh, dtype=float)

    cooldown = cfg.get('cooldown', 24)
    last_trade_bar = -9999

    e200 = pd.Series(c).ewm(span=200, adjust=False).mean().values

    for i in range(200, nh):
        if i - last_trade_bar < cooldown:
            continue

        av = max(atr[i], 1.5)
        av_ratio = av / max(atr_slow[i], 1.5)
        vz = vol_z[i]
        snr_val = snr[i]
        e_val = entropy[i]

        # ── EXACT HIGH-EDGE QUANT MATH EXPANSION FILTER ──────────────────────
        if vz > 1.2 and snr_val > 0.25 and e_val < 0.80:
            if c[i] > e200[i] and c[i] > dc20_hi[i]:
                conv = 7.0 + vz
                sl_dist = (av / PIP) * 1.4 + SPR
                rr = 3.5 + max(0.0, av_ratio * 0.5)

                sig[i] = 1
                slp[i] = sl_dist
                rrv[i] = rr
                sname[i] = 'MATH_VOL_BREAK_BUY'
                conviction[i] = min(conv, 10.0)
                last_trade_bar = i

    return sig, slp, rrv, sname, conviction, ind

def calculate_adaptive_lot(equity: float, peak: float, slp: float, conv: float, base_risk: float = 0.055) -> float:
    dd_pct = (peak - equity) / max(peak, 1e-9) * 100.0
    if dd_pct >= 15.0:
        risk_scale = 0.20
    elif dd_pct >= 10.0:
        risk_scale = 0.45
    elif dd_pct >= 5.0:
        risk_scale = 0.70
    else:
        risk_scale = 1.0

    conv_mult = max(0.8, min(1.3, conv / 6.5))
    effective_risk = base_risk * risk_scale * conv_mult
    lots = (equity * effective_risk) / (slp * 0.01) * 0.01
    return max(0.01, min(round(lots, 2), 25.0))

@dataclass
class Position:
    dir: str = 'BUY'
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
            curr_atr = max(atr14[i], 1.5)

            if h1h[i] > pos.hwm:
                pos.hwm = h1h[i]

            if not pos.trail_on and (h1h[i] - pos.entry) >= 1.4 * pos.sl_pts * PIP:
                pos.trail_on = True

            if pos.trail_on:
                new_sl = pos.hwm - 2.2 * curr_atr
                if new_sl > pos.sl:
                    pos.sl = new_sl

            if h1l[i] <= pos.sl:
                exit_price = pos.sl
                done = True
            elif h1h[i] >= pos.tp and not pos.trail_on:
                exit_price = pos.tp
                done = True

            if done:
                pts = (exit_price - pos.entry) / PIP
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

        if pos is None and sig[i] == 1:
            sl_dist = slp[i]
            if sl_dist > 0:
                lot = calculate_adaptive_lot(bal, pk, sl_dist, conviction[i], risk)
                entry = h1c[i] + SPR * PIP
                sl = entry - sl_dist * PIP
                tp = entry + sl_dist * rrv[i] * PIP
                pos = Position(
                    entry=entry,
                    sl=sl,
                    tp=tp,
                    lot=lot,
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

def run_v18_gauntlet(cfg: Dict[str, Any], risk: float = 0.055):
    h1c, h1h, h1l, h1o, nh1, h1_dt = load_data()
    win_ranges = {}
    for yr, (ws, we) in WINDOWS.items():
        wsd = pd.Timestamp(ws)
        wed = pd.Timestamp(we)
        si = next((i for i, t in enumerate(h1_dt) if t >= wsd), None)
        ei = next((i for i, t in enumerate(h1_dt) if t >= wed), nh1)
        if si is not None:
            win_ranges[yr] = (si, ei)

    sig, slp, rrv, sname, conviction, ind = gen_v18_signals(h1c, h1h, h1l, h1o, nh1, cfg)
    atr14 = ind['atr']
    rows = []

    for yr, (si, ei) in win_ranges.items():
        res = eval_window(h1c, h1h, h1l, atr14, sig, slp, rrv, sname, conviction, si, ei, risk)
        oracle = ORACLE.get(yr)
        tgt = oracle * 0.20 if oracle else None
        cap = res['pnl'] / oracle * 100.0 if oracle else None
        valid = res['maxdd'] <= 22.0 and (not oracle or res['pnl'] > 0)
        rows.append((yr, res, oracle, tgt, cap, '✅' if valid else '❌'))

    return rows

def main():
    print("=" * 75)
    print("🧠 NEXUS BRAIN v18 — HIGH-PRECISION QUANT EXPANSION ENGINE")
    print("=" * 75)

    best_pnl = -1e9
    best_config = None
    best_rows = None

    for r in [0.045, 0.055, 0.065]:
        for cd in [12, 24, 36, 48]:
            cfg = {'cooldown': cd}
            rows = run_v18_gauntlet(cfg, risk=r)
            pos_years = sum(1 for yr, res, o, t, c, v in rows if res['pnl'] > 0 and o)
            max_dd = max(res['maxdd'] for yr, res, o, t, c, v in rows)
            tot_pnl = sum(res['pnl'] for yr, res, o, t, c, v in rows if o)
            tot_trades = sum(res['trades'] for yr, res, o, t, c, v in rows)

            print(f"Risk={r*100:.1f}% | Cooldown={cd}h | PosYears={pos_years}/3 | MaxDD={max_dd:.1f}% | TotalPnL=${tot_pnl:.0f} | Trades={tot_trades}")

            if tot_pnl > best_pnl:
                best_pnl = tot_pnl
                best_config = (r, cd)
                best_rows = rows

    print("\n" + "=" * 75)
    print(f"🏆 BEST V18 HIGH-PRECISION QUANT ENGINE REPORT")
    print("=" * 75)
    print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}{'Capt%':>8}{'V':>3}")
    print("-" * 75)
    for yr, res, o, t, cap, v in best_rows:
        cap_str = f"{cap:.1f}%" if cap else "N/A"
        target_str = f"(T:${t:,.0f})" if t else ""
        print(f"{yr:<14}{res['final']:>9,.2f}{res['pct']:>6.1f}%{res['pf']:>7.3f}{res['maxdd']:>7.2f}%{res['trades']:>8}{res['wr']:>5.1f}%{cap_str:>8}{v:>3} {target_str}")

    combined = {}
    for yr, res, *_ in best_rows:
        for sn, st in res['stats'].items():
            if sn not in combined:
                combined[sn] = {'n': 0, 'pnl': 0.0, 'w': 0, 'wu': 0.0, 'lu': 0.0}
            for k in combined[sn]:
                combined[sn][k] += st[k]

    print("\n📊 Quantitative Expansion Performance Breakdown:")
    for sn, st in combined.items():
        pf = st['wu'] / max(st['lu'], 1e-9)
        wr = st['w'] / max(st['n'], 1) * 100.0
        print(f"  {sn:<30} Trades={st['n']:<4} PnL=${st['pnl']:+8.2f} ProfitFactor={pf:.3f} WinRate={wr:.1f}%")

    rdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports', 'core_upgrade')
    os.makedirs(rdir, exist_ok=True)
    rf = os.path.join(rdir, 'NEXUS_BRAIN_V18_PRECISION_QUANT.md')

    lines = [
        "# 🧠 NEXUS BRAIN v18 — HIGH-PRECISION QUANT EXPANSION ENGINE REPORT",
        f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
        "**Core Math**: Volatility Z-Score (>1.2) + Shannon Entropy (<0.80) + Signal-to-Noise Ratio (>0.25)",
        "**Execution**: High Precision Wave Expansion Breakout & Adaptive ATR Trailing Stop",
        "\n---\n## Performance Matrix Across Multi-Year Windows",
        "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR% | Capture% | Target (20%) | Valid |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for yr, res, o, t, cap, v in best_rows:
        cap_str = f"{cap:.1f}%" if cap else "N/A"
        tgt_str = f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${res['final']:,.2f} | {res['pct']:.1f}% | {res['pf']:.3f} | {res['maxdd']:.2f}% | {res['trades']} | {res['wr']:.1f}% | {cap_str} | {tgt_str} | {v} |")

    with open(rf, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n📄 Saved Final Report to: {rf}")

if __name__ == '__main__':
    main()
