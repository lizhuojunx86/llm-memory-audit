# Leaderboard v0 addendum: an open Jev-style model

Addendum to PREREG_LB.md, written before any study event was sent to this model. Author: Zhuojun Li; drafted by Claude (Anthropic) on the author's instruction.

Model: von (wfzyx/von, Apache-2.0), von-sdk 1.2.2, weights von-1.2.0 from Hugging Face snapshot 5df8185a4f2327ad0a7cd117cc4f701ac557b9ae, run locally on CPU in-process (no hosted API). It is a roughly 395M-parameter non-autoregressive decision model offered as a local drop-in for Jev.

Inputs: exactly Jev's K arm. The state is `state_for("K", event)` and the three questions are Jev's noul questions with their true/false criteria (`K_QUESTIONS`), for the 3,708 subsample-S events in the public `events.csv`. One call per event.

Statistic, decision rule and invalid-output handling: as in PREREG_LB.md. von is reported next to the eight API models, with its own Holm family of one.

Other open Jev-style models were considered: Bosun v3.1 needs `trust_remote_code` and a GPU to run in reasonable time, and jeff and openJev-verdict are smaller encoders of the same kind as von; they are left for a later round.
