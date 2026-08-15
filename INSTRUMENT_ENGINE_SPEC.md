# INSTRUMENT ENGINE SPECIFICATION: ASSET-AWARE EXECUTION ARCHITECTURE

This document specifies the trade-level asset-aware execution and economic valuation architecture implemented directly inside `deep_quant_engine.py`.

---

## 1. INSTRUMENT SPECIFICATION SCHEMA (`InstrumentSpec`)

```python
@dataclass
class InstrumentSpec:
    symbol: str
    asset_class: str            # "COMMODITY", "FOREX_USD_QUOTE", "FOREX_USD_BASE", "CRYPTO"
    price_digits: int           # Digits of price precision (e.g. 2 for Gold/Crypto, 5 for EURUSD, 3 for USDJPY)
    point_size: float           # Minimum price increment (e.g. 0.01, 0.00001, 0.001)
    pip_size: float             # Standard pip price increment (e.g. 0.01 for Gold/USDJPY, 0.0001 for EURUSD)
    contract_size: float        # Contract units per 1.0 standard lot (e.g. 100 oz Gold, 100,000 base FX, 1.0 BTC)
    default_lot: float          # Default trading volume (e.g. 0.10 standard lot)
    quote_currency: str         # "USD", "JPY", etc.
    account_currency: str       # "USD"
    default_spread_pips: float  # Default spread in pips (e.g. 25.0 Gold, 1.5 EURUSD, 1.8 GBPUSD/USDJPY, 50.0 BTC)
    commission_per_lot_usd: float # Fixed round-trip commission per 1.0 lot in USD ($7.00/lot -> $0.70 on 0.10 lot)
```

---

## 2. STANDARD INSTRUMENT REGISTRY

| Symbol | Asset Class | Digits | Pip Size | Contract Size (1.0 lot) | Volume (0.10 lot) | PnL Formula (USD) | Default Spread |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`XAUUSD` (Gold)** | `COMMODITY` | 2 | 0.01 | 100 oz | 10 oz | $\Delta P \times \text{Volume} - \text{Costs}$ | 25.0 pips ($0.25) |
| **`EURUSD`** | `FOREX_USD_QUOTE` | 5 | 0.0001 | 100,000 EUR | 10,000 EUR | $\Delta P \times \text{Volume} - \text{Costs}$ | 1.5 pips (0.00015) |
| **`GBPUSD`** | `FOREX_USD_QUOTE` | 5 | 0.0001 | 100,000 GBP | 10,000 GBP | $\Delta P \times \text{Volume} - \text{Costs}$ | 1.8 pips (0.00018) |
| **`USDJPY`** | `FOREX_USD_BASE` | 3 | 0.01 | 100,000 USD | 10,000 USD | $\frac{\Delta P \times \text{Volume}}{P_{\text{exit}}} - \text{Costs}$ | 1.8 pips (0.018) |
| **`BTCUSD`** | `CRYPTO` | 2 | 1.00 (or 0.01) | 1.0 BTC | 0.10 BTC | $\Delta P \times \text{Volume} - \text{Costs}$ | 50.0 points ($50.00) |

---

## 3. AUTHORITATIVE TRADE-LEVEL PNL CALCULATION FUNCTION

```python
def calculate_trade_pnl(spec: InstrumentSpec, direction: int, entry_price: float, exit_price: float,
                        lots: float = 0.10, spread_pips: float = None, commission_per_lot: float = None,
                        slippage_pips: float = 0.0) -> dict:
    """
    Authoritative function calculating exact trade-level PnL, gross PnL, and transaction friction
    in account currency (USD) DURING backtest execution.
    """
    spr = spread_pips if spread_pips is not None else spec.default_spread_pips
    comm_rate = commission_per_lot if commission_per_lot is not None else spec.commission_per_lot_usd
    
    vol = lots * spec.contract_size
    price_diff = (exit_price - entry_price) * direction
    
    # 1. Gross PnL in Quote Currency
    if spec.asset_class in ["COMMODITY", "FOREX_USD_QUOTE", "CRYPTO"]:
        gross_pnl_usd = price_diff * vol
    elif spec.asset_class == "FOREX_USD_BASE": # e.g. USDJPY
        gross_pnl_jpy = price_diff * vol
        gross_pnl_usd = gross_pnl_jpy / (exit_price if exit_price > 0 else entry_price)
    else:
        gross_pnl_usd = price_diff * vol

    # 2. Transaction Costs in Account Currency (USD)
    spread_price = (spr + slippage_pips) * spec.pip_size
    if spec.asset_class in ["COMMODITY", "FOREX_USD_QUOTE", "CRYPTO"]:
        spread_cost_usd = spread_price * vol
    elif spec.asset_class == "FOREX_USD_BASE":
        spread_cost_usd = (spread_price * vol) / (exit_price if exit_price > 0 else entry_price)
    else:
        spread_cost_usd = spread_price * vol
        
    comm_cost_usd = comm_rate * lots
    total_costs_usd = spread_cost_usd + comm_cost_usd
    
    net_pnl_usd = gross_pnl_usd - total_costs_usd
    
    return {
        'gross_pnl_usd': gross_pnl_usd,
        'spread_cost_usd': spread_cost_usd,
        'commission_usd': comm_cost_usd,
        'total_costs_usd': total_costs_usd,
        'net_pnl_usd': net_pnl_usd,
        'is_win': net_pnl_usd > 0
    }
```
