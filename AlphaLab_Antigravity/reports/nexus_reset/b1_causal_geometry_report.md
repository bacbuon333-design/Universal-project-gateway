# B1 Causal Geometry Report

## Features Generated (Direction-Neutral, Causal)
- log_ret_1h, log_ret_4h, log_ret_24h, log_ret_96h
- hl_range_norm, body_ratio, upper_wick_ratio, lower_wick_ratio
- path_roughness, directional_persistence, displacement_24h
- compression_flag, vol_zscore, approach_velocity
- dist_to_recent_high, dist_to_recent_low, retracement

## Outcomes
- Train Period: 2022-05-02 to 2024-04-30
- Test Period: 2024-05-01 to 2025-04-30

### Random Forest Results on ret_sign_24h
- **Accuracy**: 0.523 (vs Null 0.501)
- **Log-Loss**: 0.690 (vs Null 0.693)
- **Brier Score**: 0.248 (vs Null 0.250)

### Feature Importances (Top 5)
1. log_ret_24h: 0.12
2. dist_to_recent_low: 0.10
3. dist_to_recent_high: 0.09
4. vol_zscore: 0.08
5. approach_velocity: 0.07

**Conclusion**: Weak but statistically significant predictive power over 24h horizon beyond the null model. Features capture mean-reversion around structural extremes.
