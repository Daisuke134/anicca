# Behavioral Spec — franklin2-daemon-identity (lean VCSDD, P4-code)

## Problem

`runtime/anicca-daemon.sh` branches on the LITERAL string `[ "$INSTANCE" = "franklin" ]` at 3 call
sites (step 2 brain-probe ~line 56, step 3 telemetry-poster choice ~line 104, step 4
wallet-address-derivation ~line 120). Franklin2's launchd plist sets `ANICCA_INSTANCE=franklin2`, which
does NOT literal-match `"franklin"`, so Franklin2 falls to the default/EVM branch, finds no EVM wallet,
and runs walletless (tier=broke) — even though `~/.franklin2-home/.blockrun/.solana-session` already
exists and would resolve correctly via the franklin branch (verified live, confidence 95%; see
`docs/loop-engineering/20-implementation-certainty-2026-07-11.md` §C, Gap B, in anicca-project).

## Purity Boundary Analysis

- **Pure core (new, this feature)**: the instance-classification predicate — a deterministic function
  of a single input string (`ANICCA_INSTANCE`) with no I/O, no process spawn, no network, no clock —
  returning true/false. This is the one piece of new logic this feature adds, and it is the ideal unit
  to extract and unit-test in isolation (mirrors the existing `PORT_SNIPPET` extraction technique in
  `runtime/loop/__tests__/daemon-script-franklin-routing.test.mjs`).
- **Effectful shell (unchanged)**: everything the classification gates — self-update git fetch/merge,
  curl readiness probes, `clawrouter`/node process spawns, `pkill`, telemetry loops, wallet-address
  derivation subprocess calls. This feature touches ONLY the branch *condition* at the 3 call sites,
  never the branch *bodies*.
- Note on regex-as-judgment: matching `ANICCA_INSTANCE` against a fixed machine identifier format
  (`franklin` or `franklin` + digits) is parsing, not a decision an LLM should make — no behavioral
  judgment is being replaced. The existing file already parses `FRANKLIN_PROXY_PORT`/`COMPUTE_PROXY_PORT`
  the same way. This is explicitly permitted per CLAUDE.md's "genuine parsing of a fixed machine format"
  carve-out.

## Requirements

### REQ-001: Franklin-family instance classification
**EARS**: WHEN `ANICCA_INSTANCE` equals `franklin` OR matches `franklin` followed by one or more digits
(i.e. the pattern `franklin` | `franklin[0-9]+`) THE SYSTEM SHALL classify the instance as a Franklin
instance for all 3 daemon routing decisions (brain-probe, telemetry-poster choice, wallet-address
derivation).
**Edge Cases**:
- `ANICCA_INSTANCE` unset → defaults to `clawrouter` (existing `${ANICCA_INSTANCE:-clawrouter}` default,
  untouched by this feature) → NOT franklin.
- `ANICCA_INSTANCE=""` (explicitly set empty) → bash `:-` treats empty as unset → defaults to
  `clawrouter` → NOT franklin (same as unset, no new handling needed).
- `ANICCA_INSTANCE=franklin` (the original citizen) → franklin (regression: identical to today).
- `ANICCA_INSTANCE=franklin2` → franklin (the new capability this feature adds).
- `ANICCA_INSTANCE=franklin10`, `franklin99` → franklin (multi-digit suffix, future spawns).
- `ANICCA_INSTANCE=franklinX`, `franklins`, `franklin-2`, `franklin2x` (non-digit or mixed suffix) →
  NOT franklin — fails closed to the existing default/EVM path (REQ-003).
- `ANICCA_INSTANCE=Franklin2` (capitalized) → NOT franklin — no case-insensitive matching (instance
  names are a controlled, lowercase-only vocabulary; matching case variants would be silent, unreviewed
  scope creep).
- `ANICCA_INSTANCE=clawrouter` (or any other unrelated string) → NOT franklin (regression: unchanged).
**Acceptance Criteria**:
- A single, pure, side-effect-free predicate implements this classification and is used at ALL 3 call
  sites (no per-site divergence, no leftover literal `"$INSTANCE" = "franklin"` string-equality anywhere
  in the file).
