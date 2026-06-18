# Behavioral Specification — ship-anicca-loop

**Feature**: `ship-anicca-loop`
**Phase**: 1a
**VCSDD Epic**: `VCSDD-ship-anicca-loop-1781765291339`
**Status**: Under Review

---

## Overview

Ship a self-contained ReAct automaton loop (`runtime/loop/`) that closes the
gap declared in README.md — "this repository does not ship the automaton loop."
When installed via `install.sh` and started via `start-local.sh`, the loop
boots without human intervention, calls the self-pay compute proxy
(OpenAI-compatible, `127.0.0.1:8402/v1`), executes skill slots (earn first),
persists every wake to an append-only ledger, and repeats indefinitely on a
self-chosen sleep schedule calibrated to wallet balance.

### Purity Boundary Analysis

**Pure Core** (deterministic, side-effect-free, formally verifiable):
- Wake context assembly: wallet address + balance + recent ledger lines +
  genesis prompt assembled into a message payload.
- System prompt construction from identity file + skill manifest.
- Tool call parsing from a raw model response string.
- Sleep-seconds calculation from wallet balance and survival tier.
- Loop-detect: comparing the current action tuple to the last N action tuples.
- Ledger record formatting (JSON serialisation of a wake record).

**Effectful Shell** (I/O, network, process):
- HTTP call to the compute proxy (`/v1/chat/completions`).
- Subprocess execution of `skills/earn/run.sh` (and any other skill entrypoint).
- Wallet USDC balance read (Base RPC or cached value).
- `~/.anicca/state/ledger.jsonl` append.
- `process.exit` on SIGTERM after state flush.
- `sleep` (timer, OS-level).

---

## Requirements

### REQ-001: Single-Wake Lifecycle

**EARS**: WHEN the automaton wakes, THE SYSTEM SHALL load the current context
(wallet address, USDC balance, last 20 ledger lines, genesis prompt from
`~/.anicca/identity/genesis.md`), construct a system prompt + tool definitions,
call the compute proxy at `OPENAI_BASE_URL` (defaulting to
`http://127.0.0.1:8402/v1`) with a single chat-completions request, parse the
model's response to extract at most one tool call per wake, execute that tool
call, collect its output as the observation, append one ledger record to
`~/.anicca/state/ledger.jsonl`, choose sleep seconds, sleep, then repeat.

**Edge Cases**:
- Proxy not yet up at wake time: retry the HTTP call up to 3 times with 2 s
  back-off; if all retries fail, write a `{kind:"wake_error",error:"proxy_down"}`
  ledger line and sleep `SLEEP_ERROR_S` (default 60) before retrying.
- Model returns no tool call (text-only response): write a `{kind:"narrate"}`
  ledger line and sleep the standard interval.
- `OPENAI_BASE_URL` is unset: default to `http://127.0.0.1:8402/v1`.
- `ledger.jsonl` parent dir does not exist: create it on first write.

**Acceptance Criteria**:
- After one wake, exactly one line is appended to `ledger.jsonl`.
- The ledger line contains `ts`, `wake_id` (ULID), `kind`, `sleep_s` fields.
- A failed proxy call does NOT leave an empty/partial ledger line.

---

### REQ-002: Survival-Tier Model Selection

**EARS**: WHEN the loop assembles a wake, THE SYSTEM SHALL determine the current
survival tier from the wallet USDC balance and pass the appropriate model name in
the chat-completions request body.

Tier table (amounts in USDC, thresholds configurable via env):

| Tier       | Balance condition           | Model env / default                          |
|------------|-----------------------------|----------------------------------------------|
| `broke`    | balance == 0                | `ANICCA_FREE_MODEL` / `nvidia/deepseek-v4-flash` |
| `lean`     | 0 < balance ≤ 1.00          | `ANICCA_LEAN_MODEL` / `deepseek/deepseek-r1-0528` |
| `funded`   | balance > 1.00              | `ANICCA_FUNDED_MODEL` / `openai/gpt-4o-mini` |

**Edge Cases**:
- Balance read fails (RPC timeout): remain on previous tier and log a warning
  in the ledger; do NOT crash.
- Balance is a non-finite number (NaN, Infinity from a malformed RPC response):
  treat as `broke`.

**Acceptance Criteria**:
- Given a mocked balance of 0, the request body contains `ANICCA_FREE_MODEL`.
- Given a mocked balance of 0.5, the request body contains `ANICCA_LEAN_MODEL`.
- Given a mocked balance of 5.0, the request body contains `ANICCA_FUNDED_MODEL`.
- A balance-read error does NOT change the model from its previously chosen value.

---

### REQ-003: Tool Execution — Earn Skill

