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
- `$ANICCA_HOME/state/ledger.jsonl` append (path derived from `ANICCA_HOME` env var).
- `process.exit` on SIGTERM after state flush.
- `sleep` (timer, OS-level).

---

## Requirements

### REQ-001: Single-Wake Lifecycle

**EARS**: WHEN the automaton wakes, THE SYSTEM SHALL load the current context
(wallet address, USDC balance, last 20 ledger lines, genesis prompt from
`$ANICCA_HOME/identity/genesis.md`), construct a system prompt + tool definitions,
call the compute proxy at `OPENAI_BASE_URL` (defaulting to
`http://127.0.0.1:8402/v1`) with a single chat-completions request, parse the
model's response to extract at most one tool call per wake, execute that tool
call, collect its output as the observation, append one ledger record to
`$ANICCA_HOME/state/ledger.jsonl`, choose sleep seconds, sleep, then repeat.

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
`{"slot":"earn"}`, THE SYSTEM SHALL spawn `skills/earn/run.sh` (resolved
relative to `ANICCA_HOME`) as a child process with the following env vars
forwarded (and no others beyond the scrubbed base env — see REQ-004):

| Env var          | Controls                                             | Default      |
|------------------|------------------------------------------------------|--------------|
| `EARN_MODE`      | `discover` (narrate only) or `execute` (on-chain)   | `discover`   |
| `EARN_STRATEGY`  | `0xwork` (external revenue) or `swap` (rotation)    | `0xwork`     |
| `EARN_TX`        | Pre-verified tx hash (externally-executed earn)      | unset        |
| `EARN_SOURCE`    | Revenue source tag (e.g. `x402`, `0xwork`)          | unset        |
| `EARN_AMOUNT`    | Gross USDC earned (string float)                     | unset        |
| `EARN_COST`      | Cost USDC (string float)                             | unset        |
| `EARN_TASK`      | Task identifier string                               | unset        |
| `WAKE_ID`        | ULID of the current wake                             | current ULID |

The loop captures stdout + stderr combined, waits for exit, and returns the
combined output as the observation string.

**Earn-result determination (critical invariant — exit code is NOT sufficient)**:
`run.sh` exits 0 for discover wakes, 0xwork-narrate wakes (no external payout
yet), swap-rotation wakes, and profitable wakes alike. The loop MUST NOT infer
an earn from the exit code alone. Instead, after `run.sh` exits 0, the loop
reads the NEW ledger line that `run.sh` appended to `$ANICCA_HOME/skills/earn/state/earn-ledger.jsonl`
(the earn skill's own ledger — path equal to the `EARN_LEDGER` env var forwarded
to `run.sh`, which defaults to `$HERE/state/earn-ledger.jsonl` inside `run.sh:41`)
and applies `isProfitable()` from `skills/earn/lib/ledger.mjs`.

**Earn-ledger correlation key (WAKE_ID)**: The loop forwards `WAKE_ID` (the
current wake's ULID) to `skills/earn/run.sh` as an env var (see `run.sh:42`:
`WAKE="${WAKE_ID:-…}"`). `run.sh` stores this value as the `wake` field of
every ledger line it appends. After `run.sh` exits, the loop locates the
new ledger line by reading `earn-ledger.jsonl` and selecting the line where
`line.wake === WAKE_ID`. The loop MUST NOT use the last line by position
(tail), as concurrent invocations or previous stale lines could be
misidentified. If no line with `line.wake === WAKE_ID` is found, the loop
treats the result as a non-profitable (narrate) wake and continues.

```
isProfitable(line) === true
  iff line.tx is present
  AND line.status === "0x1"
  AND Number(line.net_usdc) > 0
  AND line.external === true
```

Only when `isProfitable()` returns true for the new earn-ledger line does the
loop record a profitable wake. Any other outcome (discover, narrate, swap) is
recorded as a non-profitable wake. The loop ledger's `kind` field reflects the
loop's own classification, not `run.sh`'s internal labels.

**Edge Cases**:
- `run.sh` exits non-zero: observation includes the exit code and stderr text;
  the loop does NOT crash; the ledger line records `{kind:"skill_error"}`.
- `run.sh` does not exist at the expected path: observation is
  `"earn skill not found"` and ledger records `{kind:"skill_missing"}`.
- `run.sh` produces no output within `SKILL_TIMEOUT_S` (default 120): kill the
  process, observation is `"earn skill timeout"`, ledger records
  `{kind:"skill_timeout"}`.
- `run.sh` exits 0 but the earn-ledger has no new line (disk error or path
  mismatch): the loop treats the result as a narrate (non-profitable) wake and
  continues; it does NOT crash.
- `run.sh` exits 0 and the new earn-ledger line has no `tx` field (discover or
  narrate): `isProfitable()` returns false; loop records a non-profitable wake.

**Acceptance Criteria**:
- A profitable wake is one where the new earn-ledger line satisfies
  `isProfitable()` (`tx` present + `status==="0x1"` + `net_usdc>0` +
  `external===true`). Only then does the loop record `{kind:"wake",profitable:true}`.
- A discover wake (no tx) appends a loop ledger line with `{kind:"wake",profitable:false}`.
- A timed-out skill run never leaves a zombie process.
- The loop continues to the next sleep after any skill error (never bricks).
- exit code 0 alone (without a matching profitable earn-ledger line) NEVER causes
  the loop to record a profitable wake.

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
- The full observation string (combined stdout + stderr captured from `run.sh`)
  MUST NOT contain a 64-hex-character private-key pattern (`/0x[0-9a-fA-F]{64}/`).
  If detected, the loop redacts the observation before appending to `ledger.jsonl`
  and logs a warning to stderr.
