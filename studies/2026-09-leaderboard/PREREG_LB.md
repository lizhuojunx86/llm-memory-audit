# Model memory leaderboard v0: which models remember how past earnings turned out?

Protocol supplement to jev-lookahead PREREG v1.0 (frozen 2026-09-23T03:49:37Z). Author: Zhuojun Li. This supplement was drafted by Claude (Anthropic) on the author's instruction. Status: frozen before any leaderboard request was sent; `freeze.json` holds the hashes and `freeze.json.ots` its OpenTimestamps proof.

## What is new

Only the list of models. Everything else is the positive-control arm of the original study:

- Prompt: `control_payload("K", event, model)` from `jev-lookahead/src/payloads.py`, the same system prompt and name-and-date record that Claude Sonnet 5 and Llama 3.1 70B received.
- Events: subsample S, every announcement from 2023-01-01 to 2026-08-14 of the 250 S&P 500 tickers drawn for the controls, 3,708 events, one call each.
- Labels: frozen in `jev-lookahead/work/events.jsonl` (hash in the original `freeze.json`).
- Statistic and bootstrap: the original S10 / control statistic, described below.

## Models

| Key | OpenRouter id | Reasoning |
|---|---|---|
| gpt6sol | openai/gpt-6-sol | disabled |
| gpt6luna | openai/gpt-6-luna | disabled |
| dsv4pro | deepseek/deepseek-v4-pro-0813 | disabled |
| kimik3 | moonshotai/kimi-k3 | disabled |
| gemini38f | google/gemini-3.8-flash | mandatory on this endpoint: effort "low", reasoning text excluded |
| qwen38max | qwen/qwen3.8-max-0902 | mandatory: effort "low", excluded |
| grok47 | x-ai/grok-4.7 | mandatory: effort "low", excluded |
| glm53 | z-ai/glm-5.3 | mandatory: effort "low", excluded |

Where reasoning can be switched off it is, with `max_tokens` 300 (the setting of deviation D2 in the original study). Where the endpoint refuses (checked in `preflight/smoke.jsonl` with a fictional company), the lowest effort is used with `max_tokens` 2000. Reasoning may help a model recall, so the setting is printed next to every result. Temperature is 0 where the endpoint honours it. The served model string is logged per call.

Existing results from the original study are reported alongside, unchanged: Jev (K arm, restricted to subsample S), Claude Sonnet 5 (reasoning off) and Llama 3.1 70B. Claude Opus 5.5 was considered and left out to keep the run within budget; smoke cost about US$0.003 a call.

## Primary statistic, per model

Pooled within-company AUC in PRE: pairs of announcements of the same ticker in the same calendar quarter, one in 2023 and one in 2024, with different labels, over the three name-and-date questions pooled. Scores are demeaned by calendar month first. Ticker-cluster bootstrap with B = 2,000 draws and seed 20260923 + 1004, as for the original controls. Per-question within-company AUCs are secondary.

## Decision rule

A model "shows memory" if the one-sided test of pooled within-company AUC > 0.5 rejects after Holm correction across the eight new models at α = 0.05. Every model's estimate and 95% interval is reported whatever the outcome. Not rejecting is not proof of no memory; the design's minimum detectable effect is reported with each result.

## Invalid outputs and failures

Answers that are unparseable or miss an item are dropped, as in section 6 of the original protocol, and counted per model. Transient HTTP errors are retried up to five times with backoff; anything still failing is reported. Spending stops at US$50 for the whole leaderboard.

## Deviations

Anything changed after the freeze goes into `DEVIATIONS_LB.md` with its reason and the results it can touch.
