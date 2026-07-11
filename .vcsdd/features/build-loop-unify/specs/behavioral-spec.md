# Behavioral Spec — build-loop-unify (TODO #4)

## Scope note (read first)

This feature is assigned as "1本化 of mainloop(6h) + founder-loop(30min) build cadences"
per `docs/loop-engineering/27-ideal-earn-record-verify-architecture.md` line 45/91/114.
**Before writing any requirement, the actual code was read** (per this repo's honesty rule:
"symbol/function/importの存在は使う前に確認する"). The code contradicts the doc's premise.
That finding is REQ-000 below and it governs every other requirement in this spec.

## Requirements

### REQ-000: Corrected finding — there is only ONE `claude` BUILD-loop cron, not two
**EARS**: WHEN an engineer reads `skills/self/founder-loop/founder-loop.sh` and its
launchd job `ai.anicca.founder-loop-cadence` THE SYSTEM SHALL be found to invoke **zero**
`claude` CLI calls — it is a purely deterministic recorder (`node record-earn.mjs`) plus a
CEO capital-allocation pass (`bash ceo/ceo-pass.sh` → `python3 ceo/run_pass.py`, a bandit
allocator — pure Python, no LLM subprocess anywhere in its call chain).

**Evidence (fresh-context, this session, 2026-07-12)**:
- `grep -n "claude" skills/self/founder-loop/founder-loop.sh` → 0 matches.
- `grep -rn "claude" skills/self/founder-loop/ceo/*.py` → 1 match, and it is a code
  *comment* citing `~/.claude/rules/building-effective-ai-agents.md`, not an invocation.
- `find / -iname "founder-loop-prompt*"` → 0 results anywhere on disk. The doc's claim
  "2つのprompt.txt" (line 45/114 implies a `founder-loop-prompt.txt` twin of
  `claude-p-mainloop-prompt.txt`) does not exist and never has, per `git log --all` scope
  of this session.
- `grep -rl "claude --model\|claude -p \|claude --dangerously-skip-permissions"
  skills/self/` (repo-wide) → exactly one file pair: `claude-p-mainloop.sh` +
  `claude-p-mainloop-prompt.txt`.
- Live launchd (`launchctl list | grep anicca`) confirms `ai.anicca.claude-p-mainloop` and
  `ai.anicca.founder-loop-cadence` are both loaded and firing, but only the former's
  ProgramArguments chain ever reaches a `claude` binary.

**Edge Cases**:
- If a future commit adds a `claude` call inside `founder-loop.sh` or its `ceo/` chain,
  that changes REQ-000's premise and this spec must be re-run through phase 1a before any
  merge is attempted (do not silently merge based on stale assumptions).
**Acceptance Criteria**:
- The evidence commands above are reproducible verbatim in this worktree and return the
  stated results (verified in Verification Architecture, PROP-000).

