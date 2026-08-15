"""
BUILD AND EXECUTE CP-950 DIAGNOSTIC EA WITH VERBOSE MQL5 LOGGING
================================================================
"""

import os, sys, shutil, subprocess, time

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
MQL5_SRC = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", "ALAB_CP950_DiagnosticEA.mq5")
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')
INI_PATH = os.path.join(DATA_DIR, "generate_cp950_report.ini")

MQL5_CODE = """//+------------------------------------------------------------------+
//|                               ALAB_CP950_DiagnosticEA.mq5        |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseRiskPct        = 0.05;   // Base Risk Per Trade (5.0%)
input double   InpMaxDrawdownLimit   = 0.25;   // Maximum Equity Drawdown Cutoff (25%)
input ulong    InpMagicNumber        = 2026950;// Magic Number
input string   InpTradeComment       = "ALAB_CP950_Diag";

CTrade         trade;
datetime       lastBarTime;
double         peakEquity;
bool           isHalted;

int h_ema9_m15, h_ema20_m15, h_rsi_m15, h_atr14_m15;

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) return(INIT_FAILED);
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   isHalted = false;
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   IndicatorRelease(h_ema9_m15);
   IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_rsi_m15);
   IndicatorRelease(h_atr14_m15);
}

void OnTick()
{
   if(!MQLInfoInteger(MQL_TESTER)) return;
   
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(current_equity > peakEquity) peakEquity = current_equity;
   
   double equity_dd = (peakEquity - current_equity) / peakEquity;
   if(isHalted || equity_dd >= InpMaxDrawdownLimit)
   {
      isHalted = true;
      return;
   }
   
   if(PositionsTotal() > 0) return;
   
   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   double ema9[], ema20[], rsi[], atr[];
   ArraySetAsSeries(ema9, true); ArraySetAsSeries(ema20, true);
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(h_ema9_m15, 0, 1, 2, ema9) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 1, 2, ema20) < 2) return;
   if(CopyBuffer(h_rsi_m15, 0, 1, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 1, 2, atr) < 2) return;
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 2, rates) < 2) return;
   
   bool buy_sig  = (ema9[0] > ema20[0]) && (rates[0].close > rates[0].open);
   bool sell_sig = (ema9[0] < ema20[0]) && (rates[0].close < rates[0].open);
   if(!buy_sig && !sell_sig) return;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double av  = MathMax(atr[0], 0.8);
   double sl_dist = av * 1.2 + 0.25;
   double tp_dist = av * 2.4;
   
   ENUM_ORDER_TYPE ord_type = buy_sig ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double entry_price = buy_sig ? ask : bid;
   double sl_price    = buy_sig ? NormalizeDouble(entry_price - sl_dist, _Digits) : NormalizeDouble(entry_price + sl_dist, _Digits);
   double tp_price    = buy_sig ? NormalizeDouble(entry_price + tp_dist, _Digits) : NormalizeDouble(entry_price - tp_dist, _Digits);
   
   double tick_sz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_sz <= 0) tick_sz = 0.01; if(tick_val <= 0) tick_val = 1.0;
   
   double one_lot_loss = (sl_dist / tick_sz) * tick_val;
   double risk_amount = AccountInfoDouble(ACCOUNT_BALANCE) * InpBaseRiskPct;
   double lot_size = NormalizeDouble(risk_amount / one_lot_loss, 2);
   if(lot_size < 0.01) lot_size = 0.01;
   if(lot_size > 10.0) lot_size = 10.0;
   
   if(buy_sig)  trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
   else         trade.Sell(lot_size, _Symbol, bid, sl_price, tp_price, InpTradeComment);
}
"""

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def run_protocol():
    print("="*115)
    print("STEP 1: TERMINATING RUNNING TERMINAL PROCESSES")
    print("="*115)
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(1)
    
    print("="*115)
    print("STEP 2: COMPILING ALAB_CP950_DiagnosticEA.mq5 VIA METAEDITOR CLI")
    print("="*115)
    
    os.makedirs(os.path.dirname(MQL5_SRC), exist_ok=True)
    with open(MQL5_SRC, 'w', encoding='utf-8') as f:
        f.write(MQL5_CODE)
        
    cmd_compile = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if not os.path.exists(ex5_src):
        print("COMPILATION FAILED!")
        return
        
    print("Compilation successful! Syncing EX5...")
    for root in TERMINAL_ROOTS:
        dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(ex5_src, os.path.join(dest_dir, "ALAB_CP950_DiagnosticEA.ex5"))
        
    print("="*115)
    print("STEP 3: LAUNCHING NATIVE MT5 TESTER (MODEL=4 REAL TICKS)")
    print("="*115)
    
    ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP950_DiagnosticEA.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=4
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report=MQL5\\Experts\\AlphaLab\\cp950_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    proc = subprocess.Popen(cmd_run)
    proc.wait()

if __name__ == '__main__':
    run_protocol()
