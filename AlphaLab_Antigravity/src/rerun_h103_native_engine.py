"""
RERUN H-103 NATIVE CROSS-ASSET TRANSFER EXPERIMENT
==================================================
Runs H-103 through the native asset-aware DeepQuantEngine without any post-hoc rescaling.
"""

import os
import sys
import pandas as pd
from deep_quant_engine import DeepQuantEngine, STANDARD_SPECS
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def rerun_h103():
    print("=" * 95)
    print("🌐 RERUNNING H-103 NATIVE CROSS-ASSET TRANSFER (NO POST-HOC RESCALING)")
    print("=" * 95)
    
    sig_fn_h1 = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    
    datasets = [
        ("GOLD_H1_2001_2026.csv", "XAUUSD (Gold)", 25.0),
        ("EURUSD_H1.csv", "EURUSD", 1.5),
        ("GBPUSD_H1.csv", "GBPUSD", 1.8),
        ("USDJPY_H1.csv", "USDJPY", 1.8),
        ("BTCUSD_H1.csv", "BTCUSD", 50.0)
    ]
    
    results = []
    for fname, name, spr in datasets:
        eng = DeepQuantEngine(fname)
        tdf, qdf, summ = eng.run_strategy(sig_fn_h1, spread_pips=spr, commission_per_lot=7.0, fixed_lot=0.10)
        
        results.append({
            'Asset Symbol': name,
            'Asset Class': eng.spec.asset_class,
            'Contract Size (0.10 lot)': f"{0.10 * eng.spec.contract_size:g} {eng.spec.quote_currency if eng.spec.asset_class=='FOREX_USD_BASE' else 'units'}",
            'History Span': f"{len(eng.df['year'].unique())} yrs",
            'Total Trades': summ['total_trades'],
            'Net PnL (USD)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Avg Expectancy': f"${summ['avg_expectancy_usd']:+.2f} ({summ['avg_expectancy_r']:+.3f} R)",
            'Scientific Verdict': 'SURVIVES (POSITIVE EDGE)' if summ['total_pnl_usd'] > 0 and summ['overall_pf'] >= 1.20 else 'FAILS TRANSFER'
        })
        
    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_2"), exist_ok=True)
    out_p = os.path.join(os.path.dirname(__file__), "..", "reports", "v3_2", "h103_rerun_native_results.csv")
    res_df.to_csv(out_p, index=False)
    print(f"\nSaved H-103 rerun results to {out_p}")
    return res_df

if __name__ == '__main__':
    rerun_h103()
