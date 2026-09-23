# Does Jev know how past earnings turned out?

Pre-registered protocol, version 1.0
Author: Zhuojun Li
Status: frozen before any study event was sent to any model. `freeze.json` holds the SHA-256 of this file, the code and every input; `freeze.json.ots` is its OpenTimestamps proof.
This protocol was drafted by Claude (Anthropic) on the author's instruction.

## 1. Summary

TypeSafe says Jev (`jev-1.13`, released 2026-09-15) is trained on synthetic data and answers from the state it is given. People are already running it over historical earnings events and reading the results as backtests. If Jev remembers how those events turned out, such backtests score its memory, not its judgment.

I test this on 12,533 US earnings announcements from 2023-01-01 to 2026-08-14. The main test asks a narrow question: for the same company and the same season, can Jev tell its 2023 announcement from its 2024 one when told only the name and the date? A model with no memory has nothing to separate them. A model that remembers does.

## 2. Data

- Source: Financial Modeling Prep (FMP) stable API, pulled once on 2026-09-23 under the author's subscription. Endpoints: `sp500-constituent`, `profile`, `earnings`, `historical-price-eod/full` (split-adjusted closes, no dividends).
- Universe: 900 tickers. 500 current S&P 500 members (one symbol per CIK) and 400 tickers drawn at random (seed 20260923) from 1,922 non-S&P tickers in the author's PEAD research universe that had an event on or after 2023-01-01.
- Events: FMP earnings records dated 2023-01-01 to 2026-08-14 with non-null reported and consensus EPS. A second record for the same ticker within 30 days is dropped.
- Exclusions, applied before any model call: EPS missing (211), missing price on a window date (89), close below $1 the day before the announcement (43), duplicate within 30 days (12). A daily close ratio outside 0.25–4.0 inside a window would also exclude the event (none did).
- Trading calendar: SPY trading days. `d_prev` is the last trading day before the announcement date, `d_next` the first trading day after it, `d_end` is 20 trading days after `d_next`.
- Labels, computed before any model call and hashed in `freeze.json`:
  - `y_beat` = 1 if reported EPS > consensus EPS, 0 if lower. Ties (410) are left out of beat analyses. Base rate 73.7%.
  - `y_react` = 1 if the stock's price return minus SPY's price return from `d_prev` close to `d_next` close is above 0. The two-day window covers before-open and after-close reports. Base rate 49.0%.
  - `y_drift` = the same over `d_next` close to `d_end` close. Base rate 44.4%.
