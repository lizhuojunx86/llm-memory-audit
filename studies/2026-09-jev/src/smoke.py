"""Pre-freeze pipeline check with ONE fictional company. Never touches study events.

  python src/smoke.py      # writes preflight/smoke.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import parse_control  # noqa: E402
from common import CONTROL_MODELS, JEV_MODEL, ROOT, openrouter_key, utc_now  # noqa: E402
from payloads import ARM_QUESTIONS, control_payload, jev_payload  # noqa: E402
from run_models import call  # noqa: E402

FAKE = {"ticker": "ACMW", "company": "Acme Widgets Holdings Inc. (fictional)", "exchange": "NASDAQ",
        "sector": "Industrials", "date": "2024-05-01", "event_id": "ACMW|2024-05-01",
        "eps_surp_pct": 7.5, "rev_surp_pct": 1.2}


def main() -> None:
    key = openrouter_key()
    s = requests.Session()
    out = ROOT / "preflight" / "smoke.jsonl"
    out.parent.mkdir(exist_ok=True)
    plan = [("jev", a) for a in ("K", "N", "A")] + [("sonnet5", "K")] + [("llama31", a) for a in ("K", "N", "A")]
    with open(out, "a") as f:
        for mk, arm in plan:
            payload = (jev_payload(arm, FAKE, JEV_MODEL) if mk == "jev"
                       else control_payload(arm, FAKE, CONTROL_MODELS[mk]))
            req = {"request_id": f"smoke|{mk}|{arm}", "model_key": mk, "arm": arm,
                   "event_id": FAKE["event_id"], "repeat": 0, "payload": payload}
            rec = call(s, key, req, 60)
            rec["smoke_utc"] = utc_now()
            f.write(json.dumps(rec) + "\n")
            if mk == "jev":
                ans = ((rec.get("response") or {}).get("answers") or {})
                parsed = {k: v.get("noul") for k, v in ans.items()}
            else:
                parsed = parse_control(rec.get("content"), list(ARM_QUESTIONS[arm]))
            print(mk, arm, rec["http_status"], rec.get("served_model"), f"{rec['latency_ms']}ms",
                  "cost", (rec.get("usage") or {}).get("cost"), "->", parsed,
                  "" if mk == "jev" else f"| raw: {str(rec.get('content'))[:160]!r}")


if __name__ == "__main__":
    main()
