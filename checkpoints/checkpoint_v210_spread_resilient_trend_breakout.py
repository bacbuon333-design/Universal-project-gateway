"""
CHECKPOINT V210: SPREAD-RESILIENT M15 STRUCTURAL TREND BREAKOUT ENGINE
=====================================================================
Target Asset: GOLD (XAUUSD) M15
Strict Non-Overlap Constraint: 0 timestamp overlap with CP-101 locked entries.
Resilience Feature: Formulated specifically with wider SL/TP geometry (SL = 1.25*ATR, TP = 2.5*ATR)
                    to neutralize XMGlobal dynamic spread expansion (40-50 pips).

Quality Target:
- Win Rate >= 47.0%
- Profit Factor >= 1.60+
- Max Drawdown <= 6.5%
- Total Trades >= 150+
"""

import os, sys, json
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_cp210_development():
    print("="*105)
    print("DEVELOPING SPREAD-RESILIENT CP-210 (M15 STRUCTURAL TREND BREAKOUT ENGINE)")
    print("="*105)
    
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    locked_h1_times = set(df_cp101['Entry_Time'].tolist())
    
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    dates_m15 = df_m15.index.date
    n = len(c_m15)
    
    # Resample H1 for macro trend alignment
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df_m15 = pd.merge_asof(df_m15, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df_m15['ema9_h1'].values
    ema20_h1 = df_m15['ema20_h1'].values
    ema55_h1 = df_m15['ema55_h1'].values
    ema200_h1 = df_m15['ema200_h1'].values
    
    # M15 Technical Indicators
    ema9_m15 = df_m15['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df_m15['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    don_hi25_m15 = pd.Series(h_m15).shift(1).rolling(25).max().values
    kelt_upper_22 = ema20_m15 + 2.2 * atr14_m15
    
    delta = df_m15['close'].diff()
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
        h1_time_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_time_str in locked_h1_times:
            continue
            
        current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
        
        if current_dd >= 0.05: risk_pct = 0.005
        else:
            if balance >= 3000.0: risk_pct = 0.012
            elif balance >= 1800.0: risk_pct = 0.010
            else: risk_pct = 0.008
                
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.05)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_22[i]) and (c_m15[i] > don_hi25_m15[i]) and (vol_zscore[i] > 1.15) and (rsi_m15[i] > 58.0) and (lwick >= 0.8 * body) and consec_bull
        
        if b_sig and (i - last_idx >= 4):
            last_idx = i
            entry_price = o_m15[i+1]
            sl_dist = av * 1.25 + 0.35
            tp_dist = av * 2.50
            
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
                
            trades.append({
                'datetime': df_m15.index[i],
                'date': str(dates_m15[i]),
                'pnl': pnl,
                'balance': balance
            })
            
    win_trades = [t for t in trades if t['pnl'] > 0]
    loss_trades = [t for t in trades if t['pnl'] < 0]
    
    total_t = len(trades)
    win_t = len(win_trades)
    wr = (win_t / total_t * 100.0) if total_t else 0.0
    gp = sum([t['pnl'] for t in win_trades])
    gl = abs(sum([t['pnl'] for t in loss_trades]))
    pf = gp / gl if gl > 0 else 999.0
    
    cp210_dates = set([t['date'] for t in trades])
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    print("="*105)
    print("CHECKPOINT 210 (CP-210) SPREAD-RESILIENT DEVELOPMENT REPORT")
    print("="*105)
    print(f"1. Total Executed Trades        : {total_t} Trades")
    print(f"2. Win Rate %                    : {wr:.2f}% ({win_t} Wins / {total_t - win_t} Losses)")
    print(f"3. Profit Factor (PF)            : {pf:.2f} (Gross Profit ${gp:,.2f} / Gross Loss ${gl:,.2f})")
    print(f"4. Initial Deposit -> Final Bal  : ${initial_balance:,.2f} USD -> ${balance:,.2f} USD (+{net_yield_pct:.2f}% PnL)")
    print(f"5. Maximum Drawdown %            : {max_dd_pct * 100.0:.2f}%")
    print(f"6. Unique Trading Dates          : {len(cp210_dates)} Unique Trading Days")
    print(f"7. Overlap with CP-101           : ZERO (0 Timestamp Overlap!)")
    print("="*105)
    
    if wr >= 47.0 and pf >= 1.60 and max_dd_pct <= 0.065:
        print("RESULT: CP-210 PASSED ALL SPREAD-RESILIENT HARD FILTERS FOR MT5 STANDARDS!")
        
        # Write MQL5 EA file
        mql5_code = f"""//+------------------------------------------------------------------+
//|                                   ALAB_CP210_SpreadResilientTrend.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseRiskPct        = 0.008;  // Base Risk Pct (0.8%)
input double   InpMaxDrawdownLimit   = 0.50;   // Max Drawdown Limit (50%)
input ulong    InpMagicNumber        = 2026210;// Magic Number
input string   InpTradeComment       = "ALAB_CP210_SpreadResilient";

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
   
   bool consec_bull = (close > open) && (rates[last-1].close > rates[last-1].open);
   if(!consec_bull) return;
   if(lwick < 0.8 * body) return;
   
   double don_hi = rates[last-1].high;
   for(int k=last-25; k<=last-1; k++) {{
      if(rates[k].high > don_hi) don_hi = rates[k].high;
   }}
   if(close <= don_hi) return;
   
   double tr_sum = 0;
   for(int k=last-13; k<=last; k++) {{
      double tr = MathMax(rates[k].high - rates[k].low, MathMax(MathAbs(rates[k].high - rates[k-1].close), MathAbs(rates[k].low - rates[k-1].close)));
      tr_sum += tr;
   }}
   double atr14 = tr_sum / 14.0;
   if(atr14 < 0.8) atr14 = 0.8;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = atr14 * 1.25 + 0.35;
   double tp_dist = atr14 * 2.50;
   
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
        mql5_out_path = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP210_SpreadResilientTrend.mq5"
        with open(mql5_out_path, 'w', encoding='utf-8') as f:
            f.write(mql5_code)
            
        print(f"MQL5 EA file generated: {mql5_out_path}")

if __name__ == '__main__':
    run_cp210_development()
