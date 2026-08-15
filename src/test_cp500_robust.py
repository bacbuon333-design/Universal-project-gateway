"""
TEST CP-500 ROBUST PULLBACK CANDIDATE ON NATIVE MT5 TESTER
=========================================================
"""

import os, sys, shutil, subprocess, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
TERMINAL = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
AGENT_LOG = os.path.join(DATA_DIR, "Tester", "Agent-127.0.0.1-3000", "logs", "20260801.log")

CP500_MQL5 = """//+------------------------------------------------------------------+
//|                                ALAB_CP500_RobustPullbackEA.mq5   |
//|                                  Copyright 2026, AlphaLab Antigravity |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "1.00"

#include <Trade\\Trade.mqh>

input double   InpRiskPct            = 0.025;   // Risk Per Trade (2.5%)
input double   InpMaxDrawdownLimit   = 0.25;   // Max Drawdown Limit (25%)
input ulong    InpMagicNumber        = 2026500;// Magic Number
input string   InpTradeComment       = "ALAB_CP500_RobustPullback";

CTrade         trade;
datetime       lastBarTime;
double         peakBalance;

int h_ema20_h4, h_ema50_h4;
int h_ema20_h1, h_ema50_h1;
int h_ema9_m15, h_ema20_m15, h_rsi_m15, h_atr14_m15;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   lastBarTime = 0;
   peakBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   h_ema20_h4  = iMA(_Symbol, PERIOD_H4, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema50_h4  = iMA(_Symbol, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_ema50_h1  = iMA(_Symbol, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
   
   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   h_rsi_m15   = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15 = iATR(_Symbol, PERIOD_M15, 14);
   
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   IndicatorRelease(h_ema20_h4); IndicatorRelease(h_ema50_h4);
   IndicatorRelease(h_ema20_h1); IndicatorRelease(h_ema50_h1);
   IndicatorRelease(h_ema9_m15); IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_rsi_m15);  IndicatorRelease(h_atr14_m15);
}

void OnTick()
{
   // Manage Open Positions (Trailing Stop / Break-Even)
   ManagePositions();

   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance > peakBalance) peakBalance = balance;
   
   double current_dd = (peakBalance - balance) / peakBalance;
   if(current_dd >= InpMaxDrawdownLimit) return;
   if(PositionsTotal() > 0) return;
   
   // Copy H4 Trend (Index 1)
   double ema20_h4[], ema50_h4[];
   ArraySetAsSeries(ema20_h4, true); ArraySetAsSeries(ema50_h4, true);
   if(CopyBuffer(h_ema20_h4, 0, 1, 2, ema20_h4) < 2) return;
   if(CopyBuffer(h_ema50_h4, 0, 1, 2, ema50_h4) < 2) return;
   bool h4_bull = (ema20_h4[0] > ema50_h4[0]);
   bool h4_bear = (ema20_h4[0] < ema50_h4[0]);
   
   // Copy H1 Trend (Index 1)
   double ema20_h1[], ema50_h1[];
   ArraySetAsSeries(ema20_h1, true); ArraySetAsSeries(ema50_h1, true);
   if(CopyBuffer(h_ema20_h1, 0, 1, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema50_h1, 0, 1, 2, ema50_h1) < 2) return;
   bool h1_bull = (ema20_h1[0] > ema50_h1[0]);
   bool h1_bear = (ema20_h1[0] < ema50_h1[0]);
   
   // Copy M15 Indicators
   double ema9_m15[], ema20_m15[], rsi[], atr[];
   ArraySetAsSeries(ema9_m15, true); ArraySetAsSeries(ema20_m15, true);
   ArraySetAsSeries(rsi, true);      ArraySetAsSeries(atr, true);
   if(CopyBuffer(h_ema9_m15, 0, 1, 2, ema9_m15) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 1, 2, ema20_m15) < 2) return;
   if(CopyBuffer(h_rsi_m15, 0, 1, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 1, 2, atr) < 2) return;
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 5, rates) < 5) return;
   
   double close = rates[0].close;
   double open  = rates[0].open;
   double high  = rates[0].high;
   double low   = rates[0].low;
   double body  = MathAbs(close - open) + 0.00001;
   double lwick = MathMin(open, close) - low;
   double uwick = high - MathMax(open, close);
   
   double av = atr[0]; if(av < 0.8) av = 0.8;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   // BUY Signal: H4 Bull + H1 Bull + Oversold Pullback to EMA20 + Bullish Rejection Wick
   bool buy_sig = h4_bull && h1_bull && (rates[1].low <= ema20_m15[1]) && (rsi[1] < 48.0) && (close > ema9_m15[0]) && (lwick >= 0.40 * body);
   
   // SELL Signal: H4 Bear + H1 Bear + Overbought Rally to EMA20 + Bearish Rejection Wick
   bool sell_sig = h4_bear && h1_bear && (rates[1].high >= ema20_m15[1]) && (rsi[1] > 52.0) && (close < ema9_m15[0]) && (uwick >= 0.40 * body);
   
   double active_risk = InpRiskPct;
   if(current_dd >= 0.10) active_risk = 0.012; // Safety brake
   
   if(buy_sig)
   {
      double sl_dist = av * 1.5 + 0.30;
      double tp_dist = av * 3.0;
      double risk_amount = balance * active_risk;
      double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_sz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tick_sz <= 0) tick_sz = 0.01; if(tick_val <= 0) tick_val = 1.0;
      double loss_per_lot = (sl_dist / tick_sz) * tick_val;
      double lot_size = NormalizeDouble(risk_amount / loss_per_lot, 2);
      if(lot_size < 0.01) lot_size = 0.01; if(lot_size > 10.0) lot_size = 10.0;
      
      double sl_price = NormalizeDouble(ask - sl_dist, _Digits);
      double tp_price = NormalizeDouble(ask + tp_dist, _Digits);
      trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
   }
   else if(sell_sig)
   {
      double sl_dist = av * 1.5 + 0.30;
      double tp_dist = av * 3.0;
      double risk_amount = balance * active_risk;
      double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_sz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tick_sz <= 0) tick_sz = 0.01; if(tick_val <= 0) tick_val = 1.0;
      double loss_per_lot = (sl_dist / tick_sz) * tick_val;
      double lot_size = NormalizeDouble(risk_amount / loss_per_lot, 2);
      if(lot_size < 0.01) lot_size = 0.01; if(lot_size > 10.0) lot_size = 10.0;
      
      double sl_price = NormalizeDouble(bid + sl_dist, _Digits);
      double tp_price = NormalizeDouble(bid - tp_dist, _Digits);
      trade.Sell(lot_size, _Symbol, bid, sl_price, tp_price, InpTradeComment);
   }
}

void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         ulong ticket = PositionGetInteger(POSITION_TICKET);
         double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
         double current_sl = PositionGetDouble(POSITION_SL);
         double current_price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         
         double atr[];
         ArraySetAsSeries(atr, true);
         if(CopyBuffer(h_atr14_m15, 0, 0, 1, atr) < 1) continue;
         double av = atr[0]; if(av < 0.8) av = 0.8;
         
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
         {
            // Move to Break-even when price reaches 1.5 * ATR profit
            if(current_price >= open_price + av * 1.5 && current_sl < open_price)
            {
               double new_sl = NormalizeDouble(open_price + 0.20, _Digits);
               trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }
         }
         else if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
         {
            if(current_price <= open_price - av * 1.5 && (current_sl > open_price || current_sl == 0))
            {
               double new_sl = NormalizeDouble(open_price - 0.20, _Digits);
               trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }
         }
      }
   }
}
"""

