from __future__ import annotations

"""Causal feature computation for ALAB-M1-FUSION-001/001R."""

from typing import Tuple
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
    c = df["close"]
    diff = np.abs(np.diff(c.to_numpy(dtype=float), prepend=c.iloc[0]))
    
    # Causal displacement over trailing window ending at t - 1:
    # net_disp = abs(close[t - 1] - close[t - 1 - window])
    c_end = c.shift(1)
    c_start = c.shift(1 + window)
    net_disp = (c_end - c_start).abs().to_numpy(dtype=float)
    
    # Path length over trailing `window` 1-bar differences ending at t-1
    path_len = pd.Series(diff).rolling(window, min_periods=window).sum().shift(1).to_numpy(dtype=float)
    
    valid_mask = (path_len > 1e-9) & np.isfinite(path_len) & np.isfinite(net_disp)
    eff_ratio = np.where(valid_mask, net_disp / np.where(valid_mask, path_len, 1.0), 0.0)
    eff_ratio[:window + 1] = 0.0

    is_up = np.zeros(n, dtype=bool)
    is_down = np.zeros(n, dtype=bool)
    valid_dir = np.isfinite(c_end.to_numpy()) & np.isfinite(c_start.to_numpy())
    is_up = np.where(valid_dir, (c_end > c_start).to_numpy(), False)
    is_down = np.where(valid_dir, (c_end < c_start).to_numpy(), False)
    is_up[:window + 1] = False
    is_down[:window + 1] = False

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

    chunk_size = 100000
    for start in range(window + 1, n, chunk_size):
        end = min(start + chunk_size, n)
        k = end - start
        w_start = start - 1 - window
        w_end = end - 2
        sub_c = c[w_start : w_end + 1]
        sub_windows = np.lib.stride_tricks.sliding_window_view(sub_c, window)[:k]
        c_prev = c[start - 1 : end - 1]
        
        med = np.median(sub_windows, axis=1)
        mad = np.median(np.abs(sub_windows - med[:, None]), axis=1)
        sigma = 1.4826 * mad
        valid = (sigma > 1e-9) & np.isfinite(sigma)
        z_calc = np.where(valid, (c_prev - med) / np.where(valid, sigma, 1.0), 0.0)
        stretch_z[start : end] = np.clip(z_calc, -20.0, 20.0)

    stretch_z[:window + 1] = 0.0
    return stretch_z


def compute_atr_percentiles(
    atr: pd.Series, window: int = ATR_PERCENTILE_WINDOW
) -> np.ndarray:
    """Causal percentile rank of ATR[t-1] relative to trailing `window` ATR values ending at t-1."""
    n = len(atr)
    a = atr.to_numpy(dtype=float)
    pct = np.zeros(n, dtype=float)

    chunk_size = 100000
    for start in range(window + 1, n, chunk_size):
        end = min(start + chunk_size, n)
        k = end - start
        w_start = start - 1 - window
        w_end = end - 2
        sub_a = a[w_start : w_end + 1]
        sub_windows = np.lib.stride_tricks.sliding_window_view(sub_a, window)[:k]
        a_prev = a[start - 1 : end - 1]
        
        valid_mask = np.isfinite(sub_windows)
        valid_counts = np.sum(valid_mask, axis=1)
        hits = np.sum((sub_windows <= a_prev[:, None]) & valid_mask, axis=1)
        ranks = np.where(valid_counts >= 50, (hits / np.maximum(valid_counts, 1)) * 100.0, 0.0)
        pct[start : end] = ranks

    pct[:window + 1] = 0.0
    return pct
