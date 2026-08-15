"""
NEXUS BRAIN v3 — VERIFIED SIGNAL ARCHITECTURE
Core insight from data analysis:
- 2022-2023: Only 49.9% bars above EMA200, nearly 50/50 — standard pullback long fails
- 2023-2024: 53.1% above, gradual uptrend — but acceleration only in Oct/Nov/Mar/Apr
- 2024-2025: 60.9% above, strong bull — pullback strategy works best

Solution: Use HIGHER timeframe trend (4H/Daily equivalent using 96-bar / 386-bar EMA)
Then within that trend, pick only DEEP pullbacks (RSI < 40) or Strong Breakouts.

Oracle targets (20%):
  2022-2023: +$1,526 from $1,000
  2023-2024: +$1,341 from $1,000
  2024-2025: +$2,808 from $1,000
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np, pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Optional, Dict

PIP=0.01; PTVAL=0.01; COMM=0.07; SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

def ema(arr,s): return pd.Series(arr).ewm(span=s,adjust=False).mean().values

def make_ind(c,h,l):
    # Approximate 4H = 16 M15 bars; Daily = 96 M15; Weekly = 480
    e8=ema(c,8); e21=ema(c,21); e50=ema(c,50); e200=ema(c,200)
    e96=ema(c,96)    # ~daily
    e384=ema(c,384)  # ~weekly
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr50=pd.Series(tr).rolling(50).mean().values
    d2=pd.Series(c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    lss=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/lss)).values
    up=pd.Series(h).diff(); dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.); ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di_diff=(pdi-ndi).values
    # Keltner channel for breakout
    kc_mid=ema(c,20); kc_upper=kc_mid+2*atr14; kc_lower=kc_mid-2*atr14
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,e96=e96,e384=e384,
                atr14=atr14,atr50=atr50,rsi=rsi,adx=adx,di_diff=di_diff,
                kc_upper=kc_upper,kc_lower=kc_lower)

def gen_signals(df):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    n=len(c); ind=make_ind(c,h,l)
    e8=ind['e8']; e21=ind['e21']; e50=ind['e50']
    e96=ind['e96']; e200=ind['e200']; e384=ind['e384']
    atr=ind['atr14']; rsi=ind['rsi']; adx=ind['adx']
    di=ind['di_diff']
    sig=np.zeros(n,dtype=int); slp=np.zeros(n); rrv=np.zeros(n); nm=['']*n

    for i in range(400,n):
        cv=c[i]; av=max(atr[i],1.5); rv=rsi[i]; dv=adx[i]; div=di[i]

        # HTF bias: daily and weekly EMAs
        htf_bull = e96[i] > e384[i] and cv > e96[i]   # price above daily above weekly
        htf_bear = e96[i] < e384[i] and cv < e96[i]

        # ATF momentum
        mid_bull = cv > e200[i] and e50[i] > e200[i] and div > 0
        mid_bear = cv < e200[i] and e50[i] < e200[i] and div < 0

        # ── ENTRY 1: DEEP VALUE PULLBACK (best signal from IS year) ──
        # HTF bullish + MTF bullish + deep RSI dip to EMA8 (strong demand)
        # Key: low MUST touch EMA8 (body or wick), close ABOVE it = immediate bounce
        if htf_bull and mid_bull and dv >= 18:
            if l[i] <= e8[i] and cv > e8[i] and rv <= 42:
                rr_val = 4.0 if dv >= 28 else 3.5
                sig[i]=1; slp[i]=(av/PIP)*1.3+SPR; rrv[i]=rr_val
                nm[i]='DEEP_PULLBACK_BUY'; continue

        # ── ENTRY 2: KELTNER BREAKOUT (trend expansion signal) ──
        # Price breaks above KC upper with ADX rising + RSI 50-65 (not overbought)
        if htf_bull and mid_bull and dv >= 22 and div > 8:
            if cv > ind['kc_upper'][i] and 48 <= rv <= 68 and c[i-1] < ind['kc_upper'][i-1]:
                sig[i]=1; slp[i]=(av/PIP)*1.5+SPR*1.2; rrv[i]=3.8
                nm[i]='KC_BREAKOUT_BUY'; continue

        # ── ENTRY 3: EMA21 SUPPORT BOUNCE (medium-term bull signal) ──
        # HTF still bullish, price pulls deeper to EMA21, RSI < 38 (oversold dip)
        if htf_bull and cv > e200[i] and e50[i] > e200[i]:
            if l[i] <= e21[i] and cv > e21[i] and rv <= 38 and dv >= 15:
                sig[i]=1; slp[i]=(av/PIP)*1.5+SPR*1.2; rrv[i]=3.5
                nm[i]='EMA21_BOUNCE_BUY'; continue

    return sig,slp,rrv,nm

def lot_size(eq,pk,slp,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=16: r=risk*0.2
    elif dd>=11: r=risk*0.4
    elif dd>=7: r=risk*0.65
    else: r=risk
    return max(0.01,min(round(eq*r/(slp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str='';entry:float=0.;sl:float=0.;tp:float=0.
    lot:float=0.01;pnl:float=0.;sname:str=''

def backtest(df, risk=0.055):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    sig,slp,rrv,nm = gen_signals(df)
    bal=1000.;pk=1000.;mx_dd=0.;mx_ddp=0.
    trades=[];stats={};ot=None
    for i in range(400,len(c)):
        if ot:
            done=False;ex=c[i];rsn=''
            if ot.dir=='BUY':
                if l[i]<=ot.sl: ex=ot.sl;rsn='SL';done=True
                elif h[i]>=ot.tp: ex=ot.tp;rsn='TP';done=True
            if done:
                pts=(ex-ot.entry)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net
                if bal>pk: pk=bal
                dd=pk-bal
                if dd>mx_dd: mx_dd=dd;mx_ddp=dd/pk*100
                ot.pnl=net
                sn=ot.sname
                if sn not in stats: stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1;stats[sn]['pnl']+=net
                if net>0: stats[sn]['w']+=1;stats[sn]['wu']+=net
                else: stats[sn]['lu']+=abs(net)
                trades.append(ot);ot=None
        if ot is None and sig[i]==1:
            sp=slp[i]
            if sp>0:
                lot=lot_size(bal,pk,sp,risk)
                e=c[i]+SPR*PIP
                ot=Tr(dir='BUY',entry=e,sl=e-sp*PIP,tp=e+sp*rrv[i]*PIP,lot=lot,sname=nm[i])
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    ret=pd.Series(pnls)
    sh=float(ret.mean()/ret.std()*np.sqrt(252*24)) if len(ret)>1 and ret.std()>0 else 0.
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx_ddp,sharpe=sh,stats=stats)

def main():
    print("="*65)
    print("🧠 NEXUS BRAIN v3 — MULTI-YEAR WAVE CAPTURE GAUNTLET")
    print("="*65)
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    windows={'2022-2023':('2022-05-02','2023-05-01'),
             '2023-2024':('2023-05-01','2024-05-01'),
             '2024-2025':('2024-05-01','2025-05-01'),
             '2025-2026':('2025-05-01','2026-07-24')}
    RISK=0.055
    rows=[]
    for yr,(s,e) in windows.items():
        d=df.loc[s:e].copy()
        r=backtest(d,RISK)
        oracle=ORACLE.get(yr)
        tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3}")

    print("\n📊 Signal-level stats (all years combined):")
    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined: combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]: combined[sn][k]+=st[k]
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9); wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<28}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    # Save
    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V3_MULTIYEAR.md')
    lines=["# 🧠 NEXUS BRAIN v3 — MULTI-YEAR GAUNTLET",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           f"**Risk**: {RISK*100}%/trade | Spread: {SPR}pts | Comm: ${COMM}/0.01lot",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% Target | Verdict |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f: f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__': main()
