"""Send frozen requests to one model. Resumable, time-boxed, spend-capped.

  python src/run_models.py --model jev --max-seconds 150
  python src/run_models.py --model sonnet5 --max-seconds 150
  python src/run_models.py --model llama31 --max-seconds 150
  python src/run_models.py --model jev --only-prospective ...

Refuses to run unless work/freeze.json exists and its request digest matches
work/requests.jsonl (so nothing is sent before the protocol is frozen).
Responses append to runs/<model>.jsonl. The API key is never logged.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BUDGET_USD, OPENROUTER_BASE, ROOT, RUNS, WORK, jsonl_read, openrouter_key,  # noqa: E402
                    sha256_file, utc_now)

TRANSIENT = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


def spent_usd() -> float:
    total = 0.0
    for p in RUNS.rglob("*.jsonl"):   # includes runs/_superseded/
        for r in jsonl_read(p):
            c = (r.get("usage") or {}).get("cost")
            if isinstance(c, (int, float)):
                total += c
    return total


def check_frozen() -> None:
    fz = ROOT / "freeze.json"
    if not fz.exists():
        raise SystemExit("freeze.json missing: freeze the protocol before sending study requests")
    f = json.loads(fz.read_text())
    if f["files"].get("work/requests.jsonl") != sha256_file(WORK / "requests.jsonl"):
        raise SystemExit("work/requests.jsonl does not match freeze.json")


def endpoint(model_key: str) -> str:
    return f"{OPENROUTER_BASE}/systemone" if model_key == "jev" else f"{OPENROUTER_BASE}/chat/completions"


def call(session: requests.Session, key: str, req: dict, timeout: float, override: dict | None = None) -> dict:
    t0 = time.monotonic()
    sent = utc_now()
    if override:
        req = {**req, "payload": {**req["payload"], **override}}
    status, body, err = -1, None, None
    for attempt in range(6):
        try:
            r = session.post(endpoint(req["model_key"]), json=req["payload"], timeout=timeout,
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                      "X-Title": "jev-lookahead-prereg"})
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
    out = {"request_id": req["request_id"], "model_key": req["model_key"], "arm": req["arm"],
           "payload_override": override or None,
           "event_id": req["event_id"], "repeat": req["repeat"], "prospective": req.get("prospective", False),
           "sent_utc": sent, "recv_utc": utc_now(), "latency_ms": int((time.monotonic() - t0) * 1000),
           "http_status": status, "error": err, "attempts": attempt + 1}
    if req["model_key"] == "jev":
        out["response"] = body
        out["usage"] = (body or {}).get("usage") if isinstance(body, dict) else None
        out["served_model"] = (body or {}).get("model") if isinstance(body, dict) else None
    else:
        choice = ((body or {}).get("choices") or [{}])[0] if isinstance(body, dict) else {}
        out["content"] = ((choice.get("message") or {}).get("content")) if choice else None
        out["finish_reason"] = choice.get("finish_reason") if choice else None
        out["usage"] = (body or {}).get("usage") if isinstance(body, dict) else None
        out["served_model"] = (body or {}).get("model") if isinstance(body, dict) else None
        if status != 200:
            out["response"] = body
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["jev", "sonnet5", "llama31"])
    ap.add_argument("--max-seconds", type=float, default=150)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--only-prospective", action="store_true")
    ap.add_argument("--retry-failed", action="store_true", help="re-send requests whose last record is non-200")
    ap.add_argument("--override", default=None,
                    help="JSON merged into each payload at send time (post-freeze deviation; see DEVIATIONS.md)")
    a = ap.parse_args()

    check_frozen()
    override = json.loads(a.override) if a.override else None
    if override and a.model == "jev":
        raise SystemExit("no overrides for Jev: its requests stay exactly as frozen")
    out_path = RUNS / f"{a.model}.jsonl"
    RUNS.mkdir(parents=True, exist_ok=True)
    last = {}
    for r in jsonl_read(out_path):
        last[r["request_id"]] = r
    done = {rid for rid, r in last.items() if r["http_status"] == 200 or not a.retry_failed}
    reqs = [r for r in jsonl_read(WORK / "requests.jsonl")
            if r["model_key"] == a.model and r["request_id"] not in done
            and (r.get("prospective", False) if a.only_prospective else True)]
    print(f"{a.model}: {len(reqs)} to send; spent so far ${spent_usd():.4f}")
    if not reqs:
        return
    if spent_usd() >= BUDGET_USD:
        raise SystemExit("budget reached")

    key = openrouter_key()
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=a.concurrency, pool_maxsize=a.concurrency)
    session.mount("https://", adapter)
    lock = threading.Lock()
    deadline = time.monotonic() + a.max_seconds
    it = iter(reqs)
    n_ok = n_fail = 0
    cost = 0.0
    spent0 = spent_usd()
    with open(out_path, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        pending = set()
        exhausted = False
        while True:
            if spent0 + cost >= BUDGET_USD:
                exhausted = True
            while not exhausted and len(pending) < a.concurrency and time.monotonic() < deadline:
                nxt = next(it, None)
                if nxt is None:
                    exhausted = True
                    break
                pending.add(ex.submit(call, session, key, nxt, a.timeout, override))
            if not pending:
                break
            finished, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fu in finished:
                rec = fu.result()
                with lock:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
                if rec["http_status"] == 200:
                    n_ok += 1
                else:
                    n_fail += 1
                c = (rec.get("usage") or {}).get("cost")
                if isinstance(c, (int, float)):
                    cost += c
            if time.monotonic() >= deadline:
                exhausted = True
    left = len(reqs) - n_ok - n_fail
    print(f"{a.model}: ok {n_ok}, non-200 {n_fail}, not sent {left}, cost this run ${cost:.4f}, "
          f"total spent ${spent_usd():.4f}")


if __name__ == "__main__":
    main()
