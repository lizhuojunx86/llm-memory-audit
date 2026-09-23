"""Freeze the protocol: hash PREREG.md, the code and every study input, then timestamp.

  python src/freeze.py            # writes freeze.json (refuses to overwrite)
  ots stamp freeze.json           # OpenTimestamps proof -> freeze.json.ots (run right after)

run_models.py refuses to send anything unless freeze.json matches work/requests.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, jsonl_read, sha256_file, utc_now  # noqa: E402

FILES = [
    "PREREG.md",
    "src/common.py", "src/payloads.py", "src/fmp_pull.py", "src/build_events.py",
    "src/run_models.py", "src/analyze.py", "src/freeze.py", "src/smoke.py",
    "tests/test_stats.py", "tests/test_e2e.py",
    "data/universe.json",
    "work/events.jsonl", "work/prospective.jsonl", "work/requests.jsonl", "work/manifest.json",
    "preflight/smoke.jsonl", "data/fetch_log.jsonl",
]


def main() -> None:
    out = ROOT / "freeze.json"
    if out.exists():
        raise SystemExit("freeze.json already exists; a new protocol version needs a new folder or a DEVIATIONS.md entry")
    runs = list((ROOT / "runs").glob("*.jsonl")) if (ROOT / "runs").exists() else []
    study_sent = sum(1 for p in runs for _ in jsonl_read(p))
    if study_sent:
        raise SystemExit(f"runs/ already holds {study_sent} records; freezing now would be after data collection")
    files = {f: sha256_file(ROOT / f) for f in FILES}
    lines = [f"{p.relative_to(ROOT).as_posix()}:{sha256_file(p)}"
             for p in sorted((ROOT / "data" / "fmp").rglob("*.json.gz"))]
    files["data/fmp/** (sha256 of sorted path:sha256 lines)"] = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    files["data/fmp/** file count"] = str(len(lines))
    manifest = json.loads((ROOT / "work/manifest.json").read_text())
    rec = {
        "frozen_utc": utc_now(),
        "protocol_version": "1.0",
        "files": files,
        "manifest_counts": {k: manifest[k] for k in ("events", "events_by_period", "balanced_panel_tickers",
                                                      "prospective_events", "requests_by_model")},
        "note": "No study event had been sent to any model when this file was written.",
    }
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps(rec, indent=1, sort_keys=True))
    try:
        r = subprocess.run(["ots", "stamp", str(out)], capture_output=True, text=True, timeout=120)
        print("ots:", r.returncode, r.stdout.strip(), r.stderr.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"ots not run ({type(e).__name__}); run `ots stamp freeze.json` manually")


if __name__ == "__main__":
    main()
