# INSTRUMENT SPECIFICATIONS & VALUATION CONVENTIONS

This document specifies the exact contract sizes, pip geometries, and account-currency (USD) valuation formulas for all assets evaluated in V3.1.

---

## 1. INSTRUMENT SPECIFICATION MATRIX

| Asset Symbol | Asset Class | Base Currency | Quote Currency | Price Digits | Pip Definition | Contract Size (1.0 lot) | Volume (0.10 lot) | Pip Value (0.10 lot in USD) | PnL Formula (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`XAUUSD` (Gold)** | Commodity | XAU (oz) | USD | 2 | $0.01 price move | 100 oz | 10 oz | **$0.10 USD / pip** | $\Delta P \times 10.0 - \text{Costs}$ |
| **`EURUSD`** | Forex | EUR | USD | 5 | $0.0001 (10 pts) | 100,000 EUR | 10,000 EUR | **$1.00 USD / pip** | $\frac{\Delta P}{0.0001} \times 1.00 - \text{Costs}$ |
| **`GBPUSD`** | Forex | GBP | USD | 5 | $0.0001 (10 pts) | 100,000 GBP | 10,000 GBP | **$1.00 USD / pip** | $\frac{\Delta P}{0.0001} \times 1.00 - \text{Costs}$ |
| **`USDJPY`** | Forex | USD | JPY | 3 | $0.01 (10 pts) | 100,000 USD | 10,000 USD | **$\frac{100}{\text{Price}}$ USD / pip** | $\frac{\Delta P}{0.01} \times \frac{100}{\text{Exit Price}} - \text{Costs}$ |
| **`BTCUSD`** | Crypto | BTC | USD | 2 | $1.00 price move | 1 BTC | 0.10 BTC | **$0.10 USD / pip** | $\Delta P \times 0.10 - \text{Costs}$ |

---

## 2. TRANSACTION COST & SPREAD CONVENTIONS (0.10 LOT)

| Asset Symbol | Standard Spread | Spread Cost (USD on 0.10 lot) | Round-Trip Commission (USD on 0.10 lot) | Total Execution Friction / Trade |
| :--- | :--- | :--- | :--- | :--- |
| **`XAUUSD`** | 25 pips ($0.25) | $2.50 USD | $0.70 USD ($7/lot) | **$3.20 USD** |
| **`EURUSD`** | 1.5 pips (0.00015) | $1.50 USD | $0.70 USD ($7/lot) | **$2.20 USD** |
| **`GBPUSD`** | 1.8 pips (0.00018) | $1.80 USD | $0.70 USD ($7/lot) | **$2.50 USD** |
| **`USDJPY`** | 1.8 pips (0.018) | ~$1.20 USD (@ 150.00) | $0.70 USD ($7/lot) | **~$1.90 USD** |
| **`BTCUSD`** | 50 points ($50.00) | $5.00 USD | $0.70 USD ($7/lot) | **$5.70 USD** |

---

## 3. VALUATION VERIFICATION STATUS

* **`XAUUSD`**: **`VERIFIED`** (Tested across 10 engine unit tests).
* **`EURUSD`**: **`VERIFIED`** (Validated via synthetic +100/-100 pip unit test).
* **`GBPUSD`**: **`VERIFIED`** (Validated via synthetic +100/-100 pip unit test).
* **`USDJPY`**: **`VERIFIED`** (Validated via synthetic dynamic JPY/USD quote conversion test).
* **`BTCUSD`**: **`VERIFIED`** (Validated via synthetic BTC point valuation test).
