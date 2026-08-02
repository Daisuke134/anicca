# O1C-24 YC Daily-driver Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the deprecated YC `:9223` browser path and route its compatibility entry through the repository-owned `apply-to-funder --funder yc-w26` successor on the existing CloakBrowser daily-driver `:9222`.

**Architecture:** Check in an inert legacy skill tombstone and a minimal shell compatibility shim, then validate the entire migration with a content-addressed deterministic receipt. Deploy those exact assets with a recovery archive, remove obsolete active helpers, reconcile the disabled cron's durable state, and prove the route using controlled dry-run and read-only live observations. No YC field, file, save control, or submit control is touched.

**Tech Stack:** Node.js CommonJS, `node:test`, Bash, SHA-256, JSON, OpenClaw cron CLI, Playwright Core CDP, Git.

## Global Constraints

- The only YC browser endpoint is exact `http://127.0.0.1:9222` and browser ref `browser-profile://cloakbrowser/daily-driver`.
- The `gig-daily-driver` process that owns `:9223` is unrelated and must remain running with the same PID.
- The compatibility shim performs routing only; application semantics remain agent/provider-owned.
- The successor is exact `$HOME/.openclaw/skills/apply-to-funder/scripts/run.sh --funder yc-w26`.
- `DRAFT_ID`, `FOUNDER_VIDEO`, `DEMO_VIDEO`, unknown arguments, another endpoint, and a missing successor fail before successor execution.
- Existing `MODE` and `DRY_RUN` pass through. Live form access remains protected by the existing persisted day/freshness gates.
- The old active `fill.js` and `progress.js` are retired only after an exact recovery archive is created and verified.
- Do not persist cookies, credentials, raw YC bodies, application answers, websocket IDs, or full process environments.
- Browser navigation/write/save/submit effects are all zero except one bounded read-only owned-page observation of YC Home.
- O1C-25, O1C-26, and O1C-27 remain out of scope.

---

### Task 1: Checked-in compatibility assets

