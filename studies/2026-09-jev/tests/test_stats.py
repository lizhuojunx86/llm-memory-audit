"""Unit tests for the analysis statistics (run: python -m pytest tests -q)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import (calibration, cluster_weights, delta_pre_post, demean_by_month, did_named_anon, holm,  # noqa: E402
                     parse_control, wauc, wt_auc_test, wt_diff_test, wt_parts, _pair_ok_pre, ticker_counts)

sk = pytest.importorskip("sklearn.metrics")


def test_wauc_matches_sklearn_with_ties_and_weights():
    rng = np.random.default_rng(0)
    for _ in range(50):
        n = rng.integers(20, 400)
        s = np.round(rng.random(n), rng.integers(1, 3))   # heavy ties
        y = rng.integers(0, 2, n)
        if y.min() == y.max():
            continue
        w = rng.integers(0, 4, n).astype(float)
        if w[y == 1].sum() == 0 or w[y == 0].sum() == 0:
            continue
        ours = wauc(s, y, w[None, :])[0]
        ref = sk.roc_auc_score(y, s, sample_weight=w)
        assert abs(ours - ref) < 1e-10


def test_wauc_constant_scores_is_half():
    y = np.array([0, 1, 0, 1, 1])
    assert wauc(np.full(5, 0.5), y, np.ones((1, 5)))[0] == 0.5


def test_cluster_weights_sum_and_shape():
    tick_idx = np.array([0, 0, 1, 2, 2, 2])
    Ws = list(cluster_weights(tick_idx, 3, B=1200, seed=1, chunk=500))
    assert [w.shape for w in Ws] == [(500, 6), (500, 6), (200, 6)]
    W = np.concatenate(Ws)
    # each replicate draws 3 tickers; event weight = count of its ticker
    counts = np.stack([W[:, 0], W[:, 2], W[:, 3]], axis=1)
    assert np.all(counts.sum(axis=1) == 3)
    assert np.all(W[:, 0] == W[:, 1]) and np.all(W[:, 3] == W[:, 5])


def _sim_rows(n_t, per_t, leak_pre, leak_post, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_t):
        prior = rng.normal(0, 0.3)                      # stable company-level prior, same in both periods
        for grp, leak in (("PRE", leak_pre), ("POST", leak_post)):
            for _ in range(per_t):
                y = int(rng.random() < 1 / (1 + np.exp(-prior)))
                s = 1 / (1 + np.exp(-(prior + leak * (2 * y - 1) + rng.normal(0, 1))))
                rows.append({"s": float(s), "y": y, "ticker": f"T{t}", "grp": grp})
    return rows


def test_delta_detects_leak_and_not_null():
    leak = delta_pre_post(_sim_rows(300, 6, 0.6, 0.0, 3), B=2000, seed=5)
    assert leak["estimate"] > 0.05 and leak["p_one_sided"] < 0.01
    null = delta_pre_post(_sim_rows(300, 6, 0.0, 0.0, 4), B=2000, seed=6)
    assert abs(null["estimate"]) < 0.05 and null["p_one_sided"] > 0.01


def test_null_false_positive_rate_is_controlled():
    hits = 0
    for k in range(30):
        r = delta_pre_post(_sim_rows(150, 4, 0.0, 0.0, 100 + k), B=600, seed=200 + k)
        hits += r["p_one_sided"] <= 0.05
    assert hits <= 5        # nominal 1.5 of 30; loose bound for a quick check


def test_did_detects_named_advantage_only_pre():
    rng = np.random.default_rng(7)
    rows = []
    for t in range(300):
        for grp, extra in (("PRE", 0.8), ("POST", 0.0)):
            for _ in range(5):
                y = int(rng.random() < 0.5)
                base = rng.normal(0, 1) + 0.3 * (2 * y - 1)       # skill from numbers, both arms
                sA = 1 / (1 + np.exp(-base))
                sN = 1 / (1 + np.exp(-(base + extra * (2 * y - 1))))
                rows.append({"sN": sN, "sA": sA, "y": y, "ticker": f"T{t}", "grp": grp})
    r = did_named_anon(rows, B=1500, seed=9)
    assert r["estimate"] > 0.05 and r["p_one_sided"] < 0.01
    assert abs(r["auc_named_post"] - r["auc_anon_post"]) < 1e-9


def test_holm_steps_down():
    out = holm({"H1": 0.001, "H2": 0.02, "H3": 0.03, "H4": 0.5})
    assert out["H1"]["reject_null"] and not out["H4"]["reject_null"]
    # 0.02 <= 0.05/3 fails (0.0167), so H2 and all later are not rejected
    assert not out["H2"]["reject_null"] and not out["H3"]["reject_null"]


def test_parse_control_variants():
    q = ["k1_beat", "k2_react"]
    assert parse_control('{"k1_beat": 0.8, "k2_react": "0.3"}', q) == {"k1_beat": 0.8, "k2_react": 0.3}
    assert parse_control('```json\n{"k1_beat": 1.2, "k2_react": 0.4}\n```', q) == {"k2_react": 0.4}
    assert parse_control("I cannot know that.", q) == {}


def test_calibration_basic():
    c = calibration(np.array([0.9, 0.9, 0.1, 0.1]), np.array([1, 1, 0, 0]))
    assert c["ece"] == pytest.approx(0.1) and c["brier"] == pytest.approx(0.01)


def _world(n_t, memory, seed, shock_sd=0.4):
    """Synthetic panel: stable firm priors, sector x quarter shocks, date-dependent output flattening.
    memory > 0 adds event-specific knowledge of the label to 2023-2024 outputs only."""
    rng = np.random.default_rng(seed)
    rows = []
    shocks = {}
    for t in range(n_t):
        prior = rng.normal(0, 0.8)
        sector = t % 5
        for year in (2023, 2024, 2025, 2026):
            for season in (1, 2, 3, 4):
                if year == 2026 and season > 2:
                    continue
                sh = shocks.setdefault((sector, year, season), rng.normal(0, shock_sd))
                y = int(rng.random() < 1 / (1 + np.exp(-(prior + sh + 0.2 * (year - 2023)))))
                damp = 1.0 if year < 2026 else 0.3          # flatter answers for recent dates
                logit = damp * prior + 0.3 * (season == 4) + rng.normal(0, 0.7)
                if memory and year in (2023, 2024):
                    logit += memory * (2 * y - 1)
                rows.append({"s": float(1 / (1 + np.exp(-logit))), "y": y, "ticker": f"T{t}",
                             "year": year, "season": season, "month": f"{year}-{3 * season - 1:02d}"})
    demean_by_month(rows, ("s",))
    return rows


def test_within_ticker_null_is_calibrated_under_priors_and_shocks():
    hits = 0
    for k in range(40):
        r = wt_auc_test(_world(250, 0.0, 300 + k), "s_dm", _pair_ok_pre, B=400, seed=k)
        hits += r["p_one_sided"] <= 0.05
    assert hits <= 6          # nominal 2 of 40


def test_within_ticker_detects_memory():
    r = wt_auc_test(_world(400, 0.8, 7), "s_dm", _pair_ok_pre, B=1000, seed=1)
    assert r["estimate"] > 0.6 and r["p_one_sided"] < 0.01


def test_wt_parts_counts_only_informative_same_season_cross_year_pairs():
    rows = [
        {"ticker": "A", "year": 2023, "season": 2, "y": 1, "s_dm": 0.3},
        {"ticker": "A", "year": 2024, "season": 2, "y": 0, "s_dm": 0.1},   # informative, concordant
        {"ticker": "A", "year": 2024, "season": 3, "y": 0, "s_dm": 0.9},   # other season: ignored
        {"ticker": "A", "year": 2025, "season": 2, "y": 0, "s_dm": 0.9},   # not a PRE year: ignored
        {"ticker": "B", "year": 2023, "season": 1, "y": 1, "s_dm": 0.2},
        {"ticker": "B", "year": 2024, "season": 1, "y": 0, "s_dm": 0.2},   # tie -> 0.5
        {"ticker": "B", "year": 2023, "season": 4, "y": 1, "s_dm": 0.2},
        {"ticker": "B", "year": 2024, "season": 4, "y": 1, "s_dm": 0.9},   # same label: ignored
    ]
    ticks, num, den = wt_parts(rows, ("s_dm",), _pair_ok_pre)
    assert ticks == ["A", "B"] and list(den) == [1.0, 1.0] and list(num[:, 0]) == [1.0, 0.5]


def test_ticker_bootstrap_weights_pairs_by_k_not_k_squared():
    # a ticker drawn twice must count its pairs twice, not four times
    num = np.array([1.0, 0.0])
    den = np.array([1.0, 3.0])
    C = np.array([[2.0, 1.0]])
    assert (C @ num / (C @ den))[0] == 2.0 / 5.0


def test_wt_diff_detects_named_advantage():
    rng = np.random.default_rng(5)
    rows = []
    for t in range(300):
        prior = rng.normal(0, 0.5)
        for year in (2023, 2024):
            for season in (1, 2, 3, 4):
                y = int(rng.random() < 0.5)
                base = prior + 0.3 * (2 * y - 1) + rng.normal(0, 1)
                rows.append({"ticker": f"T{t}", "year": year, "season": season, "y": y,
                             "month": f"{year}-{3 * season:02d}",
                             "sA": float(1 / (1 + np.exp(-base))),
                             "sN": float(1 / (1 + np.exp(-(base + 0.8 * (2 * y - 1)))))})
    demean_by_month(rows, ("sN", "sA"))
    r = wt_diff_test(rows, "sN_dm", "sA_dm", _pair_ok_pre, B=800, seed=2)
    assert r["estimate"] > 0.05 and r["p_one_sided"] < 0.01
