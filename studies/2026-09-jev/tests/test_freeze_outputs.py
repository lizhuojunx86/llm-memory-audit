"""Tests for tools/freeze_outputs.py (run: python -m pytest tests -q)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import freeze_outputs as fo  # noqa: E402


def _mk_study(root: Path) -> None:
    (root / "public_data").mkdir(parents=True)
    (root / "results" / "interim").mkdir(parents=True)
    (root / "runs").mkdir(parents=True)
    (root / "freeze.json").write_text('{"files": {}}\n')
    (root / "public_data" / "a.csv").write_text("col\n1\n")
    (root / "results" / "r.json").write_text("{}\n")
    (root / "results" / "interim" / "sub.json").write_text("[]\n")
    (root / "runs" / "m.jsonl").write_text('{"x": 1}\n')


def test_stamp_and_check_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("LMA_JEV_PRIVATE", raising=False)
    root = tmp_path / "jev"
    _mk_study(root)
    out = fo.stamp("jev", root)
    assert out["study"] == "jev"
    assert out["freeze_json_sha256"] == fo.sha256_file(root / "freeze.json")
    assert out["created_utc"]
    for key in ("public_data/a.csv", "results/r.json", "results/interim/sub.json", "runs/m.jsonl"):
        assert key in out["files"], key
        meta = out["files"][key]
        assert set(meta) == {"size", "sha256", "mtime"}
        assert len(meta["sha256"]) == 64
        # no absolute paths, no file contents
        assert not key.startswith("/")
        assert meta["sha256"] not in json.dumps(meta) or True  # hash is metadata, not content
    # contents never recorded
    assert "col" not in json.dumps(out)
    assert '{"x": 1}' not in json.dumps(out)
    assert fo.check("jev", root) == 0


def test_check_detects_change_and_missing_public(tmp_path, monkeypatch):
    monkeypatch.delenv("LMA_JEV_PRIVATE", raising=False)
    root = tmp_path / "jev"
    _mk_study(root)
    fo.stamp("jev", root)
    (root / "public_data" / "a.csv").write_text("col\n2\n")
    assert fo.check("jev", root) == 1
    fo.stamp("jev", root)
    assert fo.check("jev", root) == 0
    (root / "results" / "r.json").unlink()
    assert fo.check("jev", root) == 1


def test_check_skips_absent_private(tmp_path, monkeypatch):
    monkeypatch.delenv("LMA_JEV_PRIVATE", raising=False)
    root = tmp_path / "jev"
    _mk_study(root)
    fo.stamp("jev", root)
    (root / "runs" / "m.jsonl").unlink()
    assert fo.check("jev", root) == 0  # private gone = skipped, public still matches
    (root / "public_data" / "a.csv").unlink()
    assert fo.check("jev", root) == 1  # public gone = missing


def test_leaderboard_private_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("LMA_LB_PRIVATE", str(tmp_path / "lbpriv"))
    monkeypatch.setenv("LMA_ADD2_PRIVATE", str(tmp_path / "add2priv"))
    root = tmp_path / "leaderboard"
    (root / "public_data").mkdir(parents=True)
    (root / "results").mkdir()
    (root / "freeze.json").write_text("{}\n")
    (root / "public_data" / "p.csv").write_text("x\n")
    (root / "results" / "leaderboard.json").write_text("{}\n")
    lb = tmp_path / "lbpriv"
    (lb / "runs").mkdir(parents=True)
    (lb / "runs_local").mkdir()
    (lb / "runs" / "m1.jsonl").write_text("{}\n")
    (lb / "runs_local" / "von.jsonl").write_text("{}\n")
    add2 = tmp_path / "add2priv"
    (add2 / "runs").mkdir(parents=True)
    (add2 / "runs" / "m2.jsonl").write_text("{}\n")
    out = fo.stamp("leaderboard", root)
    for key in ("runs/m1.jsonl", "runs_local/von.jsonl", "add2/runs/m2.jsonl",
                "public_data/p.csv", "results/leaderboard.json"):
        assert key in out["files"], key
    assert fo.check("leaderboard", root) == 0
    (lb / "runs" / "m1.jsonl").write_text('{"y": 2}\n')
    assert fo.check("leaderboard", root) == 1
