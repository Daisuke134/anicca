# Verification Architecture — franklin-ledger-push (P2)

## Purity Boundary Map

- **Pure Core** (`runtime/loop/ledger-publish.mjs`, exported, no I/O):
  - `decidePublish({ pendingLineCount, lastPushTs, nowMs, minLines, minIntervalMs })` — throttle
    decision, deterministic truth table.
  - `extractWakeId(line)` — JSON parse + field extraction, deterministic, never throws (malformed →
    `'unknown'`).
  - Reused: `redactPrivateKeyPatterns` (`env-filter.mjs`, unmodified, already formally covered by its
    own PROP-018/PROP-020).
- **Effectful Shell** (`runtime/loop/ledger-publish.mjs`, same file, I/O functions):
  - `readMarker`/`writeMarker` — fs read/write of `$ANICCA_HOME/state/.ledger-publish-marker`.
  - `readSourceLinesRaw`/`appendRawLines` — fs read of source `ledger.jsonl`, fs append to
    `state/franklin-ledger/<instance>.jsonl`.
  - `defaultGit` — `child_process.execFileSync` wrapper (injectable via `opts.git`, mirrors
    `evolve.mjs:154-156`'s own `git()` helper).
  - `publishLedgerCycle` — orchestrator; sequences fs + git calls per REQ-701..707; the only exported
    function actually wired into `index.mjs`.
  - Wiring: `index.mjs`'s `while (!shuttingDown) { await runOneWake(); ... }` loop — one call per
    completed wake, wrapped in an additional try/catch at the call site (defense-in-depth on top of
    `publishLedgerCycle`'s own internal non-throwing contract).

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-701 | `decidePublish`: `pendingLineCount<=0` → never push, any `nowMs`/`lastPushTs` | 1 | true | node:test (boundary-value example-based — no fast-check dep in this package; matches existing repo convention across `__tests__/`) |
| PROP-702 | `decidePublish`: `pendingLineCount>=minLines(10)` → always push regardless of elapsed time | 1 | true | node:test |
| PROP-703 | `decidePublish`: `pendingLineCount>0` and `nowMs-lastPushTs>=minIntervalMs(15min)` → push | 1 | true | node:test |
| PROP-704 | `decidePublish`: `0<pendingLineCount<10` and elapsed`<15min` → never push (`throttled`) | 1 | true | node:test |
| PROP-705 | `extractWakeId`: valid JSON with string `wake_id` → returns it verbatim; missing/malformed/non-JSON → `'unknown'`, never throws | 0 | true | node:test |
| PROP-706 | Redaction pass-through: a line containing `0x[0-9a-fA-F]{64}` written to the destination file has it replaced by `[REDACTED]`; a 40-hex address is untouched | 1 | true | node:test (real fs, tmp dir) |
| PROP-707 | Default-OFF: `enabled` resolves `false` for unset/empty/any non-`"1"` env value AND for `opts.enabled` explicitly `false`; zero fs/git calls occur | 0 | true | node:test |
| PROP-708 | Non-fatal git failure: `publishLedgerCycle` never throws/rejects when the injected `git` mock throws at EACH of the 4 call sites independently (`fetch`, `merge`, `commit`, `push`) — 4 separate cases | 1 | true | node:test (mock `git` callback, mirrors "mock git wrapper" per task spec) |
| PROP-709 | Idempotent cursor advance: after a first cycle whose injected `git` throws on `commit`, a second cycle's destination-file content contains every source line exactly once (no duplicates) | 1 | true | node:test (real fs tmp dir + mock git) |
| PROP-710 | Path-scoped commit idiom: the recorded `git` call sequence for a successful append+commit cycle is EXACTLY `['fetch',...]`, `['merge','--ff-only',...]`, `['add','--',destPath]`, `['-c','user.name=...','-c','user.email=...','commit','-m',<msg>,'--',destPath]` — never `git add -A`/`git commit -a` | 1 | true | node:test (mock `git` call-log assertion) |

## Verification Strategy

- **Tier 0**: pure parsing/gating with no meaningful edge-case surface beyond input-domain enumeration
  (`extractWakeId`, default-OFF flag resolution) — direct example-based `node:test` assertions are
  sufficient and match this codebase's existing convention (no formal-methods tooling — Kani/Hypothesis
  — is present anywhere in `runtime/loop/`).
- **Tier 1**: the throttle decision (`decidePublish`) and the effectful orchestrator's non-fatality/
  idempotency contracts get exhaustive boundary-value `node:test` coverage (every `>=`/`<` edge named
  in behavioral-spec.md REQ-704/707 gets its own test case) plus injected-failure-mode coverage (a
  mock `git` function that throws at each of the 4 call sites in turn, one test per site) — this is
  the repo's established substitute for property-based testing in this package (no `fast-check`/
  `hypothesis` dependency declared in `runtime/loop/package.json`; introducing one is out of scope for
  a LEAN feature and would itself need its own spec justification).
- **Tier 2/3**: not applicable — no cryptographic, numeric-precision, or safety-critical money-moving
  logic in this feature (it copies already-written, already-redacted evidence; it never signs a
  transaction or moves funds). `evolve.mjs`'s own `promote()` (a genuinely money-adjacent auto-commit)
  sets the repo precedent that real-git-in-tmp-dir + `node:test` is the accepted verification depth for
  this class of effectful git-wrapping code — this feature follows the same precedent, using an
  injectable mock `git` additionally so tests never touch a real network/remote.
