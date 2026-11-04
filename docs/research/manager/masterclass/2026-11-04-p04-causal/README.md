# Manager Masterclass | P04-1–P04-3 Causal Inference

- **Date:** 2026-11-04 (Asia/Tokyo)
- **Study progress:** P04-1, P04-2, P04-3 lecture, synthetic code, and unit tests complete. P04-4 is next.
- **Empirical status:** Synthetic examples only. The Manager Behavior Foundation Model 1.0, real-world effects, and any user intervention remain **unvalidated**.
- **P00-3:** Real-world target, permissions and safety gate have **not** been signed off.

## Where to start

| Path | Purpose |
|---|---|
| `ROADMAP_STATUS_JA.md` | Single source of truth (P00–P12 course and progress) |
| `P04-1_JA.md` | Association, intervention, confounding, DAG, potential outcomes |
| `P04-2_JA.md` | RCT, ATE, ITT (original lesson) |
| `P04-3_JA.md` | Target trial, identification, g-formula, IPW, matching, AIPW and DiD |
| `experiments/p04_*.py` | Reproducible causal simulation, RCT and estimation code |
| `experiments/test_p04_*.py` | Unit tests, 57 total |
| `evidence/P04-3_SYNTHETIC_RESULTS.json` | Fully synthetic 30,000-person experiment results |
| `figures/*.png` | P04-3 estimation and DiD figures |
| `figures/build_figures.py` | Figure reproduction |
| `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx` | **74-slide** editable PowerPoint; 68 prior slides preserved, 6 P04 appendix slides added |
| `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf` | Corresponding 74-page PDF |
| `journal_club/SPEAKER_NOTES_JA.md` | Slide-by-slide Japanese speaker notes |
| `journal_club/RUN_OF_SHOW_JA.md` | Presenter run of show |
| `journal_club/build_p04_appendix.py` | Rebuild 74-slide deck from a supplied 68-slide base |

## Reproduce the tests

Install Python 3.11+ and NumPy (`python -m pip install numpy`). The figure build additionally requires Matplotlib; slide generation additionally requires python-pptx. Change into `experiments`, then:

```bash
python -m unittest discover -p 'test_p04_*.py' -v
python p04_3_observational_causal.py
```

The tests were run on 2026-11-04 and finished **57/57 passing** (P04-1: 14 newly reconstructed tests for the previously authored P04-1 script; P04-2: 17 existing tests; P04-3: 26 new tests). A passing synthetic test verifies a code contract, **not** a causal effect in a real population.

## Methodological notes

The artificial example has intentionally measured confounders, good overlap, binary treatment and stable treatment effects. Its recovered causal ATE does not establish no-unmeasured-confounding in actual data. The observed +26.12 percentage point association is misleading; appropriately identified estimators return approximately -10 percentage points for this particular artificial setting. A partial proxy for confounders is still biased (approximately +19.60 percentage points). AIPW tests demonstrate robustness when either nuisance function is correct, in this simplified setup. The AIPW toy estimate uses fitted nuisance models without cross-fitting and should not be confused with a production statistical analysis.

PowerPoint has **74** slides and the exported PDF **74** pages. Existing slides 1–68 are the original presentation, with only slide-total footers brought in line; slides 69–74 are causal appendices. Slides are presentation material, not a peer-reviewed causal study.

## Next milestone

P04-4: individual treatment effect heterogeneity and mediation. In parallel: specify P00-3 real-world consent, permissions and safety scope before any real intervention. The Manager policy-vs-policy RCT and benchmarking remain future milestones.
