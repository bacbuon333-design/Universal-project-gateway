# V3.3.1 EVALUATION WINDOW SPECIFICATION
## DEFINITION OF AUTHORITATIVE TRADE POPULATION

---

## 1. AUTHORITATIVE EVALUATION POPULATION
The evaluation population is strictly defined as all executed trades whose **ENTRY TIME** falls within the precommitted 33 complete quarters:

$$\text{evaluation\_trades} = \{ t \in \text{All Trades} \mid 2018\text{Q}2 \le \text{quarter}(t.\text{entry\_time}) \le 2026\text{Q}2 \}$$

---

## 2. ENTRY-QUARTER CONVENTION
1. **Assignment**: A trade belongs to the quarter of its entry time, NOT its exit time.
2. **Boundary Behavior**:
   - A trade entering in `2018Q1` and exiting in `2018Q2` is **EXCLUDED**.
   - A trade entering in `2018Q2` and exiting in `2018Q2` is **INCLUDED**.
   - A trade entering in `2026Q2` and exiting in `2026Q3` is **INCLUDED** (as a `2026Q2` trade).
   - A trade entering in `2026Q3` is **EXCLUDED**.

---

## 3. DERIVED METRICS RECOMPUTED EXCLUSIVELY FROM `evaluation_trades`
All candidate evaluation metrics are computed solely from `evaluation_trades`:
- Total trades: $N = |\text{evaluation\_trades}|$
- Gross Profit: $\text{GP} = \sum_{t \in \text{evaluation\_trades}, \text{pnl} > 0} t.\text{pnl\_usd}$
- Gross Loss: $\text{GL} = \sum_{t \in \text{evaluation\_trades}, \text{pnl} < 0} |t.\text{pnl\_usd}|$
- Profit Factor: $\text{PF} = \text{GP} / \text{GL}$ (or $0.0$ if $\text{GL} = 0$ and $\text{GP} = 0$)
- Net PnL: $\text{PnL} = \sum_{t \in \text{evaluation\_trades}} t.\text{pnl\_usd}$
- Net Expectancy: $\text{Exp} = \text{mean}(t.\text{pnl\_usd})$
- Win Rate: $\text{WR} = |\{t \mid t.\text{pnl\_usd} > 0\}| / N \times 100\%$
- Long/Short breakdowns: Computed exclusively on subsets of `evaluation_trades`.
- Quarter table: 33 complete rows built by grouping `evaluation_trades` by `entry_quarter`.
