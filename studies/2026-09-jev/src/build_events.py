"""Build study events, labels, subsamples and every request payload. Runs before freeze.

  python src/build_events.py

Outputs (work/):
  events.jsonl       study events with labels (vendor-derived; private)
  prospective.jsonl  scheduled Q3-2026 announcements (no labels yet)
  requests.jsonl     every model request, shuffled (seeded)
  manifest.json      counts and exclusion reasons
"""
from __future__ import annotations

import bisect
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CONTROL_MODELS, DATA, DEDUP_DAYS, DRIFT_DAYS, JEV_MODEL, JUMP_HI, JUMP_LO,  # noqa: E402
                    MIN_PRICE, PERIODS, POST, PRE, PROSP_END, PROSP_START, REPEAT_EXTRA, REPEAT_N, SEED,
                    STUDY_END, STUDY_START, SUBSAMPLE_TICKERS, SURP_CAP, WORK, gz_json_read,
                    jsonl_write, parse_date, period_of, utc_now)
from payloads import control_payload, jev_payload  # noqa: E402


def load(kind: str, sym: str):
    p = DATA / "fmp" / kind / f"{sym}.json.gz"
    return gz_json_read(p)["body"] if p.exists() else None


def closes(sym: str) -> dict[str, float]:
    body = load("prices", sym) or []
    rows = body if isinstance(body, list) else body.get("historical", [])
    return {r["date"][:10]: float(r["close"]) for r in rows if r.get("close") not in (None, 0)}


def surprise_pct(actual, est, min_abs: float) -> float | None:
    if actual is None or est is None:
        return None
    if abs(est) < min_abs:
        return None
    v = (actual - est) / abs(est) * 100.0
    return round(max(-SURP_CAP, min(SURP_CAP, v)), 1)


