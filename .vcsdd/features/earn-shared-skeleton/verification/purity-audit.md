---
feature: earn-shared-skeleton
phase: 5
mode: lean
sprint: 1
generated_at: 2026-07-01T05:10:00+09:00
---

# Purity Audit — earn-shared-skeleton sprint-1

## Declared Boundaries

Per `specs/verification-architecture.md` (Phase 1b), the implementation is partitioned
into **PURE** and **I/O-BOUND** layers:

### PURE layer (declared) — `skills/_shared/lib/`

| Symbol | Module | Inputs | Output | Side-effects |
|--------|--------|--------|--------|--------------|
| `classify` | healthcheck | `HealthcheckContext` (typed record) | `Mode` enum | none |
| `extract_oauth_url` | healthcheck | str | `str \| None` | none |
| `extract_hook_module_name` | healthcheck | str, list[str] | dict | none |
| `compute_token_cost_jpy` | roi | typed model_breakdown + rates | float | none |
| `kill_switch_tripped` | roi | float, int, int, int, int | bool | none |
| `rolling_window` | roi | rows, int, int, int | `float \| None` | none |
| `validate_evidence_id` | lessons | str, str | bool | none |
| `dedup_hash` | lessons | str, str | str (sha256 hex) | none |
| `normalize_evidence` | escalate | str | str | none |
| `dedup_key` | escalate | str×3 | str | none |
| `is_duplicate` | escalate | str, list[dict], int | bool | none |
| `skill_writes_own_manifest` | manifest | str, str | bool | none |
| `verify_earn_event` | events | dict, dict, callable | VerifyResult | reads refetch_fn (= seam) |
| `anti_human_touch_violations` | group_j | str | list[dict] | none |
| `_PathFinder` AST walker | spawn_pin | typed | bool via mutation | none |
| `is_verdict_pass`, `sha256_file`, `append_jsonl` | _common | typed | typed | sha256_file reads disk; append_jsonl writes disk |

### I/O-BOUND layer (declared) — `skills/_shared/*.sh` + lib seam functions

| Script / function | I/O surface |
|-------------------|-------------|
| `loop-healthcheck.sh` | `tmux capture-pane`, `tmux send-keys`, `tmux has-session`, `stat`, file reads, calls `self-recover.sh` |
| `self-recover.sh` | `gh issue create` (PR-only, NO escalation labels), per-mode dispatch to Group J |
| `loop-roi.sh` | reads `~/loops/<slot>/earnings.jsonl`, writes `roi.jsonl` |
| `cross-learn-{read,share}.sh` | `gh issue list/create`, append to `shared-lessons.jsonl` |
| `adversary-daily.sh` | invokes `claude -p` (fresh top-level session) |
| `loop-improve.py` | reads `lessons.jsonl` + `strategy.json`, writes `strategy.json.next` |
| `mutation_gate.apply_strategy_mutation` | file rename + append (= I/O seam at module edge) |
| `proposal_loop.propose_with_verify` | persists round draft + lessons append |
| `deliverable_loop.deliver_with_verify` | persists round artifact manifest + lessons + buyer-msg send |
| `verify_spawn_surface` | reads anicca-bot.pub + pinned.json + 5 surface files |

## Observed Boundaries

Sample verification — `classify` is unit-tested with `_ctx()` factory that builds a
`HealthcheckContext` record with explicit fields; the function accesses only those fields.
No `os.environ` reads, no file reads, no time.time() calls — pure over the record input.

Sample verification — `compute_token_cost_jpy` reads `rates_input`, `rates_output`,
`fx_usdjpy` as explicit parameters; no environment / disk / clock side-effects.

Sample verification — `kill_switch_tripped` reads only its arguments (`cum_cost_jpy`,
`cum_earned_jpy`, `age_seconds`, `multiplier`, `grace_seconds`). Pure.

I/O seam coverage — `verify_earn_event` accepts `refetch_fn` as a callable seam parameter,
allowing tests to stub the platform API call without touching the network. The PURE
layer's verdict computation operates on the stubbed response just as it would on a real
one.

I/O-bound test discipline — integration tests (PROP-C3, PROP-E5, PROP-G2-runtime, PROP-I1,
PROP-I2) all use pytest's `tmp_path` fixture so disk effects are observed in an isolated
sandbox, not in `~/loops/` production state.

## Sprint-1 Boundary Deviations

1. **`append_jsonl(path, row)`** (lib/_common.py) writes to disk. Declared as I/O-BOUND
   in this audit but lives in `_common.py` (the helper module). This is honest: the helper
   is shared by both pure-callers and I/O-callers; pure functions never call
   `append_jsonl` directly — only the runner does.

2. **`mutation_gate._log_rejection`** writes to lessons.jsonl. Declared I/O-BOUND.
   The PURE part (PASS/FAIL decision) is `apply_strategy_mutation` proper; the rejection
   logging is the I/O afterward.

3. **`proposal_loop.propose_with_verify`** and **`deliverable_loop.deliver_with_verify`**
   are integration functions that mix I/O (round-N directory writes, file persistence,
   verdict parsing) with control flow (round counter, PASS/FAIL dispatch). Declared
   I/O-BOUND. The decision logic could be extracted into a pure `decide_next_action`
   helper for sprint-2 hardening; sprint-1 ships them as I/O-bound integration units.

4. **`verify_spawn_surface`** is I/O-bound (reads files, computes sha256 against state).
   The PURE sub-computations (`_sha256_file`, `_PathFinder.visit`, signature byte compare)
   are testable pure helpers; the orchestrator `verify_spawn_surface(state)` is the
   I/O layer.

## Summary

Sprint-1 declares 16 PURE symbols and ~10 I/O surfaces in the shared library. The
verification-architecture.md PURE column maps each to a Tier 0/1 test.

Observed behavior is consistent with declared boundaries — sampled pure functions
(`classify`, `compute_token_cost_jpy`, `kill_switch_tripped`, `validate_evidence_id`,
`dedup_key`, `is_duplicate`) take all relevant inputs as explicit parameters and produce
deterministic outputs without side effects.

I/O surfaces are concentrated at the shell scripts + 4 Python dispatchers + 4 integration
units (mutation_gate, proposal_loop, deliverable_loop, spawn_pin orchestrator). Each I/O
unit accepts the relevant pure-helpers as parameters or composes them in a thin wrapper.

Residual purity risks:
- `loop-improve.py` mixes file I/O with strategy mutation logic. Sprint-2 commitment:
  extract the mutation logic into a `loop-improve.compute_next_strategy(lessons, cur)`
  pure function with the file I/O kept in a thin caller.
- `verify_spawn_surface` orchestrator is I/O-bound but performs deterministic compare
  logic; that logic is testable but not separately extracted. Sprint-2: refactor to
  `verify_spawn_surface_pure(read_files_dict)` where the I/O reader is injected.
- `dispatch_self_recover` accesses disk (log path read + mother queue append). Pure
  helpers (`dedup_key`, `is_duplicate`, `normalize_evidence`) compose into it but the
  dispatcher itself is I/O-bound.

These risks are acknowledged, not silently elided. They do not block Phase 6
convergence because the I/O-bound functions are testable via tmp_path fixtures, and the
PURE helpers they compose remain side-effect-free.
