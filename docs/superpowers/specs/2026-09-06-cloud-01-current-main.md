# CLOUD-01 current-main execution note

This branch reapplies the already-reviewed CLOUD-01 formatter/test slice to current `main` without carrying the stale long-lived PR history.

Scope:
- detailed ordered walking/transit reminder text;
- online/locationless/failure-safe reminder variants;
- provider arrival display rather than Calendar start as route arrival;
- one bounded Telegram message;
- focused regression tests and the dedicated Cloud reminder workflow.

Not in scope:
- departure-time ownership or Calendar/call timing changes (CLOUD-02);
- onboarding, tenant, billing or landing changes;
- local loops, Docker/self-host experiments, ElizaOS, hackathon submissions;
- provider contract changes or new transport providers.

Base at branch creation: `2634105c7f310560077cf994b1adfb350cc252de`.
Implementation commit before this note: `00d2fe16d2c938ad918c69ae88a2aca22c8e5600`.

Release acceptance still requires applicable CI/review, merge of the exact candidate, deployment/readback of the target Cloud service, one authorized physical and online Telegram receipt, and replay-zero. Unit tests or this note alone are not release evidence.
