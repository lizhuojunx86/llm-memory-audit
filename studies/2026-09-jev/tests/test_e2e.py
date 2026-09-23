"""End-to-end check of analyze.run on synthetic events and fake model outputs."""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analyze  # noqa: E402
from common import JEV_PIN, PERIODS  # noqa: E402

SEASON_MONTHS = {1: 2, 2: 5, 3: 8, 4: 11}


def _period(year, month):
    d = dt.date(year, month, 10)
    for name, lo, hi in PERIODS:
        if lo <= d <= hi:
            return name
    return None


def _write(tmp, memory: float, seed: int, served=JEV_PIN):
    rng = np.random.default_rng(seed)
    work, runs = tmp / "work", tmp / "runs"
    work.mkdir()
    runs.mkdir()
    events, recs = [], []
    for t in range(220):
        prior = rng.normal(0, 0.8)
        for year in (2023, 2024, 2025, 2026):
            for season, month in SEASON_MONTHS.items():
                per = _period(year, month)
                if per is None:
                    continue
                date = f"{year}-{month:02d}-10"
                eid = f"T{t}|{date}"
                y = {k: int(rng.random() < 1 / (1 + np.exp(-prior))) for k in ("y_beat", "y_react", "y_drift")}
                events.append({"event_id": eid, "ticker": f"T{t}", "period": per, "sp500": t < 110,
                               "sector": ["Tech", "Health", "Energy"][t % 3], "date": date, "year": year,
                               "season": season, "month": date[:7], "eps_surp_pct": 5.0,
                               "in_S": t < 120, "in_R": t % 20 == 0 and season == 1, **y})
                mem = memory if year in (2023, 2024) else 0.0

                def p(yv, extra=0.0):
                    return float(1 / (1 + np.exp(-(prior + (mem + extra) * (2 * yv - 1) + rng.normal(0, 0.7)))))
                reps = 3 if (t % 20 == 0 and season == 1) else 1
                for k in range(reps):
                    recs.append({"request_id": f"jev|K|{eid}|r{k}", "model_key": "jev", "arm": "K",
                                 "event_id": eid, "repeat": k, "http_status": 200, "served_model": served,
                                 "sent_utc": "2026-09-23T04:00:00.000000Z",
                                 "response": {"answers": {q: {"type": "noul", "noul": p(y[lab])}
                                                          for q, lab in (("k1_beat", "y_beat"), ("k2_react", "y_react"),
                                                                         ("k3_drift", "y_drift"))}}})
                base = prior + rng.normal(0, 1)
                for arm, extra in (("N", mem), ("A", 0.0)):
                    ans = {q: {"type": "noul",
                               "noul": float(1 / (1 + np.exp(-(base + extra * (2 * y[lab] - 1)))))}
                           for q, lab in (("r2_react", "y_react"), ("r3_drift", "y_drift"))}
                    recs.append({"request_id": f"jev|{arm}|{eid}|r0", "model_key": "jev", "arm": arm,
                                 "event_id": eid, "repeat": 0, "http_status": 200, "served_model": served,
                                 "sent_utc": "2026-09-23T04:00:01.000000Z", "response": {"answers": ans}})
                if t < 120:
                    known = year in (2023, 2024)
                    content = {"k1_beat": (0.9 if y["y_beat"] else 0.2) if known else 0.6,
                               "k2_react": 0.5, "k3_drift": 0.5}
                    recs.append({"request_id": f"sonnet5|K|{eid}|r0", "model_key": "sonnet5", "arm": "K",
                                 "event_id": eid, "repeat": 0, "http_status": 200, "served_model": "s",
                                 "sent_utc": "2026-09-23T05:00:00.000000Z", "content": json.dumps(content)})
    (work / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    for mk in ("jev", "sonnet5"):
        (runs / f"{mk}.jsonl").write_text("\n".join(json.dumps(r) for r in recs if r["model_key"] == mk) + "\n")
    return work, runs


def _run(tmp_path, monkeypatch, **kw):
    work, runs = _write(tmp_path, **kw)
    monkeypatch.setattr(analyze, "WORK", work)
    monkeypatch.setattr(analyze, "RUNS", runs)
    return analyze.run(B=300)


def test_e2e_memory(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch, memory=0.9, seed=1)
    assert res["decision"]["verdict"] == "leakage_detected"
    assert res["controls"]["probe_valid"] is True
    assert res["secondary"]["S5_repeatability"]["k1_beat"]["events"] > 0
    assert "Primary" in analyze.md_table(res)


def test_e2e_priors_only_no_false_alarm(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch, memory=0.0, seed=2)
    assert res["decision"]["verdict"] == "no_detectable_leakage_provisional"


def test_e2e_version_change_forces_rerun(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch, memory=0.0, seed=3, served="typesafe/jev-1.14-20261001")
    assert res["decision"]["verdict"] == "rerun_required_model_changed"
