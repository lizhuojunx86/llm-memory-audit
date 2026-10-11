"""Tie-policy tests for the within-company statistic (run: python -m pytest tests -q).

The frozen default (demeaned) scores a raw tie by the two month means. These tests
check that the additive policies raw_tie_half and raw keep a null null, and that
demeaned still reproduces its existing numbers on a fixed fixture.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import (TIE_POLICIES, demean_by_month, wt_auc_test, wt_parts,  # noqa: E402
                     _pair_ok_pre, _pair_ok_pre_same_q, _raw_of)


def test_raw_of_strips_dm_suffix():
    assert _raw_of("s_dm") == "s"
    assert _raw_of("sN_dm") == "sN"
    assert _raw_of("s") == "s"


def test_two_event_equal_raw_scores_different_months():
    """Equal raw scores in different months: demeaned lets the month means decide,
    the other two policies call it a tie."""
    rows = [
        # the informative pair: same ticker, same season, 2023 vs 2024, opposite labels
        {"ticker": "T", "year": 2023, "season": 2, "y": 1, "s": 0.7, "month": "2023-05"},
        {"ticker": "T", "year": 2024, "season": 2, "y": 0, "s": 0.7, "month": "2024-05"},
        # filler that sets different month means without forming pairs with T
        {"ticker": "F1", "year": 2023, "season": 2, "y": 1, "s": 0.3, "month": "2023-05"},
        {"ticker": "F2", "year": 2024, "season": 2, "y": 1, "s": 0.9, "month": "2024-05"},
    ]
    demean_by_month(rows, ("s",))
    # 2023-05 mean 0.5 -> T2023 s_dm=0.2; 2024-05 mean 0.8 -> T2024 s_dm=-0.1
    # positive is T2023, so demeaned scores it higher: 1.0
    ticks, num, den = wt_parts(rows, ("s_dm",), _pair_ok_pre, ties="demeaned")
    assert ticks == ["T"] and den[0] == 1.0 and num[0, 0] == 1.0
    for policy, expected in (("raw_tie_half", 0.5), ("raw", 0.5)):
        ticks, num, den = wt_parts(rows, ("s_dm",), _pair_ok_pre, ties=policy)
        assert ticks == ["T"] and den[0] == 1.0 and num[0, 0] == expected, policy


def test_demeaned_reproduces_existing_numbers():
    """ties='demeaned' must equal the original pairwise arithmetic on a fixed fixture."""
    rows = [
        {"ticker": "A", "year": 2023, "season": 2, "y": 1, "s": 0.8, "month": "2023-05"},
        {"ticker": "A", "year": 2024, "season": 2, "y": 0, "s": 0.6, "month": "2024-05"},
        {"ticker": "B", "year": 2023, "season": 1, "y": 1, "s": 0.4, "month": "2023-02"},
        {"ticker": "B", "year": 2024, "season": 1, "y": 0, "s": 0.4, "month": "2024-02"},
        {"ticker": "C", "year": 2023, "season": 3, "y": 0, "s": 0.9, "month": "2023-08"},
        {"ticker": "C", "year": 2024, "season": 3, "y": 1, "s": 0.1, "month": "2024-08"},
        {"ticker": "X", "year": 2023, "season": 2, "y": 1, "s": 0.1, "month": "2023-05"},
        {"ticker": "X", "year": 2024, "season": 2, "y": 0, "s": 0.9, "month": "2024-05"},
    ]
    demean_by_month(rows, ("s",))
    # Month means: 2023-05 = 0.45, 2024-05 = 0.75; single-event months mean the score itself.
    # A pair: pos A2023 (s_dm=0.35) vs neg A2024 (s_dm=-0.15) -> 1.0
    # X pair: pos X2023 (s_dm=-0.35) vs neg X2024 (s_dm=0.15) -> 0.0
    # B and C pairs: s_dm 0 on both sides -> 0.5 each
    # demeaned AUC = (1 + 0 + 0.5 + 0.5) / 4 = 0.5
    r_default = wt_auc_test(rows, "s_dm", _pair_ok_pre, B=100, seed=1)
    r_explicit = wt_auc_test(rows, "s_dm", _pair_ok_pre, B=100, seed=1, ties="demeaned")
    assert r_default["estimate"] == r_explicit["estimate"] == 0.5
    assert r_default["pairs"] == r_explicit["pairs"] == 4
    # raw: A 1.0, X 0.0, B tie 0.5, C pos C2024 s=0.1 vs neg C2023 s=0.9 -> 0.0  => 0.375
    r_raw = wt_auc_test(rows, "s_dm", _pair_ok_pre, B=100, seed=1, ties="raw")
    assert r_raw["estimate"] == 0.375


def test_null_grid_ties_raw_policies_calibrated():
    """Null world: coarse-grid scores (many ties), independent of the label; the label
    base rate drifts between the two paired years. raw_tie_half and raw must stay
    within bootstrap noise of 0.5. demeaned is printed for the record (it can deviate
    because raw ties are broken by the month means rather than left undecided)."""
    rng = np.random.default_rng(20261011)
    grid = 0.05
    rows = []
    for t in range(300):
        for year, base in ((2023, 0.35), (2024, 0.65)):
            for season in (1, 2, 3, 4):
                month = f"{year}-{3 * season - 1:02d}"
                y = int(rng.random() < base)
                # score independent of the label and the year: a pure null on a coarse grid
                s = round(float(rng.integers(2, 19)) * grid, 2)   # {0.10 .. 0.90}
                rows.append({"s": s, "y": y, "ticker": f"T{t}",
                             "year": year, "season": season, "month": month, "q": "k1_beat"})
    demean_by_month(rows, ("s",))
    results = {}
    for policy in TIE_POLICIES:
        r = wt_auc_test(rows, "s_dm", _pair_ok_pre_same_q, B=400, seed=7, ties=policy)
        results[policy] = r
    print(f"\nnull grid-world demeaned = {results['demeaned']['estimate']} "
          f"({results['demeaned']['ci95']}), raw_tie_half = {results['raw_tie_half']['estimate']}, "
          f"raw = {results['raw']['estimate']}")
    for policy in ("raw_tie_half", "raw"):
        r = results[policy]
        assert r["estimate"] is not None and r["pairs"] > 100
        # within bootstrap noise of 0.5: |est - 0.5| <= 2 * boot_sd (loose) and one-sided p not tiny
        assert abs(r["estimate"] - 0.5) <= 2 * r["boot_sd"] + 0.01, (policy, r)
        assert r["p_one_sided"] > 0.005, (policy, r)


def test_ties_policy_rejected_when_unknown():
    rows = [{"ticker": "T", "year": 2023, "season": 1, "y": 1, "s": 0.5, "s_dm": 0.1, "month": "2023-02"},
            {"ticker": "T", "year": 2024, "season": 1, "y": 0, "s": 0.5, "s_dm": -0.1, "month": "2024-02"}]
    try:
        wt_parts(rows, ("s_dm",), _pair_ok_pre, ties="bogus")
    except ValueError as e:
        assert "ties" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_run_ties_output_shape(tmp_path, monkeypatch):
    """run() with a non-default policy records it and adds the posthoc block;
    the default leaves the output shape unchanged."""
    import json
    import analyze
    work, runs = tmp_path / "work", tmp_path / "runs"
    work.mkdir(); runs.mkdir()
    events, recs = [], []
    for t in range(30):
        for year, season, period in ((2023, 1, "P1"), (2023, 2, "P1"), (2024, 1, "P2"), (2024, 2, "P2"),
                                     (2026, 1, "P6")):
            date = f"{year}-{3 * season - 1:02d}-10"
            eid = f"T{t}|{date}"
            y = {k: (t + season + year) % 2 for k in ("y_beat", "y_react", "y_drift")}
            events.append({"event_id": eid, "ticker": f"T{t}", "period": period,
                           "sp500": True, "sector": "Tech", "date": date, "year": year,
                           "season": season, "month": date[:7], "eps_surp_pct": 5.0,
                           "in_S": True, "in_R": False, **y})
            ans = {q: {"type": "noul", "noul": 0.3 if y[lab] else 0.7}
                   for q, lab in (("k1_beat", "y_beat"), ("k2_react", "y_react"), ("k3_drift", "y_drift"))}
            ans["r2_react"] = {"type": "noul", "noul": 0.5}
            ans["r3_drift"] = {"type": "noul", "noul": 0.5}
            recs.append({"request_id": f"jev|K|{eid}|r0", "model_key": "jev", "arm": "K",
                         "event_id": eid, "repeat": 0, "http_status": 200,
                         "served_model": "typesafe/jev-1.13-20260917", "response": {"answers": ans}})
            for arm in ("N", "A"):
                recs.append({"request_id": f"jev|{arm}|{eid}|r0", "model_key": "jev", "arm": arm,
                             "event_id": eid, "repeat": 0, "http_status": 200,
                             "served_model": "typesafe/jev-1.13-20260917",
                             "response": {"answers": {"r2_react": {"type": "noul", "noul": 0.5},
                                                      "r3_drift": {"type": "noul", "noul": 0.5}}}})
            recs.append({"request_id": f"sonnet5|K|{eid}|r0", "model_key": "sonnet5", "arm": "K",
                         "event_id": eid, "repeat": 0, "http_status": 200, "served_model": "s",
                         "content": json.dumps({"k1_beat": 0.8 if y["y_beat"] else 0.2,
                                                "k2_react": 0.5, "k3_drift": 0.5})})
    (work / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    for mk in ("jev", "sonnet5"):
        (runs / f"{mk}.jsonl").write_text("\n".join(json.dumps(r) for r in recs if r["model_key"] == mk) + "\n")
    monkeypatch.setattr(analyze, "WORK", work)
    monkeypatch.setattr(analyze, "RUNS", runs)

    res0 = analyze.run(B=50, ties="demeaned")
    assert "ties_policy" not in res0
    assert "posthoc_same_subsample" not in res0

    res1 = analyze.run(B=50, ties="raw")
    assert res1["ties_policy"] == "raw"
    ph = res1["posthoc_same_subsample"]
    assert "jev" in ph and "sonnet5" in ph and "jev|k1_beat" in ph
    # default-demeaned primary values must be unaffected by the tie-policy plumbing
    assert res0["primary"]["H1"]["estimate"] is not None
    assert res0["primary"]["H1"]["pairs"] == res1["primary"]["H1"]["pairs"]
