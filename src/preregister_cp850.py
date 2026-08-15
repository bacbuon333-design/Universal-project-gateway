"""
PREREGISTRATION MANIFEST FOR CP-850 MULTI-TIMEFRAME EA
======================================================
"""

import os, sys, json, hashlib

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
GOV_DIR = os.path.join(DATA_DIR, "governance")
os.makedirs(GOV_DIR, exist_ok=True)
MANIFEST_PATH = os.path.join(GOV_DIR, "cp850_multi_timeframe_v1.json")

manifest_data = {
    "version": "1.0",
    "architecture_name": "ALAB_CP850_MultiTimeframeEA",
    "hypothesis": "Causal multi-timeframe EMA trend alignment (H1 EMA9/20 and M15 EMA9/20) with M15 price momentum breakout. 100% causal closed-bar signals (shift 1), per-tick hard equity drawdown protection, BarsCalculated handle readiness check, and exact risk budget sizing using OrderCalcProfit.",
    "target_asset": "GOLD",
    "period": "M15",
    "from_date": "2022.05.01",
    "to_date": "2026.07.27",
    "initial_deposit": 1000.0,
    "leverage": "1:500",
    "tester_model": 4,
    "model_name": "Model=4 Real Ticks",
    "target_gates": {
        "min_net_profit_usd": 5000.0,
        "min_profit_factor": 1.50,
        "min_win_rate_pct": 45.0,
        "max_equity_drawdown_pct": 20.0,
        "absolute_equity_dd_ceiling_pct": 25.0,
        "min_history_quality_pct": 99.0
    },
    "risk_parameters": {
        "base_risk_pct": 3.5,
        "hard_equity_dd_cutoff_pct": 20.0,
        "max_open_positions": 1,
        "stop_loss_atr_mult": 1.2,
        "take_profit_atr_mult": 2.4
    },
    "directional_rules": {
        "buy_leg_enabled": True,
        "sell_leg_enabled": True,
        "buy_condition": "H1 EMA9 > EMA20 AND M15 EMA9 > EMA20 AND Close[1] > Open[1]",
        "sell_condition": "H1 EMA9 < EMA20 AND M15 EMA9 < EMA20 AND Close[1] < Open[1]"
    },
    "execution_contract": {
        "shift_index": 1,
        "hard_dd_check_freq": "EVERY_TICK",
        "volume_calculation": "OrderCalcProfit",
        "margin_check": "OrderCalcMargin",
        "order_check_required": True,
        "magic_number": 2026850
    }
}

def preregister():
    content_str = json.dumps(manifest_data, indent=2)
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content_str)
    
    manifest_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    print("="*105)
    print(f"PREREGISTRATION MANIFEST CREATED: {MANIFEST_PATH}")
    print(f"SHA-256 HASH: {manifest_hash}")
    print("="*105)

if __name__ == '__main__':
    preregister()