**Files:**
- Create: `apps/life-manager/runtime-assets/apply-to-yc/SKILL.md`
- Create: `apps/life-manager/runtime-assets/apply-to-yc/scripts/apply.sh`
- Create: `apps/life-manager/lib/yc-browser-route-migration.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: zero positional arguments plus optional existing `MODE`, `DRY_RUN`, and `BU_CDP_URL` environment values.
- Produces: one exact `exec bash "$HOME/.openclaw/skills/apply-to-funder/scripts/run.sh" --funder yc-w26`, or a non-zero refusal before the successor is invoked.

- [ ] **Step 1: Write the shim behavior tests first**

Create a temporary `.openclaw/skills` tree, copy the real shim into its `apply-to-yc` location, and place a fake executable sibling successor under `apply-to-funder` that writes its received argv and selected environment values to a temporary receipt. Execute that exact shim copy and assert literal output:

```json
{
  "argv": ["--funder", "yc-w26"],
  "BU_CDP_URL": "http://127.0.0.1:9222",
  "MODE": "prepare",
  "DRY_RUN": "true"
}
```

Add separate cases for default endpoint injection and pass-through of `MODE`/`DRY_RUN`. Name the production mutation each catches: wrong endpoint, wrong funder, missing argument, or dropped mode.

- [ ] **Step 2: Verify RED for the missing shim**

Run:

```bash
cd apps/life-manager
node --test lib/yc-browser-route-migration.test.js
```

Expected: fail because `runtime-assets/apply-to-yc/scripts/apply.sh` does not exist.

- [ ] **Step 3: Add refusal tests before implementation**

Assert the fake successor receipt remains absent when any of these are supplied: endpoint `:9223`, public/alternate host, URL credentials/query/fragment, positional argument, `DRAFT_ID`, `FOUNDER_VIDEO`, `DEMO_VIDEO`, caller-controlled `SKILL_DIR`, missing successor, or non-executable successor. Also prove that an attacker-controlled `HOME` cannot replace the sibling successor, and sanitize `BASH_ENV`/`ENV` before the fixed `/bin/bash` handoff. Assert each refusal exits non-zero with a bounded message that contains no environment values.

- [ ] **Step 4: Implement the minimal real shim and tombstone**

The shell script uses `set -euo pipefail`, validates exact zero arguments and exact endpoint string, checks legacy overrides are unset, requires the exact successor to be executable, exports exact `BU_CDP_URL`, and uses `exec bash ... --funder yc-w26`. The skill document names the successor, supported invocation, safety boundary, and recovery status only. It contains no field values, credentials, direct YC browser steps, `:9223`, browser launch command, save command, or submit command.

- [ ] **Step 5: Verify GREEN and wire outbound regression**

Run the focused test, then add `lib/yc-browser-route-migration.test.js` to `test:outbound` and run `npm run test:outbound`. Expected: all focused and outbound tests pass with zero failures.

### Task 2: Closed content-addressed migration receipt

**Files:**
- Create: `apps/life-manager/lib/yc-browser-route-migration.js`
- Modify: `apps/life-manager/lib/yc-browser-route-migration.test.js`

**Interfaces:**
- Consumes: `buildYcBrowserRouteMigrationReceipt(input, { now })`, where `input` contains fresh repository/runtime artifact observations, exact route and provider manifests, two live browser-owner observations, one cron observation, a deployment observation, and effect counts.
- Produces: a frozen privacy-minimal receipt with exact identities, artifact hashes/lengths, route, owner, cron, deployment, effects, and `migration_receipt_digest`. The digest is a deterministic structural checksum, not an authenticity signature; direct same-run readbacks remain the evidence source.

- [ ] **Step 1: Write a literal valid-receipt test**

Use arbitrary in-memory artifact bodies with independently computed declared hashes, current real route/provider manifests, literal PIDs, exact profile refs, exact endpoints, a disabled cron command containing `apply-to-funder/scripts/run.sh --funder yc-w26`, an exact recovery path/digest, and all zero effects. Assert the output contains no artifact body, cookie, credential, websocket ID, page body, form answer, or process environment.

- [ ] **Step 2: Verify RED for the missing builder**

Run the focused file. Expected: fail because `yc-browser-route-migration.js` does not exist.

- [ ] **Step 3: Add adversarial tests before production code**

Reject, one mutation per case:

- missing/extra/duplicate artifact role, bytes/hash substitution, non-canonical path, unknown nested field;
- route manifest endpoint/ref/context/connection/origin drift and missing `yc-application` route;
- provider manifest identity/route/successor/mode/submit-operation drift;
- daily-driver endpoint/profile/PID/browser/protocol drift;
- gig-driver endpoint/profile/PID drift or failure to preserve the same PID;
- cron ID/name/disabled state/command/funder drift;
- missing recovery archive, digest, retired helper inventory, installed asset digest, or readback equality;
- observation after receipt, observations over fifteen minutes apart, receipt older than five minutes, or non-canonical RFC3339;
- non-zero launch/navigation/form-write/file-write/save/submit/browser-close/gig-process-signal effects;
- forged receipt digest and input mutation.

- [ ] **Step 4: Implement minimal closed validator/builder**

Reuse `validateFunderBrowserRoutes` and `loadYcApplicationProviderManifest` through their public behavior. Add exact-key validation, canonical URL/path/role checks, SHA-256 recomputation, byte bounds, freshness/chronology, PID/safe-integer checks, exact effect zeroes, stable canonical hashing, recursive freezing, and privacy-minimal projection. Do not embed application facts or semantic browser judgments.

- [ ] **Step 5: Verify GREEN and mutation coverage**

Run focused and outbound tests. Mentally mutate endpoint, successor argv, cron enabled state, profile ref, old/new PID equality, one effect count, or artifact digest; require at least one named test to fail for every mutation.

### Task 3: Recoverable external deployment and live readback

**Files:**
- Modify externally: `~/.openclaw/skills/apply-to-yc/SKILL.md`
- Modify externally: `~/.openclaw/skills/apply-to-yc/scripts/apply.sh`
- Retire externally: `~/.openclaw/skills/apply-to-yc/scripts/fill.js`
- Retire externally: `~/.openclaw/skills/apply-to-yc/scripts/progress.js`
- Modify externally through CLI: OpenClaw cron `accelerator-application-monthly-1777948324077`
- Create: `docs/evidence/funding/2026-08-02-o1c24-yc-daily-driver-migration.json`

**Interfaces:**
- Consumes: exact checked-in asset hashes and the verified current external state.
- Produces: external readback equal to checked-in assets, one recovery archive, disabled durable cron, unchanged `:9223` owner PID, successful controlled dry-run routing, and one live migration receipt.

- [ ] **Step 1: Record fresh pre-state and create recovery archive**

Record sanitized process identity for `:9222` and `:9223`, active legacy file hashes/modes, successor hashes, cron live/disk state, and exact route/provider manifest hashes. Create an owner-only recovery directory under `~/.openclaw/recovery/apply-to-yc/`, outside every active skill subtree, named with the digest of a canonical inventory; copy the four legacy files into it preserving bytes/modes, and verify every copied SHA-256 before touching the active directory.

- [ ] **Step 2: Deploy exact assets and retire obsolete helpers**

Use the exact checked-in bytes for `SKILL.md` and `scripts/apply.sh`, preserve executable mode on the shim, and move `fill.js`/`progress.js` into the recovery directory rather than unlinking them. Read back hashes and require exact equality with the repository assets. If any step fails, restore all four original files from the verified recovery directory.

- [ ] **Step 3: Reconcile cron through OpenClaw and durable readback**

Run `openclaw cron edit accelerator-application-monthly-1777948324077 --message <exact-successor-command> --disable`, then require `openclaw cron list --all --json` and `~/.openclaw/cron/jobs.json` both report exact ID/name, `enabled:false`, and `--funder yc-w26`. If the live gateway updates but does not flush its documented durable store, first make an exact SHA-named backup and patch only those two fields in the exact durable row; re-read both surfaces. Keep it disabled and do not run the monthly job.

- [ ] **Step 4: Execute controlled shim routing tests on the deployed bytes**

First point a temporary-home copy of the installed shim at a fake successor and require exact argv/environment. Then run the actual installed shim with `MODE=prepare DRY_RUN=true`; require successor dry-run completion, no `browser-harness` invocation, and no live browser/process change. Do not execute default live mode.

- [ ] **Step 5: Perform bounded read-only live owner observation**

Connect Playwright Core over CDP to exact `:9222`, require one shared context, record existing pages, create one owned page, navigate to `https://apply.ycombinator.com/home`, record only final HTTPS origin/path and an agent-owned authenticated/current-home assessment, then close that page in `finally`. Do not call `browser.close()`. Re-read both listener PIDs/profile roots and require `:9223` PID unchanged and still reachable.

