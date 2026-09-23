# Results: Jev look-ahead test

Generated 2026-09-23T04:06:01.030611Z; bootstrap B=10000; events 12533; balanced-panel tickers 812; Jev pin typesafe/jev-1.13-20260917 share 1.0.

**Decision (pre-registered rule): inconclusive_probe_insensitive**

## Primary (Jev, within-ticker, same season, 2023 vs 2024, month-demeaned)

| H | question | estimate | 95% CI | one-sided p | Holm reject | pairs | tickers | design MDE |
|---|---|---|---|---|---|---|---|---|
| H1 | k1_beat | 0.506 | [0.4721, 0.5396] | 0.3648 | False | 915 | 541 | 0.0524 |
| H2 | k2_react | 0.4787 | [0.4539, 0.5034] | 0.9571 | False | 1619 | 747 | 0.0394 |
| H3 | k3_drift | 0.4829 | [0.4582, 0.5074] | 0.9144 | False | 1462 | 729 | 0.0414 |
| H4 | r3_drift | -0.0062 (N 0.5 / A 0.5062) | [-0.0208, 0.0086] | 0.8048 | False | 1462 | 729 | 0.0586 |
| H5 | r2_react | -0.0012 (N 0.6726 / A 0.6739) | [-0.0131, 0.0106] | 0.5994 | False | 1619 | 747 | 0.0557 |

## Memory by year (Jev K arm, within-ticker within-year wtAUC)

| question | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| k1_beat | 0.5106 [0.4768, 0.5434] (1461 pairs) | 0.4996 [0.4661, 0.5354] (1337 pairs) | 0.4993 [0.4668, 0.5334] (1416 pairs) | 0.4803 [0.4358, 0.528] (610 pairs) |
| k2_react | 0.5044 [0.4787, 0.5297] (2508 pairs) | 0.4801 [0.4538, 0.5059] (2560 pairs) | 0.4958 [0.4714, 0.5208] (2511 pairs) | 0.5047 [0.4723, 0.5375] (1167 pairs) |
| k3_drift | 0.5023 [0.4759, 0.5279] (2387 pairs) | 0.5299 [0.5059, 0.5551] (2438 pairs) | 0.4784 [0.4535, 0.5017] (2615 pairs) | 0.4952 [0.4631, 0.5278] (1143 pairs) |

## Cross-sectional AUC by period (Jev K arm)

| question | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| k1_beat | 0.6142 | 0.6187 | 0.6274 | 0.6476 | 0.6158 | 0.6692 |
| k2_react | 0.5284 | 0.5278 | 0.5214 | 0.5089 | 0.4987 | 0.5043 |
| k3_drift | 0.5465 | 0.5653 | 0.4856 | 0.4679 | 0.4925 | 0.5141 |

## Controls (subsample S, within-ticker PRE)

### sonnet5

- k1_beat: wtAUC_PRE None  (0 pairs); within-year 2023: None, 2024: None, 2025: None, 2026: None
- k2_react: wtAUC_PRE None  (0 pairs); within-year 2023: 0.0, 2024: None, 2025: 0.5, 2026: None
- k3_drift: wtAUC_PRE None  (0 pairs); within-year 2023: None, 2024: None, 2025: 1.0, 2026: None
### llama31

- k1_beat: wtAUC_PRE None  (0 pairs); within-year 2023: None, 2024: None, 2025: None, 2026: None
- k2_react: wtAUC_PRE None  (0 pairs); within-year 2023: None, 2024: None, 2025: None, 2026: None
- k3_drift: wtAUC_PRE None  (0 pairs); within-year 2023: None, 2024: None, 2025: None, 2026: None
- wt_pre_named_minus_anon_r2_react: None 
- wt_pre_named_minus_anon_r3_drift: None 
- sonnet5 pooled K wtAUC_PRE: None  (0 pairs)
- llama31 pooled K wtAUC_PRE: None  (0 pairs)

Probe valid (Sonnet 5 pooled K wtAUC_PRE, CI above 0.5): False

## Secondary

