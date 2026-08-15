# V3.3.1 PROFIT CONCENTRATION SPECIFICATION
## MATHEMATICAL DEFINITION OF POSITIVE PROFIT CONCENTRATION ESTIMATOR

---

## 1. FORMULATION
For each complete quarter $q \in \{2018\text{Q}2, \dots, 2026\text{Q}2\}$, let $\text{Q\_PnL}[q]$ be the net PnL of all trades entering in quarter $q$.

1. **Positive Quarter Profit Pool**:
   $$\text{Total Positive Profit} = \sum_{q=1}^{33} \max(\text{Q\_PnL}[q], 0)$$

2. **Top-K Concentration**:
   Let $\{P_{(1)}, P_{(2)}, \dots, P_{(m)}\}$ be the set of positive quarterly PnLs sorted in descending order ($P_{(1)} \ge P_{(2)} \ge \dots > 0$).
   $$\text{Top3 Share (\%)} = \frac{\sum_{k=1}^{\min(3, m)} P_{(k)}}{\text{Total Positive Profit}} \times 100\%$$
   $$\text{Top5 Share (\%)} = \frac{\sum_{k=1}^{\min(5, m)} P_{(k)}}{\text{Total Positive Profit}} \times 100\%$$

---

## 2. NULL POOL RESOLUTION
If $\text{Total Positive Profit} \le 0$:
- `Top3 Share` = `NaN`
- `Top5 Share` = `NaN`
- Gate B1 = **FAIL**
- Gate B2 = **FAIL**
- Status: `profit_concentration_applicable = False` (No sentinel numbers such as `-999`).
