import os
import sys
import glob
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data"

def audit_file(filepath):
    filename = os.path.basename(filepath)
    print(f"\n=======================================================")
    print(f"AUDITING: {filename}")
    print(f"=======================================================")
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return None

    print(f"Columns: {list(df.columns)}")
    print(f"Total Rows: {len(df):,}")

    # Identify datetime column
    dt_col = None
    for col in ['datetime_str', 'datetime', 'time', 'date', 'Date', 'Time', 'dt']:
        if col in df.columns:
            dt_col = col
            break

    if dt_col is None:
        print("ERROR: No recognizable datetime column found.")
        return None

    df['dt'] = pd.to_datetime(df[dt_col], errors='coerce')
    null_dates = df['dt'].isnull().sum()
    if null_dates > 0:
        print(f"WARNING: {null_dates} unparseable datetime rows!")

    df = df.dropna(subset=['dt']).sort_values('dt').reset_index(drop=True)

    start_date = df['dt'].min()
    end_date = df['dt'].max()
    print(f"Date Range: {start_date} to {end_date} (Duration: {end_date - start_date})")

    # Duplicate timestamps
    dups = df['dt'].duplicated().sum()
    print(f"Duplicate timestamps: {dups}")

    # Check OHLC columns
    cols_lower = {c.lower(): c for c in df.columns}
    required = ['open', 'high', 'low', 'close']
    has_ohlc = all(r in cols_lower for r in required)
    if not has_ohlc:
        print(f"WARNING: Missing OHLC columns! Present: {list(df.columns)}")
        return None

    o = df[cols_lower['open']].values
    h = df[cols_lower['high']].values
    l = df[cols_lower['low']].values
    c = df[cols_lower['close']].values

    # Sanity checks
    nan_count = np.isnan(o).sum() + np.isnan(h).sum() + np.isnan(l).sum() + np.isnan(c).sum()
    zero_count = (o <= 0).sum() + (h <= 0).sum() + (l <= 0).sum() + (c <= 0).sum()
    invalid_hl = (h < l).sum()
    invalid_oh = (o > h).sum()
    invalid_ol = (o < l).sum()
    invalid_ch = (c > h).sum()
    invalid_cl = (c < l).sum()

    print(f"NaN price values: {nan_count}")
    print(f"Zero / negative price values: {zero_count}")
    print(f"Invalid High < Low: {invalid_hl}")
    print(f"Invalid Open > High: {invalid_oh}")
    print(f"Invalid Open < Low: {invalid_ol}")
    print(f"Invalid Close > High: {invalid_ch}")
    print(f"Invalid Close < Low: {invalid_cl}")

    # Volume / Spread
    for vol_name in ['tick_volume', 'volume', 'vol', 'spread']:
        if vol_name in cols_lower:
            actual_col = cols_lower[vol_name]
            v = df[actual_col].values
            print(f"Column '{actual_col}': min={np.nanmin(v)}, max={np.nanmax(v)}, mean={np.nanmean(v):.2f}, zeros={(v == 0).sum()}")

    # Sampling interval / time delta stats
    time_diffs = df['dt'].diff().dropna()
    vc = time_diffs.value_counts().head(5)
    print(f"Top 5 bar intervals:")
    for delta, count in vc.items():
        print(f"  {delta}: {count:,} bars ({count/len(df)*100:.1f}%)")

    # Check for major weekend / overnight gaps vs abnormal intraday gaps
    large_gaps = time_diffs[time_diffs > pd.Timedelta(days=4)]
    print(f"Gaps > 4 days (extended holiday/market closures): {len(large_gaps)}")

    return {
        'file': filename,
        'rows': len(df),
        'start': str(start_date),
        'end': str(end_date),
        'dups': dups,
        'invalid_hl': invalid_hl,
        'nan_count': nan_count
    }

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    print(f"Found {len(files)} CSV files in data directory.")
    summaries = []
    for f in files:
        res = audit_file(f)
        if res:
            summaries.append(res)

    print("\n\n" + "="*80)
    print("AUDIT SUMMARY TABLE")
    print("="*80)
    sdf = pd.DataFrame(summaries)
    print(sdf.to_string(index=False))

if __name__ == '__main__':
    main()
