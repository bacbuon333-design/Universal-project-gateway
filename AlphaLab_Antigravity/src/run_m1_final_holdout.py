from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from m1_final_holdout.confirmation import (
    BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED, EXPERIMENT_ID, REPRESENTATIONS,
    audit_holdout_dataset, build_confirmation_table, build_holdout_frame,
    build_yearly_descriptive_table, evaluate_final_holdout_gates,
    joint_max_rho_day_block_bootstrap, validate_holdout_frame,
)

ROOT=Path(__file__).resolve().parents[2]
DATA_PATH=ROOT/"AlphaLab_Antigravity"/"data"/"canonical"/"GOLD_M1_FINAL_HOLDOUT_2015_2017.csv"
OUT=ROOT/"AlphaLab_Antigravity"/"reports"/"m1_final_holdout"
SEAL_PATH=OUT/"M1_FINAL_HOLDOUT_EXTRACTION_SEAL.json"
FAILURE_PATH=OUT/"M1_FINAL_HOLDOUT_OPENED_FAILURE.json"
LOCAL_EVENT_PATH=OUT/"local"/"M1_FINAL_HOLDOUT_EVENTS.csv.gz"


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def safe(x:Any)->Any:
    if isinstance(x,dict): return {str(k):safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [safe(v) for v in x]
    if isinstance(x,np.integer): return int(x)
    if isinstance(x,np.floating):
        y=float(x); return y if np.isfinite(y) else None
    if isinstance(x,float): return x if np.isfinite(x) else None
    return x


def write_json(path:Path,payload:Any)->None:
    path.write_text(json.dumps(safe(payload),indent=2),encoding="utf-8")


def main()->None:
    if FAILURE_PATH.exists(): raise RuntimeError("STOP_BLOCKED_HOLDOUT_OPENED_FAILURE_MARKER_PRESENT")
    if not DATA_PATH.exists() or not SEAL_PATH.exists(): raise RuntimeError("STOP_BLOCKED_HOLDOUT_NOT_EXTRACTED_OR_NOT_SEALED")
    seal=json.loads(SEAL_PATH.read_text(encoding="utf-8")); actual_sha=sha256_file(DATA_PATH); sealed_sha=str(seal.get("canonical_sha256",""))
    if not sealed_sha or actual_sha!=sealed_sha: raise RuntimeError(f"STOP_BLOCKED_HOLDOUT_HASH_MISMATCH: sealed={sealed_sha} actual={actual_sha}")

    df=pd.read_csv(DATA_PATH); df["datetime"]=pd.to_datetime(df["datetime"],utc=True)
    validate_holdout_frame(df,require_all_years=True)
    OUT.mkdir(parents=True,exist_ok=True); LOCAL_EVENT_PATH.parent.mkdir(parents=True,exist_ok=True)
    audit=audit_holdout_dataset(df,dataset_sha256=actual_sha); write_json(OUT/"M1_FINAL_HOLDOUT_DATA_AUDIT.json",audit)

    frame=build_holdout_frame(df)
    confirmation,boots,fits=build_confirmation_table(frame)
    joint=joint_max_rho_day_block_bootstrap(fits)
    yearly=build_yearly_descriptive_table(frame)
    gates=evaluate_final_holdout_gates(audit,frame,confirmation,boots,joint)

    confirmation.to_csv(OUT/"M1_FINAL_HOLDOUT_CONFIRMATION.csv",index=False)
    write_json(OUT/"M1_FINAL_HOLDOUT_BOOTSTRAP.json",boots)
    write_json(OUT/"M1_FINAL_HOLDOUT_JOINT_MAX_RHO.json",joint)
    yearly.to_csv(OUT/"M1_FINAL_HOLDOUT_YEARLY_DESCRIPTIVE.csv",index=False)
    write_json(OUT/"M1_FINAL_HOLDOUT_GATES.json",gates)
    frame.to_csv(LOCAL_EVENT_PATH,index=False,compression="gzip"); local_sha=sha256_file(LOCAL_EVENT_PATH)

    manifest={
        "experiment_id":EXPERIMENT_ID,"research_type":"ONE_SHOT_FINAL_HOLDOUT_CONFIRMATION",
        "dataset_path":str(DATA_PATH),"dataset_sha256":actual_sha,"dataset_rows":int(len(df)),
        "holdout_start":str(df["datetime"].min()),"holdout_end":str(df["datetime"].max()),
        "holdout_years":sorted(int(y) for y in df["datetime"].dt.year.unique()),
        "development_2018_2025_accessed":False,"discovery_2026_accessed":False,
        "breach_events":int(len(frame)),"representations":list(REPRESENTATIONS),"primary_horizon_minutes":5,
        "bootstrap_iterations":BOOTSTRAP_ITERATIONS,"bootstrap_seed":BOOTSTRAP_SEED,
        "strict_gradient_claim":"NOT_TESTED_FINAL_HOLDOUT","placebo_claim":"NOT_RETESTED_FINAL_HOLDOUT",
        "fixed_budget_claim":False,"market_law_claim":False,"causal_identification_claim":False,
        "strategy_backtest":"NOT_RUN","paper_trading":"NO","live_trading":"NO","broker_execution":"NO",
        "gates":gates,"local_event_table":str(LOCAL_EVENT_PATH),"local_event_table_sha256":local_sha,
    }
    write_json(OUT/"M1_FINAL_HOLDOUT_MANIFEST.json",manifest)

    report=f"""# ALAB-M1 — FINAL HOLDOUT 2015–2017

## Scope
One-shot confirmation of the single surviving narrow development hypothesis. No further discovery, gradient rescue, placebo redesign, strategy creation, PnL backtest, paper/live trading, or broker execution.

## Frozen hypothesis
After a prior-20-closed-M1-bar extreme breach, greater in-candle snapback realization is associated with sub-one-for-one +5m future total-reversion persistence (`rho_5m < 1`) across ATR_T, ATR_PRE, PRICE_BPS, and EXCURSION_RATIO.

No strict monotonic-bin claim, fixed-budget claim, market-law claim, or causal microstructure claim is part of this holdout test.

## Dataset
- Holdout years: 2015–2017 only
- SHA256: `{actual_sha}`
- Rows: `{len(df):,}`
- Range: `{df['datetime'].min()}` to `{df['datetime'].max()}`
- Development 2018–2025 read by this runner: NO
- 2026+ read by this runner: NO

## Frozen confirmation rule
PASS requires data/coverage integrity, all four point `rho_5m < 1`, all four individual UTC-day bootstrap 95% upper bounds `<1`, and the shared-day bootstrap 97.5th percentile of `max(rho)` across the four representations `<1`.

Year-specific 2015/2016/2017 coefficients are descriptive only and cannot rescue or overturn the pooled rule.

## Final verdict
`{gates['verdict']}`

## Research program status
`{gates['research_program_status']}`
"""
    (OUT/"M1_FINAL_HOLDOUT_REPORT.md").write_text(report,encoding="utf-8")
    (ROOT/"M1_FINAL_HOLDOUT_MANIFEST.json").write_text((OUT/"M1_FINAL_HOLDOUT_MANIFEST.json").read_text(encoding="utf-8"),encoding="utf-8")
    (ROOT/"M1_FINAL_HOLDOUT_REPORT.md").write_text(report,encoding="utf-8")


if __name__=="__main__": main()
