# Behavioral Spec: reality-verifier (AGENTIC verification layer)

Scope: TODO #5 of `docs/loop-engineering/27-ideal-earn-record-verify-architecture.md`.
Design source of truth: `docs/loop-engineering/24-shared-ground-truth-verifier-design.md` (v3, 2026-07-11).

## Purpose (non-negotiable framing)

Verification of "did we earn" is split into two layers that MUST NOT be merged:

- **DETERMINISTIC layer** (already implemented, out of scope here, NOT touched by this
  feature): on-chain tx status / wallet balance delta / `external:true`. This is the sole
  authority on "did money move". No LLM judgment is involved.
- **AGENTIC layer** (this feature): a fresh-context subagent that checks whether a loop's
  **report/log is honest** relative to ledger + on-chain ground truth — i.e. it detects lies,
  fake-green, mislabeled internal transfers, mock/narrate-only claims, and unhealthy strategy
  patterns. It never itself declares "money moved"; it only judges honesty and reality of the
  claim.

## Requirements

### REQ-001: Subagent definition exists and is spawnable
**EARS**: WHEN a caller (self-heal harness, weekly build pass, or an interactive VCSDD/main
session) needs an agentic honesty check THE SYSTEM SHALL provide a Claude Code subagent
definition at `.claude/agents/reality-verifier.md` with valid YAML frontmatter (`name`,
`description`, `tools`, `model`) that Claude Code's Task tool can spawn as a new instance.
**Edge Cases**:
- Missing/invalid YAML frontmatter: agent cannot be spawned — treated as a build failure.
- `tools` list omitted: MUST default-deny (explicit allow-list required, never implicit
  full access).
**Acceptance Criteria**:
- File exists at the exact path above.
- Frontmatter contains `name: reality-verifier`.
- Frontmatter `tools` is present and is a strict array (validated by REQ-002).

### REQ-002: Tool grant is read-only / evidence-gathering only
**EARS**: WHEN the reality-verifier subagent is spawned THE SYSTEM SHALL grant it exactly
`Read`, `Grep`, `Glob`, `Bash` and SHALL NOT grant `Write` or `Edit`, so it can gather
evidence (files, ledgers, on-chain state via CLI/RPC, browser via CLI) but cannot mutate
loop source, ledgers, or state — and structurally cannot "fix" what it is reviewing.
**Edge Cases**:
- A future on-chain MCP tool is connected (e.g. `mcp__*_Base_MCP__get_transaction_history`):
  additive, read-only, allowed; MUST NOT include any signing/send-transaction capable tool.
- Bash is granted despite being generically mutable: the prompt (REQ-007) constrains its use
  to read-only invocations; this is a prompt-level control layered on top of the tool grant,
  not a substitute for it.
**Acceptance Criteria**:
- Frontmatter `tools` array is exactly `["Read", "Grep", "Glob", "Bash"]` (order-independent,
  no additions of `Write`/`Edit`).

### REQ-003: Role boundary vs the DETERMINISTIC layer is explicit
**EARS**: WHEN reality-verifier issues a verdict THE SYSTEM SHALL NOT itself declare "money
moved" / "earned" as a fact it determined; it SHALL treat on-chain tx status, wallet balance
delta, and ledger `external:true` rows as ground truth it reads and cites, and SHALL instead
judge whether the loop's report/log is an honest reflection of that ground truth.
**Edge Cases**:
- Report says "EARNING $X" but ledger/on-chain shows $0 or an internal transfer only →
  FAIL, category `report_ledger_mismatch` or `internal_transfer_mislabeled`.
- Report is silent about a real on-chain external inbound tx that DID occur → under-claiming
  is not dishonesty; MUST NOT be flagged as a FAIL on its own (verdict may still be PASS).
- Ledger/on-chain data itself is unreachable (RPC down, file missing) → verdict MUST be FAIL
  with category `verification_incomplete` (fail-closed, never silently PASS on missing
  ground truth).
**Acceptance Criteria**:
- The subagent's system prompt contains an explicit statement of this boundary (see REQ-VER
  in verification-architecture.md for the literal string check).
- Verdict schema (REQ-006) carries a `role` field fixed to `"agentic-honesty-check"` so
  downstream consumers cannot confuse it with the DETERMINISTIC gate's output.

### REQ-004: Fresh-context / no self-evaluation
**EARS**: WHEN reality-verifier is invoked THE SYSTEM SHALL run with zero conversational
context from the loop/session being verified (a new Task-tool subagent instance, or a newly
spawned `claude` process with no prior history) and SHALL gather evidence itself via tool
calls rather than trusting any report text pasted into its prompt.
**Edge Cases**:
- Caller is the SAME loop/session being verified (self-eval): explicitly forbidden by this
  spec; the spawn wrapper (REQ-008) MUST always launch a distinct process/instance.