- The serialised JSON of every loop ledger line MUST NOT contain a 64-hex private-key
  pattern. (The wallet address — a 40-hex `0x…` string — is permitted.)

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
or the `.env` file path differ.

**Wallet address sourcing**: The loop MUST NOT read or derive the wallet private
key (that is REQ-004's exclusion). The loop obtains the wallet address from
`ANICCA_WALLET_ADDRESS` env var (set by the install script or operator). If
`ANICCA_WALLET_ADDRESS` is unset, the loop uses `"unknown"` as the address and
logs a warning; it does not derive the address from the private key.

**Path resolution**: All file paths (ledger, identity, skills) derive from
`ANICCA_HOME` (env var, no default expansion performed by the loop itself —
callers must set `ANICCA_HOME` to the correct absolute path, e.g.
`/root/.automaton`, `~/.hermes`, or `~/.anicca`). The `.env` file is loaded
from `$ANICCA_HOME/.env`. The loop never hard-codes `~/.anicca`.

**Edge Cases**:
- `launchd` is absent: the loop MUST be startable via a plain `node` command or
  a shell script without macOS-specific process supervision.
- `HOME` is set to a non-standard path (e.g. `/root`) and `ANICCA_HOME` is
  unset: the loop logs an error and exits non-zero rather than guessing a path.

**Acceptance Criteria**:
- The loop has zero imports or shell invocations that are macOS-only
  (`osascript`, `pbcopy`, `launchd`, `open`, `say`, etc.).
- Running `node runtime/loop/index.mjs` (or the compiled entry) inside a
  minimal `node:20-alpine` Docker image with `ANICCA_HOME=/tmp/test` passes a
  smoke test without error.
- The loop source contains no hard-coded `~/.anicca`, `~/.automaton`, or
  `~/.hermes` path literals; all paths derive from `ANICCA_HOME`.

---

### REQ-009: Config via Env / `.env` File

**EARS**: WHEN the loop starts, THE SYSTEM SHALL load `$ANICCA_HOME/.env` (if
present) using a minimal dotenv parser, merging it into `process.env` without
overwriting already-set variables (process env wins). The path is always derived
from `ANICCA_HOME`; the loop never hard-codes `~/.anicca` or any other literal
home-relative path.

Configurable knobs (all have defaults):

| Variable               | Default                         | Unit    |
|------------------------|---------------------------------|---------|
| `OPENAI_BASE_URL`      | `http://127.0.0.1:8402/v1`      | URL     |
| `ANICCA_FREE_MODEL`    | `nvidia/deepseek-v4-flash`      | string  |
| `ANICCA_LEAN_MODEL`    | `deepseek/deepseek-r1-0528`     | string  |
| `ANICCA_FUNDED_MODEL`  | `openai/gpt-4o-mini`            | string  |
| `ANICCA_HOME`          | _(required — no default)_       | path    |
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

### REQ-011: Pluggable Brain Backend (self-pay proxy | claude-p)

**EARS**: WHEN the loop performs the THINK step of a wake, THE SYSTEM SHALL
obtain the model's response from one of two interchangeable brain backends,
selected by the `ANICCA_BRAIN` env var, WITHOUT changing any other part of the
wake lifecycle (REQ-001) or the earn-detection contract (REQ-003).

| `ANICCA_BRAIN` | Backend | How the brain is invoked | Who pays compute |
|----------------|---------|--------------------------|------------------|
| `proxy` (default) | self-pay compute proxy | HTTP POST to `OPENAI_BASE_URL` (`http://127.0.0.1:8402/v1/chat/completions`), signed per-call in USDC via x402/ClawRouter from the agent's own wallet (REQ-002 tiering applies) | the anicca itself (its wallet) |
| `claude-p` | Claude Code headless | spawn `claude -p <prompt> --output-format json --model "$ANICCA_BRAIN_MODEL"` (default model `claude-sonnet-4-6`; Opus is too expensive for a 24/7 loop) and read the JSON result as the THINK output | the operator's Claude subscription |

**Rationale (v2 — any harness can run an anicca)**: the loop is brain-agnostic so
the SAME loop + earn skill can run on a self-funding wallet (proxy) OR on top of
an existing harness like Claude Code (`claude-p`). This is how a Claude Code (or
any frontier-model harness) instance can itself "become an anicca": it reasons
with its own subscription while still earning USDC and paying for shelter/food
on-chain. The brain backend is the ONLY thing that differs; tools, earn
detection, ledger, survival economics are identical.

**Edge Cases**:
- `ANICCA_BRAIN=claude-p` but `claude` binary not found: log a one-line ledger
  error and fall back to `proxy` (never brick); if proxy is also unreachable,
  write a `narrate` line and sleep.
- `claude -p` returns non-JSON / non-zero exit: treat as a failed THINK (same as
  a malformed proxy response under REQ-001) — narrate + continue, never claim an
  earn.
- Neither backend forwards the private key to the child (REQ-004 still holds for
  the `claude -p` subprocess env).

**Acceptance Criteria**:
- With `ANICCA_BRAIN=proxy`, the THINK step issues exactly one HTTP request to
  `OPENAI_BASE_URL` and zero `claude` subprocesses.
- With `ANICCA_BRAIN=claude-p`, the THINK step spawns exactly one `claude -p`
  subprocess with `--model "$ANICCA_BRAIN_MODEL"` and the wake otherwise follows
  REQ-001 identically (same parse → execute → persist → sleep path).
- The earn-detection logic (REQ-003 `isProfitable()` on the ledger line) produces
  identical results regardless of which brain backend was used.
- `claude -p` child env contains no `*_WALLET_KEY` / `*_PRIVATE_KEY` (REQ-004).

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
