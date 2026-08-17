from __future__ import annotations

"""Neutral market-state decomposition for ALAB-M1-MECH-002.

The module deliberately avoids strategy rules and economic labels such as
"liquidity refill" or "informed flow". It measures only observable M1 price
state transitions around already-defined Failed Auction events.

Primary state labels are CLOSE based. High/Low are used only for excursion
statistics because OHLC cannot reveal intrabar ordering.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from m1_fusion.failed_auction import FailedAuctionEvent
from m1_fusion.features import compute_atr14
from m1_fusion.reaction_zones import REACTION_DISTANCE_ATR

# Frozen development dataset. 2015-2017 remains sealed final holdout.
DEVELOPMENT_START_UTC = pd.Timestamp("2018-01-01T00:00:00Z")
DEVELOPMENT_END_UTC = pd.Timestamp("2026-01-01T00:00:00Z")
EXPECTED_DATA_SHA256 = "10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e"
HORIZONS_MINUTES: Tuple[int, ...] = (1, 3, 5, 10, 15, 30)
PRIMARY_HORIZON_MINUTES = 5
SESSION_LOOKBACK = pd.Timedelta(hours=24)
M15_SWING_LOOKBACK = pd.Timedelta(hours=24)
M15_PIVOT_FLANK = 2
M15_SWING_ZONE_ATR = 0.10


@dataclass(frozen=True)
class TimedLevelIndex:
    """Sorted timestamp index for one level side (HIGH or LOW)."""

    times_ns: np.ndarray
    levels: np.ndarray
    widths: np.ndarray
    labels: np.ndarray

    @classmethod
    def empty(cls) -> "TimedLevelIndex":
        return cls(
            times_ns=np.array([], dtype=np.int64),
            levels=np.array([], dtype=float),
            widths=np.array([], dtype=float),
            labels=np.array([], dtype=object),
        )

    def recent_slice(
        self, event_time: pd.Timestamp, lookback: pd.Timedelta
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if len(self.times_ns) == 0:
            return (
                np.array([], dtype=float),
                np.array([], dtype=float),
                np.array([], dtype=object),
            )
        event_ns = pd.Timestamp(event_time).value
        left_ns = event_ns - lookback.value
        left = int(np.searchsorted(self.times_ns, left_ns, side="left"))
        right = int(np.searchsorted(self.times_ns, event_ns, side="right"))
        return self.levels[left:right], self.widths[left:right], self.labels[left:right]


def _make_level_indexes(records: List[Tuple[pd.Timestamp, str, float, float, str]]) -> Dict[str, TimedLevelIndex]:
    out: Dict[str, TimedLevelIndex] = {}
    for side in ("HIGH", "LOW"):
        rows = [r for r in records if r[1] == side]
        rows.sort(key=lambda r: r[0])
        if not rows:
            out[side] = TimedLevelIndex.empty()
            continue
        out[side] = TimedLevelIndex(
            times_ns=np.array([pd.Timestamp(r[0]).value for r in rows], dtype=np.int64),
            levels=np.array([r[2] for r in rows], dtype=float),
            widths=np.array([r[3] for r in rows], dtype=float),
            labels=np.array([r[4] for r in rows], dtype=object),
        )
    return out


def validate_development_frame(df: pd.DataFrame) -> None:
    """Fail closed if data can touch the sealed 2015-2017 holdout or 2026."""
    required = {"datetime", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Development dataset is empty.")
    dt = pd.to_datetime(df["datetime"], utc=True)
    if not dt.is_monotonic_increasing:
        raise ValueError("Datetime must be monotonic increasing.")
    if dt.duplicated().any():
        raise ValueError("Duplicate timestamps are not allowed.")
    if dt.min() < DEVELOPMENT_START_UTC:
        raise RuntimeError(
            "STOP_BLOCKED_SEALED_HOLDOUT_ACCESS: MECH-002 may not access pre-2018 data."
        )
    if dt.max() >= DEVELOPMENT_END_UTC:
        raise RuntimeError(
            "STOP_BLOCKED_DISCOVERY_LEAKAGE: MECH-002 may not access 2026+ data."
        )


def compute_previous_observed_day_levels(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Causal previous observed trading-day H/L.

    The name is explicit because a Friday session maps to the next observed
    trading day, not necessarily the immediately previous UTC calendar date.
    """
    dates = df["datetime"].dt.date
    daily = df.groupby(dates, sort=True).agg(day_high=("high", "max"), day_low=("low", "min"))
    shifted = daily.shift(1)
    return (
        dates.map(shifted["day_high"]).to_numpy(dtype=float),
        dates.map(shifted["day_low"]).to_numpy(dtype=float),
    )


