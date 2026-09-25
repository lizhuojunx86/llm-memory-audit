"""Check this leaderboard's published files against freeze.json and freeze_clones.json.

  python tools/check_freeze_lb.py

1. Confirms each .ots proof commits to its freeze file.
2. Rehashes every published file the freeze files list (work/requests.jsonl is published gzipped and
   is decompressed before hashing). Files that stay private (the FMP-derived events file) are listed as
   withheld. Paths starting with ../jev-lookahead/ refer to the sibling study folder 2026-09-jev.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JEV = ROOT.parent / "2026-09-jev"
MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ots_digest(p: Path):
    b = p.read_bytes()
    if not b.startswith(MAGIC) or b[len(MAGIC) + 1] != 0x08:
        return None
    i = len(MAGIC) + 2
    return b[i:i + 32].hex()


def resolve(rel: str):
    if rel.startswith("../jev-lookahead/"):
        p = JEV / rel[len("../jev-lookahead/"):]
    else:
        p = ROOT / rel
    if p.is_file():
        return p.read_bytes()
    gz = p.with_name(p.name + ".gz")
    if gz.is_file():
        return gzip.decompress(gz.read_bytes())
    return None


def main() -> int:
    ok = True
    for fz_name, sub in (("freeze.json", ""), ("freeze.json", "add2/"), ("freeze_clones.json", "clones/")):
        fz = ROOT / sub / fz_name
        if not fz.is_file():
            continue
        same = ots_digest(fz.with_name(fz.name + ".ots")) == sha(fz.read_bytes())
        ok &= same
        print(f"{'match' if same else 'MISMATCH':9} {sub}{fz_name}.ots commits to {sub}{fz_name}")
        for rel, digest in sorted(json.loads(fz.read_text())["files"].items()):
            if rel.startswith("studies/2026-09-jev/"):
                data = resolve("../jev-lookahead/" + rel[len("studies/2026-09-jev/"):])
            else:
                data = resolve(sub + rel if not rel.startswith("../") else rel)
            if data is None:
                print(f"{'withheld':9} {rel}")
                continue
            m = sha(data) == digest
            ok &= m
            print(f"{'match' if m else 'MISMATCH':9} {rel}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
