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

- Active release: `736c398a095fab3655ad9f18dda08b75df37aa64`.
- NVIDIA `JR2015317` is not submitted. Fresh reset message `1a02a62e0498e3e2`
  opened the correct tenant page; visual evidence showed two password fields and
  one `Submit` button. The message is `navigation_unknown` and must not be retried.
- The unique reset-page `Submit` label is now supported, but the next daily run
  `daily-20260823-015932` naturally recovered and requested fresh message
  `1a02a70e1d915f80`. Inbox run `inbox-20260823-020818` opened it but observed
  both the native `Submit` and Workday's clickable `click_filter` wrapper. The
  secret rail now restricts reset actions to native button/input controls. The
  opened message is `navigation_unknown`; request a new reset message and never
  retry it.
- Fresh message `1a02a75c17302d42` subsequently reset the NVIDIA credential;
  visual evidence showed the final Sign In UI. Daily runs reached Review and
  consumed one submit fence. The completion screenshot was blank, so the Ledger
  remained `submit_unknown` and the action must never be retried. Gog independently
  found authoritative receipt `1a02a898712efee9` from `nvidia@myworkday.com` with
  exact company, role, JR2015317, and "has been received" text. Reconciler Gmail
  discovery now includes that real Workday wording; kick the existing inbox owner,
  verify Ledger `submitted`, then repair/verify the Telegram ACK without resubmitting.
