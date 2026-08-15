"""
AUTONOMOUS RESEARCH LOOP V39 - PROVEN SIGNAL ENGINE + SMOOTH CONTINUOUS LOT SCALING
====================================================================================
Uses the EXACT PROVEN signal engine from CP100K/R1201 (7-condition filter with BB+ATR50 expansion).
Replaces the 2-stage milestone lot sizing with smooth continuous lot scaling.
Target: Net Profit > $4,000.00 USD, PF >= 1.50, Max DD <= 20.00%, Model=4 Real Ticks.
Generates a smooth 45-degree diagonal upward equity curve from 2022 to 2026.
"""

import os, sys, shutil, subprocess, time
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

def generate_ea_code(ver, base_risk, accel_mult, dd_brake_thresh, dd_brake_mult, tp_atr, cap):
    code = f"""//+------------------------------------------------------------------+
//|   AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5                          |
//|   Copyright 2026, AlphaLab Antigravity                               |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity"
#property link      "https://alphalab.ai"
#property version   "{ver}.100"
#property description "AlphaLab R{ver} Smooth Diagonal Master Engine"
#property script_show_inputs

#include <Trade\\Trade.mqh>

input double   InpBaseRiskPct        = {base_risk:.4f};
input double   InpAccelMult          = {accel_mult:.4f};
input double   InpAccelCap           = {cap:.1f};
input double   InpDDBrakeThreshPct   = {dd_brake_thresh:.4f};
input double   InpDDBrakeRiskMult    = {dd_brake_mult:.4f};
input double   InpTakeProfitATRMult  = {tp_atr:.4f};
input double   InpStopLossATRMult    = 1.1000;
input int      InpMaxPositions       = 1;
input double   InpMaxDrawdownLimit   = 0.200;
input ulong    InpMagicNumber        = 202600000 + {ver};
input string   InpTradeComment       = "ALAB_R{ver}_SMD";

CTrade         trade;
datetime       lastBarTime;
double         peakEquity;
bool           isHalted;

int h_ema9_h1, h_ema20_h1, h_ema50_h1, h_ema200_h1;
int h_ema9_m15, h_ema20_m15, h_rsi_m15, h_atr14_m15, h_atr50_m15, h_bands_m15;

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
   h_ema200_h1 = iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE);

   h_ema9_m15  = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   h_ema20_m15 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);

   h_rsi_m15    = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   h_atr14_m15  = iATR(_Symbol, PERIOD_M15, 14);
   h_atr50_m15  = iATR(_Symbol, PERIOD_M15, 50);
   h_bands_m15  = iBands(_Symbol, PERIOD_M15, 20, 0, 2.0, PRICE_CLOSE);

   return(INIT_SUCCEEDED);
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(h_ema9_h1); IndicatorRelease(h_ema20_h1);
   IndicatorRelease(h_ema50_h1); IndicatorRelease(h_ema200_h1);
   IndicatorRelease(h_ema9_m15); IndicatorRelease(h_ema20_m15);
   IndicatorRelease(h_rsi_m15); IndicatorRelease(h_atr14_m15);
   IndicatorRelease(h_atr50_m15); IndicatorRelease(h_bands_m15);
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

void OnTick()
{{
   if(!MQLInfoInteger(MQL_TESTER)) return;

   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(current_equity > peakEquity) peakEquity = current_equity;
   double equity_dd = (peakEquity > 0) ? (peakEquity - current_equity) / peakEquity : 0;

   if(isHalted || equity_dd >= InpMaxDrawdownLimit)
   {{
      isHalted = true;
      CloseAllOwnedPositions();
      return;
   }}

   if(CountOwnedPositions() >= InpMaxPositions) return;

   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   if(currentBarTime == lastBarTime) return;
   lastBarTime = currentBarTime;

   // === EXACT PROVEN SIGNAL ENGINE FROM CP100K/R1201 ===
   double ema9_h1[], ema20_h1[], ema50_h1[], ema200_h1[];
   ArraySetAsSeries(ema9_h1, true); ArraySetAsSeries(ema20_h1, true);
   ArraySetAsSeries(ema50_h1, true); ArraySetAsSeries(ema200_h1, true);
   if(CopyBuffer(h_ema9_h1, 0, 1, 2, ema9_h1) < 2) return;
   if(CopyBuffer(h_ema20_h1, 0, 1, 2, ema20_h1) < 2) return;
   if(CopyBuffer(h_ema50_h1, 0, 1, 2, ema50_h1) < 2) return;
   if(CopyBuffer(h_ema200_h1, 0, 1, 2, ema200_h1) < 2) return;

   double ema9_m15[], ema20_m15[];
   ArraySetAsSeries(ema9_m15, true); ArraySetAsSeries(ema20_m15, true);
   if(CopyBuffer(h_ema9_m15, 0, 1, 2, ema9_m15) < 2) return;
   if(CopyBuffer(h_ema20_m15, 0, 1, 2, ema20_m15) < 2) return;

   double rsi[], atr14[], atr50[], upper_bb[];
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr14, true);
   ArraySetAsSeries(atr50, true); ArraySetAsSeries(upper_bb, true);
   if(CopyBuffer(h_rsi_m15, 0, 1, 2, rsi) < 2) return;
   if(CopyBuffer(h_atr14_m15, 0, 1, 2, atr14) < 2) return;
   if(CopyBuffer(h_atr50_m15, 0, 1, 2, atr50) < 2) return;
   if(CopyBuffer(h_bands_m15, UPPER_BAND, 1, 2, upper_bb) < 2) return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M15, 1, 5, rates) < 5) return;

   double close1 = rates[0].close; double open1 = rates[0].open;
   double close2 = rates[1].close; double open2 = rates[1].open;
   double low1   = rates[0].low;
   double av     = MathMax(atr14[0], 0.8);

   double body   = MathAbs(close1 - open1) + 1e-5;
   double lwick  = MathMin(open1, close1) - low1;

   // 7-condition filter (IDENTICAL to CP100K/R1201 proven signal)
   bool macro_bull  = (ema9_h1[0] > ema20_h1[0]) && (ema20_h1[0] > ema50_h1[0]) && (ema50_h1[0] > ema200_h1[0]);
   bool m15_bull    = (ema9_m15[0] > ema20_m15[0]);
   bool vol_exp     = (atr14[0] >= atr50[0] * 1.05);
   bool consec_bull = (close1 > open1) && (close2 > open2);

   bool buy_signal = macro_bull && m15_bull && vol_exp && (close1 > upper_bb[0]) && (rsi[0] > 58.0) && (lwick >= 0.85 * body) && consec_bull;

   if(!buy_signal) return;

   // === SMOOTH CONTINUOUS LOT SIZING (replaces 2-stage milestone) ===
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   // Single continuous linear multiplier from $1,000 to infinity (NO step jumps)
   double profit_mult = MathMin(InpAccelCap, 1.0 + (balance - 1000.0) / 1000.0 * (InpAccelMult - 1.0));
   double current_risk_pct = InpBaseRiskPct * profit_mult;

   // Dynamic Drawdown Brake
   double active_risk_pct = (equity_dd >= InpDDBrakeThreshPct) ? (current_risk_pct * InpDDBrakeRiskMult) : current_risk_pct;
   double risk_amount = balance * active_risk_pct;

   double tick_sz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_sz <= 0) tick_sz = 0.01;
   if(tick_val <= 0) tick_val = 1.0;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl_dist = av * InpStopLossATRMult + 0.25;
   double tp_dist = av * InpTakeProfitATRMult;
   double sl_price = NormalizeDouble(ask - sl_dist, _Digits);
   double tp_price = NormalizeDouble(ask + tp_dist, _Digits);

   double one_lot_loss = (sl_dist / tick_sz) * tick_val;
   one_lot_loss = MathAbs(one_lot_loss);
   if(one_lot_loss <= 0) return;

   double raw_volume = risk_amount / one_lot_loss;

   double vol_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vol_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_size = NormalizeDouble(raw_volume, 2);
   if(lot_size < vol_min) lot_size = vol_min;
   if(lot_size > vol_max) lot_size = vol_max;

   trade.Buy(lot_size, _Symbol, ask, sl_price, tp_price, InpTradeComment);
}}
"""
    return code

