from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATES = [
    ROOT / "GOLD_M30.csv",
    ROOT / "AlphaLab_Antigravity" / "GOLD_M30.csv",
    ROOT / "AlphaLab_Antigravity" / "data" / "GOLD_M30.csv",
    ROOT / "data" / "GOLD_M30.csv",
]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_6_1"

# Strong evidence must refer to semantics, not merely 30-minute cadence.
OPEN_PATTERNS = [
    re.compile(r"bar\s*open\s*time", re.I),
    re.compile(r"timestamp.{0,80}open\s*time", re.I),
    re.compile(r"MqlRates.{0,120}\btime\b.{0,120}open", re.I | re.S),
    re.compile(r"copy_rates|copyrates", re.I),
]
CLOSE_PATTERNS = [
    re.compile(r"bar\s*close\s*time", re.I),
    re.compile(r"timestamp.{0,80}close\s*time", re.I),
    re.compile(r"timestamp\s*=\s*.*close", re.I),
]

TEXT_EXTS = {".py", ".md", ".txt", ".mq5", ".mqh", ".json", ".yaml", ".yml", ".toml"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "reports"}


def find_data_file() -> Path:
    for p in DATA_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("GOLD_M30.csv not found in expected locations")


def dataset_facts(path: Path) -> Dict:
    df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}
    dt_col = cols.get("datetime_str") or cols.get("datetime") or cols.get("time") or cols.get("timestamp")
    if dt_col is None:
        raise ValueError("No recognizable timestamp column in GOLD_M30.csv")
    dt = pd.to_datetime(df[dt_col], errors="coerce").dropna().sort_values().reset_index(drop=True)
    if len(dt) < 3:
        raise ValueError("Insufficient timestamp rows")
    deltas = dt.diff().dropna().dt.total_seconds() / 60.0
    return {
        "path": str(path.relative_to(ROOT)),
        "timestamp_column": dt_col,
        "row_count": int(len(df)),
        "first_timestamp": str(dt.iloc[0]),
        "last_timestamp": str(dt.iloc[-1]),
        "median_delta_minutes": float(deltas.median()),
        "pct_30m_deltas": float((deltas == 30.0).mean() * 100.0),
        "note": "Cadence confirms M30 spacing but does NOT prove whether timestamps denote bar open or bar close.",
    }


def iter_text_files() -> List[Path]:
    files: List[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        # Do not use V3.6/V3.6.1 result prose as source-of-truth for dataset semantics.
        if p.name.startswith("V3_6") or "v3_6" in p.as_posix().lower():
            continue
        files.append(p)
    return files


def scan_semantic_evidence() -> Dict:
    open_hits = []
    close_hits = []
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Keep short excerpts around actual matched text.
        for label, patterns, sink in [
            ("BAR_OPEN_TIME", OPEN_PATTERNS, open_hits),
            ("BAR_CLOSE_TIME", CLOSE_PATTERNS, close_hits),
        ]:
            for pattern in patterns:
                for m in pattern.finditer(text):
                    start = max(0, m.start() - 180)
                    end = min(len(text), m.end() + 220)
                    excerpt = " ".join(text[start:end].split())
                    sink.append({
                        "semantic": label,
                        "file": str(path.relative_to(ROOT)),
                        "pattern": pattern.pattern,
                        "excerpt": excerpt[:600],
                    })
                    if len(sink) >= 30:
                        break
                if len(sink) >= 30:
                    break
    return {"open_time_hits": open_hits, "close_time_hits": close_hits}


def classify(evidence: Dict) -> Dict:
    open_hits = evidence["open_time_hits"]
    close_hits = evidence["close_time_hits"]

    # A mere CopyRates mention is useful evidence, but not automatically conclusive unless
    # the excerpt ties exported timestamp to MT5/MqlRates time semantics. Human executor may
    # promote a hit only with source-level proof. This script remains conservative.
    explicit_open = [h for h in open_hits if "bar open time" in h["excerpt"].lower() or "timestamp" in h["excerpt"].lower() and "open time" in h["excerpt"].lower()]
    explicit_close = [h for h in close_hits if "bar close time" in h["excerpt"].lower() or "timestamp" in h["excerpt"].lower() and "close time" in h["excerpt"].lower()]

    if explicit_open and not explicit_close:
        status = "BAR_OPEN_TIME_PROVEN"
        semantic = "BAR_OPEN_TIME"
        confidence = "HIGH"
    elif explicit_close and not explicit_open:
        status = "BAR_CLOSE_TIME_PROVEN"
        semantic = "BAR_CLOSE_TIME"
        confidence = "HIGH"
    else:
        status = "TIMESTAMP_SEMANTICS_AMBIGUOUS"
        semantic = "UNRESOLVED"
        confidence = "INSUFFICIENT"

    return {
        "status": status,
        "semantic": semantic,
        "confidence": confidence,
        "explicit_open_evidence_count": len(explicit_open),
        "explicit_close_evidence_count": len(explicit_close),
        "decision_rule": "Do not infer open-vs-close semantics from M30 cadence alone. Require explicit source/export/documentation evidence.",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data_path = find_data_file()
    facts = dataset_facts(data_path)
    evidence = scan_semantic_evidence()
    decision = classify(evidence)
    result = {
        "audit": "V3.6.1 LMDC timestamp semantics",
        "dataset": facts,
        "decision": decision,
        "evidence": evidence,
        "allowed_next_action": (
            "EXACT_REPRODUCTION_WITH_TIMESTAMP_ALIGNMENT_ONLY"
            if decision["semantic"] == "BAR_OPEN_TIME"
            else "CORRECT_FROZEN_VERDICT_ONLY"
            if decision["semantic"] == "BAR_CLOSE_TIME"
            else "STOP_WITH_TIMESTAMP_AMBIGUITY"
        ),
    }
    out = OUT_DIR / "timestamp_semantics_audit.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
