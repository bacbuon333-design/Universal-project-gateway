import pandas as pd, numpy as np

df = pd.read_csv('data/GOLD_M15.csv')
df['dt'] = pd.to_datetime(df['datetime_str'])
df.set_index('dt', inplace=True)

years = {
    '2022-2023': df.loc['2022-05-02':'2023-05-01'],
    '2023-2024': df.loc['2023-05-01':'2024-05-01'],
    '2024-2025': df.loc['2024-05-01':'2025-05-01'],
}

for name, d in years.items():
    print(f'--- {name} monthly close direction ---')
    dg = d.groupby(pd.Grouper(freq='ME'))
    for mkey, mg in dg:
        if len(mg) < 100: continue
        mc = mg['close'].values
        slope = (mc[-1]-mc[0]) / mc[0] * 100
        rng = float(mc.max()-mc.min())
        mstr = mkey.strftime('%Y-%m')
        print(f'  {mstr}: slope={slope:+.2f}% | range={rng:.2f} | bars={len(mc)}')
    print()
