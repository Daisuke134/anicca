# Capafy Live-Browser Marketing Recovery Plan

**Goal:** Make the existing Marketer loop recover from a restarted or wrong-owner Instagram browser without a manual login, a duplicate publisher, or a stale retry incident.

**Architecture:** Keep `ai.anicca.capafy-ig-marketing-daily` as the only publisher and `ai.anicca.capafy-ig-account-manager` as the only replacement owner. The daily controller acquires the account's existing browser identity, asks the existing session verifier for one exact-owner Instagram target, and uses only that returned target. The verifier reuses or creates a tab inside the leased persistent profile, navigates to Instagram's account settings, and proves the live handle from page evidence. Missing/login/challenge/wrong-owner evidence fails closed. The controller reuses the existing `active Instagram browser tab is missing` incident identity, retires the invalid registry row, requests replacement, records a future RFC3339 retry, and wakes the account manager once. No password login, private API, new daemon, new state ledger, or manual publishing is added.

**Observed production cause:** Registry truth selects active row `@capafy.skills8m4q2z`, but its declared profile `capafy-mkt-69019` does not exist. Browser identity `instagram:capafy-provision` resolves to the live persistent profile `capafy-mkt-provision`; a leased read-only owner probe reached `/accounts/edit/` but proved `@capafy.skills10491`, an already-retired challenged account. The latest Marketer run therefore wrote `active Instagram browser tab is missing`, exited `1`, and refreshed incident `capafy-marketer-20260803T070010Z-99b1374a` while preserving its past-due 2026-08-07 retry. Account manager runs `1196` and exits `0` because lifecycle snapshot incorrectly remains `commercial_ready / session_established=true` from registry history.

**Ponytail scope:** Change three existing production files and three existing focused test files. Expected production delta is about 70 net lines and test delta about 60 net lines. Six files are necessary because exact-owner proof, controller routing, immutable incident retry, and the already-stale canonical event-count contract are one end-to-end trust boundary; no new file or abstraction is allowed.

## Files owned by implementer

- `skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh`
- `skills/earn/capafy-marketing/capafy-marketing-handoff.sh`
- `skills/earn/capafy-marketing/scripts/capafy_ig_session_verify.py`
- `skills/earn/capafy-marketing/tests/test_capafy_ig_session_verify.py`
- `skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh`
- `skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh`

The implementer must not edit this plan, the authoritative spec, launchd plists, production state, browser registry, account credentials, or any other file.

## Required implementation

1. Strengthen `capafy_ig_session_verify.py` without changing the account manager's current CLI contract:
   - keep registry-shape, unique-handle, browser ownership, and credential/handle validation for new-account verification;
   - add a current-session mode that does not require a credential and does not trust the registry's stale dynamic port;
   - under the caller's already-held browser lease, select one existing Instagram or blank page, creating one target only when none is reusable;
   - navigate that exact target to `https://www.instagram.com/accounts/edit/` and require a non-login, non-challenge page whose username/profile-link evidence resolves to the exact expected handle;
   - return one JSON object containing `verified=true`, exact `handle`, `session_owner=browser`, and numeric-free opaque `target_id`; never print cookies, credentials, DOM text, URLs with secrets, or screenshots;
   - exact mismatch, unavailable proof, login, challenge, malformed CDP response, or an untrusted target returns nonzero and no success JSON;
   - retain a command seam only for focused tests; production defaults to the existing raw-CDP adapter already used by `capafy_reel_poster.py`.
2. In `capafy-ig-marketing-daily.sh`:
   - after resolving the active row and acquiring its browser identity, call the strengthened verifier before creative generation;
   - use only the verifier-returned target ID; an explicit `CAPAFY_IG_TID` remains a test seam and must not bypass live verification in production launchd;
   - if exact owner proof fails, write a deterministic failure result whose stable reason remains `active Instagram browser tab is missing`, with the invalid active handle, a clear repair detail, and a future aware RFC3339 `next_retry_at` (five minutes is sufficient);
   - hand that result to the existing handoff; do not run the creative agent, selector, or poster, and do not attempt login or account creation in the controller;
   - release the browser guard exactly once on every success/failure path.
3. In `capafy-marketing-handoff.sh`:
   - for the exact controller session-recovery failure, preserve the stable reason/fingerprint so existing incident `capafy-marketer-20260803T070010Z-99b1374a` is reused rather than creating a competing incident;
   - when an invalid handle and valid future retry are present, retire that exact registry row, request replacement in lifecycle state, transition the incident with that retry, and kickstart only `ai.anicca.capafy-ig-account-manager` once;
   - reject or replace malformed/past/naive retry input with a bounded future RFC3339 value before transition;
   - do not use `-k` when waking an already-running manager; do not kill it, double-wake it, send success Telegram, or swallow an event-store conflict;
   - keep existing challenge, account-created, dry, and published behavior compatible.
4. Focused regressions, written after implementation (no TDD/RED cycle):
   - a missing tab is recreated/reused and exact current owner returns one target;
   - a logged-out, challenge, wrong-owner, malformed, or no-proof page cannot verify;
   - a stale registry port is allowed only in current-session mode; new-account verification still requires the exact port and matching credential;
   - controller exact-owner success reaches the existing selector/creative/poster once;
   - controller owner mismatch runs no selector/creative/poster, releases its lease once, retires only the invalid row, sets `replacement_requested`, gives the reused incident a future retry, and wakes only the account manager once without `-k`;
   - immediate replay does not create another incident, duplicate canonical incident event, second account retirement, or second simultaneous manager process.
5. Synchronize only the three directly affected stale assertions in `test_capafy_marketing_outcome.sh`. Its pre-change baseline is `34 passed / 3 failed` because a verified publication now correctly emits three canonical events while the old assertions expect two. Update those three expected counts to three; do not change production event emission to satisfy the stale expectations.

## Direct verification — no TDD/RED cycle

Run after implementation:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_session_verify.py
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_ig_lifecycle.py skills/earn/capafy-marketing/tests/test_capafy_reel_poster.py
bash -n skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh skills/earn/capafy-marketing/capafy-marketing-handoff.sh
python3 -m py_compile skills/earn/capafy-marketing/scripts/capafy_ig_session_verify.py
git diff --check
```

Then commit and push the isolated implementation branch.

## Single review and production closure

- Exactly one fresh Sol adversarial reviewer is read-only. It attacks wrong-owner acceptance, public-profile false proof, login/challenge redirects, stale dynamic ports, arbitrary target injection, secret leakage, `-k`, duplicate manager wakes, multiple active incidents, immutable event conflicts, and replay behavior. At most one correction returns to the same implementer; there is no second review.
- Parent independently reruns the focused commands, merges, and pushes only after the one review is resolved.
- Parent captures the production registry/lifecycle/incident/ledger hashes and Marketer/account-manager run counts, then kickstarts only the existing Marketer loop. The loop—not Codex—owns any retirement, provisioning, or publication.
- Accepted production terminals are exactly one of:
  1. the exact owner session is reacquired and the loop produces a verified public Reel with post-write owner proof;
  2. the loop proves a commercially valid no-op without a new external post;
  3. the existing incident is reused, its retry becomes a future RFC3339 timestamp, the invalid owner row is retired once, and the existing account manager owns replacement without event conflict or duplicate Telegram.
- Immediate replay must cause no duplicate external post, account creation, incident, canonical event, or Telegram. Close Item 9 only after a real terminal and replay evidence are written to the authoritative spec, committed, and pushed.
