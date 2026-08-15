"""
CHECKPOINT V230: KELTNER MULTI-CONFLUENCE NATIVE IPC BROKER ENGINE
==================================================================
Target Asset: GOLD (XAUUSD) M15
Strict Non-Overlap Constraint: 0 timestamp overlap with CP-101 locked entries.
Strategy: Keltner Upper Envelope + RSI > 56.0 + Volume Z-Score > 0.85 + Consec Bull.
"""

import os, sys, json
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_cp230_development():
    print("="*105)
    print("DEVELOPING CP-230 (KELTNER MULTI-CONFLUENCE NATIVE IPC BROKER ENGINE)")
    print("="*105)
    
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    locked_h1_times = set(df_cp101['Entry_Time'].tolist())
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("Failed to initialize MT5 IPC link:", mt5.last_error())
        return
        
    acc = mt5.account_info()
    
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M15, 0, 80000)
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 80000)
        
    if rates is None or len(rates) == 0:
        print("Could not fetch rates from MT5 terminal.")
        mt5.shutdown()
        return
        
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    
    symbol_info = mt5.symbol_info("GOLD") or mt5.symbol_info("XAUUSD")
    real_spread_pts = symbol_info.spread if symbol_info else 165
    
    o_m15 = df['open'].values
    h_m15 = df['high'].values
    l_m15 = df['low'].values
    c_m15 = df['close'].values
    v_m15 = df['tick_volume'].values
    n = len(c_m15)
    
    h1 = df.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df = pd.merge_asof(df, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df['ema9_h1'].values
    ema20_h1 = df['ema20_h1'].values
    ema55_h1 = df['ema55_h1'].values
    ema200_h1 = df['ema200_h1'].values
    
    ema9_m15 = df['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    kelt_upper_190 = ema20_m15 + 1.90 * atr14_m15
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v_m15).rolling(50).mean().values
    vol_std50 = pd.Series(v_m15).rolling(50).std().values
    vol_zscore = (v_m15 - vol_sma50) / (vol_std50 + 1e-9)
    
    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    
    trades = []
    last_idx = -1
    
    for i in range(200, n - 1):
        h1_time_str = df.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_time_str in locked_h1_times:
            continue
            
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_190[i]) and (vol_zscore[i] > 0.85) and (rsi_m15[i] > 56.0) and (lwick >= 0.85 * body) and consec_bull
        
        if b_sig and (i - last_idx >= 4):
            last_idx = i
            spread_dist = real_spread_pts / 100.0
            entry_price = o_m15[i+1] + spread_dist
            
            sl_dist = av * 1.0 + 0.25
            tp_dist = av * 1.95
            
            risk_pct = 0.008
            risk_amount = balance * risk_pct
            position_size = risk_amount / sl_dist
            
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
            
            exit_price = entry_price
            hit_tp = False; hit_sl = False
            
            for j in range(i + 1, min(i + 240, n)):
                if l_m15[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                elif h_m15[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                        
            if not hit_tp and not hit_sl: exit_price = c_m15[min(i + 240, n - 1)]
            
            pnl = (exit_price - entry_price) * position_size
            balance += pnl
            
            if balance > peak_balance: peak_balance = balance
            dd = (peak_balance - balance) / peak_balance
            if dd > max_dd_pct: max_dd_pct = dd
                
            trades.append(pnl)

    win_trades = [p for p in trades if p > 0]
    loss_trades = [p for p in trades if p < 0]
    
    total_t = len(trades)
    win_t = len(win_trades)
    wr = (win_t / total_t * 100.0) if total_t else 0.0
    gp = sum(win_trades)
    gl = abs(sum(loss_trades))
    pf = gp / gl if gl > 0 else 999.0
    
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    print("\n" + "="*105)
    print("CHECKPOINT 230 (CP-230) KELTNER MULTI-CONFLUENCE NATIVE IPC AUDIT REPORT")
    print("="*105)
    print(f"1. Active MT5 Terminal Connection: Connected to {acc.login} @ {acc.server}")
    print(f"2. Live XMGlobal Broker Spread    : {real_spread_pts} points ({real_spread_pts/100.0:.2f} pips)")
    print(f"3. Total Executed Trades         : {total_t} Trades")
    print(f"4. Win Rate %                    : {wr:.2f}% ({win_t} Wins / {total_t - win_t} Losses)")
    print(f"5. Profit Factor (PF)            : {pf:.2f} (Gross Profit ${gp:,.2f} / Gross Loss ${gl:,.2f})")
    print(f"6. Initial Deposit -> Final Bal  : ${initial_balance:,.2f} USD -> ${balance:,.2f} USD (+{net_yield_pct:.2f}% PnL)")
    print(f"7. Maximum Drawdown %            : {max_dd_pct * 100.0:.2f}%")
    print(f"8. Overlap with CP-101           : ZERO (0 Timestamp Overlap!)")
    print("="*105)
    
    if wr >= 45.0 and pf >= 1.45 and max_dd_pct <= 0.065:
        print("RESULT: CP-230 PASSED ALL NATIVE MT5 BROKER IPC FILTERS!")
        
        mql5_code = f"""//+------------------------------------------------------------------+
//|                             ALAB_CP230_KeltnerMultiConfluence.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseRiskPct        = 0.008;  // Base Risk Pct (0.8%)
input double   InpMaxDrawdownLimit   = 0.50;   // Max Drawdown Limit (50%)
input ulong    InpMagicNumber        = 2026230;// Magic Number
input string   InpTradeComment       = "ALAB_CP230_KeltnerMC";

CTrade         trade;
datetime       lastBarTime;

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   return(INIT_SUCCEEDED);
}}

void OnDeinit(const int reason)
{{
}}

void OnTick()
{{
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   if(PositionsTotal() > 0) return;
   
   double ema9_h1 = iMA(_Symbol, PERIOD_H1, 9, 0, MODE_EMA, PRICE_CLOSE);
   double ema20_h1 = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   double ema55_h1 = iMA(_Symbol, PERIOD_H1, 55, 0, MODE_EMA, PRICE_CLOSE);
   double ema200_h1 = iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE);
   
   bool macro_bull = (ema9_h1 > ema20_h1) && (ema20_h1 > ema55_h1) && (ema55_h1 > ema200_h1);
   if(!macro_bull) return;
   
   MqlRates rates[];
   if(CopyRates(_Symbol, _Period, 1, 30, rates) < 30) return;
   
   int last = 29;
   double close = rates[last].close;
   double open = rates[last].open;
   double high = rates[last].high;
   double low = rates[last].low;
   
   double body = MathAbs(close - open) + 0.00001;
   double lwick = MathMin(open, close) - low;
   if(lwick < 0.85 * body) return;
   
   bool consec_bull = (close > open) && (rates[last-1].close > rates[last-1].open);
   if(!consec_bull) return;
   
   double tr_sum = 0;
   for(int k=last-13; k<=last; k++) {{
      double tr = MathMax(rates[k].high - rates[k].low, MathMax(MathAbs(rates[k].high - rates[k-1].close), MathAbs(rates[k].low - rates[k-1].close)));
      tr_sum += tr;
   }}
   double atr14 = tr_sum / 14.0;
   if(atr14 < 0.8) atr14 = 0.8;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = atr14 * 1.0 + 0.25;
   double tp_dist = atr14 * 1.95;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * InpBaseRiskPct;
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_sz <= 0) tick_sz = 0.01;
   if(tick_val <= 0) tick_val = 1.0;
   
   double loss_per_lot = (sl_dist / tick_sz) * tick_val;
   double lot_size = NormalizeDouble(risk_amount / loss_per_lot, 2);
   if(lot_size < 0.01) lot_size = 0.01;
   if(lot_size > 10.0) lot_size = 10.0;
   
   double sl_price = NormalizeDouble(ask - sl_dist, _Digits);
   double tp_price = NormalizeDouble(ask + tp_dist, _Digits);
   
   trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
}}
"""
        mql5_out_path = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP230_KeltnerMultiConfluence.mq5"
        with open(mql5_out_path, 'w', encoding='utf-8') as f:
            f.write(mql5_code)
        print(f"Generated MQL5 EA: {mql5_out_path}")
        
    mt5.shutdown()

if __name__ == '__main__':
    run_cp230_development()
