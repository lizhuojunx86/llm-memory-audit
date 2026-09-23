"""Exact states and questions sent to every model. Frozen with the protocol.

Arms
  K  knowledge probe: identity only, three past-tense statements
  N  named backtest:  identity + results, two forward-looking questions
  A  anonymized:      sector + the same results, same two questions
"""
from __future__ import annotations

import json

RECORD_TYPE = "quarterly earnings announcement"

WINDOW_REACT = ("the announcement window (from the last close before the announcement date "
                "to the close of the first trading day after it)")
WINDOW_DRIFT = "the 20 trading days after the announcement window"

K_QUESTIONS = {
    "k1_beat": {
        "type": "noul",
        "instructions": ("Is this statement true? In this earnings announcement, the company reported "
                         "quarterly EPS above the analyst consensus EPS estimate."),
        "criteria": {
            "true": "Reported EPS was above the consensus estimate.",
            "false": "Reported EPS was at or below the consensus estimate.",
        },
    },
    "k2_react": {
        "type": "noul",
        "instructions": (f"Is this statement true? Over {WINDOW_REACT}, the stock's price return was "
                         "higher than the S&P 500's price return."),
        "criteria": {
            "true": "The stock beat the S&P 500 over the announcement window.",
            "false": "The stock did not beat the S&P 500 over the announcement window.",
        },
    },
    "k3_drift": {
        "type": "noul",
        "instructions": (f"Is this statement true? Over {WINDOW_DRIFT}, the stock's price return was "
                         "higher than the S&P 500's price return."),
        "criteria": {
            "true": "The stock beat the S&P 500 over those 20 trading days.",
            "false": "The stock did not beat the S&P 500 over those 20 trading days.",
        },
    },
}

R_QUESTIONS = {
    "r2_react": {
        "type": "noul",
        "instructions": (f"Will the stock's price return over {WINDOW_REACT} be higher than the "
                         "S&P 500's price return?"),
        "criteria": {
            "true": "Yes, the stock will beat the S&P 500 over the announcement window.",
            "false": "No, the stock will not beat the S&P 500 over the announcement window.",
        },
    },
    "r3_drift": {
        "type": "noul",
        "instructions": (f"Will the stock's price return over {WINDOW_DRIFT} be higher than the "
                         "S&P 500's price return?"),
        "criteria": {
            "true": "Yes, the stock will beat the S&P 500 over those 20 trading days.",
            "false": "No, the stock will not beat the S&P 500 over those 20 trading days.",
        },
    },
}

ARM_QUESTIONS = {"K": K_QUESTIONS, "N": R_QUESTIONS, "A": R_QUESTIONS}

# label key for each question id
LABEL_OF = {"k1_beat": "y_beat", "k2_react": "y_react", "k3_drift": "y_drift",
            "r2_react": "y_react", "r3_drift": "y_drift"}


def _results(ev: dict) -> dict:
    def fmt(x):
        return "not available" if x is None else x
    return {
        "eps_vs_consensus_pct": fmt(ev.get("eps_surp_pct")),
        "revenue_vs_consensus_pct": fmt(ev.get("rev_surp_pct")),
    }


def state_for(arm: str, ev: dict) -> dict:
    ident = {
        "record_type": RECORD_TYPE,
        "company": ev["company"],
        "ticker": ev["ticker"],
        "exchange": ev["exchange"],
        "sector": ev["sector"],
        "announcement_date": ev["date"],
    }
    if arm == "K":
        return ident
    if arm == "N":
        return {**ident, "as_of": "announcement date, results just released", "results": _results(ev)}
    if arm == "A":
        return {"record_type": RECORD_TYPE, "company": "Company A", "sector": ev["sector"],
                "as_of": "results just released", "results": _results(ev)}
    raise ValueError(arm)


def jev_payload(arm: str, ev: dict, model: str) -> dict:
    return {"state": state_for(arm, ev), "model": model, "questions": ARM_QUESTIONS[arm]}


CONTROL_SYSTEM = (
    "You estimate probabilities. You will receive a JSON record and a list of items about it. "
    "For each item, give the probability (a number from 0 to 1) that the answer is true or yes, "
    "using everything you know. Respond with only a JSON object that maps each item id to a number. "
    "No other text."
)


def control_payload(arm: str, ev: dict, model: str) -> dict:
    qs = ARM_QUESTIONS[arm]
    items = "\n".join(f"- {qid}: {q['instructions']}" for qid, q in qs.items())
    user = (f"Record:\n{json.dumps(state_for(arm, ev), ensure_ascii=False)}\n\n"
            f"Items:\n{items}\n\nJSON:")
    return {
        "model": model,
        "messages": [{"role": "system", "content": CONTROL_SYSTEM},
                     {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": 120,
        "usage": {"include": True},
    }
