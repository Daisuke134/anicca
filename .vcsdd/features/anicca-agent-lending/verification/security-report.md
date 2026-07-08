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

## Sprint-3 Addendum (Phase 5, `run.sh` + `scripts/wake-gate.mjs` + `registry.json` `economy/lending` slot)

### Tooling

- **Semgrep 1.168.0** (same install as sprint-1/sprint-2):
  - `semgrep --config=auto skills/economy/lending/run.sh skills/economy/lending/scripts/wake-gate.mjs`
    → **203 rules run, 0 findings**. Raw output: `verification/security-results/semgrep-auto-sprint3.json`.
  - `semgrep --config=p/security-audit --config=p/secrets` (same 2 files) → **61 rules run, 0 findings**.
    Raw output: `verification/security-results/semgrep-security-audit-secrets-sprint3.json`.
  - 264 rules total this sprint, 0 findings — same rule sets sprint-1/sprint-2 already ran.
- **shellcheck** (`run.sh`, this session — not run in sprint-1/sprint-2 since no `.sh` file existed yet):
  2 INFO-level `SC1091` notices only (`Not following: ./.hermes/.env was not specified as input` /
  same for `.openclaw/.env`) — expected and benign: both are best-effort-sourced per-instance env files
  that genuinely may not exist at lint time, exactly mirroring `self/spawn/run.sh`'s own identical
  sourcing convention. **Zero warnings, zero errors.**
- **Manual grep sweep** of both new files:
  ```
  fs.*                         -> 1 hit  (wake-gate.mjs:40, fs.readFileSync only, read-only registry parse)
  fetch(                        -> 0 hits (wake-gate.mjs never calls fetch directly -- routed through the
                                   already-hardened, reused usdcBalance primitive, not this file's own
                                   surface)
  eval(/exec(/child_process     -> 0 hits (no command-injection surface; run.sh's own `exec "$NODE" ...`
                                   is a fixed, hardcoded argv, never string-interpolated from external input)
  process.env                   -> 2 hits, both `runWakeGate`'s own `env = process.env` default parameter
                                   and the CLI entrypoint's real invocation -- `env` itself is never read
                                   inside runWakeGate's own body (confirmed: `env` is accepted for the
                                   test-injection seam's own symmetry with self/spawn's convention, unused
                                   internally)
  ANICCA_ARGS                   -> 0 hits (confirms PROP-117d's own no-decision-lever discipline)
  Date.now()                    -> 1 hit, the `nowMs` default parameter only (line 97), never re-read
                                   elsewhere in the file
  writeFile/appendFile/unlink    -> 0 hits (wake-gate.mjs performs no direct file mutation of its own --
                                   every ledger append happens inside the reused, already-hardened
                                   executeLoanIssuanceAttempt/executeDefaultDetectionSweep)
  ```

### `registry.json` diff

Reviewed via `git show ccef6ee480add1f7e3d670fab53a12fbfb07339e -- skills/registry.json`: the entire diff
is one new slot object (`economy/lending`), inserted immediately before the pre-existing `cook` entry,
zero other slot touched, zero secrets/credentials/private keys in any field (`track`/`dir`/`entrypoint`/
`status`/`spec`/`summary`/`owner`/`risk`/`riskNote` only — all plain descriptive strings).

### Findings

**No HIGH/CRITICAL/MEDIUM findings.** No new LOW-severity observations this sprint — the two carry-forward
design notes above (`gojo-read.mjs`'s per-line `JSON.parse`, `lending-verify.mjs`'s unpinned `rpcUrl`) are
unaffected by this sprint's own 2 files, since neither `run.sh` nor `scripts/wake-gate.mjs` touches either
surface.

### Summary

Zero exploitable vulnerabilities found in `run.sh`, `scripts/wake-gate.mjs`, and the `registry.json` diff,
across Semgrep (264 rules, 0 findings), shellcheck (0 warnings/errors), and manual review. Combined with
sprint-1's/sprint-2's own already-clean files, all 7 files this feature has delivered across 3 sprints are
Semgrep-clean and manually reviewed clean.
