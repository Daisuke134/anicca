# R4/G1 push decider handoff — 2026-11-17

Implementation committed on codex/manager-push-decider; no push or production effects.

## Integration artifact

**Sender is an apply-ready patch, not an anicca-products commit:** `sender.patch`.
Verified with `git apply --check` against `/home/hatch/workspace/anicca-products`
HEAD `48d95f2d70493f4cbebf1d7a13c70b65a5906dc7`. That checkout is on main and has
unrelated dirty work, which was preserved. Apply from its root using `git apply
/path/to/sender.patch` on the integrator's owned branch.

Manager router gains an authenticated service-only `/manager/push-decisions`
batch endpoint (1–100 requests). Existing app authentication cannot select subjects.
The mount lane must pass `authenticate_sender` to router; default denies access.
Sender requires MANAGER_PRODUCT_URL (service origin, no /manager suffix) and
MANAGER_SENDER_TOKEN supplied at runtime. No real credentials included.
Use the same pseudonym key and stable account/profile subject as app observations.

The existing InterventionStore cases journal is the decision-log path: durable
assignment before response, delivery_id, assigned_probability, backend,
policy_version, decision_point_at and candidates. Sender uses that same UUID for
nudgeDelivery.id and APNs deliveryId/messageId; messageDetail also persists the
complete decision for replay. No independent decision engine or event schema.
Snake_case API fields retain the base branch contract; downstream camelCase
upload adapters must preserve their meanings and the same deliveryId.

Profile.metadata plus the latest 20 NudgeOutcome signals/rewards/timestamps,
local date, slot, language and time band reach the model. Stored delivery snapshots
are reused before mutable state is fetched. Model no-send is respected.
Manager failures or invalid responses suppress delivery; no catalogue fallback is
implemented, so there is no unflagged rotation path. Historical catalogue rows
are not resent. All slot constants and the server sender-enabled gate are unchanged.

Per-user/day/slot database uniqueness and an atomic parent queued→sending claim
permit at most one APNs attempt, including across devices, restarts and races.
**Tradeoff:** ambiguous APNs outcomes are not retried; a crash after claiming may
lose that notification. Failed/sending rows require reconciliation, never automatic
replay. This deliberately replaces the old retry path, which could duplicate a
push after remote acceptance. APNs collapse/idempotency keys alone cannot guarantee
exactly-once delivery. Multiple devices now receive one user-slot attempt total.

## Verification evidence

`/tmp/push-verify-venv/bin/python -m unittest discover -s tests/manager -v`

```
test_http_service_auth_batch_and_app_isolation ... ok
test_state_and_replay ... ok
Ran 2 tests
OK
same slot: user one=Rest; user two=Focus; replay generations=0
```

`node verify-sender.mjs /tmp/push-sender.mjs` executes the actual patched sender
source with isolated DB, Manager and APNs fixtures. To reproduce, apply the patch
in a disposable checkout, and pass its patched sender file as the argument.

```
fixture same slot 09:00: one=Rest; two=Focus; first sends=2; rerun duplicate sends=0; decision records=2
two devices per user: no duplicate user-slot send; Manager offline: sends=0
```

`node --check` on patched sender, `git apply --check` and `git diff --check` passed.
FastAPI/httpx were installed only in /tmp/push-verify-venv to run the HTTP tests.
These are fixture E2E results, not live model quality, PostgreSQL concurrency,
APNs delivery or deployment evidence. Proxy mount/service authentication and
shared journal identity must be wired by integration; no production claim made.

## Procedure / discrepancies

Read delegation first, audit R1/R2/R4, current base store/router, sender and Prisma
schema. Reused the sibling app decision journal and the sender's DB uniqueness
and claiming shape. Read using-superpowers (dispatched-task exclusion applies),
verification-before-completion and docs/team README/RULES/OWNERSHIP/WORKFLOW.
Astra Advisor is unavailable. The supplied assignment overrides legacy Life
Manager origin/worktree/push rules. Audit describes an older products commit;
the actual patch targets the local HEAD above. Old sender comments described
problem nudges and retries; the actual current path sends affirmations, and this
patch removes retries to satisfy strict duplicate prevention.