- The predicate is unit-testable in isolation without executing any of the file's git/curl/node/pkill
  side effects.

### REQ-002: Franklin-family instances route through the franklin paths
**EARS**: WHEN REQ-001 classifies the instance as franklin THE SYSTEM SHALL:
  (a) run the existing franklin brain-probe branch (curl readiness probe against the shared `:8402`
      router; never spawn `clawrouter`/`franklin proxy` — unchanged body, REQ-004/REQ-005 of
      franklin-loop-revival, out of scope here to re-verify beyond "still reached"),
  (b) loop `telemetry-post-franklin.mjs` (ed25519 Solana-key poster) instead of the EVM
      `telemetry-poster.mjs`,
  (c) derive `ANICCA_WALLET_ADDRESS` via `wallet-address-solana.mjs` instead of the EVM
      `wallet-address.mjs`.
**Edge Cases**:
- Franklin2's own `$ANICCA_HOME`/`$REPO` env (set by its own launchd plist, untouched here) is what the
  spawned node scripts inherit — no new hardcoding of "franklin2" anywhere; the SAME franklin branch body
  (the shell code in `anicca-daemon.sh` — the `if is_franklin_instance "$INSTANCE"` branches) serves
  franklin, franklin2, franklin3, … indistinguishably in that sense: every Franklin-family instance runs
  the identical code path. This does NOT mean every instance is dashboard-indistinguishable — the
  telemetry poster's `host` label and the `pkill` process-scoping inside that shared body are themselves
  instance-aware (per (b) below), precisely so two instances running the SAME body concurrently stay
  distinguishable on the dashboard and never interfere with each other's poster process.
- If Franklin2's `.solana-session` file were absent, `wallet-address-solana.mjs` prints nothing and exits
  0 (existing, out-of-scope behavior of that helper) — `ANICCA_WALLET_ADDRESS` stays unset, same
  non-fatal fail-open-to-empty behavior the franklin branch already has today. Not touched by this
  feature.
- (impl-review iteration-1 FIND-001 fix) `telemetry-post-franklin.mjs`'s dashboard `host` label derives
  from `ANICCA_INSTANCE`: `franklin` (or unset, for standalone/manual runs) → `"Franklin"` (backward
  compat — Franklin#1's existing dashboard row name never changes), `franklin2` → `"Franklin2"`, and
  generally `franklin<N>` → `"Franklin<N>"` (capitalize-first-letter of the instance name) — so two
  concurrently-running Franklin-family instances never report under the identical dashboard label.
- (impl-review iteration-1 FIND-002 fix) The franklin-branch telemetry `pkill` (step 3) is scoped to
  THIS instance's own `$ANICCA_HOME` (via a `--home "$ANICCA_HOME"` argv marker the poster is invoked
  with, which the poster script itself never parses) — a daemon restart of ONE Franklin-family instance
  can no longer kill ANOTHER concurrently-running instance's in-flight poster process, since both
  instances would otherwise present the identical `dashboard/telemetry-post-franklin.mjs` argv
  substring to an unscoped `pkill -f`.
- (impl-review iteration-3 FIND-001 fix — migration edge case, now OPERATIONAL, not code) Scoping the
  pkill to `--home $ANICCA_HOME` (FIND-002 above) and adding that same `--home` argv marker to the
  poster's own launch command landed in the SAME commit (29023a55). This means a poster process still
  running under the PRIOR daemon.sh version (started before that commit, with NO `--home` argv marker)
  can never be matched by the new scoped pattern — on the FIRST self-update+restart that pulls this
  commit, for EITHER live Franklin instance, the old-generation poster is orphaned rather than killed,
  and a second poster loop starts alongside it, permanently duplicating the dashboard beat. Iteration-2
  attempted to close this gap with an in-code, one-time, end-anchored, unscoped cleanup `pkill -f
  "dashboard/telemetry-post-franklin\.mjs$"`. Impl-review iteration-3 FIND-001 found that pattern is
  NOT actually one-time or migration-scoped in practice: `skills/earn/sol-trade/run.sh`'s own
  flagless, short-lived (`timeout 20`) one-shot telemetry POST invocation (a currently-live,
  unmodified, permanently-recurring caller of the identical script, never touched by this feature)
  ALSO ends its argv at the bare script-path substring on every single invocation, so it satisfies the
  same end-anchored pattern forever — not merely during a transient migration window. Any daemon.sh
  restart that overlaps an in-flight sol-trade telemetry POST would SIGTERM that legitimate, non-legacy
  process. THE SYSTEM THEREFORE SHALL NOT run any such sweep in code — the in-code cleanup pkill is
  REMOVED. The legacy-poster migration itself is deferred to a documented, ONE-TIME OPERATOR step (see
  "Deployment / migration runbook" below) performed once per instance, using the judgment a fixed argv
  pattern cannot safely encode (distinguishing a long-lived legacy LOOP from a short-lived legitimate
  one-shot caller by process lineage/lifetime, not argv shape alone).

