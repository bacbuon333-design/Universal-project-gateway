"""
Debug v14 scoring — find out what the actual score distribution looks like
"""
import os,sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform=='win32' else None
import numpy as np,pandas as pd
from nexus_brain_v14 import build_ind,score_trade,is_pin_bull,is_pin_bear,is_bull_engulf,is_bear_engulf

p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data','GOLD_M15.csv')
df=pd.read_csv(p); df['dt']=pd.to_datetime(df['datetime_str']); df.set_index('dt',inplace=True)

for yr,(s,e) in [('2023-2024',('2023-05-01','2024-05-01')),
                  ('2024-2025',('2024-05-01','2025-05-01'))]:
    d=df.loc[s:e].copy()
    c=d['close'].values; h=d['high'].values; l=d['low'].values; o=d['open'].values
    n=len(c)
    ind=build_ind(c,h,l,o)
    atr=ind['atr14']

    # Count scores
    scores_l=[]; scores_s=[]
    pins_bull=0; pins_bear=0; engulf_bull=0; engulf_bear=0
    for i in range(1500,n):
        av=max(atr[i],1.5)
        sl,_,_=score_trade(i,1,c,h,l,o,ind)
        ss,_,_=score_trade(i,-1,c,h,l,o,ind)
        scores_l.append(sl); scores_s.append(ss)
        if i>=1:
            if is_pin_bull(o[i],h[i],l[i],c[i],av): pins_bull+=1
            if is_pin_bear(o[i],h[i],l[i],c[i],av): pins_bear+=1
            if is_bull_engulf(o[i-1],c[i-1],o[i],c[i]): engulf_bull+=1
            if is_bear_engulf(o[i-1],c[i-1],o[i],c[i]): engulf_bear+=1

    sl=pd.Series(scores_l); ss=pd.Series(scores_s)
    print(f"\n{yr} (n={n-1500} bars after warmup):")
    print(f"  LONG score dist: {sl.value_counts().sort_index().to_dict()}")
    print(f"  SHORT score dist: {ss.value_counts().sort_index().to_dict()}")
    print(f"  Scores>=7 LONG: {(sl>=7).sum()}, Scores>=8: {(sl>=8).sum()}")
    print(f"  Scores>=7 SHORT: {(ss>=7).sum()}, Scores>=8: {(ss>=8).sum()}")
    print(f"  Pin Bull: {pins_bull}, Pin Bear: {pins_bear}")
    print(f"  Engulf Bull: {engulf_bull}, Engulf Bear: {engulf_bear}")
    # What are the limiting factors?
    cnt_ctx=sum(1 for i in range(1500,n) if c[i]>ind['e1440'][i] and c[i]>ind['e960'][i] and ind['e480'][i]>ind['e960'][i])
    cnt_near_sr=sum(1 for i in range(1500,n) if (ind['w_lo'][i]>0 and abs(l[i]-ind['w_lo'][i])<=atr[i]*2.0))
    print(f"  Context>=3 (bull): {cnt_ctx}")
    print(f"  Near weekly S/R (low): {cnt_near_sr}")
