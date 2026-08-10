# CFO-OPS1 Hourly Runtime Dependency Recovery Plan

> **Roles:** Sol owns diagnosis, plan, live trigger, verification, state, commit, and push. Luna runs the bounded
> dependency restoration command. No production source or test file changes.

**Status:** COMPLETE — real launchd run restored, no repository change

**Goal:** Restore the already-loaded local hourly CFO loop from exit `1` to one real terminal run without changing
its plist, report policy, financial logic, database state, or Telegram code.

## Measured failure

- Loaded label: `ai.anicca.life-manager-cfo-hourly`, interval `3600`, runs `2`, last exit `1`.
- Loaded script root: `.worktrees/cfo-4d1-finalize/apps/life-call` at commit `46f185327`.
- Failure: Node cannot resolve `@opentelemetry/api` before the hourly script starts.
- The committed lockfile contains `node_modules/@opentelemetry/api`; the loaded worktree currently does not.
- The plist and source code are not the cause. Do not edit or repoint them in this recovery.

## Ponytail decision

Restore the lockfile-defined dependency tree with one `npm ci --no-audit --no-fund`. Do not add fallback imports,
vendor packages, change module resolution, add a service, copy `node_modules`, or edit the launchd definition.

Change target: **0 repository files / 0 LOC**.

## Steps

1. Luna runs in the exact loaded package directory:

   ```bash
   npm ci --no-audit --no-fund
   node -e 'require("@opentelemetry/api"); process.stdout.write("otel-api: PASS\n")'
   git status --short
   ```

   Require install exit `0`, module resolution PASS, and no tracked change.

2. Sol records the current plist hash and loaded run count, then kickstarts the existing label once. Do not spawn a
   replacement executor.

3. Sol watches the same label to terminal state. Require runs to increase by exactly one, last exit `0`, and one new
   content-free hourly stdout result. The existing financial run may legitimately be `sent` or `quiet`; do not claim
   a Telegram delivery unless a positive provider receipt appears.

4. Require the plist hash/path to remain unchanged and stderr to gain no new module-resolution failure. If the run
   fails for a later real source problem, preserve that truth and plan the next single repair; never fake success.

## Out of scope

Changing quiet-on-unchanged behavior, adding hourly spam, billing reconciliation, Moneytree adapter changes,
provider usage repair, database migrations, cloud deployment, Binance, trading, or any financial write.

## Completion evidence

- Luna restored the exact lockfile tree: 237 packages, module-resolution PASS, tracked status clean.
- Sol triggered only `ai.anicca.life-manager-cfo-hourly`; runs advanced `2→3` and last exit changed `1→0`.
- The real result was content-free `quiet`, revision `5`, with no append or delivery; provider billing remained
  truthfully `confirmed_unresolved`.
- Stderr gained zero bytes. The plist path and SHA-256 stayed unchanged.
- No code, test, migration, plist, database, ledger, or Telegram write was made by the recovery itself.
