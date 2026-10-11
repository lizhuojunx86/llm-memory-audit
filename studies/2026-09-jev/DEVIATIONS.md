# Deviations from the frozen protocol (v1.0, frozen 2026-09-23T03:49:37Z)

Every entry says what changed, when, why, and which results it can touch.

## D1 · 2026-09-23 · Positive-control calls failed on account credit (operational, no protocol change)

The OpenRouter account ran out of credit right after the Jev run finished (total credit US$10.00, usage US$10.05). Of the 3,708 Sonnet 5 calls, 3,625 came back HTTP 402 "in_flight_budget_exhausted". No Llama 3.1 70B call had been sent. The Jev run (38,956 calls, all HTTP 200, all served by `typesafe/jev-1.13-20260917`) finished before this happened and is unaffected. Resolved the same day: the author added credit, and from 04:31Z every Sonnet 5 call (under D2) and every Llama 3.1 70B call was sent. All 3,708 + 11,124 came back HTTP 200.

## D2 · 2026-09-23 · Sonnet 5: reasoning switched off, token cap raised (protocol change, positive control only)

What happened: Sonnet 5 on OpenRouter spends part of `max_tokens` on hidden reasoning. With the frozen cap of 120 tokens, 17 of the 83 calls that did go through returned empty content with `finish_reason = "length"`. At that rate about a fifth of the control would be missing.

Change: all Sonnet 5 calls are re-sent with `"reasoning": {"enabled": false}` and `"max_tokens": 300`, merged into the frozen payload at send time (`run_models.py --override`). `work/requests.jsonl` is unchanged and still matches `freeze.json`. Each response record stores the override it was sent with. The first 83 responses are kept in `runs/_superseded/` and are not analyzed.

Code change: `src/run_models.py` gained the `--override` flag, which refuses to run for Jev, and its spend counter now includes `runs/_superseded/`. The frozen version is kept in `frozen_code/run_models.py` (its SHA-256 matches `freeze.json`).

Order of events, stated plainly: the Jev primary results had already been computed and read (`results/interim_jev_only/`) before this change was made. The change touches only the positive control, which gates the "no detectable memory" wording. The higher cap only removes empty answers. Switching reasoning off can only make recall harder, so if the change biases the gate at all, it biases it toward failing. No Jev request, Jev result or Jev test was altered.

Llama 3.1 70B does not reason and is sent exactly as frozen.

Outcome of D2: 3,708 of 3,708 Sonnet 5 answers came back with `finish_reason = "stop"`, zero reasoning tokens and parseable JSON.

## Not a deviation, but not pre-registered either

- `results/posthoc_same_subsample_jev_vs_sonnet.json`: Jev and Sonnet 5 scored on exactly the same 1,207 within-company pairs of subsample S (Jev 0.483, 95% CI 0.458 to 0.509; Sonnet 5 0.587, 0.560 to 0.614). Added after seeing the results to make the comparison like-for-like. Descriptive only.
- Llama 3.1 70B returned a misspelled key (`k1_be`) in 55 of 3,708 K-arm answers and an incomplete answer in 5 N-arm ones. Under section 6 these are invalid outputs and are dropped; nothing was repaired.

## D3 · 2026-10-11 · Analysis code changed after publication: tie policies and a private-data path (no result in `results/results.json` changed)

What prompted it: an outside review found that the within-company statistic compares scores *after* month-demeaning and only then checks for a tie. Two answers from the same model that are identical in the raw output sit in different months, so after demeaning their difference equals the gap between the two month means. That gap has nothing to do with the firm. For Jev 30% of the same-company 2023-vs-2024 pairs are raw ties on the pooled K questions; for Llama 3.1 70B it is 73%, for DeepSeek V4 Pro 79%. `tests/test_stats.py` drew continuous Gaussian scores, so it never produced a tie and could not see this.

Change: `src/analyze.py` gained a `--ties` option with three policies. `demeaned` is the frozen behaviour and stays the default; `results/results.json` and `results/results.md` are untouched. `raw_tie_half` counts a raw tie as one half and otherwise lets the demeaned difference decide. `raw` drops demeaning and compares raw scores. The two new policies write to `results/ties_raw_tie_half/` and `results/ties_raw/`. `src/common.py` now reads `LMA_JEV_PRIVATE` for the location of `runs/` and `work/`, so the code runs from the published tree against private data kept elsewhere; the default is unchanged. `tests/test_ties.py` adds six tests, including a null draw on a coarse score grid with base-rate drift. Frozen originals: `frozen_code/analyze.py`, `frozen_code/common.py` (their SHA-256 match `freeze.json`).

What it does to Jev: nothing that matters. Pooled K within-company AUC is 0.504 (0.479 to 0.531) demeaned, 0.511 (0.489 to 0.533) with raw ties as one half, 0.504 (0.481 to 0.528) raw. H1 to H5 stay inside their intervals under every policy, the decision rule returns `no_detectable_leakage_provisional` each time, and the Sonnet 5 control stays above 0.5 (0.568 and 0.567 under the two new policies). Full numbers are in the two `results/ties_*/` folders.

Order of events: both new policies were run after the published results had been read. They are post-hoc checks, not pre-registered tests.

## Not a deviation, but the README did not say it

- PREREG section 7 expected Llama 3.1 70B, whose stated cutoff is December 2023, to show memory of 2023 and none after. It shows none of 2023 either: within-2023 wtAUC on the beat question 0.447, pooled 0.490 (0.464 to 0.517). So one of the two sensitivity checks on the probe failed. Only Sonnet 5 passed. The 'no detectable memory' verdict for Jev rests on a probe that found memory in one of two models expected to have it.
