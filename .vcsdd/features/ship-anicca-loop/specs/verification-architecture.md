# Verification Architecture — ship-anicca-loop

**Feature**: `ship-anicca-loop`
**Phase**: 1b
**VCSDD Epic**: `VCSDD-ship-anicca-loop-1781765291339`

---

## Purity Boundary Map

### Pure Core — deterministic, no side effects, formally verifiable

| Module (planned path)                  | Role                                                              | REQ coverage          |
|----------------------------------------|-------------------------------------------------------------------|-----------------------|
| `runtime/loop/context.mjs`             | Assembles wake context (wallet addr, balance, ledger tail, genesis prompt) into a message payload. No I/O. | REQ-001               |
| `runtime/loop/prompt.mjs`              | Constructs system-prompt string from identity + skill manifest. Pure string transform. | REQ-001               |
| `runtime/loop/tier.mjs`               | `selectTier(balanceUsdc) → {tier, model}`. Pure arithmetic on a float. | REQ-002               |
| `runtime/loop/parse-tool-call.mjs`     | `parseToolCall(rawResponse) → {slot, args} | null`. Pure JSON/object parse + validation. | REQ-001, REQ-003      |
| `runtime/loop/ledger-record.mjs`       | `formatRecord(fields) → string`. Pure: JSON.stringify + newline. | REQ-007               |
| `runtime/loop/loop-detect.mjs`         | `isLooping(recentActions, window) → boolean`. Pure array comparison. | REQ-005               |
| `runtime/loop/env-filter.mjs`          | `scrubPrivateKeys(env) → filteredEnv`. Pure: object transform, no I/O. | REQ-004               |
| `runtime/loop/config.mjs`              | `loadConfig(processEnv, dotenvText) → Config`. Pure: parse + merge, returns record. | REQ-009               |

### Effectful Shell — I/O, network, process

| Module (planned path)                  | Effects                                                           | REQ coverage          |
|----------------------------------------|-------------------------------------------------------------------|-----------------------|
| `runtime/loop/index.mjs`               | Entry point: event loop, signal handlers, wires all modules.      | REQ-001, REQ-006      |
| `runtime/loop/inference.mjs`           | HTTP POST to `OPENAI_BASE_URL/v1/chat/completions`.               | REQ-001, REQ-002      |
| `runtime/loop/balance.mjs`             | Base RPC call for USDC balance, with TTL cache.                   | REQ-002               |
| `runtime/loop/skill-runner.mjs`        | `child_process.spawn` with timeout + env scrub.                   | REQ-003, REQ-004      |
| `runtime/loop/ledger.mjs`              | `fs.appendFile` (O_APPEND) to `ledger.jsonl`.                     | REQ-007               |
| `runtime/loop/dotenv.mjs`              | `fs.readFile` of `~/.anicca/.env`, feeds pure `loadConfig`.       | REQ-009               |

---

## Proof Obligations

| ID        | Description                                                                                          | Tier | Required | Tool           | REQ Link |
|-----------|------------------------------------------------------------------------------------------------------|------|----------|----------------|----------|
| PROP-001  | `selectTier(0) === "broke"` and model equals `ANICCA_FREE_MODEL`                                     | 1    | true     | node:test      | REQ-002  |
| PROP-002  | `selectTier(0.5) === "lean"` and model equals `ANICCA_LEAN_MODEL`                                   | 1    | true     | node:test      | REQ-002  |
| PROP-003  | `selectTier(5.0) === "funded"` and model equals `ANICCA_FUNDED_MODEL`                               | 1    | true     | node:test      | REQ-002  |
| PROP-004  | `selectTier(NaN)` and `selectTier(Infinity)` both return `"broke"`                                  | 1    | true     | node:test      | REQ-002  |
| PROP-005  | `scrubPrivateKeys(env)` removes every key matching `.*_WALLET_KEY|.*_PRIVATE_KEY|.*_PRIV_KEY`        | 1    | true     | node:test      | REQ-004  |
| PROP-006  | `scrubPrivateKeys(env)` is idempotent: calling it twice returns the same object                     | 1    | true     | node:test      | REQ-004  |
| PROP-007  | `formatRecord(fields)` always produces valid JSON that round-trips through `JSON.parse`              | 1    | true     | node:test      | REQ-007  |
| PROP-008  | `isLooping(actions, 3)` returns true iff the last 3 entries are identical (same slot + args)        | 1    | true     | node:test      | REQ-005  |
| PROP-009  | `isLooping(actions, 3)` returns false when the window has fewer than 3 entries                      | 1    | true     | node:test      | REQ-005  |
| PROP-010  | `parseToolCall` returns null for any response that is not a well-formed tool-call object             | 1    | true     | node:test      | REQ-001  |
| PROP-011  | `loadConfig` gives environment variables precedence over `.env` file values                         | 1    | true     | node:test      | REQ-009  |
| PROP-012  | `loadConfig` skips malformed `.env` lines without throwing                                          | 1    | true     | node:test      | REQ-009  |
| PROP-013  | After SIGTERM, `ledger.jsonl` ends with a line where `kind === "shutdown"`                          | 2    | true     | node:test (integration) | REQ-006 |
| PROP-014  | After 10 consecutive wakes (mocked proxy), `ledger.jsonl` has exactly 10 lines                     | 2    | true     | node:test (integration) | REQ-007  |
| PROP-015  | A skill that exits non-zero does not crash the loop; next wake is attempted                         | 2    | true     | node:test (integration) | REQ-003  |
| PROP-016  | After LOOP_DETECT_WINDOW identical actions, the inference HTTP call is NOT made                     | 2    | true     | node:test (integration) | REQ-005  |
| PROP-017  | No import / shell invocation in `runtime/loop/` references macOS-only commands                      | 0    | true     | grep audit     | REQ-008  |
| PROP-018  | `scrubPrivateKeys` never allows `BLOCKRUN_WALLET_KEY` through regardless of env shape               | 1    | true     | node:test      | REQ-004  |

