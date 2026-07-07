# Spec Review Verdict — anicca-agent-spawn — iteration 10

**Overall verdict: FAIL**

Fresh-context, zero-prior-history adversary pass. No Bash/shell tool was available in this session
(only Read/Write/Edit/Grep/Glob) -- this is disclosed explicitly wherever it affects a verification
method below. Both spec files were read in full, end to end (2037 + 641 lines), and every real
source file either spec cites in the areas under scrutiny was independently re-read from disk.

## Verification of the 2 prior (iteration-9) findings

| Finding | Status |
|---|---|
| FIND-801 (critical -- EVM-only re-derivation tool) | **Genuinely resolved.** Re-read `resolve-identity.mjs::readRawSecretFile` and `~/anicca/runtime/dashboard/telemetry-post-franklin.mjs` in full. Confirmed `telemetry-post-franklin.mjs` never imports/calls `@solana/web3.js`/`Keypair.fromSecretKey` (it does a manual `bs58.decode()` + byte-slice instead) -- I initially suspected this made the spec's "the EXACT, already-proven conversion telemetry-post-franklin.mjs already performs" citation false, but a careful literal re-parse of the exact sentence shows the appositive modifies only the *bs58-decode-to-64-bytes step*, not the subsequent `Keypair.fromSecretKey` call -- and that narrower claim is true and directly confirmed by the source (whose own comment, quoted verbatim in the spec, literally says "64 bytes: tweetnacl secretKey format == Solana Keypair.secretKey"). The spec is honest elsewhere that `@solana/web3.js` itself, while a real declared dependency, has zero production usages anywhere in this repo yet (confirmed via a repo-wide grep). PROP-105g/PROP-105i's conjunctive, two-branch structural requirement genuinely closes the EVM-only gap. |
| FIND-802 (major -- un-pinned `COORDINATOR_HOME` recreated in spec prose) | **Genuinely resolved.** Grepped both spec files for the literal `/Users/anicca` myself (27 + 4 occurrences) and classified every one: the one authoritative definition (REQ-105, before REQ-403 in reading order), every current worked-example invocation now correctly using the `COORDINATOR_HOME` symbol at the `env.HOME` slot (zero remaining hardcoded `env: {HOME: '/Users/anicca', ...}` literals), legitimate `homeDir`-field DATA values (a different concept), and historical changelog narration of the prior bug. The specific defect iteration 9 found (a worked example using the bare literal *before* the symbol's own definition, and one internally-inconsistent Acceptance Criteria bullet) does not recur anywhere in the current text. |

## New finding this iteration

- **FIND-901 (critical, spec_fidelity + verification_readiness)** -- REQ-103/105's brand-new
  `citizens.json` colony-citizen registry is placed at `~/anicca/skills/self/spawn/registry/citizens.json`
  -- a path INSIDE the git working tree -- and is specified to be BOTH a "versioned" seed file
  AND a live runtime-append target (REQ-305 appends a new record on every successful spawn), with
  no reconciliation of that tension anywhere in either spec file. Critically, the EXACT same `lib/`
  directory REQ-103 is adding a new module (`registry-path.mjs`) into already contains a
  pre-existing, purpose-built module, `state-path.js::resolveStateDir()`, whose own header comment
  documents a REAL prior incident this project already suffered from exactly this failure class:
  "The 2026-06 self-spawn E2E wrote children.jsonl to /tmp/spawn-live-state, which the OS
  tmp-cleaner deleted -- the colony record was lost." The real, currently-used caller of that
  mechanism (`run.sh`, lines 39-45) resolves the ledger to `~/.hermes/state/children.jsonl` --
  deliberately OUTSIDE the repo tree. `~/anicca/.gitignore` already excludes exactly this class of
  directory (`skills/*/state/`, `skills/*/*/state/`), but REQ-105's proposed `skills/self/spawn/registry/`
  path matches neither pattern, so by this project's own current conventions `citizens.json` would,
  by default, be git-TRACKED. Neither spec file ever mentions `state-path.js`, `resolveStateDir`,
  `.gitignore`, "durable", or "tmp-clean" anywhere (confirmed by exhaustive grep). Given this
  project's own routine, frequently agent-automated `git pull`/`git checkout`/`git worktree` operations
  on this exact repo (per this project's own CLAUDE.md/worktree.md), an uncommitted, live-appended
  `citizens.json` is a real, plausible, currently-unaddressed silent-data-loss risk for the colony's
  own citizen registry -- the same failure class, in the same directory, this codebase has already
  been burned by once. No proof obligation (PROP-105a through PROP-105i, PROP-103d) tests this
  property anywhere in `verification-architecture.md`.

## Why this is still FAIL

This would have been the first clean PASS after 10 iterations of the same REQ-101/105/403
wallet-identity area recurring (FIND-501 -> 601 -> 603 -> 701/703 -> 801/802) -- and, on their own
narrower terms, FIND-801 and FIND-802 genuinely are resolved. But a full, fresh, source-grounded
pass over the rest of the spec surfaced a new, previously-unflagged, critical defect in a closely
adjacent concern (the SAME registry file's own storage durability) that this iteration's fixes
never touched and that no prior iteration's findings ever examined. This is reported because it is
real and independently verified against actual, on-disk source files (`state-path.js`, `run.sh`,
`.gitignore`) -- not manufactured to avoid reporting a PASS.

## Full fresh pass over the rest of the spec

REQ-101 through REQ-403 were re-read in full and cross-checked directly against real, current
source: `is-self-funded.mjs`, `child-spec.js` + its test, `ledger.js`, `lock.mjs`,
`akt-cost-gate.js` + `config.json`, `colony-status.sh`, `resolve-identity.mjs` + its test file's
exact case count (20, confirmed), `telemetry-post-franklin.mjs`, and both `package.json` files. No
additional drift was found beyond FIND-901 above -- every other citation checked
(`isSelfFunded`'s boolean contract, `buildChildSpec`'s real required-field list and
`wallet:childWallet` string field plus its test assertion at line 36, `ledger.js`'s exact
`{readChildren, appendChild}` export surface, `lock.mjs`'s real `isLockStale`/`withGigLock`
signatures, `akt-cost-gate.js`'s real `computeSpawnGate` signature and `config.json`'s real
`spawn_cost_akt`/`buffer_akt`/`funding_route` values, and both real wallet addresses appearing
consistently across three independent files) matches the real, on-disk source exactly.
