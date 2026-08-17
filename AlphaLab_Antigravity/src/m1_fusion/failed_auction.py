from __future__ import annotations

"""Failed Auction detection and Reaction Score computation for ALAB-M1-FUSION-001."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from .features import (
    PRIOR_EXTREME_LOOKBACK,
    PATH_WINDOW,
    EFFICIENCY_THRESHOLD,
    ROBUST_WINDOW,
    ROBUST_Z_THRESHOLD,
    ATR_PERCENTILE_THRESHOLD,
    compute_atr14,
    compute_prior_extremes,
    compute_path_efficiency,
    compute_robust_stretch_z,
    compute_atr_percentiles,
)
from .reaction_zones import (
    REACTION_DISTANCE_ATR,
    compute_pdh_pdl,
    compute_completed_session_levels,
    compute_m15_swings,
)


@dataclass(frozen=True)
class FailedAuctionEvent:
    event_id: int
    bar_index: int
    datetime: pd.Timestamp
    side: str  # "LONG" or "SHORT"
    failed_auction: bool
    prior_extreme: float
    price_open: float
    price_high: float
    price_low: float
    price_close: float
    efficiency_ratio: float
    path_eff_match: bool
    stretch_z: float
    stretch_z_match: bool
    atr14: float
    atr_percentile: float
    atr_pct_match: bool
    pdh_pdl_match: bool
    session_level_match: bool
    m15_swing_match: bool
    reaction_score: int
    score_bin: str


def detect_failed_auction_events(df: pd.DataFrame) -> List[FailedAuctionEvent]:
    """Detect all causal failed auction events and compute their reaction scores."""
    n = len(df)
    if n < 550:
        return []

    # 1. Base features
    atr = compute_atr14(df)
    prior_high, prior_low = compute_prior_extremes(df, PRIOR_EXTREME_LOOKBACK)
    eff_ratio, is_up, is_down = compute_path_efficiency(df, PATH_WINDOW)
    stretch_z = compute_robust_stretch_z(df, ROBUST_WINDOW)
    atr_pct = compute_atr_percentiles(atr, 500)

    # 2. Reaction zones
    pdh_arr, pdl_arr = compute_pdh_pdl(df)
    session_highs, session_lows = compute_completed_session_levels(df)
    m15_highs, m15_lows = compute_m15_swings(df, flank=2)

    # Arrays for fast iteration
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    dts = df["datetime"]
    atr_vals = atr.to_numpy(dtype=float)
    ph_vals = prior_high.to_numpy(dtype=float)
    pl_vals = prior_low.to_numpy(dtype=float)

    events: List[FailedAuctionEvent] = []
    event_counter = 0

    # Start after warm-up of 510 bars to ensure all rolling indicators have matured
    for t in range(510, n - 35):
        c_atr = atr_vals[t]
        if not np.isfinite(c_atr) or c_atr <= 0:
            continue

        c_open = opens[t]
        c_high = highs[t]
        c_low = lows[t]
        c_close = closes[t]
        c_dt = dts.iloc[t]

        # Check Short Failed Auction
        is_short_fa = False
        if np.isfinite(ph_vals[t]):
            if c_high > ph_vals[t] and c_close < ph_vals[t]:
                is_short_fa = True

        # Check Long Failed Auction
        is_long_fa = False
        if np.isfinite(pl_vals[t]):
            if c_low < pl_vals[t] and c_close > pl_vals[t]:
                is_long_fa = True

        if not (is_short_fa or is_long_fa):
            continue

        # In the extremely rare case of both (huge wick both ways), skip or prioritize
        if is_short_fa and is_long_fa:
            continue

        side = "SHORT" if is_short_fa else "LONG"
        prior_ext = ph_vals[t] if is_short_fa else pl_vals[t]

        # Score components
        # 1. Failed auction (mandatory): +3
        score = 3

        # 2. Path efficiency: +1
        c_eff = eff_ratio[t]
        eff_match = False
        if side == "SHORT" and is_up[t] and c_eff >= EFFICIENCY_THRESHOLD:
            eff_match = True
            score += 1
        elif side == "LONG" and is_down[t] and c_eff >= EFFICIENCY_THRESHOLD:
            eff_match = True
            score += 1

        # 3. Robust stretch: +1
        c_z = stretch_z[t]
        z_match = False
        if side == "SHORT" and c_z >= ROBUST_Z_THRESHOLD:
            z_match = True
            score += 1
        elif side == "LONG" and c_z <= -ROBUST_Z_THRESHOLD:
            z_match = True
            score += 1

        # 4. Volatility percentile: +1
        c_atr_pct = atr_pct[t]
        atr_pct_match = False
        if c_atr_pct >= ATR_PERCENTILE_THRESHOLD:
            atr_pct_match = True
            score += 1

        # 5. PDH / PDL: +2
        pdh_pdl_match = False
        tol = REACTION_DISTANCE_ATR * c_atr
        if side == "SHORT" and np.isfinite(pdh_arr[t]):
            pdh = pdh_arr[t]
            if (c_low <= pdh <= c_high) or (abs(c_high - pdh) <= tol):
                pdh_pdl_match = True
                score += 2
        elif side == "LONG" and np.isfinite(pdl_arr[t]):
            pdl = pdl_arr[t]
            if (c_low <= pdl <= c_high) or (abs(c_low - pdl) <= tol):
                pdh_pdl_match = True
                score += 2

        # 6. Completed session extreme: +1
        sess_match = False
        if side == "SHORT":
            for s_h in session_highs[t]:
                if (c_low <= s_h <= c_high) or (abs(c_high - s_h) <= tol):
                    sess_match = True
                    score += 1
                    break
        else:
            for s_l in session_lows[t]:
                if (c_low <= s_l <= c_high) or (abs(c_low - s_l) <= tol):
                    sess_match = True
                    score += 1
                    break

        # 7. Confirmed M15 swing: +1
        m15_match = False
        if side == "SHORT":
            for sw_h in m15_highs[t]:
                if (c_low <= sw_h <= c_high) or (abs(c_high - sw_h) <= tol):
                    m15_match = True
                    score += 1
                    break
        else:
            for sw_l in m15_lows[t]:
                if (c_low <= sw_l <= c_high) or (abs(c_low - sw_l) <= tol):
                    m15_match = True
                    score += 1
                    break

        # Score bin
        if score <= 4:
            s_bin = "3-4"
        elif score <= 6:
            s_bin = "5-6"
        elif score <= 8:
            s_bin = "7-8"
        else:
            s_bin = "9-10"

        event = FailedAuctionEvent(
            event_id=event_counter,
            bar_index=t,
            datetime=c_dt,
            side=side,
            failed_auction=True,
            prior_extreme=prior_ext,
            price_open=c_open,
            price_high=c_high,
            price_low=c_low,
            price_close=c_close,
            efficiency_ratio=c_eff,
            path_eff_match=eff_match,
            stretch_z=c_z,
            stretch_z_match=z_match,
            atr14=c_atr,
            atr_percentile=c_atr_pct,
            atr_pct_match=atr_pct_match,
            pdh_pdl_match=pdh_pdl_match,
            session_level_match=sess_match,
            m15_swing_match=m15_match,
            reaction_score=score,
            score_bin=s_bin,
        )
        events.append(event)
        event_counter += 1

    return events
