# Results: Jev look-ahead test

Generated 2026-10-11T16:38:25.121715Z; bootstrap B=10000; events 12533; balanced-panel tickers 812; Jev pin typesafe/jev-1.13-20260917 share 1.0; tie policy `raw`.

**Decision (pre-registered rule): no_detectable_leakage_provisional**

## Primary (Jev, within-ticker, same season, 2023 vs 2024, tie policy `raw`)

| H | question | estimate | 95% CI | one-sided p | Holm reject | pairs | tickers | design MDE |
|---|---|---|---|---|---|---|---|---|
| H1 | k1_beat | 0.5219 | [0.4907, 0.5522] | 0.0853 | False | 915 | 541 | 0.0524 |
| H2 | k2_react | 0.4839 | [0.4632, 0.5046] | 0.9417 | False | 1619 | 747 | 0.0394 |
| H3 | k3_drift | 0.5085 | [0.4872, 0.5299] | 0.2182 | False | 1462 | 729 | 0.0414 |
| H4 | r3_drift | -0.0044 (N 0.4952 / A 0.4997) | [-0.0162, 0.0074] | 0.7796 | False | 1462 | 729 | 0.0586 |
| H5 | r2_react | 0.0012 (N 0.6733 / A 0.672) | [-0.0085, 0.0108] | 0.4144 | False | 1619 | 747 | 0.0557 |

## Memory by year (Jev K arm, within-ticker within-year wtAUC)

| question | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| k1_beat | 0.4928 [0.461, 0.5223] (1461 pairs) | 0.5138 [0.4837, 0.5441] (1337 pairs) | 0.4816 [0.4565, 0.5077] (1416 pairs) | 0.4689 [0.4324, 0.5057] (610 pairs) |
| k2_react | 0.5104 [0.4892, 0.5318] (2508 pairs) | 0.4877 [0.4659, 0.5084] (2560 pairs) | 0.5084 [0.4869, 0.5291] (2511 pairs) | 0.503 [0.4772, 0.5283] (1167 pairs) |
| k3_drift | 0.5086 [0.485, 0.5322] (2387 pairs) | 0.54 [0.5184, 0.5622] (2438 pairs) | 0.4994 [0.4778, 0.5202] (2615 pairs) | 0.4755 [0.4474, 0.5039] (1143 pairs) |

## Cross-sectional AUC by period (Jev K arm)

| question | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| k1_beat | 0.6142 | 0.6187 | 0.6274 | 0.6476 | 0.6158 | 0.6692 |
| k2_react | 0.5284 | 0.5278 | 0.5214 | 0.5089 | 0.4987 | 0.5043 |
| k3_drift | 0.5465 | 0.5653 | 0.4856 | 0.4679 | 0.4925 | 0.5141 |

## Controls (subsample S, within-ticker PRE)

### sonnet5

- k1_beat: wtAUC_PRE 0.6074 [0.5528, 0.6632] (256 pairs); within-year 2023: 0.5435, 2024: 0.6116, 2025: 0.5929, 2026: 0.4905
- k2_react: wtAUC_PRE 0.6008 [0.5675, 0.6359] (511 pairs); within-year 2023: 0.5094, 2024: 0.6045, 2025: 0.5514, 2026: 0.5058
- k3_drift: wtAUC_PRE 0.5034 [0.4762, 0.5307] (440 pairs); within-year 2023: 0.5086, 2024: 0.5021, 2025: 0.51, 2026: 0.5014
### llama31

- k1_beat: wtAUC_PRE 0.4819 [0.454, 0.51] (249 pairs); within-year 2023: 0.4817, 2024: 0.5104, 2025: 0.4916, 2026: 0.5
- k2_react: wtAUC_PRE 0.5088 [0.4863, 0.5317] (510 pairs); within-year 2023: 0.504, 2024: 0.4929, 2025: 0.4879, 2026: 0.4826
- k3_drift: wtAUC_PRE 0.4898 [0.464, 0.5148] (440 pairs); within-year 2023: 0.4792, 2024: 0.4973, 2025: 0.4931, 2026: 0.5213
- wt_pre_named_minus_anon_r2_react: 0.0167 [-0.0193, 0.0533]
- wt_pre_named_minus_anon_r3_drift: 0.0286 [-0.0106, 0.0696]
- sonnet5 pooled K wtAUC_PRE: 0.5667 [0.546, 0.5875] (1207 pairs)
- llama31 pooled K wtAUC_PRE: 0.4962 [0.4812, 0.5116] (1199 pairs)

