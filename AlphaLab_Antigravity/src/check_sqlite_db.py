import sqlite3
import os

db_path = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\gold_history.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("Tables in gold_history.db:")
for t in tables:
    name = t[0]
    cur.execute(f"PRAGMA table_info({name})")
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f"SELECT count(*) FROM {name}")
    count = cur.fetchone()[0]
    time_col = 'time' if 'time' in cols else ('datetime_str' if 'datetime_str' in cols else cols[0])
    cur.execute(f"SELECT min({time_col}), max({time_col}) FROM {name}")
    tmin, tmax = cur.fetchone()
    print(f"Table: {name:20} | Rows: {count:10,} | Cols: {cols} | Min: {tmin} | Max: {tmax}")
conn.close()