- Caller pastes a "report" string as part of the task: reality-verifier MUST NOT accept it as
  fact — it must re-derive the same conclusion independently from ledger/on-chain/logs before
  agreeing with it.
**Acceptance Criteria**:
- System prompt contains an explicit "do not trust the input report; verify independently"
  instruction (checked by REQ-VER string match).
- The spawn wrapper (REQ-008) never re-uses an existing session/context.

### REQ-005: Detection catalog
**EARS**: WHEN given a loop name and a claim/report/artifact path THE SYSTEM SHALL check for
each of the following failure modes and, when found, emit a finding tagged with the matching
category:
- `report_ledger_mismatch` — report claims an outcome the ledger does not contain.
- `report_onchain_mismatch` — report/ledger claims an outcome on-chain state contradicts.
- `internal_transfer_mislabeled` — a wallet-to-wallet transfer between the colony's own
  addresses (e.g. seed/bootstrap capital) is labeled as external earning.
- `mock_marker_in_success_path` — a "success"/"PASS"/"EARNING" claim is backed by code or
  logs containing `mock`/`dry`/`fake`/`simulated`/`TODO: real impl` on the path that produced
  the claim.
- `narrate_only_claim` — the report describes an action (posted, traded, sent) with no
  corresponding tool-call evidence, log line, or on-chain/API artifact.
- `unhealthy_strategy` — repeated identical losing actions, spend with no corresponding
  receipt/position, or other patterns indicating the loop is not actually pursuing its stated
  strategy.
**Edge Cases**:
- Multiple categories apply to the same underlying fact: SHALL emit one finding per category
  (no forced merging) each with distinct evidence.
- None of the categories apply and evidence was actually gathered: PASS is allowed (see
  REQ-006 for the "vague PASS" prohibition).
**Acceptance Criteria**:
- Each category above is a literal member of `FINDING_CATEGORIES` in
  `skills/self/lib/reality-verdict-schema.mjs`.
- The subagent prompt enumerates all six categories verbatim.

### REQ-006: Verdict output format (binary, evidence-cited, anti-vague-PASS)
**EARS**: WHEN reality-verifier completes its checks THE SYSTEM SHALL write a single
structured verdict object with `role`, `overallVerdict` (`PASS`|`FAIL` only, no partial
credit), `findings[]` (each with `category` from REQ-005's catalog, `severity`, and
`evidence` citing a concrete `filePath`+`lineRange`, or `txHash`, or `domExcerpt`), and — when
`overallVerdict` is `PASS` with zero findings — `evidenceReviewed[]` describing what was
actually checked and where, so a PASS can never be a content-free positive summary.
**Edge Cases**:
- `overallVerdict: "FAIL"` with `findings: []` → INVALID (a FAIL must always cite at least
  one finding).