Probe valid (Sonnet 5 pooled K wtAUC_PRE, CI above 0.5): True

## Secondary

- S3 cross-sectional season-matched: {"k1_beat": {"estimate": -0.0427, "ci95": [-0.0846, 0.0004], "p_one_sided": 0.9740129935032483, "boot_sd": 0.0218, "n_boot": 2000, "auc_pre": 0.6274, "auc_post": 0.6701, "n_pre": 2849, "n_post": 1499, "tickers": 812}, "k2_react": {"estimate": 0.0036, "ci95": [-0.031, 0.0401], "p_one_sided": 0.4102948525737131, "boot_sd": 0.0179, "n_boot": 2000, "auc_pre": 0.5084, "auc_post": 0.5048, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "k3_drift": {"estimate": 0.0399, "ci95": [0.0053, 0.0756], "p_one_sided": 0.008995502248875561, "boot_sd": 0.0179, "n_boot": 2000, "auc_pre": 0.5547, "auc_post": 0.5148, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "did_r2_react": {"estimate": 0.0048, "ci95": [-0.001, 0.0105], "p_one_sided": 0.050974512743628186, "boot_sd": 0.003, "n_boot": 2000, "auc_named_pre": 0.6611, "auc_anon_pre": 0.6585, "auc_named_post": 0.6341, "auc_anon_post": 0.6363, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "did_r3_drift": {"estimate": 0.015, "ci95": [0.006, 0.0241], "p_one_sided": 0.0009995002498750624, "boot_sd": 0.0048, "n_boot": 2000, "auc_named_pre": 0.539, "auc_anon_pre": 0.5331, "auc_named_post": 0.5117, "auc_anon_post": 0.5208, "n_pre": 2980, "n_post": 1523, "tickers": 812}}
- S5 repeatability: {"k1_beat": {"events": 300, "mean_abs_pairwise_diff": 0.0058, "max_abs_diff": 0.03, "share_side_flips": 0.0433}, "k2_react": {"events": 300, "mean_abs_pairwise_diff": 0.0068, "max_abs_diff": 0.03, "share_side_flips": 0.0}, "k3_drift": {"events": 300, "mean_abs_pairwise_diff": 0.0068, "max_abs_diff": 0.04, "share_side_flips": 0.0}}
- S6 calibration: {"k1_beat": {"brier": 0.2622, "ece": 0.2731, "mean_p": 0.4637, "base_rate": 0.7369, "share_p_eq_0_5": 0.0556, "distinct_values": 57, "n": 12123}, "k2_react": {"brier": 0.2514, "ece": 0.041, "mean_p": 0.4494, "base_rate": 0.4904, "share_p_eq_0_5": 0.0131, "distinct_values": 41, "n": 12533}, "k3_drift": {"brier": 0.2475, "ece": 0.0404, "mean_p": 0.4038, "base_rate": 0.4443, "share_p_eq_0_5": 0.0007, "distinct_values": 37, "n": 12533}, "r2_react|N": {"brier": 0.2428, "ece": 0.0625, "mean_p": 0.4958, "base_rate": 0.4904, "share_p_eq_0_5": 0.0209, "distinct_values": 72, "n": 12533}, "r2_react|A": {"brier": 0.2498, "ece": 0.1036, "mean_p": 0.519, "base_rate": 0.4904, "share_p_eq_0_5": 0.0103, "distinct_values": 76, "n": 12533}, "r3_drift|N": {"brier": 0.2556, "ece": 0.0813, "mean_p": 0.4682, "base_rate": 0.4443, "share_p_eq_0_5": 0.0524, "distinct_values": 50, "n": 12533}, "r3_drift|A": {"brier": 0.2625, "ece": 0.1128, "mean_p": 0.4789, "base_rate": 0.4443, "share_p_eq_0_5": 0.0298, "distinct_values": 53, "n": 12533}}
- S8 H1 on |surprise|>=2%: {"estimate": 0.5286, "ci95": [0.4938, 0.5638], "p_one_sided": 0.05997001499250375, "boot_sd": 0.0178, "mde_design": 0.0592, "pairs": 716, "tickers": 459, "n_boot": 2000}
- S10 Jev pooled K: {"estimate": 0.5016, "ci95": [0.4888, 0.5142], "p_one_sided": 0.4027986006996502, "boot_sd": 0.0067, "mde_design": 0.0251, "pairs": 3996, "tickers": 794, "n_boot": 2000}
- valid output rate by period: {"K": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}, "N": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}, "A": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}}

