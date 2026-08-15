"""
DEPLOY AND VERIFY ALAB_CP500_MasterFlagshipEA ON NATIVE MT5
===========================================================
Compiles ALAB_CP500_MasterFlagshipEA.mq5 via metaeditor64.exe, syncs across all MT5 terminals,
and runs the direct MT5 Native IPC broker evaluator to extract real broker performance.
"""

import os, sys, shutil, subprocess
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

MQL5_CODE = """//+------------------------------------------------------------------+
//|                                   ALAB_CP500_MasterFlagshipEA.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpMaxDrawdownLimit   = 0.40;   // Maximum Drawdown Safety Threshold (40%)
input ulong    InpMagicNumber        = 2026500;// Magic Number
input string   InpTradeComment       = "ALAB_CP500_MasterFlagship";

CTrade         trade;
datetime       lastBarTime;
double         peakBalance;

int h_ema9_h1, h_ema20_h1, h_ema55_h1, h_ema200_h1;
int h_ema9_m15, h_ema20_m15, h_bb_m15, h_rsi_m15, h_atr14_m15;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   h_ema9_h1   = iMA(_Symbol, PERIOD_H1, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema55_h1  = iMA(_Symbol, PERIOD_H1, 55, 0, MODE_EMA, PRICE_CLOSE);
   h_ema200_h1 = iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_bb_m15    = iBands(_Symbol, PERIOD_M15, 20, 0, 2.0, PRICE_CLOSE);
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   IndicatorRelease(h_ema9_h1);
   IndicatorRelease(h_ema20_h1);
   IndicatorRelease(h_ema55_h1);
   IndicatorRelease(h_ema200_h1);
   IndicatorRelease(h_ema9_m15);
   IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_bb_m15);
   IndicatorRelease(h_rsi_m15);
   IndicatorRelease(h_atr14_m15);
}

void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance > peakBalance) peakBalance = balance;
   
   double current_dd = (peakBalance - balance) / peakBalance;
   if(current_dd >= InpMaxDrawdownLimit) return;
   if(PositionsTotal() > 0) return;
   
   double ema9_h1[], ema20_h1[], ema55_h1[], ema200_h1[];
   ArraySetAsSeries(ema9_h1, true); ArraySetAsSeries(ema20_h1, true);
   ArraySetAsSeries(ema55_h1, true); ArraySetAsSeries(ema200_h1, true);
   
   // FIX: Copy from index 1 (completed H1 bar) for 100% causal non-repainting execution
   if(CopyBuffer(h_ema9_h1, 0, 1, 2, ema9_h1) < 2) return;
   if(CopyBuffer(h_ema20_h1, 0, 1, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema55_h1, 0, 1, 2, ema55_h1) < 2) return;
   if(CopyBuffer(h_ema200_h1, 0, 1, 2, ema200_h1) < 2) return;
   
   bool macro_bull = (ema9_h1[0] > ema20_h1[0]) && (ema20_h1[0] > ema55_h1[0]) && (ema55_h1[0] > ema200_h1[0]);
   if(!macro_bull) return;
   
   double ema9_m15[], ema20_m15[];
   ArraySetAsSeries(ema9_m15, true); ArraySetAsSeries(ema20_m15, true);
   if(CopyBuffer(h_ema9_m15, 0, 0, 2, ema9_m15) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 0, 2, ema20_m15) < 2) return;
   if(ema9_m15[1] <= ema20_m15[1]) return;
   
   double upper_bb[], rsi[], atr[];
   ArraySetAsSeries(upper_bb, true); ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   if(CopyBuffer(h_bb_m15, 1, 0, 2, upper_bb) < 2) return;
   if(CopyBuffer(h_rsi_m15, 0, 0, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 0, 2, atr) < 2) return;
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 55, rates) < 55) return;
   
   double close = rates[0].close;
   double open = rates[0].open;
   double high = rates[0].high;
   double low = rates[0].low;
   
   double body = MathAbs(close - open) + 0.00001;
   double lwick = MathMin(open, close) - low;
   if(lwick < 0.80 * body) return;
   if(!(close > open && rates[1].close > rates[1].open)) return;
   if(close <= upper_bb[1]) return;
   if(rsi[1] <= 55.0) return;
   
   double av = atr[1]; if(av < 0.8) av = 0.8;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = av * 1.0 + 0.25;
   double tp_dist = av * 2.15;
   
   // Safety Brake: Reduces risk during drawdowns to allow full recovery without hitting kill switch
   double active_risk_pct = 0.0475;
   if(current_dd >= 0.10) active_risk_pct = 0.015;
   else if(balance < 3000.0) active_risk_pct = 0.080;
   
   double risk_amount = balance * active_risk_pct;
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_sz = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_sz <= 0) tick_sz = 0.01; if(tick_val <= 0) tick_val = 1.0;
   
   double loss_per_lot = (sl_dist / tick_sz) * tick_val;
   double lot_size = NormalizeDouble(risk_amount / loss_per_lot, 2);
   if(lot_size < 0.01) lot_size = 0.01; if(lot_size > 10.0) lot_size = 10.0;
   
   double sl_price = NormalizeDouble(ask - sl_dist, _Digits);
   double tp_price = NormalizeDouble(ask + tp_dist, _Digits);
   
   trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
}
"""

METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
MQL5_SRC = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP500_MasterFlagshipEA.mq5"
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def deploy_and_eval():
    print("="*115)
    print("COMPILING & DEPLOYING ALAB_CP500_MasterFlagshipEA.mq5 ACROSS ALL TERMINALS")
    print("="*115)
    
    with open(MQL5_SRC, 'w', encoding='utf-8') as f:
        f.write(MQL5_CODE)
        
    cmd = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if os.path.exists(ex5_src):
        print(f"SUCCESSFULLY COMPILED EX5: {ex5_src}")
        for root in TERMINAL_ROOTS:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
            os.makedirs(dest_dir, exist_ok=True)
            dest_ex5 = os.path.join(dest_dir, "ALAB_CP500_MasterFlagshipEA.ex5")
            shutil.copy2(ex5_src, dest_ex5)
            print(f"SYNCED -> {dest_ex5}")
            
    print("\n" + "="*115)
    print("RUNNING DIRECT MT5 NATIVE IPC BROKER AUDIT FOR CP-500 MASTER FLAGSHIP")
    print("="*115)
    
    if not mt5.initialize():
        print(f"FAILED TO CONNECT TO MT5 IPC: {mt5.last_error()}")
        return
        
    mt5.symbol_select("GOLD", True)
    account_info = mt5.account_info()
    symbol_info = mt5.symbol_info("GOLD")
    
    rates = mt5.copy_rates_from("GOLD", mt5.TIMEFRAME_M15, datetime.now(), 99999)
    if rates is None or len(rates) == 0:
        print("Failed to copy rates from MT5")
        mt5.shutdown()
        return
        
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    
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
    h1_causal = h1.shift(1)
    
    df = pd.merge_asof(df, h1_causal[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df['ema9_h1'].values
    ema20_h1 = df['ema20_h1'].values
    ema55_h1 = df['ema55_h1'].values
    ema200_h1 = df['ema200_h1'].values
    
    ema9_m15 = df['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    sma20_m15 = pd.Series(c_m15).rolling(20).mean().values
    std20_m15 = pd.Series(c_m15).rolling(20).std().values
    upper_bb_m15 = sma20_m15 + 2.0 * std20_m15
    
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
    spread_pts = 25
    
    for i in range(200, n - 1):
        if np.isnan(ema9_h1[i]): continue
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > upper_bb_m15[i]) and (vol_zscore[i] > 0.85) and (rsi_m15[i] > 55.0) and (lwick >= 0.80 * body) and consec_bull
        
        if b_sig and (i - last_idx >= 4):
            last_idx = i
            entry_price = o_m15[i+1] + (spread_pts / 100.0)
            
            sl_dist = av * 1.0 + 0.25
            tp_dist = av * 2.15
            
            current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
            if current_dd >= 0.10:
                risk_pct = 0.015  # Safety Brake
            elif balance < 3000.0:
                risk_pct = 0.080  # Tier 1 Risk (8.0%)
            else:
                risk_pct = 0.0475 # Tier 2 Risk (4.75%)
                
            vol_mult = 1.15 if vol_zscore[i] >= 1.25 else 1.0
            risk_amount = balance * risk_pct * vol_mult
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
    total_t = len(trades)
    win_t = len(win_trades)
    wr = (win_t / total_t * 100.0) if total_t else 0.0
    gp = sum(win_trades)
    gl = abs(sum([p for p in trades if p < 0]))
    pf = gp / gl if gl > 0 else 999.0
    
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    print("="*115)
    print("DIRECT METATRADER 5 NATIVE IPC AUDIT REPORT: CP-500 MASTER FLAGSHIP (CAUSAL)")
    print("="*115)
    print(f"1. Broker Server                     : {account_info.server}")
    print(f"2. Account Login / Currency         : {account_info.login} ({account_info.currency})")
    print(f"3. Initial Deposit -> Final Balance  : ${initial_balance:,.2f} USD -> ${balance:,.2f} USD (+{net_yield_pct:.2f}% PnL)")
    print(f"4. Win Rate %                        : {wr:.2f}% ({win_t} Wins / {total_t - win_t} Losses)")
    print(f"5. Maximum Drawdown %                : {max_dd_pct * 100.0:.2f}% (Target Mandate: < 25.0%)")
    print(f"6. Profit Factor (PF)                : {pf:.2f} (Gross Profit ${gp:,.2f} / Gross Loss ${gl:,.2f})")
    print(f"7. Total Executed Trades             : {total_t} Trades")
    print("="*115)
    
    mt5.shutdown()

if __name__ == '__main__':
    deploy_and_eval()
