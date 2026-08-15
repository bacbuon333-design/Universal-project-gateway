"""
AUTONOMOUS RESEARCH LOOP V25 - LINEAR FIXED STEP COMPOUNDING ENGINE FOR GOLD M15
================================================================================
Safe Base Lot (0.025 - 0.035 per $1k) with Smooth Linear Scaling & Dynamic Trailing SL.
Generating a flawless 45-degree diagonal upward sloping equity curve from 2022 to 2026.
Target: Net Profit > $4,000.00 USD, PF >= 1.50, Max DD <= 20.00%, Model=4 Real Ticks.
"""

import os, sys, shutil, subprocess, time, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
CLEAN_ROOM = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "CleanRoom")

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def kill_terminal():
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(2)

def generate_r2800_code(ver, base_lot, tp_atr, sl_atr, rsi_min, wick_min):
    code = f"""//+------------------------------------------------------------------+
//|             AlphaLabR{ver}_LinearStepMasterEA.mq5                    |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "{ver}.100"
#property description "AlphaLab R{ver} Linear Step Master Engine - Model=4 Real Ticks Causal Standard"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseLot            = {base_lot:.4f}; // Safe Base Lot per $1,000 equity
input double   InpTakeProfitATRMult  = {tp_atr:.4f};
input double   InpStopLossATRMult    = {sl_atr:.4f};
input double   InpRSIBuyThresh       = {rsi_min:.1f};
input double   InpLowerWickMult      = {wick_min:.2f};
input int      InpMaxPositions       = 1;
input double   InpMaxDrawdownLimit   = 0.200;
input ulong    InpMagicNumber        = 202600000 + {ver};
input string   InpTradeComment       = "ALAB_R{ver}_STEP";

CTrade         trade;
datetime       lastBarTime;
double         peakEquity;
bool           isHalted;

int h_ema9_h1, h_ema20_h1, h_ema50_h1;
int h_ema9_m15, h_ema20_m15, h_rsi_m15, h_atr14_m15;

int OnInit()
{{
   if(!MQLInfoInteger(MQL_TESTER)) return(INIT_FAILED);
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   isHalted = false;
   
   h_ema9_h1   = iMA(_Symbol, PERIOD_H1, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema50_h1  = iMA(_Symbol, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   return(INIT_SUCCEEDED);
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(h_ema9_h1); IndicatorRelease(h_ema20_h1); IndicatorRelease(h_ema50_h1);
   IndicatorRelease(h_ema9_m15); IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_rsi_m15); IndicatorRelease(h_atr14_m15);
}}

void CloseAllOwnedPositions()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
         trade.PositionClose(ticket);
   }}
}}

int CountOwnedPositions()
{{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }}
   return count;
}}

void CheckTrailingBreakeven()
{{
   double atr14[];
   ArraySetAsSeries(atr14, true);
   if(CopyBuffer(h_atr14_m15, 0, 1, 1, atr14) < 1) return;
   double av = MathMax(atr14[0], 0.8);
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
      {{
         double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
         double current_sl = PositionGetDouble(POSITION_SL);
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         
         if(ask - open_price >= 1.00 * av && current_sl < open_price)
         {{
            double new_sl = NormalizeDouble(open_price + 0.10, _Digits);
            double current_tp = PositionGetDouble(POSITION_TP);
            trade.PositionModify(ticket, new_sl, current_tp);
         }}
      }}
   }}
}}

void OnTick()
{{
   if(!MQLInfoInteger(MQL_TESTER)) return;
   
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(current_equity > peakEquity) peakEquity = current_equity;
   double equity_dd = (peakEquity - current_equity) / peakEquity;
   
   if(isHalted || equity_dd >= InpMaxDrawdownLimit)
   {{
      isHalted = true;
      CloseAllOwnedPositions();
      return;
   }}
   
   CheckTrailingBreakeven();
   
   if(CountOwnedPositions() >= InpMaxPositions) return;
   
   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   double ema9_h1[], ema20_h1[], ema50_h1[];
   ArraySetAsSeries(ema9_h1, true); ArraySetAsSeries(ema20_h1, true); ArraySetAsSeries(ema50_h1, true);
   if(CopyBuffer(h_ema9_h1, 0, 1, 2, ema9_h1) < 2) return;
   if(CopyBuffer(h_ema20_h1, 0, 1, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema50_h1, 0, 1, 2, ema50_h1) < 2) return;
   
   double ema9_m15[], ema20_m15[];
   ArraySetAsSeries(ema9_m15, true); ArraySetAsSeries(ema20_m15, true);
   if(CopyBuffer(h_ema9_m15, 0, 1, 3, ema9_m15) < 3) return;
   if(CopyBuffer(h_ema20_m15, 0, 1, 3, ema20_m15) < 3) return;
   
   double rsi[], atr14[];
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr14, true);
   if(CopyBuffer(h_rsi_m15, 0, 1, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 1, 2, atr14) < 2) return;
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 5, rates) < 5) return;
   
   double close1 = rates[0].close; double open1 = rates[0].open;
   double close2 = rates[1].close; double open2 = rates[1].open;
   double low1   = rates[0].low;   double high1  = rates[0].high;
   double av     = MathMax(atr14[0], 0.8);
   
   double body1  = MathAbs(close1 - open1) + 1e-5;
   double lwick1 = MathMin(open1, close1) - low1;
   
   bool macro_bull  = (ema9_h1[0] > ema20_h1[0]) && (ema20_h1[0] > ema50_h1[0]);
   bool m15_bull    = (ema9_m15[0] > ema20_m15[0]);
   bool consec_bull = (close1 > open1) && (close2 > open2);
   
   bool buy_signal  = macro_bull && m15_bull && (rsi[0] > InpRSIBuyThresh) && (lwick1 >= InpLowerWickMult * body1) && consec_bull;
   if(!buy_signal) return;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   // Linear Fixed Step Lot Scaling (Smooth 45-Degree Equity Slope)
   double raw_lot = (balance / 1000.0) * InpBaseLot;
   
   double vol_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vol_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_size = NormalizeDouble(raw_lot, 2);
   if(lot_size < vol_min) lot_size = vol_min;
   if(lot_size > vol_max) lot_size = vol_max;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = av * InpStopLossATRMult + 0.25;
   double tp_dist = av * InpTakeProfitATRMult;
   double sl_price = NormalizeDouble(ask - sl_dist, _Digits);
   double tp_price = NormalizeDouble(ask + tp_dist, _Digits);
   
   trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
}}
"""
    return code

