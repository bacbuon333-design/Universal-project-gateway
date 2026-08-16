"""Generate the V3.7.2 compatibility report from committed machine artifacts."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_2"
REPORT = ROOT / "V3_7_2_CANONICAL_ENGINE_COMPATIBILITY_REPORT.md"
SOURCE = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30_CANONICAL.source.json"


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def pct(v):
    return "N/A" if v is None else f"{100.0 * float(v):.6f}%"


def generate() -> str:
    snapshot = load(OUT_DIR / "canonical_engine_snapshot.json")
    concordance = load(OUT_DIR / "legacy_canonical_concordance.json")
    decision = load(OUT_DIR / "V3_7_2_ENGINE_COMPATIBILITY_DECISION.json")
    source = load(SOURCE)
    parent = head()

    checks = "\n".join(
        f"- `{k}`: **{'PASS' if v else 'FAIL'}**"
        for k, v in decision["compatibility_checks"].items()
    )

    def view(name, obj):
        return (
            f"- {name}: overlap `{obj['overlap_rows']}`; "
            f"all-OHLC exact match `{pct(obj.get('all_ohlc_exact_match_rate'))}`"
        )

    terminal = source.get("terminal_metadata_non_sensitive", {})
    requested_start = source.get("requested_start_utc")
    returned_first = source.get("returned_first_bar_open_utc")

    text = f"""# V3.7.2 CANONICAL ENGINE COMPATIBILITY REPORT

- Artifact-generation parent SHA: `{parent}`
- Canonical dataset SHA-256: `{snapshot['dataset_sha256']}`
- Canonical row count: `{snapshot['row_count']}`
- First parsed engine datetime: `{snapshot['first_datetime']}`
- Last parsed engine datetime: `{snapshot['last_datetime']}`
- Parsed timezone: `{snapshot['timezone']}`
- Instrument spec: `{snapshot['instrument_symbol']} / {snapshot['instrument_asset_class']}`
- Final status: **`{decision['status']}`**
- Strategy executed: **`{decision['strategy_executed']}`**

## Compatibility checks

{checks}

## Legacy/canonical empirical concordance

{view('Same label', concordance['same_label'])}
{view('Canonical +30m matched to legacy', concordance['canonical_plus_30m_to_legacy'])}
{view('Canonical -30m matched to legacy', concordance['canonical_minus_30m_to_legacy'])}

This concordance is descriptive only. The legacy dataset remains `BLOCKED`; no empirical match retroactively proves its exporter or source lineage.

## Terminal-history boundary note

- MT5 terminal `maxbars`: `{terminal.get('maxbars', 'UNAVAILABLE')}`
- Requested canonical start: `{requested_start}`
- Returned first canonical bar: `{returned_first}`

The canonical export contains exactly the terminal-available history. V3.7.1 coverage passed because the returned history begins before the frozen research boundary 2018Q2. This does **not** claim that the terminal supplied every requested bar back to 2018-01-01.

## Scientific conclusion

> **{decision['status']}**

A PASS authorizes the canonical dataset/adapter interface for a future independently precommitted research chapter. It does not validate any legacy strategy result and does not create H-221.

## Stop rule

No strategy, signal, event-study optimization, or candidate promotion is executed in V3.7.2.
"""
    REPORT.write_text(text, encoding="utf-8")
    return str(REPORT)


if __name__ == "__main__":
    print(generate())
