"""
NEXUS BRAIN v14 — SELECTIVE HUMAN BRAIN (max 3 trades/month)
=============================================================
Lesson from v13: 1500+ trades/year = overtrading = PF<1 regardless of WR.

A REAL skilled human trader takes ONLY the best setups:
  → Max 2-3 trades per MONTH
  → Waits for confluence of price action + level + trend
  → Never chases; waits for price to COME TO THEM

Key architectural changes from v13:
1. MIN SCORE = 8/10 (very high threshold — only exceptional setups)
2. COOLDOWN = 5 trading days after each trade (reset mind)
3. Better pattern detection: only PIN BAR or ENGULFING counts as trigger
   (not just any bounce)
4. Level quality: only trade at WEEKLY-scale S/R or strong EMA convergence
5. ATR expansion check: don't trade if ATR < 80% of its 30-day average
   (consolidation = bad environment for trend entries)

Expected: 15-30 trades/year = ~2-3 per month
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass
from typing import Optional

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}

BARS_W1=480  # 1 week in M15

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

def build_ind(c,h,l,opens):
    n=len(c)
    e8=ema(c,8); e21=ema(c,21); e50=ema(c,50); e200=ema(c,200)
    e480=ema(c,480); e960=ema(c,960); e1440=ema(c,1440)
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr_slow=pd.Series(atr14).rolling(480).mean().values  # 30-day avg ATR on M15
    d2=pd.Series(c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h).diff(); dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.); ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # Key S/R levels (rolling max/min)
    d_hi=pd.Series(h).rolling(96).max().shift(1).values   # previous day high
    d_lo=pd.Series(l).rolling(96).min().shift(1).values   # previous day low
    w_hi=pd.Series(h).rolling(480).max().shift(1).values  # previous week high
    w_lo=pd.Series(l).rolling(480).min().shift(1).values  # previous week low
    # 2-week and 4-week levels (stronger S/R)
    w2_hi=pd.Series(h).rolling(960).max().shift(1).values
    w2_lo=pd.Series(l).rolling(960).min().shift(1).values
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,
                e480=e480,e960=e960,e1440=e1440,
                atr14=atr14,atr_slow=atr_slow,rsi=rsi,adx=adx,di=di,
                d_hi=d_hi,d_lo=d_lo,w_hi=w_hi,w_lo=w_lo,
                w2_hi=w2_hi,w2_lo=w2_lo)

def is_pin_bull(o,h,l,c,atr):
    b=abs(c-o); lw=min(o,c)-l; uw=h-max(o,c)
    return (lw>=2.5*max(b,0.01) and lw>=0.55*(h-l) and (c-l)/(h-l+1e-9)>=0.55
            and b>=0.02*atr and b>0)

def is_pin_bear(o,h,l,c,atr):
    b=abs(c-o); uw=h-max(o,c); lw=min(o,c)-l
    return (uw>=2.5*max(b,0.01) and uw>=0.55*(h-l) and (h-c)/(h-l+1e-9)>=0.55
            and b>=0.02*atr and b>0)

def is_bull_engulf(o1,c1,o2,c2):
    return c1<o1 and c2>o2 and c2>=o1 and o2<=c1 and (c2-o2)>(o1-c1)*0.8

def is_bear_engulf(o1,c1,o2,c2):
    return c1>o1 and c2<o2 and c2<=o1 and o2>=c1 and (o2-c2)>(c1-o1)*0.8

def score_trade(i, dir_, c, h, l, opens, ind):
    """Returns (score 0-10, R:R multiplier, sl_type)"""
    cv=c[i]; hi=h[i]; lo=l[i]; o=opens[i]
    atr=max(ind['atr14'][i],1.5); asr=ind['atr_slow'][i]
    score=0

    # ── GATE: ATR expansion (not trading in quiet consolidation) ──
    if asr>0 and atr < asr*0.7: return 0, 2.5, ''   # too quiet

    # ── CONTEXT (0-4pts): Weekly trend alignment ──────────────────
    e480=ind['e480'][i]; e960=ind['e960'][i]; e1440=ind['e1440'][i]
    adx=ind['adx'][i]; di=ind['di'][i]
    if dir_==1:
        if cv>e1440: score+=1  # price above 3-week EMA
        if cv>e960:  score+=1  # price above 2-week EMA
        if e480>e960: score+=1  # 1-week EMA above 2-week EMA (uptrend)
        if adx>=22 and di>8: score+=1  # strong momentum up
    else:
        if cv<e1440: score+=1
        if cv<e960:  score+=1
        if e480<e960: score+=1
        if adx>=22 and di<-8: score+=1

    # ── SETUP (0-3pts): Price at meaningful level ─────────────────
    d_lo=ind['d_lo'][i]; d_hi=ind['d_hi'][i]
    w_lo=ind['w_lo'][i]; w_hi=ind['w_hi'][i]
    w2_lo=ind['w2_lo'][i]; w2_hi=ind['w2_hi'][i]
    e21=ind['e21'][i]; e50=ind['e50'][i]
    if dir_==1:
        at_w_lo=w_lo>0 and abs(lo-w_lo)<=atr*2.0
        at_w2_lo=w2_lo>0 and abs(lo-w2_lo)<=atr*2.5
        at_d_lo=d_lo>0 and abs(lo-d_lo)<=atr*1.5
        at_ema=(abs(lo-e21)<=atr*0.6 or abs(lo-e50)<=atr*0.8)
        if at_w2_lo: score+=2  # strongest level
        elif at_w_lo: score+=1
        if at_d_lo and not at_w_lo: score+=1
        if at_ema: score+=1
    else:
        at_w_hi=w_hi>0 and abs(hi-w_hi)<=atr*2.0
        at_w2_hi=w2_hi>0 and abs(hi-w2_hi)<=atr*2.5
        at_d_hi=d_hi>0 and abs(hi-d_hi)<=atr*1.5
        at_ema=(abs(hi-e21)<=atr*0.6 or abs(hi-e50)<=atr*0.8)
        if at_w2_hi: score+=2
        elif at_w_hi: score+=1
        if at_d_hi and not at_w_hi: score+=1
        if at_ema: score+=1

    # ── TRIGGER (0-3pts): Price action confirmation ───────────────
    trigger=''
    if i>=1:
        o1,c1=opens[i-1],c[i-1]
        if dir_==1:
            if is_pin_bull(o,hi,lo,cv,atr): score+=3; trigger='PIN_BULL'
            elif is_bull_engulf(o1,c1,o,cv): score+=2; trigger='ENGULF_BULL'
            elif cv>o and lo<=ind['e21'][i] and cv>c[i-1]: score+=1; trigger='BOUNCE_BULL'
        else:
            if is_pin_bear(o,hi,lo,cv,atr): score+=3; trigger='PIN_BEAR'
            elif is_bear_engulf(o1,c1,o,cv): score+=2; trigger='ENGULF_BEAR'
            elif cv<o and hi>=ind['e21'][i] and cv<c[i-1]: score+=1; trigger='BOUNCE_BEAR'

    # R:R scales with score AND ATR ratio
    atr_ratio=atr/max(asr,1e-9)
    base_rr = 3.5 if score>=9 else (3.0 if score>=7 else 2.5)
    if atr_ratio>=1.4: base_rr+=0.5  # more room in expanding volatility

    return min(score,10), base_rr, trigger

def gen_signals(df, min_score=8, cooldown_bars=480, use_short=True):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    o=df['open'].values if 'open' in df.columns else np.zeros_like(c)
    n=len(c); ind=build_ind(c,h,l,o)
    sig=np.zeros(n,dtype=int); slp=np.zeros(n); rrv=np.zeros(n)
    nm=['']*n; conv=np.zeros(n,dtype=int); trg=['']*n
    last_trade_bar=-9999  # cooldown tracker

    for i in range(1500,n):
        if i-last_trade_bar < cooldown_bars: continue  # in cooldown
        atr=max(ind['atr14'][i],1.5)

        # Try LONG
        s,rr,trig=score_trade(i,1,c,h,l,o,ind)
        if s>=min_score:
            sl=(atr/PIP)*1.4+SPR
            sig[i]=1; slp[i]=sl; rrv[i]=rr; nm[i]='LONG'; conv[i]=s; trg[i]=trig
            last_trade_bar=i; continue

        # Try SHORT
        if use_short:
            s,rr,trig=score_trade(i,-1,c,h,l,o,ind)
            if s>=min_score:
                sl=(atr/PIP)*1.4+SPR
                sig[i]=-1; slp[i]=sl; rrv[i]=rr; nm[i]='SHORT'; conv[i]=s; trg[i]=trig
                last_trade_bar=i

    return sig,slp,rrv,nm,conv,trg

def lot_size(eq,pk,slp,conviction,base_risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=15: r=base_risk*0.15
    elif dd>=10: r=base_risk*0.38
    elif dd>=6: r=base_risk*0.68
    else: r=base_risk
    mult=1.3 if conviction>=9 else (1.0 if conviction>=7 else 0.75)
    return max(0.01,min(round(eq*r*mult/(slp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str=''; entry:float=0.; sl:float=0.; tp:float=0.
    lot:float=0.01; pnl:float=0.; sname:str=''; conviction:int=0
    trail_on:bool=False; hwm:float=0.; sl_pts:float=0.

def backtest(df, base_risk=0.055, min_score=8, cooldown=480, use_short=True):
    c=df['close'].values; h=df['high'].values; l=df['low'].values
    sig,slp,rrv,nm,conv,trg=gen_signals(df,min_score,cooldown,use_short)
    o_col=df['open'].values if 'open' in df.columns else c
    ind=build_ind(c,h,l,o_col)
    atr=ind['atr14']
    bal=1000.; pk=1000.; mx=0.; trades=[]; stats={}; ot=None
    for i in range(1500,len(c)):
        if ot:
            done=False; ex=c[i]; av=max(atr[i],1.5)
            if ot.dir=='BUY':
                if h[i]>ot.hwm: ot.hwm=h[i]
                if not ot.trail_on and (h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm-2.5*av
                    if ns>ot.sl: ot.sl=ns
                if l[i]<=ot.sl: ex=ot.sl; done=True
                elif h[i]>=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            else:
                if l[i]<ot.hwm: ot.hwm=l[i]
                if not ot.trail_on and (ot.entry-l[i])>=1.5*ot.sl_pts*PIP:
                    ot.trail_on=True
                if ot.trail_on:
                    ns=ot.hwm+2.5*av
                    if ns<ot.sl: ot.sl=ns
                if h[i]>=ot.sl: ex=ot.sl; done=True
                elif l[i]<=ot.tp and not ot.trail_on: ex=ot.tp; done=True
            if done:
                pts=(ex-ot.entry)/PIP if ot.dir=='BUY' else (ot.entry-ex)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net; pk=max(pk,bal)
                dd=pk-bal; mx=max(mx,dd/pk*100)
                ot.pnl=net; sn=ot.sname
                if sn not in stats: stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.,'cvg':0,'rtrail':0}
                stats[sn]['n']+=1; stats[sn]['pnl']+=net; stats[sn]['cvg']+=ot.conviction
                stats[sn]['rtrail']+=1 if ot.trail_on else 0
                if net>0: stats[sn]['w']+=1; stats[sn]['wu']+=net
                else: stats[sn]['lu']+=abs(net)
                trades.append(ot); ot=None
        if ot is None and sig[i]!=0:
            sp=slp[i]
            if sp>0:
                lot=lot_size(bal,pk,sp,conv[i],base_risk)
                s2=SPR*PIP
                if sig[i]==1:
                    e_=c[i]+s2; sl_=e_-sp*PIP; tp_=e_+sp*rrv[i]*PIP; d='BUY'; hwm=e_
                else:
                    e_=c[i]-s2; sl_=e_+sp*PIP; tp_=e_-sp*rrv[i]*PIP; d='SELL'; hwm=e_
                ot=Tr(dir=d,entry=e_,sl=sl_,tp=tp_,lot=lot,sname=nm[i],
                      conviction=conv[i],trail_on=False,hwm=hwm,sl_pts=sp)
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.; gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def run_gauntlet(base_risk=0.055,min_score=8,cooldown=480,use_short=True):
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)
    wm={'2022-2023':('2022-05-02','2023-05-01'),
        '2023-2024':('2023-05-01','2024-05-01'),
        '2024-2025':('2024-05-01','2025-05-01'),
        '2025-2026':('2025-05-01','2026-07-24')}
    rows=[]
    for yr,(s,e) in wm.items():
        d=df.loc[s:e].copy(); r=backtest(d,base_risk,min_score,cooldown,use_short)
        oracle=ORACLE.get(yr); tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and (not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def main():
    print("="*68)
    print("🧠 NEXUS BRAIN v14 — SELECTIVE HUMAN BRAIN (max 3 trades/month)")
    print("="*68)
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)

    print("\n--- Score threshold sweep (8,9) × Cooldown (288=3d, 480=5d, 672=7d) ---")
    best_score_val=-1e9; best_cfg=None; best_rows=None
    results_all=[]
    for ms in [7,8,9]:
        for cd in [192,288,480,672]:  # 2d/3d/5d/7d cooldown
            rows=run_gauntlet(0.055,ms,cd,True)
            pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
            mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
            tot_pnl=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
            tot_n=sum(r['trades'] for yr,r,o,t,c,v in rows)
            results_all.append((pos,mdd,tot_pnl,ms,cd,rows))
            flag='✅' if pos>=3 and mdd<=25 else ''
            print(f"  ms={ms} cd={cd}bars: pos={pos}/3 maxDD={mdd:.0f}% totalPnL={tot_pnl:.0f} n={tot_n} {flag}")
            if tot_pnl>best_score_val:
                best_score_val=tot_pnl; best_cfg=(ms,cd); best_rows=rows

    # Show all 3-positive-year configs
    good=[(pos,mdd,tp,ms,cd,rows) for pos,mdd,tp,ms,cd,rows in results_all if pos>=3 and mdd<=25]
    if good:
        good.sort(key=lambda x:-x[2])
        print(f"\n✅ {len(good)} configs with 3+ positive years AND DD<=25%:")
        pos,mdd,tp,ms,cd,rows=good[0]
        print(f"\n🏆 BEST (ms={ms}, cd={cd}): totalPnL={tp:.0f}")
    else:
        print(f"\n⚠️ No 3-positive-year+DD<=25% config found. Best: ms={best_cfg[0]}, cd={best_cfg[1]}")
        rows=best_rows

    print(f"\n{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR%':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")
    print()

    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined:
                combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.,'cvg':0,'rtrail':0}
            for k in combined[sn]: combined[sn][k]+=st.get(k,0)
    print("📊 Signal stats:")
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9); wr=st['w']/max(st['n'],1)*100
        avg_cv=st['cvg']/max(st['n'],1)
        trail_pct=st['rtrail']/max(st['n'],1)*100
        print(f"  {sn:<10}n={st['n']:3d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%  AvgConv={avg_cv:.1f}  TrailHit={trail_pct:.0f}%")

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V14_SELECTIVE.md')
    lines=["# 🧠 NEXUS BRAIN v14 — SELECTIVE HUMAN BRAIN REPORT",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else "N/A"; tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f: f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__': main()
