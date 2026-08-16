"""Machine-generated V3.7.2 V2 canonical engine compatibility report."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_2_v2"
REPORT_PATH = ROOT / "V3_7_2_V2_CANONICAL_ENGINE_COMPATIBILITY_REPORT.md"


def load_json(name: str):
    with (OUT_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def pct(x):
    return "N/A" if x is None else f"{100.0 * float(x):.6f}%"


def main() -> None:
    snap = load_json("canonical_v2_engine_snapshot.json")
    conc = load_json("legacy_canonical_v2_concordance.json")
    dec = load_json("V3_7_2_V2_ENGINE_COMPATIBILITY_DECISION.json")
    parent = git_head()

    checks = "\n".join(f"- {k}: `{'PASS' if v else 'FAIL'}`" for k, v in dec["compatibility_checks"].items())

    def view(label, obj):
        return (
            f"### {label}\n\n"
            f"- Shift minutes: `{obj['shift_minutes_applied_to_canonical_label']}`\n"
            f"- Overlap rows: `{obj['overlap_rows']}`\n"
            f"- All-OHLC exact-match rate: `{pct(obj.get('all_ohlc_exact_match_rate'))}`\n"
        )

    report = f"""# V3.7.2 V2 CANONICAL ENGINE COMPATIBILITY REPORT

- Artifact-generation parent SHA: `{parent}`
- Canonical dataset: `{snap['dataset_id']}`
- SHA-256: `{snap['dataset_sha256']}`
- Rows: `{snap['row_count']}`
- First parsed datetime: `{snap['first_datetime']}`
- Last parsed datetime: `{snap['last_datetime']}`
- Parsed timezone: `{snap['timezone']}`
- Timestamp semantic: `{snap['timestamp_semantic']}`
- Request boundary: `{snap['request_boundary_representation']}`
- Instrument: `{snap['instrument_symbol']} / {snap['instrument_asset_class']}`
- Strategy executed: `{dec['strategy_executed']}`
- Final status: **`{dec['status']}`**

## Compatibility checks

{checks}

## Legacy/canonical empirical concordance

Legacy research eligibility remains: **`{conc['legacy_research_eligibility_remains']}`**.

- Canonical labels missing in legacy inside common range: `{conc['canonical_labels_missing_in_legacy_within_common_range']}`
- Legacy labels missing in canonical inside common range: `{conc['legacy_labels_missing_in_canonical_within_common_range']}`

{view('Same label', conc['same_label'])}
{view('Canonical +30m to legacy', conc['canonical_plus_30m_to_legacy'])}
{view('Canonical -30m to legacy', conc['canonical_minus_30m_to_legacy'])}

## Interpretation boundary

Concordance is descriptive only. It does not retroactively prove the legacy file's source, timezone, or bar-label semantics, and does not change legacy status `BLOCKED`.

## Scientific conclusion

> **{dec['status']}**

A PASS authorizes the V2 canonical dataset/engine interface for a future independently precommitted research chapter. It does not validate prior strategies or authorize strategy execution inside V3.7.2.

## Stop rule

No strategy, H-221, LMDC rerun, parameter tuning, or new mechanism batch is executed by this report.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
