# FORWARD CANDIDATE REGISTRY (IMMUTABLE FUTURE OOS TRACKING)

This registry logs all frozen candidates pre-committed to future unobserved market data observation. Once registered, candidate parameters, logic, and acceptance criteria are strictly immutable.

---

## CANDIDATE INVENTORY

| Candidate ID | Strategy Name | Asset / Timeframe | Freeze Timestamp | Configuration SHA256 | Historical Cutoff | Status | Acceptance Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CAND-001`** | `ALAB_SQUEEZE_REGIME_V1` | GOLD (XAUUSD) / H1 | `2026-08-15T22:10:00+07:00` | `addf9673bb779c865e4425e7c397cd8af11aa9152ca045cd5955bfd4641104f5` | `2026-07-24 23:00:00` | **`FORWARD OBSERVATION — INCONCLUSIVE`** | Min 30 future trades, $\ge 4$ forward quarters, $PF \ge 1.30$, MaxDD $< 20\%$ |
| **`CAND-002`** | `ALAB_MINIMAL_SQUEEZE_V1` | GOLD (XAUUSD) / H1 | `2026-08-16T00:15:00+07:00` | `c8b417932cfae89dfb61b2a9261a8686134b22c710fa53cfcf871d33cb4112e4` | `2026-07-24 23:00:00` | **`FORWARD OBSERVATION — HISTORICAL SURVIVOR`** | Min 30 future trades, $\ge 4$ forward quarters, $PF \ge 1.30$, MaxDD $< 20\%$ |

---

## 1. CANDIDATE PROFILE: CAND-001 (LANE A BENCHMARK)

* **Candidate ID**: `CAND-001`
* **Strategy Name**: `ALAB_SQUEEZE_REGIME_V1`
* **Asset / Primary Timeframe**: `GOLD (XAUUSD) / H1`
* **Architecture**: 4-Component System (Squeeze + Macro EMA 200 + Kaufman ER 0.20 + MACD momentum).
* **Historical Performance (2001–2026)**: 136 trades, $PF = 1.837$, Net PnL +$6,451.00 USD, Win Rate 32.35%, Expectancy +0.273 R / trade.
* **Status**: **Lane A Benchmark (Inconclusive)**.

---

## 2. CANDIDATE PROFILE: CAND-002 (LANE B MINIMALIST SURVIVOR)

* **Candidate ID**: `CAND-002`
* **Strategy Name**: `ALAB_MINIMAL_SQUEEZE_V1`
* **Asset / Primary Timeframe**: `GOLD (XAUUSD) / H1`
* **Architecture**: Minimalist 2-Component System (Volatility Squeeze + Macro EMA 200 Trend Alignment, NO ER filter, NO MACD filter).
* **Parameters**:
  - `bb_period`: 20, `bb_mult`: 2.0
  - `kelt_mult`: 1.2
  - `macro_ema_len`: 200
  - `sl_atr_mult`: 2.0, `tp_rr_ratio`: 3.0
  - `use_squeeze`: true, `use_macro`: true, `use_er`: false, `use_macd`: false
  - `spread_pips`: 25.0, `commission_per_lot`: 7.0
* **Historical Performance (2001–2026)**: 144 trades, $PF = 1.752$, Net PnL +$6,169.71 USD, Win Rate 31.94%, Expectancy +0.233 R / trade.
* **Parameter Plateau**: Broad, cliff-free plateau across Macro EMA ($100–250$) and RR ($2.0–3.5$) with all 16 grid cells achieving $PF > 1.26$.
* **Status**: **Lane B Historical Survivor Candidate**.
