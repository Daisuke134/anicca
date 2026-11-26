# Manager Execution Run 03: binary DPO smoke test

Four optimizer steps per condition, two seeds, same 32 training sessions, calibration64, test64 (8 positive). Test slice ids[3520:3584] disjoint from own Run02; not verified globally untouched. SFT→DPO uses two steps each, frozen SFT reference at switch, different second-half examples. DPO uses observed action as pseudo-preference, not welfare preference. Beta=.1, r=4, AdamW lr=.0003. Raw order gap is mean absolute A/B swap probability difference. No statistical superiority, no promotion, no official benchmark. Logistic not calibrated unlike LM; probability metrics comparison is asymmetric. All weights saved but reload parity not yet tested. Script depends on pinned Pilot004 calibrate.py and its prior checkpoint preflight. UCI CC BY 4.0 data; upstream model license review required before public weight release. No raw data in this package.

| condition | AUROC | Brier | NLL | raw order gap |
|---|---:|---:|---:|---:|
| base | 0.558036 | 0.113025 | 0.390088 | 0.205161 |
| logistic | 0.636161 | 0.133244 | 0.426464 | nan |
| sft_42 | 0.555804 | 0.112981 | 0.389940 | 0.024101 |
| weighted_42 | 0.558036 | 0.113053 | 0.390180 | 0.014473 |
| dpo_42 | 0.573661 | 0.112877 | 0.389596 | 0.230994 |
| sft_dpo_42 | 0.553571 | 0.112998 | 0.389998 | 0.041767 |
| sft_43 | 0.555804 | 0.112976 | 0.389924 | 0.029015 |
| weighted_43 | 0.560268 | 0.113054 | 0.390183 | 0.014657 |
| dpo_43 | 0.573661 | 0.112879 | 0.389603 | 0.235790 |
| sft_dpo_43 | 0.555804 | 0.112983 | 0.389947 | 0.058357 |
