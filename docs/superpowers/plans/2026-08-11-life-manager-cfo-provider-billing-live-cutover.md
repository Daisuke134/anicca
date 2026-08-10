# CFO-2a3.3b2 — Provider Billing Live Local Cutover Plan

**Status: COMPLETE.** The repaired target dependency install and second live bootstrap passed every gate below.

> Workflow: Ponytail full → Superpowers GLVS. Sol owns the reversible runtime cutover and final verification; no
> production/test code is written in this slice.

**Goal:** Repoint the one existing hourly launchd job from its stale/dirty CFO worktree to the verified CFO runtime,
run it once, and prove one autonomous real counts line without weakening the existing Moneytree/Telegram flow.

**Measured baseline**

- label `ai.anicca.life-manager-cfo-hourly` is loaded, `StartInterval=3600`, `RunAtLoad=true`, state is not running,
  runs are recorded, and last exit is `0`;
- its command and `WorkingDirectory` currently point to `.worktrees/cfo-m0-business-registry`, whose branch is behind
  canonical and has unrelated dirty/untracked spec work. That worktree is read-only for this cutover;
- target `.worktrees/cfo-4d1-finalize` is clean at verified runtime commit `390342404` plus plan-only ancestry merges,
  declares the required dependencies, passed focused
  `11/11`, CFO `320/320`, full tests, and isolated real main E2E;
- stdout/stderr paths, label, environment keys, interval, and shell/env-loading command already exist and are reused.

**Ponytail full decision**

1. Do not create another job, wrapper, daemon, scheduler, state store, backup branch, service, DB, or Telegram message
   path. Do not edit the dirty old worktree.
2. Change exactly two plist strings: only the worktree prefix in `ProgramArguments[2]` and `WorkingDirectory`, so the
   script and cwd use the same verified tree. Preserve every other plist key and command token byte-for-byte.
3. Use the existing job, logs, real Gmail configuration, private local state, Moneytree recovery, snapshot/delivery
   dedupe, and 3600-second interval.
4. A same-facts `quiet` finance result is valid and intentionally sends no duplicate Telegram. An actual `sent`
   result must retain `delivered=true`. Hourly forced duplicate Telegram UX belongs to M4, not this cutover.

## Cutover gates

0. Require the declared runtime dependencies to resolve from the exact target `apps/life-call` directory. If real
   launchd reveals a missing declared module, roll back first; Luna restores only the existing lockfile install and
   reruns focused/CFO tests. Do not add a new dependency, wrapper, loader, or fallback.
1. Save the exact old/new command strings, plist hash, log byte offsets, current run count/last exit, target commit,
   and target worktree cleanliness in the execution record. Print no env values or private financial data.
2. Patch only the two old worktree path occurrences to `.worktrees/cfo-4d1-finalize`, run `plutil -lint`, and require
   a structural check showing the exact command and `WorkingDirectory`, with all other keys unchanged.
3. Declare the live mutation, then `bootout` and `bootstrap` the same plist. Verify one loaded job, identical
   label/interval/RunAtLoad/log paths/environment-key set, and the exact new command.
4. Treat the `RunAtLoad=true` bootstrap run as the single trigger. Only if no run starts after bootstrap, kickstart the
   existing job once. Poll for a completed run and last exit `0`; do not spawn a second executor.
5. Read only log bytes appended after the saved offsets. Require one final JSON line with finance status `sent` or
   `quiet` and exact `providerBilling = confirmed_unresolved / 1 / 1 / 0`. Require no 64-hex source ref, account,
   invoice/path label, provider error, or secret-like field in that line.
6. Verify the live private provider-billing directory has one `0600` immutable JSON record, all fixed directories are
   `0700`, the record has only normalized confirmed keys, and no PDF/text/temp file remains. Print only booleans and
   counts, never the record values.
7. If any gate fails, immediately restore the exact old command, lint, reload, and verify the old job definition.
   Report the redacted failed gate; do not claim cutover success.
8. On pass, update parent/child specs, commit/push docs, and send one `Codex:::` milestone. Do not change the normal
   hourly schedule or manually send a duplicate finance report.

## Execution record

- First live attempt: structural plist checks passed, but the bootstrap run exited `1` before finance execution
  because the target install could not resolve the already-declared `@opentelemetry/api`. Sol immediately restored
  both old worktree references, linted and reloaded the original job; no stdout, finance message, or private record
  was produced. The rollback bootstrap also exposed the same stale-install failure in the old worktree.
- Repair remains inside this item: Luna restores the target install from its existing manifest/lock, then Sol repeats
  the same two-string cutover and real launchd gates. No product code or extra runtime component is justified.
- Completion: Luna restored the existing lockfile install with zero tracked changes; focused `9/9` and CFO `320/320`
  passed. Sol's second bootstrap run exited `0`, emitted one safe `quiet` finance line with provider counts `1/1/0`,
  added no stderr, retained exactly one private normalized `0600` record under `0700` directories, and left no PDF,
  text, or temp artifact. The live plist now points both command and cwd to the verified target worktree.