- `overallVerdict: "PASS"` with `findings: []` and no `evidenceReviewed` → INVALID ("vague
  PASS", explicitly disallowed, mirrors `vcsdd-adversary`'s anti-leniency rule).
- A finding whose `category` is not in the REQ-005 catalog → INVALID.
- A finding whose `evidence` has none of `filePath`, `txHash`, `domExcerpt` → INVALID
  (hallucinated/uncited findings are a process failure).
**Acceptance Criteria**:
- `validateVerdictShape()` in `skills/self/lib/reality-verdict-schema.mjs` rejects every
  invalid shape above and accepts every valid shape.

### REQ-007: Money-safety — read-only, no wallet mutation
**EARS**: WHEN reality-verifier runs THE SYSTEM SHALL NOT execute any wallet-mutating action
(transfer, trade, sign transaction, spend, faucet claim) and SHALL restrict on-chain access to
read-only operations (balance reads, transaction-history reads, receipt/status reads).
**Edge Cases**:
- A connected MCP tool exposes both read and write RPC methods (e.g. a generic
  `chain_rpc_request`): the prompt MUST enumerate an explicit read-only allow-list
  (`eth_getBalance`, `eth_getTransactionByHash`, `eth_getTransactionReceipt`,
  `eth_blockNumber`, `get_transaction_history`, and Solana/HL read equivalents) and forbid
  any `sendTransaction`/`signTransaction`/`eth_sendRawTransaction`-class call.
**Acceptance Criteria**:
- System prompt contains an explicit read-only RPC allow-list and an explicit prohibition of
  signing/sending.
- No file this feature adds imports or calls a signing/keypair/private-key library.

### REQ-008: Spawn wiring — one documented invocation point
**EARS**: WHEN a self-heal harness or weekly build pass needs an agentic honesty check for
loop X THE SYSTEM SHALL expose exactly one script, `skills/self/reality-verify-spawn.sh`,
that (a) derives a deterministic result-file path from `<loop-name>` + a timestamp via a pure
helper, (b) spawns a fresh, detached `claude` process (same spawn pattern as
`skills/self/self-fix.sh`: new tmux session, no prior context, `--dangerously-skip-permissions`
so it can run non-interactively) whose task prompt instructs it to act as reality-verifier
against the given loop/report/artifact, and (c) never modifies the target loop's own
ledger/state files itself (it only reads them and its own result file).
**Edge Cases**:
- Verifier process crashes, times out, or never writes a verdict: the caller MUST treat a
  missing/malformed result file as FAIL-safe (never silently treated as PASS).
- Concurrent verify calls for different loops: result files MUST be isolated per
  `<loop-name>+<timestamp>` (no shared/overwritable path).
- Called with `REALITY_VERIFY_DRYRUN=1`: MUST print the derived loop name + result path and
  exit 0 without spawning any process (mirrors `SELF_FIX_DRYRUN=1` in `self-fix.sh`), so the
  path-derivation logic is testable without spawning `claude`.
**Acceptance Criteria**:
- `skills/self/reality-verify-spawn.sh` exists, is executable, accepts
  `<loop-name> <artifact-or-report-path> [claim-text]`.
- `REALITY_VERIFY_DRYRUN=1` seam produces deterministic, script-testable output.
- This feature does NOT edit `skills/self/self-fix.sh`, any cron file, or any
  ledger/earn-detect file — wiring self-fix/healthcheck to call this script is left to the
  parent to do after own-eyes review.

## Purity Boundary Analysis

- **Pure core** (deterministic, no I/O, unit-testable):
  - `buildResultPath(stateDir, loopName, timestampMs)` — string derivation only.
  - `normalizeLoopName(loopName)` — string normalization (mirrors `self-fix.sh`'s `-loop`
    suffix rule).
  - `validateVerdictShape(verdict)` — pure structural/semantic validation of a verdict object
    against REQ-005/REQ-006 (no file/network access).
  - `isKnownCategory(category)` — pure lookup against `FINDING_CATEGORIES`.
- **Effectful shell** (I/O, non-deterministic, NOT unit-tested for outcome, only for the
  seams that are pure):
  - The LLM judgment itself (reality-verifier's actual reasoning) — inherently
    non-deterministic; verified only by structural/content checks on the prompt file
    (REQ-001/002/003/004/005/007) and by manual own-eyes runs, not by unit tests.
  - `reality-verify-spawn.sh`'s tmux/`claude` process spawn — effectful; only its pure
    path-derivation seam (`REALITY_VERIFY_DRYRUN=1`) is tested.
  - File reads of ledgers/reports, RPC calls, browser CLI calls performed BY the spawned
    reality-verifier instance at runtime — effectful, outside this feature's automated test
    boundary (this feature ships the definition + spawn wrapper, not a mock of Claude Code's
    Task-tool runtime).

## Edge Case Catalog (cross-cutting)

- Empty/missing loop name argument to the spawn script → non-zero exit, no process spawned.
- Empty/missing artifact-or-report-path argument → non-zero exit, no process spawned.
- Loop name already ends in `-loop` vs not → both normalize to the same `<name>-loop` form
  (parity with `self-fix.sh` REQ, avoids split state across two spellings).
- Verdict JSON with extra/unknown top-level fields → tolerated (forward-compatible), only the
  required fields are validated strictly.
- Verdict JSON with `findings` containing duplicate `category`+`evidence.filePath`+
  `evidence.lineRange` → tolerated by the schema (dedup is a caller/UX concern, not a shape
  validity concern).

## Non-Functional Requirements

- **No new runtime dependency**: `reality-verdict-schema.mjs` uses only Node.js builtins (no
  new npm package).
- **Money-safety**: this feature performs zero on-chain writes, zero wallet key handling,
  zero `Write`/`Edit` grants to the spawned subagent (REQ-002, REQ-007).
- **No overlap with parallel work**: this feature MUST NOT modify any file under
  `skills/earn/**/earn-detect.mjs`, any ledger file, or any file already touched by the
  parallel `ledger-reconcile`/`gig-reality-verify` worktrees. All files this feature adds are
  new files (`.claude/agents/reality-verifier.md`,
  `skills/self/lib/reality-verdict-schema.mjs`, `skills/self/reality-verify-spawn.sh`, and
  their test files).

## Operational Note (2026-07-12)

This is a highly concurrent shared repo (many parallel builder worktrees under
`.worktrees/`). The first attempt at this worktree was garbage-collected by a concurrent
process while uncommitted (branch `feature/reality-verifier` and its worktree both vanished
mid-session). This spec was rewritten identically in a fresh worktree; from this point on
every phase is committed immediately to reduce the uncommitted-state window.