**EARS**: WHEN the model's tool call is `run_skill` with argument
`{"slot":"earn"}`, THE SYSTEM SHALL spawn `~/.anicca/skills/earn/run.sh` as a
child process with the earn env vars forwarded, capture stdout + stderr
(combined), wait for exit, and return the combined output as the observation
string.

**Edge Cases**:
- `run.sh` exits non-zero: observation includes the exit code and stderr text;
  the loop does NOT crash; the ledger line records `{kind:"skill_error"}`.
- `run.sh` does not exist at the expected path: observation is
  `"earn skill not found"` and ledger records `{kind:"skill_missing"}`.
- `run.sh` produces no output within `SKILL_TIMEOUT_S` (default 120): kill the
  process, observation is `"earn skill timeout"`, ledger records
  `{kind:"skill_timeout"}`.
- The earn skill itself is in discover mode (exits 0, prints discover line):
  observation is the stdout text; ledger records `{kind:"wake", action:"earn_discover"}`.

**Acceptance Criteria**:
- A successful earn wake appends a ledger line with `kind:"wake"` and `action:"earn_execute"`.
- A timed-out skill run never leaves a zombie process.
- The loop continues to the next sleep after any skill error (never bricks).

---

### REQ-004: Private-Key Isolation

**EARS**: WHEN the loop spawns a skill subprocess, THE SYSTEM SHALL NEVER pass
the wallet private key (the value of `BLOCKRUN_WALLET_KEY` or any variable
matching `.*_WALLET_KEY|.*_PRIVATE_KEY|.*_PRIV_KEY`) in the child process
environment.

**Edge Cases**:
- The variable is present in the parent `process.env`: it MUST be deleted from
  the env snapshot passed to `child_process.spawn`.
