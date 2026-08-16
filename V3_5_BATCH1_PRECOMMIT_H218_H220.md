# V3.5 BATCH-1 PRECOMMIT — H-218 TO H-220

## Status
Immutable pre-execution specification. No result from H-218/H-219/H-220 may exist before this commit.

Parent framework: `V3_5_RESEARCH_FRAMEWORK_PRECOMMIT.md`.

Research budget: exactly 12 configurations across 3 distinct mechanism families. No dynamic expansion.

Instrument/timeframe: GOLD M30.
Evaluation: entry-quarter 2018Q2 through 2026Q2 inclusive.
Execution: fixed lot 0.10, spread 25 pips, commission $7/lot, slippage 0, pessimistic ambiguous bars, one active trade, next-bar entry.

## Scientific design rule
This batch deliberately avoids another squeeze/compression repair and does not tune H-215/H-216/H-217. It tests three new mechanism representations:
1. interday structural breakout continuation;
2. normalized multi-bar impulse continuation;
3. session-to-session directional carry.

All directions are symmetric Long/Short in this first pass. Any later directional variant requires a new precommit.

---

# H-218 — PREVIOUS-DAY RANGE BREAKOUT CONTINUATION (PDBC)

## Economic hypothesis
A first decisive close through the fully completed previous UTC day's high/low may contain continuation information because the market has crossed a visible prior-day inventory boundary.

## Causal construction
For each UTC calendar day D, compute previous completed day D-1:
- `prev_day_high` = maximum high of D-1;
- `prev_day_low` = minimum low of D-1.

At M30 bar i close:
- Long trigger: `close[i] > prev_day_high[i]` AND `close[i-1] <= prev_day_high[i-1]`.
- Short trigger: `close[i] < prev_day_low[i]` AND `close[i-1] >= prev_day_low[i-1]`.

The previous-day levels are shifted by one complete day. No current-day future bars may enter them.
Entry occurs at bar i+1 open.

ATR = simple rolling mean True Range(14), using data available by bar i close.

Configurations:
- H-218-C1: SL 1.5 ATR, TP = 2.0 x SL
- H-218-C2: SL 1.5 ATR, TP = 2.5 x SL
- H-218-C3: SL 2.0 ATR, TP = 2.0 x SL
- H-218-C4: SL 2.0 ATR, TP = 2.5 x SL

No EMA, no squeeze, no session filter, no direction filter.

---

# H-219 — NORMALIZED IMPULSE CONTINUATION (NIC)

## Economic hypothesis
A sufficiently large multi-bar directional displacement relative to recent ATR may represent persistent order-flow pressure rather than a level-based breakout.

## Causal construction
Define:
`impulse_N[i] = close[i] - close[i-N]`
`z_N[i] = impulse_N[i] / ATR14[i]`.

A signal occurs only on threshold crossing to avoid repeated signals while the same impulse remains extreme.

Long:
`z_N[i] > K` AND `z_N[i-1] <= K`.

Short:
`z_N[i] < -K` AND `z_N[i-1] >= -K`.

Entry bar i+1 open.
SL = 1.5 ATR14.
TP = 2.0 x SL.

Configurations:
- H-219-C1: N=6 bars, K=1.5
- H-219-C2: N=6 bars, K=2.0
- H-219-C3: N=12 bars, K=1.5
- H-219-C4: N=12 bars, K=2.0

No EMA/regime filter and no range/squeeze definition.

---

# H-220 — LONDON-MORNING DIRECTIONAL CARRY (LMDC)

## Economic hypothesis
Direction established during the completed 08:00-12:00 UTC morning block may persist into the next intraday block when the completed move is large relative to recent volatility.

This differs from H-212: H-212 traded breakouts of an Asian-session range. H-220 uses the signed return of a completed 08:00-12:00 block and asks whether that direction carries forward.

## Causal construction
For each UTC day, using ONLY bars with timestamps:
`08:00 <= time < 12:00`:
- `morning_open` = open of first available bar in that block;
- `morning_close` = close of last available bar in that block;
- `morning_return = morning_close - morning_open`.

Signal evaluation occurs only on the bar timestamped 12:00 UTC.
Use `ATR14[i-1]` so the normalization is known before the 12:00 bar begins.

`morning_z = morning_return / ATR14[i-1]`.

Long at the 12:00 bar close if `morning_z > K`.
Short if `morning_z < -K`.
No signal otherwise.
Entry occurs at the next M30 open (normally 12:30 UTC).

SL = 1.5 ATR14[i] at signal close.

Configurations:
- H-220-C1: K=1.0, TP = 2.0 x SL
- H-220-C2: K=1.0, TP = 2.5 x SL
- H-220-C3: K=1.5, TP = 2.0 x SL
- H-220-C4: K=1.5, TP = 2.5 x SL

No day-of-week filter. No EMA. No DST reinterpretation; UTC timestamps are authoritative.

---

# Acceptance
Every configuration is evaluated using the full V3.5 gates, including 4Q, 8Q, and full-calendar-year gates. All must pass simultaneously.

Allowed statuses:
- REJECTED
- HISTORICAL DISTRIBUTED SURVIVOR — REQUIRES PRECOMMITTED STABILITY BATCH
- INVALID — EXECUTION OR SPECIFICATION FAILURE

## Stop rule
After exactly 12 configurations are executed, stop. Do not add H-221, change a threshold, remove one direction, or build a stability batch before independent audit.