def build_completed_session_levels_clocktime(df: pd.DataFrame) -> Dict[str, TimedLevelIndex]:
    """Build session H/L with true clock-time completion and efficient day groups."""
    records: List[Tuple[pd.Timestamp, str, float, float, str]] = []
    dt = df["datetime"]
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    hours = dt.dt.hour.to_numpy(dtype=int)
    normalized = dt.dt.normalize()
    groups: Mapping[pd.Timestamp, np.ndarray] = df.groupby(normalized, sort=True).indices

    sessions = (
        ("ASIA", 0, 8),
        ("LONDON_RESEARCH", 8, 13),
        ("NEW_YORK_RESEARCH", 13, 18),
    )
    for day, idx_like in groups.items():
        idx = np.asarray(idx_like, dtype=int)
        if len(idx) == 0:
            continue
        day_ts = pd.Timestamp(day)
        for label, start_hour, end_hour in sessions:
            mask = (hours[idx] >= start_hour) & (hours[idx] < end_hour)
            sidx = idx[mask]
            if len(sidx) == 0:
                continue
            completion = day_ts + pd.Timedelta(hours=end_hour)
            records.append((completion, "HIGH", float(np.max(highs[sidx])), 0.0, label))
            records.append((completion, "LOW", float(np.min(lows[sidx])), 0.0, label))
    return _make_level_indexes(records)


def build_confirmed_m15_swing_zones(df: pd.DataFrame) -> Dict[str, TimedLevelIndex]:
    """Build fully-confirmed M15 pivots preserving each 0.10*M15 ATR zone.

    A pivot is admitted only when its five-bar flank window contains complete
    and consecutive 15-minute candles. Confirmation occurs at the close of the
    second right-hand bar.
    """
    indexed = df.set_index("datetime")
    m15 = indexed.resample("15min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        count=("close", "count"),
    )
    m15 = m15.dropna(subset=["open", "high", "low", "close"]).reset_index()
    m15["is_complete"] = m15["count"] == 15
    m15["atr14"] = compute_atr14(m15)

    ts = pd.DatetimeIndex(m15["datetime"])
    t_ns = ts.asi8
    hi = m15["high"].to_numpy(dtype=float)
    lo = m15["low"].to_numpy(dtype=float)
    atr = m15["atr14"].to_numpy(dtype=float)
    complete = m15["is_complete"].to_numpy(dtype=bool)

    records: List[Tuple[pd.Timestamp, str, float, float, str]] = []
    f = M15_PIVOT_FLANK
    step_ns = pd.Timedelta(minutes=15).value
    for j in range(f, len(m15) - f):
        w0, w1 = j - f, j + f
        if not np.all(complete[w0 : w1 + 1]):
            continue
        if not np.all(np.diff(t_ns[w0 : w1 + 1]) == step_ns):
            continue
        confirm_idx = j + f
        if not np.isfinite(atr[confirm_idx]) or atr[confirm_idx] <= 0:
            continue
        confirm_time = ts[confirm_idx] + pd.Timedelta(minutes=15)
        width = float(M15_SWING_ZONE_ATR * atr[confirm_idx])

        if hi[j] > np.max(hi[j-f:j]) and hi[j] > np.max(hi[j+1:j+f+1]):
            records.append((confirm_time, "HIGH", float(hi[j]), width, "M15_SWING"))
        if lo[j] < np.min(lo[j-f:j]) and lo[j] < np.min(lo[j+1:j+f+1]):
            records.append((confirm_time, "LOW", float(lo[j]), width, "M15_SWING"))
    return _make_level_indexes(records)


