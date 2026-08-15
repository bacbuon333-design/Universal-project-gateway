"""
===================================================================
ALPHA RESEARCH FACTORY: MULTI-TIMEFRAME REGIME DETECTOR
===================================================================
Classifies market microstructure into high-conviction regimes:
1. TRENDING: HTF EMA 200 alignment + ADX >= 20.
2. VOLATILITY_EXPANSION: ATR 14 / ATR 100 ratio >= 1.20.
3. CHOP: Filters out low-expectancy mean-reversion noise.

Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple

class MTFRegimeDetector:
    @staticmethod
    def compute_regimes(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        # Moving Averages
        ema_8 = pd.Series(close).ewm(span=8, adjust=False).mean().values
        ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().values
        ema_100 = pd.Series(close).ewm(span=100, adjust=False).mean().values
        ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values
        
        # ATR & Volatility Ratio
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr = np.append([0.0], tr)
        atr14 = pd.Series(tr).rolling(14).mean().values
        atr_avg = pd.Series(atr14).rolling(100).mean().values
        
        # ADX 14
        up = pd.Series(high).diff()
        dn = -pd.Series(low).diff()
        pdm = up.where((up > dn) & (up > 0), 0.0)
        ndm = dn.where((dn > up) & (dn > 0), 0.0)
        atr_adx = pd.Series(tr).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        pdi = 100 * pdm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
        ndi = 100 * ndm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-10)
        adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean().values
        
        regimes = ["" for _ in range(n)]
        trend_directions = np.zeros(n, dtype=int) # +1 Bull, -1 Bear, 0 Neutral
        
        for i in range(201, n):
            c_val = close[i]
            a_val = atr14[i] if atr14[i] > 0 else 1.5
            a_avg = atr_avg[i] if atr_avg[i] > 0 else 1.5
            adx_val = adx[i]
            vol_ratio = a_val / a_avg
            
            # Trend Direction Alignment
            if c_val > ema_200[i] and ema_8[i] > ema_21[i]:
                trend_directions[i] = 1 # Bullish Trend
            elif c_val < ema_200[i] and ema_8[i] < ema_21[i]:
                trend_directions[i] = -1 # Bearish Trend
            else:
                trend_directions[i] = 0
                
            # Regime Classification
            if vol_ratio >= 1.20:
                regimes[i] = "VOLATILITY_EXPANSION"
            elif adx_val >= 20 and trend_directions[i] != 0:
                regimes[i] = "TRENDING"
            else:
                regimes[i] = "CHOP"
                
        return np.array(regimes), trend_directions, atr14, adx, ema_200
