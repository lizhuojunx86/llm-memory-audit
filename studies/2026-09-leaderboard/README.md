# Which language models remember how past earnings turned out?

Give a model a company name and an earnings date, nothing else, and ask whether that report beat consensus. A model with no memory can't tell a company's 2023 report from its 2024 one. I ran that test, pre-registered, on twelve current API models (eight in a first round and four in a second, separately frozen round) and on von, an open Jev-style model, with the probe and the 3,708 announcements from [the Jev study](../2026-09-jev/).

| Model | OpenRouter id / source | Within-company AUC (95% CI) | Pairs | Memory detected | Reasoning |
|---|---|---|---|---|---|
| GPT-6 Astra | `openai/gpt-6-astra` | 0.904 (0.886 to 0.921) | 1,207 | yes (addendum) | low (can't be switched off) |
| Gemini 3.8 Flash | `google/gemini-3.8-flash` | 0.799 (0.776 to 0.822) | 1,199 | yes | low (can't be switched off) |
| Claude Opus 5.5 | `anthropic/claude-opus-5.5` | 0.766 (0.742 to 0.792) | 1,207 | yes (addendum) | low (can't be switched off) |
| GPT-6 Sol | `openai/gpt-6-sol` | 0.691 (0.665 to 0.717) | 1,207 | yes | off |
| Grok 4.7 | `x-ai/grok-4.7` | 0.603 (0.573 to 0.634) | 1,205 | yes | low (can't be switched off) |
| Claude Sonnet 5 | `anthropic/claude-sonnet-5` | 0.587 (0.561 to 0.613) | 1,207 | yes (control) | off |
| Qwen3.8 Max | `qwen/qwen3.8-max-0902` | 0.578 (0.550 to 0.605) | 1,206 | yes | low (can't be switched off) |
| GPT-6 Luna | `openai/gpt-6-luna` | 0.573 (0.547 to 0.601) | 1,207 | yes | off |
| DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | 0.551 (0.521 to 0.578) | 1,205 | yes (addendum) | off |
| von 1.2 (open Jev-style) | `wfzyx/von (von-1.2.0, local CPU)` | 0.541 (0.512 to 0.569) | 1,207 | withdrawn, see below | n/a |
| Kimi K3 | `moonshotai/kimi-k3` | 0.538 (0.511 to 0.567) | 1,202 | yes | off |
| GLM-5.3 | `z-ai/glm-5.3` | 0.531 (0.501 to 0.560) | 1,206 | yes | low (can't be switched off) |
| Jev 1.13 | `typesafe/jev-1.13-20260917` | 0.504 (0.478 to 0.530) | 1,207 | no | n/a |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro-0813` | 0.504 (0.476 to 0.533) | 1,207 | no | off |
| Qwen3.8 Flash | `qwen/qwen3.8-flash` | 0.498 (0.470 to 0.527) | 1,207 | no (addendum) | off |
| Llama 3.1 70B | `meta-llama/llama-3.1-70b-instruct` | 0.490 (0.464 to 0.517) | 1,199 | no | n/a |

0.5 means the model can't tell. Each figure is the within-company AUC pooled over three questions: did EPS beat consensus, and did the stock beat the S&P 500 over the 2-day reaction and over the next 20 trading days. It is the share of same-company, same-season pairs, one report from 2023 and one from 2024 with different outcomes, where the model scored the right one higher. Intervals come from a ticker bootstrap. "Memory detected" means the one-sided test rejected after Holm correction within its round: the eight first-round models, the four second-round models, and von on its own. The Sonnet 5, Jev and Llama rows come from the original study.

## What it means for a backtest

If your pipeline hands one of the top rows a ticker and a date, part of what looks like skill is recall. On EPS beats alone, GPT-6 Astra ranked the report that beat above the one that missed in 91% of same-company pairs, and Gemini 3.8 Flash in 87%. Two cheap defences: leave names and dates out when the task allows, and test your own pipeline with a within-company comparison like this one before trusting a backtest.

## Two things found after publication

**The statistic scored raw ties by the calendar.** Scores are demeaned by month before pairs are compared, so two identical raw answers from the same firm get a direction from the gap between their two month means. An outside reader caught this on 2026-10-11. For six of the sixteen rows, 20% to 79% of pairs are raw ties. I rescored everything two more ways: raw ties as one half, and no demeaning at all (`results/ties_raw_tie_half/`, `results/ties_raw/`, `DEVIATIONS_LB.md` D2). Every yes among the twelve API models stays a yes and every no stays a no. The one casualty is von: 0.541 demeaned, 0.495 (0.469 to 0.520) raw. Its raw answers barely vary, so the demeaning was supplying the signal. I withdraw the claim that von remembers. The open Jev-style model behaves like Jev.

**The signal stops at each model's training cutoff.** The same within-company comparison, run on two reports of the same firm inside one calendar year (so not season-matched), with raw scores:

| Model | 2023 | 2024 | 2025 | 2026 (Apr to Aug) | both reports after 2026-05-01 (89 pairs) |
|---|---|---|---|---|---|
| GPT-6 Astra (cutoff 2026-04-30) | 0.886 | 0.913 | 0.816 | 0.610 | 0.472 (0.398 to 0.553) |
| Gemini 3.8 Flash | 0.785 | 0.789 | 0.518 | 0.524 | 0.471 |
| Claude Opus 5.5 (cutoff June 2026) | 0.737 | 0.813 | 0.843 | 0.642 | 0.489 |
| GPT-6 Sol | 0.671 | 0.695 | 0.598 | 0.527 | 0.522 |
| Grok 4.7 | 0.569 | 0.575 | 0.560 | 0.488 | 0.461 |
| Claude Sonnet 5 (cutoff January 2026) | 0.516 | 0.566 | 0.542 | 0.501 | 0.511 |
| the other ten | 0.47 to 0.55 | 0.50 to 0.55 | 0.47 to 0.54 | 0.48 to 0.51 | 0.44 to 0.56 |

Gemini drops from 0.79 to 0.52 between 2024 and 2025. Astra and Opus 5.5 are the two rows still above 0.5 in 2026, and they are the two models whose published cutoffs fall inside that window; on pairs where both reports post-date Astra's cutoff, every model sits at or below 0.5 within noise. A date heuristic or knowledge of a firm's trend would not switch off at the cutoff. So what the table above measures is recall. The full year-by-year table with intervals and pair counts is in `results/ties_raw/leaderboard.md`.

## Read the rows carefully

- GPT-6 Astra stopped at 1,464 of its 3,708 calls when the account ran out of credit. I finished it the same day, after I had seen that partial result, with the requests unchanged. See `add2/DEVIATIONS_LB.md`.
- Six endpoints refuse to switch reasoning off (Gemini 3.8 Flash, Qwen3.8 Max, Grok 4.7, GLM-5.3, Claude Opus 5.5 and GPT-6 Astra), so they ran at the lowest effort. Reasoning may help recall, so those rows aren't strictly like-for-like with the rest.
- Not detecting memory isn't proof there is none. With about 1,200 pairs the test can detect a pooled AUC of roughly 0.546.
- Jev's row (0.504) and the 0.483 in the original write-up cover the same pairs. The difference is how month averages are subtracted, explained in `DEVIATIONS_LB.md`. That 0.02 swing from a demeaning choice is the same size as the margin of the bottom three yes rows, which is why those rows were rechecked without demeaning (they hold).
- One prompt, 250 S&P 500 companies, one window. Each row is the model served on 2026-09-24, and versions change.

## What the timestamps prove

`freeze.json.ots` and `clones/freeze_clones.json.ots` anchor their freezes in Bitcoin block 968402 (mined 2026-09-24T14:36:13Z) and two later blocks. Each stamp was requested seconds before its round's first call, but a stamp only counts once a block confirms it. The first-round calls ran from 13:59:05Z to 14:32:01Z, so for that round the proof on its own shows only that the protocol existed by 14:36:13Z, four minutes after the last call. von's calls ran from 14:10:58Z to 15:39:53Z, so its proof covers all but the first 25 minutes of its run. `add2/freeze.json.ots` anchors the second-round freeze in block 968413 (timestamped 2026-09-24T15:10:05Z), two minutes after that round's first call at 15:08:12Z. By then 5,486 of its 14,832 requests had been sent, so on its own the proof covers the other 9,346, including all of GPT-6 Astra's resumed calls. Miners set block times loosely, and the rules allow errors of an hour or more, so read all of these times as approximate.

## Files

| Path | What it is |
|---|---|
| `PREREG_LB.md`, `freeze.json`, `freeze.json.ots` | first-round protocol, its freeze and OpenTimestamps proof |
| `add2/` | second round: its protocol, models, requests, deviations and its own freeze |
| `clones/` | the addendum for von, its runner and its own freeze |
| `DEVIATIONS_LB.md` | what changed during the first round and why none of it touches a result |
| `lb.py`, `lb_analyze.py`, `models.json` | runner (frozen, still carries the author's old sibling-directory paths), analysis (changed after publication, D2) and first-round model settings |
| `freeze_outputs.json` | SHA-256 of every raw model log, public output file and results file, written after the runs |
| `preflight/smoke.jsonl` | the fictional-company calls used to fix settings before the freeze |
| `work/requests.jsonl.gz` | every first-round request, gzipped |
| `public_data/model_outputs.csv.gz` | every parsed probability, all models |
| `results/` | the published table and statistics, plus `ties_raw_tie_half/` and `ties_raw/` with the rescored tables, the year-by-year and the post-cutoff placebo |
| `tools/check_freeze_lb.py` | rehashes the published files against all three freezes |

## Check it

```bash
python tools/check_freeze_lb.py
python ../2026-09-jev/tools/freeze_outputs.py check --study leaderboard
```

To rerun the analysis you need the private logs and labels; `lb_analyze.py --help` lists the three `LMA_*_PRIVATE` variables that point to them.

The labels come from FMP earnings and price data, which stay private under FMP's licence; see the Jev study for how to rebuild them with your own key. API cost on OpenRouter: US$128.56 across both rounds. von ran on a CPU at no cost.

Zhuojun Li. The protocol, code and write-up were drafted by Claude (Anthropic) on my instruction. Apache-2.0.