- Periods: P1 2023 (3,420 events), P2 2024 (3,405), P3 2025 H1 (1,684), P4 2025 H2 (1,663), P5 2026 Q1 (830), P6 2026-04-01 to 2026-08-14 (1,531). Per-period base rates, sector mix, S&P share and surprise quantiles are in `work/manifest.json`. They differ between periods (the P6 drift base rate is 36.4%, P4's is 53.1%), which is why the main test compares a company with itself.
- Season: calendar quarter of the announcement date (1 = Jan–Mar ... 4 = Oct–Dec).
- Balanced panel: the 812 tickers with at least one event in 2023–2024 (PRE) and one in P6 (POST).

## 3. Arms

Every event is sent to Jev in three arms. Exact payloads are built by `src/payloads.py`; the wording is in the appendix.

- K, knowledge probe: company name, ticker, exchange, sector, announcement date. Nothing about the results. Three past-tense statements (beat, reaction, drift), each asked as a Jev `noul` question.
- N, named backtest: the K fields plus the results as percentages (EPS vs consensus, revenue vs consensus). Two forward-looking questions (reaction, drift).
- A, anonymized backtest: sector and the same results. No name, ticker, exchange or date. The same two questions.

## 4. Models and sets

- Jev: `typesafe/jev-1.13` through OpenRouter `POST /api/v1/systemone`, one call per event per arm. The served model string read `typesafe/jev-1.13-20260917` in every pre-freeze check and is pinned: responses from any other string are kept on disk but left out of the analysis. If fewer than 80% of study responses carry the pinned string, the verdict is "rerun required" and the whole run is repeated on the new version, with both reported.
- Positive control 1: `anthropic/claude-sonnet-5`, chat completions, temperature 0, K arm, subsample S.
- Positive control 2: `meta-llama/llama-3.1-70b-instruct` (Meta states a pretraining data cutoff of December 2023), temperature 0, arms K, N and A, subsample S.
- Controls get the same record and item wording, with a system prompt asking for a probability per item "using everything you know", as JSON.
- Subsample S: every event of 250 S&P 500 balanced-panel tickers drawn at random (seed 20260923), 3,708 events. Drawing whole tickers lets the controls run the same within-company test; S&P names are where a model with memory should show it.
- Repeatability set R: 300 random events, K arm, two extra Jev calls each.
- Prospective set PROSP: 757 announcements scheduled for 2026-10-01 to 2026-11-30, one per ticker, from the full 900-ticker universe, K arm, sent to Jev before 2026-10-01.
- Requests are shuffled (seeded) before sending, so any drift in the service during the run is spread across periods.

## 5. Primary statistic: within-company AUC

For one model, arm and question:

1. Month-demean the scores: subtract from each probability the mean probability of all events announced in the same calendar month. This removes any generic date effect, for example a model that answers more cautiously about recent dates.
2. Form pairs from the same ticker and the same season, one event in 2023 and one in 2024, with different labels. A ticker has at most four such pairs.
3. wtAUC = share of pairs where the positive event has the higher demeaned score, ties counted as one half.

A company-level prior ("this firm usually beats") gives both events of a pair the same score and cannot move wtAUC. A generic date effect is removed in step 1. Seasonal habits cancel because both events are in the same season. What can move wtAUC above 0.5 is information about the specific event, or a company-specific sense of how that firm did in 2024 versus 2023. Both are hindsight for a backtest set in 2023.

Inference: bootstrap over tickers, 10,000 resamples. A ticker drawn k times adds k times its pair count to the numerator and the denominator. The one-sided p-value is (1 + number of resamples at or below the null) / (1 + number of valid resamples). Seeds are 20260923 plus a fixed offset per test, as written in `src/analyze.py`.

## 6. Primary hypotheses (Jev, balanced panel)

- H1: wtAUC(K, beat) > 0.5
- H2: wtAUC(K, reaction) > 0.5
- H3: wtAUC(K, drift) > 0.5
- H4: wtAUC(N, drift) − wtAUC(A, drift) > 0 on the same pairs
- H5: wtAUC(N, reaction) − wtAUC(A, reaction) > 0 on the same pairs

Holm correction across H1–H5 at family-wise α = 0.05. Events with a missing or invalid output are dropped from the tests that need them; S9 repeats the tests with missing answers set to 0.5.

Planned sensitivity, from the labels before any call: 915 informative pairs for beat (a firm's beat record is persistent, so fewer pairs differ), 1,619 for reaction and 1,462 for drift. At one-sided α = 0.01 with 80% power, that detects a wtAUC of about 0.552 for beat, 0.539 for reaction and 0.541 for drift, and an N − A gap of about 0.059 (drift) and 0.056 (reaction). Each result reports its design-based minimum detectable effect (from the pair count, so it cannot collapse to zero when a model gives constant answers) and its bootstrap SD.

## 7. Secondary analyses

- S1: memory by year. Within-company, within-year wtAUC for 2023, 2024, 2025 and 2026 (pairs of different seasons in the same year, month-demeaned), plus cross-sectional AUC by period. The 2026 figure is the closest thing to an out-of-knowledge baseline in the retrospective data. Seasonal habits of individual firms can move these, so they are descriptive.
- S2: H1–H5 within S&P 500 tickers and within the rest. Memory should be strongest for well-known names.
- S3: the cross-sectional contrast AUC(PRE) − AUC(POST) for K, and [N − A](PRE) − [N − A](POST), with PRE limited to Apr 1–Aug 14 of 2023 and 2024 to match POST's season. Reported for comparison only: cross-sectional contrasts also pick up stale priors and one-regime shocks in POST.
- S4: cross-sectional AUC of the N and A arms by period. Skill Jev draws from the numbers themselves shows up in A.
- S5: repeatability on set R: mean absolute difference between repeated answers and the share of events whose answer changes side of 0.5.
- S6: calibration of every Jev output: Brier score, ECE (10 bins), mean probability against base rate, share of answers at exactly 0.5.
- S8: H1 on events with an EPS surprise of at least 2% either way, where restatements are least likely to flip the label.
- S9: H1–H5 with missing answers set to 0.5. Valid-output rates by period and arm are reported.
- S10: the three K statements pooled into one within-company statistic (pairs are only formed within a statement), for more power.
- Controls: wtAUC in PRE and by year for both control models, per statement and pooled; the N − A version for Llama 3.1 70B. Llama's cutoff predicts memory in 2023 and not after.
- Prospective, reported after 2027-01-08: labels for PROSP built with the same code once 20-day drift windows close; cross-sectional AUC of Jev's K answers on PROSP against 0.5, and against the same season (Oct–Nov) of 2023–2024.

## 8. Decision rules for the write-up

- "Jev shows memory of outcomes": H1, H2 or H3 rejected after Holm.
- "Named backtests leak": H4 or H5 rejected after Holm.
- "No detectable memory (provisional)": none rejected, and the Sonnet 5 control's pooled K wtAUC in PRE (the S10 statistic, on subsample S: 256 beat, 511 reaction and 440 drift pairs) has a 95% interval above 0.5, which shows the probe finds memory where a model has it. The write-up states the minimum detectable effects, and the verdict stays provisional until the prospective set is scored.
- "Inconclusive": none rejected and the Sonnet 5 control also fails.
- "Rerun required": the served-model rule in section 4 triggers.
- Any within-2026 wtAUC (S1) with a 95% interval above 0.5 is reported next to the verdict.

## 9. Known limits and which way they push

- FMP restates EPS. Older records carry more restated values; in a related dataset I measured 41.4% of `epsActual` values changing between first-seen and final. Restated beat labels push toward finding nothing. S8 checks the clear cases.
- Labels use price returns without dividends, and the questions say "price return". Over 2 to 20 trading days the difference is small.
- A company-specific trend the model knew before 2023 (for example a firm already improving in 2022) could still separate a 2024 event from a 2023 one. I judge this weak but cannot rule it out.
- The universe is today's S&P 500 and tickers FMP still covers, so it leans toward survivors. The within-company design does not use differences between companies.
- An announcement date can be off by a day. The two-day reaction window absorbs most of that; the drift window starts after it.
- Company names are today's names from FMP profiles. A renamed firm appears under its new name, which can only make memory harder to trigger.
- The K statements are in the past tense and the N/A questions in the future tense. The two families are never compared with each other.

## 10. Done before freeze

- The data pull and event build described above.
- One Jev call with the example payload from TypeSafe's API docs (a customer-support message), to check the endpoint.
- Pipeline checks with a fictional company ("Acme Widgets Holdings Inc. (fictional)", ticker ACMW), one call per model and arm, run twice: before and after the questions were reworded to say "price return". Logged in `preflight/smoke.jsonl`.
- An independent review of an earlier draft (by a separate Claude instance). It showed by simulation that the draft's primary test, a cross-sectional PRE − POST AUC contrast, could flag stable priors and one-regime shocks as memory, with false-positive rates up to about 25%. The within-company design in section 5 replaced it; the old contrast survives as S3.
- No study event and no prospective event was sent to any model before freeze.

## 11. Budget, stopping and deviations

Hard stop at US$15 of total API spend. Expected spend is about US$7 (Jev about $1, Sonnet 5 about $4, Llama 3.1 70B about $2). There is no early stopping on results. Any change after freeze goes into `DEVIATIONS.md` with a timestamp and the reason, and affected results are marked.

## 12. Publication

This protocol, the code, the freeze proofs and all aggregate results will be published whatever the outcome. Per-event vendor values (EPS, revenue, prices) will not be, to respect FMP's terms. Tickers, dates and model outputs may be.

## Appendix: exact wording

K arm state fields: `record_type` ("quarterly earnings announcement"), `company`, `ticker`, `exchange`, `sector`, `announcement_date`.

K statements (Jev `noul`, criteria true/false as in `src/payloads.py`):
- `k1_beat`: "Is this statement true? In this earnings announcement, the company reported quarterly EPS above the analyst consensus EPS estimate."
- `k2_react`: "Is this statement true? Over the announcement window (from the last close before the announcement date to the close of the first trading day after it), the stock's price return was higher than the S&P 500's price return."
- `k3_drift`: "Is this statement true? Over the 20 trading days after the announcement window, the stock's price return was higher than the S&P 500's price return."

N arm state: K fields plus `as_of` ("announcement date, results just released") and `results` (`eps_vs_consensus_pct`, `revenue_vs_consensus_pct`, rounded to 0.1, capped at ±500, "not available" when the consensus is near zero or missing).
A arm state: `record_type`, `company` ("Company A"), `sector`, `as_of` ("results just released"), `results`.

N and A questions:
- `r2_react`: "Will the stock's price return over the announcement window (from the last close before the announcement date to the close of the first trading day after it) be higher than the S&P 500's price return?"
- `r3_drift`: "Will the stock's price return over the 20 trading days after the announcement window be higher than the S&P 500's price return?"

Control system prompt: "You estimate probabilities. You will receive a JSON record and a list of items about it. For each item, give the probability (a number from 0 to 1) that the answer is true or yes, using everything you know. Respond with only a JSON object that maps each item id to a number. No other text."
