from __future__ import annotations

import hashlib, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from m1_final_holdout.confirmation import (
    HOLDOUT_END_UTC, HOLDOUT_START_UTC, HOLDOUT_YEARS, MIN_YEAR_ROWS,
    audit_holdout_dataset,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_FINAL_HOLDOUT_2015_2017.csv"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_final_holdout"
SEAL_PATH = OUT / "M1_FINAL_HOLDOUT_EXTRACTION_SEAL.json"
FAILURE_PATH = OUT / "M1_FINAL_HOLDOUT_OPENED_FAILURE.json"
SYMBOL = "GOLD"
MIN_TERMINAL_MAXBARS = 1_000_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_safe(v) for v in x]
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, np.floating):
        y=float(x); return y if np.isfinite(y) else None
    return x


def _write_opened_failure(exc: Exception, opened_years: List[int], per_year: Dict[str, int]) -> None:
    if not opened_years: return
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id":"ALAB-M1-FINAL-HOLDOUT-2015-2017",
        "status":"HOLDOUT_OPENED_FAILURE_DO_NOT_RERUN",
        "holdout_opened":True,
        "opened_years":opened_years,
        "per_year_rows_returned_before_failure":per_year,
        "error_type":type(exc).__name__, "error":str(exc),
        "scientific_inference_run":False, "rerun_authorized":False,
    }
    FAILURE_PATH.write_text(json.dumps(_safe(payload), indent=2), encoding="utf-8")


def main() -> None:
    if DATA_PATH.exists() or SEAL_PATH.exists() or FAILURE_PATH.exists():
        raise RuntimeError("STOP_BLOCKED_HOLDOUT_ALREADY_OPENED_OR_EXTRACTED: one-shot protocol refuses rerun")
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        raise RuntimeError("STOP_BLOCKED_METATRADER5_IMPORT_FAILED") from exc

    opened_years: List[int] = []; per_year: Dict[str,int] = {}; terminal=None
    try:
        if not mt5.initialize():
            raise RuntimeError(f"STOP_BLOCKED_MT5_INITIALIZE_FAILED: {mt5.last_error()}")
        try:
            terminal=mt5.terminal_info()
            if terminal is None: raise RuntimeError("STOP_BLOCKED_MT5_TERMINAL_INFO_UNAVAILABLE")
            if int(getattr(terminal,"maxbars",0)) < MIN_TERMINAL_MAXBARS:
                raise RuntimeError(f"STOP_BLOCKED_MT5_MAXBARS_TOO_LOW: {getattr(terminal,'maxbars',None)} < {MIN_TERMINAL_MAXBARS}")
            if not mt5.symbol_select(SYMBOL, True): raise RuntimeError(f"STOP_BLOCKED_SYMBOL_SELECT_FAILED: {SYMBOL}")
            chunks=[]
            for year in HOLDOUT_YEARS:
                start=datetime(year,1,1,tzinfo=timezone.utc)
                end=datetime(year+1,1,1,tzinfo=timezone.utc)-timedelta(microseconds=1)
                rates=mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start, end)
                if rates is None or len(rates)==0:
                    raise RuntimeError(f"STOP_BLOCKED_HOLDOUT_YEAR_EMPTY: {year}; last_error={mt5.last_error()}")
                opened_years.append(int(year))
                part=pd.DataFrame(rates); part["datetime"]=pd.to_datetime(part["time"], unit="s", utc=True)
                per_year[str(year)]=int(len(part))
                if len(part) < MIN_YEAR_ROWS:
                    raise RuntimeError(f"STOP_BLOCKED_HOLDOUT_YEAR_INSUFFICIENT: {year} rows={len(part)} min={MIN_YEAR_ROWS}")
                chunks.append(part)
        finally:
            mt5.shutdown()

        df=pd.concat(chunks,ignore_index=True).sort_values("datetime",kind="mergesort").reset_index(drop=True)
        if df["datetime"].duplicated().any(): raise RuntimeError("STOP_BLOCKED_HOLDOUT_DUPLICATE_TIMESTAMPS")
        if df["datetime"].min()<HOLDOUT_START_UTC or df["datetime"].max()>=HOLDOUT_END_UTC: raise RuntimeError("STOP_BLOCKED_HOLDOUT_BOUNDARY_VIOLATION")
        if set(int(y) for y in df["datetime"].dt.year.unique()) != set(HOLDOUT_YEARS): raise RuntimeError("STOP_BLOCKED_HOLDOUT_MISSING_YEAR")
        cols=["datetime","open","high","low","close","tick_volume","spread","real_volume"]
        missing=[c for c in cols if c not in df.columns]
        if missing: raise RuntimeError(f"STOP_BLOCKED_MT5_RATE_SCHEMA_MISMATCH: {missing}")
        canonical=df[cols].copy()
        DATA_PATH.parent.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
        td=DATA_PATH.with_suffix(DATA_PATH.suffix+".tmp"); ts=SEAL_PATH.with_suffix(SEAL_PATH.suffix+".tmp")
        if td.exists(): td.unlink()
        if ts.exists(): ts.unlink()
        canonical.to_csv(td,index=False,date_format="%Y-%m-%dT%H:%M:%S%z")
        sha=sha256_file(td); audit=audit_holdout_dataset(canonical,dataset_sha256=sha)
        seal={
            "experiment_id":"ALAB-M1-FINAL-HOLDOUT-2015-2017","extraction_status":"SEALED_CANONICAL_CREATED_ONCE",
            "source":"MetaTrader5.copy_rates_range","symbol":SYMBOL,"timeframe":"M1","requested_years":list(HOLDOUT_YEARS),
            "annual_chunks":3,"failed_chunks":0,"per_year_rows":per_year,"interpolation":False,"deduplication_applied":False,
            "canonical_path":str(DATA_PATH),"canonical_sha256":sha,"terminal_maxbars":int(getattr(terminal,"maxbars",0)),
            "terminal_build":int(getattr(terminal,"build",0)),"terminal_name":str(getattr(terminal,"name","")),"audit":audit,
        }
        ts.write_text(json.dumps(_safe(seal),indent=2),encoding="utf-8")
        os.replace(td,DATA_PATH); os.replace(ts,SEAL_PATH)
        print(json.dumps(_safe(seal),indent=2))
    except Exception as exc:
        _write_opened_failure(exc,opened_years,per_year)
        raise


if __name__ == "__main__": main()
