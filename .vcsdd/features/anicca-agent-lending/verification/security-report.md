# Security Hardening Report — anicca-agent-lending (Phase 5, Formal Hardening)

## Tooling

- **Semgrep 1.168.0** (`/opt/homebrew/bin/semgrep`, already installed on this Mac Mini):
  - `semgrep --config=auto skills/economy/lending/lib/{lending-gate,lending-verify,gojo-read,lending-path}.mjs`
    → 200 rules run, **0 findings**. Raw output: `verification/security-results/semgrep-auto.json`.
  - `semgrep --config=p/security-audit --config=p/secrets` (same 4 files) → 61 rules run,
    **0 findings**. Raw output: `verification/security-results/semgrep-security-audit-secrets.json`.
- **Manual security-focused read** of all 4 files (injection, unsafe deserialization, missing input
  validation on money-affecting fields, integer overflow/precision loss, replay/reentrancy hazards),
  supplemented by a grep sweep confirmed by this session:
  ```
  fs.*          -> 1 hit  (gojo-read.mjs:10, fs.readFileSync only, read-only)
  fetch(        -> 1 hit  (lending-verify.mjs:17, routed through the single rpcCall() helper)
  Date.now()    -> 0 hits (every "nowMs" is an explicit parameter, no internal wall-clock read)
  writeFile/appendFile/unlink -> 0 hits (no file mutation anywhere in this diff)
  eval(/exec(/child_process   -> 0 hits (no command-injection surface)
  ```

## Findings

**No HIGH/CRITICAL findings.** Two LOW-severity, non-blocking observations, neither a defect in the
code delivered this sprint:

1. **`gojo-read.mjs`'s per-line `JSON.parse` is not wrapped in try/catch.** A single malformed line in
   `gojo-log.jsonl` would throw uncaught, propagating to whatever caller invoked `readGojoLogRows`
   (fail-open crash rather than a graceful skip-this-line/fail-closed-empty behavior). Low severity: this
   file is `economy/ubi`'s own trusted, self-written state, not external/attacker-supplied input, and the
   function's OTHER failure mode (`ENOENT`, the file not existing at all) is already correctly handled.
   Recommendation for a future sprint: wrap the per-line `JSON.parse` in its own try/catch and skip (not
   throw on) a malformed line, matching this feature's own fail-closed convention used everywhere else
   (e.g. `computeLenderAvailableUsd`'s `finiteOr` guards, `verifyRepayment`'s `safeBigIntNumber`).

2. **`lending-verify.mjs`'s `rpcUrl` parameter is fully caller-controlled with no allow-list/pinning.**
   `verifyRepayment`/`reconcileProvisionalDisbursement` both accept `rpcUrl` as a plain argument and POST
   directly to it — by design, so tests can point at a local mock server and production can point at
   Base mainnet. Not exploitable today: no orchestrator/caller exists yet that would ever pass an
   externally-influenced value for this parameter. Flagged as a **design note for the future
   orchestrator sprint**: pin/validate `rpcUrl` against a small, code-configured allow-list (mirroring
   `escrow.mjs`'s own `GIG_CHAIN=base` chain-selection discipline) rather than accepting an arbitrary
   caller-supplied endpoint, to close a latent SSRF-shaped surface before any caller with less-trusted
   input reaches this function.

## Positive finding worth recording — inherited path-traversal defense

This feature's new lock keys (`` `loan_${lenderId}` ``, `` `loan_borrower_${borrowerId}` ``, and the
REQ-108/109 `` `loan_${loan_id}` `` key — all constructed in `lending-gate.mjs`'s
`resolveLoanLockAcquisitionOrder` and used, per the spec, via the reused, unmodified
`~/anicca/skills/economy/gig/lib/lock.mjs`) automatically inherit that module's own **SEC-1**
path-traversal hardening (`isSafeLockKey`/`assertSafeLockKey`, `SAFE_LOCK_KEY_PATTERN =
/^[A-Za-z0-9_-]+$/`, fixed during a prior Phase 5 pass on the `gig` feature, confirmed by this session's
read of `lock.mjs` lines 40-77). Any `lenderId`/`borrowerId`/`loan_id` containing unsafe characters
(`/`, `..`, etc.) would cause `withGigLock` to throw rather than silently traverse outside the intended
`locks/` directory — this is a genuine, verified protection inherited via code reuse, not merely assumed.

