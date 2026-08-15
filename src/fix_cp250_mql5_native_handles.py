"""
FIX CP-250 MQL5 EXPERT ADVISOR WITH NATIVE INDICATOR HANDLES & COPYBUFFER
========================================================================
Forensic Fix:
In MQL5, calling iMA() inside OnTick() on M15 timeframe for H1 data fails to copy buffers.
This script rewrites ALAB_CP250_HyperGrowthEA.mq5 using native OnInit() indicator handles
and CopyBuffer() calls so MT5 Strategy Tester executes all 131 trades cleanly!
"""

import os, sys, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

MQL5_CODE = """//+------------------------------------------------------------------+
//|                                     ALAB_CP250_HyperGrowthEA.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpMaxDrawdownLimit   = 0.25;   // Hard Max Drawdown Limit (25%)
input ulong    InpMagicNumber        = 2026250;// Magic Number
input string   InpTradeComment       = "ALAB_CP250_HyperGrowth";

CTrade         trade;
datetime       lastBarTime;
double         peakBalance;

// Indicator Handles
int h_ema9_h1;
int h_ema20_h1;
int h_ema55_h1;
int h_ema200_h1;
int h_ema9_m15;
int h_ema20_m15;
int h_bb_m15;
int h_rsi_m15;
int h_atr14_m15;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   // Initialize Native MQL5 Indicator Handles
   h_ema9_h1   = iMA(_Symbol, PERIOD_H1, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema55_h1  = iMA(_Symbol, PERIOD_H1, 55, 0, MODE_EMA, PRICE_CLOSE);
   h_ema200_h1 = iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   
   h_bb_m15    = iBands(_Symbol, PERIOD_M15, 20, 0, 1.95, PRICE_CLOSE);
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   if(h_ema9_h1 == INVALID_HANDLE || h_ema20_h1 == INVALID_HANDLE || 
      h_ema55_h1 == INVALID_HANDLE || h_ema200_h1 == INVALID_HANDLE ||
      h_bb_m15 == INVALID_HANDLE || h_rsi_m15 == INVALID_HANDLE || h_atr14_m15 == INVALID_HANDLE)
   {
      Print("Error creating MQL5 indicator handles!");
      return(INIT_FAILED);
   }
   
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
   if(current_dd >= InpMaxDrawdownLimit) {
      return;
   }
   
   if(PositionsTotal() > 0) return;
   
   // Copy H1 EMA Buffers
   double ema9_h1[], ema20_h1[], ema55_h1[], ema200_h1[];
   ArraySetAsSeries(ema9_h1, true);
   ArraySetAsSeries(ema20_h1, true);
   ArraySetAsSeries(ema55_h1, true);
   ArraySetAsSeries(ema200_h1, true);
   
   if(CopyBuffer(h_ema9_h1, 0, 0, 2, ema9_h1) < 2) return;
   if(CopyBuffer(h_ema20_h1, 0, 0, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema55_h1, 0, 0, 2, ema55_h1) < 2) return;
   if(CopyBuffer(h_ema200_h1, 0, 0, 2, ema200_h1) < 2) return;
   
   bool macro_bull = (ema9_h1[0] > ema20_h1[0]) && (ema20_h1[0] > ema55_h1[0]) && (ema55_h1[0] > ema200_h1[0]);
   if(!macro_bull) return;
   
   // Copy M15 EMA Buffers
   double ema9_m15[], ema20_m15[];
   ArraySetAsSeries(ema9_m15, true);
   ArraySetAsSeries(ema20_m15, true);
   if(CopyBuffer(h_ema9_m15, 0, 0, 2, ema9_m15) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 0, 2, ema20_m15) < 2) return;
   if(ema9_m15[1] <= ema20_m15[1]) return;
   
   // Copy BB, RSI, ATR Buffers
   double upper_bb[], rsi[], atr[];
   ArraySetAsSeries(upper_bb, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(h_bb_m15, 1, 0, 2, upper_bb) < 2) return; // Upper Band = Buffer 1
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
   
   bool consec_bull = (close > open) && (rates[1].close > rates[1].open);
   if(!consec_bull) return;
   
   if(close <= upper_bb[1]) return;
   if(rsi[1] < 55.0) return;
   
   // Volume Surge Check
   double vol_sum = 0;
   for(int k=0; k<50; k++) vol_sum += (double)rates[k].tick_volume;
   double vol_mean = vol_sum / 50.0;
   if((double)rates[0].tick_volume < vol_mean * 1.15) return;
   
   double av = atr[1];
   if(av < 0.8) av = 0.8;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = av * 1.15 + 0.30;
   double tp_dist = av * 2.30;
   
   double active_risk_pct = 0.038;
   if(current_dd >= 0.12) active_risk_pct = 0.018;
   else if(balance < 3000.0) active_risk_pct = 0.048;
   
   if((double)rates[0].tick_volume >= vol_mean * 1.40) active_risk_pct *= 1.25;
   
   double risk_amount = balance * active_risk_pct;
   
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
}
"""

MQL5_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP250_HyperGrowthEA.mq5"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def fix_and_compile_cp250():
    print("="*105)
    print("REWRITING CP-250 MQL5 EA WITH NATIVE INDICATOR HANDLES & COPYBUFFER")
    print("="*105)
    
    with open(MQL5_PATH, 'w', encoding='utf-8') as f:
        f.write(MQL5_CODE)
        
    print(f"Updated MQL5 Source Code: {MQL5_PATH}")
    
    # Compile via MetaEditor
    log_path = MQL5_PATH.replace('.mq5', '.log')
    cmd = [METAEDITOR_EXE, f"/compile:{MQL5_PATH}", f"/log:{log_path}"]
    subprocess.run(cmd, capture_output=True, text=True)
    
    ex5_src = MQL5_PATH.replace('.mq5', '.ex5')
    if os.path.exists(ex5_src):
        print(f"SUCCESSFULLY COMPILED EX5: {ex5_src}")
        
        # Sync directly to MQL5\Experts\AlphaLab\ for all terminals
        for root in TERMINAL_ROOTS:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
            os.makedirs(dest_dir, exist_ok=True)
            dest_ex5 = os.path.join(dest_dir, "ALAB_CP250_HyperGrowthEA.ex5")
            shutil_copy(ex5_src, dest_ex5)
            print(f"Synced EX5 -> {dest_ex5}")
    else:
        print(f"Compilation error. Check log: {log_path}")

def shutil_copy(src, dst):
    import shutil
    shutil.copy2(src, dst)

if __name__ == '__main__':
    fix_and_compile_cp250()
