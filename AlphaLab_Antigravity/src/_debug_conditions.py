"""
Signal condition debug — check if conditions are being met in each year
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)

windows={'2022-2023':('2022-05-02','2023-05-01'),
         '2023-2024':('2023-05-01','2024-05-01'),
         '2024-2025':('2024-05-01','2025-05-01')}

for yr,(s,e) in windows.items():
    d=df.loc[s:e].copy()
    c=d['close'].values;h=d['high'].values;l=d['low'].values
    e8=ema(c,8);e21=ema(c,21);e50=ema(c,50);e200=ema(c,200)
    tr=np.maximum(h[1:]-l[1:],np.maximum(np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])))
    tr=np.append([tr[0]],tr)
    atr14=pd.Series(tr).rolling(14).mean().values
    d2=pd.Series(c).diff()
    g=d2.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    ls=(-d2.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean().replace(0,1e-9)
    rsi=(100-100/(1+g/ls)).values
    up=pd.Series(h).diff();dn=-pd.Series(l).diff()
    pdm=up.where((up>dn)&(up>0),0.);ndm=dn.where((dn>up)&(dn>0),0.)
    aa=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    ndi=100*ndm.ewm(alpha=1/14,adjust=False).mean()/aa.replace(0,1e-9)
    adx=(100*(pdi-ndi).abs()/(pdi+ndi).replace(0,1e-9)).ewm(alpha=1/14,adjust=False).mean().values
    e200_slope=np.gradient(e200)
    n=len(c)

    # Count which components fire
    cnt_macro_bull=cnt_macro_bear=0
    cnt_s1=cnt_s2=cnt_s3=cnt_s4=0
    for i in range(250,n):
        sloping_up=e200_slope[i]>0;sloping_down=e200_slope[i]<0
        macro_bull=c[i]>e200[i] and e50[i]>e200[i] and sloping_up
        macro_bear=c[i]<e200[i] and e50[i]<e200[i] and sloping_down
        if macro_bull:cnt_macro_bull+=1
        if macro_bear:cnt_macro_bear+=1
        if macro_bull and adx[i]>=16:
            if l[i]<=e8[i] and c[i]>e8[i] and rsi[i]<=44 and c[i]>e21[i]: cnt_s1+=1
            if l[i]<=e21[i] and c[i]>e21[i] and rsi[i]<=38 and c[i]>e50[i]: cnt_s2+=1
        if macro_bear and adx[i]>=16:
            if h[i]>=e8[i] and c[i]<e8[i] and rsi[i]>=56 and c[i]<e21[i]: cnt_s3+=1
            if h[i]>=e21[i] and c[i]<e21[i] and rsi[i]>=62 and c[i]<e50[i]: cnt_s4+=1

    pct_bull=cnt_macro_bull/max(n-250,1)*100
    pct_bear=cnt_macro_bear/max(n-250,1)*100
    print(f"{yr}: macro_bull={cnt_macro_bull}({pct_bull:.1f}%) macro_bear={cnt_macro_bear}({pct_bear:.1f}%)")
    print(f"  S1(pull_e8_buy)={cnt_s1}  S2(pull_e21_buy)={cnt_s2}  S3(reb_e8_sell)={cnt_s3}  S4(reb_e21_sell)={cnt_s4}")
    
    # Looser check without slope requirement
    cnt_loose_bull=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i])
    cnt_loose_s1=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and l[i]<=e8[i] and c[i]>e8[i] and rsi[i]<=44)
    print(f"  Loose(no slope): macro_bull={cnt_loose_bull}  S1_loose={cnt_loose_s1}")
    print()
