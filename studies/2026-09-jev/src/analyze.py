"""Pre-registered analysis. Reads work/events.jsonl and runs/*.jsonl, writes results/.

  python src/analyze.py [--boot 10000]

Primary statistic: within-ticker AUC (wtAUC). Pairs are two events of the SAME ticker, in the SAME
calendar quarter of the year, one in 2023 and one in 2024, with different labels. Scores are
month-demeaned (each score minus the mean score of all events announced in that calendar month,
same model/arm/question). A company-level prior is identical for a firm's two events and cancels;
a generic date effect is removed by the demeaning. What is left is event-specific information.

Primary family (Jev, balanced panel, cluster bootstrap over tickers, Holm at 0.05):
  H1  wtAUC_PRE(K, k1_beat)  > 0.5
  H2  wtAUC_PRE(K, k2_react) > 0.5
  H3  wtAUC_PRE(K, k3_drift) > 0.5
  H4  wtAUC_PRE(N, r3_drift) - wtAUC_PRE(A, r3_drift) > 0
  H5  wtAUC_PRE(N, r2_react) - wtAUC_PRE(A, r2_react) > 0
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import JEV_PIN, PERIODS, POST, PRE, PRE_YEARS, RESULTS, RUNS, SEED, WORK, jsonl_read, utc_now  # noqa: E402
from payloads import ARM_QUESTIONS, LABEL_OF  # noqa: E402

ALPHA = 0.05
Z_MDE = 2.326 + 0.842          # one-sided alpha 0.01 (first Holm step with 5 tests), power 0.80
PIN_MIN_SHARE = 0.80
SEASON_MATCH = ((4, 1), (8, 14))   # PRE window matched to the POST season, cross-sectional S3 only


# ------------------------------------------------------------------ AUC building blocks

def wauc(scores: np.ndarray, labels: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Weighted ROC AUC for each row of W (shape B x n). Ties in score count one half."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    W = np.atleast_2d(np.asarray(W, dtype=float))
    order = np.argsort(scores, kind="mergesort")
    s, y, Wo = scores[order], labels[order], W[:, order]
    _, starts = np.unique(s, return_index=True)
    gpos = np.add.reduceat(Wo * (y == 1), starts, axis=1)
    gneg = np.add.reduceat(Wo * (y == 0), starts, axis=1)
    below = np.cumsum(gneg, axis=1) - gneg
    num = (gpos * (below + 0.5 * gneg)).sum(axis=1)
    den = gpos.sum(axis=1) * gneg.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def cluster_weights(tick_idx: np.ndarray, n_tick: int, B: int, seed: int, chunk: int = 500):
    """Event weights for a ticker-cluster bootstrap: weight = number of times the ticker is drawn."""
    rng = np.random.default_rng(seed)
    p = np.full(n_tick, 1.0 / n_tick)
    done = 0
    while done < B:
        b = min(chunk, B - done)
        counts = rng.multinomial(n_tick, p, size=b)
        yield counts[:, tick_idx]
        done += b


def ticker_counts(n_tick: int, B: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.multinomial(n_tick, np.full(n_tick, 1.0 / n_tick), size=B).astype(float)


def holm(pvals: dict[str, float], alpha: float = ALPHA) -> dict[str, dict]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, still = {}, True
    for k, (name, p) in enumerate(items):
        thr = alpha / (m - k)
        rej = still and p <= thr
        if not rej:
            still = False
        out[name] = {"p": p, "holm_threshold": thr, "reject_null": bool(rej)}
    return out


# ------------------------------------------------------------------ within-ticker AUC

def demean_by_month(rows: list[dict], keys: tuple[str, ...]) -> None:
    """Adds '<key>_dm' = score minus the mean score of all rows announced in the same month."""
    for key in keys:
        by = collections.defaultdict(list)
        for r in rows:
            by[r["month"]].append(r[key])
        means = {m: float(np.mean(v)) for m, v in by.items()}
        for r in rows:
            r[key + "_dm"] = r[key] - means[r["month"]]


def _pair_ok_pre(a: dict, b: dict) -> bool:
    return (a["season"] == b["season"] and a["year"] != b["year"]
            and a["year"] in PRE_YEARS and b["year"] in PRE_YEARS)


def _pair_ok_pre_same_q(a: dict, b: dict) -> bool:
    return a["q"] == b["q"] and _pair_ok_pre(a, b)


def _pair_ok_within_year(year: int):
    return lambda a, b: a["year"] == year and b["year"] == year


def wt_parts(rows: list[dict], keys: tuple[str, ...], pair_ok) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Per ticker: concordance numerators (one column per score key) and informative-pair counts."""
    by_t = collections.defaultdict(list)
    for r in rows:
        by_t[r["ticker"]].append(r)
    ticks, nums, dens = [], [], []
    for t in sorted(by_t):
        rs = by_t[t]
        num = np.zeros(len(keys))
        den = 0
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if a["y"] == b["y"] or not pair_ok(a, b):
                    continue
                pos, neg = (a, b) if a["y"] == 1 else (b, a)
                for k, key in enumerate(keys):
                    d = pos[key] - neg[key]
                    num[k] += 1.0 if d > 1e-9 else (0.5 if d >= -1e-9 else 0.0)
                den += 1
        if den:
            ticks.append(t)
            nums.append(num)
            dens.append(den)
    return ticks, np.array(nums, float).reshape(-1, len(keys)), np.array(dens, float)