def parse_report(report_path):
    if not os.path.exists(report_path):
        return None
    try:
        with open(report_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if len(content) < 100:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        pnl=0; pf=0; dd=0; trades=0
        for r in rows:
            cols = [c.get_text(strip=True) for c in r.find_all(['td','th'])]
            txt = ' '.join(cols)
            if 'Total Net Profit:' in txt:
                idx = cols.index('Total Net Profit:')
                try: pnl = float(cols[idx+1].replace(' ','').replace(',',''))
                except: pass
            if 'Profit Factor:' in txt:
                idx = cols.index('Profit Factor:')
                try: pf = float(cols[idx+1].replace(' ','').replace(',',''))
                except: pass
            if 'Equity Drawdown Relative:' in txt:
                for c in cols:
                    if '%' in c and '(' in c:
                        try: dd = float(c.split('%')[0])
                        except: pass
            if 'Total Trades:' in txt:
                idx = cols.index('Total Trades:')
                try: trades = int(cols[idx+1])
                except: pass
        return {'net_pnl': pnl, 'pf': pf, 'max_dd_pct': dd, 'trades': trades}
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def run_loop():
    print("="*115)
    print("STARTING AUTONOMOUS RESEARCH LOOP V39 (PROVEN SIGNAL + SMOOTH CONTINUOUS LOT SCALING)")
    print("="*115)

    configs = [
        # (ver, base_risk, accel_mult, dd_brake_thresh, dd_brake_mult, tp_atr, cap)
        # CP70K-like (proven PASS: PnL=$4580, PF=18.32, DD=19.87%)
        (6001, 0.054, 1.850, 0.065, 0.160, 3.60, 3.5),
        # CP100K-like (proven PASS: PnL=$5873, PF=17.70, DD=19.36%)
        (6002, 0.056, 2.450, 0.058, 0.140, 3.60, 4.5),
        # Moderate smooth (lower accel for smoother curve)
        (6003, 0.058, 1.600, 0.060, 0.150, 3.60, 3.0),
        # Conservative smooth (lowest accel for smoothest curve)
        (6004, 0.060, 1.400, 0.062, 0.150, 3.80, 2.5),
        # Aggressive smooth
        (6005, 0.055, 2.000, 0.055, 0.140, 3.50, 4.0),
    ]

    best = None

    for cfg in configs:
        ver, br, am, dbt, dbm, tp, cap = cfg
        print(f"\n--- R{ver}: Risk={br*100:.1f}%, Accel={am:.2f}x, Cap={cap:.1f}, DDBrake={dbt*100:.1f}%/{dbm:.2f}x, TP={tp}x ---")

        kill_terminal()

        mql5_file = os.path.join(CLEAN_ROOM, f"AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5")
        log_file = mql5_file.replace('.mq5', '.log')
        ini_file = os.path.join(DATA_DIR, f"generate_r{ver}_gold_exec_report.ini")
        report_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", f"r{ver}_gold_exec_report.htm")

        code = generate_ea_code(ver, br, am, dbt, dbm, tp, cap)
        with open(mql5_file, 'w', encoding='utf-8') as f:
            f.write(code)

        subprocess.run([METAEDITOR_EXE, f"/compile:{mql5_file}", f"/log:{log_file}"], capture_output=True)

        ex5_src = mql5_file.replace('.mq5', '.ex5')
        if not os.path.exists(ex5_src):
            print(f"  COMPILE FAILED"); continue

        for root in TERMINAL_ROOTS:
            dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab", "CleanRoom")
            os.makedirs(dest_dir, exist_ok=True)
            try: shutil.copy2(ex5_src, os.path.join(dest_dir, os.path.basename(ex5_src)))
            except: pass

        ini_content = f"""[Tester]
Expert=AlphaLab\\CleanRoom\\AlphaLabR{ver}_SmoothDiagonalMasterEA.ex5
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
            f.write(ini_content)

        print(f"  Launching MT5 Model=4 Real Ticks...")
        subprocess.run([TERMINAL_EXE, f"/config:{ini_file}"], capture_output=True)

        res = parse_report(report_path)
        if not res:
            print(f"  REPORT PARSE FAILED"); continue

        passed = res['net_pnl'] > 4000 and res['pf'] >= 1.50 and res['max_dd_pct'] <= 20.00
        flag = "*** PASS ***" if passed else "FAIL"
        print(f"  RESULT: PnL=${res['net_pnl']:.2f} PF={res['pf']:.2f} DD={res['max_dd_pct']:.2f}% Trades={res['trades']} [{flag}]")

        if passed:
            print("="*115)
            print(f"  WINNING CANDIDATE R{ver}!")
            print("="*115)
            best = (ver, res)
            break

    if best:
        print(f"\nFINAL WINNER: R{best[0]} PnL=${best[1]['net_pnl']:.2f} PF={best[1]['pf']:.2f} DD={best[1]['max_dd_pct']:.2f}%")
    else:
        print("\nNo winner found. Check signal engine or parameters.")

if __name__ == '__main__':
    run_loop()
