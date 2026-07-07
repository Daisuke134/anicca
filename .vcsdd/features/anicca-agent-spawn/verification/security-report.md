# Security Hardening Report

**Feature**: anicca-agent-spawn · **Sprint**: 1 · **Phase**: 5 · **Date**: 2026-07-08

## Tooling

| Tool | Availability | Invocation |
|---|---|---|
| Semgrep | Available (`/opt/homebrew/bin/semgrep`, v1.168.0) | `semgrep --config=auto --config=p/security-audit --config=p/secrets skills/self/spawn/lib/ --exclude="__tests__"` |
| Manual security-focused read | Performed | All 9 delivered files read line-by-line for injection, unsafe deserialization, missing validation on money-affecting fields, path traversal, integer overflow/precision loss |

Raw Semgrep output: `security-results/semgrep-raw.json` (also captured in this session's terminal
transcript). 203 rules run (154 JS-specific + 49 multilang) across 12 tracked files (the 9 delivered
modules + `ledger.js`/`state-path.js`/`spawn-decision.js`, reused unmodified from prior sprints and
included by directory scope).

## Findings

**Semgrep: 0 findings across 203 rules, 12 files, 0 errors.**

**Manual review (no blocking findings):**

| Area checked | Result |
|---|---|
| Injection (shell/SQL/eval) | None of the 9 files invokes a shell, eval, or SQL — `treasury-gate.mjs`, `colony-balances.mjs`, `cloud-target.mjs`, `needs-solana-wallet.mjs`, `akash-funding-gate.mjs`, `child-spec.js` are pure/injected-callback modules with zero direct I/O; `citizens-registry.mjs`/`shelter-cost-ledger.js` only call `node:fs`/`node:fs/promises` APIs (`fs.open`, `fs.mkdir`, `fs.readFileSync`/`appendFileSync` via the reused `ledger.js`), never a shell command built from untrusted input. |
| Unsafe deserialization | `citizens-registry.mjs`/`ledger.js` only call `JSON.parse` on locally-written files under this process's own control (never untrusted network input) — same pattern already accepted elsewhere in this codebase (`lock.mjs`, `is-self-funded.mjs`). |
| Missing input validation on money-affecting fields | `decideColonySpawn`'s `colonySurplusUsd`/`spawnThresholdUsd`/`childrenProvisioning`/`maxConcurrentSpawns` all fail closed on non-finite/malformed input (FIND-1901/FIND-1902 fixes, confirmed by both the existing fixture tests and this session's NEW `fast-check` property tests sweeping ~700 generated non-finite/malformed inputs — see `verification-report.md`). `evaluateAkashFundingGate`'s `costAkt`/`bufferAkt` are passed straight through to the already-hardened, unmodified `computeSpawnGate` (`akt-cost-gate.js`, out of this sprint's scope, not re-audited here). |
| Path traversal | `registry-path.mjs`/`citizens-registry.mjs` construct `CITIZENS_REGISTRY_PATH` from `resolveStateDir({})` + a fixed literal (`"citizens.json"`) — never from caller-supplied/user-controlled path segments. No file path in any of the 9 files is built from untrusted external input. |
| Integer overflow / precision loss | All money math (`computeColonySurplusUsd`, `computePerCitizenSurplusUsd`, `evaluateAkashFundingGate`) uses plain JS `number` (IEEE-754 double), consistent with the established convention already used by `catalog-gate.mjs`/`lending-gate.mjs` elsewhere in this codebase — not a new risk introduced by this feature, and well within safe-integer/precision range for the USD/AKT magnitudes these gates operate on (single/double-digit to low-thousands). No `BigInt`/fixed-point requirement was identified for this sprint's scope. |
| Hardcoded secrets | Semgrep's `p/secrets` ruleset found 0. Manual read confirms no private key, API key, or credential is hardcoded in any of the 9 files — `colony-balances.mjs`/`cloud-target.mjs`/`akash-funding-gate.mjs` all take their network-calling functions as REQUIRED injected parameters with no default real endpoint wired (an intentional fail-closed-by-omission design choice already documented in `contracts/sprint-1.md`'s "Known residual scope boundary"). |
| Secrets handling discipline (live proof harnesses, this session's OWN new code) | `proof-harnesses/prop-403b-live-key-distinctness.mjs` reads real private-key material (via the unmodified `resolve-identity.mjs`) into process memory but never logs/prints it — only booleans (non-null, pairwise-equal) leave the process, matching `resolve-identity.mjs`'s own documented R5 discipline. `proof-harnesses/prop-204a-live-agentid-reverify.mjs` reads only a cached `{address, agentId}` pair (never a private key) from disk. |

## Summary

0 blocking findings. 0 Semgrep findings across 203 rules / 12 files. Manual review surfaced no injection,
deserialization, path-traversal, or hardcoded-secret issues, and confirmed the FIND-1901/FIND-1902
fail-closed money-safety fixes hold under randomized property-test input. No security-hardening action
required before Phase 6, beyond the pre-existing (already-documented) scope gaps covered in
`verification-report.md`.
