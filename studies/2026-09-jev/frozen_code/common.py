"""Shared configuration and helpers for the Jev look-ahead experiment.

Directory layout (relative to the experiment root):
  data/     private  raw FMP cache (vendor data, never publish)
  work/     private  events, labels, request payloads (vendor-derived numbers)
  runs/     private  raw model responses
  results/  public   aggregate tables only
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import pathlib
import re
from typing import Iterable, Iterator

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORK = ROOT / "work"
RUNS = ROOT / "runs"
RESULTS = ROOT / "results"

SEED = 20260923

STUDY_START = dt.date(2023, 1, 1)
STUDY_END = dt.date(2026, 8, 14)
PROSP_START = dt.date(2026, 10, 1)
PROSP_END = dt.date(2026, 11, 30)
PRICE_FROM = dt.date(2022, 11, 1)
PRICE_TO = dt.date(2026, 9, 22)

N_NON_SP = 400          # random non-S&P 500 tickers from the PEAD universe
DRIFT_DAYS = 20         # trading days in the drift window
DEDUP_DAYS = 30         # drop a second record for the same ticker within this many days
MIN_PRICE = 1.0
JUMP_LO, JUMP_HI = 0.25, 4.0   # daily close ratio outside this band = data error, exclude
SURP_CAP = 500.0

PERIODS = [
    ("P1", dt.date(2023, 1, 1), dt.date(2023, 12, 31)),
    ("P2", dt.date(2024, 1, 1), dt.date(2024, 12, 31)),
    ("P3", dt.date(2025, 1, 1), dt.date(2025, 6, 30)),
    ("P4", dt.date(2025, 7, 1), dt.date(2025, 12, 31)),
    ("P5", dt.date(2026, 1, 1), dt.date(2026, 3, 31)),
    ("P6", dt.date(2026, 4, 1), dt.date(2026, 8, 14)),
]
PRE = ("P1", "P2")
POST = ("P6",)

SUBSAMPLE_TICKERS = 250      # controls subsample S: all events of 250 random S&P 500 panel tickers
REPEAT_N = 300               # repeatability set R
REPEAT_EXTRA = 2             # extra Jev calls per event in R (K arm)

JEV_MODEL = "typesafe/jev-1.13"
JEV_PIN = "typesafe/jev-1.13-20260917"   # served-model string seen in pre-freeze checks
PRE_YEARS = (2023, 2024)
CONTROL_MODELS = {
    "sonnet5": "anthropic/claude-sonnet-5",
    "llama31": "meta-llama/llama-3.1-70b-instruct",
}
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
FMP_BASE = "https://financialmodelingprep.com/stable"
BUDGET_USD = 15.0


def period_of(d: dt.date) -> str | None:
    for name, lo, hi in PERIODS:
        if lo <= d <= hi:
            return name
    return None


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def jsonl_read(p: pathlib.Path) -> Iterator[dict]:
    if not p.exists():
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def jsonl_write(p: pathlib.Path, rows: Iterable[dict]) -> int:
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def gz_json_write(p: pathlib.Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(obj, f)
    tmp.replace(p)


def gz_json_read(p: pathlib.Path):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- secrets
# Keys are read from env vars or local key files and never written to disk or logs.

def _first_existing(paths: list[str]) -> pathlib.Path | None:
    for s in paths:
        if not s or not s.strip():
            continue
        p = pathlib.Path(os.path.expanduser(os.path.expandvars(s)))
        if p.is_file():
            return p
    return None


def openrouter_key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if k:
        return k
    p = _first_existing([
        os.environ.get("OPENROUTER_KEY_FILE", ""),
        "$HOME/mnt/Keys/OpenRouter_API_Key.txt",
        "~/Keys/OpenRouter_API_Key.txt",
    ])
    if p:
        m = re.search(r"sk-or-[A-Za-z0-9_-]+", p.read_text())
        if m:
            return m.group(0)
    raise SystemExit("OpenRouter key not found (set OPENROUTER_API_KEY or OPENROUTER_KEY_FILE)")


def fmp_key() -> str:
    k = os.environ.get("FMP_API_KEY", "").strip()
    if k:
        return k
    p = _first_existing([
        os.environ.get("QAV2_ENV_FILE", ""),
        "$HOME/mnt/quant_alpha_v2/.env",
        "~/apps/quant_alpha_v2/.env",
    ])
    if p:
        for line in p.read_text().splitlines():
            if line.startswith("FMP_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("FMP key not found (set FMP_API_KEY or QAV2_ENV_FILE)")


def pead_universe_csv() -> pathlib.Path:
    p = _first_existing([
        os.environ.get("PEAD_CSV", ""),
        "$HOME/mnt/quant_alpha_v2/data/pead_backtest_qav2_independent.csv",
        "~/apps/quant_alpha_v2/data/pead_backtest_qav2_independent.csv",
    ])
    if not p:
        raise SystemExit("PEAD universe CSV not found (set PEAD_CSV)")
    return p
