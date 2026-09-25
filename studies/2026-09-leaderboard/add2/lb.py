"""Model memory leaderboard v0: the jev-lookahead K-arm probe on subsample S, for more models.

  python lb.py models              # list candidate OpenRouter models with prices (read-only)
  python lb.py smoke               # fictional-company call per model (pre-freeze settings check)
  python lb.py build               # write work/requests.jsonl for MODELS
  python lb.py freeze              # hash protocol, code and requests; OpenTimestamps stamp
  python lb.py run KEY [--max-seconds S] [--concurrency C]
  python lb.py analyze [--boot B]  # results/leaderboard.{json,md}

Same prompt, events, labels and statistics as the Sonnet 5 / Llama control in
../jev-lookahead (PREREG section 6 and S10); see PREREG_LB.md. API keys are never logged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

HERE = Path(__file__).resolve().parent
JL = HERE.parent / "jev-lookahead"
sys.path.insert(0, str(JL / "src"))
import requests  # noqa: E402
from common import OPENROUTER_BASE, openrouter_key, utc_now  # noqa: E402
from payloads import control_payload  # noqa: E402

WORK, RUNS, RESULTS, PRE = HERE / "work", HERE / "runs", HERE / "results", HERE / "preflight"
BUDGET_USD = 50.0
# key -> (OpenRouter model id, extra payload fields). Settings fixed from the smoke run, before freezing.
MODELS: dict[str, tuple[str, dict]] = json.loads((HERE / "models.json").read_text()) if (HERE / "models.json").exists() else {}
TRANSIENT = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}
FICTIONAL = {"event_id": "ACMW|2024-05-01", "ticker": "ACMW", "company": "Acme Widgets Holdings Inc.",
             "exchange": "NASDAQ", "sector": "Industrials", "date": "2024-05-01"}


def jl(path: Path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def payload_for(key: str, ev: dict) -> dict:
    mid, extra = MODELS[key]
    p = control_payload("K", ev, mid)
    p.update(extra)
    return p


def post(session, key_, payload, timeout=90):
    status, body, err = -1, None, None
    for attempt in range(6):
        try:
            r = session.post(f"{OPENROUTER_BASE}/chat/completions", json=payload, timeout=timeout,
                             headers={"Authorization": f"Bearer {key_}", "Content-Type": "application/json",
                                      "X-Title": "llm-memory-leaderboard"})
            status = r.status_code
            try:
                body = r.json()
            except ValueError:
                body = {"_raw_text": r.text[:2000]}
            err = None
        except requests.RequestException as e:
            status, body, err = -1, None, type(e).__name__
        if status in TRANSIENT or status == -1:
            time.sleep(min(30, 1.5 * 2 ** attempt))
            continue
        break
    return status, body, err, attempt + 1


def record(req, status, body, err, attempts, t0, sent):
    choice = ((body or {}).get("choices") or [{}])[0] if isinstance(body, dict) else {}
    out = {"request_id": req["request_id"], "model_key": req["model_key"], "arm": "K", "event_id": req["event_id"],
           "repeat": 0, "prospective": False, "sent_utc": sent, "recv_utc": utc_now(),
           "latency_ms": int((time.monotonic() - t0) * 1000), "http_status": status, "error": err, "attempts": attempts,
           "content": ((choice.get("message") or {}).get("content")) if choice else None,
           "finish_reason": choice.get("finish_reason") if choice else None,
           "usage": (body or {}).get("usage") if isinstance(body, dict) else None,
           "served_model": (body or {}).get("model") if isinstance(body, dict) else None}
    if status != 200:
        out["response"] = body
    return out


def spent() -> float:
    return sum(((r.get("usage") or {}).get("cost") or 0) for p in list(RUNS.glob("*.jsonl")) + list(PRE.glob("*.jsonl"))
               for r in jl(p) if isinstance((r.get("usage") or {}).get("cost"), (int, float)))


def cmd_models(_):
    k = openrouter_key()
    m = requests.get(f"{OPENROUTER_BASE}/models", headers={"Authorization": f"Bearer {k}"}, timeout=60).json()["data"]
    for x in m:
        if any(s in x["id"] for s in ("bosun", "von", "jeff", "verdict", "hanno", "jev")):
            print(x["id"], x.get("pricing", {}).get("prompt"), x.get("pricing", {}).get("completion"))


def cmd_smoke(_):
    k = openrouter_key()
    s = requests.Session()
    PRE.mkdir(exist_ok=True)
    with open(PRE / "smoke.jsonl", "a", encoding="utf-8") as f:
        for key in MODELS:
            req = {"request_id": f"smoke|{key}", "model_key": key, "event_id": FICTIONAL["event_id"]}
            t0, sent = time.monotonic(), utc_now()
            st, body, err, att = post(s, k, payload_for(key, FICTIONAL))
            rec = record(req, st, body, err, att, t0, sent)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            u = rec.get("usage") or {}
            print(f"{key:10s} {st} fin={rec['finish_reason']} served={rec['served_model']} "
                  f"reason_tok={(u.get('completion_tokens_details') or {}).get('reasoning_tokens')} "
                  f"out_tok={u.get('completion_tokens')} cost={u.get('cost')} content={str(rec['content'])[:90]!r}")


def cmd_build(_):
    evs = [e for e in jl(JL / "work/events.jsonl") if e.get("in_S")]
    WORK.mkdir(exist_ok=True)
    n = 0
    with open(WORK / "requests.jsonl", "w", encoding="utf-8") as f:
        for key in MODELS:
            for e in evs:
                f.write(json.dumps({"request_id": f"lb|{key}|K|{e['event_id']}", "model_key": key, "arm": "K",
                                    "event_id": e["event_id"], "repeat": 0, "payload": payload_for(key, e)},
                                   ensure_ascii=False) + "\n")
                n += 1
    print(f"{len(evs)} S events x {len(MODELS)} models = {n} requests")


def cmd_freeze(_):
    fz = HERE / "freeze.json"
    if fz.exists() or any(RUNS.glob("*.jsonl")):
        raise SystemExit("already frozen or runs exist")
    files = ["PREREG_LB.md", "lb.py", "models.json", "work/requests.jsonl", "preflight/smoke.jsonl",
             "../jev-lookahead/freeze.json", "../jev-lookahead/work/events.jsonl"]
    out = {"frozen_utc": utc_now(), "files": {p: sha256(HERE / p) for p in files},
           "note": "No leaderboard request had been sent to any model when this file was written (smoke calls use a fictional company)."}
    fz.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    print(subprocess.run(["ots", "stamp", str(fz)], capture_output=True, text=True))


def cmd_run(a):
    fz = json.loads((HERE / "freeze.json").read_text())
    if fz["files"]["work/requests.jsonl"] != sha256(WORK / "requests.jsonl"):
        raise SystemExit("requests do not match freeze.json")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{a.key}.jsonl"
    done = {r["request_id"] for r in jl(out) if r["http_status"] == 200 or not a.retry_failed}
    reqs = [r for r in jl(WORK / "requests.jsonl") if r["model_key"] == a.key and r["request_id"] not in done]
    print(f"{a.key}: {len(reqs)} to send; spent so far ${spent():.3f}", flush=True)
    if not reqs:
        return
    k = openrouter_key()
    s = requests.Session()
    s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=a.concurrency, pool_maxsize=a.concurrency))
    lock, deadline, cost, n_ok, n_bad = threading.Lock(), time.monotonic() + a.max_seconds, 0.0, 0, 0
    spent0 = spent()

    def one(req):
        t0, sent = time.monotonic(), utc_now()
        st, body, err, att = post(s, k, req["payload"])
        return record(req, st, body, err, att, t0, sent)

    it = iter(reqs)
    with open(out, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        pending, exhausted = set(), False
        while True:
            if spent0 + cost >= BUDGET_USD or time.monotonic() >= deadline:
                exhausted = True
            while not exhausted and len(pending) < a.concurrency:
                nxt = next(it, None)
                if nxt is None:
                    exhausted = True
                    break
                pending.add(ex.submit(one, nxt))
            if not pending:
                break
            fin, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fu in fin:
                rec = fu.result()
                with lock:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
                n_ok += rec["http_status"] == 200
                n_bad += rec["http_status"] != 200
                c = (rec.get("usage") or {}).get("cost")
                cost += c if isinstance(c, (int, float)) else 0
    print(f"{a.key}: ok {n_ok}, non-200 {n_bad}, cost this run ${cost:.3f}, total ${spent():.3f}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models")
    sub.add_parser("smoke")
    sub.add_parser("build")
    sub.add_parser("freeze")
    r = sub.add_parser("run")
    r.add_argument("key")
    r.add_argument("--max-seconds", type=float, default=3600)
    r.add_argument("--concurrency", type=int, default=12)
    r.add_argument("--retry-failed", action="store_true")
    an = sub.add_parser("analyze")
    an.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    if a.cmd == "analyze":
        import lb_analyze
        lb_analyze.main(a.boot)
    else:
        {"models": cmd_models, "smoke": cmd_smoke, "build": cmd_build, "freeze": cmd_freeze, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
