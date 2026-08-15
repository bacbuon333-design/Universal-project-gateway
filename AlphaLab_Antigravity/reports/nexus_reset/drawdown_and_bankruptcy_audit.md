# Drawdown and Bankruptcy Audit

- **Finding:** v31 SELL-only had MaxDD of 52-125%.
- **Analysis:** These values exceed 100% which means the simulation allows negative equity (bankruptcy). The `bal` variable was never floor-limited to zero.
- **Conclusion:** This is a critical accounting bug.
