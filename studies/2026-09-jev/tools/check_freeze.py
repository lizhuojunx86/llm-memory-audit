"""Check this study's published files against freeze.json.

  python tools/check_freeze.py

freeze.json was written, and timestamped with OpenTimestamps, before any study
request was sent to any model. This script
  1. confirms that freeze.json.ots commits to this exact freeze.json, and
  2. rehashes every file listed in freeze.json that is published here.
Files withheld under the FMP licence are listed as withheld. src/run_models.py
changed after the freeze (DEVIATIONS.md, D2); its frozen original is
frozen_code/run_models.py, which is checked against the frozen hash instead.
Exit code 0 when everything published matches.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
OP_SHA256 = 0x08


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ots_file_digest(p: Path) -> str | None:
    """The file digest a detached .ots proof commits to (header, version, op, digest)."""
    b = p.read_bytes()
    if not b.startswith(OTS_MAGIC):
        return None
    i = len(OTS_MAGIC) + 1  # skip the major version byte
    if b[i] != OP_SHA256:
        return None
    return b[i + 1:i + 33].hex()


def main() -> int:
    ok = True
    fz = ROOT / "freeze.json"
    committed = ots_file_digest(ROOT / "freeze.json.ots")
    same = committed == sha256_file(fz)
    ok &= same
    print(f"{'match' if same else 'MISMATCH':9} freeze.json.ots commits to sha256 {committed}")
    files = json.loads(fz.read_text())["files"]
    n = {"match": 0, "changed": 0, "withheld": 0}
    for rel, frozen in sorted(files.items()):
        p = ROOT / rel
        if "**" in rel or not p.is_file():
            n["withheld"] += 1
            print(f"{'withheld':9} {rel}")
            continue
        if sha256_file(p) == frozen:
            n["match"] += 1
            print(f"{'match':9} {rel}")
            continue
        orig = ROOT / "frozen_code" / p.name
        if orig.is_file() and sha256_file(orig) == frozen:
            n["changed"] += 1
            print(f"{'changed':9} {rel} (after the freeze, see DEVIATIONS.md; frozen_code/{p.name} matches)")
            continue
        ok = False
        print(f"{'MISMATCH':9} {rel}")
    print(f"\n{n['match']} match, {n['changed']} changed after the freeze with its frozen copy matching, "
          f"{n['withheld']} withheld (FMP licence)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
