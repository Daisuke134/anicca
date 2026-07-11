# self-heal-allslots — Changelog (lean VCSDD, P3)

## Phase 1a/1b — Spec
See `specs/behavioral-spec.md` (REQ-AS-001..006) and `specs/verification-architecture.md`.

## Phase 2a — RED
Added `skills/self/tests/test_earning_health_allslots.sh` BEFORE `earning-health-allslots.sh`
existed. Confirmed failing:
```
new-feature-tests: FAIL (9/13 checks failed — script not found, rc=127)
regression-baseline: PASS (test_earning_health.py 9/9, test_sol_trade_healthcheck.sh 9/9)
```

## Phase 2b — GREEN
Added:
- `skills/self/earning-health-registry.json` — 8 slot entries (`earn/sol-trade`,
  `earn/polymarket-trade` instrumented; `economy/gig`, `hl_trade`, `x402_sell`, `token_launch`,
  `earn/clip`, `earn/video` documented gaps with `gapNote`).
- `skills/self/earning-health-allslots.sh` — registry-driven generalization of
  `sol-trade-healthcheck.sh`, reusing `earning-health.py::is_fresh_but_barren` unmodified.
- `skills/self/tests/test_earning_health_allslots.sh` — 13 checks.
- `skills/self/launchd/ai.anicca.earning-health-allslots.plist` — ONE launchd job (300s interval),
  `plutil -lint` OK, **not copied to `~/Library/LaunchAgents/` and not `launchctl load`ed**.

Verified GREEN:
```
target-feature-tests: PASS (test_earning_health_allslots.sh 13/13)
regression-baseline: PASS (test_earning_health.py 9/9, test_sol_trade_healthcheck.sh 9/9)
```
Smoke-tested the REAL registry (isolated tmpdir, empty synthetic trace files — never touched live
`~/.blockrun`/`~/.openclaw` state): correctly logs `OK` for the two instrumented slots and
`NOT-INSTRUMENTED <id> -- <gapNote>` for all six documented-gap slots, zero `self-fix.sh` calls.

## Why only 2 of 8 slots are `instrumented:true` this sprint

Investigated every required slot's actual telemetry (read `skills/earn/*/run.sh`,
`skills/earn/gig/*.sh`, `skills/earn/video/*.py`, `skills/earn/clip/*.sh`,
`skills/_shared/lib/ledger.mjs`):

- **`earn/sol-trade`, `earn/polymarket-trade`**: both write a per-wake mechanism-failure trace line
  (`sol-trade.trace.jsonl` / `pm-trade.trace.jsonl` under `skills/earn/state/`) and both are wired
  into the registry this sprint. **Correction (iter1 adversary review, FIND-001)**: the original
  claim here — "both already write the EXACT contract `is_fresh_but_barren` needs" — was factually
  inaccurate. sol-trade's vocabulary is a clean `skip`/`live-pass` pair; pm-trade has a genuine
  THIRD state, `action:"error"` (AGENT_HOME missing / `pick.py` non-zero exit), that the original
  `action == "skip"`-only predicate could never see. See "self-heal iter1 fixes FIND-001..006"
  below for the fix (the pure predicate now also recognizes a sustained `error` run as unhealthy).
- **`hl_trade`, `x402_sell`, `token_launch`**: all three are branches of ONE shared dispatcher,
  `skills/earn/run.sh`, writing to ONE shared `skills/earn/state/earn-ledger.jsonl` keyed by a
  free-text `task` field (e.g. `"hl-cooldown — holding..."`, `"x402 server up..."`,
  `"token-observe"`) — not a stable `{action,reason}` pair. Reusing `is_fresh_but_barren` here would
  require either (a) per-strategy string-matching to decide which `task` values mean "mechanism
  rejected" vs "agent legitimately chose WAIT/hold" — brittle, and arguably the kind of hardcoded
  judgment `rules/building-effective-ai-agents.md` forbids — or (b) treating literally-zero-gain
  narrate lines as barren, which would misfire on `x402_sell`'s and `token_launch`'s *expected*
  steady state (a passive server with no buyer yet / a model that hasn't decided to launch a token
  is healthy, not broken). Correctly closing this gap needs a small, deliberate instrumentation
  change to `run.sh`'s own strategy branches (tag genuine mechanism-rejection paths — e.g.
  `hl-fund-skipped` — with a real `action:"skip"` field) done as its own reviewed change, not
  bundled into this generalization sprint.
