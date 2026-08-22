# Job Hunter model-loop handover

## SSOT

- Spec: `/Users/anicca/lm-loops-core/docs/superpowers/specs/2026-07-28-job-search-loop-design.md`
- Remaining-TODO SSOT: section `1.0` atomic queue, row `2a`, and section `1.2` model-based browser loop contract.

## Verified runtime

- Worktree: `/Users/anicca/lm-loops-core`
- Branch/push target: `codex/job-search-spec-20260821`
- HEAD: `f8dae46936ab774eafa1fee2934515b735675d9b`
- Active immutable release: `/Users/anicca/.local/share/anicca/job-search/releases/96f49a0ff5ba29557f5725dd2bc55c8750facc1d`
- Launchd: `ai.anicca.job-search-daily`, `StartInterval=3600`; trigger only with `launchctl kickstart -k gui/$(id -u)/ai.anicca.job-search-daily`
- CDP: `http://127.0.0.1:9222`
- State root: `/Users/anicca/.local/state/anicca/job-search`
- Latest checked run: `daily-20260822-082615`
- Latest Workday result: Rakuten `blocked / application_surface_not_found`
- Latest Telegram checkpoint: `28150`
- No Rakuten submit request, completion UI, or authoritative receipt evidence.

## Architecture decision

All ATS form interaction must be model-based browser work. Deterministic code is
limited to discovery, hard exclusions, duplicate/profile/CAPTCHA safety gates,
material routing, evidence, and ledger fencing. On a variable or unrecognized
surface, the existing authenticated CDP page and the same row go to
`browser-lane-agent`; the agent observes visible UI, clicks ordinary controls,
waits for rendered surfaces, snapshots each step, blocks only that row when a
fact is unknown, and continues the queue. `submitted` requires completion UI or
an exact authoritative receipt email. Current production has not implemented the
handoff yet: `JOB_SEARCH_ENABLE_MODEL_FALLBACK=0` remains the old default.

## First safe resume action

Read the spec and this file, then inspect `/Users/anicca/lm-loops-core/apps/job-search-loop/scripts/run-daily.sh` around the Workday lane and model runner. Implement the mandatory per-row browser-agent handoff in a test-first slice; do not create a second executor. Run focused tests, build/checksum a new immutable release, activate it only after the daily owner is idle, trigger the existing launchd loop, and verify Rakuten reaches step 2 before any submission claim.

## User-sendable `/goal`

```text
/goal Continue the Job Hunter in `/Users/anicca/lm-loops-core` until the hourly owner uses a mandatory model-based browser loop for every eligible Ashby/Workday form and produces real verified application outcomes. Read `/Users/anicca/lm-loops-core/.claude/handovers/2026-08-22_0857_job-hunter-model-loop.md` and `/Users/anicca/lm-loops-core/docs/superpowers/specs/2026-07-28-job-search-loop-design.md` first, then verify HEAD/upstream/dirty state and the active release before editing. Worktree/branch is `/Users/anicca/lm-loops-core` / `codex/job-search-spec-20260821`, upstream push target is `origin:refs/heads/codex/job-search-spec-20260821`, current verified commit is `f8dae46936ab774eafa1fee2934515b735675d9b`; do not touch `docs/loops/x-repost.md` or `state/effective-cron/`. Done means: deterministic safety gates hand each eligible row to `browser-lane-agent` through the existing authenticated CDP owner; the agent observes visible controls, handles provider-varying questions without guessing, snapshots each step, isolates blockers per row, and continues the queue; Rakuten reaches Workday step 2 and eventually a final completion UI or is truthfully blocked; `submitted` is written only for completion UI or an exact authoritative receipt email; Telegram reports submitted/blocked/not submitted per company and role. Verify with focused tests, release checksum/read-only checks, existing launchd kickstart, live evidence JSON, ledger reconciliation, and Gmail receipt evidence. Never bypass CAPTCHA/provider limits, retry `submit_unknown`, reapply Salesforce JR355047, create a second executor, or claim success from a click/HTTP response/ledger state alone. Iterate on the smallest root-cause fix; stop only on verified Done or a repeated external/credential blocker documented in the spec and handover.
```

## Protected state

Do not reapply Salesforce FDE JR355047 from `workday-manual-completed.json`. Do
not bypass CAPTCHA or provider limits. Do not retry `submit_unknown`. Preserve
unrelated dirty paths `docs/loops/x-repost.md` and `state/effective-cron/`.

## Current live blocker

- Active release: `4a4cd5c9f19e14888dd9f969bdd66fa0ff52989d`; both launchd owners use the
  immutable release and the daily owner has `StartInterval=1800`.
- NVIDIA `JR2015317` is authoritatively `submitted`. Gmail receipt
  `1a02a898712efee9` identifies the exact role and says the application was received.