def test_cp500():
    print("="*105)
    print("TESTING CP-500 ROBUST PULLBACK ON NATIVE MT5 TESTER (MODEL 0 REAL TICKS)")
    print("="*105)
    
    mq5_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", "ALAB_CP500_RobustPullbackEA.mq5")
    ex5_path = mq5_path.replace('.mq5', '.ex5')
    log_path = mq5_path.replace('.mq5', '.log')
    
    with open(mq5_path, 'w', encoding='utf-8') as f:
        f.write(CP500_MQL5)
        
    cmd_compile = [METAEDITOR, f"/compile:{mq5_path}", f"/log:{log_path}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    if os.path.exists(ex5_path):
        print("Successfully compiled ALAB_CP500_RobustPullbackEA.ex5")
        for root in [
            r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
            r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
            r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
        ]:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(ex5_path, os.path.join(dest_dir, "ALAB_CP500_RobustPullbackEA.ex5"))
            
        ini_path = os.path.join(DATA_DIR, "run_cp500.ini")
        ini_content = f"""[Tester]
Expert=AlphaLab\\alphalab\\ALAB_CP500_RobustPullbackEA.ex5
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
ShutdownTerminal=1
"""
        with open(ini_path, 'w', encoding='utf-8') as f:
            f.write(ini_content)
            
        cmd_run = [TERMINAL, f"/config:{ini_path}"]
        print("Launching native MT5 Strategy Tester process for CP-500...")
        proc = subprocess.Popen(cmd_run)
        proc.wait()
        
        if os.path.exists(AGENT_LOG):
            with open(AGENT_LOG, 'r', encoding='utf-16-le', errors='ignore') as f:
                lines = f.readlines()
            for l in reversed(lines[-200:]):
                if "final balance" in l:
                    print("="*105)
                    print(f"OFFICIAL MT5 TESTER RESULT FOR CP-500: {l.strip()}")
                    print("="*105)
                    break

if __name__ == '__main__':
    test_cp500()
