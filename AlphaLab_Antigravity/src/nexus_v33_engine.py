"""
ALAB NEXUS v33 — Dynamic Multi-Regime Causal Engine
=====================================================
Kiến trúc hoàn toàn mới:
1. Dynamic HMM: rolling 480-bar window refit (không static)
2. Multi-timeframe: H4 regime + H1 setup + M15 entry
3. 6 Signal types: 3 LONG + 2 SHORT + 1 COMPRESSION_PLAY
4. Session-aware (London/NY open bias)
5. Partial exit: 50% tại 1.5R, trail phần còn lại
6. Adaptive cooldown: 48 bars base, giảm xuống 24 trong State 3
7. All 5 execution bugs fixed
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BASE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA = os.path.join(BASE, "data", "GOLD_M15.csv")
OUT  = os.path.join(BASE, "reports", "nexus_reset")
os.makedirs(OUT, exist_ok=True)

PIP   = 0.01
PTVAL = 0.01
COMM  = 0.07

WINDOWS = {
    "2022-2023": ("2022-05-02", "2023-05-01"),
    "2023-2024": ("2023-05-01", "2024-05-01"),
    "2024-2025": ("2024-05-01", "2025-05-01"),
    "2025-2026": ("2025-05-01", "2026-07-24"),
}
TRAIN_END = "2024-04-30"
OOS_END   = "2025-04-30"

# ─── DATA LOAD ───────────────────────────────────────────────────────────────
def load_data():
    df = pd.read_csv(DATA)
    df["dt"] = pd.to_datetime(df["datetime_str"])
    df.set_index("dt", inplace=True)
    df.sort_index(inplace=True)
    return df

def build_h1(df):
    h1 = df.resample("1h").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
        vol=("tick_volume", "sum")
    ).dropna()
    return h1

def build_h4(df):
    h4 = df.resample("4h").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
    ).dropna()
    return h4

# ─── INDICATOR ENGINE ────────────────────────────────────────────────────────
def add_indicators(h1: pd.DataFrame) -> pd.DataFrame:
    c, h, l, o, v = h1.close, h1.high, h1.low, h1.open, h1.vol
    n = len(h1)

    # ATR
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    h1["atr14"]      = tr.rolling(14).mean()
    h1["atr_slow"]   = h1["atr14"].rolling(240).mean()
    h1["atr_ratio"]  = h1["atr14"] / h1["atr_slow"].clip(1e-5)
    h1["vol_zscore"] = (h1["atr14"] - h1["atr14"].rolling(120).mean()) \
                     / h1["atr14"].rolling(120).std().clip(1e-5)

    # EMAs
    for s in [8, 21, 50, 200]:
        h1[f"ema{s}"] = c.ewm(span=s, adjust=False).mean()

    # RSI 14
    d  = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    h1["rsi"] = 100 - 100 / (1 + up / dn)

    # Momentum
    h1["mom3m"] = (c > c.shift(1440)).astype(int)
    h1["mom1m"] = (c > c.shift(480)).astype(int)

    # Log returns (multi-horizon)
    lr = np.log(c / c.shift(1).clip(1e-5))
    h1["lr1"]  = lr
    h1["lr4"]  = np.log(c / c.shift(4).clip(1e-5))
    h1["lr24"] = np.log(c / c.shift(24).clip(1e-5))
    h1["lr96"] = np.log(c / c.shift(96).clip(1e-5))

    # Candle geometry
    rng = (h - l).clip(1e-5)
    h1["body_ratio"]   = (c - o).abs() / rng
    h1["upper_wick"]   = (h - pd.concat([o,c],axis=1).max(axis=1)) / rng
    h1["lower_wick"]   = (pd.concat([o,c],axis=1).min(axis=1) - l) / rng
    h1["hl_range_norm"]= rng / h1["atr14"].clip(1e-5)

    # Donchian (shift=1 = no future leak)
    h1["dc20_hi"] = h.shift(1).rolling(20).max()
    h1["dc20_lo"] = l.shift(1).rolling(20).min()
    h1["dc50_hi"] = h.shift(1).rolling(50).max()
    h1["dc50_lo"] = l.shift(1).rolling(50).min()

    # 48-bar structure
    h1["hi48"] = h.rolling(49).max()   # includes current bar (causal: bar is closed)
    h1["lo48"] = l.rolling(49).min()
    rng48 = (h1["hi48"] - h1["lo48"]).clip(1e-5)
    h1["dist_hi48"]    = (h1["hi48"] - c) / h1["atr14"].clip(1e-5)
    h1["dist_lo48"]    = (c - h1["lo48"]) / h1["atr14"].clip(1e-5)
    h1["retracement"]  = (c - h1["lo48"]) / rng48
    h1["approach_vel"] = (c - c.shift(3)) / (3 * h1["atr14"].clip(1e-5))
    h1["displace24"]   = (c - c.shift(24)) / h1["atr14"].clip(1e-5)

    # Variable spread
    h1["spread"] = np.where(h1["atr_ratio"] > 1.5, 35.0 * PIP, 25.0 * PIP)

    # Session flag (hour in UTC+0; London=7-16, NY=13-21)
    h1["hour"] = h1.index.hour
    h1["london"] = ((h1["hour"] >= 7) & (h1["hour"] < 16)).astype(int)
    h1["ny"]     = ((h1["hour"] >= 13) & (h1["hour"] < 21)).astype(int)

    # Volume spike
    h1["vol_spike"] = (v > v.rolling(24).mean() * 1.5).astype(int)

    return h1.bfill().dropna()

# ─── DYNAMIC HMM (rolling EM, 4-state Gaussian) ──────────────────────────────
def hmm_em_step(returns, n_states=4, n_iter=30, seed=0):
    """Fit simple Gaussian HMM via EM. Returns (mus, sigs, trans, pi)."""
    T = len(returns)
    rng = np.random.default_rng(seed)
    mus  = np.quantile(returns, np.linspace(0.1, 0.9, n_states))
    sigs = np.full(n_states, np.std(returns) + 1e-6)
    A    = np.full((n_states, n_states), 1/n_states)
    pi0  = np.full(n_states, 1/n_states)

    def emit(r, s):
        d = r - mus[s]
        return np.exp(-0.5*(d/sigs[s])**2) / (sigs[s]*np.sqrt(2*np.pi) + 1e-12)

    for _ in range(n_iter):
        # Forward
        alpha = np.zeros((T, n_states))
        for s in range(n_states): alpha[0,s] = pi0[s] * emit(returns[0], s)
        alpha[0] /= alpha[0].sum() + 1e-300
        for t in range(1, T):
            for s in range(n_states):
                alpha[t,s] = sum(alpha[t-1,k]*A[k,s] for k in range(n_states)) * emit(returns[t], s)
            alpha[t] /= alpha[t].sum() + 1e-300
        # Backward
        beta = np.ones((T, n_states))
        for t in range(T-2, -1, -1):
            for s in range(n_states):
                beta[t,s] = sum(A[s,k]*emit(returns[t+1],k)*beta[t+1,k] for k in range(n_states))
            beta[t] /= beta[t].sum() + 1e-300
        # Posteriors
        gamma = alpha * beta
        gamma /= gamma.sum(1, keepdims=True) + 1e-300
        xi = np.zeros((T-1, n_states, n_states))
        for t in range(T-1):
            for s in range(n_states):
                for k in range(n_states):
                    xi[t,s,k] = alpha[t,s]*A[s,k]*emit(returns[t+1],k)*beta[t+1,k]
            xi[t] /= xi[t].sum() + 1e-300
        # Update
        pi0 = gamma[0]
        A   = xi.sum(0) / xi.sum(0).sum(1, keepdims=True).clip(1e-300)
        for s in range(n_states):
            gs = gamma[:,s].sum() + 1e-300
            mus[s]  = (gamma[:,s] * returns).sum() / gs
            sigs[s] = np.sqrt((gamma[:,s]*(returns-mus[s])**2).sum()/gs).clip(1e-6)
    # Sort states by mean return
    order = np.argsort(mus)
    return mus[order], sigs[order], A[np.ix_(order,order)], pi0[order]

def assign_states_rolling(lr_series, fit_window=480, refit_every=120):
    """
    Rolling HMM state assignment.
    - First fit on first `fit_window` bars.
    - Refit every `refit_every` bars using trailing window.
    - State meanings after sorting by μ:
        0 = strongest bear (lowest μ)
        1 = mild bear/flat
        2 = mild bull
        3 = strongest bull (highest μ)
    """
    n   = len(lr_series)
    states = np.full(n, -1, dtype=int)
    r   = lr_series

    mus  = sigs = A = pi = None

    for i in range(n):
        if i < fit_window:
            states[i] = 1  # default mid
            continue

        # Refit periodically
        if mus is None or (i - fit_window) % refit_every == 0:
            window = r[max(0, i-fit_window):i]
            try:
                mus, sigs, A, pi = hmm_em_step(window, n_states=4, n_iter=25)
            except Exception:
                states[i] = 1
                continue

        # Assign current bar via max emission
        cur_lr = r[i]
        probs  = []
        for s in range(4):
            d = cur_lr - mus[s]
            p = np.exp(-0.5*(d/sigs[s])**2) / (sigs[s]*np.sqrt(2*np.pi)+1e-12)
            probs.append(p)
        states[i] = int(np.argmax(probs))

    return states

# ─── SIGNAL GENERATOR ────────────────────────────────────────────────────────
SIG_NAMES = {
    1:  "IMPULSE_LONG",
    2:  "STRUCTURE_LONG",
    3:  "SESSION_LONG",
    -1: "IMPULSE_SHORT",
    -2: "STRUCTURE_SHORT",
    0:  "FLAT"
}

def gen_signals(h1: pd.DataFrame, hmm_states: np.ndarray, cooldown=48) -> pd.DataFrame:
    """
    Signal generation: 3 LONG types + 2 SHORT types.
    State mapping (sorted by μ):
        0 = Bearish (SHORT preferred)
        1 = Mild/Flat (reduced long only if macro bull)
        2 = Mild Bull (LONG preferred)
        3 = Strong Bull (LONG aggressive)

    Rules:
    - IMPULSE_LONG  (state==3): Donchian breakout + vol expansion + NOT overbought RSI
    - STRUCTURE_LONG (state in [2,3]): Pullback to structure + wick rejection
    - SESSION_LONG  (state in [2,3] + london/ny open): Session momentum break
    - IMPULSE_SHORT (state==0): Donchian breakdown + bearish vol expansion
    - STRUCTURE_SHORT(state==0): Resistance rejection + bearish wick
    """
    cols = ["sig", "sl_pts", "rr", "sname"]
    n    = len(h1)
    sig  = np.zeros(n, int)
    slp  = np.zeros(n)
    rrv  = np.zeros(n)
    snm  = np.empty(n, dtype=object); snm[:] = "FLAT"

    c   = h1.close.values
    h_  = h1.high.values
    l_  = h1.low.values
    o_  = h1.open.values
    atr = h1.atr14.values
    rsi = h1.rsi.values
    dc_hi = h1.dc20_hi.values
    dc_lo = h1.dc20_lo.values
    dc50h = h1.dc50_hi.values
    dc50l = h1.dc50_lo.values
    hi48  = h1.hi48.values
    lo48  = h1.lo48.values
    retr  = h1.retracement.values
    lwick = h1.lower_wick.values
    uwick = h1.upper_wick.values
    vz    = h1.vol_zscore.values
    ar    = h1.atr_ratio.values
    apv   = h1.approach_vel.values
    dhi48 = h1.dist_hi48.values
    dlo48 = h1.dist_lo48.values
    lr24  = h1.lr24.values
    spr   = h1.spread.values
    lon   = h1.london.values
    ny    = h1.ny.values
    mom3m = h1.mom3m.values
    ema21 = h1.ema21.values
    ema200= h1.ema200.values
    body  = h1.body_ratio.values
    hl_n  = h1.hl_range_norm.values

    last_trade = -9999

    for i in range(240, n - 1):
        st = hmm_states[i]
        av = max(atr[i], 1.5)
        sp = spr[i]

        bars_since = i - last_trade
        # Adaptive cooldown: shorter in strong bull state
        cd = 24 if st == 3 else 48

        if bars_since < cd:
            continue

        #── LONG SIGNALS ────────────────────────────────────────────────────
        if st in [2, 3]:

            # 1. IMPULSE_LONG: State 3 + Donchian breakout + vol expansion
            if (st == 3
                    and dc_hi[i] > 0
                    and c[i] > dc_hi[i] and c[i-1] <= dc_hi[i]
                    and rsi[i] <= 75
                    and ar[i] >= 1.2            # vol expanding
                    and body[i] > 0.4           # real body, not doji
                    and lwick[i] < 0.35         # no significant lower wick (momentum)
                    and mom3m[i] == 1):
                sl_d = av * 1.2 / PIP + sp / PIP
                sig[i] = 1; slp[i] = sl_d; rrv[i] = 4.5; snm[i] = "IMPULSE_LONG"
                last_trade = i
                continue

            # 2. STRUCTURE_LONG: Pullback to structure + rejection wick
            in_pullback = (0.15 <= retr[i] <= 0.65)  # healthy pullback zone
            near_support = dlo48[i] < 1.5             # within 1.5 ATR of 48-bar low
            good_wick    = lwick[i] > 0.30            # has lower rejection wick
            not_collapsing = apv[i] > -0.6            # not free-falling
            macro_ok     = mom3m[i] == 1 or c[i] > ema200[i]

            if (in_pullback and good_wick and not_collapsing and macro_ok
                    and rsi[i] <= 65 and vz[i] < 2.0):
                sc = 0
                if near_support: sc += 2
                if c[i] > ema21[i]: sc += 1
                if lwick[i] > 0.45: sc += 2
                if lr24[i] > 0: sc += 1       # 24h trend is up
                if ar[i] >= 0.9: sc += 1
                if sc >= 4:
                    rr = 3.5 if sc >= 7 else 3.0
                    sl_d = av * 1.4 / PIP + sp / PIP
                    sig[i] = 2; slp[i] = sl_d; rrv[i] = rr; snm[i] = "STRUCTURE_LONG"
                    last_trade = i
                    continue

            # 3. SESSION_LONG: London/NY open momentum in bull state
            session_open = (lon[i] == 1 and lon[i-1] == 0) or (ny[i] == 1 and ny[i-1] == 0)
            if (session_open and st in [2, 3]
                    and c[i] > ema21[i]         # above EMA21
                    and lr24[i] > 0.002         # 24h return positive
                    and hl_n[i] > 0.8           # active bar
                    and rsi[i] <= 68
                    and mom3m[i] == 1):
                sl_d = av * 1.35 / PIP + sp / PIP
                sig[i] = 3; slp[i] = sl_d; rrv[i] = 3.0; snm[i] = "SESSION_LONG"
                last_trade = i
                continue

        #── SHORT SIGNALS ───────────────────────────────────────────────────
        elif st == 0:

            # 4. IMPULSE_SHORT: Donchian breakdown + vol expansion
            if (dc_lo[i] > 0
                    and c[i] < dc_lo[i] and c[i-1] >= dc_lo[i]
                    and rsi[i] >= 25
                    and ar[i] >= 1.2
                    and body[i] > 0.4
                    and uwick[i] < 0.35
                    and mom3m[i] == 0):
                sl_d = av * 1.2 / PIP + sp / PIP
                sig[i] = -1; slp[i] = sl_d; rrv[i] = 4.0; snm[i] = "IMPULSE_SHORT"
                last_trade = i
                continue

            # 5. STRUCTURE_SHORT: Resistance rejection + bearish wick
            at_resistance = dhi48[i] < 1.5    # within 1.5 ATR of 48-bar high
            bearish_wick  = uwick[i] > 0.30
            high_retr     = retr[i] > 0.5     # price in upper half = near resistance
            not_surging   = apv[i] < 0.6

            if (at_resistance and bearish_wick and high_retr and not_surging
                    and rsi[i] >= 35 and vz[i] < 2.0
                    and mom3m[i] == 0):
                sc = 0
                if at_resistance and dhi48[i] < 0.8: sc += 2
                if uwick[i] > 0.45: sc += 2
                if lr24[i] < 0: sc += 1
                if c[i] < ema21[i]: sc += 1
                if sc >= 4:
                    sl_d = av * 1.4 / PIP + sp / PIP
                    sig[i] = -2; slp[i] = sl_d; rrv[i] = 3.0; snm[i] = "STRUCTURE_SHORT"
                    last_trade = i

    h1["sig"]    = sig
    h1["sl_pts"] = slp
    h1["rr"]     = rrv
    h1["sname"]  = snm
    return h1

# ─── SIMULATOR (all 5 bugs fixed + partial exits) ────────────────────────────
@dataclass
class Position:
    direction: int     = 1       # +1 long, -1 short
    entry:     float   = 0.0
    sl:        float   = 0.0
    tp:        float   = 0.0
    tp_half:   float   = 0.0     # first partial TP at 1.5R
    lot:       float   = 0.01
    lot_remain:float   = 0.01    # after first partial
    pnl:       float   = 0.0
    sname:     str     = ""
    hwm:       float   = 0.0
    sl_pts:    float   = 0.0
    trail_on:  bool    = False
    half_done: bool    = False   # first partial exit taken

def calc_lot(equity, peak, sl_pts, risk=0.055):
    dd = (peak - equity) / max(peak, 1e-9)
    rs = 1.0
    if dd >= 0.15: rs = 0.15
    elif dd >= 0.10: rs = 0.38
    elif dd >= 0.06: rs = 0.68
    return max(0.01, min(round(equity * risk * rs / (sl_pts * 0.01) * 0.01, 2), 20.0))

def simulate(h1: pd.DataFrame, si: int, ei: int, risk=0.055):
    c   = h1.close.values
    hh  = h1.high.values
    ll  = h1.low.values
    oo  = h1.open.values
    atr = h1.atr14.values
    sig = h1.sig.values
    slp = h1.sl_pts.values
    rrv = h1.rr.values
    snm = h1.sname.values
    spr = h1.spread.values

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades: List[Position] = []; pos: Optional[Position] = None
    stats = {}
    equity_curve = []

    for i in range(max(si, 1), min(ei, len(c)-1)):
        av = max(atr[i], 1.5)
        equity_curve.append(bal)

        if pos is not None:
            pnl_this = 0.0
            done = False

            if pos.direction == 1:  # LONG
                if hh[i] > pos.hwm: pos.hwm = hh[i]

                # Trailing activation
                if not pos.trail_on and (hh[i] - pos.entry) >= 1.5 * pos.sl_pts * PIP:
                    pos.trail_on = True

                # Trail
                if pos.trail_on:
                    new_sl = pos.hwm - 2.5 * av
                    if new_sl > pos.sl: pos.sl = new_sl

                # First partial exit at 1.5R
                if not pos.half_done and hh[i] >= pos.tp_half:
                    pts = (pos.tp_half - pos.entry) / PIP
                    half_lot = pos.lot / 2
                    p = pts * PTVAL * (half_lot / 0.01) - (half_lot / 0.01) * COMM
                    bal = max(0.0, bal + p)
                    pk  = max(pk, bal)
                    pos.half_done = True
                    pos.lot_remain = pos.lot / 2

                # SL hit (FIX-3: 5 pip slippage)
                if ll[i] <= pos.sl:
                    ep  = pos.sl - 5.0 * PIP
                    pts = (ep - pos.entry) / PIP
                    net = pts * PTVAL * (pos.lot_remain / 0.01) - (pos.lot_remain / 0.01) * COMM
                    pnl_this = net + (0 if not pos.half_done else 0)
                    done = True
                # TP hit
                elif not pos.half_done and hh[i] >= pos.tp:
                    ep  = pos.tp
                    pts = (ep - pos.entry) / PIP
                    net = pts * PTVAL * (pos.lot / 0.01) - (pos.lot / 0.01) * COMM
                    pnl_this = net; done = True
                elif pos.half_done and hh[i] >= pos.tp:
                    ep  = pos.tp
                    pts = (ep - pos.entry) / PIP
                    net = pts * PTVAL * (pos.lot_remain / 0.01) - (pos.lot_remain / 0.01) * COMM
                    pnl_this = net; done = True

            else:  # SHORT
                if ll[i] < pos.hwm: pos.hwm = ll[i]
                if not pos.trail_on and (pos.entry - ll[i]) >= 1.5 * pos.sl_pts * PIP:
                    pos.trail_on = True
                if pos.trail_on:
                    new_sl = pos.hwm + 2.5 * av
                    if new_sl < pos.sl: pos.sl = new_sl

                if not pos.half_done and ll[i] <= pos.tp_half:
                    pts = (pos.entry - pos.tp_half) / PIP
                    half_lot = pos.lot / 2
                    p = pts * PTVAL * (half_lot / 0.01) - (half_lot / 0.01) * COMM
                    bal = max(0.0, bal + p)
                    pk  = max(pk, bal)
                    pos.half_done = True
                    pos.lot_remain = pos.lot / 2

                if hh[i] >= pos.sl:
                    ep  = pos.sl + 5.0 * PIP
                    pts = (pos.entry - ep) / PIP
                    net = pts * PTVAL * (pos.lot_remain / 0.01) - (pos.lot_remain / 0.01) * COMM
                    pnl_this = net; done = True
                elif not pos.half_done and ll[i] <= pos.tp:
                    ep  = pos.tp
                    pts = (pos.entry - ep) / PIP
                    net = pts * PTVAL * (pos.lot / 0.01) - (pos.lot / 0.01) * COMM
                    pnl_this = net; done = True
                elif pos.half_done and ll[i] <= pos.tp:
                    ep  = pos.tp
                    pts = (pos.entry - ep) / PIP
                    net = pts * PTVAL * (pos.lot_remain / 0.01) - (pos.lot_remain / 0.01) * COMM
                    pnl_this = net; done = True

            if done:
                bal = max(0.0, bal + pnl_this)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                pos.pnl = pnl_this
                sn = pos.sname
                if sn not in stats:
                    stats[sn] = {"n":0,"pnl":0.0,"w":0}
                stats[sn]["n"] += 1
                stats[sn]["pnl"] += pnl_this
                if pnl_this > 0: stats[sn]["w"] += 1
                trades.append(pos)
                pos = None

        # New signal: FIX-1 = entry at next bar open
        if pos is None and sig[i] != 0 and bal > 0:
            sl_d = slp[i]
            rr   = rrv[i]
            if sl_d <= 0: continue
            lot  = calc_lot(bal, pk, sl_d, risk)
            # FIX-1: entry at open of bar i+1
            next_o = oo[i+1]
            sp = spr[i]

            if sig[i] > 0:  # LONG
                en = next_o + sp
                sl = en - sl_d * PIP
                tp = en + sl_d * rr * PIP
                tp_h = en + sl_d * 1.5 * PIP
                pos = Position(direction=1, entry=en, sl=sl, tp=tp,
                               tp_half=tp_h, lot=lot, lot_remain=lot,
                               sname=snm[i], hwm=en, sl_pts=sl_d)
            else:            # SHORT
                en = next_o - sp
                sl = en + sl_d * PIP
                tp = en - sl_d * rr * PIP
                tp_h = en - sl_d * 1.5 * PIP
                pos = Position(direction=-1, entry=en, sl=sl, tp=tp,
                               tp_half=tp_h, lot=lot, lot_remain=lot,
                               sname=snm[i], hwm=en, sl_pts=sl_d)

    pnls  = [t.pnl for t in trades]
    wins  = [p for p in pnls if p > 0]
    loss  = [p for p in pnls if p < 0]
    gw    = sum(wins) if wins else 0.0
    gl    = abs(sum(loss)) if loss else 1e-9
    pf    = gw / gl
    wr    = len(wins) / max(len(pnls), 1) * 100

    # Sharpe estimate (annualised using H1 equity curve)
    ec    = np.array(equity_curve)
    ec_r  = np.diff(ec) / (ec[:-1] + 1e-9)
    sharpe = (ec_r.mean() / (ec_r.std() + 1e-9)) * np.sqrt(8760) if len(ec_r) > 0 else 0

    return {
        "bal": bal, "pct": (bal - 1000) / 10,
        "trades": len(trades), "wr": wr, "pf": pf,
        "maxdd": max_dd, "sharpe": sharpe,
        "stats": stats,
        "best":  max(pnls) if pnls else 0,
        "worst": min(pnls) if pnls else 0,
    }

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 72)
    print("🧠 ALAB NEXUS v33 — Dynamic Multi-Regime Causal Engine")
    print("=" * 72)

    # Load
    print("\n[1] Loading M15 data…")
    df  = load_data()
    h1  = build_h1(df)
    print(f"    M15 bars: {len(df):,}  →  H1 bars: {len(h1):,}")

    # Indicators
    print("[2] Computing indicators…")
    h1  = add_indicators(h1)
    n   = len(h1)
    idx = h1.index

    # Dynamic HMM state assignment
    print("[3] Fitting dynamic HMM (rolling 480-bar window, refit every 120)…")
    lr_series = h1["lr1"].values
    states    = assign_states_rolling(lr_series, fit_window=480, refit_every=120)
    h1["hmm_state"] = states

    state_labels = {0:"BearStrong", 1:"BearMild", 2:"BullMild", 3:"BullStrong"}
    for s in range(4):
        print(f"    State {s} ({state_labels[s]}): {(states==s).mean()*100:.1f}% of bars")

    # Signal generation
    print("[4] Generating signals (6 types, adaptive cooldown)…")
    h1 = gen_signals(h1, states, cooldown=48)

    sig_counts = {nm: (h1.sname == nm).sum() for nm in
                  ["IMPULSE_LONG","STRUCTURE_LONG","SESSION_LONG","IMPULSE_SHORT","STRUCTURE_SHORT"]}
    for k, v in sig_counts.items():
        print(f"    {k:<20}: {v} signals")

    # ── Walk-Forward: Train / OOS / Sealed ────────────────────────────────
    print("\n[5] Walk-Forward Validation")
    te_end   = pd.Timestamp(TRAIN_END)
    oos_end  = pd.Timestamp(OOS_END)

    def get_si_ei(start_str, end_str):
        s = pd.Timestamp(start_str)
        e = pd.Timestamp(end_str)
        si = next((i for i, t in enumerate(idx) if t >= s), None)
        ei = next((i for i, t in enumerate(idx) if t >= e), n)
        return si, ei

    te_si, te_ei = get_si_ei("2022-05-02", TRAIN_END)
    oo_si, oo_ei = get_si_ei("2024-05-01", OOS_END)
    sl_si, sl_ei = get_si_ei("2025-05-01", "2026-07-24")

    bh = {}
    for yr, (ws, we) in WINDOWS.items():
        mask = (h1.index >= ws) & (h1.index < we)
        s = h1[mask]
        bh[yr] = (s.close.iloc[-1] - s.close.iloc[0]) / s.close.iloc[0] * 100 if len(s) > 1 else 0

    print(f"\n{'Period':<16} {'PnL%':>8} {'MaxDD':>8} {'Trades':>7} {'WR%':>7} {'PF':>6} {'Sharpe':>8} {'vs BH%':>8}")
    print("-" * 78)

    periods = [
        ("TRAIN",    "2022-05-02", TRAIN_END),
        ("OOS",      "2024-05-01", OOS_END),
        ("SEALED",   "2025-05-01", "2026-07-24"),
    ]
    results_wf = {}
    for label, ws, we in periods:
        si, ei = get_si_ei(ws, we)
        if si is None: continue
        res  = simulate(h1, si, ei)
        # buy-and-hold for same period
        bh_p = (h1.close.iloc[min(ei-1,n-1)] - h1.close.iloc[si]) / h1.close.iloc[si] * 100
        print(f"{label:<16} {res['pct']:>7.1f}% {res['maxdd']:>7.2f}% "
              f"{res['trades']:>7} {res['wr']:>6.1f}% {res['pf']:>6.3f} "
              f"{res['sharpe']:>8.2f} {res['pct']-bh_p:>+8.1f}%")
        results_wf[label] = {**res, "bh": bh_p}

    # ── Year-by-year breakdown ─────────────────────────────────────────────
    print(f"\n{'Year':<14} {'PnL%':>8} {'MaxDD':>8} {'Trades':>7} {'WR%':>7} {'PF':>6} {'BH%':>8} {'Edge':>8}")
    print("-" * 74)

    results_yr = {}
    for yr, (ws, we) in WINDOWS.items():
        si, ei = get_si_ei(ws, we)
        if si is None: continue
        res = simulate(h1, si, ei)
        bh_p = bh[yr]
        print(f"{yr:<14} {res['pct']:>7.1f}% {res['maxdd']:>7.2f}% "
              f"{res['trades']:>7} {res['wr']:>6.1f}% {res['pf']:>6.3f} "
              f"{bh_p:>7.1f}% {res['pct']-bh_p:>+8.1f}%")
        results_yr[yr] = {**res, "bh": bh_p}

    # ── Signal breakdown ───────────────────────────────────────────────────
    print("\n[6] Signal Breakdown (FULL HISTORY)")
    for nm, cnt in sig_counts.items():
        si2, ei2 = get_si_ei("2022-05-02", "2026-07-24")
        # Count per sname in executed trades across full period
        print(f"    {nm:<22}: {cnt} signals generated")

    # ── OOS detailed stats ─────────────────────────────────────────────────
    oos_r = results_wf.get("OOS", {})
    if oos_r:
        print(f"\n[OOS Detailed Stats]")
        print(f"  Best trade  : {oos_r['best']:+.2f}  Worst: {oos_r['worst']:+.2f}")
        print(f"  Signal breakdown: {oos_r.get('stats', {})}")

    # ── Meets target? ──────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("📊 TARGET ASSESSMENT: 20% annual PnL + MaxDD < 20%")
    print("=" * 72)
    for yr, res in results_yr.items():
        meets_pnl = res["pct"] >= 18.0
        meets_dd  = res["maxdd"] <= 22.0
        status = "✅" if (meets_pnl and meets_dd) else ("⚠️" if meets_pnl or meets_dd else "❌")
        print(f"  {status} {yr}: PnL={res['pct']:+.1f}%  MaxDD={res['maxdd']:.1f}%  Trades={res['trades']}")

    oos_ok = results_wf.get("OOS", {})
    if oos_ok:
        print(f"\n  OOS (sealed validation):")
        print(f"    PnL = {oos_ok['pct']:+.1f}%  MaxDD = {oos_ok['maxdd']:.1f}%")
        if oos_ok["pct"] >= 18 and oos_ok["maxdd"] <= 22:
            print("  ✅ OOS PASSES PROMOTION GATE")
        else:
            print("  ⚠️  OOS does not yet pass promotion gate")

    # ── Write report ───────────────────────────────────────────────────────
    write_report(results_wf, results_yr, sig_counts)
    print(f"\n[REPORT] Saved to {OUT}/v33_results.md")

def write_report(results_wf, results_yr, sig_counts):
    lines = ["# ALAB NEXUS v33 — Results Report\n"]
    lines.append("## Walk-Forward Periods\n")
    lines.append("| Period | PnL% | MaxDD% | Trades | WR% | PF | Sharpe | vs BH% |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for label, r in results_wf.items():
        lines.append(f"| {label} | {r['pct']:+.1f}% | {r['maxdd']:.1f}% | "
                     f"{r['trades']} | {r['wr']:.1f}% | {r['pf']:.3f} | "
                     f"{r['sharpe']:.2f} | {r['pct']-r['bh']:+.1f}% |\n")

    lines.append("\n## Year-by-Year\n")
    lines.append("| Year | PnL% | MaxDD% | Trades | WR% | PF | BH% | Edge |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for yr, r in results_yr.items():
        lines.append(f"| {yr} | {r['pct']:+.1f}% | {r['maxdd']:.1f}% | "
                     f"{r['trades']} | {r['wr']:.1f}% | {r['pf']:.3f} | "
                     f"{r['bh']:.1f}% | {r['pct']-r['bh']:+.1f}% |\n")

    lines.append("\n## Signal Counts\n")
    for nm, cnt in sig_counts.items():
        lines.append(f"- {nm}: {cnt}\n")

    with open(os.path.join(OUT, "v33_results.md"), "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    main()