- S3 cross-sectional season-matched: {"k1_beat": {"estimate": -0.0427, "ci95": [-0.0846, 0.0004], "p_one_sided": 0.9740129935032483, "boot_sd": 0.0218, "n_boot": 2000, "auc_pre": 0.6274, "auc_post": 0.6701, "n_pre": 2849, "n_post": 1499, "tickers": 812}, "k2_react": {"estimate": 0.0036, "ci95": [-0.031, 0.0401], "p_one_sided": 0.4102948525737131, "boot_sd": 0.0179, "n_boot": 2000, "auc_pre": 0.5084, "auc_post": 0.5048, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "k3_drift": {"estimate": 0.0399, "ci95": [0.0053, 0.0756], "p_one_sided": 0.008995502248875561, "boot_sd": 0.0179, "n_boot": 2000, "auc_pre": 0.5547, "auc_post": 0.5148, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "did_r2_react": {"estimate": 0.0048, "ci95": [-0.001, 0.0105], "p_one_sided": 0.050974512743628186, "boot_sd": 0.003, "n_boot": 2000, "auc_named_pre": 0.6611, "auc_anon_pre": 0.6585, "auc_named_post": 0.6341, "auc_anon_post": 0.6363, "n_pre": 2980, "n_post": 1523, "tickers": 812}, "did_r3_drift": {"estimate": 0.015, "ci95": [0.006, 0.0241], "p_one_sided": 0.0009995002498750624, "boot_sd": 0.0048, "n_boot": 2000, "auc_named_pre": 0.539, "auc_anon_pre": 0.5331, "auc_named_post": 0.5117, "auc_anon_post": 0.5208, "n_pre": 2980, "n_post": 1523, "tickers": 812}}
- S5 repeatability: {"k1_beat": {"events": 300, "mean_abs_pairwise_diff": 0.0058, "max_abs_diff": 0.03, "share_side_flips": 0.0433}, "k2_react": {"events": 300, "mean_abs_pairwise_diff": 0.0068, "max_abs_diff": 0.03, "share_side_flips": 0.0}, "k3_drift": {"events": 300, "mean_abs_pairwise_diff": 0.0068, "max_abs_diff": 0.04, "share_side_flips": 0.0}}
- S6 calibration: {"k1_beat": {"brier": 0.2622, "ece": 0.2731, "mean_p": 0.4637, "base_rate": 0.7369, "share_p_eq_0_5": 0.0556, "distinct_values": 57, "n": 12123}, "k2_react": {"brier": 0.2514, "ece": 0.041, "mean_p": 0.4494, "base_rate": 0.4904, "share_p_eq_0_5": 0.0131, "distinct_values": 41, "n": 12533}, "k3_drift": {"brier": 0.2475, "ece": 0.0404, "mean_p": 0.4038, "base_rate": 0.4443, "share_p_eq_0_5": 0.0007, "distinct_values": 37, "n": 12533}, "r2_react|N": {"brier": 0.2428, "ece": 0.0625, "mean_p": 0.4958, "base_rate": 0.4904, "share_p_eq_0_5": 0.0209, "distinct_values": 72, "n": 12533}, "r2_react|A": {"brier": 0.2498, "ece": 0.1036, "mean_p": 0.519, "base_rate": 0.4904, "share_p_eq_0_5": 0.0103, "distinct_values": 76, "n": 12533}, "r3_drift|N": {"brier": 0.2556, "ece": 0.0813, "mean_p": 0.4682, "base_rate": 0.4443, "share_p_eq_0_5": 0.0524, "distinct_values": 50, "n": 12533}, "r3_drift|A": {"brier": 0.2625, "ece": 0.1128, "mean_p": 0.4789, "base_rate": 0.4443, "share_p_eq_0_5": 0.0298, "distinct_values": 53, "n": 12533}}
- S8 H1 on |surprise|>=2%: {"estimate": 0.514, "ci95": [0.4778, 0.5511], "p_one_sided": 0.23488255872063968, "boot_sd": 0.019, "mde_design": 0.0592, "pairs": 716, "tickers": 459, "n_boot": 2000}
- S10 Jev pooled K: {"estimate": 0.4865, "ci95": [0.4716, 0.5018], "p_one_sided": 0.9600199900049975, "boot_sd": 0.0077, "mde_design": 0.0251, "pairs": 3996, "tickers": 794, "n_boot": 2000}
- valid output rate by period: {"K": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}, "N": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}, "A": {"P1": 1.0, "P2": 1.0, "P3": 1.0, "P4": 1.0, "P5": 1.0, "P6": 1.0}}

## Output quality

- jev|K: {'records': 13133, 'served:typesafe/jev-1.13-20260917': 13133}
- jev|A: {'records': 12533, 'served:typesafe/jev-1.13-20260917': 12533}
- jev|N: {'records': 12533, 'served:typesafe/jev-1.13-20260917': 12533}
- jev|K|prosp: {'records': 757, 'served:typesafe/jev-1.13-20260917': 757}
- sonnet5|K: {'records': 3708, 'served:anthropic/claude-sonnet-5': 83, 'incomplete_output': 17, 'http_402': 3625}