def main() -> None:
    u = json.loads((DATA / "universe.json").read_text())
    sp_set = set(u["sp500"])
    syms = u["sp500"] + u["non_sp"]

    spy = closes("SPY")
    cal = sorted(spy)                      # trading calendar = SPY trading days
    excl = collections.Counter()
    events, prosp = [], []
    prosp_seen: set[str] = set()

    for sym in syms:
        prof = load("profile", sym)
        earn = load("earnings", sym)
        if not prof or not earn:
            excl["no_profile_or_earnings"] += 1
            continue
        p0 = prof[0] if isinstance(prof, list) and prof else {}
        company = p0.get("companyName") or sym
        exchange = p0.get("exchange") or "unknown"
        sector = p0.get("sector") or "unknown"
        px = closes(sym)
        recs = sorted((r for r in earn if r.get("date")), key=lambda r: r["date"])
        last_kept = None
        for r in recs:
            d = parse_date(r["date"])
            base = {"ticker": sym, "company": company, "exchange": exchange, "sector": sector,
                    "sp500": sym in sp_set, "date": d.isoformat(), "event_id": f"{sym}|{d.isoformat()}",
                    "year": d.year, "season": (d.month - 1) // 3 + 1, "month": d.isoformat()[:7]}
            if PROSP_START <= d <= PROSP_END and r.get("epsActual") is None and r.get("epsEstimated") is not None:
                if sym not in prosp_seen:
                    prosp_seen.add(sym)
                    prosp.append({**base, "period": "PROSP", "eps_est": r["epsEstimated"]})
                else:
                    excl["prosp_second_record_same_ticker"] += 1
                continue
            if not (STUDY_START <= d <= STUDY_END):
                continue
            if last_kept is not None and (d - last_kept).days < DEDUP_DAYS:
                excl["dup_within_30d"] += 1
                continue
            a, e = r.get("epsActual"), r.get("epsEstimated")
            if a is None or e is None:
                excl["eps_missing"] += 1
                continue
            i_prev = bisect.bisect_left(cal, d.isoformat()) - 1
            i_next = bisect.bisect_right(cal, d.isoformat())
            i_end = i_next + DRIFT_DAYS
            if i_prev < 0 or i_end >= len(cal):
                excl["window_outside_calendar"] += 1
                continue
            days = cal[i_prev:i_end + 1]
            if any(x not in px for x in (cal[i_prev], cal[i_next], cal[i_end])):
                excl["missing_price"] += 1
                continue
            if px[cal[i_prev]] < MIN_PRICE:
                excl["price_below_1"] += 1
                continue
            seq = [px[x] for x in days if x in px]
            if any(not (JUMP_LO <= b / a_ <= JUMP_HI) for a_, b in zip(seq, seq[1:])):
                excl["price_jump"] += 1
                continue
            s_prev, s_next, s_end = px[cal[i_prev]], px[cal[i_next]], px[cal[i_end]]
            m_prev, m_next, m_end = spy[cal[i_prev]], spy[cal[i_next]], spy[cal[i_end]]
            r_react = (s_next / s_prev - 1) - (m_next / m_prev - 1)
            r_drift = (s_end / s_next - 1) - (m_end / m_next - 1)
            ev = {**base,
                  "period": period_of(d),
                  "eps_actual": a, "eps_est": e,
                  "rev_actual": r.get("revenueActual"), "rev_est": r.get("revenueEstimated"),
                  "eps_surp_pct": surprise_pct(a, e, 0.01),
                  "rev_surp_pct": surprise_pct(r.get("revenueActual"), r.get("revenueEstimated"), 1.0),
                  "d_prev": cal[i_prev], "d_next": cal[i_next], "d_end": cal[i_end],
                  "r_react": round(r_react, 6), "r_drift": round(r_drift, 6),
                  "y_beat": (1 if a > e else 0) if a != e else None,
                  "y_react": int(r_react > 0), "y_drift": int(r_drift > 0)}
            events.append(ev)
            last_kept = d

    rng = random.Random(SEED)
    # controls subsample S: ALL events of 250 randomly drawn S&P 500 balanced-panel tickers
    # (well-known names, where a model with memory should show it)
    t_pre = {e["ticker"] for e in events if e["period"] in PRE}
    t_post = {e["ticker"] for e in events if e["period"] in POST}
    panel = t_pre & t_post
    pool = sorted(t for t in panel if t in sp_set)
    s_tickers = set(rng.sample(pool, min(SUBSAMPLE_TICKERS, len(pool))))
    sub_set = {e["event_id"] for e in events if e["ticker"] in s_tickers}
    rep = set(random.Random(SEED + 1).sample(sorted(e["event_id"] for e in events), REPEAT_N))
    for e in events:
        e["in_S"] = e["event_id"] in sub_set
        e["in_R"] = e["event_id"] in rep

    reqs = []
    for e in events:
        for arm in ("K", "N", "A"):
            reqs.append({"request_id": f"jev|{arm}|{e['event_id']}|r0", "model_key": "jev", "arm": arm,
                         "event_id": e["event_id"], "repeat": 0, "payload": jev_payload(arm, e, JEV_MODEL)})
        if e["in_R"]:
            for k in range(1, REPEAT_EXTRA + 1):
                reqs.append({"request_id": f"jev|K|{e['event_id']}|r{k}", "model_key": "jev", "arm": "K",
                             "event_id": e["event_id"], "repeat": k, "payload": jev_payload("K", e, JEV_MODEL)})
        if e["in_S"]:
            reqs.append({"request_id": f"sonnet5|K|{e['event_id']}|r0", "model_key": "sonnet5", "arm": "K",
                         "event_id": e["event_id"], "repeat": 0,
                         "payload": control_payload("K", e, CONTROL_MODELS["sonnet5"])})
            for arm in ("K", "N", "A"):
                reqs.append({"request_id": f"llama31|{arm}|{e['event_id']}|r0", "model_key": "llama31",
                             "arm": arm, "event_id": e["event_id"], "repeat": 0,
                             "payload": control_payload(arm, e, CONTROL_MODELS["llama31"])})
    for e in prosp:
        reqs.append({"request_id": f"jev|K|{e['event_id']}|prosp", "model_key": "jev", "arm": "K",
                     "event_id": e["event_id"], "repeat": 0, "prospective": True,
                     "payload": jev_payload("K", {**e, "eps_surp_pct": None, "rev_surp_pct": None}, JEV_MODEL)})
    random.Random(SEED + 2).shuffle(reqs)

    WORK.mkdir(parents=True, exist_ok=True)
    jsonl_write(WORK / "events.jsonl", events)
    jsonl_write(WORK / "prospective.jsonl", prosp)
    jsonl_write(WORK / "requests.jsonl", reqs)

    by_period = collections.Counter(e["period"] for e in events)
    by_period_sp = collections.Counter((e["period"], e["sp500"]) for e in events)
    tick_pre = {e["ticker"] for e in events if e["period"] in ("P1", "P2")}
    tick_post = {e["ticker"] for e in events if e["period"] == "P6"}
    base_rates = {}
    for y in ("y_beat", "y_react", "y_drift"):
        vals = [e[y] for e in events if e[y] is not None]
        base_rates[y] = round(sum(vals) / len(vals), 4) if vals else None
    import statistics as _st
    per = {}
    for name, _, _ in PERIODS:
        pe = [e for e in events if e["period"] == name]
        if not pe:
            continue
        surps = sorted(e["eps_surp_pct"] for e in pe if e["eps_surp_pct"] is not None)
        q = lambda f: surps[min(len(surps) - 1, int(f * len(surps)))] if surps else None  # noqa: E731
        per[name] = {
            "n": len(pe),
            "base_rates": {y: round(sum(e[y] for e in pe if e[y] is not None) /
                                    max(1, sum(1 for e in pe if e[y] is not None)), 4)
                           for y in ("y_beat", "y_react", "y_drift")},
            "sp500_share": round(sum(e["sp500"] for e in pe) / len(pe), 4),
            "eps_surp_pct_q10_q50_q90": [q(0.1), q(0.5), q(0.9)],
            "abs_eps_surp_over_50pct": sum(1 for e in pe if e["eps_surp_pct"] is not None and abs(e["eps_surp_pct"]) > 50),
            "season_counts": dict(sorted(collections.Counter(e["season"] for e in pe).items())),
            "sector_mix": dict(collections.Counter(e["sector"] for e in pe).most_common()),
        }
    manifest = {
        "built_utc": utc_now(),
        "by_period": per,
        "subsample_S_tickers": sorted(s_tickers),
        "universe": {"sp500": len(u["sp500"]), "non_sp": len(u["non_sp"])},
        "events": len(events),
        "events_by_period": dict(sorted(by_period.items())),
        "events_by_period_sp500": {f"{p}|{'sp' if s else 'non'}": n for (p, s), n in sorted(by_period_sp.items())},
        "tickers_with_events": len({e["ticker"] for e in events}),
        "balanced_panel_tickers": len(tick_pre & tick_post),
        "prospective_events": len(prosp),
        "subsample_S_events": len(sub_set),
        "repeat_R": len(rep),
        "requests_by_model": dict(collections.Counter(r["model_key"] for r in reqs)),
        "exclusions": dict(excl),
        "base_rates": base_rates,
        "beat_ties_excluded_from_k1": sum(1 for e in events if e["y_beat"] is None),
    }
    (WORK / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
