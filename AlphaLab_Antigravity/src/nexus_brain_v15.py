"""
NEXUS BRAIN v15 — ADAPTIVE REGIME ENGINE (FINAL)
==================================================
Combines all learnings into one coherent brain:

REGIME DETECTION (per H1 bar):
  A) PARABOLIC BULL: macro_bull AND ATR > 1.6x avg AND ADX > 30
     → Entry: H1 DC20 breakout (buy new highs, momentum following)
  B) NORMAL BULL:   macro_bull AND NOT parabolic
     → Entry: H1 EMA21 pullback buy (buy dips to key EMA)
  C) BEAR:          macro_bear
     → FLAT — no trade (short signals proven losers for Gold)

MACRO FILTER:
  3-month momentum: close > close[3 months ago] → macro_bull
  (No EMA warmup needed, works from bar 0)

EXIT: Adaptive trailing stop (activates at 1.5R, trails at 2.5 ATR)

Bug fix: si=0 is valid (use 'is not None' check)
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np,pandas as pd
from datetime import datetime,timezone
from dataclasses import dataclass

PIP=0.01;PTVAL=0.01;COMM=0.07;SPR=25.0
ORACLE={'2022-2023':7630.94,'2023-2024':6704.25,'2024-2025':14041.03}
WINDOWS={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01'),
         '2025-2026':('2025-05-01','2026-07-24')}

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values
def sma(a,s): return pd.Series(a).rolling(s,min_periods=1).mean().values

def build_indicators(h1c,h1h,h1l,h1o,nh1):
    e8=ema(h1c,8); e21=ema(h1c,21); e50=ema(h1c,50); e200=ema(h1c,200)
    tr=np.maximum(h1h[1:]-h1l[1:],np.maximum(np.abs(h1h[1:]-h1c[:-1]),np.abs(h1l[1:]-h1c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    atr_slow=pd.Series(atr14).rolling(240).mean().values  # 10-day avg ATR on H1
    d2=pd.Series(h1c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h1h).diff(); dn=-pd.Series(h1l).diff()
    pdm=up.where((up>dn)&(up>0),0.); ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    di=(pdi-ndi).values
    # 3-month momentum (480*3 = 1440 H1 bars ≈ 3 months)
    mom3m=np.zeros(nh1,dtype=bool)
    for i in range(1440,nh1): mom3m[i]=h1c[i]>h1c[i-1440]
    # 1-month momentum (480 bars)
    mom1m=np.zeros(nh1,dtype=bool)
    for i in range(480,nh1): mom1m[i]=h1c[i]>h1c[i-480]
    # DC20 for breakout signals
    dc20_hi=pd.Series(h1h).rolling(20).max().shift(1).values
    # Fractal pivot lows (5-bar lookback each side)
    pivot_lo=np.full(nh1,np.nan)
    for i in range(5,nh1-5):
        if h1l[i]==min(h1l[i-5:i+6]): pivot_lo[i]=h1l[i]
    return dict(e8=e8,e21=e21,e50=e50,e200=e200,
                atr14=atr14,atr_slow=atr_slow,rsi=rsi,adx=adx,di=di,
                mom3m=mom3m,mom1m=mom1m,dc20_hi=dc20_hi,pivot_lo=pivot_lo)

def build_signals_full(h1c,h1h,h1l,h1o,nh1,cfg):
    ms=cfg.get('min_score',5); cd=cfg.get('cooldown',48)
    pl_lb=cfg.get('pivot_lb',100); za=cfg.get('zone_atr',1.0)
    para_th=cfg.get('para_th',1.6)  # ATR expansion threshold for parabolic
    adx_para=cfg.get('adx_para',28) # ADX threshold for parabolic
    adx_norm=cfg.get('adx_norm',18) # ADX threshold for normal entry

    ind=build_indicators(h1c,h1h,h1l,h1o,nh1)
    e8=ind['e8'];e21=ind['e21'];e50=ind['e50'];e200=ind['e200']
    atr=ind['atr14'];atr_s=ind['atr_slow'];rsi=ind['rsi']
    adx=ind['adx'];di=ind['di'];mom3m=ind['mom3m'];mom1m=ind['mom1m']
    dc20=ind['dc20_hi'];pvlo=ind['pivot_lo']

    sig=np.zeros(nh1,dtype=int); slp=np.zeros(nh1); rrv=np.zeros(nh1)
    nm=['']*nh1; conv=np.zeros(nh1,dtype=int)
    last_bar=-9999

    for i in range(250,nh1):
        if i-last_bar<cd: continue
        cv=h1c[i];hi=h1h[i];lo=h1l[i];oi=h1o[i]
        av=max(atr[i],1.5);rv=rsi[i];dv=adx[i];div=di[i]
        as_=max(atr_s[i],1.5);ar=av/as_  # ATR expansion ratio

        # ── MACRO: 3-month momentum (no warmup issue) ──
        macro_bull=mom3m[i] and mom1m[i] and cv>e200[i]

        if not macro_bull: continue

        # ── REGIME ──────────────────────────────────────────────
        parabolic=ar>=para_th and dv>=adx_para  # ATR expanding + strong ADX

        # ── PARABOLIC REGIME: DC20 Breakout ─────────────────────
        if parabolic:
            if (dc20[i]>0 and h1c[i]>dc20[i] and h1c[i-1]<=dc20[i-1]
                    and dv>=adx_para and div>10 and rv<=72):
                rr=4.0 + (0.5 if ar>=2.0 else 0.)
                sc=6+int(dv>=35)+int(ar>=2.0)
                sig[i]=1;slp[i]=(av/PIP)*1.3+SPR;rrv[i]=rr;nm[i]='PARA_BREAK_BUY'
                conv[i]=sc;last_bar=i;continue

        # ── NORMAL BULL: EMA21 Pullback ──────────────────────────
        if dv>=adx_norm and div>0:
            # Get recent pivot lows as support confirmation
            start=max(0,i-pl_lb)
            p_lows=[pvlo[j] for j in range(start,i) if not np.isnan(pvlo[j])]
            # Deduplicate nearby levels
            p_lows_u=[]
            for lv in sorted(p_lows):
                if not any(abs(lv-x)<1.5*av for x in p_lows_u):p_lows_u.append(lv)

            at_pivot=any(abs(lo-lvl)<=za*av for lvl in p_lows_u)
            at_e21=h1l[i]<=e21[i] and h1c[i]>e21[i]
            at_e8=h1l[i]<=e8[i] and h1c[i]>e8[i] and h1c[i]>e21[i]

            sc=0
            if cv>e200[i]:sc+=1
            if e50[i]>e200[i]:sc+=1
            if dv>=22 and div>5:sc+=1
            if at_pivot:sc+=2
            if at_e21:sc+=1
            if i>=1:
                o1,c1=h1o[i-1],h1c[i-1]
                b=abs(h1c[i]-h1o[i])+1e-9;lw=min(h1o[i],h1c[i])-lo
                is_pin=(lw>=2.0*b and lw>=0.5*(hi-lo+1e-9) and(h1c[i]-lo)/(hi-lo+1e-9)>=0.5)
                is_eng=(c1<o1 and h1c[i]>h1o[i] and h1c[i]>=(o1-abs(o1-c1)*0.15))
                if is_pin:sc+=3
                elif is_eng:sc+=2
                elif h1c[i]>h1o[i] and at_e21 and ar>=0.9:sc+=1

            if sc>=ms and rv<=68:
                rr=3.5 if sc>=8 else(3.0 if sc>=6 else 2.5)
                if ar>=1.3:rr+=0.3
                sig[i]=1;slp[i]=(av/PIP)*1.4+SPR;rrv[i]=rr;nm[i]='PULL_BUY'
                conv[i]=sc;last_bar=i

    return sig,slp,rrv,nm,conv,ind

def lot_size(eq,pk,sp,cv,risk):
    dd=(pk-eq)/max(pk,1e-9)*100
    if dd>=15:r=risk*0.15
    elif dd>=10:r=risk*0.38
    elif dd>=6:r=risk*0.68
    else:r=risk
    mult=1.3 if cv>=8 else(1.0 if cv>=6 else 0.8)
    return max(0.01,min(round(eq*r*mult/(sp*0.01)*0.01,2),25.))

@dataclass
class Tr:
    dir:str='BUY';entry:float=0.;sl:float=0.;tp:float=0.
    lot:float=0.01;pnl:float=0.;sname:str='';conv:int=0
    trail_on:bool=False;hwm:float=0.;sl_pts:float=0.

def eval_window(h1c,h1h,h1l,atr14,sig,slp,rrv,nm,conv,si,ei,risk):
    bal=1000.;pk=1000.;mx=0.;trades=[];stats={};ot=None
    for i in range(si,ei):
        if ot:
            done=False;ex=h1c[i];av=max(atr14[i],1.5)
            if h1h[i]>ot.hwm:ot.hwm=h1h[i]
            if not ot.trail_on and(h1h[i]-ot.entry)>=1.5*ot.sl_pts*PIP:ot.trail_on=True
            if ot.trail_on:
                ns=ot.hwm-2.5*av
                if ns>ot.sl:ot.sl=ns
            if h1l[i]<=ot.sl:ex=ot.sl;done=True
            elif h1h[i]>=ot.tp and not ot.trail_on:ex=ot.tp;done=True
            if done:
                pts=(ex-ot.entry)/PIP
                net=pts*PTVAL*(ot.lot/0.01)-(ot.lot/0.01)*COMM
                bal+=net;pk=max(pk,bal);dd=pk-bal;mx=max(mx,dd/pk*100)
                ot.pnl=net;sn=ot.sname
                if sn not in stats:stats[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
                stats[sn]['n']+=1;stats[sn]['pnl']+=net
                if net>0:stats[sn]['w']+=1;stats[sn]['wu']+=net
                else:stats[sn]['lu']+=abs(net)
                trades.append(ot);ot=None
        if ot is None and sig[i]==1:
            sp=slp[i]
            if sp>0:
                lt=lot_size(bal,pk,sp,conv[i],risk)
                e_=h1c[i]+SPR*PIP;sl_=e_-sp*PIP;tp_=e_+sp*rrv[i]*PIP
                ot=Tr(entry=e_,sl=sl_,tp=tp_,lot=lt,sname=nm[i],
                      conv=conv[i],trail_on=False,hwm=e_,sl_pts=sp)
    pnls=[t.pnl for t in trades]
    wins=[p for p in pnls if p>0];losses=[p for p in pnls if p<0]
    gw=sum(wins) if wins else 0.;gl=abs(sum(losses)) if losses else 1e-9
    return dict(final=bal,pnl=bal-1000.,pct=(bal-1000.)/10.,
                trades=len(pnls),wr=len(wins)/max(len(pnls),1)*100,
                pf=gw/gl,maxdd=mx,stats=stats)

def load_data():
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
    df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)
    c=df['close'].values;h=df['high'].values;l=df['low'].values;o=df['open'].values
    n=len(c);seg=n//4
    h1c=np.array([c[i*4+3] for i in range(seg)])
    h1h=np.array([max(h[i*4:i*4+4]) for i in range(seg)])
    h1l=np.array([min(l[i*4:i*4+4]) for i in range(seg)])
    h1o=np.array([o[i*4] for i in range(seg)])
    h1_dt=[df.index[i*4+3] for i in range(seg)]
    return h1c,h1h,h1l,h1o,seg,h1_dt

def run_gauntlet(cfg,risk=0.055):
    h1c,h1h,h1l,h1o,nh1,h1_dt=load_data()
    # BUG FIX: si is not None (not just truthy)
    win_ranges={}
    for yr,(ws,we) in WINDOWS.items():
        wsd=pd.Timestamp(ws);wed=pd.Timestamp(we)
        si=next((i for i,t in enumerate(h1_dt) if t>=wsd),None)
        ei=next((i for i,t in enumerate(h1_dt) if t>=wed),nh1)
        if si is not None:win_ranges[yr]=(si,ei)  # FIX: was 'if si:'
    sig,slp,rrv,nm,conv,ind=build_signals_full(h1c,h1h,h1l,h1o,nh1,cfg)
    atr14=ind['atr14']
    rows=[]
    for yr,(si,ei) in win_ranges.items():
        r=eval_window(h1c,h1h,h1l,atr14,sig,slp,rrv,nm,conv,si,ei,risk)
        oracle=ORACLE.get(yr);tgt=oracle*0.20 if oracle else None
        cap=r['pnl']/oracle*100 if oracle else None
        ok=r['maxdd']<=25 and(not oracle or r['pnl']>0)
        rows.append((yr,r,oracle,tgt,cap,'✅'if ok else '❌'))
    return rows

def print_table(rows,label=""):
    if label:print(label)
    print(f"{'Year':<14}{'Final$':>9}{'PnL%':>7}{'PF':>7}{'MaxDD':>8}{'Trades':>8}{'WR':>6}{'Capt%':>8}{'V':>3}")
    print("-"*72)
    for yr,r,o,t,cap,v in rows:
        cs=f"{cap:.1f}%" if cap else 'N/A'
        tg=f"(T:{t:,.0f}$)" if t else ""
        print(f"{yr:<14}{r['final']:>9,.2f}{r['pct']:>6.1f}%{r['pf']:>7.3f}{r['maxdd']:>7.2f}%{r['trades']:>8}{r['wr']:>5.1f}%{cs:>8}{v:>3} {tg}")

def main():
    print("="*68)
    print("🧠 NEXUS BRAIN v15 — ADAPTIVE REGIME ENGINE (3-month momentum)")
    print("="*68)
    RISK=0.055
    best_score=-1e9;best_cfg=None;best_rows=None;pos3=[]

    for ms in [4,5,6]:
        for cd in [24,48,72]:
            for pl in [50,100,150]:
                for za in [0.8,1.0,1.5]:
                    for pt in [1.4,1.6,2.0]:
                        cfg={'min_score':ms,'cooldown':cd,'pivot_lb':pl,
                             'zone_atr':za,'para_th':pt,'adx_para':28,'adx_norm':16}
                        rows=run_gauntlet(cfg,RISK)
                        pos=sum(1 for yr,r,o,t,c,v in rows if r['pnl']>0 and o)
                        mdd=max(r['maxdd'] for yr,r,o,t,c,v in rows)
                        tot=sum(r['pnl'] for yr,r,o,t,c,v in rows if o)
                        nt=sum(r['trades'] for yr,r,o,t,c,v in rows)
                        if pos>=3 and mdd<=25:pos3.append((tot,cfg.copy(),rows,nt))
                        if tot>best_score:best_score=tot;best_cfg=cfg.copy();best_rows=rows

    pos3.sort(key=lambda x:-x[0])
    if pos3:
        print(f"\n✅ {len(pos3)} configs: 3+ positive years AND DD<=25%!")
        for tot,cfg,rows,nt in pos3[:5]:
            yr_str=' | '.join(f"{yr[:7]}:{r['pct']:+.0f}%(DD:{r['maxdd']:.0f}%)" for yr,r,*_ in rows)
            print(f"  ms={cfg['min_score']} cd={cfg['cooldown']} pl={cfg['pivot_lb']} za={cfg['zone_atr']} pt={cfg['para_th']} | {yr_str} | n={nt}")
        tot,cfg,rows,nt=pos3[0]
        print(f"\n🏆 BEST ({tot:.0f}): {cfg}")
    else:
        print(f"\n⚠️  No 3+yr DD<=25%. Best({best_score:.0f}): {best_cfg}")
        rows=best_rows

    print_table(rows)
    combined={}
    for yr,r,*_ in rows:
        for sn,st in r['stats'].items():
            if sn not in combined:combined[sn]={'n':0,'pnl':0.,'w':0,'wu':0.,'lu':0.}
            for k in combined[sn]:combined[sn][k]+=st[k]
    print("\n📊 Signal stats:")
    for sn,st in combined.items():
        pf=st['wu']/max(st['lu'],1e-9);wr=st['w']/max(st['n'],1)*100
        print(f"  {sn:<20}n={st['n']:4d}  PnL={st['pnl']:+8.2f}  PF={pf:.3f}  WR={wr:.1f}%")

    rdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'reports','core_upgrade')
    os.makedirs(rdir,exist_ok=True)
    rf=os.path.join(rdir,'NEXUS_BRAIN_V15_FINAL.md')
    out=pos3[0][2] if pos3 else best_rows; cfg_out=pos3[0][1] if pos3 else best_cfg
    lines=["# 🧠 NEXUS BRAIN v15 — ADAPTIVE REGIME ENGINE",
           f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC",
           f"**Config**: {cfg_out}",
           "**Macro Filter**: 3-month momentum (no EMA warmup issue)",
           "**Regimes**: PARABOLIC (DC20 breakout) / NORMAL (EMA21 pullback)",
           "\n---\n## Results",
           "| Year | Final$ | PnL% | PF | MaxDD | Trades | WR | Capture% | Oracle20% | V |",
           "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"]
    for yr,r,o,t,cap,v in out:
        cs=f"{cap:.1f}%" if cap else "N/A";tg=f"${t:,.0f}" if t else "N/A"
        lines.append(f"| **{yr}** | ${r['final']:,.2f} | {r['pct']:.1f}% | {r['pf']:.3f} | {r['maxdd']:.2f}% | {r['trades']} | {r['wr']:.1f}% | {cs} | {tg} | {v} |")
    with open(rf,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(f"\n📄 Saved: {rf}")

if __name__=='__main__':main()
