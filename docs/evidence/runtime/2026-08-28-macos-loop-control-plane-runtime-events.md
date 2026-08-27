# macOS Loop Control Plane — TODO 6 uniform runtime events

`runtime/loop/runtime_event.py` defines the single version-1 runtime envelope:

```text
version, event_id, timestamp, loop_id, domain, run_id, phase, status,
release_sha, provider, profile_alias, effect_class, effect_status, blocker,
evidence_refs
```

The schema is exact and closed. It rejects missing/unknown fields, invalid
domain/phase/status/effect enums, malformed IDs/timestamps/release SHAs,
credential-shaped values, bearer/token/password/API-key text, `auth.json`, and
absolute `/Users/...` paths. Evidence references are bounded URI-like values.

JSONL append uses `flock`, `O_APPEND`, `fsync`, and mode 0600. Replaying the
same `event_id` is idempotent. Existing business ledgers and provider receipts
are unchanged and remain authoritative.

## Shared runner boundary

`runtime/agent-runner/agent_runner.py` emits one final `report` event when a
migrated job provides `LIFE_MANAGER_RELEASE_SHA`. It resolves domain,
effect class, and state root from the schema-v2 registry. The run ID is a hash
of the evidence directory, so private filesystem paths never enter the event.
Pre-migration invocations without a release SHA retain their prior behavior.

An event-write or validation failure changes the runner result to nonzero; a
provider success cannot be reported as observable success without its runtime
event. For non-`none` effects, provider/schema success yields
`effect_status=unknown`, never `verified`. Official adapters must later
reconcile and verify the external effect.

## Verification

- Runtime-event focused tests: valid private append, replay idempotence,
  unknown/secret/path rejection, effect-state separation, and no-effect status.
- Shared-runner integration test: one registry-grounded event, no private path.
- Status regression: invalid event rows cannot spoof PASS or verified effect.
- Canonical agent-runner suite: 24 tests pass.

Fixture readback produced exactly 15 fields, mode 0600, no absolute path, and
`status=pass` with `effect_class=application` / `effect_status=unknown`.

The legacy gig and writer runner copies are intentionally not declared unified;
TODO 7 must route them through the shared provider/profile boundary before
their labels migrate.

