# llm-memory-audit

If a language model remembers how a market event turned out, a backtest run through it measures its memory, not its judgment. This repo holds pre-registered tests for that, one folder per study.

| Study | Models | Result |
|---|---|---|
| [studies/2026-09-jev](studies/2026-09-jev/) | TypeSafe Jev, `jev-1.13-20260917` | no detectable memory of 2023–2024 earnings outcomes (provisional until the prospective set is scored in January 2027) |
| [studies/2026-09-leaderboard](studies/2026-09-leaderboard/) | 12 current models through OpenRouter, plus von, an open Jev-style model | memory in 10 of the 12; DeepSeek V4 Pro and Qwen3.8 Flash show none. The von result was withdrawn on 2026-10-11 (it depended on how ties were scored). The signal stops at each model's published training cutoff |

After the leaderboard study, ai-hedge-fund made every backtest withhold the ticker, industry and calendar dates from its LLM agents ([virattt/ai-hedge-fund#721](https://github.com/virattt/ai-hedge-fund/pull/721), released in v2.4.1).

Each study hashes its protocol, code and inputs into a freeze file before the first model call (one per round) and anchors it in Bitcoin with OpenTimestamps. Each study's README says what that anchor does and doesn't prove. Since 2026-10-11 each study also carries a `freeze_outputs.json` that hashes the raw model logs and every published output after the fact. Every later change goes into the study's deviations file, including the two found by an outside review in October (ties were scored by month means; one of two positive controls failed).

The pipeline around the model can leak the future too. [TraceGuard](https://github.com/lizhuojunx86/traceguard) is my Python library for that side of the problem.

Zhuojun Li · Apache-2.0
