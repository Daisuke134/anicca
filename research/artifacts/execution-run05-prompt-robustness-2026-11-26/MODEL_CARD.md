# Run05: prompt sensitivity evaluation

Four fixed checkpoints (base and Run04 seed42 weighted, DPO, DPO+consistency); no new training. Four hand-written templates, two option orders, same 96 retrospective UCI test rows (9 positive), calibration64. Fixed canonical calibrator applied to all templates, separate ensemble calibrator fitted on same calibration set. Equal probability averaging, not Bayesian Prompt Ensembles reproduction. Raw probability range measures wording sensitivity; not POSIX score. Full Japanese template also changes choice labels and feature language, mixed template changes question only; no independent translation adjudication. Own-pilot disjoint test; team-wide and pretraining overlap unknown. No promotion, official benchmark or human benefit. References POSIX https://aclanthology.org/2024.findings-emnlp.852/ and BayesPE https://aclanthology.org/2024.findings-acl.728/.

| checkpoint | canonical AUC | ensemble AUC | raw range | calibrated range |
|---|---:|---:|---:|---:|
| base | 0.535121 | 0.316731 | 0.014931 | 0.008864 |
| weighted_42 | 0.546616 | 0.326948 | 0.015114 | 0.008959 |
| dpo_42 | 0.422733 | 0.232439 | 0.026508 | 0.021300 |
| dpo_consistency_42 | 0.565773 | 0.348659 | 0.017560 | 0.010129 |