### REQ-001: Do not merge a deterministic ledger-writer into the LLM build loop
**EARS**: WHEN considering whether to fold `founder-loop.sh` into `claude-p-mainloop.sh`'s
cron THE SYSTEM SHALL refuse the merge, because `founder-loop.sh` is the sole writer path
to the founder earn-ledger (`node record-earn.mjs`, INV-H2 in that script: "ONLY
record-earn writes the ledger") and runs every 30 min specifically so wallet reconciliation
stays fresh (architecture doc §2: "毎 wake wallet on-chain 残高 → reconcile"). Co-scheduling
it inside a `claude --model sonnet` subprocess with up to a 3600s timeout would (a) slow
ledger reconciliation from 30min→6h cadence, contradicting the doc's own money-truth
requirement, and (b) violate the doc's own 鉄則 at line 80 ("DETERMINISTIC/AGENTIC を混同
しない") by making a financial-record-of-truth path depend on a non-deterministic LLM call
succeeding.
**Edge Cases**:
- A future proposal to speed up `claude-p-mainloop` by having it *read* founder-loop's
  STATE.md/ledger (observe-only, no write) is fine and already happens today (mainloop
  prompt step 1 runs `colony-status.sh`, which reads ledgers) — that is not the same as
  merging the write-path cron.
**Acceptance Criteria**:
- No change in this feature touches `record-earn.mjs`, `ceo/*.py`, or the ledger write
  path. (Verified by `git diff` scope check in Verification Architecture.)

### REQ-002: The single existing BUILD-loop cron already satisfies "launchd job = 1"
**EARS**: WHEN counting launchd jobs whose ProgramArguments chain invokes `claude`
THE SYSTEM SHALL find exactly one (`ai.anicca.claude-p-mainloop`), fulfilling the outcome
"build loop が1本" without any cron consolidation being required.
**Edge Cases**: none — this is a count, not a behavior.
**Acceptance Criteria**:
- `grep -rl "claude --model\|claude -p \|claude --dangerously" skills/self/*.sh
  skills/self/**/*.sh` returns exactly one script (`claude-p-mainloop.sh`) and one prompt
  (`claude-p-mainloop-prompt.txt`).

### REQ-003: Purify the BUILD loop's role to LOOP B (harness architect, never an earner)
**EARS**: WHEN `claude-p-mainloop.sh` fires THE SYSTEM SHALL run a prompt that explicitly
states: (a) its role is the large brain (LOOP B) whose only job is to make the small-brain
EARN loops able to earn — by fixing skills/harnesses — and it must never perform or
simulate an earn action itself; (b) the truth of "did the colony earn" is the on-chain
wallet balance / ledger reconciliation, never this loop's own narrated report.
**Edge Cases**:
- The existing prompt (`claude-p-mainloop-prompt.txt`) already contains a
  harness-not-cook framing ("You do NOT run their economy for them") and an
  evidence-over-opinion clause ("Judge good/done by the adversary + evidence, NEVER your
  own opinion") — REQ-003 must not duplicate these, only make the "never earn / wallet is
  truth" boundary explicit where it is currently implicit.
**Acceptance Criteria**:
- Updated prompt file contains an explicit sentence forbidding the build loop from
  recording/simulating an earn action, and an explicit sentence naming on-chain
  wallet/ledger reconciliation as the only source of earn-truth (not this loop's own
  report).

### REQ-004: Preserve existing safety design (pidfile / kill-switch / prompt-in-own-file)
**EARS**: WHEN `claude-p-mainloop.sh` is modified for REQ-005 (model selection) THE SYSTEM
SHALL preserve the existing pidfile single-instance guard, the `~/.anicca/claude-p-loop.pause`
kill-switch checked first, and the pattern of loading the prompt from a separate file via
`"$(cat "$PROMPT_FILE")"` (never inlined, to avoid the backtick/command-substitution
footgun already documented in the script's own header comment).
**Edge Cases**:
- None of these mechanisms may be weakened (e.g. no removing the kill-switch check, no
  inlining the prompt text into a double-quoted string).
**Acceptance Criteria**:
- `diff` of the modified script against the original shows only the model-selection lines
  added (REQ-005); no lines are removed from the pidfile guard, kill-switch check, prompt
  file existence check, or `trap cleanup EXIT`.

### REQ-005: Model division — sonnet default, opus for heavy design runs
**EARS**: WHEN `claude-p-mainloop.sh` launches the build-loop process THE SYSTEM SHALL
invoke `claude --model sonnet` by default, but SHALL allow an operator to override the
model via an environment variable (`CLAUDE_P_MAINLOOP_MODEL`) so a heavy-design run can be
kicked off with `opus` (per the project model-division table:
"深い推論（本当に必要な時のみ）: Opus") **without editing the script or the launchd plist**.
**Edge Cases**:
- `CLAUDE_P_MAINLOOP_MODEL` unset or empty → falls back to `sonnet` (current default
  behavior unchanged; no launchd plist edit needed, no regression for the live cron).
- `CLAUDE_P_MAINLOOP_MODEL` set to an unsupported string → passed through as-is to `claude
  --model`; `claude` itself will reject an invalid model name (no extra validation layer
  invented here — that would be an unrequested abstraction).
**Acceptance Criteria**:
- Running the script with `CLAUDE_P_MAINLOOP_MODEL` unset launches `claude --model sonnet`
  (byte-identical to current production behavior).
- Running the script with `CLAUDE_P_MAINLOOP_MODEL=opus` launches `claude --model opus`.

### REQ-006: Test-isolation seam (required to test REQ-005 safely on a LIVE system)
**EARS**: WHEN a test invokes `claude-p-mainloop.sh` THE SYSTEM SHALL allow the pidfile
directory, log directory, kill-switch pause file, and working directory to be redirected to
a temp directory via `CLAUDE_P_MAINLOOP_TEST=1` + `CLAUDE_P_MAINLOOP_STATE_DIR` /
`CLAUDE_P_MAINLOOP_LOG_DIR` / `CLAUDE_P_MAINLOOP_PAUSE_FILE` / `CLAUDE_P_MAINLOOP_WORKDIR`,
mirroring the already-established `FOUNDER_TEST`/`FOUNDER_DIR` pattern in
`founder-loop.sh` (read-only reference, not touched). This is required because the script
otherwise hardcodes `$HOME/.openclaw/state/claude-p-mainloop.pid` — the **exact same
pidfile the live launchd cron uses** — so testing without this seam would risk colliding
with the currently-running production loop (forbidden by this task's safety constraint:
"実 launchd 操作禁止" / do not interfere with the live job).
**Edge Cases**:
- `CLAUDE_P_MAINLOOP_TEST` unset (production/launchd invocation) → every path resolves
  exactly as before this feature (byte-identical default paths).
- `CLAUDE_P_MAINLOOP_TEST=1` but the corresponding `_DIR`/`_FILE` var is unset → falls back
  to the production path for that one value (mirrors founder-loop's own fallback rule) —
  a test author must set the dir vars they care about isolating.
**Acceptance Criteria**:
- With no env vars set, `grep`-diffing the script's resolved default paths against the
  pre-feature script shows no change.
- With `CLAUDE_P_MAINLOOP_TEST=1` and all four dir/file vars pointed at a `mktemp -d`, a
  full run of the script touches zero files outside that temp dir (verified by `find
  $HOME/.openclaw/state -newer <test-start-marker>` showing no new pidfile from the test
  run).

## Purity Boundary Analysis

- **Pure/deterministic core** (untouched by this feature): `founder-loop.sh`,
  `record-earn.mjs`, `ceo/ceo-pass.sh`, `ceo/run_pass.py` — the money-truth RECORD/CEO
  layer. REQ-001 forbids this feature from touching or scheduling alongside them.
- **Effectful shell** (this feature's actual surface): `claude-p-mainloop.sh` (spawns a
  `claude` subprocess, writes logs, manages a pidfile) and `claude-p-mainloop-prompt.txt`
  (pure text, no execution, but shapes the LLM's effectful actions once it runs).

## Non-functional requirements
- No launchd job is created, edited, unloaded, or removed by this feature (constraint from
  the assigning task: "実 launchd 操作禁止"). `SWITCHOVER.md` documents commands but does
  not execute them.
- Default behavior of `claude-p-mainloop.sh` (model=sonnet, cadence, timeout=3600s) must be
  byte-for-byte unchanged when `CLAUDE_P_MAINLOOP_MODEL` is unset, so the live cron (which
  this worktree does not touch) sees zero behavior change if this diff is ever merged as-is.