- Recurrence run `daily-20260823-030807` resumed fresh NVIDIA Workday role
  `JR2022223` from its visual checkpoint, reached Review, invoked the one fenced
  submit action, and captured the visible Workday `Application Submitted` modal.
  Gmail independently produced message `1a02aab4b967f64a` confirming receipt of
  `JR2022223 Physical AI and Simulation Solution Architect`; inbox run
  `inbox-20260823-031243` reconciled that exact message and Ledger row to `submitted`.
- The remaining blocker is Telegram truth, not Workday application execution. The
  old run outcome and resume delivery are `send_started` without provider message
  IDs and must never be retried. `application_reporting deliver` now sends a new
  receipt-bound correction event keyed by application ID plus immutable receipt
  message ID. Deploy it, kick the existing inbox owner, and require a real Telegram
  message ID before closing the loop. Do not create another executor or browser.
- Release `7fdc2d29be0d7aeb0899d4e4f4b8a9a55b34ccd1` is active and passed its
  checksum. Existing owner run `daily-20260823-031951` used Luna/xhigh and the same
  CloakBrowser, then truthfully returned `queue_complete`: there was no eligible or
  discovered Workday row left in Ledger. The daily slot is not a quota. The next
  implementation slice is recurring official Workday discovery/admission before
  each 30-minute model wake, with canonical URL dedupe and existing submit fences.
- `workday_discovery` now implements that supply slice from the official NVIDIA,
  Workday, and Salesforce CXS surfaces. It isolates source failures, admits one
  unseen Japan/remote target-role row, and runs before the existing Luna owner.
  Focused tests pass; build, activate, kickstart, and verify the live discovery
  receipt plus exact model handoff next.
- Live run `daily-20260823-032744` passed discovery and exact Luna handoff for
  Salesforce `AI Native Delivery Consultant` (`JR334569`, application `add61f0f...75c`).
  Luna signed in with the stored tenant credential, uploaded the resume, and reached
  Personal Information. The stale prompt forced an invisible `Website` option copied
  from a different tenant, so choose failed before submit. That hardcoded path is now
  removed; a vanished provider option returns `action_rejected` plus fresh observation.
  The row remains `materials_ready`, submit was never called, and it is safe to resume
  after release. Telegram provider ACK remains independently unresolved.
- Resume run `daily-20260823-033554` had only exit-zero runtime commands and exposed
  `Job Board not checked`, yet Luna falsely returned `transport_failed`. The prompt
  now permits that status only after a real nonzero command. Discovery now skips
  provider calls while an eligible Workday queue exists, so recovery wakes drain
  checkpoints before adding more rows. No submit fence was consumed; resume again.
- Release `8ddb0bba47eec17ca1f55fdfe60e66184eb67418` then live-proved the fix:
  discovery returned `queue_present`, Luna selected visible `Job Board`, and completed
  the former-employment, country, and phone-type fields. Before `Save and Continue`,
  Ledger open failed with `sqlite3.OperationalError: unable to open database file`.
  Data-volume free space fell from 326 MiB to 290 MiB; `PRAGMA quick_check` remains
  `ok`. Canonical disk-cleanup preflight passed but its existing owner is still
  `spawn scheduled`; emergency guard last exited 3. No submit fence was consumed.
  Resume the same checkpoint only after capacity and Ledger open are stable.
- Free space later fell below 200 MiB. Canonical cleanup could not create its own
  lock/receipt (`ENOSPC`), while emergency guard remained inside `colima status`.
  `run-daily.sh` now invokes the shared Life Manager producer preflight before any
  evidence directory, Ledger, Telegram, or model work; it honors global stop flags,
  requires 512 MiB, and exits 75 without touching the checkpoint. Focused checks
  pass. Release the guard, but do not start Luna until capacity readback is stable.
- Capacity has recovered to 19 GiB and the canonical Ledger again opens with
  `PRAGMA quick_check=ok`. The 30-minute schedule is already installed
  (`StartInterval=1800`), and the browser owner is configured with `KeepAlive=1`.
  The latest saved Salesforce `JR334569` screenshot visibly stops at Personal
  Information with the required phone fields filled and `Save and Continue`
  available; it is not a completion screen, so both fresh Salesforce rows remain
  `materials_ready` and no submission may be claimed.
- Runtime recovery is now blocked outside the job code: CDP `127.0.0.1:9222` is
  down, no Job Hunter Chromium process exists, and `launchctl-safe preflight
  gui/501` returns `blocked_control_plane` with unresolved username/directory
  services plus unreadable GUI domain (`launchctl` error 141, `Reentrancy
  avoided`). Immutable release `8d59090e22739a3c8a15ac43ecfe2dbab4cfc30c`
  is installed but not active; active remains `8ddb0bba47eec17ca1f55fdfe60e66184eb67418`.
  Do not bypass the preflight, create a second executor/browser, or switch the
  symlink without proving the existing owner idle. On GUI-domain recovery, activate
  the installed release, kick only the existing daily owner, resume `JR334569`, and
  close only on Workday completion UI or an exact receipt email plus Ledger and
  Telegram provider-message-ID reconciliation.