## Output quality

- jev|K: {'records': 13133, 'served:typesafe/jev-1.13-20260917': 13133}
- jev|A: {'records': 12533, 'served:typesafe/jev-1.13-20260917': 12533}
- jev|N: {'records': 12533, 'served:typesafe/jev-1.13-20260917': 12533}
- jev|K|prosp: {'records': 757, 'served:typesafe/jev-1.13-20260917': 757}
- llama31|K: {'records': 3708, 'served:meta-llama/llama-3.1-70b-instruct': 3708, 'incomplete_output': 55}
- llama31|A: {'records': 3708, 'served:meta-llama/llama-3.1-70b-instruct': 3708}
- llama31|N: {'records': 3708, 'served:meta-llama/llama-3.1-70b-instruct': 3708, 'incomplete_output': 5}
- sonnet5|K: {'records': 3708, 'served:anthropic/claude-sonnet-5': 3708}

## Posthoc same-subsample (Jev vs Sonnet 5, shared pairs of S)

{"jev": {"estimate": 0.5041, "ci95": [0.4813, 0.5274], "p_one_sided": 0.3665633436656334, "boot_sd": 0.0118, "mde_design": 0.0456, "pairs": 1207, "tickers": 247, "n_boot": 10000}, "jev|k1_beat": {"estimate": 0.4902, "ci95": [0.4319, 0.5488], "p_one_sided": 0.6402719456108779, "boot_sd": 0.0299, "mde_design": 0.099, "pairs": 256, "tickers": 158, "n_boot": 5000}, "jev|k2_react": {"estimate": 0.4902, "ci95": [0.4559, 0.526], "p_one_sided": 0.7096580683863227, "boot_sd": 0.0182, "mde_design": 0.0701, "pairs": 511, "tickers": 242, "n_boot": 5000}, "jev|k3_drift": {"estimate": 0.5284, "ci95": [0.4896, 0.5677], "p_one_sided": 0.07658468306338732, "boot_sd": 0.0198, "mde_design": 0.0755, "pairs": 440, "tickers": 231, "n_boot": 5000}, "sonnet5": {"estimate": 0.5667, "ci95": [0.5457, 0.588], "p_one_sided": 9.999000099990002e-05, "boot_sd": 0.0107, "mde_design": 0.0456, "pairs": 1207, "tickers": 247, "n_boot": 10000}, "sonnet5|k1_beat": {"estimate": 0.6074, "ci95": [0.5522, 0.6607], "p_one_sided": 0.0001999600079984003, "boot_sd": 0.0276, "mde_design": 0.099, "pairs": 256, "tickers": 158, "n_boot": 5000}, "sonnet5|k2_react": {"estimate": 0.6008, "ci95": [0.5675, 0.6347], "p_one_sided": 0.0001999600079984003, "boot_sd": 0.0172, "mde_design": 0.0701, "pairs": 511, "tickers": 242, "n_boot": 5000}, "sonnet5|k3_drift": {"estimate": 0.5034, "ci95": [0.4762, 0.5312], "p_one_sided": 0.41551689662067587, "boot_sd": 0.0142, "mde_design": 0.0755, "pairs": 440, "tickers": 231, "n_boot": 5000}}
