"""
PREREGISTRATION MANIFEST FOR CP-1500 MASTER FLAGSHIP EA
========================================================
"""

import os, sys, json, hashlib

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
GOV_DIR = os.path.join(DATA_DIR, "governance")
os.makedirs(GOV_DIR, exist_ok=True)
MANIFEST_PATH = os.path.join(GOV_DIR, "cp1500_master_flagship_v1.json")

manifest_data = {
    "version": "1.0",
    "architecture_name": "ALAB_CP1500_MasterFlagshipEA",
    "hypothesis": "Triple H1 EMA alignment (EMA9 > EMA20 > EMA55 > EMA200) combined with M15 EMA9/20 direction, Bollinger Band breakout, RSI momentum, Wick Reversion filter, and Dynamic Equity Drawdown Risk Brake (3.5% base risk, reduced to 1.4% when drawdown >= 6.0%). 100% causal closed-bar shift 1 signals, per-tick hard equity DD protection, and exact risk budget volume sizing using OrderCalcProfit on 100% real tick server history.",
    "target_asset": "GOLD",
    "period": "M15",
    "from_date": "2023.11.17",
    "to_date": "2026.07.27",
    "initial_deposit": 1000.0,
    "leverage": "1:500",
    "tester_model": 4,
    "model_name": "Model=4 Real Ticks",
    "target_gates": {
        "min_net_profit_usd": 1000.0,
        "min_profit_factor": 1.50,
        "min_win_rate_pct": 38.0,
        "max_equity_drawdown_pct": 20.0,
        "absolute_equity_dd_ceiling_pct": 25.0,
        "min_history_quality_pct": 99.0
    },
    "risk_parameters": {
        "base_risk_pct": 3.5,
        "dd_brake_trigger_pct": 6.0,
        "dd_brake_risk_mult": 0.40,
        "hard_equity_dd_cutoff_pct": 20.0,
        "max_open_positions": 1,
        "stop_loss_atr_mult": 1.1,
        "take_profit_atr_mult": 3.2
    },
    "directional_rules": {
        "buy_leg_enabled": True,
        "sell_leg_enabled": False,
        "buy_condition": "H1 EMA9 > EMA20 > EMA55 > EMA200 AND M15 EMA9 > EMA20 AND ATR_14 >= ATR_50 * 1.05 AND Close[1] > Upper_BB AND Vol_ZScore > 1.0 AND RSI > 58.0 AND LowerWick >= 0.85 * Body AND ConsecBull"
    },
    "execution_contract": {
        "shift_index": 1,
        "hard_dd_check_freq": "EVERY_TICK",
        "volume_calculation": "OrderCalcProfit",
        "margin_check": "OrderCalcMargin",
        "order_check_required": True,
        "magic_number": 20261500
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