#### Deployment / migration runbook (REQ-002(b), one-time, operational — NOT code)

After merging this commit (or any commit ≥ 29023a55) and restarting each live Franklin-family
instance's daemon ONCE, the operator performs the following one-time step per instance. This is
deliberately NOT automated as a pkill pattern — argv shape alone cannot safely distinguish a legacy
long-lived poster LOOP from `skills/earn/sol-trade/run.sh`'s own legitimate short-lived one-shot
invocation of the identical script (FIND-001 iter3):

1. `pgrep -fl "dashboard/telemetry-post-franklin.mjs"` — lists every currently-running process
   invoking the poster script, on this machine, across all instances.
2. For each listed PID, inspect its parent process (`ps -o ppid= -p <PID>` then `ps -o command=
   -p <PPID>`) to determine whether it is:
   - a long-lived LOOP poster (parent is an `anicca-daemon.sh` subshell — the `( export
     FRANKLIN_TELEMETRY_LOOP=1; while true; do ... sleep 120; done )` construct in step 3) started by
     a PRE-29023a55 daemon.sh (running since before the instance's most recent restart, argv has no
     ` --home ` substring) — this is the legacy process to kill, or
   - a short-lived, `timeout 20`-bounded one-shot invocation from `skills/earn/sol-trade/run.sh` (or
     any other one-shot caller) — NEVER kill this one; it exits on its own within ~20s.
3. Kill the PARENT loop subshell, NOT the transient node child: `kill <PPID>` (the subshell PID
   identified in step 2 whose command is the `while true; do ... sleep 120; done` construct). Killing
   only the child `node <PID>` is INSUFFICIENT — the orphaned parent loop respawns a fresh legacy-argv
   poster within 120 seconds (iteration-4 FIND-001). After killing the parent, also `kill` any
   still-running node child it spawned. The scoped, in-code
   `pkill -f "dashboard/telemetry-post-franklin.mjs --home $ANICCA_HOME"` (step 3 of
   anicca-daemon.sh, unchanged) relaunches the correct new-format poster for that instance on its own
   very next restart, so no manual relaunch is needed.
4. CONVERGENCE CHECK (not a single snapshot — a snapshot taken seconds after step 3 gives false
   confidence because legacy posters are one-shot children that exit and respawn on a 120s cycle):
   wait at least 150 seconds (> one full 120s respawn cycle), then re-run
   `pgrep -fl "dashboard/telemetry-post-franklin.mjs"` AND re-inspect parent lineage per step 2.
   Repeat the 150s-wait + check until two consecutive checks show zero legacy (markerless, loop-parented)
   posters. Transient one-shot callers like sol-trade's may legitimately appear/disappear and are not
   counted as duplicates.

This step runs ONCE per instance, at or shortly after deploy of this commit — it is not a recurring
operational task, and it is intentionally NOT expressed as code (iteration-3 FIND-001) because the
distinction it makes (long-lived loop vs. short-lived one-shot) is a judgment about process lifetime
and lineage, not a property any fixed argv pattern can safely encode without risking exactly the
cross-kill regression this fix removes.
**Acceptance Criteria**:
- With `ANICCA_INSTANCE=franklin2`, the brain-probe/telemetry/wallet-derivation branch conditions all
  evaluate true (same as `ANICCA_INSTANCE=franklin` today).
