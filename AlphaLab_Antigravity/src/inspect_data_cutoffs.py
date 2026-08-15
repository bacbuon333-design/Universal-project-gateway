import os
import sys
import glob
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))

print(f"Inspecting {len(files)} CSV datasets in {DATA_DIR}...")
records = []

for f in files:
    fname = os.path.basename(f)
    try:
        df = pd.read_csv(f)
        dt_col = 'datetime_str' if 'datetime_str' in df.columns else ('dt' if 'dt' in df.columns else 'time')
        df['dt'] = pd.to_datetime(df[dt_col])
        df = df.sort_values('dt').reset_index(drop=True)
        
        min_dt = df['dt'].min()
        max_dt = df['dt'].max()
        rows = len(df)
        
        # Years coverage
        df['year'] = df['dt'].dt.year
        df['quarter'] = df['dt'].dt.to_period('Q').astype(str)
        unique_years = sorted(df['year'].unique())
        unique_quarters = sorted(df['quarter'].unique())
        
        records.append({
            'filename': fname,
            'rows': rows,
            'start_timestamp': str(min_dt),
            'latest_timestamp': str(max_dt),
            'first_quarter': unique_quarters[0],
            'last_quarter': unique_quarters[-1],
            'total_quarters': len(unique_quarters),
            'years_count': len(unique_years),
            'years_range': f"{unique_years[0]} - {unique_years[-1]}"
        })
    except Exception as e:
        print(f"Error parsing {fname}: {e}")

res_df = pd.DataFrame(records)
print(res_df[['filename', 'rows', 'start_timestamp', 'latest_timestamp', 'total_quarters']].to_string(index=False))

# Export for manifest generation
res_df.to_json(os.path.join(os.path.dirname(__file__), "dataset_boundaries.json"), orient='records', indent=2)
