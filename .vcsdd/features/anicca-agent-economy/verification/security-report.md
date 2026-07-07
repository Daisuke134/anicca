# Security Hardening Report

## Feature: anicca-agent-economy | Sprint: 1 | Phase: 5 (Formal Hardening) | Date: 2026-07-07

## Tooling

| Tool | Availability | Version | Notes |
|---|---|---|---|
| Semgrep | Installed this session (`brew install semgrep`) | 1.168.0 | Ran against all 5 target files with `--config=p/security-audit --config=p/secrets --config=p/command-injection` (community registry rules, no login required). Resolved to 64 rules across `<multilang>` (38, generic), `js` (25), `json` (1). Raw JSON + text output captured. |
| Manual control-flow / grep review | This session | n/a | Wallet/private-key handling, command-injection surface (`child_process`), and path-traversal surface (unsanitized identifiers used to build filesystem paths) — the three categories this Phase 5 pass was explicitly asked to check — reviewed by direct code reading, not pattern-matching alone. |
| Wycheproof (cryptographic test vectors) | Not applicable | n/a | This increment introduces no new cryptographic primitive implementation (signing/hashing/KDF code). It uses `viem`'s `privateKeyToAccount` (existing, unchanged dependency) for address derivation only — no raw crypto math is implemented in the reviewed files. Explicitly noting non-applicability per the verifier protocol rather than silently skipping it. |

Raw captured outputs: `verification/security-results/semgrep-raw.json` (machine-readable, `results: []`, `errors: []`, `scanned` lists all 5 target file paths), `verification/security-results/semgrep-report.txt` (human-readable; empty body because Semgrep only writes findings to the text report and there were none — the "0 findings" summary itself was printed to the console, reproduced below).

```
Ran 64 rules on 5 files: 0 findings.
```

## Findings

### Semgrep (automated): 0 findings
All 64 rules (`p/security-audit`, `p/secrets`, `p/command-injection`) ran clean across `skills/economy/gig/lib/lock.mjs`, `skills/economy/gig/gig.mjs`, `runtime/loop/catalog-gate.mjs`, `runtime/loop/index.mjs`, and `skills/registry.json`. No hardcoded secrets, no obvious injection sinks, no flagged crypto misuse.

### Manual review: no hardcoded secrets or command-injection found
- Grepped all 4 `.mjs` target files for `PRIVATE_KEY = '0x...'`/`privateKey = '0x...'`/raw 64-hex-char literals — **none found**. All private-key material (`GIG_ESCROW_PRIVATE_KEY`, `posterPrivateKey`, `escrowPrivateKey()`) is read from `process.env` or passed in as a caller-supplied function argument, never hardcoded.
- Grepped for `eval(`/`new Function(`/`exec(`/`execSync(` — **none found** in any of the 4 target `.mjs` files.
- `runtime/loop/index.mjs` imports `child_process.spawn` (line ~483, `runSkillWithKillRef`) to launch a skill's `run.sh`. Reviewed the call: `spawn(skillPath, [], { env: childEnv, stdio: [...] })` — **no `shell: true`**, so there is no shell-metacharacter injection surface; `skillPath` is built via `path.join(ANICCA_HOME, 'skills', ...earnSkillRelPath(slot).split('/'))`, where `slot` is always a name drawn from `activeSkillSlots`/`eligibleSkillSlots` (registry-derived or `filterCatalog`-filtered), never a raw, unvalidated external string. This code is **pre-existing** (not part of this increment's own diff — `filterCatalog` only narrows which already-known slot names are eligible, it does not introduce a new path-construction step) and was reviewed as context, not as an in-scope finding.

### ⚠ Finding SEC-1 (MEDIUM, live-verified, pre-existing, non-blocking for this Phase 5 gate): path traversal via unsanitized `gigId`/lock key
**Location**: `skills/economy/gig/lib/lock.mjs::lockPaths(statePath, lockKey)` (line 45-46: `return { dir, file: path.join(dir, \`${lockKey}.lock\`) }`), reached via `skills/economy/gig/gig.mjs`'s `gigTake`/`gigDeliver`/`gigVerifyAndPay`, all of which call `withGigLock(statePath, gigId, ...)` with the caller-supplied `gigId` used directly as the lock key — **before** `store.getGig(state, gigId)` validates that the gig even exists (that check happens later, inside the locked critical section). The MCP-facing schema for `gigId` (`skills/economy/gig/mcp-server.mjs`, not itself one of this sprint's 5 target files, but the origin of the untrusted input) is `z.string()` — no format/character restriction.

