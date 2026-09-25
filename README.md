# llm-memory-audit

If a language model remembers how a market event turned out, a backtest run through it measures its memory, not its judgment. This repo holds pre-registered tests for that, one folder per study.

| Study | Models | Result |
|---|---|---|
| [studies/2026-09-jev](studies/2026-09-jev/) | TypeSafe Jev, `jev-1.13-20260917` | no detectable memory of 2023–2024 earnings outcomes (provisional until the prospective set is scored in January 2027) |
| [studies/2026-09-leaderboard](studies/2026-09-leaderboard/) | 12 current models through OpenRouter, plus von, an open Jev-style model | memory in 10 of the 12, and in von. DeepSeek V4 Pro and Qwen3.8 Flash show none |

Each study hashes its protocol, code and inputs into a freeze file before the first model call (one per round) and anchors it in Bitcoin with OpenTimestamps. Each study's README says what that anchor does and doesn't prove. Every later change goes into the study's deviations file.

The pipeline around the model can leak the future too. [TraceGuard](https://github.com/lizhuojunx86/traceguard) is my Python library for that side of the problem.

Zhuojun Li · Apache-2.0
