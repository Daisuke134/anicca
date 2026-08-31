# Connector first launchd-owned wake Item 18 plan

## Goal

Trigger and observe the newly loaded single daily production owner once, without a parallel executor, and accept its first launchd-owned wake only from durable runtime evidence and exact cleanup.

## Preconditions

- Native label is loaded once from the mode-0600 09:00 daily plist; `runs=0`, state not running.
- Healthcheck, Healer shadow, and host bridge labels are unloaded.
- Git is clean/upstream; Connector process and lock are absent; `:9222` is healthy.
- Baseline bundle/report/delivery/action counts are `5/110/122/744`; target lease count is zero.

## Execute

- Use only `launchctl kickstart gui/<uid>/ai.anicca.mr-bot-connector-native`. Do not call `skills/connector/run.sh`, Node entrypoints, browser scripts, or another executor directly.
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

- From baseline `5/110/122/744`, invoked exactly one `launchctl kickstart` on the loaded native label. Launchd runs advanced 0→1 under PID 86408 and returned to not running with exit code 0; no manual runner or second kick occurred.
- Wake `wake-be80daf280c27a9aab26163c` used one newly claimed target and the existing single-session code path. Luma exhausted with external effect zero, Connpass existing registration/bundle was reused with submit zero, then Peatix existing registration recovered its missing photo/final-bundle boundary. Action delta was fourteen safe observe/navigate/readback rows and no cache/direct/Harness submit row.
- Bundle count advanced 5→6. New bundle `applied-bundle:1fd10f527dd4270e3bfb7ac305dd695d60f2f84c5130ad8374b6cd08f7f50a30` is mode 0600, provider Peatix, status registered, and reuses the existing receipt, Calendar event, artifact, and Telegram message while adding photo ID `11333`. Wake report is `applied_bundle`, failure count zero, with positive Telegram ID `11334`.
- Independent `gog` readback found the Calendar ID exactly once, confirmed, linked, with the 64-character private idempotency marker. Artifact is 16,826 bytes, mode 0600, and its recomputed SHA-256 matches the bundle.
- The current wake target lease and CDP target are zero after exit; process and lock are absent. Nine legacy target-ledger records predate this wake and are explicitly deferred to Item 22 rather than silently deleted. Native remains loaded with runs one and the 09:00 daily trigger; other three labels remain unloaded; Git is clean/upstream. Item 18 is complete.
