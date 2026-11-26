# Execution Run04: permutation consistency

UCI retrospective binary choice; train64 (12 positive), calibration64 (10 positive), test128 (23 positive), disjoint from own prior test slices. Two seeds, 8 steps per condition, same r4 LoRA and lr3e-4. DPO beta .1, consistency coefficient 5 fixed before run (not formal preregistration). Matched DPO vs DPO+MSE on semantic probabilities; weighted SFT comparator, calibrated logistic and prior. All six adapters reloaded and calibrated prediction parity verified. Not external benchmark or prospective/causal validation. Global and pretraining overlap unknown. No promotion without independent larger test and license review. Sources: https://arxiv.org/abs/2106.14448 and https://aclanthology.org/2025.findings-ijcnlp.127/ ; this is not an exact reproduction.

| condition | AUROC | Brier | NLL | raw order gap |
|---|---:|---:|---:|---:|
| base | 0.585093 | 0.147289 | 0.470557 | 0.205792 |
| prior | 0.500000 | 0.147949 | 0.472924 | nan |
| logistic | 0.607453 | 0.149106 | 0.468469 | nan |
| weighted_42 | 0.592961 | 0.147293 | 0.470567 | 0.084903 |
| dpo_42 | 0.644720 | 0.147126 | 0.470007 | 0.279277 |
| dpo_consistency_42 | 0.600000 | 0.147314 | 0.470637 | 0.079227 |
| weighted_43 | 0.603727 | 0.147315 | 0.470640 | 0.092048 |
| dpo_43 | 0.643892 | 0.147126 | 0.470008 | 0.279980 |
| dpo_consistency_43 | 0.599172 | 0.147313 | 0.470635 | 0.082252 |
