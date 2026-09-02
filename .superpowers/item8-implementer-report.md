# Item 8 implementer evidence

Scope: only the assigned classifier, healthcheck shell script, and Python test file are staged for commit. This scratch report is intentionally untracked.

## Direct verification

```text
$ python3 -m pytest -q skills/self/capafy-loop/tests/test_capafy_business_health.py
...............                                                          [100%]Running teardown with pytest sessionfinish...

15 passed in 1.58s

$ bash skills/self/capafy-loop/tests/test_capafy_healthcheck_business.sh
  ok healthy business outcome exits zero
  ok healthy business outcome does not self-fix
  ok expired repair SLA exits nonzero
  ok expired SLA preserves incident id
  ok expired SLA invokes Capafy fixer
=== capafy business healthcheck: 5 passed 0 failed ===

$ python3 -m py_compile skills/self/capafy-loop/capafy_business_health.py
(exit 0; no output)

$ bash -n skills/self/capafy-loop/capafy-loop-healthcheck.sh
(exit 0; no output)

$ plutil -lint skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist
skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist: OK

$ git diff --check
(exit 0; no output)
```

## Production LOC delta

```text
17  3  skills/self/capafy-loop/capafy-loop-healthcheck.sh
70 10  skills/self/capafy-loop/capafy_business_health.py
```

Added production LOC: 87 (under the 100-LOC soft target). Net production LOC: +74.

## Judgment

An unknown incident owner is classified unhealthy and routed only to the fixed Company label. This preserves the requirement that every built-in unhealthy result has fixed routing metadata while ensuring no attacker-controlled owner value reaches `launchctl`.

## Git closure

```text
$ git commit -m "feat(capafy): route business watchdog repairs"
[feature/capafy-business-watchdog c2247cdf4] feat(capafy): route business watchdog repairs
 3 files changed, 294 insertions(+), 13 deletions(-)

$ git push origin feature/capafy-business-watchdog
To https://github.com/Daisuke134/life-manager.git
 * [new branch]          feature/capafy-business-watchdog -> feature/capafy-business-watchdog

$ git ls-remote origin refs/heads/feature/capafy-business-watchdog
c2247cdf44c11e680c1935d1a374526218be1e3a refs/heads/feature/capafy-business-watchdog
```

## Adversarial correction round

Implemented the updated routing and integrity contract without changing the plan, plist, or production state:

- Missing `hourly:` proof maps only to `ai.anicca.capafy-goal-monitor-hourly`; missing `daily_close:` proof maps only to `ai.anicca.capafy-goal-monitor-daily-close`.
- All five thresholds reject non-finite/non-positive values as fixed integrity/self-fix unhealthy output.
- Naive/future past-observation timestamps are fail-closed; future `next_retry_at` remains a valid schedule.
- Monitored delivery proofs require exact v2 fields, aware RFC3339 timestamps, lowercase SHA-256 projection IDs, numeric message IDs, and real calendar periods.
- Unknown incident owners produce fixed `repair_owner=integrity`, `repair_action=self_fix`; the shell invokes the generic fixer once and never `launchctl` for this action.

```text
$ python3 -m pytest -q skills/self/capafy-loop/tests/test_capafy_business_health.py
.............................                                            [100%]Running teardown with pytest sessionfinish...

29 passed in 1.94s

$ bash skills/self/capafy-loop/tests/test_capafy_healthcheck_business.sh
  ok healthy business outcome exits zero
  ok healthy business outcome does not self-fix
  ok expired repair SLA exits nonzero
  ok expired SLA preserves incident id
  ok expired SLA invokes Capafy fixer
=== capafy business healthcheck: 5 passed 0 failed ===

$ python3 -m py_compile skills/self/capafy-loop/capafy_business_health.py
(exit 0; no output)

$ bash -n skills/self/capafy-loop/capafy-loop-healthcheck.sh
(exit 0; no output)

$ plutil -lint skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist
skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist: OK

$ git diff --check
(exit 0; no output)
```

Correction production delta versus `c2247cdf4`: +112 / -24, net +88 LOC.
Total production delta versus plan base `b28ea6ecf`: +187 / -25, net +162 LOC.

```text
$ git commit -m "fix(capafy): harden watchdog repair routing"
[feature/capafy-business-watchdog a52b2423e] fix(capafy): harden watchdog repair routing
 3 files changed, 277 insertions(+), 34 deletions(-)

$ git push origin feature/capafy-business-watchdog
To https://github.com/Daisuke134/life-manager.git
   c2247cdf4..a52b2423e  feature/capafy-business-watchdog -> feature/capafy-business-watchdog
```