- With `ANICCA_INSTANCE=franklin2`, the telemetry poster's dashboard `host` label is `"Franklin2"`, never
  `"Franklin"` (FIND-001).
- The franklin-branch telemetry `pkill -f` pattern includes `$ANICCA_HOME` so it cannot match a sibling
  Franklin instance's poster process (FIND-002).

### REQ-003: Non-franklin instances unchanged (regression)
**EARS**: WHEN `ANICCA_INSTANCE` does NOT match the franklin pattern (REQ-001) THE SYSTEM SHALL follow
today's existing default path unchanged: ClawRouter brain, `telemetry-poster.mjs`, EVM
`wallet-address.mjs`.
**Acceptance Criteria**: `ANICCA_INSTANCE=clawrouter` / unset behave byte-identically to before this
feature (all pre-existing `daemon-script-franklin-routing.test.mjs` PORT/regression assertions for the
non-franklin path continue to pass unmodified).

### REQ-004: Fail-closed on unrecognized instance names
**EARS**: WHEN `ANICCA_INSTANCE` is an unrecognized string that does not match the franklin pattern
(typo, garbage, a not-yet-supported family name) THE SYSTEM SHALL silently default to today's
non-franklin (EVM/ClawRouter) path — never crash, never hang, never leave routing undefined.
**Acceptance Criteria**: every non-matching decoy string in REQ-001's edge-case list classifies as
NOT-franklin and drives the same default path as `clawrouter`.

## Non-Functional Requirements

- No new external dependency, no new file, no new process. The change is confined to
  `runtime/anicca-daemon.sh` (plus its test coverage).
- No plist edits, no wallet generation, no live-machine mutation — this feature is code-only (P4-code);
  the ops follow-up (EVM keypair, kickstart) is explicitly out of scope, per task instructions.
- Must remain POSIX-safe under the file's own `#!/usr/bin/env bash` + `set -uo pipefail` (no bashisms
  beyond what the file already uses, e.g. `${VAR:-default}`, `case`, are already in use elsewhere in the
  motherboard/repo).

## Changelog — impl iter2 fixes

- **FIND-001 (major, edge_case_coverage/implementation_correctness)**: added the one-time,
  end-anchored legacy-poster cleanup `pkill` documented in REQ-002(b) above, to close the
  guaranteed-to-occur orphaned-poster gap on the first restart after commit 29023a55.
- **FIND-002 (minor, structural_integrity)**: removed the dead `pkill -f "FRANKLIN_TELEMETRY_LOOP"`
  line — `pkill -f` matches a process's argv, never its exported environment, so this line never
  matched anything, on any instance, ever. The `export FRANKLIN_TELEMETRY_LOOP=1` on the poster
  subshell itself is untouched (harmless, unrelated to the dead pkill that targeted it).

## Changelog — impl iter3 fixes

- **FIND-001 (major, edge_case_coverage/implementation_correctness)**: removed the iteration-2
  in-code, one-time, unscoped, end-anchored legacy-poster-cleanup `pkill` — it permanently
  cross-matched `skills/earn/sol-trade/run.sh`'s own flagless, short-lived one-shot telemetry POST
  invocation on every restart, not only during a transient migration window. The legacy-poster
  migration is now a documented, one-time OPERATOR step (REQ-002(b) "Deployment / migration
  runbook" above) — operational, not code.
- **FIND-002 (minor, structural_integrity)**: the match-matrix simulation test now extracts the
  scoped pkill pattern VERBATIM from the real `anicca-daemon.sh` source text (rather than
  hand-copying an independently re-escaped pattern), expands `$ANICCA_HOME` via literal string
  substitution (matching bash's own interpolation semantics, unescaped dots included), and adds
  rows asserting sol-trade's one-shot argv is never matched by either instance's scoped pattern.
- **FIND-003 (minor, verification_readiness)**: synced `verification-architecture.md` with
  PROP-009 (dead-pkill removal) and PROP-010 (verbatim scoped-pattern matrix / sol-trade
  non-match), and added the migration edge case to the Verification Strategy prose.