- [ ] **Step 6: Build and persist the exact live receipt/evidence**

Feed the fresh observations into the builder and store the resulting receipt plus direct artifact/deployment/readback/test evidence. Persist no raw bodies, cookies, credentials, websocket IDs, application content, or full environment. State the recovery procedure and the O1C-25 through O1C-27 claim boundary.

### Task 4: Independent review, verification, and closeout

**Files:**
- Modify: `docs/evidence/funding/2026-08-02-o1c24-yc-daily-driver-migration.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] **Step 1: Commit implementation before review**

Commit the builder, focused tests, package wiring, runtime assets, and plan. Record the full implementation SHA for the evidence and canonical spec.

- [ ] **Step 2: Request independent read-only review**

Review the exact implementation range, design, plan, runtime readback, backup, cron state, port owners, privacy boundary, and O1C-25 through O1C-27 boundary. Convert every Critical/Important finding into a focused RED regression before fixing it; repeat until final Critical/Important is zero.

- [ ] **Step 3: Run fresh full verification**

Run focused tests, `npm run test:outbound`, `npm run test:runtime-up`, full `npm test`, `bash -n` on both checked-in and installed shims, `node --check`, JSON validation, artifact SHA-256 readback, cron live/disk equality, unchanged `:9223` PID, exact `:9222` read-only receipt, `git diff --check`, and a secret/legacy-active-path scan.

- [ ] **Step 4: Close O1C-24 in the canonical spec**

Check O1C-24, record 55/143 complete and 88 remaining, name exact asset/cron/owner/readback facts, link design/plan/evidence and implementation SHA, and identify O1C-25 as next. Do not claim any preview or submission result.

- [ ] **Step 5: Commit, push, and verify remote equality**

Commit evidence/spec closeout, push `feat/five-phase-autonomous`, fetch it, and require local HEAD equals `origin/feat/five-phase-autonomous` with a clean worktree. Keep the worktree for O1C-25; do not merge main or create a PR.
