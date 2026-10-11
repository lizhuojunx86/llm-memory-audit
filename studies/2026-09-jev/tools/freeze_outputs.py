"""Hash the study outputs (runs, public_data, results) into freeze_outputs.json.

  python tools/freeze_outputs.py stamp --study jev
  python tools/freeze_outputs.py stamp --study leaderboard
  python tools/freeze_outputs.py check   --study jev

freeze.json covers protocol, code and inputs before the first model call; this tool
covers what the runs produced afterwards. stamp writes freeze_outputs.json in the
study dir with per-file size, sha256 and mtime, the sha256 of the study's freeze.json
so the two files are linked, and created_utc. It records no file contents. Private
files (raw model logs under runs/) are listed by relative name and hash only.

check rehashes and prints match / changed / missing per file; public files are always
checked, private ones only when present. Exit code 1 on any change or missing public
file. This tool never calls ots; the author stamps the JSON himself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

JEV_ROOT = Path(__file__).resolve().parents[1]
LB_ROOT = JEV_ROOT.parent / "2026-09-leaderboard"
STUDIES = {"jev": JEV_ROOT, "leaderboard": LB_ROOT}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _private_run_roots(study: str, root: Path) -> list[tuple[str, Path]]:
    """(label, dir) for every private runs directory this study reads."""
    if study == "jev":
        private = Path(os.environ.get("LMA_JEV_PRIVATE", str(root)))
        return [("runs", private / "runs")]
    lb = Path(os.environ.get("LMA_LB_PRIVATE", str(root)))
    add2 = Path(os.environ.get("LMA_ADD2_PRIVATE", str(root / "add2")))
    return [("runs", lb / "runs"), ("runs_local", lb / "runs_local"), ("add2/runs", add2 / "runs")]


def _collect_files(study: str, root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """(public, private) entries keyed by relative name with size/sha256/mtime."""
    public: dict[str, dict] = {}
    private: dict[str, dict] = {}
    for sub in ("public_data", "results"):
        base = root / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                rel = f"{sub}/{p.relative_to(base).as_posix()}"
                public[rel] = {"size": p.stat().st_size, "sha256": sha256_file(p), "mtime": p.stat().st_mtime}
    for label, base in _private_run_roots(study, root):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                rel = f"{label}/{p.relative_to(base).as_posix()}"
                private[rel] = {"size": p.stat().st_size, "sha256": sha256_file(p), "mtime": p.stat().st_mtime}
    return public, private


def stamp(study: str, root: Path) -> dict:
    public, private = _collect_files(study, root)
    files = {**public, **private}
    freeze = root / "freeze.json"
    out = {
        "created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "study": study,
        "freeze_json_sha256": sha256_file(freeze) if freeze.is_file() else None,
        "files": files,
    }
    (root / "freeze_outputs.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


def check(study: str, root: Path) -> int:
    """Rehash everything in freeze_outputs.json. Return exit code (0 = all match)."""
    fo = root / "freeze_outputs.json"
    if not fo.is_file():
        print(f"MISSING  freeze_outputs.json (run stamp first)")
        return 1
    recorded = json.loads(fo.read_text())
    files = recorded.get("files", {})
    n = {"match": 0, "changed": 0, "missing": 0, "skipped": 0}
    ok = True
    for rel, meta in sorted(files.items()):
        is_private = rel.startswith(("runs/", "runs_local/", "add2/runs/"))
        p = _resolve(rel, study, root)
        if p is None or not p.is_file():
            if is_private:
                n["skipped"] += 1
                print(f"{'skipped':9} {rel} (private, not present)")
                continue
            n["missing"] += 1
            ok = False
            print(f"{'missing':9} {rel}")
            continue
        if sha256_file(p) == meta["sha256"]:
            n["match"] += 1
            print(f"{'match':9} {rel}")
        else:
            n["changed"] += 1
            ok = False
            print(f"{'changed':9} {rel}")
    print(f"\n{n['match']} match, {n['changed']} changed, {n['missing']} missing, {n['skipped']} skipped (private absent)")
    return 0 if ok else 1


def _resolve(rel: str, study: str, root: Path) -> Path | None:
    if rel.startswith("runs/"):
        return _private_run_roots(study, root)[0][1] / rel[len("runs/"):]
    if rel.startswith("runs_local/"):
        for label, base in _private_run_roots(study, root):
            if label == "runs_local":
                return base / rel[len("runs_local/"):]
        return None
    if rel.startswith("add2/runs/"):
        for label, base in _private_run_roots(study, root):
            if label == "add2/runs":
                return base / rel[len("add2/runs/"):]
        return None
    return root / rel


def main() -> int:
    ap = argparse.ArgumentParser(description="Stamp or check the study output hashes (freeze_outputs.json).")
    ap.add_argument("cmd", choices=["stamp", "check"])
    ap.add_argument("--study", choices=sorted(STUDIES), required=True)
    ap.add_argument("--root", type=Path, default=None,
                    help=argparse.SUPPRESS)  # test hook; defaults to the published study dir
    a = ap.parse_args()
    root = a.root or STUDIES[a.study]
    if a.cmd == "stamp":
        out = stamp(a.study, root)
        print(f"freeze_outputs.json written: {len(out['files'])} files, "
              f"freeze.json sha256 {out['freeze_json_sha256']}")
        return 0
    return check(a.study, root)


if __name__ == "__main__":
    sys.exit(main())
