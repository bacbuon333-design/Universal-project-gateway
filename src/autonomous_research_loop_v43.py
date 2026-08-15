"""
V43: MULTI-ENGINE STRATEGY SWEEP (3 NEW SIGNAL ENGINES)
========================================================
Engine A: H1 EMA Crossover + Trailing Stop (inspired by Moving Average EA)
Engine B: MACD Crossover + EMA Trend (inspired by MACD Sample EA)
Engine C: Original 7-cond BUY + Symmetric SELL (dual-direction)
All with proven R6101 lot sizing + smooth compounding.
"""
import os, sys, shutil, subprocess, time
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
CLEAN_ROOM = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "CleanRoom")
TERMINAL_ROOTS = [DATA_DIR,
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"]

def kill_terminal():
    subprocess.run(["taskkill","/F","/IM","terminal64.exe","/T"], capture_output=True); time.sleep(2)

###############################################################################
# ENGINE A: H1 EMA9/EMA20 Crossover + ATR Trailing Stop (BUY+SELL)
###############################################################################
def gen_engine_a(ver, br, am, cap, dbt, dbm, trail_atr):
    return f"""#property copyright "AlphaLab Antigravity"
#property version   "{ver}.100"
#include <Trade\\Trade.mqh>
input double InpBaseRiskPct={br:.4f};
input double InpAccelMult={am:.4f};
input double InpAccelCap={cap:.1f};
input double InpDDBrakeThreshPct={dbt:.4f};
input double InpDDBrakeRiskMult={dbm:.4f};
input double InpSLATRMult=1.5000;
input double InpTrailATRMult={trail_atr:.4f};
input double InpMaxDrawdownLimit=0.200;
input ulong  InpMagicNumber=202600000+{ver};
input string InpTradeComment="ALAB_R{ver}";
CTrade trade; datetime lastBarTime; double peakEquity; bool isHalted;
int h_e9h,h_e20h,h_e200h,h_a14h;
int OnInit(){{
  if(!MQLInfoInteger(MQL_TESTER))return(INIT_FAILED);
  trade.SetExpertMagicNumber(InpMagicNumber); lastBarTime=0;
  peakEquity=AccountInfoDouble(ACCOUNT_EQUITY); isHalted=false;
  h_e9h=iMA(_Symbol,PERIOD_H1,9,0,MODE_EMA,PRICE_CLOSE);
  h_e20h=iMA(_Symbol,PERIOD_H1,20,0,MODE_EMA,PRICE_CLOSE);
  h_e200h=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);
  h_a14h=iATR(_Symbol,PERIOD_H1,14);
  return(INIT_SUCCEEDED);
}}
void OnDeinit(const int r){{
  IndicatorRelease(h_e9h);IndicatorRelease(h_e20h);
  IndicatorRelease(h_e200h);IndicatorRelease(h_a14h);
}}
void CloseOwned(ENUM_POSITION_TYPE dir){{
  for(int i=PositionsTotal()-1;i>=0;i--){{
    ulong t=PositionGetTicket(i);
    if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol){{
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==dir)
        trade.PositionClose(t);
    }}
  }}
}}
void CloseAll(){{for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)trade.PositionClose(t);}}}}
int CountPos(){{int c=0;for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}}return c;}}
void TrailStops(double atr_val){{
  double trail=atr_val*InpTrailATRMult;
  for(int i=PositionsTotal()-1;i>=0;i--){{
    ulong t=PositionGetTicket(i);
    if(t<=0||PositionGetInteger(POSITION_MAGIC)!=InpMagicNumber||PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
    ENUM_POSITION_TYPE ptype=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double sl=PositionGetDouble(POSITION_SL);
    if(ptype==POSITION_TYPE_BUY){{
      double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      double newsl=NormalizeDouble(bid-trail,_Digits);
      if(newsl>sl+0.01) trade.PositionModify(t,newsl,PositionGetDouble(POSITION_TP));
    }}else{{
      double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double newsl=NormalizeDouble(ask+trail,_Digits);
      if(sl<=0||newsl<sl-0.01) trade.PositionModify(t,newsl,PositionGetDouble(POSITION_TP));
    }}
  }}
}}
void OnTick(){{
  if(!MQLInfoInteger(MQL_TESTER))return;
  double eq=AccountInfoDouble(ACCOUNT_EQUITY);
  if(eq>peakEquity)peakEquity=eq;
  double edd=(peakEquity>0)?(peakEquity-eq)/peakEquity:0;
  if(isHalted||edd>=InpMaxDrawdownLimit){{isHalted=true;CloseAll();return;}}
  // Trailing stop on every tick
  double atr_trail[];ArraySetAsSeries(atr_trail,true);
  if(CopyBuffer(h_a14h,0,0,1,atr_trail)>=1&&atr_trail[0]>0) TrailStops(atr_trail[0]);
  // Signal check on new H1 bar
  datetime bt=iTime(_Symbol,PERIOD_H1,0);
  if(bt==lastBarTime)return; lastBarTime=bt;
  double e9[],e20[],e200[],a14[];
  ArraySetAsSeries(e9,true);ArraySetAsSeries(e20,true);
  ArraySetAsSeries(e200,true);ArraySetAsSeries(a14,true);
  if(CopyBuffer(h_e9h,0,1,3,e9)<3)return;
  if(CopyBuffer(h_e20h,0,1,3,e20)<3)return;
  if(CopyBuffer(h_e200h,0,1,2,e200)<2)return;
  if(CopyBuffer(h_a14h,0,1,2,a14)<2)return;
  double av=MathMax(a14[0],0.8);
  // EMA9/EMA20 crossover
  bool cross_up=(e9[0]>e20[0])&&(e9[1]<=e20[1]);
  bool cross_dn=(e9[0]<e20[0])&&(e9[1]>=e20[1]);
  bool above200=(e20[0]>e200[0]);
  bool below200=(e20[0]<e200[0]);
  bool buy_sig=cross_up&&above200;
  bool sell_sig=cross_dn&&below200;
  // Close opposite on signal
  if(buy_sig) CloseOwned(POSITION_TYPE_SELL);
  if(sell_sig) CloseOwned(POSITION_TYPE_BUY);
  if(!buy_sig&&!sell_sig)return;
  if(CountPos()>0)return;
  // Lot sizing
  double bal=AccountInfoDouble(ACCOUNT_BALANCE);
  double pm=MathMin(InpAccelCap,1.0+(bal-1000.0)/1000.0*(InpAccelMult-1.0));
  double crp=InpBaseRiskPct*pm;
  double arp=(edd>=InpDDBrakeThreshPct)?(crp*InpDDBrakeRiskMult):crp;
  double ra=bal*arp;
  double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
  double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
  if(ts<=0)ts=0.01;if(tv<=0)tv=1.0;
  double sld=av*InpSLATRMult;
  double oll=(sld/ts)*tv;oll=MathAbs(oll);
  if(oll<=0)return;
  double rv=ra/oll;
  double vn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double vx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
  double ls=NormalizeDouble(rv,2);
  if(ls<vn)ls=vn;if(ls>vx)ls=vx;
  if(buy_sig){{
    double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
    double slp=NormalizeDouble(ask-sld,_Digits);
    trade.Buy(ls,_Symbol,ask,slp,0,InpTradeComment);
  }}
  if(sell_sig){{
    double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
    double slp=NormalizeDouble(bid+sld,_Digits);
    trade.Sell(ls,_Symbol,bid,slp,0,InpTradeComment);
  }}
}}"""

###############################################################################
# ENGINE B: MACD Crossover + EMA Trend + Trailing (BUY+SELL)
###############################################################################
def gen_engine_b(ver, br, am, cap, dbt, dbm, trail_atr):
    return f"""#property copyright "AlphaLab Antigravity"
#property version   "{ver}.100"
#include <Trade\\Trade.mqh>
input double InpBaseRiskPct={br:.4f};
input double InpAccelMult={am:.4f};
input double InpAccelCap={cap:.1f};
input double InpDDBrakeThreshPct={dbt:.4f};
input double InpDDBrakeRiskMult={dbm:.4f};
input double InpSLATRMult=1.5000;
input double InpTrailATRMult={trail_atr:.4f};
input double InpMaxDrawdownLimit=0.200;
input ulong  InpMagicNumber=202600000+{ver};
input string InpTradeComment="ALAB_R{ver}";
CTrade trade; datetime lastBarTime; double peakEquity; bool isHalted;
int h_macd,h_ema200,h_a14;
int OnInit(){{
  if(!MQLInfoInteger(MQL_TESTER))return(INIT_FAILED);
  trade.SetExpertMagicNumber(InpMagicNumber); lastBarTime=0;
  peakEquity=AccountInfoDouble(ACCOUNT_EQUITY); isHalted=false;
  h_macd=iMACD(_Symbol,PERIOD_H1,12,26,9,PRICE_CLOSE);
  h_ema200=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);
  h_a14=iATR(_Symbol,PERIOD_H1,14);
  return(INIT_SUCCEEDED);
}}
void OnDeinit(const int r){{IndicatorRelease(h_macd);IndicatorRelease(h_ema200);IndicatorRelease(h_a14);}}
void CloseAll(){{for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)trade.PositionClose(t);}}}}
void CloseOwned(ENUM_POSITION_TYPE dir){{for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol&&(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==dir)trade.PositionClose(t);}}}}
int CountPos(){{int c=0;for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}}return c;}}
void TrailStops(double atr_val){{
  double trail=atr_val*InpTrailATRMult;
  for(int i=PositionsTotal()-1;i>=0;i--){{
    ulong t=PositionGetTicket(i);
    if(t<=0||PositionGetInteger(POSITION_MAGIC)!=InpMagicNumber||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
    ENUM_POSITION_TYPE pt=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double sl=PositionGetDouble(POSITION_SL);
    if(pt==POSITION_TYPE_BUY){{double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);double ns=NormalizeDouble(bid-trail,_Digits);if(ns>sl+0.01)trade.PositionModify(t,ns,0);}}
    else{{double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);double ns=NormalizeDouble(ask+trail,_Digits);if(sl<=0||ns<sl-0.01)trade.PositionModify(t,ns,0);}}
  }}
}}
void OnTick(){{
  if(!MQLInfoInteger(MQL_TESTER))return;
  double eq=AccountInfoDouble(ACCOUNT_EQUITY);
  if(eq>peakEquity)peakEquity=eq;
  double edd=(peakEquity>0)?(peakEquity-eq)/peakEquity:0;
  if(isHalted||edd>=InpMaxDrawdownLimit){{isHalted=true;CloseAll();return;}}
  double atr_now[];ArraySetAsSeries(atr_now,true);
  if(CopyBuffer(h_a14,0,0,1,atr_now)>=1&&atr_now[0]>0)TrailStops(atr_now[0]);
  datetime bt=iTime(_Symbol,PERIOD_H1,0);
  if(bt==lastBarTime)return; lastBarTime=bt;
  double macd_m[],macd_s[],ema200[],a14[];
  ArraySetAsSeries(macd_m,true);ArraySetAsSeries(macd_s,true);
  ArraySetAsSeries(ema200,true);ArraySetAsSeries(a14,true);
  if(CopyBuffer(h_macd,0,1,3,macd_m)<3)return;
  if(CopyBuffer(h_macd,1,1,3,macd_s)<3)return;
  if(CopyBuffer(h_ema200,0,1,2,ema200)<2)return;
  if(CopyBuffer(h_a14,0,1,2,a14)<2)return;
  double av=MathMax(a14[0],0.8);
  MqlRates rt[];ArraySetAsSeries(rt,true);
  if(CopyRates(_Symbol,PERIOD_H1,1,2,rt)<2)return;
  bool macd_cross_up=(macd_m[0]>macd_s[0])&&(macd_m[1]<=macd_s[1]);
  bool macd_cross_dn=(macd_m[0]<macd_s[0])&&(macd_m[1]>=macd_s[1]);
  bool above200=(rt[0].close>ema200[0]);
  bool below200=(rt[0].close<ema200[0]);
  bool buy_sig=macd_cross_up&&above200;
  bool sell_sig=macd_cross_dn&&below200;
  if(buy_sig)CloseOwned(POSITION_TYPE_SELL);
  if(sell_sig)CloseOwned(POSITION_TYPE_BUY);
  if(!buy_sig&&!sell_sig)return;
  if(CountPos()>0)return;
  double bal=AccountInfoDouble(ACCOUNT_BALANCE);
  double pm=MathMin(InpAccelCap,1.0+(bal-1000.0)/1000.0*(InpAccelMult-1.0));
  double crp=InpBaseRiskPct*pm;
  double arp=(edd>=InpDDBrakeThreshPct)?(crp*InpDDBrakeRiskMult):crp;
  double ra=bal*arp;
  double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
  double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
  if(ts<=0)ts=0.01;if(tv<=0)tv=1.0;
  double sld=av*InpSLATRMult;
  double oll=(sld/ts)*tv;oll=MathAbs(oll);if(oll<=0)return;
  double rv=ra/oll;
  double vn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double vx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
  double ls=NormalizeDouble(rv,2);if(ls<vn)ls=vn;if(ls>vx)ls=vx;
  if(buy_sig){{double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);trade.Buy(ls,_Symbol,ask,NormalizeDouble(ask-sld,_Digits),0,InpTradeComment);}}
  if(sell_sig){{double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);trade.Sell(ls,_Symbol,bid,NormalizeDouble(bid+sld,_Digits),0,InpTradeComment);}}
}}"""

def parse(rp):
    if not os.path.exists(rp): return None
    try:
        with open(rp,'r',encoding='utf-16-le',errors='ignore') as f: c=f.read()
        if len(c)<100:
            with open(rp,'r',encoding='utf-8',errors='ignore') as f: c=f.read()
        soup=BeautifulSoup(c,'html.parser')
        pnl=pf=dd=0;trades=0
        for r in soup.find_all('tr'):
            cols=[x.get_text(strip=True) for x in r.find_all(['td','th'])]
            txt=' '.join(cols)
            if 'Total Net Profit:' in txt:
                try: pnl=float(cols[cols.index('Total Net Profit:')+1].replace(' ','').replace(',',''))
                except: pass
            if 'Profit Factor:' in txt:
                try: pf=float(cols[cols.index('Profit Factor:')+1].replace(' ','').replace(',',''))
                except: pass
            if 'Equity Drawdown Relative:' in txt:
                for x in cols:
                    if '%' in x and '(' in x:
                        try: dd=float(x.split('%')[0])
                        except: pass
            if 'Total Trades:' in txt:
                try: trades=int(cols[cols.index('Total Trades:')+1])
                except: pass
        return {'pnl':pnl,'pf':pf,'dd':dd,'trades':trades}
    except: return None

def make_ini(ver):
    lines = ["[Tester]",
        f"Expert=AlphaLab\\CleanRoom\\AlphaLabR{ver}_SmoothDiagonalMasterEA.ex5",
        "Symbol=GOLD","Period=H1","Deposit=1000","Currency=USD",
        "Leverage=1:500","Model=4","ExecutionMode=0","Optimization=0",
        "FromDate=2022.05.01","ToDate=2026.07.27",
        f"Report=MQL5\\Experts\\AlphaLab\\r{ver}_gold_exec_report",
        "ReplaceReport=1","ShutdownTerminal=1"]
    return "\n".join(lines)+"\n"

def run():
    print("="*100)
    print("V43: MULTI-ENGINE STRATEGY SWEEP (NEW SIGNAL ENGINES)")
    print("="*100)
    # (ver, engine_fn, br, am, cap, dbt, dbm, trail_atr, label)
    cfgs=[
        # ENGINE A: H1 EMA Crossover + Trailing (BUY+SELL)
        (6501, gen_engine_a, 0.040, 2.50, 6.0, 0.080, 0.12, 2.0, "EMA_Cross Trail=2.0"),
        (6502, gen_engine_a, 0.050, 3.00, 7.0, 0.080, 0.12, 2.5, "EMA_Cross Trail=2.5"),
        (6503, gen_engine_a, 0.060, 3.50, 8.0, 0.080, 0.12, 1.5, "EMA_Cross Trail=1.5"),
        (6504, gen_engine_a, 0.045, 2.80, 6.0, 0.080, 0.12, 3.0, "EMA_Cross Trail=3.0"),
        # ENGINE B: MACD Crossover + EMA200 + Trailing (BUY+SELL)
        (6505, gen_engine_b, 0.040, 2.50, 6.0, 0.080, 0.12, 2.0, "MACD_Cross Trail=2.0"),
        (6506, gen_engine_b, 0.050, 3.00, 7.0, 0.080, 0.12, 2.5, "MACD_Cross Trail=2.5"),
        (6507, gen_engine_b, 0.060, 3.50, 8.0, 0.080, 0.12, 1.5, "MACD_Cross Trail=1.5"),
        (6508, gen_engine_b, 0.045, 2.80, 6.0, 0.080, 0.12, 3.0, "MACD_Cross Trail=3.0"),
    ]
    best=None
    for cfg in cfgs:
        ver,gen_fn,br,am,cap,dbt,dbm,trail,label=cfg
        print(f"\n--- R{ver}: {label} Risk={br*100:.1f}% Accel={am:.1f}x ---")
        kill_terminal()
        mf=os.path.join(CLEAN_ROOM,f"AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5")
        ini_path=os.path.join(DATA_DIR,f"gen_r{ver}.ini")
        rp=os.path.join(DATA_DIR,"MQL5","Experts","AlphaLab",f"r{ver}_gold_exec_report.htm")
        code=gen_fn(ver,br,am,cap,dbt,dbm,trail)
        with open(mf,'w',encoding='utf-8') as f: f.write(code)
        subprocess.run([METAEDITOR_EXE,f"/compile:{mf}",f"/log:{mf.replace('.mq5','.log')}"],capture_output=True)
        ex5=mf.replace('.mq5','.ex5')
        if not os.path.exists(ex5): print("  COMPILE FAIL"); continue
        for root in TERMINAL_ROOTS:
            d=os.path.join(root,"MQL5","Experts","AlphaLab","CleanRoom")
            os.makedirs(d,exist_ok=True)
            try: shutil.copy2(ex5,os.path.join(d,os.path.basename(ex5)))
            except: pass
        with open(ini_path,'w',encoding='utf-8') as f: f.write(make_ini(ver))
        print(f"  MT5 Model=4...")
        subprocess.run([TERMINAL_EXE,f"/config:{ini_path}"],capture_output=True)
        res=parse(rp)
        if not res: print("  PARSE FAIL"); continue
        ok=res['pnl']>4000 and res['pf']>=1.50 and res['dd']<=20.00
        print(f"  PnL=${res['pnl']:.2f} PF={res['pf']:.2f} DD={res['dd']:.2f}% Trades={res['trades']} [{'*** PASS ***' if ok else 'FAIL'}]")
        if ok: best=(ver,res); break
    if best: print(f"\nWINNER: R{best[0]} PnL=${best[1]['pnl']:.2f}")
    else: print("\nNo winner.")

if __name__=='__main__': run()
