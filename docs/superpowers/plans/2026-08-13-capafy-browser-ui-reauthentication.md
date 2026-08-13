# Capafy Existing-Account Browser Reauthentication Plan

> **For agentic workers:** Implement only the assigned production/test files. Parent Sol owns this plan, specification, production state, acceptance, merge, and deployment.

**Goal:** Restore the exact existing Instagram account that owns Capafy's last verified Reel through the dedicated browser UI, prove the live owner independently, and wake the existing Marketer once without creating another account or incident.

**Architecture:** Reuse `capafy-ig-account-manager.sh`, its existing browser lease and `run_agent` lane, the mode-0600 account credential, `capafy_ig_session_verify.py`, lifecycle snapshot, canonical incident transitions, and launchd. The model handles only the variable Instagram account-switch/login UI; deterministic code selects the sole eligible recovery target, validates proof, mutates registry/lifecycle, closes the browser-loss incident, and reserves the Marketer wake. No private Instagram API, new login service, daemon, database, state file, or handoff kind is added.

**Tech Stack:** Bash, existing Python lifecycle/outcome/verifier CLIs, raw CDP helper, launchd.

## Verified production facts

- Dedicated identity `instagram:capafy-provision` is reachable on dynamic port `49938` with no holder. Its current authenticated self-profile link is `@capafy.skills10491`; the existing verifier rejects both `8m4q2z` and `10491` because modern `/accounts/edit/` no longer exposes `input[name=username]`.
- Modern settings DOM contains one same-origin top-level profile link with a child profile image: `/capafy.skills10491/`. External links, generic nav links, and settings links do not satisfy that structure.
- `@capafy.skills8m4q2z` is the only browser-owned `session_failed` row whose unresolved incident summary is exactly `active Instagram browser tab is missing`, browser identity is `instagram:capafy-provision`, and mode-0600 credential exists with matching username/password. It owns the last verified Reel `https://www.instagram.com/reel/DbhCWLhorxy/`.
- `@capafy.skills10491` also has a credential but its retirement reason is `ChallengeRequired`; it is not the browser-loss recovery target. Later `z8aoa4no` and `2417al9pxm` rows have no Instagram credential.
- Item 9b leaves a bounded `replacement_waiting` result for `2417al9pxm`; successful reauthentication must remove/replace it before waking Marketer so the old recovery handoff cannot reopen another incident.

## Scope and Ponytail budget

- Production: two existing files, soft target `<=100` net LOC.
- Tests: two existing files, only owner-proof, unique candidate, UI failure throttle, proof-gated mutation, crash replay, and at-most-once wake regressions.
- Reuse the current agent runner and raw-CDP verifier. Do not add a browser adapter, account service, prompt file, receipt DB, scheduler, or dependency.
- The user explicitly requires direct implementation with no TDD/RED cycle. Implement first, then run focused and cross-regressions.

## Task 1: Prove the modern settings-page owner

**Files:**
- Modify: `skills/earn/capafy-marketing/scripts/capafy_ig_session_verify.py`
- Test: `skills/earn/capafy-marketing/tests/test_capafy_ig_session_verify.py`

- [ ] Keep canonical origin `https://www.instagram.com`, hostname, and exact `/accounts/edit/` mandatory.
- [ ] Prefer the legacy username input when present. When absent, accept only exactly one same-origin anchor whose path is one top-level handle segment and which contains a profile image; its normalized path must equal the expected handle.
- [ ] Reject zero/multiple self-profile candidates, external absolute URLs, settings/reel/explore paths, missing image proof, malformed values, wrong owner, and injected target IDs.
- [ ] Preserve new-account credential/port checks and all prior wrong-origin/numeric-target counterexamples.

## Task 2: Reauthenticate one credentialed browser-loss target

**Files:**
- Modify: `skills/earn/capafy-marketing/capafy-ig-account-manager.sh`
- Test: `skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh`

- [ ] Before the existing session-recovery shortcut, select raw rows that are `session_failed`, browser-owned, bound to `instagram:capafy-provision`, and reference an unresolved Marketer incident whose summary is exactly `active Instagram browser tab is missing`. Require exactly one row whose mode is `0600`, credential username matches the normalized handle, and password is non-empty. Zero, multiple, invalid, future-throttled, or challenge-only candidates do not invoke browser/model.
- [ ] Lease the existing dedicated browser and send the current marketing agent a bounded prompt: attach only to that CDP identity; use the target's credential file; inspect/switch/logout/login through Instagram web UI only; never print secrets; never use `Client().login`, `login_by_sessionid`, cookies, private API, phone, passkey, CAPTCHA bypass, registry/lifecycle/incident writes, Telegram, publication, or new-account creation. If the target already owns the page, do nothing.
- [ ] After agent exit, run the independent verifier. Agent exit zero without exact proof is failure. On failure, atomically retain the row as `session_failed` with a typed `reauth_failure_reason` and an RFC3339 retry one hour in the future; release the lease and exit `1` without handoff, incident, Telegram, account append, or recursive wake.
- [ ] Only after exact proof, atomically update that same row to `publish_probe_ready`, current dynamic port/browser identity, `reauthenticated_at`, and clear only reauth throttle fields. Preserve historical incident/retirement evidence. Derive lifecycle through the existing snapshot and require exact handle, `session_established=true`, `capability=publish_probe`, and `replacement_requested=false` on readback.
- [ ] Idempotently advance the selected browser-loss incident `unresolved -> repair_started -> repaired -> verified` with concrete verification `{owner_session_verified:true, handle, browser_identity}` through the existing outcome CLI/event store. Never alter unrelated incidents.
- [ ] Remove the stale manager result, persist `reauth_marketer_wake_reserved_at` before `launchctl kickstart` of the existing Marketer, release the browser before the wake, and invoke that label at most once. If the process crashes after reactivation, a later pass finishes incident closure and wake reservation without logging in again.
- [ ] Preserve account-created, challenge, malformed-row, credential, verifier, lock, sender-retry, and Item 9b shortcut behavior.

## Direct verification

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_session_verify.py
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
python3 -m py_compile skills/earn/capafy-marketing/scripts/capafy_ig_session_verify.py
bash -n skills/earn/capafy-marketing/capafy-ig-account-manager.sh
git diff --check
```

The same Luna implements and pushes an isolated branch. The one fresh read-only Sol adversarial reviewer attacks candidate ambiguity, credential mode/username mismatch, secret leakage, wrong current owner, agent zero/no mutation, challenge/CAPTCHA, external/self-link false proof, state-before-proof, partial registry/lifecycle/incident transitions, result replay, lease ordering, duplicate wake, private API text/code, and successful existing paths. At most one correction returns to the same Luna; no second reviewer is used.

## Production acceptance

1. Parent records account/incident/event/result hashes, browser owner, run counts, and message IDs, then kickstarts only the existing account manager.
2. The loop—not Codex—switches the dedicated browser from `10491` to `8m4q2z`. Exact `/accounts/edit/` owner proof succeeds before state mutation; no account is appended and no private API is used.
3. Registry/lifecycle identify `8m4q2z` as `publish_probe_ready`; the `99b1374a` browser-loss incident is verified with one canonical event; the browser lease is released before one Marketer wake.
4. Marketer produces a verified Reel, a commercially valid no-op, or one bounded typed platform challenge. Immediate manager replay adds no login, row, incident, event, wake, or Telegram. This slice does not claim new revenue unless a paid order appears in the canonical ledger.
