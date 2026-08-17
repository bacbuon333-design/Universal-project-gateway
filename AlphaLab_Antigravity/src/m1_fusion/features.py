from __future__ import annotations

"""Causal feature computation for ALAB-M1-FUSION-001."""

import numpy as np
import pandas as pd

PRIOR_EXTREME_LOOKBACK = 20
PATH_WINDOW = 10
EFFICIENCY_THRESHOLD = 0.65
ROBUST_WINDOW = 60
ROBUST_Z_THRESHOLD = 2.0
ATR_PERIOD = 14
ATR_PERCENTILE_WINDOW = 500
ATR_PERCENTILE_THRESHOLD = 80.0


def compute_atr14(df: pd.DataFrame) -> pd.Series:
    """Causal Wilder-style ATR14."""
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / ATR_PERIOD, adjust=False, min_periods=ATR_PERIOD).mean()


def compute_prior_extremes(
    df: pd.DataFrame, lookback: int = PRIOR_EXTREME_LOOKBACK
) -> Tuple[pd.Series, pd.Series]:
    """Causal prior high and low over `lookback` bars strictly preceding bar t."""
    prior_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
    prior_low = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)
    return prior_high, prior_low


def compute_path_efficiency(
    df: pd.DataFrame, window: int = PATH_WINDOW
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Causal path efficiency and direction over trailing `window` bars ending at t-1.
    
    Returns:
        efficiency_ratio (float array)
        is_upward_displacement (bool array)
        is_downward_displacement (bool array)
    """
    n = len(df)
    c = df["close"].to_numpy(dtype=float)
    eff_ratio = np.zeros(n, dtype=float)
    is_up = np.zeros(n, dtype=bool)
    is_down = np.zeros(n, dtype=bool)

    # Compute 1-bar price changes
    diff = np.abs(np.diff(c, prepend=c[0]))

    # Cumulative path length over trailing `window` bars ending at t-1
    # For bar t, preceding window covers indices (t - window) to (t - 1).
    for t in range(window + 1, n):
        c_end = c[t - 1]
        c_start = c[t - 1 - window]
        net_disp = abs(c_end - c_start)
        path_len = np.sum(diff[t - window : t])
        if path_len > 1e-9:
            eff_ratio[t] = net_disp / path_len
        else:
            eff_ratio[t] = 0.0

        is_up[t] = c_end > c_start
        is_down[t] = c_end < c_start

    return eff_ratio, is_up, is_down


def compute_robust_stretch_z(
    df: pd.DataFrame, window: int = ROBUST_WINDOW
) -> np.ndarray:
    """Causal robust stretch Z-score computed from rolling median & MAD over trailing window ending at t-1.
    
    stretch_z = (close[t-1] - rolling_median) / (1.4826 * MAD)
    """
    n = len(df)
    c = df["close"].to_numpy(dtype=float)
    stretch_z = np.zeros(n, dtype=float)

    for t in range(window + 1, n):
        sub = c[t - 1 - window : t - 1]
        med = np.median(sub)
        mad = np.median(np.abs(sub - med))
        sigma = 1.4826 * mad
        if sigma > 1e-9 and np.isfinite(sigma):
            z = (c[t - 1] - med) / sigma
            stretch_z[t] = np.clip(z, -20.0, 20.0)
        else:
            stretch_z[t] = 0.0

    return stretch_z


def compute_atr_percentiles(
    atr: pd.Series, window: int = ATR_PERCENTILE_WINDOW
) -> np.ndarray:
    """Causal percentile rank of ATR[t-1] relative to trailing `window` ATR values ending at t-1."""
    n = len(atr)
    a = atr.to_numpy(dtype=float)
    pct = np.zeros(n, dtype=float)

    for t in range(window + 1, n):
        current_atr = a[t - 1]
        if not np.isfinite(current_atr):
            pct[t] = 0.0
            continue
        sub = a[t - 1 - window : t - 1]
        valid_sub = sub[np.isfinite(sub)]
        if len(valid_sub) >= 50:
            rank = np.sum(valid_sub <= current_atr) / len(valid_sub) * 100.0
            pct[t] = rank
        else:
            pct[t] = 0.0

    return pct
