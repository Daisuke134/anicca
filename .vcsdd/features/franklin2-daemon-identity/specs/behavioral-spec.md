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
- (impl-review iteration-2 FIND-001 fix — migration edge case) Scoping the pkill to `--home
  $ANICCA_HOME` (FIND-002 above) and adding that same `--home` argv marker to the poster's own launch
  command landed in the SAME commit (29023a55). This means a poster process still running under the
  PRIOR daemon.sh version (started before that commit, with NO `--home` argv marker) can never be
  matched by the new scoped pattern — on the FIRST self-update+restart that pulls this commit, for
  EITHER live Franklin instance, the old-generation poster is orphaned rather than killed, and a second
  poster loop starts alongside it, permanently duplicating the dashboard beat (the orphan can never
  subsequently match ANY future scoped pattern either, since it permanently lacks `--home`). THE SYSTEM
  SHALL additionally run a ONE-TIME, end-anchored cleanup `pkill -f
  "dashboard/telemetry-post-franklin\.mjs$"` (ERE `$` end-anchor, dot escaped) immediately after the
  scoped pkill and before the poster relaunch, so it matches ONLY a legacy (markerless) argv — a
  new-format argv always has a trailing " --home <path>" and therefore never ends at the script path,
  so it never double-matches an already-scoped process. This pattern is deliberately NOT
  instance-scoped (a legacy argv carries no `--home` to scope by) and so MAY cross-kill a sibling
  Franklin instance's own legacy poster once; that is an accepted, self-healing trade-off (the sibling's
  own next ~120s loop iteration or restart re-launches it) versus the alternative of permanent
  duplication. Safe to remove once every live Franklin-family instance has restarted at least once on
  this commit or later (no legacy-argv poster can exist anymore at that point).
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
