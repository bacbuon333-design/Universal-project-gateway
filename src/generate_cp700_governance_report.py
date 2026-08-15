"""
GENERATE OFFICIAL GOVERNANCE AUDIT REPORT FOR CP-700 NATIVE MODEL=4 RUN
========================================================================
"""

import os, sys, json, hashlib

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
REPORTS_DIR = os.path.join(DATA_DIR, "reports", "antigravity_reaudit", "run_20260801_cp700_native")
os.makedirs(REPORTS_DIR, exist_ok=True)

MQ5_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", "ALAB_CP700_MultiRegimeEA.mq5")
EX5_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "ALAB_CP700_MultiRegimeEA.ex5")
MANIFEST_PATH = os.path.join(DATA_DIR, "governance", "cp700_causal_multi_regime_v1.json")
INI_PATH = os.path.join(DATA_DIR, "generate_cp700_report.ini")
GOV_REPORT_PATH = os.path.join(REPORTS_DIR, "cp700_governance_audit.json")
MD_REPORT_PATH = os.path.join(REPORTS_DIR, "cp700_governance_audit.md")

def sha256_file(path):
    if not os.path.exists(path): return "N/A"
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def build_report():
    mq5_hash = sha256_file(MQ5_PATH)
    ex5_hash = sha256_file(EX5_PATH)
    manifest_hash = sha256_file(MANIFEST_PATH)
    ini_hash = sha256_file(INI_PATH)
    
    audit_data = {
        "architecture_name": "ALAB_CP700_MultiRegimeEA",
        "governance_manifest": MANIFEST_PATH,
        "governance_manifest_sha256": manifest_hash,
        "source_mq5_sha256": mq5_hash,
        "binary_ex5_sha256": ex5_hash,
        "ini_config_sha256": ini_hash,
        "native_tester_contract": {
            "terminal_path": r"C:\Program Files\XM Global MT5\terminal64.exe",
            "compiler_path": r"C:\Program Files\XM Global MT5\metaeditor64.exe",
            "symbol": "GOLD",
            "period": "M15",
            "model": 4,
            "model_description": "Model=4 Real Ticks",
            "ticks_processed": 225125541,
            "history_quality_pct": 63.0,
            "from_date": "2022.05.01",
            "to_date": "2026.07.27",
            "deposit_usd": 1000.0,
            "leverage": "1:500"
        },
        "target_gate_evaluation": {
            "net_profit_usd": {"value": 0.0, "target": "> 5000.0", "passed": False},
            "profit_factor": {"value": 0.0, "target": ">= 1.50", "passed": False},
            "win_rate_pct": {"value": 0.0, "target": "> 45.0", "passed": False},
            "equity_drawdown_pct": {"value": 0.0, "target": "<= 20.0", "passed": True},
            "history_quality_pct": {"value": 63.0, "target": ">= 99.0", "passed": False},
            "model_4_real_ticks": {"value": True, "target": True, "passed": True}
        },
        "classification": "REJECTED_LOW_REAL_TICK_QUALITY",
        "decision": "NO_SAFE_TARGET_CANDIDATE",
        "live_trading_authorized": False
    }
    
    with open(GOV_REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
        
    md_content = f"""# AGY CLI GOVERNANCE AUDIT REPORT: CP-700 MULTI-REGIME EA

> [!IMPORTANT]
> **FINAL DECISION**: `NO_SAFE_TARGET_CANDIDATE`  
> **CLASSIFICATION**: `REJECTED_LOW_REAL_TICK_QUALITY`  
> **LIVE TRADING AUTHORITY**: **NOT GRANTED**

---

## 1. EVIDENCE LIFECYCLE & CRYPTOGRAPHIC HASHES

| Component | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **Governance Manifest** | [cp700_causal_multi_regime_v1.json](file:///{MANIFEST_PATH.replace('\\', '/')}) | `{manifest_hash}` |
| **MQL5 Source Code** | [ALAB_CP700_MultiRegimeEA.mq5](file:///{MQ5_PATH.replace('\\', '/')}) | `{mq5_hash}` |
| **Compiled Binary EX5** | [ALAB_CP700_MultiRegimeEA.ex5](file:///{EX5_PATH.replace('\\', '/')}) | `{ex5_hash}` |
| **INI Config File** | [generate_cp700_report.ini](file:///{INI_PATH.replace('\\', '/')}) | `{ini_hash}` |

---

## 2. NATIVE TESTER CONTRACT & REAL TICK METRICS

- **Terminal Process**: `C:\\Program Files\\XM Global MT5\\terminal64.exe`
- **Compiler Process**: `C:\\Program Files\\XM Global MT5\\metaeditor64.exe`
- **Tester Model**: `Model=4` (MT5 Real Ticks)
- **Symbol & Period**: `GOLD M15`
- **Window**: `2022.05.01 to 2026.07.27`
- **Ticks Processed**: `225,125,541 Ticks`
- **History Quality**: `63.0%` (Target: $\ge 99.0\%$)

---

## 3. MANDATORY TARGET GATES EVALUATION

| Mandatory Gate | Required Target | Observed Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **Net Profit** | `> $5,000.00 USD` | `$0.00 USD` | **FAILED** |
| **Profit Factor** | `>= 1.50` | `0.00` | **FAILED** |
| **Win Rate %** | `> 45.0%` | `0.00%` | **FAILED** |
| **Max Equity DD** | `<= 20.0%` | `0.00%` | **PASSED** |
| **History Quality** | `>= 99.0%` | `63.0%` | **FAILED** |
| **Model=4 Real Ticks** | `True` | `True` | **PASSED** |

---

## 4. SCIENTIFIC DIAGNOSIS & NEXT VALID RESEARCH STAGE

1. **History Quality Gate Violation**: The native MT5 server data for GOLD M15 from 2022 to 2026 exhibits only 63% history quality due to missing/discarded tick intervals. Under `AGY_CLI_NATIVE_MT5_DEVELOPMENT_PROTOCOL.md` Section 9, any dataset with history quality < 99% is strictly classified as diagnostic only and cannot be used for promotion.
2. **Conjunction Filter Overshoot**: The 7-layer conjunction filter (Quad H1 EMAs + M15 EMAs + BB breakout + RSI + wick ratio + 2 green bars) resulted in 0 trades over 225M real ticks.
3. **Next Valid Stage**: Shift to a cleaner native dataset (e.g. `US100Cash` / `US500Cash`) with confirmed $\ge 99\%$ history quality and test a preregistered two-sided causal architecture.

---
*Reported under AGY CLI Governance Standard. Backtests are research evidence, not a guarantee of future profit.*
"""
    with open(MD_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print("="*105)
    print(f"GOVERNANCE AUDIT REPORT CREATED: {MD_REPORT_PATH}")
    print("="*105)

if __name__ == '__main__':
    build_report()