---

## Verification Strategy

### Tier 0 — Static audit (no test runner)

- `PROP-017`: `grep -rE 'osascript|pbcopy|launchd|open |say '` over `runtime/loop/` must return empty.
  Rationale: macOS exclusion is a structural property detectable by source scan.

### Tier 1 — Property tests with `node:test` (pure-core functions only)

All `PROP-001` through `PROP-012` and `PROP-018`.

These are purely functional transforms with no I/O. Each test file imports the pure module, passes
inputs, and asserts outputs. No mocks, no fixtures, no network. Fast (< 50 ms per test).

Test file locations (to be written in Phase 2a):
```
runtime/loop/__tests__/tier.test.mjs
runtime/loop/__tests__/env-filter.test.mjs
runtime/loop/__tests__/ledger-record.test.mjs
runtime/loop/__tests__/loop-detect.test.mjs
runtime/loop/__tests__/parse-tool-call.test.mjs
runtime/loop/__tests__/config.test.mjs
```

### Tier 2 — Integration tests with `node:test` + mock HTTP

`PROP-013` through `PROP-016`.

These tests spin up the full `index.mjs` entry point in a child process with:
- `OPENAI_BASE_URL` pointing to an in-process mock HTTP server (no network).
- `ANICCA_HOME` pointing to a temp directory.
- `SLEEP_BASE_S=0` (no real sleep between wakes).

Each integration test runs for N wakes, then sends SIGTERM (or inspects
`ledger.jsonl`) and asserts the structural post-conditions.

Test file location:
```
runtime/loop/__tests__/integration.test.mjs
```

### Tier 3 — NOT required for this feature

The pure-core functions (Tier 1) are simple enough that property-based testing
via `node:test` with hand-crafted boundary cases fully covers the invariants.
Formal model checking (TLA+, Kani) is out of scope for this sprint.

---

## Coverage Mapping (REQ → PROP)

| REQ       | PROP obligations                                  |
|-----------|---------------------------------------------------|
| REQ-001   | PROP-010, PROP-014                                |
| REQ-002   | PROP-001, PROP-002, PROP-003, PROP-004            |
| REQ-003   | PROP-015                                          |
| REQ-004   | PROP-005, PROP-006, PROP-018                      |
| REQ-005   | PROP-008, PROP-009, PROP-016                      |
| REQ-006   | PROP-013                                          |
| REQ-007   | PROP-007, PROP-014                                |
| REQ-008   | PROP-017                                          |
| REQ-009   | PROP-011, PROP-012                                |
| REQ-010   | Covered by Phase 2 smoke-test (not a unit prop)   |

---

## Risk Notes

1. **Balance RPC flakiness** (REQ-002, PROP-004): the production Base RPC may timeout during
   integration tests. Integration tests MUST mock the balance call via an env override
   (`ANICCA_BALANCE_OVERRIDE`) so tests are not network-dependent.

2. **Ledger append atomicity** (REQ-007, PROP-014): on Linux `O_APPEND` is atomic for writes
   < PIPE_BUF (4096 bytes). Ledger records are well under this limit. No additional locking needed.

3. **SIGTERM timing** (REQ-006, PROP-013): integration tests that assert on SIGTERM must
   give the process at least 500 ms after the signal before reading `ledger.jsonl`.

4. **Loop detect false positive** (REQ-005): if `LOOP_DETECT_WINDOW=0`, the guard must be
   disabled (treated as "never detect"). The config loader must clamp to minimum 1.
