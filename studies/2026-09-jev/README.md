# Does Jev know how past earnings turned out?

Write-ups: [dev.to (EN)](https://dev.to/lizhuojunx86/does-jev-remember-2023-a-naive-test-says-yes-at-p-0001-a-within-company-test-says-no-5fja) · [知乎 (CN)](https://zhuanlan.zhihu.com/p/2086560706716087498)

I asked Jev (TypeSafe, served as `typesafe/jev-1.13-20260917`) about 12,533 US earnings announcements, 38,956 calls in all. The pre-registered test compares each company only with itself, and it finds no memory. Shown the name and date of two announcements from the same firm and the same season, one in 2023 and one in 2024, Jev can't tell which one beat. The verdict stays provisional until the prospective set below is scored after 2027-01-08.

| Test | Question | Result (95% CI) | Pairs |
|---|---|---|---|
| H1 | beat vs miss, name and date only | 0.506 (0.472 to 0.540) | 915 |
| H2 | stock beat the S&P 500 over the 2-day reaction | 0.479 (0.454 to 0.503) | 1,619 |
| H3 | stock beat the S&P 500 over the next 20 trading days | 0.483 (0.458 to 0.507) | 1,462 |
| H4 | named minus anonymized, 20-day drift | −0.006 (−0.021 to 0.009) | 1,462 |
| H5 | named minus anonymized, 2-day reaction | −0.001 (−0.013 to 0.011) | 1,619 |

H1 to H3 are within-company AUCs, where 0.5 means no memory. H4 and H5 are differences, where 0 means no memory. The same probe run on Claude Sonnet 5 gives 0.587 (0.561 to 0.613) pooled, so it does find memory in a model that has it. Everything else is in `results/results.md`.

The protocol is `PREREG.md`, frozen 2026-09-23T03:49:37Z. One thing changed after the freeze, for the control model only, and `DEVIATIONS.md` says what and why.

What the timestamp proves: `freeze.json.ots` anchors `freeze.json` in Bitcoin blocks 968225 (mined 2026-09-23T04:51:43Z) and 968226. The stamp was requested seconds before the first study request at 03:49:45Z, but the Jev run had finished by 04:03Z, so the proof on its own shows only that the protocol existed by 04:51:43Z. The prospective set below doesn't depend on that.

## Files

| Path | What it is |
|---|---|
| `PREREG.md` | the protocol as frozen |
| `DEVIATIONS.md` | every change after the freeze |
| `freeze.json`, `freeze.json.ots` | SHA-256 of the protocol, code and every input, and its OpenTimestamps proof |
| `src/`, `tests/` | the pipeline and its 17 tests |
| `frozen_code/run_models.py` | `run_models.py` as frozen, before the D2 change |
| `preflight/` | pipeline checks on a fictional company |
| `data/universe.json`, `data/fetch_log.jsonl` | the 900 tickers and the log of what was pulled from FMP |
| `work/manifest.json` | sample composition and base rates by period |
| `public_data/events.csv` | every event with ticker, company, sector, date and subsample flags, and no earnings or price values |
| `public_data/prospective_events.csv` | 757 announcements from October and November 2026 that Jev was asked about before they happened |
| `public_data/model_outputs.csv.gz` | every probability parsed from Jev, Sonnet 5 and Llama 3.1 70B |
| `public_data/output_quality.json` | per model and arm: records, HTTP statuses, served model versions, incomplete answers |
| `results/` | summary statistics from 10,000 bootstrap draws, plus the Jev-only interim run |
| `tools/check_freeze.py` | rehashes every published file against `freeze.json` |
| `tools/sim_crosssectional_false_positive.py` | the simulation that ruled out my first test design |

## What isn't here

The earnings and price data come from Financial Modeling Prep, whose licence doesn't allow redistribution. So `data/fmp/`, `work/events.jsonl`, `work/prospective.jsonl` and `work/requests.jsonl` stay private. The raw model logs stay private too, because the named and anonymized requests carry EPS and revenue surprises. All of their hashes are in `freeze.json`, and `public_data/` holds what can be shared.

## Check it

```bash
pip install -r requirements.txt
python tools/check_freeze.py      # also confirms freeze.json.ots commits to this freeze.json
python -m pytest tests -q         # 17 passed
python tools/sim_crosssectional_false_positive.py 200
ots info freeze.json.ots
```

One published file differs from its frozen hash on purpose: `src/run_models.py` gained the `--override` flag under D2. Its frozen original is `frozen_code/run_models.py`.

## Rebuild it

You need your own FMP key (`FMP_API_KEY`) and OpenRouter key (`OPENROUTER_API_KEY`).

```bash
python src/fmp_pull.py fetch      # reads data/universe.json
python src/build_events.py
python src/freeze.py              # your own freeze, replacing mine
python src/run_models.py --model jev --max-seconds 150      # resumable; repeat until nothing is left to send
python src/run_models.py --model sonnet5 --max-seconds 150 --override '{"reasoning": {"enabled": false}, "max_tokens": 300}'
python src/run_models.py --model llama31 --max-seconds 150
python src/analyze.py --boot 10000
```

Start from `fetch`. The `universe` step drew the 400 non-S&P tickers from my private PEAD research list, and `data/universe.json` is what it produced. FMP revises EPS and prices over time, so a rebuild won't reproduce my hashes. Jev's 38,956 calls cost me US$0.93 on OpenRouter, and the two control models another US$5.80.

## Prospective set

Jev answered the name-and-date questions for all 757 events in `public_data/prospective_events.csv` on 2026-09-23. The earliest of them is dated 2026-10-01. They get labelled and scored after 2027-01-08. If the 2026 events used as a comparison turn out to sit inside Jev's training data, these can't.

Zhuojun Li. The protocol, code and write-up were drafted by Claude (Anthropic) on my instruction. Apache-2.0.
