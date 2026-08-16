from __future__ import annotations

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_1_1"
REPORT = ROOT / "V3_7_1_1_UTC_BOUNDARY_REPRODUCTION_REPORT.md"
SOURCE = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30_CANONICAL_V2.source.json"
MANIFEST = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30_CANONICAL_V2.manifest.json"
DECISION = REPORT_DIR / "V3_7_1_1_REPRODUCTION_DECISION.json"
STRUCTURAL = REPORT_DIR / "GOLD_M30_CANONICAL_V2.structural_audit.json"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def generate():
    source = load(SOURCE)
    manifest = load(MANIFEST)
    decision = load(DECISION)
    structural = load(STRUCTURAL)
    terminal = source.get("terminal_metadata_non_sensitive", {})
    coverage = structural.get("coverage", {})
    text = f"""# V3.7.1.1 UTC-BOUNDARY CANONICAL REPRODUCTION REPORT

- Artifact-generation parent SHA: `{head()}`
- Dataset: `{manifest.get('dataset_id')}`
- Path: `{manifest.get('relative_path')}`
- SHA-256: `{manifest.get('sha256')}`
- Rows: `{manifest.get('row_count')}`
- First bar open UTC: `{manifest.get('first_bar_open_utc')}`
- Last bar open UTC: `{manifest.get('last_bar_open_utc')}`
- Timestamp semantic: `{manifest.get('timestamp_semantic')}`
- Timezone: `{manifest.get('timestamp_timezone_status')} / {manifest.get('timestamp_timezone')}`
- Request-boundary representation: `{decision.get('request_boundary_representation')}`
- Lineage: `{manifest.get('lineage_status')}`
- Structural validation: `{manifest.get('structural_validation_status')}`
- Coverage: `{manifest.get('coverage_status')}`
- Research eligibility: `{manifest.get('research_eligibility')}`
- Reproduction status: **`{decision.get('canonical_v2_status')}`**

## V3.7.1 byte concordance

- V3.7.1 frozen SHA: `{decision.get('v3_7_1_frozen_sha256')}`
- V3.7.1 file SHA at reproduction: `{decision.get('v3_7_1_file_sha256_at_reproduction')}`
- Result: **`{decision.get('byte_concordance_with_v3_7_1')}`**

Byte identity, if observed, does not erase the V3.7.1 request-boundary provenance defect. It only shows whether the repair changed returned CSV bytes under this terminal state.

## Terminal history limit

- Terminal maxbars: `{terminal.get('maxbars')}`
- Requested start UTC: `{source.get('requested_start_utc')}`
- Returned first bar UTC: `{source.get('returned_first_bar_open_utc')}`
- Coverage required first bar no later than: `{coverage.get('required_first_bar_no_later_than')}`

The report does not claim complete history back to the requested start if terminal history is capped.

## Scientific conclusion

> **{decision.get('canonical_v2_status')}**

No strategy research is started by this reproduction.
"""
    REPORT.write_text(text, encoding="utf-8")
    return str(REPORT)


if __name__ == "__main__":
    print(generate())
