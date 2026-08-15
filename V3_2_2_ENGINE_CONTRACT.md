# V3.2.2 STRATEGY-ENGINE CONTRACT SPECIFICATION

---

## 1. REUSABLE RUNTIME VALIDATION FUNCTION (`validate_strategy_output`)

```python
def validate_strategy_output(df: pd.DataFrame, signals: np.ndarray, sl_dists: np.ndarray, tp_dists: np.ndarray) -> None:
    """
    Authoritative runtime contract validator asserting strategy output conformity.
    Raises ValueError immediately if any interface invariant is breached.
    """
    n = len(df)
    if len(signals) != n or len(sl_dists) != n or len(tp_dists) != n:
        raise ValueError(f"Array length mismatch: df={n}, signals={len(signals)}, sl_dists={len(sl_dists)}, tp_dists={len(tp_dists)}")
        
    valid_sigs = {-1, 0, 1}
    unique_sigs = set(np.unique(signals))
    if not unique_sigs.issubset(valid_sigs):
        raise ValueError(f"Invalid signal values: {unique_sigs - valid_sigs}. Allowed: {-1, 0, 1}")
        
    active_idx = np.where(signals != 0)[0]
    if len(active_idx) > 0:
        # Check NaNs
        if np.isnan(sl_dists[active_idx]).any() or np.isnan(tp_dists[active_idx]).any():
            raise ValueError("NaN detected in active sl_dists or tp_dists")
            
        # Check non-positive distances
        if (sl_dists[active_idx] <= 0).any() or (tp_dists[active_idx] <= 0).any():
            raise ValueError("Non-positive distance detected in active sl_dists or tp_dists")
            
        # Catch accidental absolute price levels (e.g. sl_dist near market price level)
        close_vals = df['close'].values[active_idx]
        if (sl_dists[active_idx] > 0.50 * close_vals).any():
            raise ValueError("Unreasonably large sl_dist detected (>50% of market price). Possible absolute price passed instead of distance!")
```