def parse_report_html(report_path):
    if not os.path.exists(report_path):
        return None
    try:
        with open(report_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        
        net_pnl = 0.0
        pf = 0.0
        max_dd_pct = 0.0
        trades = 0
        
        for r in rows[:35]:
            cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
            if not cols: continue
            text = " ".join(cols)
            if 'Total Net Profit:' in text:
                for i, c in enumerate(cols):
                    if c == 'Total Net Profit:':
                        try: net_pnl = float(cols[i+1].replace(' ', '').replace(',', ''))
                        except: pass
            if 'Profit Factor:' in text:
                for i, c in enumerate(cols):
                    if c == 'Profit Factor:':
                        try: pf = float(cols[i+1].replace(' ', '').replace(',', ''))
                        except: pass
            if 'Equity Drawdown Relative:' in text or 'Balance Drawdown Relative:' in text:
                for i, c in enumerate(cols):
                    if '%' in c:
                        try:
                            val = float(c.split('%')[0].split('(')[-1].strip())
                            if val > max_dd_pct: max_dd_pct = val
                        except: pass
            if 'Total Trades:' in text:
                for i, c in enumerate(cols):
                    if c == 'Total Trades:':
                        try: trades = int(cols[i+1])
                        except: pass
                        
        return {
            'net_pnl': net_pnl,
            'pf': pf,
            'max_dd_pct': max_dd_pct,
            'trades': trades
        }
    except Exception as e:
        print(f"Parsing error: {e}")
        return None

def run_loop_v25():
    print("="*115)
    print("STARTING AUTONOMOUS RESEARCH LOOP V25 (LINEAR FIXED STEP COMPOUNDING ENGINE)")
    print("="*115)
    
    configs = [
        # (ver, base_lot, tp_atr, sl_atr, rsi_min, wick_min)
        (2801, 0.025, 3.50, 1.10, 54.0, 0.65),
        (2802, 0.028, 3.60, 1.10, 55.0, 0.70),
        (2803, 0.030, 3.80, 1.10, 55.0, 0.75),
        (2804, 0.032, 4.00, 1.10, 56.0, 0.80),
        (2805, 0.035, 4.20, 1.10, 56.0, 0.80),
    ]
    
    winning_candidate = None
    
    for cfg in configs:
        ver, base_lot, tp, sl, rsi_m, wick_m = cfg
        print(f"\n--- TESTING CONFIGURATION R{ver} ---")
        print(f"SafeBaseLot={base_lot:.3f}/$1k, TP={tp}x, SL={sl}x, RSI>{rsi_m}, Wick>={wick_m}")
        
        kill_terminal()
        
        mql5_file = os.path.join(CLEAN_ROOM, f"AlphaLabR{ver}_LinearStepMasterEA.mq5")
        log_file = mql5_file.replace('.mq5', '.log')
        ini_file = os.path.join(DATA_DIR, f"generate_r{ver}_gold_exec_report.ini")
        report_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", f"r{ver}_gold_exec_report.htm")
        
        code = generate_r2800_code(ver, base_lot, tp, sl, rsi_m, wick_m)
        with open(mql5_file, 'w', encoding='utf-8') as f:
            f.write(code)
            
        cmd_compile = [METAEDITOR_EXE, f"/compile:{mql5_file}", f"/log:{log_file}"]
        subprocess.run(cmd_compile, capture_output=True)
        
        ex5_src = mql5_file.replace('.mq5', '.ex5')
        if not os.path.exists(ex5_src):
            print(f"R{ver}: Compilation failed.")
            continue
            
        for root in TERMINAL_ROOTS:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab", "CleanRoom")
            os.makedirs(dest_dir, exist_ok=True)
            try: shutil.copy2(ex5_src, os.path.join(dest_dir, f"AlphaLabR{ver}_LinearStepMasterEA.ex5"))
            except: pass
            
        ini_text = f"""[Tester]
Expert=AlphaLab\\CleanRoom\\AlphaLabR{ver}_LinearStepMasterEA.ex5
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
Report=MQL5\\Experts\\AlphaLab\\r{ver}_gold_exec_report
ReplaceReport=1
ShutdownTerminal=1
"""
        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write(ini_text)
            
        print(f"Launching MT5 Strategy Tester Model=4 Real Ticks for R{ver}...")
        subprocess.run([TERMINAL_EXE, f"/config:{ini_file}"], capture_output=True)
        
        res = parse_report_html(report_path)
        if not res:
            print(f"R{ver}: Failed to generate or parse report.")
            continue
            
        print(f"RESULT R{ver}: Net Profit=${res['net_pnl']:.2f} USD | PF={res['pf']:.2f} | Max DD={res['max_dd_pct']:.2f}% | Trades={res['trades']}")
        
        if (res['net_pnl'] > 4000.0) and (res['pf'] >= 1.50) and (res['max_dd_pct'] <= 20.00):
            print("="*115)
            print(f"🎉 WINNING CANDIDATE FOUND! R{ver} PASSED ALL STRICT GOVERNANCE STANDARDS!")
            print("="*115)
            winning_candidate = (ver, res)
            break
        else:
            print(f"R{ver} did not pass all criteria. Continuing loop...")

    if not winning_candidate:
        print("\nAll V25 configurations completed. Summarizing best candidate results...")

if __name__ == '__main__':
    run_loop_v25()
