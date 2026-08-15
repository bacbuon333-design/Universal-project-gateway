"""
===================================================================
ALPHA RESEARCH FACTORY: PYRAMIDING RISK MANAGER
===================================================================
Executes Dynamic Compounding Lot Sizing & Risk-Free Pyramiding:
1. Dynamic Compounding Lot: Lot = (Equity * Risk%) / (SL Points * 0.01).
2. Risk-Free Pyramiding: When profit reaches +1.5x SL, moves SL to Entry + Spread.
3. Position Addition: Opens secondary pyramided trade (0.5x lot) on strong trend continuation.

Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import math
from dataclasses import dataclass
from typing import Optional

PIP_SIZE = 0.01          # XM Gold pip size ($0.01)
POINT_VALUE = 0.01       # USD per point per 0.01 lot
COMMISSION_PER_001LOT_RT = 0.07  # $7/lot ($0.07 / 0.01 lot)

@dataclass
class FactoryPosition:
    id: int = 0
    strategy: str = ""
    direction: str = ""      # BUY / SELL
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    lot_size: float = 0.01
    is_pyramid: bool = False
    pyramided_child: bool = False
    sl_pts: float = 0.0
    open_time: object = None

class PyramidingRiskManager:
    def __init__(self, risk_pct: float = 0.015, spread_pts: float = 25.0, max_lot: float = 50.0):
        self.risk_pct = risk_pct
        self.spread_pts = spread_pts
        self.max_lot = max_lot

    def calc_compounding_lot(self, equity: float, sl_pts: float) -> float:
        """Calculates dynamic compounding lot size based on current equity."""
        if sl_pts <= 0 or equity <= 0:
            return 0.01
        risk_usd = equity * self.risk_pct
        cost_per_001 = sl_pts * 0.01
        if cost_per_001 <= 0:
            return 0.01
        units_001 = risk_usd / cost_per_001
        lot = round(units_001 * 0.01, 2)
        return max(0.01, min(lot, self.max_lot))

    def evaluate_pyramiding(self, pos: FactoryPosition, current_high: float, current_low: float) -> Optional[FactoryPosition]:
        """
        Evaluates Risk-Free Pyramiding:
        If profit reaches +1.5x SL, moves SL to Entry + Spread (Risk-Free).
        Returns a secondary pyramided FactoryPosition (0.5x lot) if eligible.
        """
        if pos.pyramided_child:
            return None
            
        spread_adj = self.spread_pts * PIP_SIZE
        
        if pos.direction == "BUY":
            profit_dist = current_high - pos.entry
            sl_dist = pos.entry - pos.sl
            
            # Risk-Free Breakeven Shift
            if profit_dist >= sl_dist * 1.5 and pos.sl < pos.entry:
                pos.sl = pos.entry + spread_adj
                pos.pyramided_child = True
                
                # Create Secondary Pyramided Position (0.5x lot with tight SL)
                new_entry = current_high
                new_sl = new_entry - (sl_dist * 0.6)
                new_tp = pos.tp
                new_lot = round(pos.lot_size * 0.5, 2)
                
                if new_lot >= 0.01:
                    return FactoryPosition(
                        id=pos.id + 10000,
                        strategy=pos.strategy + "_PYRAMID",
                        direction="BUY",
                        entry=new_entry,
                        sl=new_sl,
                        tp=new_tp,
                        lot_size=new_lot,
                        is_pyramid=True,
                        pyramided_child=True,
                        sl_pts=pos.sl_pts
                    )

        elif pos.direction == "SELL":
            profit_dist = pos.entry - current_low
            sl_dist = pos.sl - pos.entry
            
            if profit_dist >= sl_dist * 1.5 and pos.sl > pos.entry:
                pos.sl = pos.entry - spread_adj
                pos.pyramided_child = True
                
                new_entry = current_low
                new_sl = pos.entry - spread_adj
                new_tp = new_entry - (pos.entry - pos.tp)
                new_lot = round(pos.lot_size * 0.5, 2)
                
                if new_lot >= 0.01:
                    return FactoryPosition(
                        id=pos.id + 10000,
                        strategy=pos.strategy + "_PYRAMID",
                        direction="SELL",
                        entry=new_entry,
                        sl=new_sl,
                        tp=new_tp,
                        lot_size=new_lot,
                        is_pyramid=True,
                        pyramided_child=True,
                        sl_pts=pos.sl_pts
                    )
                    
        return None
