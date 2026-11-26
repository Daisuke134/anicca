# Run06: semantic consistency training

Matched weighted binary SFT, 3 training question templates x 2 answer orders, 32 train, 32 calibration, 64 test (13 positive), 2 seeds, 4 steps each. Joint adds both order and semantic probability MSE with coefficients 5; not isolated effects. Held English and Japanese question wording not used in training; context/labels remain English. Four trained adapters saved and reloaded; no new GPU spend. Own-pilot disjoint test only, no independent translation adjudication, external benchmark or promotion. Sources: https://aclanthology.org/2021.acl-long.264/ and https://papers.neurips.cc/paper/2020/hash/44feb0096faa8326192570788b38c1d1-Abstract.html .

| checkpoint | canonical AUC | held EN AUC | held JA AUC | raw range |
|---|---:|---:|---:|---:|
| base | 0.588235 | 0.619910 | 0.618401 | 0.005531 |
| prior | 0.500000 | nan | nan | nan |
| augmentation_42 | 0.588235 | 0.633484 | 0.616893 | 0.005316 |
| joint_42 | 0.589744 | 0.621418 | 0.610860 | 0.006088 |
| augmentation_43 | 0.598793 | 0.622926 | 0.612368 | 0.006378 |
| joint_43 | 0.585219 | 0.615385 | 0.609351 | 0.006430 |
