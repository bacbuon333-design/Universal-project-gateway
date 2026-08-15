# CLAUDE.md — Project Memory: Alpha Research Factory & Lifecycle Management

This file defines the project memory, architecture blueprint, mathematical standards, and development guidelines for this institutional-grade quantitative platform.

---

## 🎯 Project Core Philosophy

We are not building an isolated trading bot. We are building an **Alpha Research Factory** designed to continuously discover, validate, rank, monitor, and retire trading alphas.

### Core Tenets:
1. **Alphas are Disposable**: We assume that all alpha eventually decays. The system's value is in the production loop, not a single static parameter set.
2. **Portfolio as the Deployable Unit**: The platform focuses on combinations of low-correlated strategies (portfolios) to smooth drawdowns and maximize diversified Sharpe ratios, rather than optimizing a single strategy.
3. **Rigorous Evidence Quality**: Reject backtest profits in favor of out-of-sample (OOS) robustness, walk-forward efficiency, slippage sensitivity, and regime stability.
4. **Dual-Track Governance (Stable Factory vs. Alpha Lab)**: Separate Track A (Stable Factory: frozen staging validation focused on distribution matching and execution drift) from Track B (Alpha Lab: R&D acceleration focused on maximizing the **learning rate** - trade density, asset coverage, and regime coverage - instead of chasing fast dollar compounding).

### 🧪 Track B (Alpha Lab) Roadmaps & KPIs:
* **North Star Metric**: **Learning Rate / Time-to-Evidence** (optimize speed of statistical inference via high trade density and multi-asset coverage).
* **R&D Filter Constraint**: Do not research anything that doesn't increase at least one of:
  1. **Trade Density**
  2. **Regime Coverage**
  3. **Diversification Quality**
  *(Banned: micro-parameter tweaking like RSI 14 -> 15).*
* **Roadmap Sprints (12 Months)**:
  - **Sprint 1: ALAB-005 (Multi-Asset Data Factory)**: Tích hợp SPY proxy (`US500Cash`), QQQ proxy (`US100Cash`), BTC proxy (`BTCUSD`), và `GOLD`. Nâng Trade Density lên **400 - 600 trade/năm**.
  - **Sprint 2: ALAB-006 (Strategy Tournament Expansion)**: Phát triển 10-15 chiến lược cấu trúc thuộc 4 nhóm (Trend, Mean Reversion, Volatility, Session). Nâng Trade Density lên **1.000 - 3.000 trade/năm**.
  - **Sprint 3: ALAB-007 (Correlation & Regime Audit)**: Đánh giá tương quan chéo, Return Clustering, và Regime Exposure để lọc các dòng lợi nhuận độc lập.
  - **Sprint 4: ALAB-008 (Portfolio Construction Factory)**: Kết hợp các chiến lược tối ưu để đạt Portfolio Sharpe danh mục $>1.0$.
* **Meta Portfolio AI Integration**:
  - *Stage 1 (Rule-Based Router)*: Hardcoded heuristics dựa trên trạng thái ADX/ATR (ví dụ: Trend -> Trend Portfolio, Range -> MR Portfolio).
  - *Stage 2 (ML Classifier)*: Random Forest dự đoán Regime dựa trên các đặc trưng ATR, VIX, Volatility, Trend Strength.
  - *Stage 3 (LLM Reasoning Layer)*: LLM đóng vai trò Head of Research để đọc Performance Reports, giải thích kết quả và đề xuất giả thuyết nghiên cứu.
* **Mục tiêu thực tế cho tài khoản 1.000 USD**:
  - *Giai đoạn 1*: 127 trade/năm, Sharpe 0.54 (Đồng bộ hóa hạ tầng, Baseline Every Tick).
  - *Giai đoạn 2*: 500+ trade/năm, Sharpe 0.8 (Đa dạng hóa Multi-Asset, chạy 10-15 chiến lược).
  - *Giai đoạn 3*: 1.000+ trade/năm, Portfolio Sharpe > 1.0 (Xây dựng Meta Portfolio).
  *(Tăng vốn từ $1k \rightarrow 5k \rightarrow 10k$ sẽ là hệ quả tự nhiên của một Research Factory mạnh mẽ).*