def _candle_intersects_any_zone(
    low: float, high: float, levels: np.ndarray, widths: np.ndarray
) -> bool:
    if len(levels) == 0:
        return False
    return bool(np.any((high >= (levels - widths)) & (low <= (levels + widths))))


def build_mechanism_event_frame(
    df: pd.DataFrame,
    events: Sequence[FailedAuctionEvent],
) -> pd.DataFrame:
    """Create causal ENERGY/LOCATION/REJECTION factors for each event."""
    validate_development_frame(df)
    if not events:
        return pd.DataFrame()

    pdh, pdl = compute_previous_observed_day_levels(df)
    session_idx = build_completed_session_levels_clocktime(df)
    m15_idx = build_confirmed_m15_swing_zones(df)

    tick_volume = df["tick_volume"].to_numpy(dtype=float) if "tick_volume" in df.columns else None
    spread = df["spread"].to_numpy(dtype=float) if "spread" in df.columns else None
    real_volume = df["real_volume"].to_numpy(dtype=float) if "real_volume" in df.columns else None

    rows: List[Dict[str, Any]] = []
    for ev in events:
        t = ev.bar_index
        atr = float(ev.atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue

        o, h, l, c = map(float, (ev.price_open, ev.price_high, ev.price_low, ev.price_close))
        rng = h - l
        if rng <= 0:
            continue

        if ev.side == "LONG":
            signed = 1.0
            event_extreme = l
            sweep_depth = (ev.prior_extreme - l) / atr
            reclaim_depth = (c - ev.prior_extreme) / atr
            close_location = (c - l) / rng
            structural_level = pdl[t]
            wanted_side = "LOW"
        else:
            signed = -1.0
            event_extreme = h
            sweep_depth = (h - ev.prior_extreme) / atr
            reclaim_depth = (ev.prior_extreme - c) / atr
            close_location = (h - c) / rng
            structural_level = pdh[t]
            wanted_side = "HIGH"

        body_snapback_atr = signed * (c - o) / atr
        event_range_atr = rng / atr
        tol = REACTION_DISTANCE_ATR * atr

        pdh_pdl_match = False
        pdh_pdl_distance_atr = np.nan
        if np.isfinite(structural_level):
            pdh_pdl_distance_atr = abs(event_extreme - structural_level) / atr
            pdh_pdl_match = (
                (l <= structural_level <= h) or abs(event_extreme - structural_level) <= tol
            )

        s_levels, s_widths, _ = session_idx[wanted_side].recent_slice(
            ev.datetime, SESSION_LOOKBACK
        )
        session_match = _candle_intersects_any_zone(l, h, s_levels, s_widths)
        if not session_match and len(s_levels):
            session_match = bool(np.any(np.abs(event_extreme - s_levels) <= tol))

        sw_levels, sw_widths, _ = m15_idx[wanted_side].recent_slice(
            ev.datetime, M15_SWING_LOOKBACK
        )
        # Repair vs 001R: actual per-swing 0.10*M15 ATR width is preserved and used.
        m15_match = _candle_intersects_any_zone(l, h, sw_levels, sw_widths)

        energy_count = int(ev.path_eff_match) + int(ev.stretch_z_match) + int(ev.atr_pct_match)
        location_count = int(pdh_pdl_match) + int(session_match) + int(m15_match)

        rows.append(
            {
                "event_id": int(ev.event_id),
                "bar_index": int(t),
                "datetime": pd.Timestamp(ev.datetime),
                "year": int(pd.Timestamp(ev.datetime).year),
                "hour": int(pd.Timestamp(ev.datetime).hour),
                "side": ev.side,
                "prior_extreme": float(ev.prior_extreme),
                "event_close": c,
                "atr14": atr,
                # ENERGY
                "path_efficiency": float(ev.efficiency_ratio),
                "path_eff_match": bool(ev.path_eff_match),
                "stretch_z": float(ev.stretch_z),
                "stretch_abs": abs(float(ev.stretch_z)),
                "stretch_match": bool(ev.stretch_z_match),
                "atr_percentile": float(ev.atr_percentile),
                "atr_pct_match": bool(ev.atr_pct_match),
                "energy_count": energy_count,
                # LOCATION
                "pdh_pdl_match": bool(pdh_pdl_match),
                "pdh_pdl_distance_atr": float(pdh_pdl_distance_atr)
                if np.isfinite(pdh_pdl_distance_atr)
                else np.nan,
                "session_level_match": bool(session_match),
                "m15_swing_zone_match": bool(m15_match),
                "location_count": location_count,
                # REJECTION
                "sweep_depth_atr": float(sweep_depth),
                "reclaim_depth_atr": float(reclaim_depth),
                "event_range_atr": float(event_range_atr),
                "body_snapback_atr": float(body_snapback_atr),
                "close_location_snapback": float(np.clip(close_location, 0.0, 1.0)),
                # Optional activity/friction proxies; never called order flow.
                "tick_volume_raw": float(tick_volume[t]) if tick_volume is not None else np.nan,
                "spread_points_raw": float(spread[t]) if spread is not None else np.nan,
                "real_volume_raw": float(real_volume[t]) if real_volume is not None else np.nan,
            }
        )

    return pd.DataFrame(rows)


def add_gap_aware_state_labels(
    df: pd.DataFrame,
    event_frame: pd.DataFrame,
    horizons: Iterable[int] = HORIZONS_MINUTES,
) -> pd.DataFrame:
    """Attach exact-clock forward states, returns, and contiguous excursions.

    Exact close labels use timestamp lookup, so an existing +5 minute close is
    still labeled even if an intermediate minute is missing. MFE/MAE require a
    truly contiguous minute-by-minute path and are therefore stricter.
    """
    if event_frame.empty:
        return event_frame.copy()

    horizons = tuple(sorted(set(int(h) for h in horizons)))
    if 5 not in horizons:
        raise ValueError("MECH-002 requires the frozen 5-minute primary horizon.")

    out = event_frame.copy()
    dts = pd.DatetimeIndex(df["datetime"])
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)

    event_idx = out["bar_index"].to_numpy(dtype=int)
    event_times = pd.DatetimeIndex(out["datetime"])
    side_sign = np.where(out["side"].to_numpy() == "LONG", 1.0, -1.0)
    event_close = out["event_close"].to_numpy(dtype=float)
    prior = out["prior_extreme"].to_numpy(dtype=float)
    atr = out["atr14"].to_numpy(dtype=float)

    max_h = max(horizons)
    first_reaccepted = np.full(len(out), np.nan)
    missing_any_to_max = np.zeros(len(out), dtype=bool)

    # Threshold-free, close-based transition path at exact clock minutes.
    for minute in range(1, max_h + 1):
        targets = event_times + pd.Timedelta(minutes=minute)
        pos = dts.get_indexer(targets)
        exact = pos >= 0
        missing_any_to_max |= ~exact

        signed_distance = np.full(len(out), np.nan)
        signed_distance[exact] = (
            side_sign[exact] * (closes[pos[exact]] - prior[exact]) / atr[exact]
        )
        newly = np.isnan(first_reaccepted) & exact & (signed_distance < 0.0)
        first_reaccepted[newly] = float(minute)

    out["first_reaccepted_minute_30"] = first_reaccepted
    out[f"gap_any_within_{max_h}m"] = missing_any_to_max

    for h in horizons:
        targets = event_times + pd.Timedelta(minutes=h)
        pos = dts.get_indexer(targets)
        exact = pos >= 0
        # With unique 1-minute data, endpoint index == t+h iff all intermediate minutes exist.
        contiguous = exact & (pos == event_idx + h)

        signed_ret = np.full(len(out), np.nan)
        signed_dist = np.full(len(out), np.nan)
        signed_ret[exact] = (
            side_sign[exact] * (closes[pos[exact]] - event_close[exact]) / event_close[exact]
        )
        signed_dist[exact] = (
            side_sign[exact] * (closes[pos[exact]] - prior[exact]) / atr[exact]
        )

        state = np.full(len(out), "GAP_CONTAMINATED", dtype=object)
        state[exact & (signed_dist > 0.0)] = "SNAPBACK_SIDE"
        state[exact & (signed_dist < 0.0)] = "BREAKOUT_SIDE"
        state[exact & (signed_dist == 0.0)] = "AT_LEVEL"

        out[f"exact_{h}m_available"] = exact
        out[f"continuous_{h}m_path"] = contiguous
        out[f"signed_return_{h}m"] = signed_ret
        out[f"signed_level_distance_atr_{h}m"] = signed_dist
        out[f"close_state_{h}m"] = state

        # Gap-aware excursions. Sliding windows are views; only output max/min arrays are materialized.
        future_max = np.full(len(df), np.nan)
        future_min = np.full(len(df), np.nan)
        if len(df) > h:
            high_windows = np.lib.stride_tricks.sliding_window_view(highs[1:], h)
            low_windows = np.lib.stride_tricks.sliding_window_view(lows[1:], h)
            k = len(high_windows)
            future_max[:k] = np.max(high_windows, axis=1)
            future_min[:k] = np.min(low_windows, axis=1)

        mfe = np.full(len(out), np.nan)
        mae = np.full(len(out), np.nan)
        long_mask = contiguous & (side_sign > 0)
        short_mask = contiguous & (side_sign < 0)

        idx_long = event_idx[long_mask]
        idx_short = event_idx[short_mask]
        mfe[long_mask] = (future_max[idx_long] - event_close[long_mask]) / event_close[long_mask]
        mae[long_mask] = (event_close[long_mask] - future_min[idx_long]) / event_close[long_mask]
        mfe[short_mask] = (event_close[short_mask] - future_min[idx_short]) / event_close[short_mask]
        mae[short_mask] = (future_max[idx_short] - event_close[short_mask]) / event_close[short_mask]

        out[f"mfe_{h}m_gap_aware"] = mfe
        out[f"mae_{h}m_gap_aware"] = mae

    gap5 = ~out["continuous_5m_path"].to_numpy(dtype=bool)
    reaccepted5 = np.isfinite(first_reaccepted) & (first_reaccepted <= 5.0)
    path5 = np.full(len(out), "PERSISTENT_SNAPBACK_SIDE", dtype=object)
    path5[reaccepted5] = "REACCEPTED_BREAKOUT_SIDE"
    path5[gap5] = "GAP_CONTAMINATED"
    out["path_state_5m"] = path5
    return out


