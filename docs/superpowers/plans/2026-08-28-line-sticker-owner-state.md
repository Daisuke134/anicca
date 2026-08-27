# LINE Sticker Durable Owner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one restart-safe owner that submits and releases a validated sticker package exactly once, reconciles lost acknowledgements from official readback, and closes only after an observe-only duplicate-zero wake.

**Architecture:** Extend the existing `line_sticker.py` CLI with an atomic JSON owner, append-only effect receipts, and a tiny injected provider interface. Deterministic code owns identity, hashes, legal transitions, intent fencing, receipts, and replay; a later `line_sticker_browser.py` owns Creators Market DOM observation and mutation. Tests use a stateful fake provider but exercise real files, package validation, restart, lost acknowledgement, and replay.

**Tech Stack:** Python 3 standard library, existing LINE package validator, `unittest`, JSON/JSONL, SHA-256, atomic `os.replace` + fsync.

**Spec:** `docs/superpowers/specs/2026-08-28-line-sticker-loop-design.md`

## Global Constraints

- Normal operation has no human approval gate; only official ceremonies can produce `NEEDS_OWNER_CEREMONY`.
- External identity is `(account_id, set_id, revision, action)` and every effect has one stable SHA-256 key.
- No submit or release retry after lost acknowledgement until official observation reconciles it.
- Official provider observation, never process return or local state alone, advances submitted, approved, released, or public states.
- `CLOSED` requires official public matching readback followed by a later observe-only wake with `effect=0` and `duplicate_effect=0`.
- State is atomic JSON; effect receipts are append-only JSONL; terminal state is immutable.
- Unknown/malformed provider output, identity mismatch, package mutation, stale policy, low disk, or ledger/state conflict fails closed with no effect.
- No network/browser implementation, credential, new dependency, launchd edit, or generated media in this slice.

---

### Task 1: Persist and reconcile the submit/release lifecycle

**Files:**
- Modify: `skills/earn/line-sticker/line_sticker.py`
- Modify: `skills/earn/line-sticker/tests/test_line_sticker.py`

**Interfaces:**
- Add `ProviderObservation` data shape with exact fields: `account_id`, `set_id`, `revision`, `artifact_sha256`, `product_id`, `status`, `public_url`; status is one of `absent`, `draft`, `submitted`, `rejected`, `approved`, `released`.
- Add provider methods `observe(identity: dict[str, object]) -> dict[str, object]`, `submit(intent: dict[str, object]) -> dict[str, object]`, and `release(intent: dict[str, object]) -> dict[str, object]`.
- Add `wake_owner(state_dir: Path, package: Path, policy: Path, provider: object, account_id: str, revision: int, ffmpeg: str = "ffmpeg") -> dict[str, object]`.
- Add CLI `state --state-dir PATH` and keep `validate` behavior unchanged. Browser-driven `wake` CLI waits for the later browser slice; this task exposes the Python interface only.
- State result always includes `status`, `state`, `effect`, `readback`, `duplicate_effect`, `effect_key`, `product_id`, `public_url`, and `reason`.

- [ ] **Step 1: Write failing lifecycle and identity tests**

Reuse the complete real package helper once per test class. Add a `FakeProvider` whose official
inventory persists separately from owner state and counts submit/release calls. Write tests for:

```python
first = MODULE.wake_owner(state, package, POLICY, provider, "acct-1", 1)
self.assertEqual((first["state"], first["effect"], first["readback"]), ("WAITING_REVIEW", 1, 1))
self.assertEqual(provider.submit_calls, 1)

provider.status = "approved"
second = MODULE.wake_owner(state, package, POLICY, provider, "acct-1", 1)
self.assertEqual((second["state"], second["effect"], second["readback"]), ("RELEASED", 1, 1))
self.assertEqual(provider.release_calls, 1)

third = MODULE.wake_owner(state, package, POLICY, provider, "acct-1", 1)
self.assertEqual(third["state"], "TERMINAL_PENDING_REPLAY")
self.assertEqual(third["public_url"], "https://store.line.me/stickershop/product/123/en")

fourth = MODULE.wake_owner(state, package, POLICY, provider, "acct-1", 1)
self.assertEqual((fourth["state"], fourth["effect"], fourth["duplicate_effect"]), ("CLOSED", 0, 0))
self.assertEqual((provider.submit_calls, provider.release_calls), (1, 1))
```

Test wrong `account_id`, `set_id`, `revision`, artifact hash, product id, status, or public URL
as exact stable fail-closed reasons with effect zero.