def wt_auc_test(rows: list[dict], key: str, pair_ok, B: int, seed: int) -> dict:
    """wtAUC against 0.5 (H1-H3 style). Ticker bootstrap weights numerator and denominator by k."""
    ticks, num, den = wt_parts(rows, (key,), pair_ok)
    if len(ticks) == 0:
        return {"estimate": None, "pairs": 0}
    num = num[:, 0]
    point = float(num.sum() / den.sum())
    C = ticker_counts(len(ticks), B, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        boots = (C @ num) / (C @ den)
    boots = boots[~np.isnan(boots)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    pairs = int(den.sum())
    se0 = 0.5 / math.sqrt(pairs)
    return {"estimate": round(point, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_one_sided": float((1 + np.sum(boots <= 0.5)) / (len(boots) + 1)),
            "boot_sd": round(float(np.std(boots, ddof=1)), 4),
            "mde_design": round(Z_MDE * se0, 4), "pairs": pairs, "tickers": len(ticks), "n_boot": int(len(boots))}


def wt_diff_test(rows: list[dict], key_n: str, key_a: str, pair_ok, B: int, seed: int) -> dict:
    """wtAUC(N) - wtAUC(A) on the same pairs, against 0 (H4/H5 style)."""
    ticks, num, den = wt_parts(rows, (key_n, key_a), pair_ok)
    if len(ticks) == 0:
        return {"estimate": None, "pairs": 0}
    point_n = float(num[:, 0].sum() / den.sum())
    point_a = float(num[:, 1].sum() / den.sum())
    C = ticker_counts(len(ticks), B, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        boots = (C @ (num[:, 0] - num[:, 1])) / (C @ den)
    boots = boots[~np.isnan(boots)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    pairs = int(den.sum())
    se0 = math.sqrt(2) * 0.5 / math.sqrt(pairs)
    return {"estimate": round(point_n - point_a, 4), "wtauc_named": round(point_n, 4),
            "wtauc_anon": round(point_a, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_one_sided": float((1 + np.sum(boots <= 0)) / (len(boots) + 1)),
            "boot_sd": round(float(np.std(boots, ddof=1)), 4),
            "mde_design": round(Z_MDE * se0, 4), "pairs": pairs, "tickers": len(ticks), "n_boot": int(len(boots))}


# ------------------------------------------------------------------ cross-sectional (secondary)

def summarize(point: float, boots: np.ndarray) -> dict:
    boots = boots[~np.isnan(boots)]
    if len(boots) == 0 or point is None or (isinstance(point, float) and math.isnan(point)):
        return {"estimate": None}
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"estimate": round(float(point), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_one_sided": float((1 + np.sum(boots <= 0)) / (len(boots) + 1)),
            "boot_sd": round(float(np.std(boots, ddof=1)), 4), "n_boot": int(len(boots))}


def auc_with_ci(s, y, tick, B, seed) -> dict:
    s, y = np.asarray(s, float), np.asarray(y, int)
    if len(s) == 0 or y.min() == y.max():
        return {"auc": None, "n": int(len(s))}
    t_codes, t_idx = np.unique(tick, return_inverse=True)
    point = float(wauc(s, y, np.ones((1, len(s))))[0])
    boots = np.concatenate([wauc(s, y, W) for W in cluster_weights(t_idx, len(t_codes), B, seed)])
    boots = boots[~np.isnan(boots)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"auc": round(point, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n": int(len(s)), "n_pos": int(y.sum()), "tickers": int(len(t_codes))}


def delta_pre_post(rows: list[dict], B: int, seed: int) -> dict:
    """Cross-sectional AUC(PRE) - AUC(POST). rows: s, y, ticker, grp."""
    s = np.array([r["s"] for r in rows], float)
    y = np.array([r["y"] for r in rows], int)
    g = np.array([r["grp"] for r in rows])
    t_codes, t_idx = np.unique([r["ticker"] for r in rows], return_inverse=True)
    pre, post = g == "PRE", g == "POST"
    if pre.sum() == 0 or post.sum() == 0:
        return {"estimate": None}
    one = np.ones((1, len(s)))
    a_pre = float(wauc(s[pre], y[pre], one[:, pre])[0])
    a_post = float(wauc(s[post], y[post], one[:, post])[0])
    boots = [wauc(s[pre], y[pre], W[:, pre]) - wauc(s[post], y[post], W[:, post])
             for W in cluster_weights(t_idx, len(t_codes), B, seed)]
    out = summarize(a_pre - a_post, np.concatenate(boots))
    out.update({"auc_pre": round(a_pre, 4), "auc_post": round(a_post, 4),
                "n_pre": int(pre.sum()), "n_post": int(post.sum()), "tickers": int(len(t_codes))})
    return out


def did_named_anon(rows: list[dict], B: int, seed: int) -> dict:
    """Cross-sectional [AUC_N - AUC_A]_PRE - [AUC_N - AUC_A]_POST. rows: sN, sA, y, ticker, grp."""
    sN = np.array([r["sN"] for r in rows], float)
    sA = np.array([r["sA"] for r in rows], float)
    y = np.array([r["y"] for r in rows], int)
    g = np.array([r["grp"] for r in rows])
    t_codes, t_idx = np.unique([r["ticker"] for r in rows], return_inverse=True)
    pre, post = g == "PRE", g == "POST"
    if pre.sum() == 0 or post.sum() == 0:
        return {"estimate": None}

    def stat(W):
        return ((wauc(sN[pre], y[pre], W[:, pre]) - wauc(sA[pre], y[pre], W[:, pre]))
                - (wauc(sN[post], y[post], W[:, post]) - wauc(sA[post], y[post], W[:, post])))

    one = np.ones((1, len(y)))
    point = float(stat(one)[0])
    boots = np.concatenate([stat(W) for W in cluster_weights(t_idx, len(t_codes), B, seed)])
    out = summarize(point, boots)
    out.update({
        "auc_named_pre": round(float(wauc(sN[pre], y[pre], one[:, pre])[0]), 4),
        "auc_anon_pre": round(float(wauc(sA[pre], y[pre], one[:, pre])[0]), 4),
        "auc_named_post": round(float(wauc(sN[post], y[post], one[:, post])[0]), 4),
        "auc_anon_post": round(float(wauc(sA[post], y[post], one[:, post])[0]), 4),
        "n_pre": int(pre.sum()), "n_post": int(post.sum()), "tickers": int(len(t_codes))})
    return out


def calibration(s: np.ndarray, y: np.ndarray, bins: int = 10) -> dict:
    s, y = np.asarray(s, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(s, edges[1:-1]), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            ece += m.mean() * abs(s[m].mean() - y[m].mean())
    return {"brier": round(float(np.mean((s - y) ** 2)), 4), "ece": round(float(ece), 4),
            "mean_p": round(float(s.mean()), 4), "base_rate": round(float(y.mean()), 4),
            "share_p_eq_0_5": round(float(np.mean(np.isclose(s, 0.5))), 4),
            "distinct_values": int(len(np.unique(np.round(s, 4)))), "n": int(len(s))}


# ------------------------------------------------------------------ loading

_JSON_OBJ = re.compile(r"\{.*\}", re.S)


def _prob(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    return v if 0.0 <= v <= 1.0 else None


def parse_control(content: str | None, qids) -> dict:
    if not content:
        return {}
    m = _JSON_OBJ.search(content)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return {}
    out = {}
    for q in qids:
        v = d.get(q)
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                continue
        p = _prob(v)
        if p is not None:
            out[q] = p
    return out


def load_outputs() -> tuple[dict, dict]:
    """({(model, arm, event_id, repeat, prospective): {qid: p}}, quality stats).

    Jev responses whose served model differs from JEV_PIN are excluded and counted.
    """
    outs, quality = {}, collections.defaultdict(collections.Counter)
    for path in sorted(RUNS.glob("*.jsonl")):
        last = {}
        for r in jsonl_read(path):
            if r["http_status"] == 200 or r["request_id"] not in last:
                last[r["request_id"]] = r
        for r in last.values():
            key = (r["model_key"], r["arm"], r["event_id"], r["repeat"], bool(r.get("prospective")))
            qids = list(ARM_QUESTIONS[r["arm"]])
            q = quality[f"{r['model_key']}|{r['arm']}{'|prosp' if r.get('prospective') else ''}"]
            q["records"] += 1
            if r["http_status"] != 200:
                q[f"http_{r['http_status']}"] += 1
                continue
            q[f"served:{r.get('served_model')}"] += 1
            if r["model_key"] == "jev" and r.get("served_model") != JEV_PIN:
                q["other_version_excluded"] += 1
                continue
            if r["model_key"] == "jev":
                ans = ((r.get("response") or {}).get("answers") or {})
                ps = {}
                for k, v in ans.items():
                    if k in qids and isinstance(v, dict):
                        p = _prob(v.get("noul"))
                        if p is not None:
                            ps[k] = p
            else:
                ps = parse_control(r.get("content"), qids)
            if len(ps) < len(qids):
                q["incomplete_output"] += 1
            outs[key] = ps
    return outs, {k: dict(v) for k, v in quality.items()}


def grp_of(period: str) -> str | None:
    if period in PRE:
        return "PRE"
    if period in POST:
        return "POST"
    return None


def in_season_match(date: str) -> bool:
    m, d = int(date[5:7]), int(date[8:10])
    return SEASON_MATCH[0] <= (m, d) <= SEASON_MATCH[1]


# ------------------------------------------------------------------ analysis

def run(B: int) -> dict:
    events = {e["event_id"]: e for e in jsonl_read(WORK / "events.jsonl")}
    outs, quality = load_outputs()
    tick_pre = {e["ticker"] for e in events.values() if e["period"] in PRE}
    tick_post = {e["ticker"] for e in events.values() if e["period"] in POST}
    panel = tick_pre & tick_post

    def k_rows(model, qid, fill=None):
        """All events with a label and a K-arm answer (fill: value used for a missing answer)."""
        rows = []
        for eid, e in events.items():
            y = e[LABEL_OF[qid]]
            if y is None:
                continue
            p = outs.get((model, "K", eid, 0, False), {}).get(qid, fill)
            if p is None:
                continue
            rows.append({"s": p, "y": y, "ticker": e["ticker"], "grp": grp_of(e["period"]), "date": e["date"],
                         "period": e["period"], "sp500": e["sp500"], "sector": e["sector"], "year": e["year"],
                         "season": e["season"], "month": e["month"], "in_S": e.get("in_S", False),
                         "surp": e.get("eps_surp_pct")})
        demean_by_month(rows, ("s",))
        return rows

    def na_rows(model, qid, fill=None):
        rows = []
        for eid, e in events.items():
            y = e[LABEL_OF[qid]]
            if y is None:
                continue
            pN = outs.get((model, "N", eid, 0, False), {}).get(qid, fill)
            pA = outs.get((model, "A", eid, 0, False), {}).get(qid, fill)
            if pN is None or pA is None:
                continue
            rows.append({"sN": pN, "sA": pA, "y": y, "ticker": e["ticker"], "grp": grp_of(e["period"]),
                         "date": e["date"], "period": e["period"], "sp500": e["sp500"], "year": e["year"],
                         "season": e["season"], "month": e["month"], "in_S": e.get("in_S", False)})
        demean_by_month(rows, ("sN", "sA"))
        return rows

    def panel_only(rows):
        return [r for r in rows if r["ticker"] in panel]

    res = {"generated_utc": utc_now(), "n_boot": B, "seed": SEED, "jev_pin": JEV_PIN,
           "events": len(events), "balanced_panel_tickers": len(panel), "output_quality": quality}

    # ---------------- version-pin check (study requests only)
    served = collections.Counter()
    for k, v in quality.items():
        if k.startswith("jev|") and not k.endswith("|prosp"):
            for kk, n in v.items():
                if kk.startswith("served:"):
                    served[kk[7:]] += n
    tot = sum(served.values())
    res["jev_pin_share"] = round(served.get(JEV_PIN, 0) / tot, 4) if tot else None
    res["jev_rerun_required"] = bool(tot and served.get(JEV_PIN, 0) / tot < PIN_MIN_SHARE)

    # ---------------- primary
    prim = {}
    for h, qid in (("H1", "k1_beat"), ("H2", "k2_react"), ("H3", "k3_drift")):
        prim[h] = {"question": qid,
                   **wt_auc_test(panel_only(k_rows("jev", qid)), "s_dm", _pair_ok_pre, B, SEED + int(h[1]))}
    for h, qid in (("H4", "r3_drift"), ("H5", "r2_react")):
        prim[h] = {"question": qid,
                   **wt_diff_test(panel_only(na_rows("jev", qid)), "sN_dm", "sA_dm", _pair_ok_pre, B, SEED + int(h[1]))}
    pv = {h: v["p_one_sided"] for h, v in prim.items() if v.get("estimate") is not None}
    res["primary"] = prim
    res["holm"] = holm(pv) if pv else {}

    # ---------------- secondary
    sec = {}
    years = (2023, 2024, 2025, 2026)
    s1 = {"within_year_wtauc": {}, "cross_sectional_auc_by_period": {}}
    for qid in ("k1_beat", "k2_react", "k3_drift"):
        rows = k_rows("jev", qid)
        s1["within_year_wtauc"][qid] = {y: wt_auc_test(rows, "s_dm", _pair_ok_within_year(y), B // 5, SEED + 101)
                                        for y in years}
        s1["cross_sectional_auc_by_period"][qid] = {
            name: auc_with_ci([r["s"] for r in rows if r["period"] == name],
                              [r["y"] for r in rows if r["period"] == name],
                              [r["ticker"] for r in rows if r["period"] == name], B // 10, SEED + 102)
            for name, _, _ in PERIODS}
    sec["S1_memory_by_year"] = s1
    sub = {}
    for label, fn in (("sp500", lambda r: r["sp500"]), ("non_sp500", lambda r: not r["sp500"])):
        sub[label] = {}
        for h, qid in (("H1", "k1_beat"), ("H2", "k2_react"), ("H3", "k3_drift")):
            rows = [r for r in panel_only(k_rows("jev", qid)) if fn(r)]
            sub[label][h] = wt_auc_test(rows, "s_dm", _pair_ok_pre, B // 5, SEED + 201)
        for h, qid in (("H4", "r3_drift"), ("H5", "r2_react")):
            rows = [r for r in panel_only(na_rows("jev", qid)) if fn(r)]
            sub[label][h] = wt_diff_test(rows, "sN_dm", "sA_dm", _pair_ok_pre, B // 5, SEED + 202)
    sec["S2_subgroups"] = sub
    s3 = {}
    for qid in ("k1_beat", "k2_react", "k3_drift"):
        rows = [r for r in panel_only(k_rows("jev", qid))
                if r["grp"] == "POST" or (r["grp"] == "PRE" and in_season_match(r["date"]))]
        s3[qid] = delta_pre_post(rows, B // 5, SEED + 301)
    for qid in ("r2_react", "r3_drift"):
        rows = [r for r in panel_only(na_rows("jev", qid))
                if r["grp"] == "POST" or (r["grp"] == "PRE" and in_season_match(r["date"]))]
        s3[f"did_{qid}"] = did_named_anon(rows, B // 5, SEED + 302)
    sec["S3_cross_sectional_season_matched"] = s3
    lev = {}
    for qid in ("r2_react", "r3_drift"):
        rows = na_rows("jev", qid)
        lev[qid] = {arm: {name: auc_with_ci([r[col] for r in rows if r["period"] == name],
                                            [r["y"] for r in rows if r["period"] == name],
                                            [r["ticker"] for r in rows if r["period"] == name], B // 10, SEED + 401)
                          for name, _, _ in PERIODS}
                    for arm, col in (("N", "sN"), ("A", "sA"))}
    sec["S4_levels_named_anon"] = lev
    rep = {}
    for qid in ("k1_beat", "k2_react", "k3_drift"):
        diffs, flips, n = [], 0, 0
        for eid, e in events.items():
            if not e.get("in_R"):
                continue
            ps = [outs.get(("jev", "K", eid, k, False), {}).get(qid) for k in range(3)]
            if any(p is None for p in ps):
                continue
            n += 1
            diffs += [abs(ps[i] - ps[j]) for i in range(3) for j in range(i + 1, 3)]
            flips += len({p > 0.5 for p in ps}) > 1
        rep[qid] = {"events": n, "mean_abs_pairwise_diff": round(float(np.mean(diffs)), 4) if diffs else None,
                    "max_abs_diff": round(float(np.max(diffs)), 4) if diffs else None,
                    "share_side_flips": round(flips / n, 4) if n else None}
    sec["S5_repeatability"] = rep
    cal = {}
    for qid in ("k1_beat", "k2_react", "k3_drift"):
        rr = k_rows("jev", qid)
        if rr:
            cal[qid] = calibration(np.array([r["s"] for r in rr]), np.array([r["y"] for r in rr]))
    for qid in ("r2_react", "r3_drift"):
        rr = na_rows("jev", qid)
        if rr:
            cal[f"{qid}|N"] = calibration(np.array([r["sN"] for r in rr]), np.array([r["y"] for r in rr]))
            cal[f"{qid}|A"] = calibration(np.array([r["sA"] for r in rr]), np.array([r["y"] for r in rr]))
    sec["S6_calibration"] = cal
    rows = [r for r in panel_only(k_rows("jev", "k1_beat")) if r["surp"] is not None and abs(r["surp"]) >= 2.0]
    sec["S8_h1_clear_surprises"] = wt_auc_test(rows, "s_dm", _pair_ok_pre, B // 5, SEED + 801)
    s9 = {}
    for h, qid in (("H1", "k1_beat"), ("H2", "k2_react"), ("H3", "k3_drift")):
        s9[h] = wt_auc_test(panel_only(k_rows("jev", qid, fill=0.5)), "s_dm", _pair_ok_pre, B // 5, SEED + 901)
    for h, qid in (("H4", "r3_drift"), ("H5", "r2_react")):
        s9[h] = wt_diff_test(panel_only(na_rows("jev", qid, fill=0.5)), "sN_dm", "sA_dm", _pair_ok_pre,
                             B // 5, SEED + 902)
    sec["S9_missing_filled_0_5"] = s9
    pooled = [dict(r, q=qid) for qid in ("k1_beat", "k2_react", "k3_drift") for r in panel_only(k_rows("jev", qid))]
    sec["S10_pooled_K"] = wt_auc_test(pooled, "s_dm", _pair_ok_pre_same_q, B // 5, SEED + 1010)
    vr = {}
    for arm in ("K", "N", "A"):
        vr[arm] = {}
        for name, _, _ in PERIODS:
            ids = [eid for eid, e in events.items() if e["period"] == name]
            ok = sum(1 for eid in ids if len(outs.get(("jev", arm, eid, 0, False), {})) == len(ARM_QUESTIONS[arm]))
            vr[arm][name] = round(ok / len(ids), 4) if ids else None
    sec["valid_output_rate_by_period"] = vr
    res["secondary"] = sec

    # ---------------- controls (subsample S = all events of 250 panel tickers)
    ctrl = {}
    for model, arms in (("sonnet5", ("K",)), ("llama31", ("K", "N", "A"))):
        c = {"wt_pre": {}, "within_year": {}}
        for qid in ("k1_beat", "k2_react", "k3_drift"):
            rows = [r for r in k_rows(model, qid) if r["in_S"]]
            c["wt_pre"][qid] = wt_auc_test(rows, "s_dm", _pair_ok_pre, B // 5, SEED + 1001)
            c["within_year"][qid] = {y: wt_auc_test(rows, "s_dm", _pair_ok_within_year(y), B // 10, SEED + 1002)
                                     for y in years}
        if "N" in arms:
            for qid in ("r2_react", "r3_drift"):
                rows = [r for r in na_rows(model, qid) if r["in_S"]]
                c[f"wt_pre_named_minus_anon_{qid}"] = wt_diff_test(rows, "sN_dm", "sA_dm", _pair_ok_pre,
                                                                    B // 5, SEED + 1003)
        ctrl[model] = c
    # probe validity: Sonnet 5, K arm, pairs of all three statements pooled (one pre-specified statistic)
    for model in ("sonnet5", "llama31"):
        pooled = [dict(r, q=qid) for qid in ("k1_beat", "k2_react", "k3_drift") for r in k_rows(model, qid) if r["in_S"]]
        ctrl[model]["wt_pre_pooled_K"] = wt_auc_test(pooled, "s_dm", _pair_ok_pre_same_q, B // 5, SEED + 1004)
    v = ctrl["sonnet5"]["wt_pre_pooled_K"]
    ctrl["probe_valid"] = bool(v.get("ci95") and v["ci95"][0] > 0.5)
    res["controls"] = ctrl

    # ---------------- decision (PREREG section 8)
    hl = res["holm"]
    memory = any(hl.get(h, {}).get("reject_null") for h in ("H1", "H2", "H3"))
    bt_leak = any(hl.get(h, {}).get("reject_null") for h in ("H4", "H5"))
    y2026 = {qid: s1["within_year_wtauc"][qid].get(2026, {}) for qid in ("k1_beat", "k2_react", "k3_drift")}
    flag_2026 = {qid: bool(v.get("ci95") and v["ci95"][0] > 0.5) for qid, v in y2026.items()}
    if res["jev_rerun_required"]:
        verdict = "rerun_required_model_changed"
    elif memory or bt_leak:
        verdict = "leakage_detected"
    elif ctrl["probe_valid"]:
        verdict = "no_detectable_leakage_provisional"
    else:
        verdict = "inconclusive_probe_insensitive"
    res["decision"] = {"verdict": verdict, "memory_H1_H3": memory, "named_backtest_leak_H4_H5": bt_leak,
                       "within_2026_wtauc_above_0_5": flag_2026,
                       "note": "'provisional' until the prospective set is scored (after 2027-01-08)."}
    return res


def md_table(res: dict) -> str:
    L = [f"# Results: Jev look-ahead test\n\nGenerated {res['generated_utc']}; bootstrap B={res['n_boot']}; "
         f"events {res['events']}; balanced-panel tickers {res['balanced_panel_tickers']}; "
         f"Jev pin {res['jev_pin']} share {res['jev_pin_share']}.\n",
         f"**Decision (pre-registered rule): {res['decision']['verdict']}**\n",
         "## Primary (Jev, within-ticker, same season, 2023 vs 2024, month-demeaned)\n",
         "| H | question | estimate | 95% CI | one-sided p | Holm reject | pairs | tickers | design MDE |",
         "|---|---|---|---|---|---|---|---|---|"]
    for h, v in res["primary"].items():
        if v.get("estimate") is None:
            L.append(f"| {h} | {v['question']} | – | – | – | – | 0 | – | – |")
            continue
        est = v["estimate"]
        if h in ("H4", "H5"):
            est = f"{v['estimate']} (N {v['wtauc_named']} / A {v['wtauc_anon']})"
        hv = res["holm"].get(h, {})
        L.append(f"| {h} | {v['question']} | {est} | {v['ci95']} | {v['p_one_sided']:.4f} | "
                 f"{hv.get('reject_null')} | {v['pairs']} | {v['tickers']} | {v['mde_design']} |")
    L.append("\n## Memory by year (Jev K arm, within-ticker within-year wtAUC)\n")
    L.append("| question | 2023 | 2024 | 2025 | 2026 |")
    L.append("|---|---|---|---|---|")
    for qid, per in res["secondary"]["S1_memory_by_year"]["within_year_wtauc"].items():
        cells = []
        for y in (2023, 2024, 2025, 2026):
            c = per.get(y, {})
            cells.append(f"{c.get('estimate')} {c.get('ci95', '')} ({c.get('pairs')} pairs)"
                         if c.get("estimate") is not None else "–")
        L.append(f"| {qid} | " + " | ".join(cells) + " |")
    L.append("\n## Cross-sectional AUC by period (Jev K arm)\n")
    L.append("| question | " + " | ".join(p for p, _, _ in PERIODS) + " |")
    L.append("|---|" + "---|" * len(PERIODS))
    for qid, per in res["secondary"]["S1_memory_by_year"]["cross_sectional_auc_by_period"].items():
        L.append(f"| {qid} | " + " | ".join(f"{per[p].get('auc')}" for p, _, _ in PERIODS) + " |")
    L.append("\n## Controls (subsample S, within-ticker PRE)\n")
    for model in ("sonnet5", "llama31"):
        c = res["controls"].get(model, {})
        L.append(f"### {model}\n")
        for qid, v in c.get("wt_pre", {}).items():
            yrs = ", ".join(f"{y}: {c['within_year'][qid][y].get('estimate')}" for y in (2023, 2024, 2025, 2026))
            L.append(f"- {qid}: wtAUC_PRE {v.get('estimate')} {v.get('ci95', '')} ({v.get('pairs')} pairs); "
                     f"within-year {yrs}")
        for k, v in c.items():
            if k.startswith("wt_pre_named_minus_anon"):
                L.append(f"- {k}: {v.get('estimate')} {v.get('ci95', '')}")
    for model in ("sonnet5", "llama31"):
        v = res["controls"].get(model, {}).get("wt_pre_pooled_K", {})
        L.append(f"- {model} pooled K wtAUC_PRE: {v.get('estimate')} {v.get('ci95', '')} ({v.get('pairs')} pairs)")
    L.append(f"\nProbe valid (Sonnet 5 pooled K wtAUC_PRE, CI above 0.5): {res['controls'].get('probe_valid')}\n")
    L.append("## Secondary\n")
    s = res["secondary"]
    L.append("- S3 cross-sectional season-matched: " + json.dumps(s["S3_cross_sectional_season_matched"]))
    L.append("- S5 repeatability: " + json.dumps(s["S5_repeatability"]))
    L.append("- S6 calibration: " + json.dumps(s["S6_calibration"]))
    L.append("- S8 H1 on |surprise|>=2%: " + json.dumps(s["S8_h1_clear_surprises"]))
    L.append("- S10 Jev pooled K: " + json.dumps(s["S10_pooled_K"]))
    L.append("- valid output rate by period: " + json.dumps(s["valid_output_rate_by_period"]))
    L.append("\n## Output quality\n")
    for k, v in res["output_quality"].items():
        L.append(f"- {k}: {v}")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    res = run(a.boot)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (RESULTS / "results.md").write_text(md_table(res))
    print(md_table(res))


if __name__ == "__main__":
    main()
