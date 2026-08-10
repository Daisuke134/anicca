# Connector first launchd-owned wake Item 18 plan

## Goal

Trigger and observe the newly loaded single daily production owner once, without a parallel executor, and accept its first launchd-owned wake only from durable runtime evidence and exact cleanup.

## Preconditions

- Native label is loaded once from the mode-0600 09:00 daily plist; `runs=0`, state not running.
- Healthcheck, Healer shadow, and host bridge labels are unloaded.
- Git is clean/upstream; Connector process and lock are absent; `:9222` is healthy.
- Baseline bundle/report/delivery/action counts are `5/110/122/744`; target lease count is zero.

## Execute

- Use only `launchctl kickstart gui/<uid>/ai.anicca.life-manager-connector-native`. Do not call `skills/connector/run.sh`, Node entrypoints, browser scripts, or another executor directly.
- Observe launchd state/runs, append-only report/delivery/action counts, one Connector-owned target lease, and process/lock lifecycle. Never stop or restart the browser.
- Do not kick a second time. Let the bounded wake reach its own terminal status.

## Acceptance

1. Launchd runs advances 0→1 and returns to not running with exit code 0 for `applied_bundle` or `completed_no_effect`; a safe nonzero terminal is not falsely accepted and is repaired through the same entrypoint only.
2. One new durable wake report and delivery share a positive Telegram provider ID.
3. The wake produces a new applied bundle or reuses existing verified registration/bundles with Submit zero and continues to unprocessed candidates.
4. Live target observation shows at most one Connector lease/target; production tests remain the session-one proof because session IDs are intentionally not persisted in safe action history.
5. Final target lease, Connector process, and lock are zero; native remains the only loaded Connector label and still has one daily trigger.
6. Git remains clean/upstream. Record the terminal evidence in SSOT, commit, and push before moving to Item 19.

## Result

Pending launchd-owned wake.