def summarize_tail_distribution(values: pd.Series) -> Dict[str, float]:
    """Distribution summary with tail metrics; input values are decimal returns."""
    x = values.dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return {"n": 0}
    probs = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
    q = {p: float(np.quantile(x, p)) for p in probs}
    lo = x[x <= q[0.05]]
    hi = x[x >= q[0.95]]
    return {
        "n": int(len(x)),
        "mean_bps": float(np.mean(x) * 10000.0),
        "median_bps": float(np.median(x) * 10000.0),
        "win_rate_pct": float(np.mean(x > 0.0) * 100.0),
        "std_bps": float(np.std(x, ddof=1) * 10000.0) if len(x) > 1 else 0.0,
        "skew": float(pd.Series(x).skew()) if len(x) > 2 else 0.0,
        "p01_bps": q[0.01] * 10000.0,
        "p05_bps": q[0.05] * 10000.0,
        "p10_bps": q[0.10] * 10000.0,
        "p25_bps": q[0.25] * 10000.0,
        "p50_bps": q[0.50] * 10000.0,
        "p75_bps": q[0.75] * 10000.0,
        "p90_bps": q[0.90] * 10000.0,
        "p95_bps": q[0.95] * 10000.0,
        "p99_bps": q[0.99] * 10000.0,
        "adverse_es_5_bps": float(np.mean(lo) * 10000.0) if len(lo) else np.nan,
        "favorable_es_5_bps": float(np.mean(hi) * 10000.0) if len(hi) else np.nan,
    }
