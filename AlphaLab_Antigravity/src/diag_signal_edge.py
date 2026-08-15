"""
DIAGNOSTIC: Kiểm tra data consistency và signal edge trước khi build engine mới
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA = os.path.join(BASE, "data", "GOLD_M15.csv")

# ── 1. DATA AUDIT ─────────────────────────────────────────────────────────────
print("="*65)
print("DIAGNOSTIC 1: DATA INTEGRITY")
print("="*65)
df = pd.read_csv(DATA)
df['dt'] = pd.to_datetime(df['datetime_str'])
df.set_index('dt', inplace=True)
df.sort_index(inplace=True)

print(f"M15 rows       : {len(df):,}")
print(f"Start          : {df.index[0]}")
print(f"End            : {df.index[-1]}")
dur_h = (df.index[-1] - df.index[0]).total_seconds() / 3600
print(f"Duration hours : {dur_h:.0f}")
print(f"Expected H1 bars (dur/1h): {dur_h:.0f}")

# Method A: resample
h1_a = df.resample('1h').agg(
    open=('open','first'), high=('high','max'),
    low=('low','min'), close=('close','last'),
    vol=('tick_volume','sum')
).dropna()
print(f"\nMethod A resample('1h').dropna() -> {len(h1_a):,} H1 bars")

# Method B: manual 4-bar aggregation (correct for M15→H1)
n = len(df)
c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
seg = n // 4
h1c = np.array([c[i*4+3] for i in range(seg)])
h1h = np.array([max(h[i*4:i*4+4]) for i in range(seg)])
h1l = np.array([min(l[i*4:i*4+4]) for i in range(seg)])
h1o = np.array([o[i*4] for i in range(seg)])
h1dt = [df.index[i*4+3] for i in range(seg)]
print(f"Method B 4-bar group -> {seg:,} H1 bars (CORRECT: 99999//4={seg})")

print("\n✅ Use Method B (manual 4-bar) — resample creates NaN-filled gaps → wrong count")

# ── 2. SIGNAL EDGE VALIDATION (simple forward return test) ───────────────────
print("\n" + "="*65)
print("DIAGNOSTIC 2: RAW SIGNAL EDGE (forward 24h return)")
print("="*65)

# Build simple H1 from Method B
h1 = pd.DataFrame({
    'close': h1c, 'high': h1h, 'low': h1l, 'open': h1o
}, index=h1dt)
N = len(h1)

c_ = h1.close.values; h_ = h1.high.values; l_ = h1.low.values; o_ = h1.open.values

# ATR14
tr  = np.maximum(h_[1:]-l_[1:], np.maximum(abs(h_[1:]-c_[:-1]), abs(l_[1:]-c_[:-1])))
tr  = np.insert(tr, 0, tr[0])
atr = pd.Series(tr).rolling(14).mean().bfill().values

# EMA
ema21  = pd.Series(c_).ewm(span=21,  adjust=False).mean().values
ema200 = pd.Series(c_).ewm(span=200, adjust=False).mean().values

# RSI
d  = pd.Series(c_).diff()
up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
rsi = (100 - 100/(1+up/dn)).values

# Momentum 3m
mom3m = np.zeros(N, bool)
for i in range(1440, N): mom3m[i] = c_[i] > c_[i-1440]

# Donchian 20 (shift=1)
dc20h = pd.Series(h_).shift(1).rolling(20).max().values
dc20l = pd.Series(l_).shift(1).rolling(20).min().values

# 48-bar structure
hi48 = pd.Series(h_).rolling(49).max().values
lo48 = pd.Series(l_).rolling(49).min().values

# Forward returns
fwd24 = np.full(N, np.nan)
fwd24[:-24] = c_[24:] - c_[:-24]  # raw price return 24h later

# Test each simple condition on TRAINING data only (2022-05-02 to 2024-04-30)
train_start = pd.Timestamp('2022-05-02')
train_end   = pd.Timestamp('2024-04-30')
mask_tr = [(t >= train_start and t < train_end) for t in h1dt]
mask_tr = np.array(mask_tr)

tests = {
    'macro_bull_any'   : (mom3m & (c_ > ema200)),
    'macro_bull_pullback': (mom3m & (c_ > ema200) & (l_ <= ema21) & (c_ > ema21) & (rsi <= 65)),
    'dc20_breakout_bull': (mom3m & (c_ > ema200) & (c_ > dc20h) & (rsi <= 72)),
    'macro_bear_any'   : (~mom3m & (c_ < ema200)),
    'dc20_breakdown_bear': (~mom3m & (c_ < ema200) & (c_ < dc20l) & (rsi >= 28)),
    'near_lo48_bull'   : (mom3m & (c_ > ema200) & ((c_ - lo48)/(atr+1e-5) < 1.5)),
    'near_hi48_bear'   : (~mom3m & (c_ < ema200) & ((hi48 - c_)/(atr+1e-5) < 1.5)),
    'unconditional_long': np.ones(N, bool),
}

print(f"\n{'Condition':<28} {'N':>5} {'AvgFwd24h':>11} {'WinRate':>8} {'t-stat':>8}")
print("-" * 65)
for name, cond in tests.items():
    mask = cond & mask_tr & ~np.isnan(fwd24)
    fwds = fwd24[mask]
    if len(fwds) < 10: continue
    wr   = (fwds > 0).mean() * 100
    avg  = fwds.mean()
    std  = fwds.std()
    t    = avg / (std / np.sqrt(len(fwds))) if std > 0 else 0
    print(f"{name:<28} {len(fwds):>5} {avg:>+11.3f} {wr:>7.1f}% {t:>+8.2f}")

# ── 3. TEST SHORT EDGE ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print("DIAGNOSTIC 3: SHORT SIGNAL EDGE (forward -24h return as profit)")
print("="*65)
fwd24_short = -fwd24  # for short: profit = -price_change

for name, cond in [
    ('dc20_breakdown_bear', tests['dc20_breakdown_bear']),
    ('near_hi48_bear',      tests['near_hi48_bear']),
    ('macro_bear_any',      tests['macro_bear_any']),
]:
    mask = cond & mask_tr & ~np.isnan(fwd24)
    fwds = fwd24_short[mask]
    if len(fwds) < 5: continue
    wr   = (fwds > 0).mean() * 100
    avg  = fwds.mean()
    std  = fwds.std()
    t    = avg / (std / np.sqrt(len(fwds))) if std > 0 else 0
    print(f"SHORT {name:<22} {len(fwds):>5} {avg:>+11.3f} {wr:>7.1f}% {t:>+8.2f}")

# ── 4. YEAR DRIFT ──────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("DIAGNOSTIC 4: UNCONDITIONAL DRIFT PER WINDOW")
print("="*65)
wins = {
    '2022-2023': ('2022-05-02','2023-05-01'),
    '2023-2024': ('2023-05-01','2024-05-01'),
    '2024-2025': ('2024-05-01','2025-05-01'),
    '2025-2026': ('2025-05-01','2026-07-24'),
}
for yr,(ws,we) in wins.items():
    mask = [(t >= pd.Timestamp(ws) and t < pd.Timestamp(we)) for t in h1dt]
    sub  = np.array(mask)
    if sub.sum() == 0: continue
    idx_ = np.where(sub)[0]
    bh   = (c_[idx_[-1]] - c_[idx_[0]]) / c_[idx_[0]] * 100
    fwds = fwd24[sub & ~np.isnan(fwd24)]
    wr   = (fwds > 0).mean()*100 if len(fwds) > 0 else 0
    print(f"  {yr}: BH={bh:+.1f}%  avg_fwd24h={fwds.mean():+.3f}  WR_long={wr:.1f}%  bars={sub.sum()}")

print("\n[DONE] Use these facts to build the correct engine.")