- A skill entrypoint sources `/opt/anicca.env` independently (acceptable — that
  is the skill's own business; the loop just must not forward the key).

**Acceptance Criteria**:
- Unit test: given `process.env.BLOCKRUN_WALLET_KEY = "0xdeadbeef"`, the
  env object passed to `spawn` does NOT contain `BLOCKRUN_WALLET_KEY`.
- The ledger never contains the string `"0x"` followed by 64 hex characters in
  the `wallet_key` field (the wallet ADDRESS is fine; the private key is not).

---

### REQ-005: Loop Detect and Idle Guard

**EARS**: WHEN the last `LOOP_DETECT_WINDOW` (default 3) consecutive tool calls
are identical (same `slot` and same arguments), THE SYSTEM SHALL skip calling
the model, write a `{kind:"loop_detect"}` ledger line, sleep
`SLEEP_LOOP_DETECT_S` (default 300), and resume.

**Edge Cases**:
- Window of 1 (configured `LOOP_DETECT_WINDOW=1`): detect immediately on the
  first repeated call.
- Ledger window does not yet contain `LOOP_DETECT_WINDOW` entries: no
  detection.

**Acceptance Criteria**:
- After 3 identical consecutive `run_skill earn` actions, the loop writes one
  `{kind:"loop_detect"}` record and sleeps `SLEEP_LOOP_DETECT_S` seconds before
  continuing.
- The inference call (HTTP to the proxy) is NOT made during a loop-detect sleep.

---

### REQ-006: Graceful Shutdown on SIGTERM

**EARS**: WHEN the process receives SIGTERM, THE SYSTEM SHALL finish the current
tool execution if one is in-flight (or discard if blocked for > 5 s), flush the
current ledger line with `{kind:"shutdown"}`, and exit with code 0.

**Edge Cases**:
- SIGTERM arrives while sleeping: immediate exit after flush.
- SIGTERM arrives while awaiting the model (HTTP in-flight): abort the HTTP
  request, write `{kind:"shutdown",note:"in_inference"}`, exit 0.
- SIGTERM arrives while a skill subprocess is running: send SIGTERM to the child
  first, wait up to 5 s, then exit.

**Acceptance Criteria**:
- A `{kind:"shutdown"}` line is always the last line in `ledger.jsonl` after a
  SIGTERM.
- Exit code is 0.
- No orphan child processes remain after shutdown.

---

### REQ-007: Ledger Immutability

**EARS**: WHEN the loop appends to `ledger.jsonl`, THE SYSTEM SHALL only ever
append (O_APPEND mode or equivalent); it SHALL NOT rewrite or truncate existing
lines.

**Edge Cases**:
- Disk full on append: log to stderr, sleep `SLEEP_ERROR_S`, retry next wake
  (do not crash).
- `ledger.jsonl` does not exist yet: create it on first append.

**Acceptance Criteria**:
- After 10 wakes, `ledger.jsonl` contains exactly 10 lines (one per wake).
- Randomly killing and restarting the loop does not corrupt or truncate existing
  ledger lines.

---

### REQ-008: Cloud Portability (No Mac-Only Assumptions)

**EARS**: WHEN the loop is started on a Linux host (e.g. Akash, Docker), THE
SYSTEM SHALL operate identically to macOS with zero code changes — only env vars
or `~/.anicca/.env` differ.

**Edge Cases**:
- `launchd` is absent: the loop MUST be startable via a plain `node` command or
  a shell script without macOS-specific process supervision.
- `HOME` is set to a non-standard path (e.g. `/root`): wallet and ledger paths
  derive from `process.env.HOME || os.homedir()`.

**Acceptance Criteria**:
- The loop has zero imports or shell invocations that are macOS-only
  (`osascript`, `pbcopy`, `launchd`, `open`, `say`, etc.).
- Running `node runtime/loop/index.mjs` (or the compiled entry) inside a
  minimal `node:20-alpine` Docker image passes a smoke test without error.

---

### REQ-009: Config via Env / `.env` File

**EARS**: WHEN the loop starts, THE SYSTEM SHALL load `~/.anicca/.env` (if
present) using a minimal dotenv parser, merging it into `process.env` without
overwriting already-set variables (process env wins).

Configurable knobs (all have defaults):

| Variable               | Default                         | Unit    |
|------------------------|---------------------------------|---------|
| `OPENAI_BASE_URL`      | `http://127.0.0.1:8402/v1`      | URL     |
| `ANICCA_FREE_MODEL`    | `nvidia/deepseek-v4-flash`      | string  |
| `ANICCA_LEAN_MODEL`    | `deepseek/deepseek-r1-0528`     | string  |
| `ANICCA_FUNDED_MODEL`  | `openai/gpt-4o-mini`            | string  |
| `ANICCA_HOME`          | `~/.anicca`                     | path    |
| `SLEEP_BASE_S`         | `120`                           | seconds |
| `SLEEP_ERROR_S`        | `60`                            | seconds |
| `SLEEP_LOOP_DETECT_S`  | `300`                           | seconds |
| `SKILL_TIMEOUT_S`      | `120`                           | seconds |
| `LOOP_DETECT_WINDOW`   | `3`                             | integer |
| `BALANCE_CACHE_TTL_S`  | `300`                           | seconds |
| `LEAN_TIER_THRESHOLD`  | `1.00`                          | USDC    |

**Edge Cases**:
- `.env` file contains syntax errors: skip the malformed line, continue loading.
- A variable is set in `.env` AND in the environment: environment wins (never
  overwrite).

**Acceptance Criteria**:
- Setting `SLEEP_BASE_S=5` in `.env` makes the loop sleep 5 s between wakes
  (verifiable in unit test with a mocked timer).
- `.env` with a syntax-error line does not crash the loop.

---

### REQ-010: Start-local Integration

**EARS**: WHEN `start-local.sh` is invoked with the argument
`runtime/loop/index.mjs`, THE SYSTEM SHALL start the compute proxy (REQ-001
prerequisite) and then exec the loop as the main process, passing
`OPENAI_BASE_URL` in environment so the loop routes inference through the
self-pay proxy.

**Edge Cases**:
- Proxy fails to start within 10 s: `start-local.sh` exits non-zero before
  exec-ing the loop.

**Acceptance Criteria**:
- `./start-local.sh node runtime/loop/index.mjs` runs end-to-end: proxy up,
  loop boots, first ledger line written within 60 s on a machine with network
  access to BlockRun.

---

## Non-Functional Requirements

| ID    | Category    | Requirement                                                                       |
|-------|-------------|-----------------------------------------------------------------------------------|
| NFR-1 | Performance | Each wake's overhead (excluding inference latency and skill runtime) ≤ 200 ms.    |
| NFR-2 | Footprint   | Loop process idle memory ≤ 64 MB RSS (no GPU; no heavy ML runtime loaded).        |
| NFR-3 | Security    | Private key NEVER logged to stdout/stderr or written to `ledger.jsonl`.           |
| NFR-4 | Portability | Zero macOS-specific syscalls or built-in commands (REQ-008).                      |
| NFR-5 | Durability  | After a crash+restart, the loop resumes from the ledger tail without re-executing the previous wake's skill. |

---

## Out of Scope (Downstream Dependencies)

- **README rewrite** noting the loop is now shipped (separate task).
- **Akash SDL / cloud deployment descriptor** (separate task).
- **`self/spawn` skill implementation** — the loop provides the hook for it
  (`run_skill spawn`) but does not implement spawn itself.
- **Telegram / LINE / WhatsApp report channels** — `skills/report/anicca-report.sh`
  is an existing slot; the loop calls it but does not change it.
