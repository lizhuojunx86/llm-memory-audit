# Deviations from the frozen leaderboard protocol (frozen 2026-09-24T13:58:55Z)

## D1 · 2026-09-24 · Runs paused, restarted and one cap raised (operational; no request or statistic changed)

- Grok 4.7 was paused at 485 of 3,708 calls to review its cost, then resumed. Its endpoint makes reasoning mandatory and it used 600 to 700 reasoning tokens a call, about seven times the per-call cost of the next most expensive model.
- Qwen3.8 Max and Grok 4.7 were restarted with higher concurrency (60 and 80) to finish sooner. Calls in flight at a restart were sent again; only completed calls are recorded, and every recorded request id is unique.
- The US$50 spending cap in PREREG_LB.md was enforced by each model's process for its own calls, not across the leaderboard. Grok 4.7 hit it with 105 calls left. Those 105 were sent after raising the cap to US$56 at run time (`lb.BUDGET_USD` set in the calling command; `lb.py` itself is unchanged and still matches `freeze.json`). Total spend for the eight models, including the smoke calls: US$55.34.

None of this changes a prompt, a model setting, an event or the analysis. All eight models have 3,708 of 3,708 calls with HTTP 200.

## Not a deviation, but worth knowing

- Jev's row (0.504) differs from the 0.483 reported for the same 1,207 pairs in the original write-up. Here every model's answers are demeaned by month within the 3,708 subsample events; there, Jev's month averages came from all 12,533 events it answered. Both numbers are inside the noise around 0.5. Recomputing Jev the original way on the same code gives 0.483 (0.457 to 0.509).
- von (an open Jev-style model) was added under a separate addendum, `clones/PREREG_LB_clones.md`, frozen and timestamped at 2026-09-24T14:10:43Z before any study event was sent to it. It ran locally on CPU, so it cost nothing.

## D2 · 2026-10-11 · Analysis code changed after publication; von's row depends on how ties are scored

`lb_analyze.py` was never in a freeze (only `lb.py`, the request builder, was). After publication it changed in four ways. It now resolves the Jev study at `../2026-09-jev` and the second round at `add2/`, the names in this repo, instead of the author's private directory names, so it runs from the published tree; private data locations come from `LMA_JEV_PRIVATE`, `LMA_LB_PRIVATE` and `LMA_ADD2_PRIVATE`. It gained the same `--ties` option as the Jev study (`demeaned`, the published default; `raw_tie_half`; `raw`), writing to `results/ties_<policy>/`. It reports a within-company AUC per calendar year, 2023 to 2026, pairing two reports of the same firm and the same question inside one year. And it reports the same statistic on pairs where both reports are dated 2026-05-01 or later. `results/leaderboard.json` and `.md` are untouched. `lb.py` keeps its old sibling-directory paths because it is frozen.

Why ties matter here: the published statistic demeans scores by month and then compares. For two raw answers that are identical, the demeaned difference is the gap between the two month means, so the pair is scored by the calendar, not by the model. Raw-tie shares on the pooled pairs: DeepSeek V4 Pro 79%, DeepSeek V4.1 Flash 71%, Kimi K3 45%, Sonnet 5 41%, Jev 30%, GLM-5.3 20%; under 10% for the six models at the top.

What changed and what did not:

- Every "memory detected" row among the twelve API models stays detected under all three policies, and every "no" stays "no". Holm rejections are identical across policies for both rounds.
- von is the exception. Its row is 0.541 (0.512 to 0.568) demeaned, 0.539 with raw ties as one half, and 0.495 (0.469 to 0.520) with no demeaning. von's raw scores barely vary (4% exact ties, but small differences), so after demeaning the sign of most pairs comes from the month means. The published "memory in von" claim does not survive the raw comparison, and the author withdraws it. The honest row for von is "depends on the statistic; no under the raw comparison".
- Qwen3.8 Max and Sonnet 5 move down by about 0.01 to 0.02 under `raw`; GPT-6 Astra, Opus 5.5 and GPT-6 Sol move up by 0.01 to 0.03. Both directions are inside the published intervals.

The year-by-year and post-cutoff tables are in `results/ties_raw/leaderboard.md` and summarised in the README. They were run after the published results had been read; none of this was pre-registered.
