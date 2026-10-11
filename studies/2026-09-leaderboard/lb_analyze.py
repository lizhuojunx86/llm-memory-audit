"""Leaderboard analysis: pooled K within-company AUC (the jev-lookahead S10 statistic) per model, subsample S.

  python lb_analyze.py [--boot B] [--ties {demeaned,raw_tie_half,raw}]

Private data (raw model logs, event labels) is not in the published tree. Point the
script at it with environment variables (defaults resolve inside the published tree):

  LMA_JEV_PRIVATE   Jev study private dir  (work/events.jsonl, runs/*.jsonl)
                    default: studies/2026-09-jev
  LMA_LB_PRIVATE    leaderboard round-1 private dir (runs/*.jsonl, runs_local/von.jsonl)
                    default: this directory
  LMA_ADD2_PRIVATE  leaderboard addendum-2 private dir (runs/*.jsonl)
                    default: this directory / add2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JL = HERE.parent / "2026-09-jev"
sys.path.insert(0, str(JL / "src"))
import analyze as A  # noqa: E402
from common import SEED  # noqa: E402
from payloads import ARM_QUESTIONS  # noqa: E402

KQ = ("k1_beat", "k2_react", "k3_drift")
EXISTING = {"jev": "typesafe/jev-1.13-20260917", "sonnet5": "anthropic/claude-sonnet-5",
            "llama31": "meta-llama/llama-3.1-70b-instruct"}
YEARS = (2023, 2024, 2025, 2026)
# 2025 and 2026 events post-date most models' training data: a placebo, not a memory test.
WITHIN_YEAR_NOTE = ("pairs are two events of the same ticker and the same question inside one calendar "
                    "year; seasons necessarily differ, so this is NOT season-matched. 2025 and 2026 are a "
                    "placebo (those events post-date most models' training data).")
# Pairs where both events fall on or after this date post-date the latest published training cutoff
# among the models tested (GPT-6 Astra: 2026-04-30). Any within-company AUC above 0.5 here cannot be
# recall of the outcome, so this bounds the non-memory channels (date heuristics, trend knowledge).
POST_CUTOFF_DATE = "2026-05-01"
POST_CUTOFF_NOTE = ("pairs are two events of the same ticker and the same question, both dated on or after "
                    f"{POST_CUTOFF_DATE}; not season-matched. Bounds the non-memory channels.")


def private_roots() -> tuple[Path, Path, Path]:
    """(jev_private, lb_private, add2_private) from env vars with published-tree defaults."""
    jev = Path(os.environ.get("LMA_JEV_PRIVATE", str(JL)))
    lb = Path(os.environ.get("LMA_LB_PRIVATE", str(HERE)))
    add2 = Path(os.environ.get("LMA_ADD2_PRIVATE", str(HERE / "add2")))
    return jev, lb, add2


def require_private_files() -> tuple[Path, Path, Path]:
    """Exit with one clear message listing what is needed and which env var to set."""
    jev, lb, add2 = private_roots()
    checks = [
        (jev / "work" / "events.jsonl", "LMA_JEV_PRIVATE", "work/events.jsonl"),
        (jev / "runs", "LMA_JEV_PRIVATE", "runs/*.jsonl (jev, sonnet5, llama31)"),
        (lb / "runs", "LMA_LB_PRIVATE", "runs/*.jsonl (8 round-1 models)"),
        (add2 / "runs", "LMA_ADD2_PRIVATE", "runs/*.jsonl (4 addendum-2 models)"),
    ]
    missing = []
    for path, env, what in checks:
        if path.suffix:
            ok = path.is_file()
        else:
            ok = path.is_dir() and any(path.glob("*.jsonl"))
        if not ok:
            missing.append(f"  {path}  — expected {what}; set {env}")
    if missing:
        raise SystemExit("Missing private leaderboard files:\n" + "\n".join(missing)
                         + "\nRaw model logs and labels are not in the published tree.")
    return jev, lb, add2


def load_lb(lb_runs: Path, add2_runs: Path):
    outs, quality, cost = {}, {}, {}
    for p in sorted(list(lb_runs.glob("*.jsonl")) + list(add2_runs.glob("*.jsonl"))):
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


def _pair_ok_post_cutoff_same_q(a: dict, b: dict) -> bool:
    return a["q"] == b["q"] and a["date"] >= POST_CUTOFF_DATE and b["date"] >= POST_CUTOFF_DATE


def _pair_ok_within_year_same_q(year: int):
    """Same year and same question (from analyze._pair_ok_within_year + a same-question check)."""
    base = A._pair_ok_within_year(year)
    return lambda a, b: a["q"] == b["q"] and base(a, b)


def main(boot: int = 2000, ties: str = "demeaned") -> None:
    B = boot
    jev_private, lb_private, add2_private = require_private_files()
    # common.RUNS/WORK honour LMA_JEV_PRIVATE; reload outputs through the resolved Jev runs dir
    events = {e["event_id"]: e for e in A.jsonl_read(jev_private / "work" / "events.jsonl")}
    old, _ = A.load_outputs()
    new, quality, cost = load_lb(lb_private / "runs", add2_private / "runs")
    outs = {**old, **new}
    vf = lb_private / "runs_local" / "von.jsonl"
    if vf.exists():
        for r in A.jsonl_read(vf):
            outs[("von", "K", r["event_id"], 0, False)] = {k: float(v) for k, v in r["answers"].items()}
        EXISTING["von"] = "wfzyx/von (von-1.2.0, local CPU)"
    models = json.loads((HERE / "models.json").read_text())
    models2 = json.loads((HERE / "add2" / "models.json").read_text()) if (HERE / "add2" / "models.json").exists() else {}

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
    if ties != "demeaned":
        res["ties_policy"] = ties
    allm = {**models, **models2}
    for m in list(EXISTING) + list(allm):
        per = rows(m)
        pooled = [r for _, rr in per for r in rr]
        if not pooled:
            continue
        entry = {"model_id": EXISTING.get(m) or allm[m][0], "settings": None if m in EXISTING else allm[m][1],
                 "family": "main" if m in models else ("addendum2" if m in models2 else "existing"),
                 "pooled_K": A.wt_auc_test(pooled, "s_dm", A._pair_ok_pre_same_q, B, SEED + 1004, ties=ties),
                 "per_question": {qid: A.wt_auc_test(rr, "s_dm", A._pair_ok_pre, B, SEED + 1001, ties=ties)
                                  for qid, rr in per},
                 "answers": len({(r["ticker"], r["date"]) for r in pooled})}
        # within-company AUC pooled over the three questions, pairs inside each single year
        wy = {"note": WITHIN_YEAR_NOTE}
        for y in YEARS:
            wy[str(y)] = {tp: A.wt_auc_test(pooled, "s_dm", _pair_ok_within_year_same_q(y), B, SEED + 1005, ties=tp)
                          for tp in A.TIE_POLICIES}
        entry["within_year"] = wy
        entry["post_cutoff"] = {"note": POST_CUTOFF_NOTE, "date": POST_CUTOFF_DATE}
        for tp in A.TIE_POLICIES:
            entry["post_cutoff"][tp] = A.wt_auc_test(pooled, "s_dm", _pair_ok_post_cutoff_same_q, B, SEED + 1006, ties=tp)
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
    out_dir = HERE / "results" if ties == "demeaned" else HERE / "results" / f"ties_{ties}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "leaderboard.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
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
    # placebo table: within-year AUC per calendar year, plus pairs both dated on/after POST_CUTOFF_DATE
    def _cell(t):
        return "–" if not t or t.get("estimate") is None else f"{t['estimate']:.3f} ({t['ci95'][0]:.3f} to {t['ci95'][1]:.3f}, n={t['pairs']})"
    P = [f"\nWithin-company AUC under tie policy `{ties}`, pairs inside one calendar year (not season-matched), "
         f"and pairs with both events on or after {POST_CUTOFF_DATE}.\n",
         "| Model | " + " | ".join(str(y) for y in YEARS) + f" | both ≥ {POST_CUTOFF_DATE} |",
         "|---|" + "---|" * (len(YEARS) + 1)]
    for m in order:
        v = res["models"][m]
        P.append(f"| {v['model_id']} | " + " | ".join(_cell(v["within_year"][str(y)][ties]) for y in YEARS)
                 + f" | {_cell(v['post_cutoff'][ties])} |")
    (out_dir / "leaderboard.md").write_text("\n".join(L) + "\n" + "\n".join(P) + "\n")
    print("\n".join(L))
    print("\n".join(P))
    print(json.dumps({m: {"quality": v.get("quality"), "cost": v.get("cost_usd")} for m, v in res["models"].items() if m in allm}, indent=0))


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Leaderboard analysis: pooled K within-company AUC per model.")
    ap.add_argument("--boot", type=int, default=2000,
                    help="ticker bootstrap replicates B (default 2000)")
    ap.add_argument("--ties", choices=list(A.TIE_POLICIES), default="demeaned",
                    help="tie policy for the within-company statistic (default: demeaned)")
    a = ap.parse_args()
    main(a.boot, ties=a.ties)


if __name__ == "__main__":
    _cli()
