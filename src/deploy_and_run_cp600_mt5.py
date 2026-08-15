"""
DEPLOY AND EXECUTE CP-600 MASTER FLAGSHIP ON NATIVE MT5 REAL TICKS
===================================================================
Compiles ALAB_CP600_MasterFlagshipEA.mq5, runs native MT5 Strategy Tester (Model=0 Real Ticks),
captures generated HTML report (cp600_report.html), and parses official MT5 metrics.
"""

import os, sys, shutil, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
MQL5_SRC = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", "ALAB_CP600_MasterFlagshipEA.mq5")
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')
INI_PATH = os.path.join(DATA_DIR, "generate_cp600_report.ini")
TARGET_REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "cp600_report.html")

MQL5_CODE = """//+------------------------------------------------------------------+
//|                                   ALAB_CP600_MasterFlagshipEA.mq5 |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpMaxDrawdownLimit   = 0.40;   // Maximum Drawdown Safety Threshold (40%)
input ulong    InpMagicNumber        = 2026600;// Magic Number
input string   InpTradeComment       = "ALAB_CP600_MasterFlagship";

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
   
   // Tight Drawdown Safety Brake: Reduces risk to 1.0% if DD reaches 8% to protect balance
   double active_risk_pct = 0.0475;
   if(current_dd >= 0.08) active_risk_pct = 0.010;
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

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def run_pipeline():
    print("="*115)
    print("STEP 1: TERMINATING RUNNING TERMINAL PROCESSES FOR CLEAN INI EXECUTION")
    print("="*115)
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(1)
    
    print("="*115)
    print("STEP 2: COMPILING & DEPLOYING ALAB_CP600_MasterFlagshipEA.mq5")
    print("="*115)
    
    with open(MQL5_SRC, 'w', encoding='utf-8') as f:
        f.write(MQL5_CODE)
        
    cmd_compile = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if os.path.exists(ex5_src):
        print(f"Compiled EX5: {ex5_src}")
        for root in TERMINAL_ROOTS:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(ex5_src, os.path.join(dest_dir, "ALAB_CP600_MasterFlagshipEA.ex5"))
            print(f"Synced -> {os.path.join(dest_dir, 'ALAB_CP600_MasterFlagshipEA.ex5')}")
            
    print("="*115)
    print("STEP 3: LAUNCHING NATIVE MT5 STRATEGY TESTER (MODEL=0 REAL TICKS)")
    print("="*115)
    
    if os.path.exists(TARGET_REPORT_PATH):
        try: os.remove(TARGET_REPORT_PATH)
        except Exception: pass
        
    ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP600_MasterFlagshipEA.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=0
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report=MQL5\\Experts\\AlphaLab\\cp600_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing MT5 Terminal process... {cmd_run}")
    proc = subprocess.Popen(cmd_run)
    proc.wait()
    
    print("="*115)
    print("STEP 4: PARSING OFFICIAL NATIVE MT5 HTML REPORT (cp600_report.html)")
    print("="*115)
    
    if os.path.exists(TARGET_REPORT_PATH):
        print(f"OFFICIAL MT5 REPORT CREATED AT: {TARGET_REPORT_PATH}")
        with open(TARGET_REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        print("OFFICIAL MT5 REPORT METRICS:")
        for r in rows:
            cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
            if len(cols) >= 2:
                for i in range(0, len(cols) - 1, 2):
                    key = cols[i].replace(':', '')
                    val = cols[i+1]
                    if any(term in key.lower() for term in ['profit', 'drawdown', 'trades', 'factor', 'payoff', 'deposit', 'balance']):
                        print(f"  [MT5 HTML REPORT] {key:32s} -> {val}")
    else:
        print(f"ERROR: HTML report not generated at {TARGET_REPORT_PATH}")

if __name__ == '__main__':
    run_pipeline()
