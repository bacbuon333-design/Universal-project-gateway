"""
BUILD AND EXECUTE CP-750 UNDER NATIVE MT5 MODEL=4 REAL-TICK PROTOCOL
===================================================================
"""

import os, sys, shutil, subprocess, hashlib, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
MQL5_SRC = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", "ALAB_CP750_DualRegimeEA.mq5")
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')
INI_PATH = os.path.join(DATA_DIR, "generate_cp750_report.ini")
TARGET_REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "cp750_report.html")

MQL5_CODE = """//+------------------------------------------------------------------+
//|                                    ALAB_CP750_DualRegimeEA.mq5   |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseRiskPct        = 0.045;  // Base Risk Per Trade (4.5%)
input double   InpMaxDrawdownLimit   = 0.20;   // Maximum Equity Drawdown Cutoff (20%)
input ulong    InpMagicNumber        = 2026750;// Magic Number
input string   InpTradeComment       = "ALAB_CP750_DualRegime";

CTrade         trade;
datetime       lastBarTime;
double         peakEquity;
bool           isHalted;

int h_ema20_h1, h_ema50_h1;
int h_ema9_m15, h_ema20_m15, h_bb_m15, h_rsi_m15, h_atr14_m15;

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER))
   {
      Print("ERROR: Live trading authority prohibited. Research EA is tester-only.");
      return(INIT_FAILED);
   }
   
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   isHalted = false;
   
   h_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema50_h1  = iMA(_Symbol, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_bb_m15    = iBands(_Symbol, PERIOD_M15, 20, 0, 2.0, PRICE_CLOSE);
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   IndicatorRelease(h_ema20_h1);
   IndicatorRelease(h_ema50_h1);
   IndicatorRelease(h_ema9_m15);
   IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_bb_m15);
   IndicatorRelease(h_rsi_m15);
   IndicatorRelease(h_atr14_m15);
}

void CloseAllOwnedPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
         {
            trade.PositionClose(ticket);
         }
      }
   }
}

int CountOwnedPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber && PositionGetString(POSITION_SYMBOL) == _Symbol)
         {
            count++;
         }
      }
   }
   return count;
}

void OnTick()
{
   if(!MQLInfoInteger(MQL_TESTER)) return;
   
   // Hard Equity Protection: Runs on EVERY TICK before bar gate
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(current_equity > peakEquity) peakEquity = current_equity;
   
   double equity_dd = (peakEquity - current_equity) / peakEquity;
   if(isHalted || equity_dd >= InpMaxDrawdownLimit)
   {
      isHalted = true;
      CloseAllOwnedPositions();
      return;
   }
   
   if(CountOwnedPositions() > 0) return;
   
   // Bar Gate: Evaluate signals on completed shift 1 bars only
   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   double ema20_h1[], ema50_h1[];
   ArraySetAsSeries(ema20_h1, true); ArraySetAsSeries(ema50_h1, true);
   
   if(CopyBuffer(h_ema20_h1, 0, 1, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema50_h1, 0, 1, 2, ema50_h1) < 2) return;
   
   bool macro_bull = (ema20_h1[0] > ema50_h1[0]);
   bool macro_bear = (ema20_h1[0] < ema50_h1[0]);
   
   double ema9_m15[], ema20_m15[];
   ArraySetAsSeries(ema9_m15, true); ArraySetAsSeries(ema20_m15, true);
   if(CopyBuffer(h_ema9_m15, 0, 1, 2, ema9_m15) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 1, 2, ema20_m15) < 2) return;
   
   double upper_bb[], lower_bb[], rsi[], atr[];
   ArraySetAsSeries(upper_bb, true); ArraySetAsSeries(lower_bb, true);
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   if(CopyBuffer(h_bb_m15, 1, 1, 2, upper_bb) < 2) return;
   if(CopyBuffer(h_bb_m15, 2, 1, 2, lower_bb) < 2) return;
   if(CopyBuffer(h_rsi_m15, 0, 1, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 1, 2, atr) < 2) return;
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 3, rates) < 3) return;
   
   double close = rates[0].close;
   double av = atr[0]; if(av < 0.8) av = 0.8;
   
   bool buy_signal  = macro_bull && (ema9_m15[0] > ema20_m15[0]) && (close > upper_bb[0]) && (rsi[0] > 52.0);
   bool sell_signal = macro_bear && (ema9_m15[0] < ema20_m15[0]) && (close < lower_bb[0]) && (rsi[0] < 48.0);
   
   if(!buy_signal && !sell_signal) return;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl_dist = av * 1.2 + 0.25;
   double tp_dist = av * 2.4;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * InpBaseRiskPct;
   
   ENUM_ORDER_TYPE ord_type = buy_signal ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double entry_price = buy_signal ? ask : bid;
   double sl_price    = buy_signal ? NormalizeDouble(entry_price - sl_dist, _Digits) : NormalizeDouble(entry_price + sl_dist, _Digits);
   double tp_price    = buy_signal ? NormalizeDouble(entry_price + tp_dist, _Digits) : NormalizeDouble(entry_price - tp_dist, _Digits);
   
   // OrderCalcProfit to compute exact one-lot loss
   double one_lot_loss = 0.0;
   if(!OrderCalcProfit(ord_type, _Symbol, 1.0, entry_price, sl_price, one_lot_loss))
   {
      double tick_sz = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      if(tick_sz <= 0) tick_sz = 0.01; if(tick_val <= 0) tick_val = 1.0;
      one_lot_loss = (sl_dist / tick_sz) * tick_val;
   }
   one_lot_loss = MathAbs(one_lot_loss);
   if(one_lot_loss <= 0) return;
   
   double raw_volume = risk_amount / one_lot_loss;
   double vol_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vol_min  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vol_max  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   double lot_size = MathFloor(raw_volume / vol_step) * vol_step;
   if(lot_size < vol_min) return; // Skip trade if risk-valid volume < min lot
   if(lot_size > vol_max) lot_size = vol_max;
   
   double margin_req = 0.0;
   if(OrderCalcMargin(ord_type, _Symbol, lot_size, entry_price, margin_req))
   {
      if(margin_req > AccountInfoDouble(ACCOUNT_MARGIN_FREE)) return;
   }
   
   MqlTradeRequest request = {};
   request.action   = TRADE_ACTION_DEAL;
   request.symbol   = _Symbol;
   request.volume   = lot_size;
   request.type     = ord_type;
   request.price    = entry_price;
   request.sl       = sl_price;
   request.tp       = tp_price;
   request.deviation= 10;
   request.magic    = InpMagicNumber;
   request.comment  = InpTradeComment;
   
   MqlTradeCheckResult check_res;
   if(!trade.OrderCheck(request, check_res)) return;
   
   if(buy_signal) trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
   else           trade.Sell(lot_size, _Symbol, bid, sl_price, tp_price, InpTradeComment);
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
    print("STEP 2: COMPILING ALAB_CP750_DualRegimeEA.mq5 VIA METAEDITOR CLI")
    print("="*115)
    
    os.makedirs(os.path.dirname(MQL5_SRC), exist_ok=True)
    with open(MQL5_SRC, 'w', encoding='utf-8') as f:
        f.write(MQL5_CODE)
        
    cmd_compile = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if not os.path.exists(ex5_src):
        print("COMPILATION FAILED! Check log.")
        return
        
    with open(LOG_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        log_txt = f.read()
    print(f"MetaEditor Log Output:\n{log_txt[-300:]}")
    
    for root in TERMINAL_ROOTS:
        dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(ex5_src, os.path.join(dest_dir, "ALAB_CP750_DualRegimeEA.ex5"))
        print(f"Synced EX5 -> {os.path.join(dest_dir, 'ALAB_CP750_DualRegimeEA.ex5')}")
        
    print("="*115)
    print("STEP 3: LAUNCHING NATIVE MT5 TESTER (MODEL=4 REAL TICKS)")
    print("="*115)
    
    if os.path.exists(TARGET_REPORT_PATH):
        try: os.remove(TARGET_REPORT_PATH)
        except Exception: pass
        
    ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP750_DualRegimeEA.ex5
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
Report=MQL5\\Experts\\AlphaLab\\cp750_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing MT5 process: {cmd_run}")
    proc = subprocess.Popen(cmd_run)
    proc.wait()
    
    print("="*115)
    print("STEP 4: READING AND EVALUATING OFFICIAL MT5 HTML REPORT (cp750_report.html)")
    print("="*115)
    
    if os.path.exists(TARGET_REPORT_PATH):
        print(f"REPORT FOUND AT: {TARGET_REPORT_PATH}")
        with open(TARGET_REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        report_data = {}
        for r in rows:
            cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
            if len(cols) >= 2:
                for i in range(0, len(cols) - 1, 2):
                    key = cols[i].replace(':', '')
                    val = cols[i+1]
                    if key and val:
                        report_data[key] = val
                        
        print("\nOFFICIAL NATIVE MT5 MODEL=4 EVALUATION RESULTS:")
        for k, v in report_data.items():
            print(f"  {k:35s} -> {v}")
    else:
        print(f"ERROR: Native MT5 Report file not generated at {TARGET_REPORT_PATH}")

if __name__ == '__main__':
    run_protocol()