- **`economy/gig`, `earn/clip`, `earn/video`**: each already has its OWN process-alive +
  heartbeat-STALE healthcheck (`gig-healthcheck.sh`, `clip-healthcheck.sh`,
  `video-healthcheck.sh`) tuned to that loop's own tmux-core architecture, plus an activity-outcome
  ledger (`earnings.jsonl`, clip's payout-check, `earn-video-ledger.jsonl`) rather than a per-wake
  decision trace. These are a different (already-covered) failure class from the "alive but
  mechanically rejecting every wake" blind spot `earning-health.py` was built to close; extending
  barren-detection to them is future work, not a regression risk today.

This is the honest, non-fabricating scope for this sprint: real coverage doubled (1 → 2
instrumented slots) behind a DRY, registry-driven, extensible mechanism that iterates and reports
on ALL 8 required slots every run — the 6 not-yet-instrumented ones are explicit, logged,
`self-fix`-inert gaps, never silently skipped and never given a fabricated verdict.

## Franklin-scoping / graduation gap (REQ-AS-006)

**Detection side (this sprint's code) IS Franklin-scoped**: `earning-health-allslots.sh` resolves
its registry + trace directory relative to its OWN script location (mirrors
`sol-trade-healthcheck.sh`'s `SKILL_DIR`-relative pattern) and the shipped plist points
`EARNHC_EARN_STATE_DIR` at Franklin's own `~/.blockrun/skills/earn/state` — confirmed live on this
machine: `~/.blockrun/skills/earn/state/pm-trade.trace.jsonl` (255.8K, actively growing) and
`sol-trade.trace.jsonl` (132.7K) both already exist from Franklin's real runs. So the healthcheck
itself needs nothing from claude-p's session to detect a problem.

**`self-fix.sh` (the repair side, unchanged this sprint) is NOT fully Franklin-scoped — a real
graduation gap**, read directly from `skills/self/self-fix.sh`:
1. `STATE="$HOME/.openclaw/state"`, `LOG="$HOME/.openclaw/logs/..."`, `RESULT`/`STARTMARK` all live
   under `$HOME/.openclaw` — per `~/anicca-project/CLAUDE.md`'s own "ローカル + push 先マップ" table
   this is claude-p/Dais's OpenClaw store (`github.com/Daisuke134/anicca-dais`), shared across
   every instance on this single macOS user account (`/Users/anicca`), NOT a per-instance
   `ANICCA_HOME`-scoped path (Franklin's own tree is `~/.blockrun`).
2. The fixer it spawns is the Anthropic `claude` CLI (`tmux new-session ... "$CLAUDE" --model sonnet
   --dangerously-skip-permissions ...`) — i.e. whichever Claude Code login is active on this shared
   macOS user account. Today that is claude-p's own human-funded Anthropic subscription, per
   `~/.claude/CLAUDE.md`'s model-division table (`実装 subagent: Sonnet`, fuel = Anthropic
   subscription), NOT Franklin's self-funded compute (BlockRun/x402 SOL wallet `8FpqdcCHqjqkVXR58e
   VJa53neXbJf9emXhvHhgeUPCV9`).

Net effect: a Franklin-triggered healthcheck CAN call `self-fix.sh` without claude-p's session
running — it is a fresh detached `tmux`+`claude` spawn, not dependent on an existing process, so
Franklin's self-heal is *operationally* decoupled from claude-p being online. But the repair work
itself is still *economically* paid for by the shared human-funded Anthropic subscription on this
machine, not by Franklin's own wallet/economy. Closing this fully (true financial self-heal
independence) needs either a per-instance Claude credential/budget for `self-fix.sh` to spawn under,
or swapping the fixer to a self-funded model path (e.g. via BlockRun/ClawRouter) — out of scope for
this sprint, documented here for the next P3 iteration.

## Not done this sprint (explicit, per task instructions)
- Plist NOT copied to `~/Library/LaunchAgents/`, NOT `launchctl load`ed.
- Old `ai.anicca.sol-trade-earning-healthcheck.plist` NOT unloaded/removed (README now documents
  that it should be, before the new plist is loaded, to avoid duplicate self-fix spawns for
  `earn/sol-trade`).
- No merge to `main`/`origin/main` — branch pushed only.

## self-heal iter1 fixes FIND-001..006

Fresh-context adversary impl review (`reviews/impl/iteration-1`, model per model-division table)
returned FAIL with 6 findings. This section is the honest correction of iteration-1's claims and
the fix for every finding.

- **FIND-001 (critical, correctness)**: iteration-1's CHANGELOG text above ("both [sol-trade,
  pm-trade] already write... the EXACT contract `is_fresh_but_barren` needs") was factually wrong.
  `earn/polymarket-trade`'s `run.sh` has a genuine THIRD trace state, `action:"error"`
  (`AGENT_HOME` missing / `pick.py` non-zero exit — `skills/earn/polymarket-trade/run.sh:23,185-186`),
  that the old `action == "skip"`-only predicate could never see, meaning a sustained pm-trade code
  bug would report `OK` forever. Fixed at the pure-core level:
  `earning-health.py::is_fresh_but_barren` now treats a sustained, identical-cause run of `skip` OR
  `error` entries as unhealthy (`_mechanism_failure_cause` reads `reason` for skip, `error` for
  error) — sol-trade's clean skip/live-pass-only vocabulary is unaffected (it never emits `error`).
  New pure-core tests: 20 identical errors → BARREN; 20 errors with two different causes → NOT
  barren; 19 errors then a real trade → NOT barren; empty error message → NOT barren
  (`skills/self/tests/test_earning_health.py`).
- **FIND-002 (major, coverage)**: added a genuine two-slots-BARREN-in-one-run scenario
  (`earn/slot-a` + `earn/slot-e`, different reasons/targets) to
  `skills/self/tests/test_earning_health_allslots.sh` — both flagged BARREN, both fire their own
  `self-fix.sh` call with their own `selfFixTarget`, both get their own marker file (asserted:
  exactly 2 distinct marker files exist), and each call's BLOCKER text is proven to carry only its
  OWN slot's reason (no cross-fire), via a new `EARNHC_SELF_FIX_SCRIPT` test seam + capture stub.
- **FIND-003 (minor, coverage)**: added a `slots: []` (present, valid, empty registry) test case,
  distinct from the pre-existing missing-registry-FILE case — asserts exit 0, zero
  OK/BARREN/NOT-INSTRUMENTED lines logged.
- **FIND-004 (major, test quality)**: `mk_healthy_trace()`'s fixture was 15 skip + 1 live-pass = 16
  total lines, below `minRun=20`, so the "healthy" verdict was actually proven by the
  `len(trace_tail) < min_run` short-circuit, not the trailing-live-pass-overrides-prior-skips path.
  Fixed to 25 skip + 1 live-pass = 26 total lines (>= minRun), which now genuinely exercises the
  real end-to-end wiring path this sprint added.
- **FIND-005 (major, security)**: trace-derived `reason`/`error` free text flowed unsanitized into
  `self-fix.sh`'s `--dangerously-skip-permissions` autonomous claude spawn prompt (zero human
  confirmation gate). Added `earning-health.py::sanitize_for_prompt` — an allowlist-only (letters,
  digits, space, `. , : ( ) = / -`) pure function, plus a `sanitize-reason` CLI subcommand —
  and wired `earning-health-allslots.sh` to sanitize BOTH the extracted reason/error text AND the
  slot id before building a FIXED structured BLOCKER message (never the raw trace text itself).
  Unit-tested at the pure-core level (malicious payload with backtick/`$()`/pipe/semicolon/angle
  brackets/ampersand all stripped, safe substring preserved, length capped, fail-soft on non-str)
  AND end-to-end via a new `EARNHC_SELF_FIX_SCRIPT` test seam + capture stub that proves the actual
  BLOCKER text handed to the self-fix invocation is neutralized.
- **FIND-006 (moderate, structural)**: added an in-file `DEPRECATED` header to
  `skills/earn/sol-trade/sol-trade-healthcheck.sh` pointing at `earning-health-allslots.sh` +
  the registry as the superseding mechanism, explaining why the file is kept (the old plist may
  still reference it until migration) rather than deleted.

Verified GREEN after all fixes:
```
target-feature-tests: PASS (test_earning_health.py 18/18, test_earning_health_allslots.sh 35/35)
regression-baseline: PASS (test_sol_trade_healthcheck.sh 9/9)
```
