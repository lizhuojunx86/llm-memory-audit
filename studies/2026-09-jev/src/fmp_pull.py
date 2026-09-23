"""Pull the study universe and raw FMP data. Resumable; safe to re-run.

  python src/fmp_pull.py universe            # S&P 500 (one symbol per CIK) + 400 random PEAD tickers
  python src/fmp_pull.py fetch --max-seconds 150

Raw payloads land in data/fmp/{profile,earnings,prices}/<SYMBOL>.json.gz.
The API key is never logged; fetch_log.jsonl records endpoint, symbol, status, bytes.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import (DATA, FMP_BASE, N_NON_SP, PRICE_FROM, PRICE_TO, SEED, STUDY_START,  # noqa: E402
                    fmp_key, gz_json_write, pead_universe_csv, utc_now)

UNIVERSE = DATA / "universe.json"
LOG = DATA / "fetch_log.jsonl"
SYMBOL_OK = re.compile(r"^[A-Z]{1,5}$")
_log_lock = threading.Lock()


def _get(session: requests.Session, path: str, params: dict, key: str):
    r = session.get(f"{FMP_BASE}/{path}", params={**params, "apikey": key}, timeout=60)
    return r.status_code, (r.json() if r.status_code == 200 else None), len(r.content)


def cmd_universe(_args) -> None:
    if UNIVERSE.exists():
        print(f"universe exists: {UNIVERSE}")
        return
    key = fmp_key()
    s = requests.Session()
    status, sp, _ = _get(s, "sp500-constituent", {}, key)
    if status != 200 or not sp:
        raise SystemExit(f"sp500-constituent failed: {status}")
    by_cik: dict[str, str] = {}
    for row in sorted(sp, key=lambda r: r["symbol"]):
        sym = row["symbol"].replace(".", "-")
        cik = row.get("cik") or sym
        by_cik.setdefault(cik, sym)
    sp_syms = sorted(by_cik.values())
    sp_all = {r["symbol"].replace(".", "-") for r in sp}

    cands = set()
    with open(pead_universe_csv(), newline="") as f:
        for r in csv.DictReader(f):
            t = r["ticker"].strip().upper()
            if r["announce_date"] >= STUDY_START.isoformat() and SYMBOL_OK.match(t) and t not in sp_all:
                cands.add(t)
    rng = random.Random(SEED)
    non_sp = sorted(rng.sample(sorted(cands), N_NON_SP))
    out = {
        "created_utc": utc_now(),
        "seed": SEED,
        "sp500_source": "FMP /stable/sp500-constituent (current membership at pull time)",
        "sp500_raw_count": len(sp),
        "sp500": sp_syms,
        "non_sp_source": f"random {N_NON_SP} of {len(cands)} PEAD-universe tickers with an event on/after "
                         f"{STUDY_START}, symbol ^[A-Z]{{1,5}}$, not S&P 500 members",
        "non_sp": non_sp,
    }
    UNIVERSE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE.write_text(json.dumps(out, indent=1))
    print(f"S&P 500: {len(sp_syms)} (raw {len(sp)}), non-S&P: {len(non_sp)} of {len(cands)} candidates")


def _targets() -> list[tuple[str, str, dict]]:
    u = json.loads(UNIVERSE.read_text())
    syms = u["sp500"] + u["non_sp"]
    t = []
    for sym in syms + ["SPY"]:
        t.append(("prices", sym, {"symbol": sym, "from": PRICE_FROM.isoformat(), "to": PRICE_TO.isoformat()}))
        if sym == "SPY":
            continue
        t.append(("profile", sym, {"symbol": sym}))
        t.append(("earnings", sym, {"symbol": sym, "limit": 40}))
    return t


ENDPOINT = {"prices": "historical-price-eod/full", "profile": "profile", "earnings": "earnings"}


def cmd_fetch(args) -> None:
    key = fmp_key()
    todo = [(kind, sym, p) for kind, sym, p in _targets()
            if not (DATA / "fmp" / kind / f"{sym}.json.gz").exists()]
    print(f"to fetch: {len(todo)}")
    if not todo:
        return
    deadline = time.monotonic() + args.max_seconds
    interval = 1.0 / args.rate
    next_slot = [time.monotonic()]
    slot_lock = threading.Lock()
    session = requests.Session()
    done = failed = 0

    def work(item):
        kind, sym, params = item
        with slot_lock:
            now = time.monotonic()
            slot = max(now, next_slot[0])
            if slot > deadline:
                return "skipped"
            next_slot[0] = slot + interval
        if slot > now:
            time.sleep(slot - now)
        for attempt in range(4):
            try:
                status, body, nbytes = _get(session, ENDPOINT[kind], params, key)
            except requests.RequestException as e:
                status, body, nbytes = -1, None, 0
                err = type(e).__name__
            else:
                err = None
            if status in (429, 500, 502, 503, 504, -1):
                time.sleep(2 ** attempt)
                continue
            break
        with _log_lock:
            with open(LOG, "a") as f:
                f.write(json.dumps({"utc": utc_now(), "kind": kind, "symbol": sym, "status": status,
                                    "bytes": nbytes, "error": err}) + "\n")
        if status == 200 and body is not None:
            gz_json_write(DATA / "fmp" / kind / f"{sym}.json.gz",
                          {"fetched_utc": utc_now(), "endpoint": ENDPOINT[kind],
                           "params": params, "body": body})
            return "ok"
        return f"fail:{status}"

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, it) for it in todo]
        for fu in as_completed(futs):
            r = fu.result()
            if r == "ok":
                done += 1
            elif r.startswith("fail"):
                failed += 1
    left = len([1 for kind, sym, _ in _targets() if not (DATA / "fmp" / kind / f"{sym}.json.gz").exists()])
    print(f"fetched {done}, failed {failed}, remaining {left}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("universe")
    f = sub.add_parser("fetch")
    f.add_argument("--max-seconds", type=float, default=150)
    f.add_argument("--rate", type=float, default=5.0, help="requests per second")
    f.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    {"universe": cmd_universe, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()
