"""
AUTONOMOUS RESEARCH LOOP V41 - ULTRA AGGRESSIVE SMOOTH DIAGONAL + PYRAMIDING
=============================================================================
MaxPositions=2, base risk 9-14%, high accel, high cap, DD brake at 12-18%.
Uses EXACT proven 7-condition signal engine.
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

def gen(ver, br, am, dbt, dbm, tp, cap, maxpos):
    return f"""#property copyright "AlphaLab Antigravity"
#property version   "{ver}.100"
#include <Trade\\Trade.mqh>
input double InpBaseRiskPct={br:.4f};
input double InpAccelMult={am:.4f};
input double InpAccelCap={cap:.1f};
input double InpDDBrakeThreshPct={dbt:.4f};
input double InpDDBrakeRiskMult={dbm:.4f};
input double InpTakeProfitATRMult={tp:.4f};
input double InpStopLossATRMult=1.1000;
input int    InpMaxPositions={maxpos};
input double InpMaxDrawdownLimit=0.200;
input ulong  InpMagicNumber=202600000+{ver};
input string InpTradeComment="ALAB_R{ver}";
CTrade trade; datetime lastBarTime; double peakEquity; bool isHalted;
int h_e9h,h_e20h,h_e50h,h_e200h,h_e9m,h_e20m,h_rsi,h_a14,h_a50,h_bb;
int OnInit(){{
  if(!MQLInfoInteger(MQL_TESTER))return(INIT_FAILED);
  trade.SetExpertMagicNumber(InpMagicNumber); lastBarTime=0;
  peakEquity=AccountInfoDouble(ACCOUNT_EQUITY); isHalted=false;
  h_e9h=iMA(_Symbol,PERIOD_H1,9,0,MODE_EMA,PRICE_CLOSE);
  h_e20h=iMA(_Symbol,PERIOD_H1,20,0,MODE_EMA,PRICE_CLOSE);
  h_e50h=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);
  h_e200h=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);
  h_e9m=iMA(_Symbol,PERIOD_M15,9,0,MODE_EMA,PRICE_CLOSE);
  h_e20m=iMA(_Symbol,PERIOD_M15,20,0,MODE_EMA,PRICE_CLOSE);
  h_rsi=iRSI(_Symbol,PERIOD_M15,14,PRICE_CLOSE);
  h_a14=iATR(_Symbol,PERIOD_M15,14); h_a50=iATR(_Symbol,PERIOD_M15,50);
  h_bb=iBands(_Symbol,PERIOD_M15,20,0,2.0,PRICE_CLOSE);
  return(INIT_SUCCEEDED);
}}
void OnDeinit(const int r){{
  IndicatorRelease(h_e9h);IndicatorRelease(h_e20h);IndicatorRelease(h_e50h);
  IndicatorRelease(h_e200h);IndicatorRelease(h_e9m);IndicatorRelease(h_e20m);
  IndicatorRelease(h_rsi);IndicatorRelease(h_a14);IndicatorRelease(h_a50);IndicatorRelease(h_bb);
}}
void CloseAll(){{for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)trade.PositionClose(t);}}}}
int CountPos(){{int c=0;for(int i=PositionsTotal()-1;i>=0;i--){{ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==InpMagicNumber&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}}return c;}}
void OnTick(){{
  if(!MQLInfoInteger(MQL_TESTER))return;
  double eq=AccountInfoDouble(ACCOUNT_EQUITY);
  if(eq>peakEquity)peakEquity=eq;
  double edd=(peakEquity>0)?(peakEquity-eq)/peakEquity:0;
  if(isHalted||edd>=InpMaxDrawdownLimit){{isHalted=true;CloseAll();return;}}
  if(CountPos()>=InpMaxPositions)return;
  datetime bt=iTime(_Symbol,PERIOD_M15,0);
  if(bt==lastBarTime)return; lastBarTime=bt;
  double e9h[],e20h[],e50h[],e200h[];
  ArraySetAsSeries(e9h,true);ArraySetAsSeries(e20h,true);
  ArraySetAsSeries(e50h,true);ArraySetAsSeries(e200h,true);
  if(CopyBuffer(h_e9h,0,1,2,e9h)<2)return;
  if(CopyBuffer(h_e20h,0,1,2,e20h)<2)return;
  if(CopyBuffer(h_e50h,0,1,2,e50h)<2)return;
  if(CopyBuffer(h_e200h,0,1,2,e200h)<2)return;
  double e9m[],e20m[];
  ArraySetAsSeries(e9m,true);ArraySetAsSeries(e20m,true);
  if(CopyBuffer(h_e9m,0,1,2,e9m)<2)return;
  if(CopyBuffer(h_e20m,0,1,2,e20m)<2)return;
  double rsi[],a14[],a50[],ubb[];
  ArraySetAsSeries(rsi,true);ArraySetAsSeries(a14,true);
  ArraySetAsSeries(a50,true);ArraySetAsSeries(ubb,true);
  if(CopyBuffer(h_rsi,0,1,2,rsi)<2)return;
  if(CopyBuffer(h_a14,0,1,2,a14)<2)return;
  if(CopyBuffer(h_a50,0,1,2,a50)<2)return;
  if(CopyBuffer(h_bb,UPPER_BAND,1,2,ubb)<2)return;
  MqlRates rt[];ArraySetAsSeries(rt,true);
  if(CopyRates(_Symbol,PERIOD_M15,1,5,rt)<5)return;
  double c1=rt[0].close,o1=rt[0].open,c2=rt[1].close,o2=rt[1].open,l1=rt[0].low;
  double av=MathMax(a14[0],0.8);
  double body=MathAbs(c1-o1)+1e-5;
  double lw=MathMin(o1,c1)-l1;
  bool mb=(e9h[0]>e20h[0])&&(e20h[0]>e50h[0])&&(e50h[0]>e200h[0]);
  bool m15b=(e9m[0]>e20m[0]);
  bool ve=(a14[0]>=a50[0]*1.05);
  bool cb=(c1>o1)&&(c2>o2);
  bool sig=mb&&m15b&&ve&&(c1>ubb[0])&&(rsi[0]>58.0)&&(lw>=0.85*body)&&cb;
  if(!sig)return;
  double bal=AccountInfoDouble(ACCOUNT_BALANCE);
  double pm=MathMin(InpAccelCap,1.0+(bal-1000.0)/1000.0*(InpAccelMult-1.0));
  double crp=InpBaseRiskPct*pm;
  double arp=(edd>=InpDDBrakeThreshPct)?(crp*InpDDBrakeRiskMult):crp;
  double ra=bal*arp;
  double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
  double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
  if(ts<=0)ts=0.01;if(tv<=0)tv=1.0;
  double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
  double sld=av*InpStopLossATRMult+0.25;
  double tpd=av*InpTakeProfitATRMult;
  double slp=NormalizeDouble(ask-sld,_Digits);
  double tpp=NormalizeDouble(ask+tpd,_Digits);
  double oll=(sld/ts)*tv; oll=MathAbs(oll);
  if(oll<=0)return;
  double rv=ra/oll;
  double vn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double vx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
  double ls=NormalizeDouble(rv,2);
  if(ls<vn)ls=vn;if(ls>vx)ls=vx;
  trade.Buy(ls,_Symbol,ask,slp,tpp,InpTradeComment);
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

def run():
    print("="*100)
    print("V41: ULTRA AGGRESSIVE SMOOTH DIAGONAL + PYRAMIDING")
    print("="*100)
    cfgs=[
        # (ver, base_risk, accel, dd_brake_thresh, dd_brake_mult, tp, cap, maxpos)
        # Strategy A: Pyramiding MaxPos=2 + moderate risk
        (6201, 0.068, 3.50, 0.080, 0.12, 4.00, 8.0, 2),
        (6202, 0.075, 4.00, 0.090, 0.10, 4.00, 10.0, 2),
        # Strategy B: Single pos but ultra-high risk+accel (like R1201 but smooth)
        (6203, 0.090, 5.00, 0.120, 0.08, 4.00, 15.0, 1),
        (6204, 0.100, 5.50, 0.140, 0.08, 4.00, 20.0, 1),
        # Strategy C: Very high risk, low accel (every trade big from day 1)
        (6205, 0.120, 1.80, 0.150, 0.10, 4.00, 3.0, 1),
        (6206, 0.140, 1.50, 0.160, 0.10, 4.00, 2.5, 1),
        # Strategy D: Pyramiding + ultra-high risk
        (6207, 0.090, 4.00, 0.100, 0.10, 4.00, 12.0, 2),
        (6208, 0.080, 3.50, 0.100, 0.10, 4.00, 10.0, 2),
        # Strategy E: No DD brake (thresh=19%)
        (6209, 0.070, 4.00, 0.190, 0.10, 4.00, 10.0, 1),
        (6210, 0.080, 5.00, 0.190, 0.08, 4.00, 15.0, 1),
    ]
    best=None
    for cfg in cfgs:
        ver,br,am,dbt,dbm,tp,cap,mp=cfg
        print(f"\n--- R{ver}: Risk={br*100:.1f}% Accel={am:.1f}x Cap={cap:.0f} DDBrake={dbt*100:.0f}%/{dbm:.2f}x TP={tp}x MaxPos={mp} ---")
        kill_terminal()
        mf=os.path.join(CLEAN_ROOM,f"AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5")
        ini=os.path.join(DATA_DIR,f"gen_r{ver}.ini")
        rp=os.path.join(DATA_DIR,"MQL5","Experts","AlphaLab",f"r{ver}_gold_exec_report.htm")
        with open(mf,'w',encoding='utf-8') as f: f.write(gen(ver,br,am,dbt,dbm,tp,cap,mp))
        subprocess.run([METAEDITOR_EXE,f"/compile:{mf}",f"/log:{mf.replace('.mq5','.log')}"],capture_output=True)
        ex5=mf.replace('.mq5','.ex5')
        if not os.path.exists(ex5): print("  COMPILE FAIL"); continue
        for root in TERMINAL_ROOTS:
            d=os.path.join(root,"MQL5","Experts","AlphaLab","CleanRoom")
            os.makedirs(d,exist_ok=True)
            try: shutil.copy2(ex5,os.path.join(d,os.path.basename(ex5)))
            except: pass
        with open(ini,'w',encoding='utf-8') as f:
            f.write(f"[Tester]\nExpert=AlphaLab\\\\CleanRoom\\\\AlphaLabR{ver}_SmoothDiagonalMasterEA.ex5\nSymbol=GOLD\nPeriod=M15\nDeposit=1000\nCurrency=USD\nLeverage=1:500\nModel=4\nExecutionMode=0\nOptimization=0\nFromDate=2022.05.01\nToDate=2026.07.27\nReport=MQL5\\\\Experts\\\\AlphaLab\\\\r{ver}_gold_exec_report\nReplaceReport=1\nShutdownTerminal=1\n")
        print(f"  MT5 Model=4...")
        subprocess.run([TERMINAL_EXE,f"/config:{ini}"],capture_output=True)
        res=parse(rp)
        if not res: print("  PARSE FAIL"); continue
        ok=res['pnl']>4000 and res['pf']>=1.50 and res['dd']<=20.00
        print(f"  PnL=${res['pnl']:.2f} PF={res['pf']:.2f} DD={res['dd']:.2f}% Trades={res['trades']} [{'PASS' if ok else 'FAIL'}]")
        if ok: best=(ver,res); break
    if best: print(f"\nWINNER: R{best[0]} PnL=${best[1]['pnl']:.2f}")
    else: print("\nNo winner.")

if __name__=='__main__': run()
