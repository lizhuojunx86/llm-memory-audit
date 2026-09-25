# Leaderboard v0, addendum 2: four more models

Addendum to `../memory-leaderboard/PREREG_LB.md` (frozen 2026-09-24T13:58:55Z), written before any study event was sent to these models. Author: Zhuojun Li; drafted by Claude (Anthropic) on the author's instruction. The author added OpenRouter credit after the first eight models finished, and this addendum spends part of it on the models most readers will ask about next.

## Models

| Key | OpenRouter id | Reasoning |
|---|---|---|
| opus55 | anthropic/claude-opus-5.5 | mandatory on this endpoint: effort "low", reasoning text excluded, max_tokens 2000 |
| gpt6astra | openai/gpt-6-astra | mandatory: effort "low", excluded, max_tokens 2000 |
| dsv41flash | deepseek/deepseek-v4.1-flash | disabled, max_tokens 300 |
| qwen38flash | qwen/qwen3.8-flash | disabled, max_tokens 300 |

Settings were fixed from `preflight/smoke.jsonl` (fictional company only).

## Everything else

Same prompt, the same 3,708 subsample-S events, the same statistic and bootstrap, and the same invalid-output rules as the main leaderboard protocol. `lb.py` here is byte-identical to the frozen main-leaderboard `lb.py`; only `models.json` differs. These four models form their own Holm family (one-sided α = 0.05), reported next to the main eight. Spending cap for this addendum: US$40.
