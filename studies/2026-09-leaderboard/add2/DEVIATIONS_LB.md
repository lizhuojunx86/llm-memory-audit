# Deviations from addendum 2 (frozen 2026-09-24T15:07:58Z)

## D1 · 2026-09-24 · Account credit ran out mid-run; GPT-6 Astra stopped at 1,464 calls

- Between 15:12:42Z and 15:13:38Z OpenRouter refused 3,708 calls with HTTP 402 ("would exceed your available credits"): 1,464 for Claude Opus 5.5 and 2,244 for GPT-6 Astra. The author's latest credit top-up had not reached the account yet.
- Claude Opus 5.5: the 1,464 refused calls were re-sent unchanged once credit was available (`lb.py run opus55 --retry-failed`).
- GPT-6 Astra: 1,464 of 3,708 calls succeeded before the refusals. Real events cost US$0.0133 a call, about 2.5 times the smoke estimate, so finishing would cost about US$30 more. Refusals and successes interleaved as in-flight calls released reserved credit, so the 1,464 completed calls were spread across all four years (406 from 2023, 389 from 2024, 392 from 2025, 277 from 2026) and 180 of the 250 tickers; which calls went through depended on timing, not on the events. On those calls alone, with 423 within-company pairs against about 1,200 for the other models, its pooled AUC was 0.889 (0.849 to 0.924). The rest were sent later; see D2.
- The US$40 cap in this addendum was enforced per process as US$50 (the unchanged `lb.py`). Addendum spend is reported in the results.

## D2 · 2026-09-24 · GPT-6 Astra finished after a further top-up (decided after seeing its partial result)

- The author approved another credit top-up to finish GPT-6 Astra after seeing its partial result in D1, so the decision to finish was not blind to the data. Finishing restores the pre-registered design: all 3,708 calls, and four models in this addendum's Holm family. No request, setting or statistic changed.
- The 2,244 refused calls were re-sent unchanged from 15:58:15Z to 16:06:42Z (`lb.py run gpt6astra --retry-failed`), all with HTTP 200 and still on 2026-09-24. GPT-6 Astra cost US$48.45 in total.
- Addendum spend rose to US$73.27, above the US$40 cap in PREREG_LB.md. The cap in the calling process was raised to US$80 at run time (`lb.BUDGET_USD`; `lb.py` itself is unchanged and still matches `freeze.json`).
