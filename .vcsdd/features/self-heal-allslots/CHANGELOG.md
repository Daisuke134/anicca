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

- **`earn/sol-trade`, `earn/polymarket-trade`**: both already write a dedicated per-wake
  `{"action":"skip","reason":"..."}` trace (`sol-trade.trace.jsonl` / `pm-trade.trace.jsonl` under
  `skills/earn/state/`) — the EXACT contract `is_fresh_but_barren` needs. Wiring these was a direct,
  safe generalization (pm-trade newly wired this sprint; sol-trade was already wired via the
  pre-existing slot-specific script, now duplicated by the registry for parity/regression, plist
  NOT double-loaded — see `launchd/README.md`).
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
