"""Leaderboard analysis: pooled K within-company AUC (the jev-lookahead S10 statistic) per model, subsample S."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JL = HERE.parent / "jev-lookahead"
sys.path.insert(0, str(JL / "src"))
import analyze as A  # noqa: E402
from common import SEED  # noqa: E402
from payloads import ARM_QUESTIONS  # noqa: E402

KQ = ("k1_beat", "k2_react", "k3_drift")
EXISTING = {"jev": "typesafe/jev-1.13-20260917", "sonnet5": "anthropic/claude-sonnet-5",
            "llama31": "meta-llama/llama-3.1-70b-instruct"}


ADD2 = HERE.parent / "memory-leaderboard-add2"


def load_lb():
    outs, quality, cost = {}, {}, {}
    for p in sorted(list((HERE / "runs").glob("*.jsonl")) + list((ADD2 / "runs").glob("*.jsonl"))):
        last = {}
        for r in A.jsonl_read(p):
            if r["http_status"] == 200 or r["request_id"] not in last:
                last[r["request_id"]] = r
        q = {"records": 0, "http_200": 0, "incomplete": 0, "served": {}}
        c = 0.0
        for r in A.jsonl_read(p):
            v = (r.get("usage") or {}).get("cost")
            c += v if isinstance(v, (int, float)) else 0
        for r in last.values():
            q["records"] += 1
            if r["http_status"] != 200:
                continue
            q["http_200"] += 1
            q["served"][r.get("served_model")] = q["served"].get(r.get("served_model"), 0) + 1
            ps = A.parse_control(r.get("content"), list(KQ))
            if len(ps) < 3:
                q["incomplete"] += 1
            outs[(r["model_key"], "K", r["event_id"], 0, False)] = ps
        quality[p.stem], cost[p.stem] = q, round(c, 4)
    return outs, quality, cost


def main(boot: int = 10000) -> None:
    B = boot // 5
    events = {e["event_id"]: e for e in A.jsonl_read(JL / "work/events.jsonl")}
    old, _ = A.load_outputs()
    new, quality, cost = load_lb()
    outs = {**old, **new}
    vf = HERE / "runs_local/von.jsonl"
    if vf.exists():
        for r in A.jsonl_read(vf):
            outs[("von", "K", r["event_id"], 0, False)] = {k: float(v) for k, v in r["answers"].items()}
        EXISTING["von"] = "wfzyx/von (von-1.2.0, local CPU)"
    models = json.loads((HERE / "models.json").read_text())
    models2 = json.loads((ADD2 / "models.json").read_text()) if (ADD2 / "models.json").exists() else {}

    def rows(model):
        out = []
        for qid in KQ:
            rr = []
            for eid, e in events.items():
                if not e.get("in_S"):
                    continue
                y = e[A.LABEL_OF[qid]]
                p = outs.get((model, "K", eid, 0, False), {}).get(qid)
                if y is None or p is None:
                    continue
                rr.append({"s": p, "y": y, "ticker": e["ticker"], "grp": A.grp_of(e["period"]), "date": e["date"],
                           "period": e["period"], "year": e["year"], "season": e["season"], "month": e["month"], "q": qid})
            A.demean_by_month(rr, ("s",))
            out.append((qid, rr))
        return out

    res = {"B": B, "models": {}}
    allm = {**models, **models2}
    for m in list(EXISTING) + list(allm):
        per = rows(m)
        pooled = [r for _, rr in per for r in rr]
        if not pooled:
            continue
        entry = {"model_id": EXISTING.get(m) or allm[m][0], "settings": None if m in EXISTING else allm[m][1],
                 "family": "main" if m in models else ("addendum2" if m in models2 else "existing"),
                 "pooled_K": A.wt_auc_test(pooled, "s_dm", A._pair_ok_pre_same_q, B, SEED + 1004),
                 "per_question": {qid: A.wt_auc_test(rr, "s_dm", A._pair_ok_pre, B, SEED + 1001) for qid, rr in per},
                 "answers": len({(r["ticker"], r["date"]) for r in pooled})}
        if m in quality:
            entry["quality"], entry["cost_usd"] = quality[m], cost[m]
            entry["partial"] = quality[m]["http_200"] < 3708
        res["models"][m] = entry
    new_p = {m: v["pooled_K"]["p_one_sided"] for m, v in res["models"].items() if m in models}
    res["holm_new_models"] = A.holm(new_p) if new_p else {}
    new_p2 = {m: v["pooled_K"]["p_one_sided"] for m, v in res["models"].items() if m in models2 and not v.get("partial")}
    res["holm_add2"] = A.holm(new_p2) if new_p2 else {}
    if "von" in res["models"]:
        res["holm_von"] = A.holm({"von": res["models"]["von"]["pooled_K"]["p_one_sided"]})
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/leaderboard.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    L = ["| Model | Pooled within-company AUC (95% CI) | Pairs | Memory (Holm, one-sided 5%) | Reasoning |", "|---|---|---|---|---|"]
    order = sorted(res["models"], key=lambda m: -res["models"][m]["pooled_K"]["estimate"])
    for m in order:
        v = res["models"][m]
        pk = v["pooled_K"]
        verdict = ("yes" if (res["holm_new_models"].get(m) or res.get("holm_add2", {}).get(m) or res.get("holm_von", {}).get(m) or {}).get("reject_null") else "no") if (m in allm or m == "von") else (
            "yes (control)" if m == "sonnet5" else "no")
        if v.get("partial"):
            verdict = "partial"
        s = v["settings"] or {}
        reason = "off" if (s.get("reasoning") or {}).get("enabled") is False else ("low (mandatory)" if s else
                                                                                 ("off" if m == "sonnet5" else "n/a"))
        if m == "von":
            reason = "n/a (local)"
        L.append(f"| {v['model_id']} | {pk['estimate']:.3f} ({pk['ci95'][0]:.3f} to {pk['ci95'][1]:.3f}) | {pk['pairs']} | {verdict} | {reason} |")
    (HERE / "results/leaderboard.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(json.dumps({m: {"quality": v.get("quality"), "cost": v.get("cost_usd")} for m, v in res["models"].items() if m in allm}, indent=0))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10000)