- [ ] **Step 2: Run focused suite and confirm RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v
```

Expected: failure because `wake_owner` does not exist. Existing 30 tests remain otherwise green.

- [ ] **Step 3: Implement state, identity, atomic storage, and effect receipts**

Inside `line_sticker.py`, add exact states:

```python
OWNER_STATES = (
    "NEW", "WAITING_REVIEW", "REJECTED", "APPROVED", "RELEASED",
    "TERMINAL_PENDING_REPLAY", "CLOSED", "RECONCILE_UNKNOWN",
    "NEEDS_OWNER_CEREMONY", "NEEDS_POLICY_REVIEW",
)
```

The initial wake validates the package and derives `set_id`, `character_id`, ZIP SHA-256, and
package SHA-256 from validator/provenance output. Create `owner.json` with `version=1`, identity,
state `NEW`, empty product/public fields, and no time-varying diagnostic fields. Existing state must
match every identity and artifact value exactly.

Write `atomic_json(path, value)` using same-directory `mkstemp`, flush/fsync, `os.replace`, and
directory fsync. Reject symlink/nonregular owner or ledger paths. Append receipts with one JSON line,
flush/fsync, and exact keys:

```text
receipt_id, effect_key, action, account_id, set_id, revision,
artifact_sha256, product_id, before_status, after_status,
effect, readback, duplicate_effect, outcome
```

Effect key is SHA-256 of canonical JSON containing only `account_id`, `set_id`, `revision`, and
`action`. Before mutation append one `intent` receipt exactly once. After official readback append
one `acknowledged` receipt. Repeated wake must not append duplicate intent or acknowledgement rows.

- [ ] **Step 4: Implement official observation and transition gates**

Call `provider.observe(identity)` before every possible effect. Validate exact keys/types/status.
`absent` is valid only before submit. Non-absent observations must match artifact identity and have
one nonempty product id. `released` must have an HTTPS `https://store.line.me/` public URL; all other
statuses must have `public_url=None`.

Transitions:

```text
NEW + absent -> fenced submit -> matching submitted readback -> WAITING_REVIEW
WAITING_REVIEW + submitted/draft -> WAITING_REVIEW, effect 0
WAITING_REVIEW + rejected -> REJECTED, effect 0
WAITING_REVIEW + approved -> APPROVED -> fenced release -> matching released readback -> RELEASED
RECONCILE_UNKNOWN + matching submitted -> WAITING_REVIEW, effect 0
RECONCILE_UNKNOWN + matching released -> RELEASED, effect 0
RELEASED + matching released -> TERMINAL_PENDING_REPLAY, effect 0
TERMINAL_PENDING_REPLAY + same released -> CLOSED, effect 0, duplicate_effect 0
CLOSED + same released -> CLOSED, effect 0, duplicate_effect 0, no writes
```

Provider mutation return is never acceptance. After `submit`/`release`, call `observe` again and
require the exact matching official state. Any exception, malformed return, timeout, or mismatched
post-observation atomically stores `RECONCILE_UNKNOWN`, emits effect as `unknown`, and never retries
that action while observation remains absent/pre-effect.

- [ ] **Step 5: Add lost-ack, restart, conflict, and immutability regressions**

Add tests where fake submit/release mutates official inventory then raises. Restart with a new fake
provider object pointed at the same official inventory and assert reconciliation with mutation call
count unchanged. Add lost-ack with still-absent observation and assert repeated wakes remain
`RECONCILE_UNKNOWN` with zero new mutation.

Add exact regressions for truncated/malformed/symlink state, duplicate/conflicting ledger rows,
package bytes changed after state creation, provider exception before/after effect, invalid provider
status, invalid URL origin, wrong product/artifact identity, terminal state mutation attempt, and two
wakes over `CLOSED` producing byte-identical owner and ledger files.

- [ ] **Step 6: Add state CLI and deterministic status output**

`line_sticker.py state --state-dir PATH` reads only. Missing state returns one JSON object
`{"status":"uninitialized","effect":0,"readback":0}` and exit 0. Valid state returns the stable
owner summary and latest receipt outcome without secrets or paths. Malformed/symlink/conflicting
state returns one stable JSON error and exit 2. Preserve the existing one-object behavior for every
`validate` parse/config error.

- [ ] **Step 7: Run fresh verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v
python3 skills/earn/line-sticker/line_sticker.py state --state-dir /tmp/nonexistent-line-sticker-state
git diff --check
git status --short
```

Expected: all tests pass; state CLI emits exactly the uninitialized JSON; only the two owned files
are modified.

- [ ] **Step 8: Commit and push the durable-owner slice**

```bash
git add skills/earn/line-sticker/line_sticker.py \
  skills/earn/line-sticker/tests/test_line_sticker.py
git commit -m "feat(line-sticker): fence submit and release"
git push
```

## Self-review result

- Spec coverage: this slice closes state, submit/release effects, reconciliation, restart, public
  readback, and replay-zero with a fake official provider. Real browser transport, generation,
  launchd/onboarding, sales, and production effects remain subsequent slices.
- Placeholder scan: every state, receipt field, transition, lost-ack behavior, CLI result, and
  verification command is explicit.
- Type consistency: identity fields, provider observation keys, result keys, state names, and
  effect receipt keys match across interfaces, transitions, and tests.
