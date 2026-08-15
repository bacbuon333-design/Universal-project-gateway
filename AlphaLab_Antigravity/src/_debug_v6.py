"""
Fix: Check why signals still 0 in v6 by verifying the EMA200 96-bar comparison condition
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd

def ema(a,s): return pd.Series(a).ewm(span=s,adjust=False).mean().values

p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
df=pd.read_csv(p);df['dt']=pd.to_datetime(df['datetime_str']);df.set_index('dt',inplace=True)

d=df.loc['2024-05-01':'2025-05-01'].copy()
c=d['close'].values;h=d['high'].values;l=d['low'].values
n=len(c)
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

e200_rising=np.zeros(n,dtype=bool)
for i in range(96,n):
    e200_rising[i]=e200[i]>e200[i-96]

# count per condition
c1=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i])
c2=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and adx[i]>=16)
c3=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and adx[i]>=16 and l[i]<=e8[i])
c4=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and adx[i]>=16 and l[i]<=e8[i] and c[i]>e8[i])
c5=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and adx[i]>=16 and l[i]<=e8[i] and c[i]>e8[i] and rsi[i]<=45)
c6=sum(1 for i in range(250,n) if c[i]>e200[i] and e50[i]>e200[i] and adx[i]>=16 and l[i]<=e8[i] and c[i]>e8[i] and rsi[i]<=45 and c[i]>e21[i])

print("2024-2025 condition cascade (PULL_E8_BUY):")
print(f"  c>e200 and e50>e200: {c1}")
print(f"  + adx>=16: {c2}")
print(f"  + l<=e8: {c3}")
print(f"  + c>e8: {c4}")
print(f"  + rsi<=45: {c5}")
print(f"  + c>e21: {c6}")
