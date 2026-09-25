"""Run von (wfzyx/von, Jev-style open model) on the leaderboard's K-arm inputs, locally on CPU.

  python von_run.py smoke            # one fictional-company call
  python von_run.py run [--limit N]  # subsample S events from the public events.csv, resumable

Inputs are public (llm-memory-audit studies/2026-09-jev/public_data/events.csv): company, ticker,
exchange, sector and date only. Same state and noul questions as Jev's K arm. No labels here.
"""
import csv, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "lma/studies/2026-09-jev"
sys.path.insert(0, str(STUDY / "src"))
from payloads import K_QUESTIONS, state_for  # noqa: E402
import von  # noqa: E402

OUT = HERE / "von_outputs.jsonl"
FICT = {"company": "Acme Widgets Holdings Inc.", "ticker": "ACMW", "exchange": "NASDAQ", "sector": "Industrials", "date": "2024-05-01"}


def questions():
    return {qid: von.noul(instructions=q["instructions"], criteria=q["criteria"]) for qid, q in K_QUESTIONS.items()}


def one(ev):
    t0 = time.time()
    r = von.system_one(state=state_for("K", ev), questions=questions())
    return {qid: float(r.answers[qid].noul) for qid in K_QUESTIONS}, int((time.time() - t0) * 1000)


def main():
    if sys.argv[1] == "smoke":
        print(one(FICT))
        print(one(FICT))
        return
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    evs = [r for r in csv.DictReader(open(STUDY / "public_data/events.csv", encoding="utf-8")) if r["in_S"] == "True"]
    done = {json.loads(l)["event_id"] for l in open(OUT)} if OUT.exists() else set()
    todo = [e for e in evs if e["event_id"] not in done][:limit]
    print(f"S events {len(evs)}, done {len(done)}, to run {len(todo)}", flush=True)
    with open(OUT, "a", encoding="utf-8") as f:
        for i, e in enumerate(todo):
            ans, ms = one(e)
            f.write(json.dumps({"event_id": e["event_id"], "model_key": "von", "answers": ans, "latency_ms": ms,
                                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
            if i % 200 == 0:
                f.flush(); print(i, ms, flush=True)


if __name__ == "__main__":
    main()