* **Track A Governance Status**: **FROZEN & RUNNING** (demotrading active for observation, execution data collection only, no live parameters modifications or capital scaling allowed).
* **Track B Status**: Active R&D under the 4-Sprint factory framework.

---

## 📐 System Architecture

The codebase is organized as a pipeline:
1. **Data Layer**: Historical bar syncing and data validation ([sync.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/data_layer/sync.py)).
2. **Regime Engine**: Detects trend state (`trend_up`, `trend_down`) and volatility state (`expansion`, `contraction`) ([regime.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/research_layer/regime.py)).
3. **Backtest Engine**: Event-driven backtester with commissions, slippage, and vectorized array loops for speed ([backtester.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/validation_layer/backtester.py)).
4. **Walk-Forward Validation**: 4 anchored splits to prevent parameter curve-fitting ([walk_forward.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/validation_layer/walk_forward.py)).
5. **Monte Carlo Simulator**: Runs 1,000 resampled paths to compute Risk of Ruin and max drawdown distributions ([monte_carlo.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/validation_layer/monte_carlo.py)).
6. **Strategy Tournament Engine**: Parallel worker processes that screen many stream combinations ([run_tournament.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/run_tournament.py)).
7. **Alpha Registry**: Persistent tracking database storing metrics across all runs.
8. **Portfolio Layer**: Timestamp-aligned returns correlation, equal-weighted portfolio builder, and portfolio-level simulator ([portfolio_research.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/portfolio_layer/portfolio_research.py)).

---

## 🚦 Alpha Lifecycle & Promotion Gates

Strategies progress through the pipeline based on objective criteria evaluated in [AlphaLifecycleManager](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/src/portfolio_layer/portfolio_research.py#L256):

```
RESEARCH ──(Gate 1)──> VALIDATED ──(Gate 2)──> PAPER_TRADING ──(Gate 3)──> CANDIDATE ──(Gate 4)──> PRODUCTION
                                                                                                        │
                                                   └───────────────────(Failsafes)──────────────────────┴─> ARCHIVED
```

* **RESEARCH**: Stream configuration under initial testing.
* **VALIDATED**: Requires OOS Sharpe $\ge 0.8$, WFE $\ge 50\%$, Risk of Ruin $\le 1\%$, and Robustness score $\ge 0.4$.
* **PAPER_TRADING**: Requires architect approval to run on live paper/demo execution bridge.
* **CANDIDATE**: Requires 20+ live execution trades, drift $\le 20\%$, and positive net profit.
* **PRODUCTION**: Requires $\ge 3$ months live trading history, realized Sharpe $\ge 0.5$, and Profit Factor $\ge 1.0$.
* **ARCHIVED**: Strategies that fail risk limits (realized drawdown $>15\%$, realized Sharpe $<0.2$, or performance decay detected) trip the circuit breaker and are retired permanently.

---

## 🧮 Mathematical Standards

1. **Sharpe Annualization (CRITICAL)**:
   - Always calculate returns on a fixed time frequency (e.g. hourly or daily aligned bars) before annualizing.
   - Use the appropriate multiplier $\sqrt{T}$ where:
     - Hourly returns: $T = 252 \times 24 = 6048$
     - Daily returns: $T = 252$
     - Monthly returns: $T = 12$
   - Never apply trade-level counts to high-frequency scaling multipliers, as trade sparseness yields massive scaling artifacts.
2. **Correlation Alignment**:
   - Align returns series on identical bar timestamps using pandas outer/inner joins before computing covariance and correlation matrices. Resample to standard daily or hourly frequencies to handle gaps.
3. **Edge Confidence Score**:
   - Combine Sharpe (25%), WFE (25%), RoR (20%), Trade Count (15%), and Cost Stability (15%) to score strategy viability out of 100.

---

## 🛠️ Code Quality & Testing
- Naming rules: classes are PascalCase, functions/variables are snake_case.
- Keep execution code decoupled from signal generator logic to allow easy strategy registration.
- Verify pipeline modifications using the test suite in `tests/` (`python -m unittest discover -s tests`). All tests must pass before deployment.
