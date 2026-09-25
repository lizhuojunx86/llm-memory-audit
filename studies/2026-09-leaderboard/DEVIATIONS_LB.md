# Deviations from the frozen leaderboard protocol (frozen 2026-09-24T13:58:55Z)

## D1 · 2026-09-24 · Runs paused, restarted and one cap raised (operational; no request or statistic changed)

- Grok 4.7 was paused at 485 of 3,708 calls to review its cost, then resumed. Its endpoint makes reasoning mandatory and it used 600 to 700 reasoning tokens a call, about seven times the per-call cost of the next most expensive model.
- Qwen3.8 Max and Grok 4.7 were restarted with higher concurrency (60 and 80) to finish sooner. Calls in flight at a restart were sent again; only completed calls are recorded, and every recorded request id is unique.
- The US$50 spending cap in PREREG_LB.md was enforced by each model's process for its own calls, not across the leaderboard. Grok 4.7 hit it with 105 calls left. Those 105 were sent after raising the cap to US$56 at run time (`lb.BUDGET_USD` set in the calling command; `lb.py` itself is unchanged and still matches `freeze.json`). Total spend for the eight models, including the smoke calls: US$55.34.

None of this changes a prompt, a model setting, an event or the analysis. All eight models have 3,708 of 3,708 calls with HTTP 200.

## Not a deviation, but worth knowing

- Jev's row (0.504) differs from the 0.483 reported for the same 1,207 pairs in the original write-up. Here every model's answers are demeaned by month within the 3,708 subsample events; there, Jev's month averages came from all 12,533 events it answered. Both numbers are inside the noise around 0.5. Recomputing Jev the original way on the same code gives 0.483 (0.457 to 0.509).
- von (an open Jev-style model) was added under a separate addendum, `clones/PREREG_LB_clones.md`, frozen and timestamped at 2026-09-24T14:10:43Z before any study event was sent to it. It ran locally on CPU, so it cost nothing.
