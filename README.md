# llm-memory-audit

If a language model remembers how a market event turned out, a backtest run through it measures its memory, not its judgment. This repo holds pre-registered tests for that, one folder per study.

| Study | Model | Result |
|---|---|---|
| [studies/2026-09-jev](studies/2026-09-jev/) | TypeSafe Jev, `jev-1.13-20260917` | no detectable memory of 2023–2024 earnings outcomes (provisional until the prospective set is scored in January 2027) |

Each study hashes its protocol, code and inputs into one file before the first model call and anchors that file in Bitcoin with OpenTimestamps. Every later change goes into that study's `DEVIATIONS.md`.

The pipeline around the model can leak the future too. [TraceGuard](https://github.com/lizhuojunx86/traceguard) is my Python library for that side of the problem.

Zhuojun Li · Apache-2.0
