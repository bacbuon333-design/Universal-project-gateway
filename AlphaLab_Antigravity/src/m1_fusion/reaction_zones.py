from __future__ import annotations

"""Reaction zone computation for ALAB-M1-FUSION-001.

Zones:
A. Previous Day High / Low (PDH / PDL)
B. Completed Session High / Low (Asia, London Research, New York Research)
C. Confirmed M15 Swings (Pivot Flank = 2)
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from .features import compute_atr14

REACTION_DISTANCE_ATR = 0.15
M15_SWING_ZONE_ATR = 0.10


def compute_pdh_pdl(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Compute strictly causal Previous Day High (PDH) and Low (PDL) for each M1 bar.
    
    Uses completed UTC calendar days only.
    """
    n = len(df)
    pdh_arr = np.full(n, np.nan, dtype=float)
    pdl_arr = np.full(n, np.nan, dtype=float)

    dates = df["datetime"].dt.date
    daily_stats = df.groupby(dates).agg(
        day_high=("high", "max"),
        day_low=("low", "min"),
    )

    # Shift by 1 day so today gets yesterday's completed high/low
    daily_stats_shifted = daily_stats.shift(1)
    shifted_dict_h = daily_stats_shifted["day_high"].to_dict()
    shifted_dict_l = daily_stats_shifted["day_low"].to_dict()

    for t in range(n):
        d = dates.iloc[t]
        pdh_arr[t] = shifted_dict_h.get(d, np.nan)
        pdl_arr[t] = shifted_dict_l.get(d, np.nan)

    return pdh_arr, pdl_arr


def compute_completed_session_levels(
    df: pd.DataFrame,
) -> Tuple[List[List[float]], List[List[float]]]:
    """Compute available completed session highs and lows for each M1 bar.
    
    Research sessions (UTC):
    - ASIA: 00:00 - 07:59 (closed at 08:00)
    - LONDON: 08:00 - 12:59 (closed at 13:00)
    - NEW_YORK: 13:00 - 17:59 (closed at 18:00)
    
    A session extreme becomes available ONLY after the session is completely closed.
    Returns:
        available_session_highs: list of active session highs for each bar t
        available_session_lows: list of active session lows for each bar t
    """
    n = len(df)
    times = df["datetime"]
    hours = times.dt.hour.to_numpy()
    minutes = times.dt.minute.to_numpy()
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)

    # Pre-extract all session intervals and compute their extremes and completion times
    sessions_completed = []  # tuples: (completion_idx, session_high, session_low)
    
    current_session = None
    sess_start_idx = 0
    
    for t in range(n):
        h = hours[t]
        # Determine session type
        if 0 <= h < 8:
            sess_type = "ASIA"
        elif 8 <= h < 13:
            sess_type = "LONDON"
        elif 13 <= h < 18:
            sess_type = "NEW_YORK"
        else:
            sess_type = "OTHER"

        # Check if session changed or day changed
        if current_session is None:
            current_session = sess_type
            sess_start_idx = t
        elif sess_type != current_session:
            # Previous session closed at index t-1
            if current_session in ("ASIA", "LONDON", "NEW_YORK"):
                s_high = np.max(highs[sess_start_idx:t])
                s_low = np.min(lows[sess_start_idx:t])
                sessions_completed.append((t, s_high, s_low))
            current_session = sess_type
            sess_start_idx = t

    # Build per-bar available session levels (retaining sessions completed within trailing ~1440 bars)
    available_highs: List[List[float]] = [[] for _ in range(n)]
    available_lows: List[List[float]] = [[] for _ in range(n)]

    sess_ptr = 0
    active_sessions: List[Tuple[int, float, float]] = []

    for t in range(n):
        while sess_ptr < len(sessions_completed) and sessions_completed[sess_ptr][0] <= t:
            active_sessions.append(sessions_completed[sess_ptr])
            sess_ptr += 1

        # Keep active sessions completed within last 1440 minutes (24 hours)
        recent = [s for s in active_sessions if t - s[0] <= 1440]
        active_sessions = recent

        available_highs[t] = [s[1] for s in recent]
        available_lows[t] = [s[2] for s in recent]

    return available_highs, available_lows


def compute_m15_swings(
    df_m1: pd.DataFrame, flank: int = 2
) -> Tuple[List[List[float]], List[List[float]]]:
    """Resample M1 to M15 and identify confirmed pivots (flank=2).
    
    Pivot at M15 bar j is confirmed only at the close of M15 bar j+2.
    Available to M1 bars with timestamp >= M15_close_time(j+2).
    """
    n_m1 = len(df_m1)
    df_indexed = df_m1.set_index("datetime")
    
    # Resample to 15min bars using UTC alignment
    m15 = df_indexed.resample("15min", label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
    ).dropna().reset_index()

    m15_highs = m15["high"].to_numpy(dtype=float)
    m15_lows = m15["low"].to_numpy(dtype=float)
    m15_times = m15["datetime"]
    m15_atr = compute_atr14(m15).to_numpy(dtype=float)
    n_m15 = len(m15)

    # Detect pivots
    # Pivot candidate j (requires j-flank >= 0 and j+flank < n_m15)
    # Confirmation occurs at close of bar j+flank, which is m15_times[j+flank] + 15 minutes.
    confirmed_swings: List[Tuple[pd.Timestamp, str, float, float]] = []
    # (confirmation_timestamp, type, price_level, zone_width)

    for j in range(flank, n_m15 - flank):
        left_h = m15_highs[j - flank : j]
        right_h = m15_highs[j + 1 : j + flank + 1]
        left_l = m15_lows[j - flank : j]
        right_l = m15_lows[j + 1 : j + flank + 1]
        
        confirm_time = m15_times.iloc[j + flank] + pd.Timedelta(minutes=15)
        atr_val = m15_atr[j + flank] if np.isfinite(m15_atr[j + flank]) else 1.0
        zone_w = M15_SWING_ZONE_ATR * atr_val

        if m15_highs[j] > np.max(left_h) and m15_highs[j] > np.max(right_h):
            confirmed_swings.append((confirm_time, "HIGH", m15_highs[j], zone_w))
        if m15_lows[j] < np.min(left_l) and m15_lows[j] < np.min(right_l):
            confirmed_swings.append((confirm_time, "LOW", m15_lows[j], zone_w))

    # Map confirmed swings causally to M1 bars
    m1_times = df_m1["datetime"].to_numpy()
    available_swing_highs: List[List[float]] = [[] for _ in range(n_m1)]
    available_swing_lows: List[List[float]] = [[] for _ in range(n_m1)]

    swing_ptr = 0
    active_highs: List[Tuple[pd.Timestamp, float]] = []
    active_lows: List[Tuple[pd.Timestamp, float]] = []

    for t in range(n_m1):
        t_time = m1_times[t]
        while swing_ptr < len(confirmed_swings) and confirmed_swings[swing_ptr][0] <= t_time:
            c_time, s_type, s_price, _ = confirmed_swings[swing_ptr]
            if s_type == "HIGH":
                active_highs.append((c_time, s_price))
            else:
                active_lows.append((c_time, s_price))
            swing_ptr += 1

        # Keep recent swings within last 24 hours (1440 minutes)
        cutoff = t_time - np.timedelta64(1440, "m")
        active_highs = [s for s in active_highs if s[0] >= cutoff]
        active_lows = [s for s in active_lows if s[0] >= cutoff]

        available_swing_highs[t] = [s[1] for s in active_highs]
        available_swing_lows[t] = [s[1] for s in active_lows]

    return available_swing_highs, available_swing_lows
