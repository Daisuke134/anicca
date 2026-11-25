# EconSimulacra × Anicca: scheduling before simulation
Research talk draft | 2026-11-25 | not submitted
---
## 1. Problem
Separate intervention timing, predicted reaction and observed outcome.
---
## 2. Reuse, do not reinvent
EconSimulacra (Hashimoto et al. 2026, arXiv:2606.26883): agents, environment, events, logs, rule-based comparator. MIT.
---
## 3. Experimental design
1,000 seeds per arm; 21 time steps; event probability 0 / .5 / 1. Exact upstream EventTrigger class. No LLM calls, no people.
---
## 4. Results
| probability | mean triggers | MC 95% interval |
| --- | --- | --- |
| 0 | 0 | 0–0 |
| .5 | 10.488 | 10.349–10.627 |
| 1 | 21 | 21–21 |
Periodic + interval rules are OR, not AND.
---
## 5. Anicca integration
Context → candidate/BCTO → scenario/trigger → simulated response/SSR → policy evaluation/OBP → consented intervention → observed benefit. Keep production eligibility separate.
---
## 6. Limitations and next study
Trigger component only; full package blocked by Python and DNS. Paired-seed rule/LLM/Manager scenarios, real heldout observations, uncertainty and safety. No efficacy or release claim.