**Live proof-of-concept (this session, real filesystem, not a hypothetical)**: called the REAL exported `withGigLock` with `statePath` inside a fresh temp directory and a crafted `gigId = "../../../../../../../../../../tmp/anicca-poc-escaped-file-live"`. Result: `path.join` collapsed the traversal segments and the lock file was created **outside** the intended `<statePath-dir>/locks/` directory, confirmed by checking `fs.stat` on the escape-target path *while the lock was held* (`true`), and observed being cleaned up by `release()`'s `fs.unlink` immediately after (`false` afterward — this is why a naive post-hoc existence check alone would miss the finding; the PoC checks **during** the critical section). PoC script: `/private/tmp/claude-501/-Users-anicca-anicca-project/549d0801-6e0b-4c52-97d1-2d7a32e94b81/scratchpad/path-traversal-poc2.mjs` (scratch file, not committed to either repo).

**Impact**: an attacker able to call `gig_take`/`gig_deliver`/`gig_verify_and_pay` (in this system's threat model, a counterparty agent such as automaton or Franklin, per `WITNESS-RUNBOOK.md` — not the open internet) with a crafted `gigId` can cause the gig-board process to create a transient `.lock` file at an attacker-chosen filesystem path (bounded by the process's own write permissions), and — because `reclaimStaleLock`'s branch performs `fs.stat`/`fs.rename`/`fs.unlink` when a file already exists at the computed path and looks stale by mtime — could potentially trigger a rename-then-delete of an **existing, unrelated file** the attacker points at, not merely create-and-clean-up a new one. This was not exploited further in this pass (out of scope for Phase 5, and doing so against a real pre-existing file was judged an unnecessary destructive escalation of a PoC that already proves the primitive); the create-and-observe PoC above is sufficient to establish the vulnerability is real, not theoretical.

**Scope disposition**: `lockPaths`'s "use the lock key verbatim as a filename fragment" pattern, and `gigId`'s unconstrained `z.string()` schema, both **predate this increment** (this sprint's REQ-101 changes to `lock.mjs` were scoped to the staleness-predicate extraction and the atomic-rename reclaim fix, per `specs/verification-architecture.md`'s Purity Boundary Map and the Phase 3 verdict's CRIT-001/002 evidence — neither touched `lockPaths` itself or `gigId`'s validation). None of this sprint's 25 proof obligations cover lock-key/gigId input sanitization, so **this finding does not block Phase 5's required obligations and is not one of the 25 PROPs**. It is disclosed here in full, live-verified detail per this project's honesty rules and the explicit instruction to check for path traversal, and is recorded as a **non-blocking, pre-existing, MEDIUM-severity finding** — analogous in disposition to how the Phase 3 adversary's FIND-501 was handled (documented, not silently dropped, not blocking, recommended as a follow-up).

**Recommended fix** (for a future increment, not applied in this Phase 5 pass since it is out of this sprint's approved contract diff): validate/allowlist `gigId` (and any other externally-supplied lock key) against a safe character set (e.g. `^[A-Za-z0-9_-]+$`, matching the same key-name generator this Phase 5's own `verification/proof-harnesses/lock-key-independence.proof.mjs` already assumes is safe) before it is ever passed to `withGigLock`/`lockPaths`, either in `gig.mjs`'s exported functions or in `mcp-server.mjs`'s zod schema (`z.string().regex(/^[A-Za-z0-9_-]+$/)`).

## Summary

- **Automated (Semgrep, 64 rules, 3 rulesets)**: 0 findings across all 5 target files.
- **Manual review (wallet/private-key handling, command injection, path traversal — the 3 categories this Phase 5 pass was asked to check)**: no hardcoded secrets, no shell-injection surface (no `shell:true`, no `eval`); **1 real, live-verified path-traversal finding (SEC-1, MEDIUM)** in the pre-existing `lockPaths`/`gigId` design, disclosed above with a live PoC, non-blocking for this sprint's 25 proof obligations, recommended as a follow-up hardening item.
- Wycheproof: not applicable (no new cryptographic primitive implementation in this increment).
- No blocking security findings against this sprint's own required proof obligations. SEC-1 is the one substantive finding from this audit and is carried forward as a disclosed, non-blocking, pre-existing issue rather than silently omitted.
