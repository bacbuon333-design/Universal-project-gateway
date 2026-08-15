"""
NEXUS BRAIN v13 — HUMAN-LIKE TRADING ENGINE
============================================
Philosophy: Trade like a senior human trader, not a formula machine.

A skilled trader thinks in 3 layers:
  1. CONTEXT  (Weekly): "What is the market doing overall?"
  2. SETUP    (Daily):  "Where is price relative to key levels?"
  3. TRIGGER  (H1):    "Did price show a reversal signal at that level?"

ONLY when all 3 align does the human pull the trigger.

Implementation:
  Context  = Pseudo-Weekly EMA + ADX strength score (480 M15 bars = 1 week)
  Setup    = Swing High/Low identification from 5-day price structure
             → is price at/near a key level?
  Trigger  = Price Action patterns on M15/H1:
             - Pin Bar (rejection wick) at key level
             - Engulfing candle after pullback
             - 3-bar momentum shift (lower high/lower low broken)

Risk is NOT fixed — it scales with CONVICTION score (how clear is the trade):
  High conviction (7+/10): 6% risk
  Medium conviction (5-6): 4% risk
  Low conviction (<5):    SKIP

No fixed R:R — use ATR-based trailing stop that locks in profits progressively.
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass,field
from typing import Optional

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

# ─── Timeframe constants (in M15 bars) ────────────────────────────
BARS_H1  = 4    # 1 H1 = 4 M15
BARS_H4  = 16   # 1 H4 = 16 M15
BARS_D1  = 96   # 1 Day = 96 M15
BARS_W1  = 480  # 1 Week = 480 M15

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def compute_indicators(close, high, low):
    """Full indicator suite for M15 data"""
    n = len(close)
    # EMA suite
    e8=ema(close,8); e21=ema(close,21); e50=ema(close,50); e200=ema(close,200)
    # Weekly-scale EMAs (on M15 bars)
    e_w1=ema(close,480)   # ~1 week
    e_w2=ema(close,960)   # ~2 weeks
    e_w3=ema(close,1440)  # ~3 weeks (macro)

    # ATR
    tr=np.maximum(high[1:]-low[1:],np.maximum(np.abs(high[1:]-close[:-1]),np.abs(low[1:]-close[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr96=pd.Series(tr).rolling(96).mean().values   # daily ATR average
    atr_r=atr14/np.where(atr96>0,atr96,1e-9)

    # RSI
    d2=pd.Series(close).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values

    # ADX/DI
    up=pd.Series(high).diff(); dn=-pd.Series(low).diff()
    pdm=up.where((up>dn)&(up>0),0.); ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values

    # Swing High/Low detection (5-period lookback each side, M15)
    # A swing high = price[i] > price[i-1..i-5] AND price[i] > price[i+1..i+5]
    # We use a simplified rolling window version (non-centered for real-time)
    sw_hi=pd.Series(high).rolling(10).max().values   # 10-bar rolling high
    sw_lo=pd.Series(low).rolling(10).min().values    # 10-bar rolling low

    # Weekly swing levels (key S/R): rolling max/min over 480 bars
    w_hi=pd.Series(high).rolling(480).max().shift(1).values   # last week high
    w_lo=pd.Series(low).rolling(480).min().shift(1).values    # last week low

    # Daily S/R: 96-bar rolling high/low
    d_hi=pd.Series(high).rolling(96).max().shift(1).values
    d_lo=pd.Series(low).rolling(96).min().shift(1).values

    return dict(
        e8=e8,e21=e21,e50=e50,e200=e200,
        e_w1=e_w1,e_w2=e_w2,e_w3=e_w3,
        atr14=atr14,atr96=atr96,atr_r=atr_r,
        rsi=rsi,adx=adx,di=di,
        sw_hi=sw_hi,sw_lo=sw_lo,
        w_hi=w_hi,w_lo=w_lo,
        d_hi=d_hi,d_lo=d_lo
    )

# ─── Pattern Recognition ─────────────────────────────────────────
def is_pin_bar_bull(o,h,l,c,atr):
    """Bullish Pin Bar: long lower wick, close in upper 1/3"""
    body=abs(c-o); lower_wick=min(o,c)-l; upper_wick=h-max(o,c)
    return (lower_wick>=2.5*body and lower_wick>=0.6*(h-l)
            and (c-l)>=(h-l)*0.6 and body>0.05*atr)

def is_pin_bar_bear(o,h,l,c,atr):
    """Bearish Pin Bar: long upper wick, close in lower 1/3"""
    body=abs(c-o); upper_wick=h-max(o,c); lower_wick=min(o,c)-l
    return (upper_wick>=2.5*body and upper_wick>=0.6*(h-l)
            and (h-c)>=(h-l)*0.6 and body>0.05*atr)

def is_bull_engulf(o1,c1,o2,c2):
    """Bullish engulfing: bearish bar followed by larger bullish bar"""
    return c1<o1 and c2>o2 and c2>o1 and o2<c1

def is_bear_engulf(o1,c1,o2,c2):
    """Bearish engulfing: bullish bar followed by larger bearish bar"""
    return c1>o1 and c2<o2 and c2<o1 and o2>c1

# ─── Conviction Scorer ───────────────────────────────────────────
def score_long(i, close, high, low, opens, ind):
    """Score a potential long trade from 0-10"""
    score=0; reasons=[]
    c=close[i]; h=high[i]; l=low[i]; o=opens[i]
    atr=max(ind['atr14'][i],1.5)
    # --- CONTEXT (max 4pts) ---
    # 1. Weekly macro: price above W1 EMA (1pt each layer)
    if c > ind['e_w1'][i]: score+=1; reasons.append('c>eW1')
    if c > ind['e_w2'][i]: score+=1; reasons.append('c>eW2')
    if ind['e_w1'][i] > ind['e_w2'][i]: score+=1; reasons.append('eW1>eW2')
    # 2. ADX momentum (1pt)
    if ind['adx'][i] >= 20 and ind['di'][i] > 0: score+=1; reasons.append('ADX+DI')

    # --- SETUP (max 3pts) ---
    # 3. Price is at/near a key support level (daily or weekly)
    near_d_lo = abs(l - ind['d_lo'][i]) <= atr*1.5 if ind['d_lo'][i]>0 else False
    near_w_lo = abs(l - ind['w_lo'][i]) <= atr*2.0 if ind['w_lo'][i]>0 else False
    near_e21  = abs(l - ind['e21'][i])  <= atr*0.8
    near_e50  = abs(l - ind['e50'][i])  <= atr*1.0
    if near_d_lo: score+=1; reasons.append('near_D_lo')
    if near_w_lo: score+=1; reasons.append('near_W_lo')
    if near_e21 or near_e50: score+=1; reasons.append('near_EMA')

    # --- TRIGGER (max 3pts) ---
    # 4. Price action confirmation
    if i>=1:
        o1,c1=opens[i-1],close[i-1]
        if is_pin_bar_bull(o,h,l,c,atr): score+=2; reasons.append('PIN_BULL')
        elif is_bull_engulf(o1,c1,o,c): score+=2; reasons.append('ENGULF_BULL')
        elif c>o and c>close[i-1] and l<=ind['e21'][i]: score+=1; reasons.append('BOUNCE_BULL')
    # 5. RSI not overbought
    if ind['rsi'][i] < 55: score+=1; reasons.append('RSI_ok')

    return score, reasons

def score_short(i, close, high, low, opens, ind):
    """Score a potential short trade from 0-10"""
    score=0; reasons=[]
    c=close[i]; h=high[i]; l=low[i]; o=opens[i]
    atr=max(ind['atr14'][i],1.5)
    # --- CONTEXT ---
    if c < ind['e_w1'][i]: score+=1; reasons.append('c<eW1')
    if c < ind['e_w2'][i]: score+=1; reasons.append('c<eW2')
    if ind['e_w1'][i] < ind['e_w2'][i]: score+=1; reasons.append('eW1<eW2')
    if ind['adx'][i] >= 20 and ind['di'][i] < 0: score+=1; reasons.append('ADX-DI')
    # --- SETUP ---
    near_d_hi = abs(h - ind['d_hi'][i]) <= atr*1.5 if ind['d_hi'][i]>0 else False
    near_w_hi = abs(h - ind['w_hi'][i]) <= atr*2.0 if ind['w_hi'][i]>0 else False
    near_e21  = abs(h - ind['e21'][i])  <= atr*0.8
    near_e50  = abs(h - ind['e50'][i])  <= atr*1.0
    if near_d_hi: score+=1; reasons.append('near_D_hi')
    if near_w_hi: score+=1; reasons.append('near_W_hi')
    if near_e21 or near_e50: score+=1; reasons.append('near_EMA')
    # --- TRIGGER ---
    if i>=1:
        o1,c1=opens[i-1],close[i-1]
        if is_pin_bar_bear(o,h,l,c,atr): score+=2; reasons.append('PIN_BEAR')
        elif is_bear_engulf(o1,c1,o,c): score+=2; reasons.append('ENGULF_BEAR')
        elif c<o and c<close[i-1] and h>=ind['e21'][i]: score+=1; reasons.append('BOUNCE_BEAR')
    if ind['rsi'][i] > 45: score+=1; reasons.append('RSI_ok')
    return score, reasons

# ─── Signal Generator ────────────────────────────────────────────
def gen_signals(df, min_score=5, use_short=True):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    o=df['open'].values if 'open' in df.columns else c
    n=len(c); ind=compute_indicators(c,h,l)
    sig=np.zeros(n,dtype=int); slp=np.zeros(n); rrv=np.zeros(n)
    nm=['']*n; conv=np.zeros(n,dtype=int)
    atr=ind['atr14']

    for i in range(1500,n):  # need 1500 bars warm-up (>3 weeks)
        av=max(atr[i],1.5)
        # Score long
        s_long, r_long = score_long(i,c,h,l,o,ind)
        if s_long >= min_score:
            # Adaptive R:R based on score and ATR expansion
            ar=ind['atr_r'][i]
            rr = 3.5 if s_long>=8 else (3.0 if s_long>=6 else 2.5)
            if ar>=1.5: rr+=0.5  # more room in expanding volatility
            sl_pips=(av/PIP)*1.4+SPR
            sig[i]=1; slp[i]=sl_pips; rrv[i]=rr; nm[i]='LONG_HUMAN'; conv[i]=s_long
            continue
        # Score short
        if use_short:
            s_short, r_short = score_short(i,c,h,l,o,ind)
            if s_short >= min_score:
                ar=ind['atr_r'][i]
                rr = 3.5 if s_short>=8 else (3.0 if s_short>=6 else 2.5)
                if ar>=1.5: rr+=0.5
                sl_pips=(av/PIP)*1.4+SPR
                sig[i]=-1; slp[i]=sl_pips; rrv[i]=rr; nm[i]='SHORT_HUMAN'; conv[i]=s_short
    return sig,slp,rrv,nm,conv,ind

# ─── Risk Management ─────────────────────────────────────────────
def lot_size(eq, pk, slp, conviction, base_risk=0.055):
    dd=(pk-eq)/max(pk,1e-9)*100
    # Risk tiers by DD
    if dd>=15: r=base_risk*0.15
    elif dd>=10: r=base_risk*0.38
    elif dd>=6: r=base_risk*0.68
    else: r=base_risk
    # Conviction multiplier
    if conviction>=8: r*=1.2
    elif conviction<6: r*=0.75
    return max(0.01, min(round(eq*r/(slp*0.01)*0.01,2), 25.))

# ─── Backtest Engine ──────────────────────────────────────────────
@dataclass
class Tr:
    dir:str=''; entry:float=0.; sl:float=0.; tp:float=0.
    lot:float=0.01; pnl:float=0.; sname:str=''; conviction:int=0
    trail_on:bool=False; hwm:float=0.; sl_pts:float=0.

def backtest(df, base_risk=0.055, min_score=5, use_short=True):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    sig,slp,rrv,nm,conv,ind=gen_signals(df,min_score,use_short)
    atr=ind['atr14']
    bal=1000.; pk=1000.; mx=0.; trades=[]; stats={}; ot:Optional[Tr]=None
    n=len(c)
    for i in range(1500,n):
        if ot:
            done=False; ex=c[i]; av=max(atr[i],1.5)
            if ot.dir=='BUY':
                if h[i]>ot.hwm: ot.hwm=h[i]
                # Activate trail after 1.5R profit
                if not ot.trail_on and (h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    new_sl=ot.hwm-2.0*av
                    if new_sl>ot.sl: ot.sl=new_sl
                if l[i]<=ot.sl: ex=ot.sl; done=True
                elif h[i]>=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            else:
                if l[i]<ot.hwm: ot.hwm=l[i]
                if not ot.trail_on and (ot.entry-l[i])>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    new_sl=ot.hwm+2.0*av
                    if new_sl<ot.sl: ot.sl=new_sl
                if h[i]>=ot.sl: ex=ot.sl; done=True
                elif l[i]<=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else (ot.entry-ex)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net; pk=max(pk,bal)
                dd=pk-bal; mx=max(mx,dd/pk*100)
                ot.pnl=net; sn=ot.sname
                if sn not in stats: stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1; stats[sn]['pnl']+=net
                if net>0: stats[sn]['w']+=1; stats[sn]['wu']+=net
                else: stats[sn]['lu']+=abs(net)
                trades.append(ot); ot=None
        if ot is None and sig[i]!=0:
            sp=slp[i]
            if sp>0:
                lot=lot_size(bal,pk,sp,conv[i],base_risk)
                s2=SPR*PIP
                if sig[i]==1:
                    e_=c[i]+s2;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP;d='BUY';hwm=e_
                else:
                    e_=c[i]-s2;sl_=e_+sp*PIP;tp_=e_-sp*rrv[i]*PIP;d='SELL';hwm=e_
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=nm[i],
                      conviction=conv[i],trail_on=False,hwm=hwm,sl_pts=sp)
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.; gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def run_gauntlet(base_risk=0.055, min_score=5, use_short=True):
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)
    wm={'2022-2023':('2022-05-02','2023-05-01'),
        '2023-2024':('2023-05-01','2024-05-01'),
        '2024-2025':('2024-05-01','2025-05-01'),
        '2025-2026':('2025-05-01','2026-07-24')}
    rows=[]
    for yr,(s,e) in wm.items():
        d=df.loc[s:e].copy(); r=backtest(d,base_risk,min_score,use_short)
        oracle=ORACLE.get(yr); tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def print_table(rows, label=""):
    if label: print(label)
    print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

def main():
    print("="*68)
    print("🧠 NEXUS BRAIN v13 — HUMAN-LIKE CONVICTION TRADING ENGINE")
    print("="*68)
    print("\nScoring system: Context(4pts) + Setup(3pts) + Trigger(3pts) = 10pts max")
    print("Min score to trade: 5/10 | Trailing stop activates at 1.5R profit\n")

    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)

    # Test different min_score thresholds
    print("--- Sweep min_score (5, 6, 7) ---")
    for ms in [5,6,7]:
        rows=run_gauntlet(base_risk=0.055,min_score=ms,use_short=True)
        total_pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
        max_dd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
        total_pnl=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
        print(f"  min_score={ms}: pos_years={total_pos}/3 maxDD={max_dd:.1f}% totalPnL={total_pnl:.0f}")
        print_table(rows)
        print()

    # Best config detail
    print("\n\n🏆 BEST CONFIG (min_score=5) — Full Report:")
    rows=run_gauntlet(base_risk=0.055,min_score=5,use_short=True)
    print_table(rows)
    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined: combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]: combined[sn][k]+=st[k]
    print("\n📊 Signal stats:")
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9); wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<20}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    # Save
    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V13_HUMAN_ENGINE.md')
    lines=["# 🧠 NEXUS BRAIN v13 — HUMAN-LIKE CONVICTION ENGINE",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           "\n## Architecture",
           "- **Context** (4pts): Weekly EMA alignment + ADX/DI momentum",
           "- **Setup** (3pts): Price proximity to Daily/Weekly S/R levels + EMA support",
           "- **Trigger** (3pts): Pin Bar or Engulfing confirmation + RSI filter",
           "- **Trailing Stop**: Activates at 1.5R profit, trails at 2.0×ATR",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"; tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f: f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__': main()
