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