**Forward-looking dependency note**: `anicca-agent-spawn`'s `citizens.json` registry (the source of real
`lenderId`/`borrowerId` values) does not exist on disk yet (confirmed this session — `find` found no
`citizens.json` anywhere under `~/anicca`), so this session could not confirm real citizen IDs are
already restricted to `[A-Za-z0-9_-]+`. If a future citizen ID ever contains another character (e.g. a
literal `#`), the orchestrator would hit a thrown exception (fail-closed, not a security breach, but a
correctness/availability concern) rather than a silent traversal. Worth confirming when
`anicca-agent-spawn`'s registry format is finalized.

## Summary

Zero exploitable vulnerabilities found in the 4 files delivered this sprint, across both automated
(Semgrep, 261 total rules, 0 findings) and manual review. The two LOW-severity observations above are
robustness/design notes for a future sprint, not blocking findings against this sprint's own delivered
scope. This feature also benefits from, and this session independently verified, an inherited
path-traversal defense in the reused `lock.mjs` module.

## Sprint-2 Addendum (Phase 5, `lending-orchestrator.mjs`)

### Tooling

- **Semgrep 1.168.0** (same install as sprint-1):
  - `semgrep --config=auto skills/economy/lending/lib/lending-orchestrator.mjs` → **200 rules run, 0
    findings**. Raw output: `verification/security-results/semgrep-auto-sprint2.json`.
  - `semgrep --config=p/security-audit --config=p/secrets` (same file) → **61 rules run, 0 findings**.
    Raw output: `verification/security-results/semgrep-security-audit-secrets-sprint2.json`.
  - 261 rules total, 0 findings — same rule sets sprint-1 already ran against the 4 pure/narrow modules.
- **Manual grep sweep** of `lending-orchestrator.mjs` (the only file this sprint adds/touches):
  ```
  fs.*                         -> 3 hits, all local-fs I/O against ledgerFile/LOANS_LEDGER_PATH-derived
                                   paths (readFileSync/mkdirSync/appendFileSync) -- no path segment is
                                   ever built from unsanitized external input (confirms PROP-112a's own
                                   structural finding: zero remote/networked path construction)
  fetch(                        -> 0 hits (this file never calls fetch directly -- payViaFacilitator/
                                   verifyRepayment/reconcileProvisionalDisbursement, sprint-1's own
                                   already-hardened effectful modules, own that surface)
  Date.now()                    -> 3 hits, all as the `nowMs = Date.now()` DEFAULT parameter value on
                                   this module's own three true entry points
                                   (executeLoanIssuanceAttempt/executeRepaymentClaim/
                                   executeDefaultDetectionSweep) -- every internal call site threads the
                                   received `nowMs` parameter, never re-reading the wall clock ad hoc
  eval(/exec(/child_process     -> 0 hits (no command-injection surface)
  process.env                   -> 1 hit (line 174, GIG_FACILITATOR_URL, see Findings below)
  ```

### Findings

**No HIGH/CRITICAL findings.** One LOW-severity observation, a carry-forward of sprint-1's own
already-documented design note (`lending-verify.mjs`'s `rpcUrl` parameter), now genuinely realized by
this sprint's own orchestrator rather than merely anticipated:

1. **`defaultDisburse`'s `facilitatorUrl` (line 174) and `executeRepaymentClaim`'s `deps.rpcUrl`
   (production-default wiring into `verifyRepayment`) are both still unpinned, caller/env-controlled
   endpoints** — `facilitatorUrl: deps.facilitatorUrl || process.env.GIG_FACILITATOR_URL ||
   "http://127.0.0.1:8405"`. Not exploitable today: the only caller of `executeLoanIssuanceAttempt`/
   `executeRepaymentClaim` in this diff is this sprint's own test suite and proof harnesses, which
   deliberately supply local mock endpoints by design (mirrors sprint-1's own precedent); no caller with
   less-trusted input reaches either parameter. Carried forward, unchanged in substance, as a design note
   for whichever future sprint wires an externally-triggered caller (e.g. an HTTP/MCP entry point) into
   these functions: pin/validate `facilitatorUrl`/`rpcUrl` against a small, code-configured allow-list
   before that caller's own input can reach either parameter.

### Summary

Zero exploitable vulnerabilities found in `lending-orchestrator.mjs`, across both automated (Semgrep,
261 rules, 0 findings) and manual review. The single LOW-severity observation is an unchanged
carry-forward of sprint-1's own already-documented `rpcUrl` design note, not a new or sprint-2-introduced
defect, and remains non-blocking (no untrusted caller reaches either parameter in this sprint's own
delivered scope). Combined with sprint-1's own already-clean 4 files, all 5 files this feature has
delivered across both sprints are Semgrep-clean and manually reviewed clean.
