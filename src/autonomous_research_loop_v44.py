"""
V44: FINAL VARIANTS — EMA55, R1201 Verify, Bollinger Bounce Pullback
=====================================================================
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

def gen_7cond_ema55(ver, br, am, cap, dbt, dbm, tp, ema_mid):
    """7-condition BUY signal with configurable middle EMA (50 or 55)"""
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
input double InpMaxDrawdownLimit=0.200;
input ulong  InpMagicNumber=202600000+{ver};
input string InpTradeComment="ALAB_R{ver}";
CTrade trade; datetime lastBarTime; double peakEquity; bool isHalted;
int h_e9h,h_e20h,h_eMIDh,h_e200h,h_e9m,h_e20m,h_rsi,h_a14,h_a50,h_bb;
int OnInit(){{
  if(!MQLInfoInteger(MQL_TESTER))return(INIT_FAILED);
  trade.SetExpertMagicNumber(InpMagicNumber); lastBarTime=0;
  peakEquity=AccountInfoDouble(ACCOUNT_EQUITY); isHalted=false;
  h_e9h=iMA(_Symbol,PERIOD_H1,9,0,MODE_EMA,PRICE_CLOSE);
  h_e20h=iMA(_Symbol,PERIOD_H1,20,0,MODE_EMA,PRICE_CLOSE);
  h_eMIDh=iMA(_Symbol,PERIOD_H1,{ema_mid},0,MODE_EMA,PRICE_CLOSE);
  h_e200h=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);
  h_e9m=iMA(_Symbol,PERIOD_M15,9,0,MODE_EMA,PRICE_CLOSE);
  h_e20m=iMA(_Symbol,PERIOD_M15,20,0,MODE_EMA,PRICE_CLOSE);
  h_rsi=iRSI(_Symbol,PERIOD_M15,14,PRICE_CLOSE);
  h_a14=iATR(_Symbol,PERIOD_M15,14);h_a50=iATR(_Symbol,PERIOD_M15,50);
  h_bb=iBands(_Symbol,PERIOD_M15,20,0,2.0,PRICE_CLOSE);
  return(INIT_SUCCEEDED);
}}
void OnDeinit(const int r){{
  IndicatorRelease(h_e9h);IndicatorRelease(h_e20h);IndicatorRelease(h_eMIDh);
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
  if(CountPos()>0)return;
  datetime bt=iTime(_Symbol,PERIOD_M15,0);
  if(bt==lastBarTime)return; lastBarTime=bt;
  double e9h[],e20h[],eMh[],e200h[];
  ArraySetAsSeries(e9h,true);ArraySetAsSeries(e20h,true);
  ArraySetAsSeries(eMh,true);ArraySetAsSeries(e200h,true);
  if(CopyBuffer(h_e9h,0,1,2,e9h)<2)return;
  if(CopyBuffer(h_e20h,0,1,2,e20h)<2)return;
  if(CopyBuffer(h_eMIDh,0,1,2,eMh)<2)return;
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
  bool mb=(e9h[0]>e20h[0])&&(e20h[0]>eMh[0])&&(eMh[0]>e200h[0]);
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
  double oll=(sld/ts)*tv;oll=MathAbs(oll);if(oll<=0)return;
  double rv=ra/oll;
  double vn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
  double vx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
  double ls=NormalizeDouble(rv,2);if(ls<vn)ls=vn;if(ls>vx)ls=vx;
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

def make_ini(ver, period="M15"):
    lines = ["[Tester]",
        f"Expert=AlphaLab\\CleanRoom\\AlphaLabR{ver}_SmoothDiagonalMasterEA.ex5",
        "Symbol=GOLD",f"Period={period}","Deposit=1000","Currency=USD",
        "Leverage=1:500","Model=4","ExecutionMode=0","Optimization=0",
        "FromDate=2022.05.01","ToDate=2026.07.27",
        f"Report=MQL5\\Experts\\AlphaLab\\r{ver}_gold_exec_report",
        "ReplaceReport=1","ShutdownTerminal=1"]
    return "\n".join(lines)+"\n"

def run():
    print("="*100)
    print("V44: EMA55 VARIANT + R1201 ACCEL PATTERN + PARAMETER FINE-TUNING")
    print("="*100)

    # Test matrix:
    # (ver, br, am, cap, dbt, dbm, tp, ema_mid, label)
    cfgs = [
        # Group 1: EMA55 (R1201 used EMA55, CP100K used EMA50)
        (6601, 0.068, 3.50, 8.0, 0.080, 0.12, 4.00, 55, "EMA55 R6101params"),
        # Group 2: R1201 2-stage accel pattern (smooth version)
        (6602, 0.078, 5.50, 25.0, 0.045, 0.10, 4.00, 55, "EMA55 R1201-like"),
        (6603, 0.078, 5.50, 25.0, 0.045, 0.10, 4.00, 50, "EMA50 R1201-like"),
        # Group 3: Very conservative base + ultra-high accel
        (6604, 0.035, 5.00, 15.0, 0.120, 0.10, 4.00, 50, "Low3.5% HighAccel5x"),
        (6605, 0.040, 6.00, 20.0, 0.120, 0.10, 4.00, 50, "Low4.0% HighAccel6x"),
        (6606, 0.030, 7.00, 25.0, 0.150, 0.08, 4.00, 50, "Low3.0% HighAccel7x"),
        # Group 4: Fine-tune around R6101 sweet spot
        (6607, 0.065, 3.80, 9.0, 0.075, 0.11, 4.00, 50, "R6101 variant A"),
        (6608, 0.070, 3.20, 7.5, 0.085, 0.13, 4.00, 50, "R6101 variant B"),
        (6609, 0.068, 3.50, 8.0, 0.080, 0.12, 4.50, 50, "R6101 TP=4.5"),
        (6610, 0.068, 3.50, 8.0, 0.070, 0.15, 4.00, 50, "R6101 DDBrake=7%"),
    ]
    best = None
    for cfg in cfgs:
        ver,br,am,cap,dbt,dbm,tp,ema,label = cfg
        print(f"\n--- R{ver}: {label} Risk={br*100:.1f}% Accel={am:.1f}x Cap={cap:.0f} ---")
        kill_terminal()
        mf=os.path.join(CLEAN_ROOM,f"AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5")
        ini_path=os.path.join(DATA_DIR,f"gen_r{ver}.ini")
        rp=os.path.join(DATA_DIR,"MQL5","Experts","AlphaLab",f"r{ver}_gold_exec_report.htm")
        code=gen_7cond_ema55(ver,br,am,cap,dbt,dbm,tp,ema)
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
        star = '*** PASS ***' if ok else ('** BEST **' if res['pnl']>1700 else 'FAIL')
        print(f"  PnL=${res['pnl']:.2f} PF={res['pf']:.2f} DD={res['dd']:.2f}% Trades={res['trades']} [{star}]")
        if ok: best=(ver,res); break
    if best: print(f"\nWINNER: R{best[0]} PnL=${best[1]['pnl']:.2f}")
    else: print("\nNo $4K winner. Reporting best results.")

if __name__=='__main__': run()
