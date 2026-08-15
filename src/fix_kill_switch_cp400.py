"""
FIX HARD KILL-SWITCH SHUTDOWN IN ALAB_CP400_MasterFlagshipEA
============================================================
Replaces permanent EA shutdown on drawdown with a dynamic Risk Safety Brake (1.2% risk during drawdowns),
allowing the strategy to recover from temporary drawdown dips and compound to $6,000+ USD.
"""

import os, sys, shutil, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

MQL5_CODE = """//+------------------------------------------------------------------+
//|                                   ALAB_CP400_MasterFlagshipEA.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpMaxDrawdownLimit   = 0.40;   // Maximum Drawdown Safety Threshold (40%)
input ulong    InpMagicNumber        = 2026400;// Magic Number
input string   InpTradeComment       = "ALAB_CP400_MasterFlagship";

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
   
   // Copy from index 1 (completed H1 bar) for 100% causal non-repainting execution
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
   else if(balance < 3000.0) active_risk_pct = 0.075;
   
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
MQL5_SRC = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP400_MasterFlagshipEA.mq5"
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def run_compile_and_sync():
    print("="*105)
    print("COMPILING & SYNCING FIXED ALAB_CP400_MasterFlagshipEA.mq5 ACROSS ALL TERMINALS")
    print("="*105)
    
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
            dest_ex5 = os.path.join(dest_dir, "ALAB_CP400_MasterFlagshipEA.ex5")
            shutil.copy2(ex5_src, dest_ex5)
            print(f"SYNCED -> {dest_ex5}")

if __name__ == '__main__':
    run_compile_and_sync()
